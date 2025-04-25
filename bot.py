from pyrogram import Client, filters
from instaloader import Instaloader, Post
import os
import re

bot = Client(
    "insta_downloader_bot",
    api_id=123456,  # جایگزین کن
    api_hash="your_api_hash",  # جایگزین کن
    bot_token="your_bot_token"  # جایگزین کن
)

def extract_shortcode(url):
    match = re.search(r"(reel|p|tv)/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(2)
    return None

# /start command
@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    await message.reply(
        "**به ربات دانلود اینستاگرام خوش آمدی!**\n\n"
        "لینک پست، ریلز یا IGTV اینستاگرام رو بفرست تا فایل‌ها برات ارسال بشه.\n\n"
        "مثال:\nhttps://www.instagram.com/reel/abc123/"
    )

# handle instagram download
@bot.on_message(filters.private & filters.text)
async def insta_download(client, message):
    url = message.text.strip()

    if "instagram.com" not in url:
        await message.reply("لطفاً یک لینک معتبر از اینستاگرام ارسال کنید.")
        return

    shortcode = extract_shortcode(url)
    if not shortcode:
        await message.reply("لینک معتبر نیست. لطفاً لینک پست، ریلز یا IGTV ارسال کن.")
        return

    downloading_msg = await message.reply("در حال دانلود... لطفاً صبر کنید.")

    try:
        L = Instaloader(dirname_pattern="downloads", save_metadata=False, download_comments=False)
        post = Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=shortcode)

        await downloading_msg.delete()
        uploading_msg = await message.reply("در حال آپلود...")

        for file in os.listdir(f"./downloads/{shortcode}"):
            if file.endswith((".mp4", ".jpg")):
                file_path = f"./downloads/{shortcode}/{file}"
                await message.reply_document(file_path)
                os.remove(file_path)

        await uploading_msg.delete()
        os.rmdir(f"./downloads/{shortcode}")

    except Exception as e:
        await downloading_msg.edit(f"خطا در دانلود: {e}")

bot.run()
