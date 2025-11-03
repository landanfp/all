import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta

# --- تنظیمات (Configuration) ---
API_ID = '3335792' # مثال، لطفاً از مقادیر واقعی خود استفاده کنید
API_HASH = '138b992a0e672e8346d8439c3f42ea78' # مثال، لطفاً از مقادیر واقعی خود استفاده کنید
BOT_TOKEN = '5355055672:AAEE8OIOqLYxbnwesF3ki2sOsXr03Q90JiI' # مثال، لطفاً از مقادیر واقعی خود استفاده کنید
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
        [[InlineKeyboardButton("✂️ شروع برش", callback_data="start_cutting")]]
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
        # ذخیره ID پیام راهنما برای حذف
        prompt_msg = await callback_query.message.reply("لطفاً ویدیوی موردنظر را ارسال کنید.")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id
        await callback_query.answer()

    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state:
            await callback_query.answer("فرآیند برش منقضی شده است. دوباره شروع کنید.", show_alert=True)
            return

        await callback_query.answer("در حال برش...")
        
        # ویرایش پیام دکمه برای حذف دکمه
        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            # ممکن است پیام قبلاً توسط کاربر یا ربات تغییر داده شده باشد
            pass

        temp_input = f"{user_id}_input.mp4"
        temp_output = f"{user_id}_cut.mp4"

        try:
            # --- دانلود ویدیو ---
            video_msg = await app.get_messages(chat_id, state["video_msg_id"])
            
            processing_msg = await callback_query.message.reply("🔄 در حال دانلود ویدیو...")
            await video_msg.download(temp_input)

            start = state["start_time"]
            end = state["end_time"]

            await processing_msg.edit_text("⚙️ در حال پردازش و برش دقیق ویدیو (کمی صبر کنید)...")

            # --------------------------------------------------------------------------
            # --- برش با FFmpeg (رفع مشکل: حذف c="copy" و استفاده از Re-encoding) ---
            #
            # برای اطمینان از صحت برش در هر زمانی، از رمزگذاری مجدد استفاده می‌کنیم:
            # vcodec='libx264' و acodec='aac' - کدک‌های استاندارد برای MP4
            # preset='veryfast' - برای سرعت بخشیدن به رمزگذاری
            # movflags='faststart' - برای شروع سریع پخش در وب
            # --------------------------------------------------------------------------
            
            (
                ffmpeg
                .input(temp_input, ss=start) # ss (تایم شروع) را قبل از ورودی قرار می‌دهیم
                .output(temp_output, to=end, 
                        vcodec='libx264', 
                        acodec='aac', 
                        f='mp4',
                        preset='veryfast',
                        movflags='faststart',
                        loglevel="error") # to (تایم پایان) را برای خروجی مشخص می‌کنیم
                .run(overwrite_output=True)
            )

            # --- آپلود و ارسال نتیجه ---
            await processing_msg.edit_text("📤 در حال ارسال ویدیوی برش‌خورده...")
            await app.send_video(chat_id, temp_output)
            await processing_msg.edit_text("✅ تمام شد! ویدیوی برش‌خورده ارسال شد.")

        except ffmpeg.Error as e:
            # تلاش برای استخراج جزئیات خطا از FFmpeg
            error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است."
            await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`")
        except Exception as e:
            # خطای غیرمنتظره دیگر
            await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: `{e}`")
        finally:
            # --- پاکسازی فایل‌ها و وضعیت ---
            if os.path.exists(temp_input):
                os.path.exists(temp_input) and os.remove(temp_input)
            if os.path.exists(temp_output):
                os.path.exists(temp_output) and os.remove(temp_output)
            
            if user_id in user_state:
                del user_state[user_id]


@app.on_message(filters.video)
async def handle_video(_, message):
    """دریافت ویدیو و ذخیره وضعیت."""
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    # حذف پیام راهنمای قبلی (لطفاً ویدیوی موردنظر را ارسال کنید.)
    if "prompt_msg_id" in user_state[user_id]:
        try:
            await app.delete_messages(message.chat.id, user_state[user_id]["prompt_msg_id"])
        except Exception:
            # اگر پیام پیدا نشد یا قبلاً حذف شده بود، مهم نیست.
            pass

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

    # ارسال و ذخیره ID پیام راهنما برای مرحله بعد (تایم شروع)
    prompt_msg = await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")
    user_state[user_id]["prompt_msg_id"] = prompt_msg.id

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
        video_msg = await app.get_messages(chat_id, state["video_edit_msg"])
    except Exception:
        return

    # 1. حذف پیام ورودی کاربر
    user_message_id = message.id
    # 2. حذف پیام راهنمای ربات (از مرحله قبل)
    prompt_message_id = state.pop("prompt_msg_id", None)

    if prompt_message_id:
        try:
            # سعی می‌کنیم هر دو پیام را همزمان حذف کنیم
            await app.delete_messages(chat_id, [user_message_id, prompt_message_id])
        except Exception:
            pass # نادیده گرفتن خطا در حذف پیام‌ها

    if state["step"] == "awaiting_start":
        user_state[user_id]["start_time"] = message.text
        state["step"] = "awaiting_end"

        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: ..."
        )
        await video_msg.edit_text(new_text)
        
        # ارسال و ذخیره ID پیام راهنما برای مرحله بعد (تایم پایان)
        prompt_msg = await message.reply("حالا تایم پایان را وارد کنید (hh:mm:ss)")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id

    elif state["step"] == "awaiting_end":
        user_state[user_id]["end_time"] = message.text
        state["step"] = "ready"
        # در این مرحله دیگر نیازی به ذخیره prompt_msg_id جدید نیست چون آخرین مرحله است.

        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {state['end_time']}"
        )
        await video_msg.edit_text(new_text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("شروع برش", callback_data="cut_now")]]
        ))

app.run()
