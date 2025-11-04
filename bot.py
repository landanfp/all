# نام فایل: bot.py (فایل اصلی ربات)
from pyrogram import Client, idle
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

# ایمپورت کردن توابع 
from plugins.image_watermark import (
    ask_image,
    handle_image_upload,
    set_image_position,
    set_image_size,
    process_image_watermark,
)
from plugins.text_watermark import (
    ask_text,
    handle_text_input,
    set_position,
    set_size,
    handle_video,
)
from plugins.start import start_handler

# توکن‌ها و شناسه‌ها (لطفاً این مقادیر را با مقادیر واقعی خود جایگزین کنید)
BOT_TOKEN = '5355055672:AAEE8OIOqLYxbnwesF3ki2sOsXr03Q90JiI'
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'

app = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ------------------------------------
# ثبت هندلرها (خطاهای مربوط به group=N اینجا اصلاح شد)
# ------------------------------------

# جریان شروع و انتخاب
app.add_handler(MessageHandler(start_handler, filters.command("start")))
app.add_handler(CallbackQueryHandler(ask_text, filters.regex("text_wm")))
app.add_handler(CallbackQueryHandler(ask_image, filters.regex("image_wm")))

# جریان واترمارک متنی
app.add_handler(MessageHandler(handle_text_input, filters.text & filters.private))
app.add_handler(CallbackQueryHandler(set_position, filters.regex("^text_pos_")))
app.add_handler(CallbackQueryHandler(set_size, filters.regex("^text_size_")))

# جریان واترمارک تصویری
# **فیکس: handler برای photo + handler برای document (بدون mime_type در filter)**
app.add_handler(MessageHandler(handle_image_upload, filters.photo & filters.private))
app.add_handler(MessageHandler(handle_image_upload, filters.document & filters.private))  # همه documentها، mime داخل handler چک می‌شه
app.add_handler(CallbackQueryHandler(set_image_position, filters.regex("^image_pos_")))
app.add_handler(CallbackQueryHandler(set_image_size, filters.regex("^image_size_")))

# هندلرهای دریافت ویدیو: آرگومان 'group' به متد add_handler منتقل شد.
app.add_handler(MessageHandler(handle_video, filters.video & filters.private), group=1) # واترمارک متنی
app.add_handler(MessageHandler(process_image_watermark, filters.video & filters.private), group=2) # واترمارک تصویری


print("Bot started. Press Ctrl+C to exit.")
app.run()
