# --- bot.py ---
from fastapi import FastAPI
import uvicorn
import threading
from pyrogram import Client, filters
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

app = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ---- هندلرهای Pyrogram ----
app.add_handler(MessageHandler(start_handler, filters.command("start")))
app.add_handler(CallbackQueryHandler(ask_text, filters.regex("text_wm")))
app.add_handler(CallbackQueryHandler(ask_image, filters.regex("image_wm")))

app.add_handler(MessageHandler(handle_text_input, filters.text & filters.private))
app.add_handler(CallbackQueryHandler(set_position, filters.regex("^text_pos_")))
app.add_handler(CallbackQueryHandler(set_size, filters.regex("^text_size_")))

app.add_handler(MessageHandler(handle_image_upload, filters.photo & filters.private))
app.add_handler(MessageHandler(handle_image_upload, filters.document & filters.private))
app.add_handler(CallbackQueryHandler(set_image_position, filters.regex("^image_pos_")))
app.add_handler(CallbackQueryHandler(set_image_size, filters.regex("^image_size_")))

app.add_handler(MessageHandler(handle_video, filters.video & filters.private), group=1)
app.add_handler(MessageHandler(process_image_watermark, filters.video & filters.private), group=2)

# ---- FastAPI برای health check ----
api = FastAPI()

@api.get("/")
def root():
    return {"status": "ok", "message": "Bot is running"}

def run_pyrogram():
    print("Starting Pyrogram bot...")
    app.run()

def run_fastapi():
    print("Starting FastAPI web server on port 8000...")
    uvicorn.run(api, host="0.0.0.0", port=8000)

# اجرای همزمان هر دو (FastAPI + Pyrogram)
if __name__ == "__main__":
    threading.Thread(target=run_pyrogram, daemon=True).start()
    run_fastapi()
