from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI
import os
import threading
import uvicorn

plugins_path = os.path.join(os.path.dirname(__file__), "plugins")

# Pyrogram bot setup
app = Client(
    "media_cutter_bot",
    api_id=3335796,
    api_hash="138b992a0e672e8346d8439c3f42ea78",
    bot_token="6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8",
    plugins=dict(root="plugins")
)


# اپ ساده FastAPI برای health check
web_app = FastAPI()

@web_app.get("/")
def read_root():
    return {"status": "ok"}

# اجرای FastAPI در ترد جداگانه
def run_web():
    uvicorn.run(web_app, host="0.0.0.0", port=8000)

# اجرای بات
if __name__ == "__main__":
    print("Bot is running...")
    print("Plugin path:", plugins_path)
    threading.Thread(target=run_web).start()
    app.run()
