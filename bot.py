from pyrogram import Client
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

plugins = dict(root="plugins")

app = Client("video_cutter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, plugins=plugins)

if __name__ == "__main__":
    app.run()
