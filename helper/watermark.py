# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - فیکس ۱۰۰%: progress time-based تخمینی, پیام مستقیم)
import asyncio
import os
import subprocess
import shlex
import json
import time
from pyrogram.types import Message
from helper.progress import progress_bar  # import صریح

async def get_video_duration(input_path):
    """استخراج duration ویدیو با ffprobe (به ثانیه)."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'json', input_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        data = json.loads(stdout.decode())
        duration = float(data['format']['duration'])  # به ثانیه
        return duration
    except Exception as e:
        print(f"Duration fetch error: {e}")
        return None

async def update_watermark_progress(message, start_time, total_duration):
    """update progress هر 5s بر اساس زمان گذشته (تخمینی linear)."""
    now = time.time()
    elapsed = now - start_time
    percentage = min((elapsed / total_duration) * 100, 100) if total_duration else 0
    await progress_bar(percentage * total_duration / 100 * 10, total_duration * 10, message, start_time, "watermark")  # Fake current for bar
    if percentage < 100:
        asyncio.create_task(asyncio.sleep(5))
        await update_watermark_progress(message, start_time, total_duration)

async def add_text_watermark(input_path, output_path, text, position, size_percent, message: Message = None, start_time: float = None):
    """افزودن واترمارک متنی (progress time-based)."""
    if not os.path.exists(input_path):
        raise Exception(f"فایل ورودی پیدا نشد: {input_path}")

    position_map = {
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

    safe_text = shlex.quote(text)
    drawtext = (
        f"drawtext=text={safe_text}:fontcolor=white@0.8:"
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}"
    )

    cmd = [
        'ffmpeg', '-i', input_path, '-vf', drawtext,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-map', '0:v:0', '-map', '0:a:0?', output_path, '-y'
    ]  # حذف -progress pipe:1
    
    try:
        total_duration = await get_video_duration(input_path)
        if message and start_time:
            await message.edit("⚙️ در حال افزودن واترمارک...")  # پیام مستقیم

        # شروع progress loop
        progress_loop = None
        if message and total_duration:
            progress_loop = asyncio.create_task(update_watermark_progress(message, start_time, total_duration))

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if progress_loop:
            await progress_loop  # منتظر loop

        if process.returncode != 0:
            error_output = stderr.decode('utf-8', errors='ignore')
            print(f"FFmpeg Text Error Full: {error_output}")
            raise Exception(f"FFmpeg failed (Text): {error_output[:300]}...")

        if message:
            await message.edit("✅ واترمارک متنی اضافه شد!")

    except Exception as e:
        raise Exception(f"Text watermark error: {e}")

async def add_image_watermark(input_path, output_path, image_path, position, size_percent, message: Message = None, start_time: float = None):
    """افزودن واترمارک تصویری (progress time-based)."""
    if not os.path.exists(input_path) or not os.path.exists(image_path):
        raise Exception(f"فایل‌ها پیدا نشد: ویدیو={input_path}, تصویر={image_path}")

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

    # ساده filter: scale + format alpha + overlay
    filter_complex = (
        f"[1:v]scale=iw*{size_percent}/100:ih*{size_percent}/100,format=argb[wm];"
        f"[0:v][wm]overlay={position_map[position]}"
    )

    cmd = [
        'ffmpeg', '-i', input_path, '-i', image_path,
        '-filter_complex', filter_complex,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-map', '0:v:0', '-map', '0:a:0?', '-movflags', '+faststart', output_path, '-y'
    ]  # حذف pipe, map [outv] چون overlay مستقیم

    print(f"Debug FFmpeg Cmd: {' '.join(cmd)}")

    try:
        total_duration = await get_video_duration(input_path)
        if message and start_time:
            await message.edit("⚙️ در حال افزودن واترمارک...")  # مستقیم, بدون آماده‌سازی

        # شروع progress loop
        progress_loop = None
        if message and total_duration:
            progress_loop = asyncio.create_task(update_watermark_progress(message, start_time, total_duration))

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if progress_loop:
            await progress_loop

        if process.returncode != 0:
            error_output = stderr.decode('utf-8', errors='ignore')
            print(f"FFmpeg Image Error Full: {error_output}")
            raise Exception(f"FFmpeg failed (Image): {error_output[:300]}...")

        if message:
            await message.edit("✅ واترمارک تصویری اضافه شد!")

    except Exception as e:
        raise Exception(f"Image watermark error: {e}")
