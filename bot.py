
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from PIL import Image
import os
import shutil
from pyrogram.types import InputMediaVideo
from aiohttp import web
import asyncio 
#import ffmpeg


#import os
#import asyncio
#from pyrogram import Client
#from aiohttp import web

API_ID = int(os.environ.get("API_ID", "3335796"))
API_HASH = os.environ.get("API_HASH", "138b992a0e672e8346d8439c3f42ea78")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8")

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)




@Client.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("تبدیل صدا به ویس", callback_data="audio_to_speech"),
         InlineKeyboardButton("تبدیل ویس به صدا", callback_data="speech_to_audio")],
        [InlineKeyboardButton("برش صدا", callback_data="audio_cut"),
         InlineKeyboardButton("ادغام صدا", callback_data="audio_merge")],
        [InlineKeyboardButton("تبدیل ویدیو به صدا", callback_data="video_to_audio"),
         InlineKeyboardButton("زیپ کردن فایل‌ها", callback_data="zip_files")],
        [InlineKeyboardButton("برش ویدیو", callback_data="video_cut"),
         InlineKeyboardButton("افزودن زیرنویس به ویدیو", callback_data="add_subtitles")],
        [InlineKeyboardButton("ادغام ویدیوها", callback_data="merge_videos"),
         InlineKeyboardButton("افزودن صدا به ویدیو", callback_data="add_audio_to_video")],
        [InlineKeyboardButton("گرفتن اسکرین‌شات", callback_data="take_screenshot")]
    ])
    await message.reply_text(
        "به ربات خوش آمدید! انتخاب کنید که می‌خواهید چه کاری انجام دهید:",
        reply_markup=keyboard
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
