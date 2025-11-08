# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - نسخه متعادل)
import asyncio
import os
import subprocess
import shlex
import re # اضافه شد
import time # اضافه شد
from pyrogram.types import Message # اضافه شد
from helper.progress import format_time_progress, time_to_seconds # اضافه شد

# تعریف Regex برای استخراج زمان (time=HH:MM:SS.ms) از خروجی FFmpeg
TIME_REGEX = re.compile(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})')

async def add_text_watermark(input_path, output_path, text, position, size_percent, message: Message, duration):
    """افزودن واترمارک متنی به ویدیو با استفاده از FFmpeg (نسخه متعادل - با فونت پیش‌فرض)."""
    position_map = {
        # با اضافه کردن حاشیه 20 پیکسلی
        "top_right": "main_w-text_w-20:20",
        "top_center": "(main_w-text_w)/2:20",
        "top_left": "20:20",
        "center_right": "main_w-text_w-20:(main_h-text_h)/2",
        "center": "(main_w-text_w)/2:(main_h-text_h)/2",
        "center_left": "20:(main_h-text_h)/2",
        "bottom_right": "main_w-text_w-20:main_h-text_h-20",
        "bottom_center": "(main_w-text_w)/2:main_h-text_h-20",
        "bottom_left": "20:main_h-text_h-20"
    }

    # استفاده از shlex.quote برای ایمن سازی متن
    safe_text = shlex.quote(text)
    
    # ft_quality حذف شد و fontfile وجود ندارد.
    drawtext = (
        f"drawtext=text={safe_text}:fontcolor=white@0.8:"
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}" 
    )

    # تنظیمات متعادل: preset veryfast و crf 23
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # اجرای ایمن FFmpeg با shlex.split و افزودن نمایش پیشرفت
    start_time = time.time()
    last_edit_time = 0
    try:
        # تغییر: استفاده از PIPE برای خواندن خروجی زنده
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # خواندن خطوط خروجی FFmpeg برای نمایش پیشرفت
        while True:
            # خواندن خط جدید از خروجی خطا
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode(errors='ignore')
            
            match = TIME_REGEX.search(line_str)
            if match:
                current_time_str = match.group(1)
                current_seconds = time_to_seconds(current_time_str)
                
                now = time.time()
                # جلوگیری از Flood Wait: آپدیت هر ۳ ثانیه
                if now - last_edit_time >= 3 or current_seconds >= duration:
                    
                    progress_text = format_time_progress(current_seconds, duration, start_time)
                    
                    try:
                        await message.edit(f"⚙️ در حال افزودن واترمارک:\n{progress_text}")
                        last_edit_time = now
                    except Exception:
                        pass # نادیده گرفتن خطاهای ویرایش

        # انتظار برای اتمام پروسه و گرفتن خروجی نهایی
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_output = stderr.decode()
            print(f"FFmpeg Error (Text): {error_output}")
            # حذف محدودیت [:200] برای تشخیص کامل خطا
            raise Exception(f"FFmpeg failed: {error_output}") 

    except FileNotFoundError as e:
        if "ffmpeg" in str(e):
            raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
        else:
            raise e
    except Exception as e:
        raise Exception(f"Error during text watermark processing: {e}")

async def add_image_watermark(input_path, output_path, image_path, position, size_percent, message: Message, duration):
    """افزودن واترمارک تصویری به ویدیو با استفاده از FFmpeg (نسخه متعادل و فیکس نهایی پیش‌نمایش)."""
    position_map = {
        "top_right": "main_w-overlay_w-20:20",
        "top_center": "(main_w-overlay_w)/2:20",
        "top_left": "20:20",
        "center_right": "main_w-overlay_w-20:(main_h-overlay_h)/2",
        "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "center_left": "20:(main_h-overlay_h)/2",
        "bottom_right": "main_w-overlay_w-20:main_h-overlay_h-20",
        "bottom_center": "(main_w-overlay_w)/2:main_h-overlay_h-20",
        "bottom_left": "20:main_h-overlay_h-20"
    }

    # **اصلاح مهم: برچسب‌گذاری صریح خروجی نهایی فیلتر**
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva420p[wm];" 
        f"[v][wm]overlay={position_map[position]}[ov];"
        f"[ov]format=yuv420p[outv]" 
    )

    # **فیکس نهایی سازگاری با تلگرام و ارور:**
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " 
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y" 
    )
    
    # اجرای ایمن FFmpeg و افزودن نمایش پیشرفت
    start_time = time.time()
    last_edit_time = 0
    try:
        # تغییر: استفاده از PIPE برای خواندن خروجی زنده
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # خواندن خطوط خروجی FFmpeg برای نمایش پیشرفت
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode(errors='ignore')
            
            match = TIME_REGEX.search(line_str)
            if match:
                current_time_str = match.group(1)
                current_seconds = time_to_seconds(current_time_str)
                
                now = time.time()
                # جلوگیری از Flood Wait: آپدیت هر ۳ ثانیه
                if now - last_edit_time >= 3 or current_seconds >= duration:
                    
                    progress_text = format_time_progress(current_seconds, duration, start_time)
                    
                    try:
                        await message.edit(f"⚙️ در حال افزودن تصویر واترمارک:\n{progress_text}")
                        last_edit_time = now
                    except Exception:
                        pass # نادیده گرفتن خطاهای ویرایش

        # انتظار برای اتمام پروسه و گرفتن خروجی نهایی
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            print(f"FFmpeg Error (Image): {error_output}")
            raise Exception(f"FFmpeg failed: {error_output[:200]}...")

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        raise Exception(f"Error during image watermark processing: {e}")
