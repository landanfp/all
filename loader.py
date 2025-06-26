from pyrogram import Client
import os

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAGLGffeJmdNVhCEangvn0GnnGK_0zWngDU'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

plugins = dict(root="plugins")

app = Client("hardsub_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


