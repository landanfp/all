# فایل: okru_telegram_bot.py

import requests
import os
import hashlib
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# === تنظیمات تلگرام ===
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '7136875110:AAGr1EREy_qPMgxVbuE4B0cHGVcwWudOrus'

# === تنظیمات OK.ru (با اطلاعات واقعی تو) ===
ACCESS_TOKEN = "-n-ImRMgTZ9CuU2hYBW9iEJnoilBkv0wUXhZvgOi8rD8RaF39FtxOYMvinTvspwiNLdXVg4sw8Gqj36SW6o8"  # توکن جدید و معتبر
APP_KEY = "COIOIMNGDIHBABABA"  # کلید عمومی (از ایمیل تأیید اپلیکیشن)
SECRET_KEY = "6B885C7A402C8EC353638176"  # کلید مخفی اپلیکیشن
SESSION_SECRET_KEY = "4ee5aa4b9721d1797c439344b9a77825"  # کلید مخفی نشست

# فولدر موقت برای دانلود ویدیوها
TEMP_DIR = "downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

app = Client("okru_uploader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def sign_request(params):
    """
    امضای دیجیتال درخواست با استفاده از SESSION_SECRET_KEY (برای توکن‌های جلسه‌ای/unlimited)
    """
    param_str = ''.join([k + '=' + str(v) for k, v in sorted(params.items())])
    sig_str = param_str + SESSION_SECRET_KEY
    return hashlib.md5(sig_str.encode('utf-8')).hexdigest()

async def get_upload_url():
    """
    دریافت URL آپلود از OK.ru
    """
    params = {
        "application_key": APP_KEY,
        "method": "video.getUploadUrl",
        "access_token": ACCESS_TOKEN,
        "format": "json"
    }
    params["sig"] = sign_request(params)

    try:
        response = requests.get("https://api.ok.ru/fb.do", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"خطای ارتباط با API OK.ru: {e}")
        return None, f"خطای ارتباط با سرور"

    print(f"پاسخ API OK.ru: {data}")  # برای دیباگ

    if "error_code" in data:
        error_msg = data.get("error_msg", "خطای نامشخص")
        error_code = data.get("error_code", "نامشخص")
        return None, f"خطای API ({error_code}): {error_msg}"

    return data.get("upload_url"), data.get("video_id")

async def upload_to_okru(file_path: str):
    """
    آپلود ویدیو به OK.ru و عمومی کردن آن
    """
    upload_url, video_id = await get_upload_url()
    if not upload_url or not video_id:
        return None, video_id  # video_id در اینجا پیام خطا است

    print(f"در حال آپلود ویدیو به: {upload_url}")
    try:
        with open(file_path, "rb") as f:
            files = {"file": f}  # نام فیلد درست "file" است (نه video_file_1)
            upload_resp = requests.post(upload_url, files=files, timeout=300)  # تایم‌اوت طولانی برای آپلود

        if upload_resp.status_code != 200:
            return None, f"آپلود ناموفق (کد {upload_resp.status_code})"

        print(f"آپلود موفق! پاسخ: {upload_resp.text}")

    except Exception as e:
        return None, f"خطا در ارسال فایل: {e}"

    # عمومی کردن ویدیو (اختیاری اما توصیه می‌شود)
    update_params = {
        "method": "video.update",
        "video_id": video_id,
        "status": "public",  # کوچک بنویس (public نه PUBLIC)
        "access_token": ACCESS_TOKEN,
        "application_key": APP_KEY,
        "format": "json"
    }
    update_params["sig"] = sign_request(update_params)
    requests.get("https://api.ok.ru/fb.do", params=update_params)

    video_link = f"https://ok.ru/video/{video_id}"
    return video_link, video_id

@app.on_message(filters.private & filters.video)
async def handle_video(client: Client, message: Message):
    progress = await message.reply_text("ویدیو دریافت شد! در حال دانلود... ⏳")

    try:
        file_path = await message.download(
            file_name=f"{TEMP_DIR}/{message.video.file_unique_id}.mp4",
            progress=lambda d, t: asyncio.create_task(progress.edit_text(f"دانلود: {int(d/t*100)}%"))
        )
    except Exception as e:
        await progress.edit_text(f"خطا در دانلود: {e}")
        return

    await progress.edit_text("دانلود کامل شد. در حال آپلود به OK.ru... 🚀")

    link, result = await upload_to_okru(file_path)

    # پاک کردن فایل موقت
    try:
        os.remove(file_path)
    except:
        pass

    if link:
        await progress.edit_text(
            f"✅ **ویدیو با موفقیت آپلود شد!** 🎉\n\n"
            f"🔗 **لینک:** {link}\n"
            f"🆔 **ID ویدیو:** `{result}`",
            disable_web_page_preview=True
        )
    else:
        await progress.edit_text(f"❌ خطا در آپلود:\n\n`{result}`")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply_text(
        "سلام دوست عزیز! 👋\n\n"
        "من ربات آپلود ویدیو به **OK.ru** هستم.\n\n"
        "فقط یک ویدیو برام بفرست، من آپلود می‌کنم و لینک مستقیمش رو بهت می‌دم! 🚀\n\n"
        "حجم ویدیو تا ۲ گیگابایت پشتیبانی می‌شه.",
        disable_web_page_preview=True
    )

print("ربات OK.ru Uploader در حال اجراست...")
app.run()
