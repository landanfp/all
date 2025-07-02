from pyrogram import Client
import os

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '7136875110:AAGr1EREy_qPMgxVbuE4B0cHGVcwWudOrus'

plugins = dict(root="plugins")

app = Client("hardsub_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


