import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '1396293494:AAFY7RXygNEZPFPXfmoJ66SljlXeCSilXG0'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    return str(timedelta(seconds=seconds))

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

        # فیکس: تغییر alert به show_alert
        await callback_query.answer("در حال برش...", show_alert=False)

        # پاک کردن پیام دکمه
        await callback_query.message.delete()

        try:
            # دانلود ویدیو
            video_msg = await app.get_messages(callback_query.message.chat.id, state["video_msg_id"])
            temp_input = f"{user_id}_input.mp4"
            temp_output = f"{user_id}_cut.mp4"
            await video_msg.download(temp_input)

            start = state["start_time"]
            end = state["end_time"]

            # ارسال پیام جداگانه در حال پردازش
            processing_msg = await app.send_message(callback_query.message.chat.id, "در حال پردازش ویدیو...")

            # برش ویدیو با try-except
            try:
                (
                    ffmpeg
                    .input(temp_input, ss=start, to=end)
                    .output(temp_output)
                    .run(overwrite_output=True, quiet=True)  # quiet برای کمتر لاگ
                )
                
                # چک کن که فایل خروجی وجود داره
                if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                    await app.send_video(callback_query.message.chat.id, temp_output)
                    await processing_msg.edit("✅ برش ویدیو با موفقیت تمام شد!")
                else:
                    await processing_msg.edit("❌ خطا: فایل برش خورده تولید نشد. لطفاً دوباره امتحان کنید.")
            except ffmpeg.Error as e:
                print(f"FFmpeg Error: {e.stderr.decode() if e.stderr else e}")
                await processing_msg.edit("❌ خطا در برش ویدیو: فرمت زمان اشتباه است یا ویدیو پشتیبانی نمی‌شود. لطفاً تایم‌ها را چک کنید (hh:mm:ss).")
            except Exception as e:
                print(f"Unexpected Error in trimming: {e}")
                await processing_msg.edit("❌ خطای غیرمنتظره در پردازش ویدیو.")
            
            # پاک کردن فایل‌ها
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
        except Exception as e:
            print(f"Download or other Error: {e}")
            await app.send_message(callback_query.message.chat.id, "❌ خطا در دانلود ویدیو.")
        
        del user_state[user_id]

@app.on_message(filters.video)
async def handle_video(_, message):
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    duration = seconds_to_hms(message.video.duration)

    text = (
        f"⏱ زمان ویدیو: {duration}\n"
        f"⏳ تایم شروع: {{}}\n"
        f"⏳ تایم پایان: {{}}"
    )
    sent_msg = await message.reply(text)

    start_prompt_msg = await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")

    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id,
        "video_edit_msg": sent_msg.id,
        "duration": duration,
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
        user_state[user_id]["start_time"] = message.text
        state["step"] = "awaiting_end"

        video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {{}}"
        )
        await video_msg.edit(new_text)

        # حذف پیام کاربر و پیام پرامپت شروع
        await message.delete()
        await app.delete_messages(message.chat.id, state["start_prompt_id"])

        end_prompt_msg = await message.reply("حالا تایم پایان را وارد کنید (hh:mm:ss)")
        user_state[user_id]["end_prompt_id"] = end_prompt_msg.id

    elif state["step"] == "awaiting_end":
        user_state[user_id]["end_time"] = message.text
        state["step"] = "ready"

        video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {state['end_time']}"
        )
        await video_msg.edit(new_text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("شروع برش", callback_data="cut_now")]]
        ))

        # حذف پیام کاربر و پیام پرامپت پایان
        await message.delete()
        await app.delete_messages(message.chat.id, state["end_prompt_id"])

app.run()
