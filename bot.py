import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta

# --- تنظیمات ---
# مقادیر شما
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAEE8OIOqLYxbnwesF3ki2sOsXr03Q90JiI'
LOG_CHANNEL = -1001792962793 

app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    """تبدیل ثانیه به فرمت زمان (hh:mm:ss)."""
    return str(timedelta(seconds=seconds))

@app.on_message(filters.command("start"))
async def start(_, message):
    """پاسخ به دستور /start و نمایش دکمه شروع."""
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✂️", callback_data="start_cutting")]]
    )
    await message.reply("سلام! برای برش ویدیو روی دکمه زیر کلیک کن:", reply_markup=keyboard)

@app.on_callback_query()
async def handle_callback(_, callback_query):
    """مدیریت دکمه‌های شیشه‌ای."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    if callback_query.data == "start_cutting":
        user_state[user_id] = {
            "step": "awaiting_video"
        }
        await callback_query.message.reply("لطفاً ویدیوی موردنظر را ارسال کنید.")
        await callback_query.answer()

    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state:
            await callback_query.answer("فرآیند برش منقضی شده است. دوباره شروع کنید.", show_alert=True)
            return

        await callback_query.answer("در حال برش...")
        await callback_query.message.edit_reply_markup(reply_markup=None) 

        temp_input = f"{user_id}_input.mp4"
        temp_output = f"{user_id}_cut.mp4"

        try:
            # --- دانلود ویدیو ---
            video_msg = await app.get_messages(chat_id, state["video_msg_id"])
            
            processing_msg = await callback_query.message.reply("🔄 در حال دانلود و پردازش ویدیو...")
            await video_msg.download(temp_input)

            start = state["start_time"]
            end = state["end_time"]

            await processing_msg.edit_text("⚙️ در حال پردازش ویدیو...")

            # --- برش با FFmpeg (با استفاده از c="copy" برای سرعت) ---
            (
                ffmpeg
                .input(temp_input, ss=start, to=end)
                .output(temp_output, c="copy", loglevel="error") # loglevel="error" برای کاهش خروجی کنسول
                .run(overwrite_output=True)
            )

            # --- آپلود و ارسال نتیجه ---
            await processing_msg.edit_text("📤 در حال ارسال ویدیوی برش‌خورده...")
            await app.send_video(chat_id, temp_output)
            await processing_msg.edit_text("✅ تمام شد! ویدیوی برش‌خورده ارسال شد.")

        except ffmpeg.Error as e:
            error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است."
            await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`")
        except Exception as e:
            await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: {e}")
        finally:
            # --- پاکسازی فایل‌ها و وضعیت ---
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
            if user_id in user_state:
                 del user_state[user_id]


@app.on_message(filters.video)
async def handle_video(_, message):
    """دریافت ویدیو و ذخیره وضعیت."""
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    duration = seconds_to_hms(message.video.duration)

    text = (
        f"⏱ زمان ویدیو: {duration}\n"
        f"⏳ تایم شروع: ...\n"
        f"⏳ تایم پایان: ..."
    )
    sent_msg = await message.reply(text)

    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id,
        "video_edit_msg": sent_msg.id, 
        "duration": duration,
        "start_time": None,
        "end_time": None
    })

    await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")

@app.on_message(filters.text)
async def handle_time(_, message):
    """دریافت زمان شروع و پایان و به‌روزرسانی پیام اصلی."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    state = user_state.get(user_id)

    if not state:
        return

    # دریافت شیء پیام ویرایش‌پذیر
    try:
        # استفاده از app.get_messages برای دریافت شیء پیام با استفاده از ID
        video_msg = await app.get_messages(chat_id, state["video_edit_msg"])
    except Exception:
        return # اگر پیام اصلی حذف شده باشد

    if state["step"] == "awaiting_start":
        user_state[user_id]["start_time"] = message.text
        state["step"] = "awaiting_end"

        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: ..."
        )
        # رفع مشکل بروزرسانی: استفاده از متد استاندارد .edit_text()
        await video_msg.edit_text(new_text)
        await message.reply("حالا تایم پایان را وارد کنید (hh:mm:ss)")

    elif state["step"] == "awaiting_end":
        user_state[user_id]["end_time"] = message.text
        state["step"] = "ready"

        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {state['end_time']}"
        )
        # رفع مشکل بروزرسانی: استفاده از متد استاندارد .edit_text() و افزودن دکمه
        await video_msg.edit_text(new_text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("شروع برش", callback_data="cut_now")]]
        ))

app.run()
