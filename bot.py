from pyrogram import Client, filters
import subprocess
from io import BytesIO
import time
import os

api_id = '3335796'
api_hash = '138b992a0e672e8346d8439c3f42ea78'
bot_token = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'

app = Client("watermark_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def progress_bar(progress):
    bar_length = 20
    filled = int(bar_length * progress)
    bar = '█' * filled + '─' * (bar_length - filled)
    return f"[{bar}] {int(progress * 100)}%"

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply("سلام! ویدیوی خودتو بفرست تا واترمارک متحرک روش قرار بگیره.")

@app.on_message(filters.video)
async def add_watermark(client, message):
    status = await message.reply("در حال دانلود و افزودن واترمارک متحرک...")

    # ایجاد یک مسیر موقت برای ذخیره ویدیو
    temp_file_path = f"temp_{message.video.file_id}.mp4"
    await message.download(temp_file_path)  # ذخیره ویدیو به صورت محلی

    process = subprocess.Popen(
        [
            "ffmpeg", "-i", temp_file_path,
            "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=24:y=h-line_h-20:x=mod(100*t\\,w+text_w)",
            "-c:v", "libx264", "-preset", "fast", "-f", "mp4", "pipe:1"
        ],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # دریافت داده‌های خروجی FFmpeg
    output_data, err = process.communicate()
    
    # در صورتی که خطایی وجود داشته باشد، نمایش می‌دهیم
    if process.returncode != 0:
        await status.edit(f"خطا در پردازش ویدیو: {err.decode()}")
        return

    output_stream = BytesIO(output_data)
    output_stream.name = "watermarked.mp4"
    output_stream.seek(0)

    total_size = len(output_data)
    chunk_size = 1024 * 64
    uploaded = 0
    start_time = time.time()

    async def generator():
        nonlocal uploaded
        while True:
            chunk = output_stream.read(chunk_size)
            if not chunk:
                break
            uploaded += len(chunk)
            yield chunk

            elapsed = time.time() - start_time
            speed = uploaded / elapsed
            eta = (total_size - uploaded) / speed if speed > 0 else 0
            progress = uploaded / total_size
            bar = progress_bar(progress)
            msg = (
                f"در حال آپلود...\n"
                f"{bar}\n"
                f"حجم: {human_readable_size(uploaded)} / {human_readable_size(total_size)}\n"
                f"سرعت: {human_readable_size(speed)}/s\n"
                f"زمان باقی‌مانده: {int(eta)} ثانیه"
            )
            try:
                await status.edit(msg)
            except:
                pass

    # ارسال ویدیو به کاربر با استفاده از generator
    await message.reply_video(
        video=generator(),
        caption="ویدیو با واترمارک متحرک آماده است.",
        file_name="watermarked.mp4"
    )

    await status.delete()

    # حذف فایل موقت پس از پردازش
    os.remove(temp_file_path)

app.run()
