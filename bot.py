from pyrogram import Client, idle, filter  # filters را به filter تغییر دادیم
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
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

BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'

app = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# اضافه کردن هندلرها
app.add_handler(MessageHandler(start_handler, filter.command("start")))
app.add_handler(CallbackQueryHandler(ask_text, filter.regex("text_wm")))
app.add_handler(MessageHandler(handle_text_input, filter.text & filter.private))
app.add_handler(CallbackQueryHandler(set_position, filter.regex("^text_pos_")))
app.add_handler(CallbackQueryHandler(set_size, filter.regex("^text_size_")))
app.add_handler(MessageHandler(handle_video, filter.video & filter.private))
app.add_handler(CallbackQueryHandler(ask_image, filter.regex("image_wm")))
app.add_handler(MessageHandler(handle_image_upload, filter.photo & filter.private))
app.add_handler(CallbackQueryHandler(set_image_position, filter.regex("^image_pos_")))
app.add_handler(CallbackQueryHandler(set_image_size, filter.regex("^image_size_")))
app.add_handler(MessageHandler(process_image_watermark, filter.video & filter.private))


app.run()
