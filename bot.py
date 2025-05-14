from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import time
import math
import subprocess # اگرچه مستقیماً استفاده نمی‌شود، اما برای آگاهی از وابستگی‌های احتمالی ffmpeg خوب است.
from flask import Flask
from threading import Thread
import json # برای تفسیر خروجی جیسون از ffprobe

# اطلاعات ربات
API_ID = '3335796' # لطفاً این مقادیر را با مقادیر واقعی خود جایگزین کنید
API_HASH = '138b992a0e672e8346d8439c3f42ea78' # لطفاً این مقادیر را با مقادیر واقعی خود جایگزین کنید
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8' # لطفاً این مقادیر را با مقادیر واقعی خود جایگزین کنید

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# وب‌سرور ساده برای health check در Koyeb
flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=os.environ.get("PORT", 8000)) # استفاده از پورت Koyeb یا پیش‌فرض

# تبدیل حجم
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# نوار پیشرفت
async def progress_bar(current, total, status_message, action, start):
    now = time.time()
    diff = now - start if now - start > 0 else 0.001 # جلوگیری از تقسیم بر صفر یا مقادیر منفی
    percentage = current * 100 / total if total > 0 else 0
    speed = current / diff if diff > 0 else 0
    elapsed_time = round(diff)
    eta = round((total - current) / speed) if speed > 0 and total > 0 else 0
    
    # اطمینان از اینکه current از total بیشتر نشود (برای نمایش 100%)
    if current >= total and total > 0 :
        percentage = 100.00
        eta = 0
        
    bar_length = 15
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    text = f"""
{action}
[{bar}] {percentage:.2f}%
• حجم: {convert_size(current if total > 0 else 0)} / {convert_size(total if total > 0 else 0)}
• سرعت: {convert_size(speed)}/s
• زمان سپری‌شده: {elapsed_time}s
• زمان باقی‌مانده: {eta}s
"""
    try:
        # جلوگیری از ویرایش پیام با متن یکسان برای کاهش بار API
        if status_message.text != text:
            await status_message.edit(text)
    except Exception as e:
        # print(f"خطا در به‌روزرسانی نوار پیشرفت: {e}") # برای دیباگ
        pass

# تابع جدید برای دریافت مدت زمان ویدیو
async def get_video_duration(video_path):
    """مدت زمان ویدیو را به ثانیه با استفاده از ffprobe دریافت می‌کند."""
    try:
        command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", video_path
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0 and stdout:
            try:
                data = json.loads(stdout.decode())
                if 'format' in data and 'duration' in data['format']:
                    return float(data['format']['duration'])
                elif 'duration' in data: # بررسی مستقیم کلید duration
                     return float(data['duration'])
            except json.JSONDecodeError:
                print(f"خطا در تجزیه JSON از ffprobe: {stdout.decode()}")

        # تلاش مجدد با فرمت خروجی دیگر در صورت عدم موفقیت فرمت json
        # این بخش برای اطمینان بیشتر است
        print(f"تلاش با فرمت default برای ffprobe. خطای قبلی (اگر بود): {stderr.decode() if stderr else 'N/A'}")
        command_fallback = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        process_fallback = await asyncio.create_subprocess_exec(
            *command_fallback,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_fallback, stderr_fallback = await process_fallback.communicate()
        if process_fallback.returncode == 0 and stdout_fallback:
            return float(stdout_fallback.decode().strip())
        else:
            print(f"خطا در دریافت مدت زمان با ffprobe (default): {stderr_fallback.decode() if stderr_fallback else 'N/A'}")
            
    except FileNotFoundError:
        print("خطا: ffprobe پیدا نشد. لطفاً از نصب بودن FFmpeg (شامل ffprobe) و در دسترس بودن آن در PATH اطمینان حاصل کنید.")
    except Exception as e:
        print(f"استثنا در get_video_duration: {e}")
    return None

# تابع اصلاح‌شده برای پردازش ویدیو با واترمارک
async def process_video_with_watermark(input_path, output_path, status_message, start_time_overall):
    total_duration_seconds = await get_video_duration(input_path)

    if total_duration_seconds is None:
        total_duration_seconds = 0 
        print("هشدار: دریافت مدت زمان ویدیو ممکن نبود. نوار پیشرفت برای واترمارک ممکن است درصد یا زمان باقی‌مانده را دقیق نشان ندهد.")

    command = [
        "ffmpeg", "-hide_banner", "-i", input_path,
        "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,20)'",
        "-codec:a", "copy",
        "-progress", "pipe:1",
        "-y",
        output_path
    ]
    
    print(f"دستور FFmpeg: {' '.join(command)}")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    last_update_time = time.time()
    # start_time_overall مربوط به شروع کل عملیات (دانلود + واترمارک) است

    while True:
        line_bytes = await process.stdout.readline()
        if not line_bytes:
            break
        
        line = line_bytes.decode('utf-8', errors='ignore').strip()
        # print(f"FFMPEG_PROGRESS_LINE: {line}") # برای دیباگ

        current_time_seconds = None
        
        if line.startswith("out_time_us="): # میکروثانیه
            try:
                microseconds = int(line.split('=')[1])
                current_time_seconds = microseconds / 1000000.0
            except ValueError:
                print(f"ناتوان در تجزیه out_time_us: {line}")
        elif line.startswith("out_time_ms="): # میلی‌ثانیه
            try:
                milliseconds = int(line.split('=')[1])
                current_time_seconds = milliseconds / 1000.0
            except ValueError:
                print(f"ناتوان در تجزیه out_time_ms: {line}")
        
        if current_time_seconds is not None and total_duration_seconds > 0:
            if time.time() - last_update_time > 1.0: # به‌روزرسانی هر ۱ ثانیه
                await progress_bar(current_time_seconds, total_duration_seconds, status_message, "در حال افزودن واترمارک...", start_time_overall)
                last_update_time = time.time()
        
        elif line.startswith("progress=end"):
            if total_duration_seconds > 0:
                 await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک در حال اتمام...", start_time_overall)
            print("پیشرفت FFmpeg پایان یافت.")
            # اجازه دهید حلقه با EOF طبیعی stdout تمام شود یا communicate() آن را مدیریت کند.

    stdout_data, stderr_data = await process.communicate()
    
    if stderr_data:
        print(f"FFmpeg STDERR: {stderr_data.decode('utf-8', errors='ignore')}")

    if process.returncode != 0:
        error_message_detail = stderr_data.decode('utf-8', errors='ignore') if stderr_data else "جزئیات بیشتر در دسترس نیست."
        error_message = f"خطا در پردازش ویدیو با FFmpeg. کد بازگشت: {process.returncode}\nجزئیات: {error_message_detail[:1000]}"
        try:
            await status_message.edit(error_message)
        except Exception as e_edit:
            print(f"خطا در ویرایش پیام وضعیت (حین خطای ffmpeg): {e_edit}")
        raise Exception(error_message)
    else:
        if total_duration_seconds > 0:
            await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک کامل شد.", start_time_overall)
        else:
            await status_message.edit("واترمارک کامل شد (پیشرفت دقیق در دسترس نبود).")


@app.on_message(filters.video & filters.private)
async def add_watermark(client: Client, message: Message):
    status = await message.reply("در حال آماده‌سازی...")
    temp_input_path, temp_output_path = None, None # مقداردهی اولیه
    try:
        start_time = time.time() # زمان شروع کل عملیات

        # دانلود فایل به دیسک
        await status.edit("در حال دانلود فایل...")
        temp_input_path = await message.download(
            in_memory=False,
            progress=progress_bar,
            progress_args=(status, "در حال دانلود...", start_time)
        )
        if not temp_input_path or not os.path.exists(temp_input_path):
            return await status.edit("خطا در دانلود فایل.")

        # تولید نام فایل خروجی در دیسک
        base, ext = os.path.splitext(os.path.basename(temp_input_path))
        temp_output_path = f"wm_{base}{ext}"


        # پردازش ویدیو با افزودن واترمارک
        await status.edit("در حال افزودن واترمارک...") # پیام اولیه قبل از شروع پردازش ffmpeg
        await process_video_with_watermark(temp_input_path, temp_output_path, status, start_time)

        # چک کردن موجود بودن فایل خروجی
        if not os.path.isfile(temp_output_path):
            # این پیام ممکن است توسط خطای ffmpeg در process_video_with_watermark پوشش داده شود
            return await status.edit(f"فایل خروجی پس از واترمارک ایجاد نشد. مسیر مورد انتظار: {temp_output_path}")

        # آپلود فایل واترمارک‌دار
        upload_start_time = time.time() # زمان شروع آپلود برای نمایش دقیق‌تر پیشرفت آپلود
        await status.edit("در حال آپلود فایل واترمارک‌دار...")
        
        try:
            await message.reply_video(
                video=temp_output_path,
                caption="✅ ویدیو با واترمارک ارسال شد.\nProcessed by @YourBotName", # نام ربات خود را جایگزین کنید
                supports_streaming=True,
                progress=progress_bar,
                progress_args=(status, "در حال آپلود...", upload_start_time) # استفاده از زمان شروع آپلود
            )
            await status.delete()
        except Exception as e:
            print(f"خطا در آپلود فایل: {e}")
            await status.edit(f"خطا در آپلود فایل: {str(e)}")

    except Exception as e:
        print(f"خطا در پردازش کلی: {e}")
        await status.edit(f"خطا در پردازش: {str(e)}")

    finally:
        # حذف فایل‌های موقت
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception as e_remove:
                print(f"خطا در حذف فایل ورودی موقت: {e_remove}")
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
            except Exception as e_remove:
                print(f"خطا در حذف فایل خروجی موقت: {e_remove}")

if __name__ == "__main__":
    # اجرای Flask در یک Thread جداگانه
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True # اطمینان از بسته شدن ترد با برنامه اصلی
    flask_thread.start()
    
    # اجرای ربات
    print("ربات واترمارک در حال اجرا است...")
    app.run()
