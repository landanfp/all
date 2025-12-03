from pyrogram import Client, filters
import os, time, asyncio
import subprocess
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '7136875110:AAGr1EREy_qPMgxVbuE4B0cHGVcwWudOrus'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# -------------------------
# Google Drive Auth
# -------------------------
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # فقط اولین بار برای گرفتن token
drive = GoogleDrive(gauth)

# -------------------------
# Progress Bar Function
# -------------------------
async def progress(current, total, message, start_time):
    now = time.time()
    diff = now - start_time
    if diff == 0: diff = 0.1
    percentage = current * 100 / total
    speed = current / diff
    eta = (total - current) / speed
    bar_length = 20
    filled = int(bar_length * percentage // 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    text = (
        f"🔄 در حال پردازش...\n\n"
        f"{bar} {percentage:.1f}%\n"
        f"{current / 1024 /1024:.2f}MB / {total /1024 /1024:.2f}MB\n"
        f"⚡ سرعت: {speed /1024 /1024:.2f} MB/s\n"
        f"⏳ مانده: {int(eta)} ثانیه"
    )
    try:
        await message.edit(text)
    except: pass

# -------------------------
# دریافت ویدیو
# -------------------------
@app.on_message(filters.video)
async def handle_video(client, message):
    status = await message.reply("⬇️ در حال دانلود ویدیو...")
    start = time.time()
    file_path = await client.download_media(
        message,
        progress=progress,
        progress_args=(status, start)
    )

    await status.edit("🎬 در حال encode ویدیو (720p) ...")
    output_file = "encoded_720p.mp4"
    # FFMPEG encode به 720p
    subprocess.run([
        "ffmpeg", "-i", file_path,
        "-vf", "scale=-2:720",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", output_file
    ])

    await status.edit("⬆️ در حال آپلود به Google Drive...")
    gfile = drive.CreateFile({'title': os.path.basename(output_file)})
    gfile.SetContentFile(output_file)
    gfile.Upload()

    # دریافت لینک shareable
    gfile.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
    link = gfile['alternateLink']

    await status.edit(f"✅ آپلود و encode شد!\n\n🔗 لینک: {link}")

    # پاک کردن فایل‌های محلی
    os.remove(file_path)
    os.remove(output_file)

app.run()
