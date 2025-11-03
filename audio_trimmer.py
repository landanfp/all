import os
import ffmpeg
# Pyrogram و انواع داده‌های مورد نیاز برای مدیریت پیام‌ها و دکمه‌ها
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import MessageNotModified
from pyrogram.errors import RPCError 

# فرض می‌کنیم bot.py و audio_trimmer.py در یک دایرکتوری هستند.
# برای دسترسی به متغیرهای مشترک (user_state، app، seconds_to_hms) از ایمپورت مستقیم استفاده می‌شود.
# توجه: اگر در زمان اجرا خطای ایمپورت (ImportError) گرفتید، ممکن است نیاز باشد
# متغیرهای user_state و seconds_to_hms را در یک فایل config.py جداگانه تعریف کنید.
from bot import user_state, seconds_to_hms, app

# --- توابع برش صدا ---

# این تابع در bot.py با استفاده از app.add_handler به ربات اضافه می‌شود
async def handle_audio_file(client: Client, message: Message):
    """دریافت فایل صوتی و ذخیره وضعیت برای دریافت زمان شروع."""
    user_id = message.from_user.id
    
    # بررسی کنید آیا کاربر فرآیند برش صدا را شروع کرده است (awaiting_audio)
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
        await message.reply("لطفاً یک فایل صوتی معتبر (مانند MP3) ارسال کنید.")
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

    # به‌روزرسانی وضعیت کاربر برای برش صدا
    # از "media_edit_msg" برای هماهنگی با هندلر handle_time در bot.py استفاده شده است.
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


# این تابع در callback_query اصلی در bot.py برای دکمه "cut_audio_now" فراخوانی می‌شود
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

    expected_input_filename = f"{user_id}_input_audio.mp3"
    temp_output = f"{user_id}_cut_audio.mp3"
    downloaded_file_path = None

    try:
        # --- دانلود فایل صوتی ---
        audio_msg = await app.get_messages(chat_id, state["audio_msg_id"])
        
        processing_msg = await callback_query.message.reply("🔄 در حال دانلود فایل صوتی...")
        downloaded_file_path = await audio_msg.download(expected_input_filename)
        
        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            raise Exception("دانلود فایل صوتی ناموفق بود یا فایل ورودی پیدا نشد.")

        start = state["start_time"]
        end = state["end_time"]

        await processing_msg.edit_text("⚡️ در حال برش سریع (کپی جریان)...")

        # --- برش با FFmpeg: استفاده از Stream Copy ---
        (
            ffmpeg
            .input(downloaded_file_path, ss=start) 
            .output(temp_output, to=end, c="copy", loglevel="error")
            .run(overwrite_output=True)
        )

        # --- آپلود و ارسال نتیجه ---
        await processing_msg.edit_text("📤 در حال ارسال فایل صوتی برش‌خورده...")
        await app.send_audio(chat_id, temp_output) # استفاده از send_audio
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
