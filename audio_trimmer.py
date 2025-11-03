import os
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import MessageNotModified
from pyrogram.errors import RPCError 

# <<< ایمپورت از config.py برای رفع خطای چرخشی >>>
from config import user_state, seconds_to_hms, app

# --- توابع برش صدا ---

async def handle_audio_file(client: Client, message: Message):
    """دریافت فایل صوتی و ذخیره وضعیت برای دریافت زمان شروع."""
    user_id = message.from_user.id
    
    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_audio":
        return

    # پاک کردن پیام پرامپت قبلی
    if "prompt_msg_id" in user_state[user_id]:
        try:
            await client.delete_messages(message.chat.id, user_state[user_id]["prompt_msg_id"])
        except RPCError:
             pass

    # بررسی نوع فایل (اطمینان از فایل صوتی)
    if not message.audio:
        # <<< پیام خطا برای پشتیبانی از M4A/MP3 به‌روزرسانی شد >>>
        await message.reply("لطفاً یک فایل صوتی معتبر (مانند MP3 یا M4A) ارسال کنید.")
        if user_id in user_state:
            del user_state[user_id]
        return

    duration = seconds_to_hms(message.audio.duration)

    text = (
        f"⏱ زمان فایل صوتی: {duration}\n"
        f"⏳ تایم شروع: ...\n"
        f"⏳ تایم پایان: ..."
    )
    sent_msg = await message.reply(text)

    user_state[user_id].update({
        "step": "awaiting_start",
        "media_type": "audio", 
        "audio_msg_id": message.id, 
        "media_edit_msg": sent_msg.id, 
        "duration": duration,
        "start_time": None,
        "end_time": None
    })

    prompt_msg = await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")
    user_state[user_id]["prompt_msg_id"] = prompt_msg.id


async def cut_audio_action(client: Client, callback_query):
    """منطق برش فایل صوتی."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    state = user_state.get(user_id)
    
    if not state or state.get("media_type") != "audio":
        await callback_query.answer("فرآیند برش منقضی شده است. دوباره شروع کنید.", show_alert=True)
        return

    await callback_query.answer("در حال برش فایل صوتی...")
    
    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except MessageNotModified:
        pass
    except Exception:
        pass

    # <<< نام فایل ورودی دیگر پسوند ثابت ندارد >>>
    expected_input_filename = f"{user_id}_input_audio" 
    # <<< نام فایل خروجی به M4A تغییر یافت >>>
    temp_output = f"{user_id}_cut_audio.m4a"
    downloaded_file_path = None

    try:
        # --- دانلود فایل صوتی ---
        audio_msg = await app.get_messages(chat_id, state["audio_msg_id"])
        
        processing_msg = await callback_query.message.reply("🔄 در حال دانلود فایل صوتی...")
        # Pyrogram پسوند اصلی فایل را در زمان دانلود اضافه می‌کند
        downloaded_file_path = await audio_msg.download(expected_input_filename)
        
        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            raise Exception("دانلود فایل صوتی ناموفق بود یا فایل ورودی پیدا نشد.")

        start = state["start_time"]
        end = state["end_time"]

        await processing_msg.edit_text("⚡️ در حال برش سریع (کپی جریان)...")

        # --- برش با FFmpeg: استفاده از Stream Copy ---
        # FFmpeg با c="copy" تلاش می‌کند جریان صوتی را بدون رمزگذاری مجدد کپی کند.
        # m4a برای خروجی مناسب است و send_audio آن را می‌شناسد.
        (
            ffmpeg
            .input(downloaded_file_path, ss=start) 
            .output(temp_output, to=end, c="copy", loglevel="error")
            .run(overwrite_output=True)
        )

        # --- آپلود و ارسال نتیجه ---
        await processing_msg.edit_text("📤 در حال ارسال فایل صوتی برش‌خورده...")
        await app.send_audio(chat_id, temp_output)
        await processing_msg.edit_text("✅ تمام شد! فایل صوتی برش‌خورده ارسال شد.")

    except ffmpeg.Error as e:
        error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است."
        await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`\n\n**توجه:** این خطا ممکن است به دلیل عدم امکان برش دقیق در نقطه زمانی درخواستی رخ داده باشد.")
    except Exception as e:
        await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: دانلود یا پردازش با مشکل مواجه شد. `{e}`")
    finally:
        # --- پاکسازی فایل‌ها و وضعیت ---
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        if user_id in user_state:
            del user_state[user_id]
