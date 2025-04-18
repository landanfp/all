from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import time
import math
import subprocess

# توکن و APIهای ربات
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'


app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


async def progress_bar(current, total, status_message, action, start):
    now = time.time()
    diff = now - start
    if diff == 0:
        diff = 0.001

    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff)
    eta = round((total - current) / speed)

    bar_length = 15
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    current_size = convert_size(current)
    total_size = convert_size(total)
    speed_str = convert_size(speed) + "/s"

    text = f"""
{action}
[{bar}] {percentage:.2f}%
• حجم: {current_size} / {total_size}
• سرعت: {speed_str}
• زمان سپری‌شده: {elapsed_time}s
• زمان باقی‌مانده: {eta}s
"""
    try:
        await status_message.edit(text)
    except:
        pass


@app.on_message(filters.video & filters.private)
async def add_watermark(client: Client, message: Message):
    status = await message.reply("در حال دانلود و افزودن واترمارک متحرک...")

    try:
        start_time = time.time()
        temp_input_path = await message.download(progress=progress_bar, progress_args=(status, "در حال دانلود...", start_time))

        if not temp_input_path or not os.path.exists(temp_input_path):
            return await status.edit("خطا در دانلود فایل.")

        temp_output_path = "wm_" + os.path.basename(temp_input_path)

        # واترمارک متنی وسط ویدیو با FFmpeg
        command = [
            "ffmpeg", "-i", temp_input_path,
            "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,20)'",
            "-codec:a", "copy", temp_output_path
        ]
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()

        if not os.path.exists(temp_output_path):
            await status.edit(f"خطا در پردازش ویدیو:\n{stderr.decode()}")
            os.remove(temp_input_path)
            return

        await status.edit("در حال آپلود فایل واترمارک‌دار...")
        await message.reply_video(
            video=temp_output_path,
            caption="✅ ویدیو با واترمارک ارسال شد.",
            progress=progress_bar,
            progress_args=(status, "در حال آپلود...", time.time())
        )

        await status.delete()

    except Exception as e:
        await status.edit(f"خطا در پردازش: {e}")

    finally:
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)


app.run()
