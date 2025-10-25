import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAEE8OIOqLYxbnwesF3ki2sOsXr03Q90JiI'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    return str(timedelta(seconds=seconds))

def parse_time_to_seconds(time_str):
    try:
        parts = [int(p) for p in time_str.strip().split(':')]
        if len(parts) == 3:
            h, m, s = parts
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = parts
            return m * 60 + s
        elif len(parts) == 1:
            return int(parts[0])
        else:
            raise ValueError("Invalid format")
    except (ValueError, IndexError):
        raise ValueError(f"فرمت زمان اشتباه: '{time_str}'. لطفاً از hh:mm:ss (مثل 00:01:23) یا mm:ss استفاده کنید.")

def download_progress(current, total):
    print(f"Download progress: {current} / {total} bytes ({(current / total * 100):.1f}%)")

@app.on_message(filters.command("start"))
async def start(_, message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✂️", callback_data="start_cutting")]]
    )
    await message.reply("سلام! برای برش ویدیو روی دکمه زیر کلیک کن:", reply_markup=keyboard)

@app.on_callback_query()
async def handle_callback(_, callback_query):
    user_id = callback_query.from_user.id

    if callback_query.data == "start_cutting":
        user_state[user_id] = {
            "step": "awaiting_video"
        }
        await callback_query.message.reply("لطفاً ویدیوی موردنظر را ارسال کنید.")

    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state:
            return

        await callback_query.answer("در حال برش...", show_alert=False)

        # پاک کردن پیام دکمه
        await callback_query.message.delete()

        chat_id = callback_query.message.chat.id
        temp_input = f"/tmp/{user_id}_input.mp4"  # تغییر به /tmp برای writable
        temp_output = f"/tmp/{user_id}_cut.mp4"

        try:
            # دانلود ویدیو با progress callback
            print(f"Starting download for user {user_id}...")
            video_msg = await app.get_messages(chat_id, state["video_msg_id"])
            await video_msg.download(
                file_name=temp_input,
                progress=download_progress,
                progress_args=(user_id,)
            )
            
            # چک دقیق فایل دانلود شده
            if not os.path.exists(temp_input):
                raise Exception("Downloaded file does not exist in /tmp")
            file_size = os.path.getsize(temp_input)
            if file_size == 0:
                raise Exception("Downloaded file is empty (0 bytes)")
            print(f"Download successful: {temp_input} (size: {file_size} bytes)")

            start_sec = state["start_sec"]
            end_sec = state["end_sec"]

            # ارسال پیام جداگانه در حال پردازش
            processing_msg = await app.send_message(chat_id, "در حال پردازش ویدیو...")

            # برش ویدیو
            try:
                (
                    ffmpeg
                    .input(temp_input, ss=start_sec, to=end_sec)
                    .output(temp_output)
                    .run(overwrite_output=True, quiet=True)
                )
                
                # چک فایل خروجی
                if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                    await app.send_video(chat_id, temp_output)
                    await processing_msg.edit("✅ برش ویدیو با موفقیت تمام شد!")
                else:
                    raise Exception("Output file not created or empty")
                    
            except ffmpeg.Error as e:
                error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
                print(f"FFmpeg Error: {error_msg}")
                await processing_msg.edit(f"❌ خطا در برش ویدیو: {error_msg}\nلطفاً تایم‌ها را چک کنید.")
            except Exception as e:
                print(f"Unexpected Error in trimming: {e}")
                await processing_msg.edit("❌ خطای غیرمنتظره در پردازش ویدیو.")
            
            # پاک کردن فایل‌ها
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
        except Exception as e:
            print(f"Download Error: {e}")
            await app.send_message(chat_id, f"❌ خطا در دانلود ویدیو: {str(e)}\nلطفاً ویدیو را دوباره ارسال کنید (ویدیو کوچک‌تر امتحان کنید).")
        
        del user_state[user_id]

@app.on_message(filters.video)
async def handle_video(_, message):
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    duration_sec = message.video.duration
    duration_hms = seconds_to_hms(duration_sec)

    text = (
        f"⏱ زمان ویدیو: {duration_hms}\n"
        f"⏳ تایم شروع: {{}}\n"
        f"⏳ تایم پایان: {{}}"
    )
    sent_msg = await message.reply(text)

    start_prompt_msg = await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")

    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id,
        "video_edit_msg": sent_msg.id,
        "duration_sec": duration_sec,
        "duration_hms": duration_hms,
        "start_time": None,
        "end_time": None,
        "start_prompt_id": start_prompt_msg.id
    })

@app.on_message(filters.text)
async def handle_time(_, message):
    user_id = message.from_user.id
    state = user_state.get(user_id)

    if not state:
        return

    if state["step"] == "awaiting_start":
        try:
            start_sec = parse_time_to_seconds(message.text)
            if start_sec > state["duration_sec"]:
                await message.reply("❌ تایم شروع نمی‌تواند بیشتر از طول ویدیو باشد!")
                return
            user_state[user_id]["start_sec"] = start_sec
            user_state[user_id]["start_time"] = message.text
            state["step"] = "awaiting_end"

            video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
            new_text = (
                f"⏱ زمان ویدیو: {state['duration_hms']}\n"
                f"⏳ تایم شروع: {state['start_time']}\n"
                f"⏳ تایم پایان: {{}}"
            )
            await video_msg.edit(new_text)

            # حذف پیام کاربر و پیام پرامپت شروع
            await message.delete()
            await app.delete_messages(message.chat.id, state["start_prompt_id"])

            end_prompt_msg = await message.reply("حالا تایم پایان را وارد کنید (hh:mm:ss)")
            user_state[user_id]["end_prompt_id"] = end_prompt_msg.id
        except ValueError as e:
            await message.reply(str(e))

    elif state["step"] == "awaiting_end":
        try:
            end_sec = parse_time_to_seconds(message.text)
            start_sec = state["start_sec"]
            if end_sec <= start_sec:
                await message.reply("❌ تایم پایان باید بیشتر از تایم شروع باشد!")
                return
            if end_sec > state["duration_sec"]:
                await message.reply("❌ تایم پایان نمی‌تواند بیشتر از طول ویدیو باشد!")
                return
            user_state[user_id]["end_sec"] = end_sec
            user_state[user_id]["end_time"] = message.text
            state["step"] = "ready"

            video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
            new_text = (
                f"⏱ زمان ویدیو: {state['duration_hms']}\n"
                f"⏳ تایم شروع: {state['start_time']}\n"
                f"⏳ تایم پایان: {state['end_time']}"
            )
            await video_msg.edit(new_text, reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("شروع برش", callback_data="cut_now")]]
            ))

            # حذف پیام کاربر و پیام پرامپت پایان
            await message.delete()
            await app.delete_messages(message.chat.id, state["end_prompt_id"])
        except ValueError as e:
            await message.reply(str(e))

app.run()
