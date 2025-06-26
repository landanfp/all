from pyrogram import Client, filters
from pyrogram.types import Message
from loader import app
import asyncio
import time
import subprocess
import os
from helper.ffmpeg import add_hardsub_stream

# ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # حداکثر ۲ گیگابایت

@app.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        if message.document.file_size > 10 * 1024 * 1024:  # حداکثر ۱۰ مگابایت برای زیرنویس
            await message.reply_text("⚠️ فایل زیرنویس بیش از حد بزرگ است (حداکثر ۱۰ مگابایت).")
            return

        user_id = message.from_user.id
        now = time.time()

        # ذخیره اطلاعات فایل srt
        user_sessions[user_id] = {
            'srt_file_id': message.document.file_id,
            'timestamp': now
        }

        await message.reply_text("✅ فایل زیرنویس دریافت شد. حالا لطفاً ویدیوی خود را ارسال کنید.")

        # شروع شمارش معکوس برای انقضای سشن
        asyncio.create_task(expire_session(user_id))

async def expire_session(user_id):
    await asyncio.sleep(SESSION_TIMEOUT)
    session = user_sessions.get(user_id)
    if session and (time.time() - session['timestamp'] >= SESSION_TIMEOUT):
        user_sessions.pop(user_id, None)

@app.on_message(filters.video & filters.private)
async def handle_video_file(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_sessions or 'srt_file_id' not in user_sessions[user_id]:
        await message.reply_text("⚠️ ابتدا باید فایل زیرنویس (.srt) را ارسال کنید.")
        return

    if message.video.file_size > MAX_FILE_SIZE:
        await message.reply_text("⚠️ فایل ویدیویی بیش از حد بزرگ است (حداکثر ۲ گیگابایت).")
        return

    # پیام در حال پردازش
    processing_msg = await message.reply_text("⏳ در حال دانلود فایل‌ها و پردازش استریم... لطفاً صبر کنید.")

    try:
        srt_file_id = user_sessions[user_id]['srt_file_id']

        # دانلود فایل‌ها
        srt_path = await client.download_media(srt_file_id, progress=progress_bar, progress_args=("دانلود زیرنویس", processing_msg))
        video_path = await client.download_media(message, progress=progress_bar, progress_args=("دانلود ویدیو", processing_msg))

        # اجرای FFmpeg در حالت استریم و آپلود مستقیم
        await add_hardsub_stream(client, message, video_path, srt_path, processing_msg)

        # حذف پیام "در حال پردازش"
        await processing_msg.delete()

    except Exception as e:
        await processing_msg.edit_text(f"❌ خطایی رخ داد: {str(e)}")

    finally:
        # پاکسازی فایل‌ها
        user_sessions.pop(user_id, None)
        for path in [video_path, srt_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"خطا در پاکسازی فایل‌ها: {e}")
