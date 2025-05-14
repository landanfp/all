import os
import subprocess
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message



bot = Client("compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def get_duration(file_path):
    """گرفتن طول ویدیو به ثانیه"""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout.decode().strip())

def parse_time_to_sec(time_str):
    """تبدیل زمان 00:01:23.45 به ثانیه"""
    h, m, s = time_str.strip().split(":")
    return float(h) * 3600 + float(m) * 60 + float(s)

def progress_bar(percent):
    filled = int(percent / 5)
    return f"[{'█' * filled}{'░' * (20 - filled)}] {int(percent)}%"

async def compress_with_progress(input_file, output_file, duration, message: Message):
    process = subprocess.Popen([
        "ffmpeg", "-i", input_file,
        "-vcodec", "libx264", "-crf", "28",
        "-preset", "slow", "-acodec", "aac", "-b:a", "128k",
        "-progress", "pipe:1", "-nostats", output_file
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    percent = 0
    while True:
        line = process.stdout.readline()
        if not line:
            break

        line = line.decode("utf-8").strip()
        if "out_time=" in line:
            out_time_str = line.split('=')[1]
            current_time = parse_time_to_sec(out_time_str)
            percent = min(current_time / duration * 100, 100)
            bar = progress_bar(percent)
            try:
                await message.edit_text(f"در حال کاهش حجم...\n{bar}")
            except:
                pass

    process.wait()

@bot.on_message(filters.video)
async def handle_video(client, message):
    info_msg = await message.reply_text("در حال دریافت ویدیو...")

    start_time = time.time()
    file_path = await message.download(progress=download_progress, progress_args=(info_msg, start_time))

    await info_msg.edit_text("در حال تحلیل ویدیو...")

    duration = get_duration(file_path)
    output_path = "compressed_" + os.path.basename(file_path)

    await compress_with_progress(file_path, output_path, duration, info_msg)

    await info_msg.edit_text("کاهش حجم کامل شد. در حال آپلود...")

    start_upload = time.time()
    await message.reply_video(
        output_path,
        caption="ویدیو با موفقیت فشرده شد!",
        progress=upload_progress,
        progress_args=(info_msg, start_upload)
    )

    await info_msg.delete()
    os.remove(file_path)
    os.remove(output_path)

# توابع پیشرفت برای دانلود و آپلود
def progress_bar_simple(current, total):
    percent = int(current * 100 / total)
    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    return f"[{bar}] {percent}%"

async def download_progress(current, total, message, start):
    elapsed = int(time.time() - start)
    text = f"در حال دریافت فایل...\n{progress_bar_simple(current, total)}\nزمان سپری‌شده: {elapsed}s"
    try:
        await message.edit_text(text)
    except:
        pass

async def upload_progress(current, total, message, start):
    elapsed = int(time.time() - start)
    text = f"در حال آپلود فایل...\n{progress_bar_simple(current, total)}\nزمان سپری‌شده: {elapsed}s"
    try:
        await message.edit_text(text)
    except:
        pass

bot.run()
