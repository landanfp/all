from pyrogram import Client, filters
from pyrogram.types import Message
from loader import app
import asyncio
import time
import subprocess
import os

# ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه

@app.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
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

    # اول پیام "در حال دانلود" بده
    processing_msg = await message.reply_text("⏳ در حال دانلود فایل‌ها و پردازش... لطفاً صبر کنید.")

    try:
        srt_file_id = user_sessions[user_id]['srt_file_id']

        # دانلود فایل‌ها
        srt_path = await client.download_media(srt_file_id)
        video_path = await client.download_media(message)

        output_path = f"hardsub_{user_id}.mp4"

        # اجرای ffmpeg برای چسباندن زیرنویس
        ffmpeg_cmd = f'ffmpeg -i "{video_path}" -vf subtitles="{srt_path}" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k "{output_path}" -y'
        subprocess.run(ffmpeg_cmd, shell=True)

        # ارسال ویدیو نهایی
        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!"
        )

        # حذف پیام "در حال دانلود"
        await processing_msg.delete()

    except Exception as e:
        await processing_msg.edit_text(f"❌ خطایی رخ داد: {e}")

    finally:
        # پاکسازی فایل‌ها
        user_sessions.pop(user_id, None)

        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(srt_path):
                os.remove(srt_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            print(f"خطا در پاکسازی فایل‌ها: {e}")
