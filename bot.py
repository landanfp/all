from pyrogram import Client
#from config import BOT_TOKEN
#from pyrogram import Client
from pyrogram import idle
from pyrogram.handlers import MessageHandler
from pyrogram.plugin import load_plugins  # این مهمه

BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'
API_ID = '3335796' 
API_HASH = '138b992a0e672e8346d8439c3f42ea78'


app = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# لود کردن پلاگین‌ها
load_plugins("plugins")


app.run()
