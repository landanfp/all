"""
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from PIL import Image
import os
import shutil
from pyrogram.types import InputMediaVideo
from aiohttp import web
import asyncio """
#import ffmpeg


import os
import asyncio
from pyrogram import Client
from aiohttp import web

# مقادیر زیر را با مقادیر واقعی جایگزین کن یا از ENV استفاده کن
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# health check server
async def health_check(request):
    return web.Response(text="OK")

async def start_fake_server():
    aio_app = web.Application()
    aio_app.router.add_get("/", health_check)
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

# اجرای ربات و سرور
async def main():
    await start_fake_server()
    await app.start()
    print("Bot is running. Press Ctrl+C to stop.")
    await idle()
    await app.stop()

if __name__ == "__main__":
    from pyrogram import idle
    asyncio.run(main())
