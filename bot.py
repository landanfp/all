from pyrogram import Client, filters
from instaloader import Instaloader, Post, Profile
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

# تابع ارسال پروفایل
async def send_profile_picture(username, message):
    try:
        L = Instaloader()
        # برای دریافت اطلاعات پروفایل باید از login استفاده کرد
        # در اینجا بدون ورود به حساب، به طور عمومی پروفایل را می‌خوانیم
        profile = Profile.from_username(L.context, username)
        profile_pic_url = profile.profile_pic_url
        await message.reply_photo(profile_pic_url)
    except Exception as e:
        await message.reply(f"خطا در دانلود عکس پروفایل: {e}")

# تابع دانلود استوری
async def download_story(url, message):
    try:
        L = Instaloader()
        # استخراج یوزرنیم از URL استوری
        username_match = re.search(r"instagram.com/stories/([a-zA-Z0-9_]+)", url)
        if username_match:
            username = username_match.group(1)
            profile = Profile.from_username(L.context, username)
            stories = L.get_stories(userids=[profile.userid])
            
            # دریافت استوری‌ها و ارسال آن‌ها
            for story in stories:
                for item in story.get_items():
                    if item.url:
                        # ارسال ویدیو یا تصویر استوری
                        if item.is_video:
                            await message.reply_video(item.url)
                        else:
                            await message.reply_photo(item.url)
        else:
            await message.reply("لینک استوری معتبر نیست.")
    except Exception as e:
        await message.reply(f"خطا در دانلود استوری: {e}")

# دستور /start
@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    await message.reply("سلام! لینک پست یا ریلز اینستاگرام، یوزرنیم پیج یا لینک استوری رو بفرست.")

# دریافت و دانلود پست
@bot.on_message(filters.private & filters.text)
async def insta_download(client, message):
    url = message.text.strip()

    # بررسی اینکه آیا این یک لینک اینستاگرام است یا یوزرنیم
    if "instagram.com" in url:
        if "stories" in url:  # اگر لینک استوری باشد
            await download_story(url, message)
        else:
            shortcode = extract_shortcode(url)
            if not shortcode:
                await message.reply("نتونستم کد پست رو استخراج کنم.")
                return

            try:
                msg = await message.reply("در حال دانلود...")
            except Exception as e:
                msg = None
                await message.reply(f"خطا در ارسال پیام: {e}")

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
                    await (msg.edit("فایلی برای ارسال پیدا نشد.") if msg else message.reply("فایلی برای ارسال پیدا نشد."))
                    return

                for file in downloaded_files:
                    await message.reply_document(file)
                    os.remove(file)

                if msg:
                    await msg.delete()

            except Exception as e:
                error_message = f"خطا در دانلود:\n{e}"
                if msg:
                    try:
                        await msg.edit(error_message)
                    except:
                        await message.reply(error_message)
                else:
                    await message.reply(error_message)

    # اگر یوزرنیم پیج ارسال شده باشد
    elif "@" in url:
        username = url.replace('@', '').strip()
        await send_profile_picture(username, message)

    else:
        await message.reply("لینک اینستاگرام معتبر نیست یا یوزرنیم اشتباه است.")
        
bot.run()
