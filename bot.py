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

API_ID = int(os.environ.get("API_ID", "3335796"))
API_HASH = os.environ.get("API_HASH", "138b992a0e672e8346d8439c3f42ea78")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7136875110:AAFzyr2i2FbRrmst1sklkJPN7Yz2rXJvSew")

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# health check handler
async def health_check(request):
    return web.Response(text="OK")

# start aiohttp server separately
async def start_fake_server():
    aio_app = web.Application()
    aio_app.router.add_get("/", health_check)
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

# main entry point
if __name__ == "__main__":
    async def run():
        await start_fake_server()
        await app.start()
        print("Bot is running. Press Ctrl+C to stop.")
        await asyncio.Event().wait()  # waits forever (instead of idle())

    asyncio.run(run())
