import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta
import time  # اضافه کردن ماژول time

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, secs)

@app.on_message(filters.command("start"))
async def start(_, message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✂️ برش ویدیو", callback_data="start_cutting")]]
    )
    await message.reply("سلام! برای برش ویدیو روی دکمه زیر کلیک کنید:", reply_markup=keyboard)

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

        await callback_query.answer("در حال برش...")

        video_msg = await app.get_messages(callback_query.message.chat.id, state["video_msg_id"])
        temp_input = f"{user_id}_input.mp4"
        temp_output = f"{user_id}_cut.mp4"
        try:
            print(f"در حال دانلود ویدیو به: {temp_input}")
            await video_msg.download(temp_input)
            print(f"دانلود ویدیو به پایان رسید.")
        except Exception as e:
            print(f"Error downloading video: {e}")
            await callback_query.message.reply("متاسفانه در دانلود ویدیو مشکلی پیش آمد.")
            return

        if not os.path.exists(temp_input):
            print(f"فایل ورودی بلافاصله بعد از دانلود پیدا نشد: {temp_input}")
            await callback_query.message.reply("متاسفانه فایل ویدیوی ورودی پیدا نشد.")
            return
        else:
            print(f"فایل ورودی بلافاصله بعد از دانلود پیدا شد: {temp_input}")

        await asyncio.sleep(3)  # افزودن تأخیر 3 ثانیه (فقط برای تست)

        if not os.path.exists(temp_input):
            print(f"فایل ورودی بعد از تأخیر پیدا نشد: {temp_input}")
            await callback_query.message.reply("متاسفانه فایل ویدیوی ورودی پیدا نشد.")
            return
        else:
            print(f"فایل ورودی بعد از تأخیر پیدا شد: {temp_input}")

        start = state["start_time"]
        end = state["end_time"]

        await callback_query.message.reply("در حال پردازش ویدیو...")

        try:
            print(f"در حال اجرای FFmpeg با ورودی: {temp_input}، شروع: {start}، پایان: {end}، خروجی: {temp_output}")
            (
                ffmpeg
                .input(temp_input, ss=start, to=end)
                .output(temp_output)
                .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"پردازش FFmpeg به پایان رسید.")
        except ffmpeg.Error as e:
            print(f"FFmpeg error: {e.stderr.decode('utf8')}")
            await callback_query.message.reply(f"متاسفانه در هنگام برش ویدیو مشکلی پیش آمد:\n{e.stderr.decode('utf8')}")
            os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            del user_state[user_id]
            return
        except Exception as e:
            print(f"General error during processing: {e}")
            await callback_query.message.reply(f"متاسفانه در هنگام پردازش ویدیو مشکلی پیش آمد:\n{e}")
            os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            del user_state[user_id]
            return

        await app.send_video(callback_query.message.chat.id, temp_output)
        await callback_query.message.edit("برش ویدیو با موفقیت انجام شد!")

        os.remove(temp_input)
        os.remove(temp_output)
        del user_state[user_id]

@app.on_message(filters.video)
async def handle_video(_, message):
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    duration_seconds = message.video.duration
    duration_hms = seconds_to_hms(duration_seconds)

    text = (
        f"⏱ زمان ویدیو: {duration_hms}\n"
        f"⏳ تایم شروع: {{}}\n"
        f"⏳ تایم پایان: {{}}"
    )
    sent_msg = await message.reply(text)
    sent_start_prompt = await message.reply("لطفاً تایم شروع را به فرمت `hh:mm:ss` وارد کنید.")

    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id,
        "video_edit_msg": sent_msg.id,
        "video_duration": duration_seconds,
        "duration_hms": duration_hms,
        "start_time": None,
        "end_time": None,
        "start_prompt_id": sent_start_prompt.id
    })

@app.on_message(filters.text)
async def handle_time(_, message):
    print(f"پیام متنی دریافت شد: {message.text}, از کاربر: {message.from_user.id}")
    user_id = message.from_user.id
    state = user_state.get(user_id)
    print(f"وضعیت کاربر {user_id}: {state}")
    if not state:
        return
    if state.get("step") == "awaiting_start":
        print("وارد بخش awaiting_start شد.")
        start_time = message.text
        try:
            h, m, s = map(int, start_time.split(":"))
            start_seconds = h * 3600 + m * 60 + s
            if start_seconds > state["video_duration"]:
                await message.reply("⚠️ تایم شروع نباید بیشتر از زمان کل ویدیو باشد.")
                return
        except ValueError:
            await message.reply("⚠️ فرمت تایم شروع اشتباه است. لطفاً به فرمت `hh:mm:ss` وارد کنید.")
            return

        user_state[user_id]["start_time"] = start_time
        state["step"] = "awaiting_end"

        try:
            video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
            new_text = (
                f"⏱ زمان ویدیو: {state['duration_hms']}\n"
                f"⏳ تایم شروع: {start_time}\n"
                f"⏳ تایم پایان: {{}}"
            )
            await video_msg.edit(new_text)
            await app.delete_messages(message.chat.id, state["start_prompt_id"])
            sent_end_prompt = await message.reply("حالا تایم پایان را به فرمت `hh:mm:ss` وارد کنید.")
            user_state[user_id]["end_prompt_id"] = sent_end_prompt.id
        except Exception as e:
            print(f"Error editing/deleting message: {e}")
            await message.reply("متاسفانه در به‌روزرسانی/حذف پیام مشکلی پیش آمد. لطفاً تایم پایان را وارد کنید.")


    elif state["step"] == "awaiting_end":
        end_time = message.text
        try:
            h, m, s = map(int, end_time.split(":"))
            end_seconds = h * 3600 + m * 60 + s
            if end_seconds > state["video_duration"]:
                await message.reply("⚠️ تایم پایان نباید بیشتر از زمان کل ویدیو باشد.")
                return
            if state["start_time"]:
                start_h, start_m, start_s = map(int, state["start_time"].split(":"))
                start_total_seconds = start_h * 3600 + start_m * 60 + start_s
                if end_seconds <= start_total_seconds:
                    await message.reply("⚠️ تایم پایان نباید قبل یا مساوی تایم شروع باشد.")
                    return
        except ValueError:
            await message.reply("⚠️ فرمت تایم پایان اشتباه است. لطفاً به فرمت `hh:mm:ss` وارد کنید.")
            return

        user_state[user_id]["end_time"] = end_time
        state["step"] = "ready"

        try:
            video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
            new_text = (
                f"⏱ زمان ویدیو: {state['duration_hms']}\n"
                f"⏳ تایم شروع: {state['start_time']}\n"
                f"⏳ تایم پایان: {end_time}"
            )
            await video_msg.edit(new_text, reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ شروع برش", callback_data="cut_now")]]
            ))
            await app.delete_messages(message.chat.id, state["end_prompt_id"])
        except Exception as e:
            print(f"Error editing/deleting message: {e}")
            await message.reply("متاسفانه در به‌روزرسانی/حذف پیام مشکلی پیش آمد. لطفاً مجدداً تلاش کنید.")

app.run()
