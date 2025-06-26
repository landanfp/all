from pyrogram import Client, filters
from pyrogram.types import Message
from loader import app
import asyncio
import time
import os
from helper.ffmpeg import add_hardsub
from helper.progress import progress_bar

# ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه

@app.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        user_id = message.from_user.id
        now = time.time()

        processing_msg = await message.reply_text("⏳ در حال دانلود زیرنویس...")
        srt_path = await client.download_media(message.document.file_id, progress=progress_bar, progress_args=("دانلود زیرنویس", processing_msg))

        # ذخیره اطلاعات فایل srt
        user_sessions[user_id] = {
            'srt_path': srt_path,
            'timestamp': now
        }

        await processing_msg.edit_text("✅ فایل زیرنویس دریافت شد. حالا لطفاً ویدیوی خود را ارسال کنید.")

        # شروع شمارش معکوس برای انقضای سشن
        asyncio.create_task(expire_session(user_id))

async def expire_session(user_id):
    await asyncio.sleep(SESSION_TIMEOUT)
    session = user_sessions.get(user_id)
    if session and (time.time() - session['timestamp'] >= SESSION_TIMEOUT):
        try:
            if os.path.exists(session['srt_path']):
                os.remove(session['srt_path'])
        except Exception as e:
            print(f"خطا در پاکسازی فایل زیرنویس: {e}")
        user_sessions.pop(user_id, None)

@app.on_message(filters.video & filters.private)
async def handle_video_file(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_sessions or 'srt_path' not in user_sessions[user_id]:
        await message.reply_text("⚠️ ابتدا باید فایل زیرنویس (.srt) را ارسال کنید.")
        return

    # پیام "در حال دانلود"
    processing_msg = await message.reply_text("⏳ در حال دانلود ویدیو...")

    try:
        srt_path = user_sessions[user_id]['srt_path']
        video_path = await client.download_media(message, progress=progress_bar, progress_args=("دانلود ویدیو", processing_msg))

        output_path = f"hardsub_{user_id}.mp4"

        # اجرای ffmpeg برای چسباندن زیرنویس
        await processing_msg.edit_text("⏳ در حال چسباندن زیرنویس...")
        await add_hardsub(video_path, srt_path, output_path, processing_msg)

        # ارسال ویدیو نهایی
        await processing_msg.edit_text("⏳ در حال آپلود ویدیو...")
        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!",
            progress=progress_bar,
            progress_args=("آپلود ویدیو", processing_msg)
        )

        # حذف پیام "در حال آپلود"
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
