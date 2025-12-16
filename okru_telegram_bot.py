
# فایل: okru_telegram_bot.py

import requests
import os
import hashlib
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# === تنظیمات تلگرام ===
# این مقادیر را با اطلاعات خودتان جایگزین کنید
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '7136875110:AAGr1EREy_qPMgxVbuE4B0cHGVcwWudOrus'

# === تنظیمات OK.ru ===
# این مقادیر را با اطلاعات اپلیکیشن خود در OK.ru جایگزین کنید
ACCESS_TOKEN = "your_ok_ru_access_token"  # <-- توکن دسترسی معتبر
APP_KEY = "your_application_public_key"  # <-- کلید عمومی اپلیکیشن (Application Key)
SECRET_KEY = "your_application_secret_key"  # <-- کلید مخفی اپلیکیشن
# این کلید مخفی نشست است که برای امضای درخواست‌های کاربر استفاده می‌شود
SESSION_SECRET_KEY = "your_session_secret_key"

# فولدر موقت برای دانلود ویدیوها
TEMP_DIR = "downloads"
os.makedirs(TEMP_DIR, exist_ok=True)

app = Client("okru_uploader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def sign_request(params):
    """
    امضای دیجیتال درخواست را با استفاده از کلید مخفی نشست (session_secret_key) تولید می‌کند.
    """
    param_str = ''.join([k + '=' + str(v) for k, v in sorted(params.items())])
    # *** تغییر اصلی اینجاست ***
    # برای درخواست‌های دارای access_token باید از کلید مخفی نشست استفاده کرد.
    sig_str = param_str + SESSION_SECRET_KEY
    return hashlib.md5(sig_str.encode('utf-8')).hexdigest()

async def get_upload_url():
    """
    URL لازم برای آپلود ویدیو را از API سایت OK.ru دریافت می‌کند.
    """
    params = {
        "application_key": APP_KEY,
        "method": "video.getUploadUrl",
        "access_token": ACCESS_TOKEN,
        "format": "json"
    }
    params["sig"] = sign_request(params)

    try:
        response = requests.get("https://api.ok.ru/fb.do", params=params)
        response.raise_for_status()  # بررسی خطاهای HTTP
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"خطای شبکه در ارتباط با API: {e}")
        return None, f"خطای شبکه: {e}"

    # برای خطایابی: پاسخ کامل از سرور OK.ru را چاپ می‌کند
    print(f"OK.ru API Response: {data}")

    if "error_code" in data:
        error_msg = data.get("error_msg", "خطای نامشخص از API")
        return None, error_msg

    return data.get("upload_url"), data.get("video_id")

async def upload_to_okru(file_path: str):
    """
    فایل ویدیو را در OK.ru آپلود کرده و لینک آن را برمی‌گرداند.
    """
    upload_url, result = await get_upload_url()
    if not upload_url:
        # result حاوی پیام خطا از get_upload_url است
        return None, f"خطا در دریافت URL آپلود: {result}"

    video_id = result
    try:
        with open(file_path, "rb") as f:
            files = {"video_file_1": f}  # نام پارامتر فایل ممکن است متفاوت باشد
            upload_resp = requests.post(upload_url, files=files)
            upload_resp.raise_for_status()
            # پاسخ آپلود معمولا شامل اطلاعاتی است که باید به سرور ok.ru برگردانده شود
            print(f"Upload response text: {upload_resp.text}")

    except requests.exceptions.RequestException as e:
        return None, f"خطا در آپلود فایل: {e}"

    # پس از آپلود موفق، ممکن است نیاز به تایید آپلود باشد
    # این بخش بسته به API ممکن است متفاوت باشد، در اینجا عمومی کردن ویدیو انجام می‌شود

    params = {
        "method": "video.update",
        "video_id": video_id,
        "status": "PUBLIC",  # معمولا مقادیر بزرگ (UPPERCASE) هستند
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
    """
    ویدیوهای ارسالی توسط کاربر را مدیریت می‌کند.
    """
    progress_message = await message.reply_text("ویدیو دریافت شد! در حال آماده‌سازی برای آپلود... ⏳")

    # دانلود ویدیو
    try:
        file_path = await message.download(
            file_name=f"{TEMP_DIR}/{message.video.file_unique_id}.mp4"
        )
    except Exception as e:
        await progress_message.edit_text(f"خطا در دانلود ویدیو از تلگرام: {e}")
        return

    await progress_message.edit_text("ویدیو دانلود شد. در حال آپلود به OK.ru... 🚀")

    # آپلود به OK.ru
    link, result = await upload_to_okru(file_path)

    # پاک کردن فایل موقت
    if os.path.exists(file_path):
        os.remove(file_path)

    if link:
        await progress_message.edit_text(
            f"✅ ویدیو با موفقیت در OK.ru آپلود شد! 🎉\n\n"
            f"**لینک:** {link}\n"
            f"**ID ویدیو:** `{result}`"
        )
    else:
        # result حاوی پیام خطا است
        await progress_message.edit_text(f"❌ خطا در آپلود به OK.ru:\n\n`{result}`")

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    """
    پاسخ به دستور /start
    """
    await message.reply_text(
        "سلام! 👋\n"
        "من ربات آپلود ویدیو به OK.ru هستم.\n\n"
        "کافی است یک ویدیو برای من بفرستید تا آن را آپلود کرده و لینک را برای شما ارسال کنم. 🚀"
    )

async def main():
    print("ربات در حال اجراست...")
    await app.start()
    await asyncio.Event().wait() # برای در حال اجرا نگه داشتن ربات

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nخروج از ربات...")
    finally:
        # ممکن است نیاز به توقف app به صورت async باشد
        # loop.run_until_complete(app.stop())
        pass
