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
api_id = "3335796"  # جایگزین کنید با api_id خود
api_hash = "138b992a0e672e8346d8439c3f42ea78"  # جایگزین کنید با api_hash خود
bot_token = "7136875110:AAFzyr2i2FbRrmst1sklkJPN7Yz2rXJvSew"  # جایگزین کنید با bot_token خود

app = Client("media_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)


# مسیر ذخیره فایل‌ها در سرور
UPLOAD_FOLDER = "uploads/"

# اطمینان از وجود پوشه ذخیره‌سازی
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

async def health_check(request):
    return web.Response(text="OK")

async def start_fake_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

loop = asyncio.get_event_loop()
loop.create_task(start_fake_server())

# شروع ربات
app.run()
