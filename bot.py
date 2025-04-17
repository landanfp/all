import os
import threading
import uvicorn
from fastapi import FastAPI
from pyrogram import Client

# مسیر مطلق برای پوشه plugins
plugin_path = os.path.join(os.path.dirname(__file__), "plugins")

# Pyrogram bot setup
app = Client(
    "media_cutter_bot",
    api_id=3335796,
    api_hash="138b992a0e672e8346d8439c3f42ea78",
    bot_token="6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8",
    plugins=dict(root=plugin_path)
)

# FastAPI app for health check
web_app = FastAPI()

@web_app.get("/")
def read_root():
    return {"status": "ok"}

def run_web():
    uvicorn.run(web_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("Bot is running...")
    print("Plugin path:", plugin_path)
    threading.Thread(target=run_web).start()
    app.run()
