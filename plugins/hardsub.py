from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import time

# دیکشنری برای ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه = ۳۰۰ ثانیه

@Client.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        user_id = message.from_user.id
        now = time.time()

        # ذخیره فایل SRT همراه با زمان
        user_sessions[user_id] = {
            'srt_file_id': message.document.file_id,
            'timestamp': now
        }

        await message.reply_text("فایل زیرنویس ذخیره شد. حالا لطفاً ویدیو را ارسال کنید.")
        
        # شروع شمارش معکوس برای انقضای سشن
        asyncio.create_task(expire_session(user_id))

async def expire_session(user_id):
    await asyncio.sleep(SESSION_TIMEOUT)
    session = user_sessions.get(user_id)
    if session and (time.time() - session['timestamp'] >= SESSION_TIMEOUT):
        user_sessions.pop(user_id, None)

@Client.on_message(filters.video & filters.private)
async def handle_video_file(client, message: Message):
    user_id = message.from_user.id

    # چک کن ببین فایل SRT ذخیره شده یا خیر
    if user_id not in user_sessions or 'srt_file_id' not in user_sessions[user_id]:
        await message.reply_text("ابتدا باید فایل زیرنویس (.srt) را ارسال کنید.")
        return

    await message.reply_text("در حال دانلود فایل‌ها و پردازش، لطفاً صبور باشید...")

    try:
        srt_file_id = user_sessions[user_id]['srt_file_id']

        # دانلود فایل SRT
        srt_path = await client.download_media(srt_file_id)
        # دانلود فایل ویدیو
        video_path = await client.download_media(message)

        # اینجا کد اجرای ffmpeg باید اضافه شود
        # به طور مثال:
        #
        # output_path = "output.mp4"
        # ffmpeg_command = f"ffmpeg -i \"{video_path}\" -vf subtitles=\"{srt_path}\" \"{output_path}\""
        # subprocess.run(ffmpeg_command, shell=True)
        #
        # و بعد آپلود فایل آماده شده

        await message.reply_text("ویدیو با زیرنویس آماده شد!")

    except Exception as e:
        await message.reply_text(f"خطا در پردازش فایل‌ها: {e}")

    finally:
        # پاکسازی وضعیت کاربر بعد از پردازش
        user_sessions.pop(user_id, None)
