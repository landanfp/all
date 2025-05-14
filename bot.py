# bot.py
from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import time
from flask import Flask
from threading import Thread
from watermark import process_video_with_watermark, generate_thumbnail, get_video_duration, get_video_dimensions
from display import progress_bar

# اطلاعات ربات (لطفاً با مقادیر واقعی خود جایگزین کنید)
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# وب‌سرور ساده برای health check
flask_app = Flask(__name__)
@flask_app.route("/")
def home_route():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text("سلام! برای افزودن واترمارک به ویدیوی خود، آن را برای من ارسال کنید.")

@app.on_message(filters.video & filters.private)
async def add_watermark(client: Client, message: Message):
    status = await message.reply("در حال آماده‌سازی...")
    temp_input_path, temp_output_path, thumbnail_file_path = None, None, None

    # ایجاد دایرکتوری موقت برای فایل‌ها
    temp_dir = os.path.join("downloads", str(message.chat.id), str(message.id))
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    try:
        start_time = time.time()

        await status.edit("در حال دانلود فایل...")
        # نام فایل ورودی با استفاده از message.id برای جلوگیری از تداخل
        input_filename = f"input_{message.video.file_unique_id}{os.path.splitext(message.video.file_name)[-1] if message.video.file_name else '.mp4'}"
        temp_input_path = await message.download(
            file_name=os.path.join(temp_dir, input_filename),
            in_memory=False,
            progress=progress_bar,
            progress_args=(status, "در حال دانلود...", start_time)
        )
        if not temp_input_path or not os.path.exists(temp_input_path):
            return await status.edit("خطا در دانلود فایل.")

        base, ext = os.path.splitext(os.path.basename(temp_input_path))
        temp_output_filename = f"wm_{base}{ext}"
        temp_output_path = os.path.join(temp_dir, temp_output_filename)

        await status.edit("در حال افزودن واترمارک...")
        await process_video_with_watermark(temp_input_path, temp_output_path, status, start_time)

        if not os.path.isfile(temp_output_path):
            return await status.edit(f"فایل خروجی پس از واترمارک ایجاد نشد.")

        await status.edit("در حال تولید تامبنیل...")
        try:
            thumbnail_file_path = await generate_thumbnail(temp_output_path, temp_dir) # تامبنیل در همان دایرکتوری موقت
            if thumbnail_file_path: await status.edit("تامبنیل با موفقیت تولید شد.")
            else: await status.edit("خطا در تولید تامبنیل، آپلود بدون تامبنیل سفارشی انجام می‌شود.")
        except Exception as e_thumb:
            await status.edit("خطا در تولید تامبنیل، آپلود بدون تامبنیل سفارشی انجام می‌شود.")
            thumbnail_file_path = None

        upload_start_time = time.time()
        await status.edit("در حال آپلود فایل واترمارک‌دار...")

        caption_text = "✅ ویدیو با واترمارک ارسال شد."
        video_duration_for_upload = await get_video_duration(temp_output_path)
        video_width, video_height = await get_video_dimensions(temp_output_path)

        try:
            await message.reply_video(
                video=temp_output_path, caption=caption_text, supports_streaming=True,
                duration=int(video_duration_for_upload) if video_duration_for_upload and video_duration_for_upload > 0 else 0,
                width=video_width if video_width > 0 else 0, height=video_height if video_height > 0 else 0,
                thumb=thumbnail_file_path,
                progress=progress_bar, progress_args=(status, "در حال آپلود...", upload_start_time)
            )
            await status.delete()
            print("✅ پردازش و ارسال ویدیو با موفقیت انجام شد.")
        except Exception as e:
            await status.edit(f"خطا در آپلود فایل: {str(e)}")
    except Exception as e:
        await status.edit(f"خطا در پردازش: {str(e)}")
    finally:
        # پاکسازی فایل‌های موقت و دایرکتوری
        if thumbnail_file_path and os.path.exists(thumbnail_file_path):
            try: os.remove(thumbnail_file_path)
            except Exception: pass
        if temp_output_path and os.path.exists(temp_output_path):
            try: os.remove(temp_output_path)
            except Exception: pass
        if temp_input_path and os.path.exists(temp_input_path):
            try: os.remove(temp_input_path)
            except Exception: pass

        try:
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
            elif os.path.exists(temp_dir):
                pass # دایرکتوری غیر خالی است، حذف نمی‌شود
        except Exception:
            pass

if __name__ == "__main__":
    if not os.path.exists("downloads"): # اطمینان از وجود دایرکتوری دانلودها در شروع
        os.makedirs("downloads")

    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("ربات واترمارک در حال اجرا است...")
    app.run()
