import os
import subprocess
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from io import BytesIO

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'

bot = Client("compressor_bot_stream", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def parse_time_to_sec(time_str):
    try:
        h, m, s = time_str.strip().split(":")
        return float(h) * 3600 + float(m) * 60 + float(s)
    except ValueError:
        return 0.0

def progress_bar(percent):
    filled = int(percent / 5)
    return f"[{'█' * filled}{'░' * (20 - filled)}] {int(percent)}%"

async def compress_stream(input_stream, output_buffer, duration, message: Message):
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", "-",
        "-vcodec", "libx264", "-crf", "28",
        "-preset", "slow", "-acodec", "aac", "-b:a", "128k",
        "-f", "mp4", "-",  # Output to stdout
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def feed_input():
        async for chunk in input_stream:
            if process.stdin and not process.stdin.is_closing:
                try:
                    process.stdin.write(chunk)
                except BrokenPipeError:
                    print("Broken pipe error while feeding input to ffmpeg.")
                    break
        if process.stdin and not process.stdin.is_closing:
            try:
                process.stdin.close()
            except BrokenPipeError:
                print("Broken pipe error while closing stdin of ffmpeg.")

    async def read_output():
        while True:
            chunk = await process.stdout.read(1024)
            if not chunk:
                break
            output_buffer.write(chunk)

    async def monitor_progress():
        while True:
            stderr_line = await process.stderr.readline()
            if not stderr_line:
                break
            line = stderr_line.decode("utf-8").strip()
            if "out_time=" in line and duration > 0:
                out_time_str = line.split('=')[1]
                current_time = parse_time_to_sec(out_time_str)
                percent = min(current_time / duration * 100, 100)
                bar = progress_bar(percent)
                try:
                    await message.edit_text(f"در حال کاهش حجم...\n{bar}")
                except:
                    pass

    await asyncio.gather(feed_input(), read_output(), monitor_progress())
    await process.wait()

@bot.on_message(filters.video)
async def handle_video(client, message):
    info_msg = await message.reply_text("در حال دریافت اطلاعات ویدیو...")

    file_id = message.video.file_id
    duration = message.video.duration if message.video.duration else 0

    output_buffer = BytesIO()

    await info_msg.edit_text("در حال شروع فشرده‌سازی...")

    start_time = time.time()
    async def stream_video():
        async for chunk in client.stream_media(file_id):
            yield chunk

    await compress_stream(stream_video(), output_buffer, float(duration), info_msg)

    output_buffer.seek(0)
    upload_start_time = time.time()

    await info_msg.edit_text("فشرده‌سازی کامل شد. در حال آپلود...")

    try:
        await message.reply_video(
            output_buffer,
            caption="ویدیو با موفقیت فشرده شد!",
            progress=upload_progress,
            progress_args=(info_msg, upload_start_time, output_buffer.getbuffer().nbytes)
        )
    except Exception as e:
        await message.reply_text(f"خطا در هنگام آپلود: {e}")
    finally:
        await info_msg.delete()

def progress_bar_simple(current, total):
    if total == 0:
        return "[░░░░░░░░░░░░░░░░░░░░] 0%"
    percent = int(current * 100 / total)
    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    return f"[{bar}] {percent}%"

async def upload_progress(current, total, message, start, file_size):
    elapsed = int(time.time() - start)
    percent = int(current * 100 / file_size) if file_size > 0 else 0
    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    text = f"در حال آپلود فایل...\n{progress_bar_simple(current, total)}\nزمان سپری‌شده: {elapsed}s"
    try:
        await message.edit_text(text)
    except:
        pass

bot.run()
