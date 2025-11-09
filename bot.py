from pyrogram import Client, idle
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
# ایمپورت کردن توابع
from plugins.image_watermark import (
    ask_image,
    handle_image_upload,
    set_image_position,
    set_image_size,
    # process_image_watermark حذف شد (حالا در text_watermark ادغام می‌شه)
)
from plugins.text_watermark import (
    ask_text,
    handle_text_input,
    set_position,
    set_size,
    handle_video,  # حالا این handle_video هر دو text و image رو manage می‌کنه
)
from plugins.start import start_handler
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

# تنظیم لاگ‌بندی کلی (فایل + کنسول)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# توکن‌ها و شناسه‌ها (لطفاً این مقادیر را با مقادیر واقعی خود جایگزین کنید)
BOT_TOKEN = '1396293494:AAFY7RXygNEZPFPXfmoJ66SljlXeCSilXG0'
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'

app = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """پاسخ دهنده ساده به درخواست‌های HTTP برای بررسی سلامت."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_health_server():
    """شروع سرور HTTP در پورت 8000."""
    server_address = ('0.0.0.0', 8000)
    try:
        httpd = HTTPServer(server_address, HealthCheckHandler)
        logger.info("✅ Health Check Server started on port 8000.")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"❌ Failed to start Health Check Server: {e}")

# جریان شروع و انتخاب
app.add_handler(MessageHandler(start_handler, filters.command("start")))
app.add_handler(CallbackQueryHandler(ask_text, filters.regex("text_wm")))
app.add_handler(CallbackQueryHandler(ask_image, filters.regex("image_wm")))

# جریان واترمارک متنی
app.add_handler(MessageHandler(handle_text_input, filters.text & filters.private))
app.add_handler(CallbackQueryHandler(set_position, filters.regex("^text_pos_")))
app.add_handler(CallbackQueryHandler(set_size, filters.regex("^text_size_")))

# جریان واترمارک تصویری
app.add_handler(MessageHandler(handle_image_upload, filters.photo & filters.private))
app.add_handler(MessageHandler(handle_image_upload, filters.document & filters.private))

app.add_handler(CallbackQueryHandler(set_image_position, filters.regex("^image_pos_")))
app.add_handler(CallbackQueryHandler(set_image_size, filters.regex("^image_size_")))

# **فیکس: یک handler واحد برای video (بدون group) - هر دو text و image رو handle می‌کنه**
app.add_handler(MessageHandler(handle_video, filters.video & filters.private))  # حالا handle_video universal هست

if __name__ == "__main__":
    # 1. سرور Health Check را در یک Thread جداگانه شروع می‌کنیم.
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True
    health_thread.start()
    logger.info("Bot started. Press Ctrl+C to exit.")
    app.run()
