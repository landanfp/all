from pyrogram import Client, filters
from pyrogram.types import Message
import os
import asyncio
import time
import math
# import subprocess
from flask import Flask
from threading import Thread
import json

# اطلاعات ربات (لطفاً با مقادیر واقعی خود جایگزین کنید)
API_ID = os.environ.get('API_ID', '3335796')
API_HASH = os.environ.get('API_HASH', '138b992a0e672e8346d8439c3f42ea78')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8')

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

# نوار پیشرفت اصلاح‌شده
async def progress_bar(
    current_val, total_val, status_message, action, start,
    # آرگومان‌های display_bytes دیگر به طور فعال توسط واترمارک استفاده نمی‌شوند
    # اما برای حفظ امضا و سازگاری احتمالی آینده باقی می‌مانند.
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
    # نمایش خط "حجم" فقط برای عملیات دانلود و آپلود
    if (action.startswith("در حال دانلود") or action.startswith("در حال آپلود")) and total_val > 0:
        # در این حالت‌ها، current_val و total_val مقادیر بایت هستند
        size_text_line = f"• حجم: {convert_size(current_val)} / {convert_size(total_val)}"
    # اگر display_bytes_current و display_bytes_total به صراحت پاس داده شوند (که دیگر برای واترمارک اینطور نیست)
    # می‌توانستیم آن را نیز مدیریت کنیم، اما طبق درخواست جدید، برای واترمارک حجمی نمایش داده نمی‌شود.
    elif display_bytes_current is not None and display_bytes_total is not None and display_bytes_total > 0:
         current_bytes_to_display = min(display_bytes_current, display_bytes_total)
         size_text_line = f"• حجم: {convert_size(current_bytes_to_display)} / {convert_size(display_bytes_total)}"

    if size_text_line:
        lines.append(size_text_line)
    
    lines.extend([
        f"• سرعت: {convert_size(speed)}/s", # برای FFmpeg، این "نرخ پردازش" را به شکل بایت نمایش می‌دهد
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
                elif 'duration' in data:
                     return float(data['duration'])
            except json.JSONDecodeError:
                print(f"خطا در تجزیه JSON از ffprobe: {stdout.decode()}")

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
    # متغیر ffmpeg_current_output_bytes دیگر برای نمایش حجم در نوار پیشرفت واترمارک لازم نیست

    while True:
        line_bytes = await process.stdout.readline()
        if not line_bytes:
            break
        
        line = line_bytes.decode('utf-8', errors='ignore').strip()
        
        current_time_seconds = None
        
        if line.startswith("out_time_us="):
            try:
                microseconds = int(line.split('=')[1])
                current_time_seconds = microseconds / 1000000.0
            except ValueError:
                print(f"ناتوان در تجزیه out_time_us: {line}")
        elif line.startswith("out_time_ms="):
            try:
                milliseconds = int(line.split('=')[1])
                current_time_seconds = milliseconds / 1000.0
            except ValueError:
                print(f"ناتوان در تجزیه out_time_ms: {line}")
        # تجزیه total_size دیگر برای نمایش در نوار پیشرفت لازم نیست
        # elif line.startswith("total_size="):
        #     pass 
        
        if current_time_seconds is not None and total_duration_seconds > 0:
            if time.time() - last_update_time > 5.0: # به‌روزرسانی هر ۵ ثانیه
                await progress_bar(
                    current_time_seconds, total_duration_seconds, 
                    status_message, "در حال افزودن واترمارک...", start_time_overall
                    # آرگومان‌های display_bytes ارسال نمی‌شوند
                )
                last_update_time = time.time()
        
        elif line.startswith("progress=end"):
            if total_duration_seconds > 0:
                await progress_bar(
                    total_duration_seconds, total_duration_seconds,
                    status_message, "واترمارک در حال اتمام...", start_time_overall
                    # آرگومان‌های display_bytes ارسال نمی‌شوند
                )
            print("پیشرفت FFmpeg پایان یافت.")

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
            await progress_bar(
                total_duration_seconds, total_duration_seconds,
                status_message, "واترمارک کامل شد.", start_time_overall
                # آرگومان‌های display_bytes ارسال نمی‌شوند
            )
        else: 
            final_output_size_str = ""
            if os.path.exists(output_path):
                final_output_size_str = f" حجم فایل خروجی: {convert_size(os.path.getsize(output_path))}"
            await status_message.edit(f"واترمارک کامل شد.{final_output_size_str}")


@app.on_message(filters.video & filters.private)
async def add_watermark(client: Client, message: Message):
    status = await message.reply("در حال آماده‌سازی...")
    temp_input_path, temp_output_path = None, None
    try:
        start_time = time.time()

        await status.edit("در حال دانلود فایل...")
        temp_input_path = await message.download(
            in_memory=False,
            progress=progress_bar,
            progress_args=(status, "در حال دانلود...", start_time) 
        )
        if not temp_input_path or not os.path.exists(temp_input_path):
            return await status.edit("خطا در دانلود فایل.")

        base, ext = os.path.splitext(os.path.basename(temp_input_path))
        temp_output_path = f"wm_{base}{ext}"

        await status.edit("در حال افزودن واترمارک...") 
        await process_video_with_watermark(temp_input_path, temp_output_path, status, start_time)

        if not os.path.isfile(temp_output_path):
            return await status.edit(f"فایل خروجی پس از واترمارک ایجاد نشد. مسیر مورد انتظار: {temp_output_path}")

        upload_start_time = time.time()
        await status.edit("در حال آپلود فایل واترمارک‌دار...")
        
        caption_text = "✅ ویدیو با واترمارک ارسال شد."

        try:
            await message.reply_video(
                video=temp_output_path,
                caption=caption_text,
                supports_streaming=True,
                progress=progress_bar,
                progress_args=(status, "در حال آپلود...", upload_start_time) 
            )
            await status.delete()
        except Exception as e:
            print(f"خطا در آپلود فایل: {e}")
            await status.edit(f"خطا در آپلود فایل: {str(e)}")

    except Exception as e:
        print(f"خطا در پردازش کلی: {e}")
        if status :
            try:
                await status.edit(f"خطا در پردازش: {str(e)}")
            except: # ممکن است پیام قبلا حذف شده باشد یا خطای دیگری رخ دهد
                pass

    finally:
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
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("ربات واترمارک در حال اجرا است...")
    app.run()
