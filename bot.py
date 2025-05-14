from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import time
import math
# import subprocess # به طور مستقیم استفاده نمی‌شود
from flask import Flask
from threading import Thread
import json

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

# تبدیل حجم
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    try:
        i = int(math.floor(math.log(size_bytes, 1024)))
        if i < 0: i = 0
    except ValueError:
        i = 0
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# نوار پیشرفت
async def progress_bar(
    current_val, total_val, status_message, action, start,
    display_bytes_current=None, display_bytes_total=None
):
    now = time.time()
    diff = now - start if now - start > 0 else 0.001
    percentage = current_val * 100 / total_val if total_val > 0 else 0
    speed = current_val / diff if diff > 0 else 0
    
    elapsed_time = round(diff)
    eta = round((total_val - current_val) / speed) if speed > 0 and total_val > 0 else 0
    
    if current_val >= total_val and total_val > 0 :
        percentage = 100.00
        eta = 0
        
    bar_length = 15
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    lines = [
        action,
        f"[{bar}] {percentage:.2f}%"
    ]

    size_text_line = ""
    if (action.startswith("در حال دانلود") or action.startswith("در حال آپلود")) and total_val > 0:
        size_text_line = f"• حجم: {convert_size(current_val)} / {convert_size(total_val)}"
    elif display_bytes_current is not None and display_bytes_total is not None and display_bytes_total > 0:
         current_bytes_to_display = min(display_bytes_current, display_bytes_total)
         size_text_line = f"• حجم: {convert_size(current_bytes_to_display)} / {convert_size(display_bytes_total)}"

    if size_text_line:
        lines.append(size_text_line)
    
    lines.extend([
        f"• سرعت: {convert_size(speed)}/s",
        f"• زمان سپری‌شده: {elapsed_time}s",
        f"• زمان باقی‌مانده: {eta}s"
    ])
    text = "\n".join(lines)

    try:
        if hasattr(status_message, 'text') and status_message.text != text:
            await status_message.edit(text)
        elif not hasattr(status_message, 'text'):
             await status_message.edit(text)
    except Exception:
        pass

async def get_video_duration(video_path):
    if not video_path or not os.path.exists(video_path): # بررسی وجود فایل
        print(f"فایل ویدیو برای get_video_duration یافت نشد: {video_path}")
        return None
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
                elif 'duration' in data: # برای برخی فرمت‌های json دیگر
                     return float(data['duration'])
            except json.JSONDecodeError:
                print(f"خطا در تجزیه JSON از ffprobe (duration): {stdout.decode()}")

        # Fallback if JSON parsing fails or no duration found
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
            try:
                return float(stdout_fallback.decode().strip())
            except ValueError:
                 print(f"خطا در تبدیل خروجی ffprobe (default) به float: {stdout_fallback.decode().strip()}")
        else:
            # پرینت stderr اصلی اگر fallback هم شکست خورد
            print(f"خطا در دریافت مدت زمان با ffprobe (default): {stderr.decode() if stderr else (stderr_fallback.decode() if stderr_fallback else 'N/A')}")
            
    except FileNotFoundError:
        print("خطا: ffprobe پیدا نشد. لطفاً از نصب بودن FFmpeg (شامل ffprobe) و در دسترس بودن آن در PATH اطمینان حاصل کنید.")
    except Exception as e:
        print(f"استثنا در get_video_duration ({video_path}): {e}")
    return None

async def get_video_dimensions(video_path):
    if not video_path or not os.path.exists(video_path):
        print(f"فایل ویدیو برای get_video_dimensions یافت نشد: {video_path}")
        return 0, 0
    try:
        command = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", video_path
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
                if data.get("streams") and len(data["streams"]) > 0:
                    stream_data = data["streams"][0]
                    return stream_data.get("width", 0), stream_data.get("height", 0)
            except json.JSONDecodeError:
                print(f"خطا در تجزیه JSON از ffprobe (dimensions): {stdout.decode()}")
        print(f"خطا در دریافت ابعاد ویدیو (ffprobe json): {stderr.decode() if stderr else 'N/A'}")
    except FileNotFoundError:
        print("خطا: ffprobe پیدا نشد.")
    except Exception as e:
        print(f"استثنا در get_video_dimensions ({video_path}): {e}")
    return 0, 0

async def generate_thumbnail(video_path, output_dir, seek_time_str="00:00:03.000"):
    if not video_path or not os.path.exists(video_path):
        print(f"فایل ویدیو برای generate_thumbnail یافت نشد: {video_path}")
        return None
        
    thumbnail_filename = os.path.splitext(os.path.basename(video_path))[0] + ".jpg"
    thumbnail_path = os.path.join(output_dir, thumbnail_filename)

    current_seek_time = seek_time_str
    duration = await get_video_duration(video_path)

    if duration is not None and duration > 0:
        try:
            h, m, s_full = current_seek_time.split(':')
            s, ms_str = s_full.split('.') if '.' in s_full else (s_full, "0")
            seek_seconds_requested = int(h) * 3600 + int(m) * 60 + float(s) + float(ms_str) / 1000
            
            if seek_seconds_requested >= duration or seek_seconds_requested < 0:
                seek_seconds_actual = duration / 4.0
            else:
                seek_seconds_actual = seek_seconds_requested
            
            seek_s_int = int(seek_seconds_actual)
            seek_ms_int = int((seek_seconds_actual - seek_s_int) * 1000)
            current_seek_time = f"{seek_s_int // 3600:02d}:{ (seek_s_int % 3600) // 60:02d}:{seek_s_int % 60:02d}.{seek_ms_int:03d}"
        except ValueError:
            print(f"فرمت seek_time نامعتبر: {current_seek_time}. استفاده از مقدار پیش‌فرض یا ۱/۴ مدت زمان.")
            seek_seconds_default = min(3.0, duration / 4.0 if duration > 0 else 3.0)
            seek_s_def = int(seek_seconds_default)
            seek_ms_def = int((seek_seconds_default - seek_s_def) * 1000)
            current_seek_time = f"{seek_s_def // 3600:02d}:{(seek_s_def % 3600) // 60:02d}:{seek_s_def % 60:02d}.{seek_ms_def:03d}"
    else:
        print("امکان دریافت مدت زمان ویدیو برای تامبنیل نبود، از زمان جستجوی پیش‌فرض استفاده می‌شود.")

    command = [
        "ffmpeg", "-y",
        "-ss", current_seek_time,
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "3",
        thumbnail_path
    ]
    print(f"در حال تولید تامبنیل با دستور: {' '.join(command)}")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
        print(f"تامبنیل با موفقیت تولید شد: {thumbnail_path}")
        return thumbnail_path
    else:
        print(f"خطا در تولید تامبنیل برای {video_path}:")
        if stdout: print(f"FFmpeg STDOUT: {stdout.decode(errors='ignore')}")
        if stderr: print(f"FFmpeg STDERR: {stderr.decode(errors='ignore')}")
        return None

async def process_video_with_watermark(input_path, output_path, status_message, start_time_overall):
    total_duration_seconds = await get_video_duration(input_path)

    if total_duration_seconds is None:
        total_duration_seconds = 0 
        print("هشدار: دریافت مدت زمان ویدیو ممکن نبود.")

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

    while True:
        line_bytes = await process.stdout.readline()
        if not line_bytes:
            break
        line = line_bytes.decode('utf-8', errors='ignore').strip()
        current_time_seconds = None
        if line.startswith("out_time_us="):
            try: microseconds = int(line.split('=')[1]); current_time_seconds = microseconds / 1000000.0
            except ValueError: print(f"ناتوان در تجزیه out_time_us: {line}")
        elif line.startswith("out_time_ms="):
            try: milliseconds = int(line.split('=')[1]); current_time_seconds = milliseconds / 1000.0
            except ValueError: print(f"ناتوان در تجزیه out_time_ms: {line}")
        
        if current_time_seconds is not None and total_duration_seconds > 0:
            if time.time() - last_update_time > 5.0: 
                await progress_bar(current_time_seconds, total_duration_seconds, status_message, "در حال افزودن واترمارک...", start_time_overall)
                last_update_time = time.time()
        elif line.startswith("progress=end"):
            if total_duration_seconds > 0:
                await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک در حال اتمام...", start_time_overall)
            print("پیشرفت FFmpeg پایان یافت.")

    stdout_data, stderr_data = await process.communicate()
    if stderr_data: print(f"FFmpeg STDERR: {stderr_data.decode('utf-8', errors='ignore')}")

    if process.returncode != 0:
        error_message_detail = stderr_data.decode('utf-8', errors='ignore') if stderr_data else "جزئیات بیشتر در دسترس نیست."
        error_message = f"خطا در پردازش ویدیو با FFmpeg. کد بازگشت: {process.returncode}\nجزئیات: {error_message_detail[:1000]}"
        try: await status_message.edit(error_message)
        except Exception as e_edit: print(f"خطا در ویرایش پیام وضعیت (حین خطای ffmpeg): {e_edit}")
        raise Exception(error_message)
    else:
        if total_duration_seconds > 0:
            await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک کامل شد.", start_time_overall)
        else: 
            final_output_size_str = ""
            if os.path.exists(output_path): final_output_size_str = f" حجم فایل خروجی: {convert_size(os.path.getsize(output_path))}"
            await status_message.edit(f"واترمارک کامل شد.{final_output_size_str}")

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
            print(f"استثنا هنگام تولید تامبنیل: {e_thumb}")
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
        except Exception as e:
            print(f"خطا در آپلود فایل: {e}"); await status.edit(f"خطا در آپلود فایل: {str(e)}")
    except Exception as e:
        print(f"خطا در پردازش کلی: {e}")
        if status:
            try: await status.edit(f"خطا در پردازش: {str(e)}")
            except: pass
    finally:
        # پاکسازی فایل‌های موقت و دایرکتوری
        # ابتدا فایل‌ها، سپس دایرکتوری اگر خالی باشد
        if thumbnail_file_path and os.path.exists(thumbnail_file_path):
            try: os.remove(thumbnail_file_path); print(f"فایل تامبنیل موقت حذف شد: {thumbnail_file_path}")
            except Exception as e_rem: print(f"خطا در حذف تامبنیل: {e_rem}")
        if temp_output_path and os.path.exists(temp_output_path):
            try: os.remove(temp_output_path); print(f"فایل خروجی موقت حذف شد: {temp_output_path}")
            except Exception as e_rem: print(f"خطا در حذف خروجی: {e_rem}")
        if temp_input_path and os.path.exists(temp_input_path):
            try: os.remove(temp_input_path); print(f"فایل ورودی موقت حذف شد: {temp_input_path}")
            except Exception as e_rem: print(f"خطا در حذف ورودی: {e_rem}")
        
        # تلاش برای حذف دایرکتوری موقت اگر خالی باشد
        try:
            if os.path.exists(temp_dir) and not os.listdir(temp_dir): # اگر خالی است
                os.rmdir(temp_dir)
                print(f"دایرکتوری موقت حذف شد: {temp_dir}")
            elif os.path.exists(temp_dir): # اگر خالی نیست، هشدار بده
                 print(f"هشدار: دایرکتوری موقت {temp_dir} خالی نیست و حذف نشد.")
        except Exception as e_rmdir:
            print(f"خطا در حذف دایرکتوری موقت {temp_dir}: {e_rmdir}")


if __name__ == "__main__":
    if not os.path.exists("downloads"): # اطمینان از وجود دایرکتوری دانلودها در شروع
        os.makedirs("downloads")
        
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("ربات واترمارک در حال اجرا است...")
    app.run()
