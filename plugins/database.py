import os
import time
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment
from pyrogram import Client
from pyrogram.types import Message

def time_to_seconds(t: str):
    """تبدیل زمان (hh:mm:ss) به ثانیه."""
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s

async def progress_bar(current, total, message, start_time, description="در حال انجام عملیات"):
    """نمایش پروگرس بار با دقت و هندل کردن تقسیم بر صفر."""
    now = time.time()
    elapsed = now - start_time
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    # دیباگ کردن مقادیر برای بررسی عملکرد
    print(f"current: {current}, total: {total}, elapsed: {elapsed}, speed: {speed}, eta: {eta}")  # برای دیباگ

    # تقسیم بر صفر جلوگیری شود
    if total == 0:
        percentage = 0
    else:
        percentage = current * 100 / total

    bar_length = 20
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = "█" * filled_length + "-" * (bar_length - filled_length)

    current_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024) if total > 0 else 0
    speed_mb = speed / (1024 * 1024)

    text = (
        f"{description}...\n"
        f"[{bar}] {percentage:.2f}%\n"
        f"حجم انجام شده: {current_mb:.2f} MB\n"
        f"حجم کل فایل: {total_mb:.2f} MB\n"
        f"سرعت: {speed_mb:.2f} MB/s\n"
        f"تایم باقی مانده: {round(eta)} ثانیه"
    )

    try:
        # ویرایش پیام فقط در صورت تغییر محتوا
        if message.text != text:
            await message.edit_text(text)
    except:
        pass

async def download_and_trim_upload(client: Client, message: Message, file_id: str, start: str, end: str):
    """دانلود و برش ویدیو با دقت بیشتر در زمان برش."""
    download_path = f"downloads/{file_id}.mp4"
    output_path = f"downloads/trimmed_{file_id}.mp4"
    os.makedirs("downloads", exist_ok=True)
    start_time = time.time()

    await client.download_media(
        file_id,
        file_name=download_path,
        progress=progress_bar,
        progress_args=(message, start_time, "در حال دانلود ویدیو")
    )

    try:
        video = VideoFileClip(download_path)

        # تبدیل زمان شروع و پایان به ثانیه برای دقت بیشتر
        start_sec = time_to_seconds(start)
        end_sec = time_to_seconds(end)

        # برش ویدیو
        trimmed = video.subclip(start_sec, end_sec)
        trimmed.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        upload_start = time.time()
        await message.reply_video(
            output_path,
            caption="ویدیو برش‌خورده آماده است!",
            progress=progress_bar,
            progress_args=(message, upload_start, "در حال آپلود ویدیو")
        )
    except Exception as e:
        await message.reply(f"خطا در برش ویدیو: {e}")
    finally:
        if os.path.exists(download_path): os.remove(download_path)
        if os.path.exists(output_path): os.remove(output_path)

async def download_and_trim_audio_upload(client: Client, message: Message, file_id: str, start: str, end: str):
    """دانلود و برش فایل صوتی با دقت بیشتر در زمان برش."""
    download_path = f"downloads/{file_id}.mp3"
    output_path = f"downloads/trimmed_{file_id}.mp3"
    os.makedirs("downloads", exist_ok=True)
    start_time = time.time()

    # اصلاح پروگرس بار
    await client.download_media(
        file_id,
        file_name=download_path,
        progress=progress_bar,
        progress_args=(message, start_time, "در حال دانلود صدا")
    )

    try:
        audio = AudioSegment.from_file(download_path)

        # تبدیل زمان شروع و پایان به میلی‌ثانیه برای دقت بیشتر
        start_ms = time_to_seconds(start) * 1000
        end_ms = time_to_seconds(end) * 1000

        # برش فایل صوتی
        trimmed = audio[start_ms:end_ms]
        trimmed.export(output_path, format="mp3")

        upload_start = time.time()

        # اصلاح پروگرس بار برای آپلود
        await message.reply_audio(
            output_path,
            caption="فایل صوتی برش‌خورده آماده است!",
            progress=progress_bar,
            progress_args=(message, upload_start, "در حال آپلود صدا")
        )
    except Exception as e:
        await message.reply(f"خطا در برش فایل صوتی: {e}")
    finally:
        if os.path.exists(download_path): os.remove(download_path)
        if os.path.exists(output_path): os.remove(output_path)
