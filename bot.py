import os
import io
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import asyncio

# ----- بخش هوش مصنوعی Face Swap (Placeholder) -----
# !!! کد واقعی AI خود را اینجا جایگزین کنید !!!
class ai_face_swap:
    @staticmethod
    def swap_faces(base_image_path, face_image_path):
        print(f"AI Placeholder: Attempting to swap face from {face_image_path} onto {base_image_path}")
        try:
            # اطمینان از وجود فایل‌های ورودی قبل از کپی
            if not os.path.exists(base_image_path):
                print(f"AI Placeholder Error: Base image not found at {base_image_path}")
                return None
            if not os.path.exists(face_image_path):
                 print(f"AI Placeholder Error: Face image not found at {face_image_path}")
                 return None

            # نام فایل خروجی در همان پوشه موقت
            output_filename = f"swapped_placeholder_{os.path.basename(base_image_path)}"
            output_path = os.path.join(os.path.dirname(base_image_path), output_filename)

            shutil.copy(base_image_path, output_path)
            print(f"AI Placeholder: Saved dummy result to {output_path}")
            return output_path
        except Exception as e:
            print(f"AI Placeholder Error during copy: {e}")
            return None
# ----- پایان بخش AI Placeholder -----

# ----- تنظیمات ربات -----
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAHoidc0x6nM3g2JHmb7xhWKmwGJOoKFNXY'

# ----- تعریف پوشه دانلود موقت -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # دایرکتوری فعلی اسکریپت
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")

# ایجاد پوشه دانلود در صورت عدم وجود
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)
print(f"Temporary download directory: {TEMP_DOWNLOAD_DIR}")

# مقداردهی اولیه کلاینت پایروگرام
app = Client(
    "face_swap_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=BASE_DIR # تنظیم workdir برای اطمینان بیشتر
)

# دیکشنری برای ذخیره وضعیت و مسیر عکس پایه کاربران
user_data = {}

# ----- توابع کمکی (بدون تغییر) -----
async def send_message_safe(chat_id, text, reply_to_message_id=None):
    try:
        await app.send_message(chat_id, text, reply_to_message_id=reply_to_message_id)
    except FloodWait as e:
        print(f"FloodWait triggered. Waiting for {e.x} seconds.")
        await asyncio.sleep(e.x)
        await app.send_message(chat_id, text, reply_to_message_id=reply_to_message_id)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

def cleanup_files(file_list):
    print(f"Attempting to clean up files: {file_list}")
    for file_path in file_list:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Successfully cleaned up file: {file_path}")
            elif file_path:
                 print(f"File not found for cleanup (already deleted?): {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")

# ----- دستور /start -----
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    files_to_remove = []
    if user_id in user_data:
        # مسیر فایل قبلی را از دیکشنری بخوان و به لیست حذف اضافه کن
        old_base_path = user_data[user_id].get('base_image_path')
        if old_base_path:
            files_to_remove.append(old_base_path)
        del user_data[user_id]
        print(f"Cleared previous data for user {user_id}")

    # فایل‌ها را پاک کن (اگر وجود دارند)
    cleanup_files(files_to_remove)

    await send_message_safe(
        message.chat.id,
        "سلام! 👋 به ربات Face Swap خوش آمدید.\n\n"
        "۱. لطفاً ابتدا عکسی که می‌خواهید صورت جدید روی آن قرار بگیرد (عکس **پایه**) را ارسال کنید.",
        reply_to_message_id=message.id
    )

# ----- مدیریت دریافت عکس‌ها -----
@app.on_message(filters.photo & filters.private)
async def handle_photo(client, message: Message):
    user_id = message.from_user.id
    # اطمینان از وجود پوشه دانلودها
    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)
    temp_files_to_remove = []

    try:
        # ۱. بررسی وضعیت کاربر
        if user_id not in user_data or 'base_image_path' not in user_data[user_id]:
            # --> دریافت عکس پایه
            processing_msg = await message.reply("⏳ در حال دریافت و ذخیره عکس پایه...", quote=True)
            base_file_name = f"base_{user_id}_{message.photo.file_id}.jpg"
            # *** تغییر کلیدی: دانلود در پوشه مشخص شده ***
            base_image_full_path = os.path.join(TEMP_DOWNLOAD_DIR, base_file_name)

            try:
                await message.download(file_name=base_image_full_path)
                print(f"Base image downloaded to: {base_image_full_path}")
            except FloodWait as e:
                 print(f"FloodWait during download. Waiting for {e.x} seconds.")
                 await asyncio.sleep(e.x)
                 await message.download(file_name=base_image_full_path) # تلاش مجدد

            temp_files_to_remove.append(base_image_full_path) # اضافه به لیست پاکسازی موقت

            # *** تغییر کلیدی: ذخیره مسیر کامل ***
            user_data[user_id] = {'base_image_path': base_image_full_path}

            await processing_msg.edit_text(
                "✅ عکس پایه دریافت شد!\n\n"
                "۲. حالا عکسی که صورتِ آن را می‌خواهید روی عکس پایه قرار دهید (عکس **صورت**) ارسال کنید."
            )

        else:
            # --> دریافت عکس صورت
            # *** تغییر کلیدی: خواندن مسیر کامل از دیکشنری ***
            base_image_path = user_data[user_id].get('base_image_path')

            # بررسی وجود کلید و مسیر در دیکشنری
            if not base_image_path:
                 await send_message_safe(message.chat.id, "خطای داخلی: مسیر عکس پایه در داده‌های کاربر یافت نشد. لطفاً با /start شروع کنید.", message.id)
                 if user_id in user_data: del user_data[user_id]
                 return

            print(f"Checking existence of base file: {base_image_path}")
            # *** بررسی مجدد وجود فایل با مسیر کامل ***
            if not os.path.exists(base_image_path):
                 await send_message_safe(message.chat.id, f"خطا: فایل عکس پایه در مسیر '{base_image_path}' یافت نشد. ممکن است مشکلی در ذخیره‌سازی رخ داده باشد. لطفاً با /start مجدد شروع کنید.", message.id)
                 # پاک کردن وضعیت نامعتبر
                 del user_data[user_id]
                 return

            processing_msg = await message.reply("⏳ در حال دریافت عکس صورت و انجام عملیات تعویض چهره...", quote=True)
            face_file_name = f"face_{user_id}_{message.photo.file_id}.jpg"
            # *** تغییر کلیدی: دانلود عکس صورت در همان پوشه ***
            face_image_full_path = os.path.join(TEMP_DOWNLOAD_DIR, face_file_name)

            try:
                await message.download(file_name=face_image_full_path)
                print(f"Face image downloaded to: {face_image_full_path}")
            except FloodWait as e:
                 print(f"FloodWait during download. Waiting for {e.x} seconds.")
                 await asyncio.sleep(e.x)
                 await message.download(file_name=face_image_full_path) # تلاش مجدد

            temp_files_to_remove.append(face_image_full_path) # اضافه به لیست پاکسازی موقت

            # ۳. فراخوانی تابع Face Swap هوش مصنوعی
            # !!! اینجا تابع واقعی شما صدا زده می‌شود !!!
            result = ai_face_swap.swap_faces(base_image_path, face_image_full_path)

            if result:
                # (بخش ارسال نتیجه بدون تغییر زیاد، فقط مسیر نتیجه را به لیست پاکسازی اضافه می‌کنیم)
                if isinstance(result, str) and os.path.exists(result):
                    swapped_image_path = result
                    temp_files_to_remove.append(swapped_image_path) # نتیجه نهایی هم باید پاک شود
                    print(f"Sending result file {swapped_image_path} to user {user_id}")
                    try:
                         await message.reply_photo(photo=swapped_image_path, caption="✨ عکس شما با چهره جدید آماده شد!", quote=True)
                    # ... (handling FloodWait for sending photo) ...
                    except FloodWait as e:
                         print(f"FloodWait during photo send. Waiting for {e.x} seconds.")
                         await asyncio.sleep(e.x)
                         await message.reply_photo(photo=swapped_image_path, caption="✨ عکس شما با چهره جدید آماده شد!", quote=True)

                    await processing_msg.delete()

                elif isinstance(result, bytes):
                     # ... (handling bytes result - no change needed here) ...
                     swapped_image_bytes = io.BytesIO(result)
                     swapped_image_bytes.name = f"swapped_{user_id}_{message.photo.file_id}.jpg"
                     print(f"Sending result bytes (as {swapped_image_bytes.name}) to user {user_id}")
                     try:
                        await message.reply_photo(photo=swapped_image_bytes, caption="✨ عکس شما با چهره جدید آماده شد!", quote=True)
                     # ... (handling FloodWait for sending photo) ...
                     except FloodWait as e:
                         print(f"FloodWait during photo send. Waiting for {e.x} seconds.")
                         await asyncio.sleep(e.x)
                         await message.reply_photo(photo=swapped_image_bytes, caption="✨ عکس شما با چهره جدید آماده شد!", quote=True)
                     await processing_msg.delete()
                else:
                    error_msg = "متاسفانه مشکلی در پردازش تصویر پیش آمد (خروجی نامعتبر از مدل)."
                    print(f"Invalid result type from AI for user {user_id}: {type(result)}")
                    await processing_msg.edit_text(error_msg)
            else:
                error_msg = "❌ متاسفانه امکان تعویض چهره در این تصاویر وجود نداشت یا خطایی در پردازش رخ داد."
                print(f"AI swap failed for user {user_id}.")
                await processing_msg.edit_text(error_msg)

            # ۴. پاک کردن اطلاعات کاربر پس از اتمام کار
            # فایل عکس پایه اصلی که در user_data بود هم به لیست پاکسازی نهایی اضافه می‌شود
            # (دیگر در temp_files_to_remove نیست چون ممکن است در مرحله اول خطا رخ داده باشد)
            if os.path.exists(base_image_path):
                final_cleanup_list = temp_files_to_remove + [base_image_path]
            else:
                 final_cleanup_list = temp_files_to_remove

            if user_id in user_data: # فقط اگر هنوز وجود دارد پاک کن
                del user_data[user_id]
                print(f"Cleared data for user {user_id} after processing.")

    except FloodWait as e:
         # ... (handling FloodWait - no change) ...
         print(f"High-level FloodWait caught for user {user_id}. Waiting {e.x} seconds.")
         await asyncio.sleep(e.x)
         await send_message_safe(message.chat.id, f"ربات به دلیل محدودیت تلگرام موقتا کند شده است. لطفا {e.x} ثانیه صبر کنید و دوباره تلاش کنید.", message.id)
         # در صورت FloodWait بالا، فایل‌ها را پاک نمی‌کنیم تا کاربر بتواند دوباره تلاش کند؟ یا پاک کنیم؟ تصمیم: پاک نکنیم فعلا.
         final_cleanup_list = [] # مانع پاک شدن فایل‌ها در finally می‌شویم

    except Exception as e:
        print(f"!!! UNHANDLED ERROR handling photo for user {user_id}: {e}")
        # در صورت بروز خطا، وضعیت و فایل کاربر را پاک کن
        final_cleanup_list = temp_files_to_remove # فایل‌های دانلود شده در این مرحله را پاک کن
        if user_id in user_data:
            base_path_in_error = user_data[user_id].get('base_image_path')
            if base_path_in_error:
                 final_cleanup_list.append(base_path_in_error)
            del user_data[user_id]
            print(f"Cleared data for user {user_id} due to error.")
        await send_message_safe(message.chat.id, "⚠️ اوپس! یک خطای غیرمنتظره در ربات رخ داد. لطفاً دوباره تلاش کنید یا با /start شروع کنید.", message.id)


    finally:
        # پاک کردن تمام فایل‌های موقتی که در این پردازش استفاده شدند
        # توجه: در نسخه قبلی ممکن بود base_image_path به temp_files_to_remove اضافه نشده باشد
        # حالا از final_cleanup_list استفاده می‌کنیم که در همه حالات (موفقیت، خطا) تنظیم می‌شود
        if 'final_cleanup_list' in locals(): # فقط اگر تعریف شده باشد (یعنی try اجرا شده)
             cleanup_files(list(set(final_cleanup_list))) # استفاده از set برای جلوگیری از حذف دوباره فایل
        else:
             # اگر خطا قبل از تعریف final_cleanup_list رخ دهد (خیلی بعید)
             cleanup_files(temp_files_to_remove)
        print(f"--- Finished processing for user {user_id} ---")


if __name__ == "__main__":
    print("Bot starting...")
    try:
        app.run()
    except Exception as e:
        print(f"Error running the bot: {e}")
    print("Bot stopped.")
