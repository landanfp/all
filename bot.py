from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import time
import math
import subprocess
from flask import Flask
from threading import Thread

# اطلاعات ربات
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# وب‌سرور ساده برای health check در Koyeb
flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# تبدیل حجم
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# نوار پیشرفت
async def progress_bar(current, total, status_message, action, start):
    now = time.time()
    diff = now - start if now - start != 0 else 0.001
    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff)
    eta = round((total - current) / speed) if speed != 0 else 0
    bar_length = 15
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    text = f"""
{action}
[{bar}] {percentage:.2f}%
• حجم: {convert_size(current)} / {convert_size(total)}
• سرعت: {convert_size(speed)}/s
• زمان سپری‌شده: {elapsed_time}s
• زمان باقی‌مانده: {eta}s
"""
    try:
        await status_message.edit(text)
    except:
        pass

@app.on_message(filters.video & filters.private)
async def add_watermark(client: Client, message: Message):
    status = await message.reply("در حال دانلود و افزودن واترمارک...")
    temp_input_path, temp_output_path = "", ""
    try:
        start_time = time.time()

        # دانلود فایل به دیسک (نه به رم)
        temp_input_path = await message.download(
            in_memory=False,  # دانلود فایل به دیسک
            progress=progress_bar,
            progress_args=(status, "در حال دانلود...", start_time)
        )
        if not temp_input_path or not os.path.exists(temp_input_path):
            return await status.edit("خطا در دانلود فایل.")

        # تولید فایل خروجی در دیسک
        temp_output_path = "wm_" + os.path.basename(temp_input_path)
        command = [
            "ffmpeg", "-i", temp_input_path,
            "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,20)'",
            "-codec:a", "copy", temp_output_path
        ]
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()

        if not os.path.exists(temp_output_path):
            await status.edit(f"خطا در پردازش ویدیو:\n{stderr.decode()}")
            return

        # اطمینان از وجود فایل پس از پردازش
        if not os.path.exists(temp_output_path):
            return await status.edit("فایل خروجی وجود ندارد.")

        # آپلود فایل واترمارک‌دار
        await status.edit("در حال آپلود فایل واترمارک‌دار...")
        try:
            await message.reply_video(
                video=temp_output_path,
                caption="✅ ویدیو با واترمارک ارسال شد.",
                progress=progress_bar,
                progress_args=(status, "در حال آپلود...", time.time())
            )
        except Exception as e:
            await status.edit(f"خطا در آپلود فایل: {str(e)}")

        await status.delete()

    except Exception as e:
        await status.edit(f"خطا در پردازش: {e}")

    finally:
        # حذف فایل‌های موقت
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)

if __name__ == "__main__":
    # اجرای Flask در یک Thread جداگانه
    Thread(target=run_flask).start()
    
    # اجرای ربات
    app.run()
