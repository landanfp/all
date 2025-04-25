from pyrogram import Client, filters
from instaloader import Instaloader, Post
import os
import re
import glob

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '1396293494:AAE6YAY-Vog3QPvSNCo8x80FsIue9FJGWh8'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

bot = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# تابع استخراج شورت‌کد از لینک اینستاگرام
def extract_shortcode(url):
    match = re.search(r"(reel|p|tv)/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(2)
    return None

# دستور /start
@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    await message.reply("سلام! لینک پست یا ریلز اینستاگرام رو بفرست.")

# دریافت و دانلود پست
@bot.on_message(filters.private & filters.text)
async def insta_download(client, message):
    url = message.text.strip()
    if "instagram.com" not in url:
        await message.reply("لینک اینستاگرام معتبر نیست.")
        return

    shortcode = extract_shortcode(url)
    if not shortcode:
        await message.reply("نتونستم کد پست رو استخراج کنم.")
        return

    try:
        msg = await message.reply("در حال دانلود...")
    except:
        msg = None

    try:
        # دانلود با Instaloader
        L = Instaloader(dirname_pattern="downloads", save_metadata=False, download_comments=False)
        post = Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=None)

        # پیدا کردن آخرین فایل‌های دانلود شده (mp4 یا jpg)
        downloaded_files = sorted(
            glob.glob("downloads/*.mp4") + glob.glob("downloads/*.jpg"),
            key=os.path.getmtime,
            reverse=True
        )[:2]

        if not downloaded_files:
            if msg:
                await msg.edit("فایلی برای ارسال پیدا نشد.")
            else:
                await message.reply("فایلی برای ارسال پیدا نشد.")
            return

        for file in downloaded_files:
            await message.reply_document(file)
            os.remove(file)

        if msg:
            await msg.delete()

    except Exception as e:
        if msg:
            try:
                await msg.edit(f"خطا در دانلود:\n{e}")
            except:
                await message.reply(f"خطا:\n{e}")
        else:
            await message.reply(f"خطا:\n{e}")

bot.run()
