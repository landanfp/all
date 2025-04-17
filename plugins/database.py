import os
import time
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment
from pyrogram import Client
from pyrogram.types import Message

def time_to_millis(t: str):
    h, m, s = map(int, t.split(":"))
    return (h * 3600 + m * 60 + s) * 1000

async def progress_bar(current, total, message, start_time, description="در حال انجام عملیات"):
    now = time.time()
    elapsed = now - start_time
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    percentage = current * 100 / total
    bar_length = 20
    filled_length = int(bar_length * current // total)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)

    current_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)
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
        await message.edit_text(text)
    except:
        pass

async def download_and_trim_upload(client: Client, message: Message, file_id: str, start: str, end: str):
    download_path = f"downloads/{file_id}.mp4"
    output_path = f"downloads/trimmed_{file_id}.mp4"
    os.makedirs("downloads", exist_ok=True)
    start_time = time.time()
    await client.download_media(file_id, file_name=download_path, progress=progress_bar, progress_args=(message, start_time, "در حال دانلود ویدیو"))
    try:
        video = VideoFileClip(download_path).subclip(start, end)
        video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        upload_start = time.time()
        await message.reply_video(output_path, caption="ویدیو برش‌خورده آماده است!", progress=progress_bar, progress_args=(message, upload_start, "در حال آپلود ویدیو"))
    except Exception as e:
        await message.reply(f"خطا در برش ویدیو: {e}")
    finally:
        if os.path.exists(download_path): os.remove(download_path)
        if os.path.exists(output_path): os.remove(output_path)

async def download_and_trim_audio_upload(client: Client, message: Message, file_id: str, start: str, end: str):
    download_path = f"downloads/{file_id}.mp3"
    output_path = f"downloads/trimmed_{file_id}.mp3"
    os.makedirs("downloads", exist_ok=True)
    start_time = time.time()
    await client.download_media(file_id, file_name=download_path, progress=progress_bar, progress_args=(message, start_time, "در حال دانلود صدا"))
    try:
        audio = AudioSegment.from_file(download_path)
        start_ms = time_to_millis(start)
        end_ms = time_to_millis(end)
        trimmed = audio[start_ms:end_ms]
        trimmed.export(output_path, format="mp3")
        upload_start = time.time()
        await message.reply_audio(output_path, caption="فایل صوتی برش‌خورده آماده است!", progress=progress_bar, progress_args=(message, upload_start, "در حال آپلود صدا"))
    except Exception as e:
        await message.reply(f"خطا در برش فایل صوتی: {e}")
    finally:
        if os.path.exists(download_path): os.remove(download_path)
        if os.path.exists(output_path): os.remove(output_path)
