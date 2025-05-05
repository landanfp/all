import jdatetime
import pytz
import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from instaloader import Instaloader, Post, Profile
import os
import re
import glob

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAHoidc0x6nM3g2JHmb7xhWKmwGJOoKFNXY'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه


known_users = set()
tehran_tz = pytz.timezone('Asia/Tehran')

bot = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# تابع استخراج شورت‌کد از لینک اینستاگرام
def extract_shortcode(url):
    match = re.search(r"(reel|p|tv)/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(2)
    return None

# تابع ارسال پروفایل (بدون لاگین)
async def send_profile_picture(username, message):
    try:
        L = Instaloader()
        try:
            profile = Profile.from_username(L.context, username)
            profile_pic_url = profile.profile_pic_url
            await message.reply_photo(profile_pic_url)
        except Exception as e:
            await message.reply(f"خطا در دریافت عکس پروفایل (بدون لاگین): {e}")
    except Exception as e:
        await message.reply(f"خطا در ایجاد Instaloader: {e}")

# تابع دانلود استوری (بدون لاگین)
async def download_story(url, message):
    try:
        L = Instaloader()
        # استخراج یوزرنیم از URL استوری
        username_match = re.search(r"instagram\.com/stories/([a-zA-Z0-9_]+)", url)
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
        await message.reply(f"خطا در دانلود استوری (بدون لاگین): {e}")

# دستور /start
@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("راهنما", callback_data="help"),
                InlineKeyboardButton("کانال پشتیبان", url="https://t.me/ir_botz"),
            ],
        ]
    )
    await message.reply("سلام! لینک پست یا ریلز اینستاگرام، یوزرنیم پیج یا لینک استوری رو بفرستید.", reply_markup=keyboard)

    # بررسی اینکه آیا کاربر قبلاً استارت کرده است یا خیر
    if user_id not in known_users:
        known_users.add(user_id)
        # ارسال پیام به کانال لاگ (فقط برای اولین استارت)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_tehran = now_utc.astimezone(tehran_tz)
        shamsi_date = jdatetime.datetime.fromgregorian(datetime=now_tehran).strftime("%Y/%m/%d")
        tehran_time = now_tehran.strftime("%H:%M:%S")

        user = message.from_user
        username = user.username if user.username else "ندارد"
        first_name = user.first_name if user.first_name else ""
        last_name = user.last_name if user.last_name else ""
        full_name = f"{first_name} {last_name}".strip() or "ندارد"

        log_message = f"""✅ کاربر جدیدی به ربات پیوست.
تاریخ و ساعت ورود : {shamsi_date} {tehran_time}
نام کاربر : {full_name}
آیدی عددی : {user.id}
یوزرنیم : @{username}"""

        try:
            await client.send_message(LOG_CHANNEL, log_message)
        except Exception as e:
            print(f"خطا در ارسال پیام لاگ: {e}")

# هندلر برای دکمه "راهنما"
@bot.on_callback_query(filters.regex("help"))
async def help_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer()  # برای جلوگیری از نمایش ساعت شنی
    await callback_query.message.reply_text("برای دانلود پست و ریلز اینستاگرام فقط کافیه\nلینک موردنظر را کپی و اینجا ارسال کنید.")

# دستور /users
@bot.on_message(filters.private & filters.command("users"))
async def users_handler(client, message):
    user_count = len(known_users)
    await message.reply(f"{user_count}")

# دریافت و دانلود پست (بدون لاگین)
@bot.on_message(filters.private & filters.text)
async def insta_download(client, message):
    user_id = message.from_user.id
    known_users.add(user_id)
    url = message.text.strip()

    if "instagram.com" in url:
        if "stories" in url:  # اگر لینک استوری باشد
            await download_story(url, message)
            return

        # تلاش برای استخراج یوزرنیم از لینک پروفایل
        profile_match = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)/?", url)
        if profile_match:
            username = profile_match.group(1)
            await send_profile_picture(username, message)
            return

        shortcode = extract_shortcode(url)
        if not shortcode:
            await message.reply("لینک اینستاگرام معتبر نیست.")
            return

        try:
            msg = await message.reply("در حال دانلود...")
        except Exception as e:
            msg = None
            await message.reply(f"خطا در ارسال پیام: {e}")

        downloaded_files = []
        post_caption = None
        try:
            L = Instaloader(dirname_pattern="downloads", save_metadata=False, download_comments=False)
            post = Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=None)
            post_caption = post.caption

            downloaded_files = sorted(
                glob.glob("downloads/*.mp4") + glob.glob("downloads/*.jpg"),
                key=os.path.getmtime,
                reverse=True
            )[:2]

            if not downloaded_files:
                await (msg.edit("فایلی برای ارسال پیدا نشد.") if msg else message.reply("فایلی برای ارسال پیدا نشد."))
                return

            for file in downloaded_files:
                try:
                    await message.reply_document(file, caption=post_caption if post_caption else "")
                    os.remove(file)
                except Exception as e:
                    await message.reply(f"خطا در ارسال فایل {file}: {e}")

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

        finally:
            # اطمینان از حذف فایل های دانلود شده
            for file in downloaded_files:
                try:
                    os.remove(file)
                except Exception as e:
                    print(f"خطا در حذف فایل {file}: {e}")

    elif "@" in url:
        username = url.replace('@', '').strip()
        await send_profile_picture(username, message)

    else:
        await message.reply("لینک اینستاگرام معتبر نیست یا یوزرنیم اشتباه است.")

bot.run()
