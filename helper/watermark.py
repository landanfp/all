# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - نسخه پیشرفته با نمایش پیشرفت)
import asyncio
import os
import subprocess
import shlex
import re
import time
from pyrogram.types import Message

# --- توابع کمکی جدید ---

async def get_video_duration(video_path):
    """
    مدت زمان کل ویدیو را با ffprobe به ثانیه برمی‌گرداند.
    """
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0 and stdout:
            return float(stdout.decode().strip())
        else:
            # نمایش خطای کامل FFprobe
            print(f"FFprobe Error: {stderr.decode()}")
            return 0.0
    except Exception as e:
        print(f"Error getting duration: {e}")
        return 0.0

def parse_ffmpeg_time(time_str):
    """
    رشته زمان 'HH:MM:SS.ms' را به ثانیه تبدیل می‌کند.
    """
    parts = time_str.split(':')
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    return (hours * 3600) + (minutes * 60) + seconds

def human_readable_time(seconds):
    """
    ثانیه را به فرمت خوانا (M:SS یا H:MM:SS) تبدیل می‌کند.
    """
    if seconds < 0:
        return "0:00"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

# --- Regex برای پارس کردن خروجی FFmpeg ---
TIME_REGEX = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

# --- توابع اصلی واترمارک (اصلاح شده) ---

# FONT_FILE_PATH حذف شد. FFmpeg از فونت پیش‌فرض سیستم استفاده خواهد کرد.

async def add_text_watermark(input_path, output_path, text, position, size_percent, msg: Message):
    """
    افزودن واترمارک متنی با نمایش پیشرفت زنده.
    """
    
    # 1. گرفتن مدت زمان کل ویدیو
    total_duration = await get_video_duration(input_path)
    if total_duration == 0.0:
        raise Exception("خطا در خواندن مدت زمان ویدیو. (فایل ورودی خراب است؟)")

    position_map = {
        "top_right": "main_w-text_w-20:20", "top_center": "(main_w-text_w)/2:20", "top_left": "20:20",
        "center_right": "main_w-text_w-20:(main_h-text_h)/2", "center": "(main_w-text_w)/2:(main_h-text_h)/2", "center_left": "20:(main_h-text_h)/2",
        "bottom_right": "main_w-text_w-20:main_h-text_h-20", "bottom_center": "(main_w-text_w)/2:main_h-text_h-20", "bottom_left": "20:main_h-text_h-20"
    }
    safe_text = shlex.quote(text)
    
    # اصلاح ۱: حذف fontfile برای استفاده از فونت پیش‌فرض
    drawtext = (
        f"drawtext=text={safe_text}:fontcolor=white@0.8:"
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}"
    )

    # اصلاح ۲: اضافه شدن -c:a aac برای انکود مجدد صدا
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? -c:a aac \"{output_path}\" -y"
    )

    # 2. اجرای FFmpeg با stderr=PIPE تا بتوانیم خروجی را بخوانیم
    process = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stderr=asyncio.subprocess.PIPE
    )

    last_update = 0
    processing_start = time.time()
    error_output = ""

    # 3. حلقه خواندن خروجی FFmpeg
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8').strip()
        error_output += line_str + "\n"
        
        match = TIME_REGEX.search(line_str)
        if match:
            current_time_str = match.group(1)
            current_time_sec = parse_ffmpeg_time(current_time_str)
            
            # جلوگیری از آپدیت‌های مکرر (هر 3 ثانیه یکبار)
            now = time.time()
            if now - last_update > 3:
                percentage = (current_time_sec / total_duration) * 100
                
                # محاسبه زمان باقیمانده (ETA)
                elapsed_time = now - processing_start
                speed_factor = current_time_sec / elapsed_time if elapsed_time > 0 else 0
                remaining_video_time = total_duration - current_time_sec
                eta_seconds = (remaining_video_time / speed_factor) if speed_factor > 0 else 0
                
                # ساخت نوار پیشرفت
                filled_blocks = int(percentage // 10)
                bar = f"[{'█' * filled_blocks}{'░' * (10 - filled_blocks)}]"
                
                progress_text = (
                    f"**⚙️ در حال پردازش واترمارک...**\n"
                    f"{percentage:.1f}% {bar}\n"
                    f"مدت زمان باقی تا اتمام: {human_readable_time(eta_seconds)}"
                )
                
                try:
                    await msg.edit(progress_text)
                    last_update = now
                except Exception:
                    pass

    await process.wait()

    # اصلاح ۳: نمایش خطای کامل
    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {error_output}") 


async def add_image_watermark(input_path, output_path, image_path, position, size_percent, msg: Message):
    """
    افزودن واترمارک تصویری با نمایش پیشرفت زنده.
    """
    
    # 1. گرفتن مدت زمان کل ویدیو
    total_duration = await get_video_duration(input_path)
    if total_duration == 0.0:
        raise Exception("خطا در خواندن مدت زمان ویدیو. (فایل ورودی خراب است؟)")

    position_map = {
        "top_right": "main_w-overlay_w-20:20", "top_center": "(main_w-overlay_w)/2:20", "top_left": "20:20",
        "center_right": "main_w-overlay_w-20:(main_h-overlay_h)/2", "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2", "center_left": "20:(main_h-overlay_h)/2",
        "bottom_right": "main_w-overlay_w-20:main_h-overlay_h-20", "bottom_center": "(main_w-overlay_w)/2:main_h-overlay_h-20", "bottom_left": "20:main_h-overlay_h-20"
    }

    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva420p[wm];"
        f"[v][wm]overlay={position_map[position]}[ov];"
        f"[ov]format=yuv420p[outv]"
    )

    # اصلاح ۴: اضافه شدن -c:a aac برای انکود مجدد صدا
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 -g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -c:a aac -metadata:s:v:0 rotate=0 \"{output_path}\" -y"
    )

    # 2. اجرای FFmpeg با stderr=PIPE
    process = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stderr=asyncio.subprocess.PIPE
    )

    last_update = 0
    processing_start = time.time()
    error_output = ""

    # 3. حلقه خواندن خروجی FFmpeg
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8').strip()
        error_output += line_str + "\n"
        
        match = TIME_REGEX.search(line_str)
        if match:
            current_time_str = match.group(1)
            current_time_sec = parse_ffmpeg_time(current_time_str)
            
            now = time.time()
            if now - last_update > 3:
                percentage = (current_time_sec / total_duration) * 100
                
                elapsed_time = now - processing_start
                speed_factor = current_time_sec / elapsed_time if elapsed_time > 0 else 0
                remaining_video_time = total_duration - current_time_sec
                eta_seconds = (remaining_video_time / speed_factor) if speed_factor > 0 else 0
                
                filled_blocks = int(percentage // 10)
                bar = f"[{'█' * filled_blocks}{'░' * (10 - filled_blocks)}]"
                
                progress_text = (
                    f"**⚙️ در حال پردازش واترمارک...**\n"
                    f"{percentage:.1f}% {bar}\n"
                    f"مدت زمان باقی تا اتمام: {human_readable_time(eta_seconds)}"
                )
                
                try:
                    await msg.edit(progress_text)
                    last_update = now
                except Exception:
                    pass

    await process.wait()

    # اصلاح ۵: نمایش خطای کامل
    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {error_output}")
