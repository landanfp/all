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

async def read_ffmpeg_output(stdout_stream, progress_data):
    """تسک: خروجی FFmpeg را از stdout می‌خواند و داده‌ها را ذخیره می‌کند."""
    while True:
        line = await stdout_stream.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8')
        
        if '=' in line_str:
            key, value = line_str.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if key == 'out_time_ms':
                try:
                    ms = int(value)
                    seconds = ms // 1000000
                    minutes = seconds // 60
                    hours = minutes // 60
                    seconds = seconds % 60
                    
                    progress_data['time'] = f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}.{ms % 1000000 // 10000:02}"
                except ValueError:
                    pass
            elif key == 'speed':
                progress_data['speed'] = value

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

        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path, '-vf', f'subtitles={srt_path}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k',
            '-y', output_path, '-nostats', '-progress', 'pipe:1'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        
        progress_data = {'time': "00:00:00.00", 'speed': "0.00x"}
        
        reader_task = asyncio.create_task(read_ffmpeg_output(process.stdout, progress_data))
        updater_task = asyncio.create_task(update_message_periodically(processing_msg, progress_data))
        
        await process.wait()
        
        reader_task.cancel()
        updater_task.cancel()
        
        try:
            await asyncio.gather(reader_task, updater_task)
        except asyncio.CancelledError:
            pass
            
        await asyncio.sleep(1)

        await processing_msg.edit_text("⬆️ در حال آپلود...")

        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!"
        )

        await processing_msg.delete()

    except Exception as e:
        await processing_msg.edit_text(f"❌ خطایی رخ داد: {type(e).__name__}\n\nجزئیات خطا:\n`{e}`")
        print(f"An error occurred: {type(e).__name__} - {e}")

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
