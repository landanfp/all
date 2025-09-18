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

    # ارسال اولین پیام وضعیت
    processing_msg = await message.reply_text("⏳ در حال دانلود فایل‌ها...")

    try:
        srt_file_id = user_sessions[user_id]['srt_file_id']

        # دانلود فایل‌ها
        srt_path = await client.download_media(srt_file_id)
        video_path = await client.download_media(message)

        output_path = f"hardsub_{user_id}.mp4"

        # به‌روزرسانی پیام برای شروع هاردساب
        await processing_msg.edit_text("⏳ در حال هاردساب... لطفاً صبر کنید.")

        # اجرای FFmpeg به صورت غیرهمزمان و خواندن خروجی آن
        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path, '-vf', f'subtitles={srt_path}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k',
            '-y', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        last_update_time = time.time()
        last_time_str = "00:00:00.00"
        last_speed_str = "0.00x"
        last_message_text = ""
        
        while process.returncode is None: # حلقه تا زمانی که فرآیند در حال اجراست
            try:
                # تلاش برای خواندن یک خط جدید با timeout کوتاه
                line = await asyncio.wait_for(process.stderr.readline(), timeout=0.1)
                
                if line:
                    line_str = line.decode('utf-8')
                    
                    # جستجو برای زمان و سرعت در خروجی FFmpeg
                    time_match = re.search(r'time=(\d{2}:\d{2}:\d{2}.\d{2})', line_str)
                    speed_match = re.search(r'speed=(\d+\.?\d*x)', line_str)
                    
                    if time_match and speed_match:
                        last_time_str = time_match.group(1)
                        last_speed_str = speed_match.group(1)

            except asyncio.TimeoutError:
                # اگر در 0.1 ثانیه خط جدیدی نبود، به حلقه ادامه بده
                pass
            
            except ValueError:
                # در صورت خطای احتمالی، از حلقه خارج شو
                break

            # اگر ۳ ثانیه از آخرین به‌روزرسانی گذشته، پیام را ویرایش کن
            if time.time() - last_update_time >= 3:
                new_message_text = (
                    f"⏳ در حال هاردساب... \n"
                    f"مدت زمان هاردساب شده: **{last_time_str}** \n"
                    f"سرعت: **{last_speed_str}**"
                )
                
                if new_message_text != last_message_text:
                    await processing_msg.edit_text(new_message_text)
                    last_message_text = new_message_text
                
                last_update_time = time.time()
                
        # منتظر ماندن تا فرآیند FFmpeg به پایان برسد
        await process.wait()

        # اضافه کردن یک تأخیر کوتاه برای اطمینان از نهایی شدن فایل
        await asyncio.sleep(1)

        # پیام "در حال آپلود..." را نمایش بده
        await processing_msg.edit_text("⬆️ در حال آپلود...")

        # ارسال ویدیو نهایی
        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!"
        )

        # حذف پیام وضعیت
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
