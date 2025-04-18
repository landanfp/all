# ---- کتابخانه‌های مورد نیاز ----
from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import os
import math
import time
from flask import Flask
from threading import Thread

# ---- اطلاعات ربات ----
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'


# ---- ساخت کلاینت Pyrogram ----
app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---- health check برای Koyeb ----
flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "OK", 200

# ---- اجرای وب‌سرور در ترد جدا ----
def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# ---- تابع تبدیل حجم بایت به MB و ... ----
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# ---- تابع ساخت نوار پیشرفت برای نمایش وضعیت ----
async def progress_bar(current, total, status_message, action, start):
    now = time.time()
    diff = now - start if now - start != 0 else 1
    percentage = current * 100 / total
    speed = current / diff
    eta = round((total - current) / speed) if speed != 0 else 0
    bar_length = 15
    filled = int(bar_length * percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    text = f"""
{action}
[{bar}] {percentage:.2f}%
• حجم: {convert_size(current)} / {convert_size(total)}
• سرعت: {convert_size(speed)}/s
• زمان باقی‌مانده: {eta}s
"""
    try:
        await status_message.edit(text)
    except:
        pass

# ---- هندل پیام‌های ویدیویی ----
@app.on_message(filters.video & filters.private)
async def stream_watermark(client: Client, message: Message):
    status = await message.reply("در حال دریافت فایل...")

    try:
        # گرفتن حجم فایل برای محاسبه پیشرفت
        file_size = message.video.file_size
        start_time = time.time()

        # دانلود ویدیو به صورت stream در RAM
        stream = await client.download_media(message.video.file_id, in_memory=True)
        if stream is None:
            return await status.edit("خطا در دریافت فایل.")

        await status.edit("در حال افزودن واترمارک به صورت استریم...")

        # ایجاد فایل خروجی موقت
        output_path = f"wm_{int(time.time())}.mp4"

        # اجرای ffmpeg و گرفتن ورودی از stdin (stream)
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", "pipe:0",  # دریافت از stdin
            "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264",  # کدک ویدیو
            "-preset", "ultrafast",  # سرعت بالا برای پردازش
            "-movflags", "+faststart",  # برای سریع شروع‌شدن ویدیو در پلیر
            "-f", "mp4",  # فرمت خروجی
            output_path,  # مسیر خروجی
            stdin=asyncio.subprocess.PIPE
        )

        # خواندن داده‌ها chunk به chunk و فرستادن به ffmpeg
        sent = 0
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            process.stdin.write(chunk)
            await process.stdin.drain()
            sent += len(chunk)
            await progress_bar(sent, file_size, status, "در حال پردازش...", start_time)

        await process.stdin.drain()
        process.stdin.close()
        await process.wait()

        await status.edit("در حال آپلود فایل نهایی...")

        # آپلود فایل نهایی
        await message.reply_video(
            video=output_path,
            caption="✅ واترمارک اضافه شد.",
            progress=progress_bar,
            progress_args=(status, "در حال آپلود...", time.time())
        )

        await status.delete()

        # پاک‌سازی فایل خروجی
        os.remove(output_path)

    except Exception as e:
        await status.edit(f"خطا در عملیات: {e}")

# ---- اجرای Flask و Pyrogram ----
if __name__ == "__main__":
    Thread(target=run_flask).start()
    app.run()
