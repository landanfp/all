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
    
    # اطمینان از اینکه کاربر در حال برش صداست
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

    # به‌روزرسانی وضعیت کاربر برای برش صدا
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

    # نام فایل ورودی، پسوند خود را از Pyrogram می‌گیرد
    expected_input_filename = f"{user_id}_input_audio" 
    # نام فایل‌های خروجی موقت
    output_filename_mp3 = f"{user_id}_cut_audio_re.mp3"
    output_filename_m4a = f"{user_id}_cut_audio.m4a"
    final_output_filename = None
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
        
        # <<< کد جدید: تعیین نوع فایل و حالت برش >>>
        _, file_extension = os.path.splitext(downloaded_file_path)
        is_mp3 = file_extension.lower() == '.mp3'
        
        if is_mp3:
            # حالت MP3: رمزگذاری مجدد (Re-encode)
            codec = "libmp3lame"
            cut_mode = "رمزگذاری مجدد MP3 (کندتر اما دقیق)"
            final_output_filename = output_filename_mp3
        else:
            # حالت M4A و بقیه: کپی سریع (Copy Stream)
            codec = "copy"
            cut_mode = "کپی سریع جریان (فوق سریع)"
            final_output_filename = output_filename_m4a

        print(f"DEBUG: Trimming audio file: {downloaded_file_path} from {start} to {end} using {cut_mode}.")
        
        await processing_msg.edit_text(f"⚡️ در حال برش: {cut_mode}...")

        # --- اجرای FFmpeg ---
        if codec == "copy":
            # برش M4A با کپی مستقیم
            (
                ffmpeg
                .input(downloaded_file_path, ss=start) 
                .output(final_output_filename, to=end, c=codec, map="0:a:0", loglevel="info") 
                .run(overwrite_output=True)
            )
        else:
            # برش MP3 با رمزگذاری مجدد
            (
                ffmpeg
                .input(downloaded_file_path, ss=start) 
                .output(final_output_filename, to=end, acodec=codec, audio_bitrate="192k", loglevel="info") 
                .run(overwrite_output=True)
            )
            
        # --- آپلود و ارسال نتیجه ---
        await processing_msg.edit_text("📤 در حال ارسال فایل صوتی برش‌خورده...")
        await app.send_audio(chat_id, final_output_filename) # استفاده از نام فایل خروجی صحیح
        await processing_msg.edit_text("✅ تمام شد! فایل صوتی برش‌خورده ارسال شد.")

    except ffmpeg.Error as e:
        # بهبود لاگ خطا
        error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است (FFmpeg خروجی خطا نداد). احتمالاً مشکل در پارامترهای زمان یا فایل ورودی آسیب دیده است."
        await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`\n\n**توجه:** اگر فایل MP3 بود، به دلیل رمزگذاری مجدد نباید خطا می‌داد.")
    except Exception as e:
        await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: دانلود یا پردازش با مشکل مواجه شد. `{e}`")
    finally:
        # --- پاکسازی فایل‌ها و وضعیت ---
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
        
        # پاکسازی هر دو فایل خروجی موقت احتمالی
        if os.path.exists(output_filename_m4a):
            os.remove(output_filename_m4a)
        if os.path.exists(output_filename_mp3):
            os.remove(output_filename_mp3)

        if user_id in user_state:
            del user_state[user_id]
