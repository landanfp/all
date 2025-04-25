import os
import io
import shutil  # برای کپی کردن فایل در نسخه نمایشی (placeholder)
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait # برای مدیریت خطای FloodWait
import asyncio # برای استفاده از sleep در FloodWait

# ----- بخش هوش مصنوعی Face Swap -----
# !!! مهم: این بخش فقط یک نمونه‌ی نمایشی (Placeholder) است !!!
# شما باید اینجا کد واقعی مدل هوش مصنوعی خود را قرار دهید.
# این مدل باید دو مسیر فایل عکس (پایه و صورت) را بگیرد
# و یا بایت‌های تصویر نتیجه را برگرداند یا مسیر فایل تصویر نتیجه را.
class ai_face_swap:
    @staticmethod
    def swap_faces(base_image_path, face_image_path):
        """
        این تابع باید عملیات واقعی face swap را انجام دهد.
        ورودی: مسیر عکس پایه (str), مسیر عکس صورت (str)
        خروجی: بایت‌های تصویر نتیجه (bytes) یا مسیر فایل تصویر نتیجه (str).
               اگر ناموفق بود None برگرداند.
        """
        print(f"AI Placeholder: Attempting to swap face from {face_image_path} onto {base_image_path}")
        # --- کد واقعی هوش مصنوعی شما اینجا قرار می‌گیرد ---
        # مثال: اگر مدل شما تابعی به نام `run_inference` دارد:
        # try:
        #     result_image_bytes = run_inference(base_image_path, face_image_path)
        #     if result_image_bytes:
        #         # اگر مدل بایت برگرداند
        #         output_path = f"swapped_{os.path.basename(base_image_path)}"
        #         with open(output_path, "wb") as f:
        #              f.write(result_image_bytes)
        #         print(f"AI Model: Saved result to {output_path}")
        #         return output_path # مسیر فایل نتیجه را برمی‌گردانیم
        #     else:
        #         print("AI Model: Failed to generate result.")
        #         return None
        # except Exception as e:
        #     print(f"AI Model Error: {e}")
        #     return None
        # --- پایان کد واقعی هوش مصنوعی ---

        # --- کد نمایشی (Placeholder) ---
        # این بخش فقط برای تست ربات است و باید حذف یا جایگزین شود.
        # فقط عکس پایه را به عنوان نتیجه کپی می‌کنیم.
        try:
            output_path = f"swapped_placeholder_{os.path.basename(base_image_path)}"
            shutil.copy(base_image_path, output_path)
            print(f"AI Placeholder: Saved dummy result to {output_path}")
            return output_path # مسیر فایل نتیجه نمایشی را برمی‌گردانیم
        except Exception as e:
            print(f"AI Placeholder Error during copy: {e}")
            return None
        # --- پایان کد نمایشی ---

# ----- تنظیمات ربات -----
# !!! مقادیر واقعی خود را جایگزین کنید !!!
# توصیه می‌شود این مقادیر را از متغیرهای محیطی بخوانید.
API_ID = '3335796'        # API ID خود را اینجا قرار دهید
API_HASH = '138b992a0e672e8346d8439c3f42ea78'  # API Hash خود را اینجا قرار دهید
BOT_TOKEN = '5355055672:AAHoidc0x6nM3g2JHmb7xhWKmwGJOoKFNXY'   # توکن ربات خود را اینجا قرار دهید

# مقداردهی اولیه کلاینت پایروگرام
app = Client(
    "face_swap_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# دیکشنری برای ذخیره وضعیت و مسیر عکس پایه کاربران
# ساختار: {user_id: {'base_image_path': 'path/to/temp_user_base.jpg'}}
user_data = {}

# ----- تابع کمکی برای ارسال پیام با مدیریت FloodWait -----
async def send_message_safe(chat_id, text, reply_to_message_id=None):
    try:
        await app.send_message(chat_id, text, reply_to_message_id=reply_to_message_id)
    except FloodWait as e:
        print(f"FloodWait triggered. Waiting for {e.x} seconds.")
        await asyncio.sleep(e.x)
        await app.send_message(chat_id, text, reply_to_message_id=reply_to_message_id) # تلاش مجدد
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

# ----- تابع کمکی برای پاک کردن فایل‌ها -----
def cleanup_files(file_list):
    for file_path in file_list:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")

# ----- دستور /start -----
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    files_to_remove = []

    # پاک کردن اطلاعات و فایل قبلی کاربر (اگر وجود دارد) برای شروع مجدد
    if user_id in user_data:
        if 'base_image_path' in user_data[user_id]:
            files_to_remove.append(user_data[user_id]['base_image_path'])
        del user_data[user_id]
        print(f"Cleared previous data for user {user_id}")

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
    temp_files_to_remove = [] # لیستی برای نگهداری فایل‌های موقت این پردازش

    try:
        # ۱. بررسی وضعیت کاربر: آیا عکس پایه را فرستاده یا این اولین عکس است؟
        if user_id not in user_data or 'base_image_path' not in user_data[user_id]:
            # این اولین عکس است -> عکس پایه
            processing_msg = await message.reply("⏳ در حال دریافت و ذخیره عکس پایه...", quote=True)
            try:
                # استفاده از file_id برای نامگذاری منحصر به فردتر
                base_image_file = await message.download(f"temp_{user_id}_{message.photo.file_id}_base.jpg")
            except FloodWait as e:
                 print(f"FloodWait during download. Waiting for {e.x} seconds.")
                 await asyncio.sleep(e.x)
                 base_image_file = await message.download(f"temp_{user_id}_{message.photo.file_id}_base.jpg") # تلاش مجدد

            temp_files_to_remove.append(base_image_file) # این فایل باید در نهایت پاک شود

            # ذخیره مسیر عکس پایه برای این کاربر
            user_data[user_id] = {'base_image_path': base_image_file}
            print(f"Stored base image for user {user_id} at {base_image_file}")

            await processing_msg.edit_text( # ویرایش پیام قبلی
                "✅ عکس پایه دریافت شد!\n\n"
                "۲. حالا عکسی که صورتِ آن را می‌خواهید روی عکس پایه قرار دهید (عکس **صورت**) ارسال کنید."
            )

        else:
            # کاربر قبلاً عکس پایه را فرستاده -> این عکس صورت است
            if 'base_image_path' not in user_data[user_id]:
                 # این حالت نباید اتفاق بیفتد اما برای اطمینان بررسی می‌شود
                 await send_message_safe(message.chat.id, "خطایی در وضعیت رخ داده. لطفاً با /start مجدد شروع کنید.", message.id)
                 if user_id in user_data: del user_data[user_id]
                 return

            base_image_path = user_data[user_id]['base_image_path']

            # بررسی وجود فایل عکس پایه (برای اطمینان)
            if not os.path.exists(base_image_path):
                 await send_message_safe(message.chat.id, "خطا: فایل عکس پایه یافت نشد. ممکن است به طور دستی پاک شده باشد. لطفاً با /start مجدد شروع کنید.", message.id)
                 del user_data[user_id] # پاک کردن وضعیت نامعتبر
                 return

            processing_msg = await message.reply("⏳ در حال دریافت عکس صورت و انجام عملیات تعویض چهره...", quote=True)
            try:
                face_image_file = await message.download(f"temp_{user_id}_{message.photo.file_id}_face.jpg")
            except FloodWait as e:
                 print(f"FloodWait during download. Waiting for {e.x} seconds.")
                 await asyncio.sleep(e.x)
                 face_image_file = await message.download(f"temp_{user_id}_{message.photo.file_id}_face.jpg") # تلاش مجدد

            temp_files_to_remove.append(face_image_file) # این فایل هم باید پاک شود
            print(f"Downloaded face image for user {user_id} to {face_image_file}")

            # ۳. فراخوانی تابع Face Swap هوش مصنوعی
            # !!! اینجا تابع واقعی شما صدا زده می‌شود !!!
            result = ai_face_swap.swap_faces(base_image_path, face_image_file)

            if result:
                # بررسی نوع خروجی مدل AI (مسیر فایل یا بایت)
                if isinstance(result, str) and os.path.exists(result): # اگر مسیر فایل بود
                    swapped_image_path = result
                    # نتیجه نهایی هم باید بعدا پاک شود، مگر اینکه بخواهید نگه دارید
                    temp_files_to_remove.append(swapped_image_path)
                    print(f"Sending result file {swapped_image_path} to user {user_id}")
                    try:
                         await message.reply_photo(
                            photo=swapped_image_path,
                            caption="✨ عکس شما با چهره جدید آماده شد!",
                            quote=True
                         )
                    except FloodWait as e:
                         print(f"FloodWait during photo send. Waiting for {e.x} seconds.")
                         await asyncio.sleep(e.x)
                         await message.reply_photo(photo=swapped_image_path, caption="✨ عکس شما با چهره جدید آماده شد!", quote=True) # تلاش مجدد

                    await processing_msg.delete() # حذف پیام "در حال پردازش"

                elif isinstance(result, bytes): # اگر بایت‌های تصویر بود
                     swapped_image_bytes = io.BytesIO(result)
                     swapped_image_bytes.name = f"swapped_{user_id}_{message.photo.file_id}.jpg" # نامگذاری فایل در تلگرام
                     print(f"Sending result bytes (as {swapped_image_bytes.name}) to user {user_id}")
                     try:
                         await message.reply_photo(
                             photo=swapped_image_bytes,
                             caption="✨ عکس شما با چهره جدید آماده شد!",
                             quote=True
                         )
                     except FloodWait as e:
                         print(f"FloodWait during photo send. Waiting for {e.x} seconds.")
                         await asyncio.sleep(e.x)
                         await message.reply_photo(photo=swapped_image_bytes, caption="✨ عکس شما با چهره جدید آماده شد!", quote=True) # تلاش مجدد

                     await processing_msg.delete() # حذف پیام "در حال پردازش"

                else:
                      error_msg = "متاسفانه مشکلی در پردازش تصویر پیش آمد (خروجی نامعتبر از مدل)."
                      print(f"Invalid result type from AI for user {user_id}: {type(result)}")
                      await processing_msg.edit_text(error_msg)

            else:
                # اگر تابع swap_faces مقدار None برگرداند (یعنی ناموفق بود)
                error_msg = "❌ متاسفانه امکان تعویض چهره در این تصاویر وجود نداشت یا خطایی در پردازش رخ داد."
                print(f"AI swap failed for user {user_id}.")
                await processing_msg.edit_text(error_msg)

            # ۴. پاک کردن اطلاعات کاربر پس از اتمام کار (موفق یا ناموفق)
            # فایل عکس پایه اصلی که در user_data بود هم به لیست پاکسازی اضافه می‌شود
            if os.path.exists(base_image_path):
                 temp_files_to_remove.append(base_image_path)
            del user_data[user_id]
            print(f"Cleared data for user {user_id} after processing.")

    except FloodWait as e:
         print(f"High-level FloodWait caught for user {user_id}. Waiting {e.x} seconds.")
         await asyncio.sleep(e.x)
         # ممکن است لازم باشد عملیات را مجددا تلاش کنید یا به کاربر اطلاع دهید
         await send_message_safe(message.chat.id, f"ربات به دلیل محدودیت تلگرام موقتا کند شده است. لطفا {e.x} ثانیه صبر کنید و دوباره تلاش کنید.", message.id)

    except Exception as e:
        print(f"!!! UNHANDLED ERROR handling photo for user {user_id}: {e}")
        await send_message_safe(message.chat.id, "⚠️ اوپس! یک خطای غیرمنتظره در ربات رخ داد. لطفاً دوباره تلاش کنید یا با /start شروع کنید.", message.id)
        # در صورت بروز خطا، وضعیت و فایل کاربر را پاک کن
        if user_id in user_data:
            if 'base_image_path' in user_data[user_id]:
                 temp_files_to_remove.append(user_data[user_id]['base_image_path'])
            del user_data[user_id]
            print(f"Cleared data for user {user_id} due to error.")

    finally:
        # پاک کردن تمام فایل‌های موقتی که در این پردازش استفاده شدند
        cleanup_files(temp_files_to_remove)
        print(f"--- Finished processing for user {user_id} ---")


if __name__ == "__main__":
    print("Bot starting...")
    try:
        app.run()
    except Exception as e:
        print(f"Error running the bot: {e}")
    print("Bot stopped.")
