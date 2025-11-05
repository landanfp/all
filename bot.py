# نام فایل: bot.py (نسخه Pyrogram با فیکس Health Check توسط FastAPI)

# ماژول‌های استاندارد پایتون
import threading
import os
import logging
import asyncio
import time

# ماژول‌های لازم برای Health Check (FastAPI و Uvicorn)
from fastapi import FastAPI
import uvicorn

# ماژول‌های اصلی Pyrogram
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ماژول‌های داخلی برای پردازش واترمارک (این فایل باید وجود داشته باشد)
from helper.watermark import add_text_watermark, add_image_watermark

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------------------------------------------------------------
# پیکربندی Pyrogram
# ----------------------------------------------------------------------

# این مقادیر باید از متغیرهای محیطی خوانده شوند.
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '1396293494:AAFY7RXygNEZPFPXfmoJ66SljlXeCSilXG0'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه
# تعریف کلاینت Pyrogram
try:
    # Pyrogram باید به صورت ناهمگام (Async) اجرا شود
    app = Client(
        "watermark_bot", 
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
except Exception as e:
    logging.error(f"Failed to initialize Pyrogram client: {e}")
    app = None

# حالت‌های مختلف کاربران
user_states = {}

# ----------------------------------------------------------------------
# منطق Health Check با FastAPI
# ----------------------------------------------------------------------

# 1. تعریف برنامه FastAPI
web_app = FastAPI()

@web_app.get("/")
@web_app.get("/health")
async def health_check():
    """یک پاسخ ساده برای اطمینان از زنده بودن سرور HTTP"""
    return {"status": "ok", "uptime": round(time.time() - start_time, 2)}

# 2. تابعی برای اجرای سرور Uvicorn (همگام)
# ما از Server و Config به جای uvicorn.run استفاده می‌کنیم تا بتوانیم آن را در یک Thread اجرا کنیم.
def run_web_server():
    """سرور Uvicorn را در یک رشته جداگانه برای Health Check اجرا می‌کند."""
    # پورت را از متغیر محیطی PORT می‌خواند، در غیر این صورت از 8000 استفاده می‌کند
    port = int(os.environ.get('PORT', 8000))
    host = '0.0.0.0'
    
    # تنظیمات Uvicorn
    config = uvicorn.Config(
        web_app, 
        host=host, 
        port=port, 
        log_level="info", 
        loop="asyncio"  # تضمین می‌کند که از حلقه asyncio استفاده شود
    )
    
    # ساخت سرور
    server = uvicorn.Server(config)
    
    logging.info(f"FastAPI/Uvicorn Health Check server starting on {host}:{port}...")
    
    # اجرای سرور به صورت همگام در این Thread
    # از آنجایی که این در یک Thread جداگانه است، حلقه اصلی Pyrogram بلاک نمی‌شود.
    server.run()


# ----------------------------------------------------------------------
# منطق اصلی ربات (Pyrogram Handlers)
# ----------------------------------------------------------------------

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    await message.reply_text("سلام! ویدیوی خود را برای افزودن واترمارک ارسال کنید.")
    user_states[user_id] = 'awaiting_video'
    logging.debug(f"User {user_id} started, state set to awaiting_video")

@app.on_message(filters.video)
async def handle_video(client: Client, message: Message):
    # منطق پردازش ویدیو در اینجا می‌آید.
    # به دلیل استفاده از Pyrogram و توابع async، باید مطمئن شوید که 
    # add_text_watermark و add_image_watermark نیز ناهمگام (async) هستند
    # یا با استفاده از run_in_executor در یک ThreadPool اجرا می‌شوند.
    
    # فعلا فقط یک پیام ساده برمی‌گردانیم تا فلو اجرا شود:
    await message.reply_text("ویدیو دریافت شد. در حال پردازش... (لطفاً منطق واترمارک را تکمیل کنید)")
    user_states[message.from_user.id] = 'awaiting_video'


# ----------------------------------------------------------------------
# نقطه شروع اجرای برنامه
# ----------------------------------------------------------------------
start_time = time.time() # زمان شروع برای نمایش در Health Check

if __name__ == '__main__':
    
    # 1. راه اندازی سرور Health Check
    # سرور وب را در یک رشته مجزا اجرا می‌کنیم
    web_server_thread = threading.Thread(target=run_web_server, daemon=True)
    web_server_thread.start()
    logging.info("FastAPI/Uvicorn Health Check Thread Started.")

    # 2. اجرای کلاینت Pyrogram
    if app:
        try:
            logging.info("Pyrogram Bot Starting...")
            app.run()
            # idle() برای جلوگیری از بسته شدن برنامه
            idle()
        except Exception as e:
            logging.error(f"An error occurred in the bot's main loop: {e}")
