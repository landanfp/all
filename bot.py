# --- bot.py ---
from fastapi import FastAPI
import uvicorn
import threading
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

# ایمپورت توابع از پلاگین‌ها
from plugins.image_watermark import (
    ask_image, handle_image_upload,
    set_image_position, set_image_size,
    process_image_watermark,
)
from plugins.text_watermark import (
    ask_text, handle_text_input,
    set_position, set_size,
    handle_video,
)
from plugins.start import start_handler

# ---- تنظیمات Pyrogram ----
BOT_TOKEN = '1396293494:AAFY7RXygNEZPFPXfmoJ66SljlXeCSilXG0'
API_ID = 3335796
API_HASH = '138b992a0e672e8346d8439c3f42ea78'

bot = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ---- هندلرهای Pyrogram ----
bot.add_handler(MessageHandler(start_handler, filters.command("start")))
bot.add_handler(CallbackQueryHandler(ask_text, filters.regex("text_wm")))
bot.add_handler(CallbackQueryHandler(ask_image, filters.regex("image_wm")))

bot.add_handler(MessageHandler(handle_text_input, filters.text & filters.private))
bot.add_handler(CallbackQueryHandler(set_position, filters.regex("^text_pos_")))
bot.add_handler(CallbackQueryHandler(set_size, filters.regex("^text_size_")))

bot.add_handler(MessageHandler(handle_image_upload, filters.photo & filters.private))
bot.add_handler(MessageHandler(handle_image_upload, filters.document & filters.private))
bot.add_handler(CallbackQueryHandler(set_image_position, filters.regex("^image_pos_")))
bot.add_handler(CallbackQueryHandler(set_image_size, filters.regex("^image_size_")))

bot.add_handler(MessageHandler(handle_video, filters.video & filters.private), group=1)
bot.add_handler(MessageHandler(process_image_watermark, filters.video & filters.private), group=2)

# ---- FastAPI برای health check ----
api = FastAPI()

@api.get("/")
def root():
    return {"status": "ok", "message": "Bot is running"}

# ✅ اجرای Pyrogram به روش امن در ترد جداگانه
def run_pyrogram():
    print("Starting Pyrogram bot...")
    asyncio.run(start_bot())

async def start_bot():
    await bot.start()
    print("Bot started successfully ✅")
    await idle()  # منتظر می‌ماند تا برنامه بسته شود
    await bot.stop()

# ✅ اجرای FastAPI (پورت 8000 برای health check)
def run_fastapi():
    print("Starting FastAPI web server on port 8000...")
    uvicorn.run(api, host="0.0.0.0", port=8000)

# اجرای همزمان هر دو
if __name__ == "__main__":
    threading.Thread(target=run_pyrogram, daemon=True).start()
    run_fastapi()
