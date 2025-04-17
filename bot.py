from pyrogram import Client
import os

API_ID = 3335796
API_HASH = "138b992a0e672e8346d8439c3f42ea78"
BOT_TOKEN = "6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8"

plugins = dict(root="plugins")

app = Client("video_cutter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, plugins=plugins)

if __name__ == "__main__":
    app.run()
