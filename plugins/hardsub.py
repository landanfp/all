from pyrogram import Client, filters
from pyrogram.types import Message
from loader import app
import asyncio
import time
import subprocess
import os
import re

# ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه

@app.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        user_id = message.from_user.id
        now = time.time()

        user_sessions[user_id] = {
            'srt_file_id': message.document.file_id,
            'timestamp': now
        }

        await message.reply_text("✅ فایل زیرنویس دریافت شد. حالا لطفاً ویدیوی خود را ارسال کنید.")
        asyncio.create_task(expire_session(user_id))

async def expire_session(user_id):
    await asyncio.sleep(SESSION_TIMEOUT)
    session = user_sessions.get(user_id)
    if session and (time.time() - session['timestamp'] >= SESSION_TIMEOUT):
        user_sessions.pop(user_id, None)

async def read_ffmpeg_output(stderr_stream, progress_data):
    """تسک: خروجی FFmpeg را می‌خواند و داده‌ها را ذخیره می‌کند."""
    while True:
        line = await stderr_stream.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8')
        
        # جستجو برای زمان و سرعت
        time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}.\d{2})', line_str)
        speed_match = re.search(r'speed=(\d+\.?\d*x)', line_str)

        if time_match and speed_match:
            progress_data['time'] = time_match.group(1)
            progress_data['speed'] = speed_match.group(1)
            
async def update_message_periodically(processing_msg, progress_data):
    """تسک: پیام را هر ۳ ثانیه با آخرین داده‌ها به‌روزرسانی می‌کند."""
    last_message_text = ""
    while True:
        new_message_text = (
            f"⏳ در حال هاردساب... \n"
            f"مدت زمان هاردساب شده: **{progress_data['time']}** \n"
            f"سرعت: **{progress_data['speed']}**"
        )
        
        if new_message_text != last_message_text:
            try:
                await processing_msg.edit_text(new_message_text)
                last_message_text = new_message_text
            except Exception:
                # اگر پیام حذف شده یا خطای دیگری رخ دهد، تسک را متوقف کن.
                break
        
        await asyncio.sleep(3)
        
@app.on_message(filters.video & filters.private)
async def handle_video_file(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_sessions or 'srt_file_id' not in user_sessions[user_id]:
        await message.reply_text("⚠️ ابتدا باید فایل زیرنویس (.srt) را ارسال کنید.")
        return

    processing_msg = await message.reply_text("⏳ در حال دانلود فایل‌ها...")

    try:
        srt_file_id = user_sessions[user_id]['srt_file_id']
        srt_path = await client.download_media(srt_file_id)
        video_path = await client.download_media(message)
        output_path = f"hardsub_{user_id}.mp4"

        await processing_msg.edit_text("⏳ در حال هاردساب... لطفاً صبر کنید.")

        # دستور FFmpeg با اضافه شدن پرچم -stats برای نمایش مداوم وضعیت
        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path, '-vf', f'subtitles={srt_path}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k',
            '-y', output_path, '-stats'  # این پرچم باعث نمایش مداوم خروجی می‌شود
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # دیکشنری مشترک برای ذخیره اطلاعات پیشرفت
        progress_data = {'time': "00:00:00.00", 'speed': "0.00x"}
        
        # اجرای همزمان دو تسک: خواندن خروجی و به‌روزرسانی پیام
        reader_task = asyncio.create_task(read_ffmpeg_output(process.stderr, progress_data))
        updater_task = asyncio.create_task(update_message_periodically(processing_msg, progress_data))
        
        # منتظر ماندن تا فرآیند FFmpeg به پایان برسد
        await process.wait()
        
        # لغو تسک‌های دیگر پس از اتمام FFmpeg
        reader_task.cancel()
        updater_task.cancel()
        
        try:
            await asyncio.gather(reader_task, updater_task)
        except asyncio.CancelledError:
            pass
            
        # اضافه کردن یک تأخیر کوتاه برای اطمینان از نهایی شدن فایل
        await asyncio.sleep(1)

        await processing_msg.edit_text("⬆️ در حال آپلود...")

        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!"
        )

        await processing_msg.delete()

    except Exception as e:
        await processing_msg.edit_text(f"❌ خطایی رخ داد: {e}")

    finally:
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
