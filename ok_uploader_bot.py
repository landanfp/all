
# فایل: okru_telegram_bot.py

from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import os
import hashlib
import asyncio

# === تنظیمات تلگرام ===
API_ID = 12345678          # <-- API_ID خودت رو بنویس
API_HASH = "your_api_hash" # <-- API_HASH خودت رو بنویس
BOT_TOKEN = "your:bot_token"  # <-- توکن ربات از BotFather

# === تنظیمات OK.ru ===
ACCESS_TOKEN = "-nIMRgTZCuU2hYBWIEn0IlBkvowUXZvgoiD8RaFFtxcOYMinTvspwiNLdXVg4swGgqSW68"
APP_KEY = "COIOIMNGDIHBABABA"
SECRET_KEY = "6B885C7A402C8EC353638176"
SESSION_SECRET_KEY = "4ee5aa4b9721d1797c439344b9a77825"

# فولدر موقت برای دانلود ویدیوها
TEMP_DIR = "downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

app = Client("okru_uploader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def sign_request(params):
    param_str = ''.join([k + '=' + str(v) for k, v in sorted(params.items())])
    sig_str = param_str + SECRET_KEY
    return hashlib.md5(sig_str.encode('utf-8')).hexdigest()

async def get_upload_url():
    params = {
        "application_key": APP_KEY,
        "method": "video.getUploadUrl",
        "access_token": ACCESS_TOKEN,
        "format": "json"
    }
    params["sig"] = sign_request(params)

    response = requests.get("https://api.ok.ru/fb.do", params=params).json()
    if "error_code" in response:
        return None, None
    return response["upload_url"], response["video_id"]

async def upload_to_okru(file_path: str):
    upload_url, video_id = await get_upload_url()
    if not upload_url:
        return None, "خطا در دریافت URL آپلود از OK.ru"

    with open(file_path, "rb") as f:
        files = {"file": f}
        upload_resp = requests.post(upload_url, files=files)

    if upload_resp.status_code != 200:
        return None, f"خطا در آپلود: {upload_resp.text}"

    # عمومی کردن ویدیو
    params = {
        "method": "video.update",
        "video_id": video_id,
        "status": "public",
        "access_token": ACCESS_TOKEN,
        "application_key": APP_KEY,
        "format": "json"
    }
    params["sig"] = sign_request(params)
    requests.get("https://api.ok.ru/fb.do", params=params)

    video_link = f"https://ok.ru/video/{video_id}"
    return video_link, video_id

@app.on_message(filters.private & filters.video)
async def handle_video(client: Client, message: Message):
    await message.reply_text("ویدیو دریافت شد! در حال آپلود به OK.ru... ⏳")

    # دانلود ویدیو
    file_path = await message.download(file_name=f"{TEMP_DIR}/{message.video.file_unique_id}.mp4")

    # آپلود به OK.ru
    link, video_id = await upload_to_okru(file_path)

    # پاک کردن فایل موقت
    try:
        os.remove(file_path)
    except:
        pass

    if link:
        await message.reply_text(
            f"ویدیو با موفقیت در OK.ru آپلود شد! 🎉\n\n"
            f"لینک: {link}\n"
            f"ID ویدیو: {video_id}"
        )
    else:
        await message.reply_text(f"خطا در آپلود: {video_id}")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text(
        "سلام! 👋\n"
        "من ربات آپلود ویدیو به OK.ru هستم.\n\n"
        "فقط یک ویدیو برام بفرست، خودم آپلود می‌کنم و لینک رو بهت می‌دم! 🚀"
    )

print("ربات در حال اجراست...")
app.run()
