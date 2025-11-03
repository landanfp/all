import os
import ffmpeg
import asyncio # نیاز است!
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

    # این بخش مدت زمان کلی فایل را نمایش می‌دهد و درست است
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

    expected_input_filename = f"{user_id}_input_audio"
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
        
        # --- محاسبه Duration برای برش دقیق ---
        start_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], start.split(':')))
        end_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], end.split(':')))

        duration_seconds = end_seconds - start_seconds
        duration_hms = seconds_to_hms(duration_seconds)
        # ------------------------------------
        
        # --- تشخیص نوع فایل بر اساس MIME Type تلگرام ---
        mime_type = audio_msg.audio.mime_type.lower() if audio_msg.audio and audio_msg.audio.mime_type else ""
        is_mp3 = 'mpeg' in mime_type or 'mp3' in mime_type
        
        if is_mp3:
            codec = "libmp3lame"
            cut_mode = "رمزگذاری مجدد MP3 (کندتر و دقیق‌تر)"
            final_output_filename = output_filename_mp3
        else:
            codec = "copy"
            cut_mode = "کپی سریع جریان (M4A/AAC)"
            final_output_filename = output_filename_m4a

        print(f"DEBUG: Trimming audio file: {downloaded_file_path} from {start} for duration {duration_hms} using {cut_mode}.")
        
        await processing_msg.edit_text(f"⚡️ در حال برش: {cut_mode}...")

        # --- تعریف دستور FFmpeg ---
        ffmpeg_process = None
        if codec == "copy":
            # برش M4A (یا فرمت‌های مشابه) با کپی مستقیم
            ffmpeg_process = (
                ffmpeg
                .input(downloaded_file_path, ss=start) 
                # استفاده از t=Duration برای دقت برش 
                .output(final_output_filename, t=duration_hms, c=codec, map="0:a:0", f="ipod", loglevel="info") 
            )
        else:
            # برش MP3 با رمزگذاری مجدد
            ffmpeg_process = (
                ffmpeg
                .input(downloaded_file_path, ss=start) 
                # استفاده از t=Duration و پارامتر map="0:a:0" برای رفع مشکل قبلی
                .output(final_output_filename, t=duration_hms, acodec=codec, audio_bitrate="192k", map="0:a:0", f="mp3", loglevel="info") 
            )
            
        # --- اجرای FFmpeg (به صورت غیر-بلاک) ---
        await asyncio.to_thread(ffmpeg_process.run, overwrite_output=True)
            
        # --- آپلود و ارسال نتیجه ---
        await processing_msg.edit_text("📤 در حال ارسال فایل صوتی برش‌خورده...")
        await app.send_audio(chat_id, final_output_filename) 
        await processing_msg.edit_text("✅ تمام شد! فایل صوتی برش‌خورده ارسال شد.")

    except ffmpeg.Error as e:
        error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است."
        print(f"--- FFmpeg Error Details ---\n{error_details}\n-------------------------")
        await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`")
    except Exception as e:
        print(f"--- General Error ---: {e}")
        await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: `{e}`")
    finally:
        # --- پاکسازی فایل‌ها و وضعیت ---
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            os.remove(downloaded_file_path)
        
        if os.path.exists(output_filename_m4a):
            os.remove(output_filename_m4a)
        if os.path.exists(output_filename_mp3):
            os.remove(output_filename_mp3)

        if user_id in user_state:
            del user_state[user_id]
