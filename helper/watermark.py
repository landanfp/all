# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - فیکس async progress بدون thread)
import asyncio
import os
import subprocess
import shlex
import json
import time
from pyrogram.types import Message

async def get_video_duration(input_path):
    """استخراج duration ویدیو با ffprobe (به میلی‌ثانیه)."""
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
        duration = float(data['format']['duration']) * 1000  # به ms
        return duration
    except Exception as e:
        print(f"Duration fetch error: {e}")
        return None

async def read_progress_async(stdout, total_ms, message, start_time):
    """خواندن progress به صورت async."""
    current_ms = 0
    last_update = time.time()
    try:
        while True:
            line = await stdout.readline()
            if not line:
                break
            line_str = line.decode().strip()
            print(f"Debug Progress: {line_str}")  # لاگ debug
            if line_str.startswith('out_time_ms='):
                try:
                    current_ms = float(line_str.split('=')[1])
                    now = time.time()
                    if (now - last_update) >= 5 or current_ms >= total_ms:
                        await progress_bar(current_ms, total_ms, message, start_time, "watermark")
                        last_update = now
                except ValueError:
                    pass
        # Final 100%
        if total_ms:
            await progress_bar(total_ms, total_ms, message, start_time, "watermark")
    except Exception as e:
        print(f"Progress read error: {e}")

async def add_text_watermark(input_path, output_path, text, position, size_percent, message: Message = None, start_time: float = None):
    """افزودن واترمارک متنی (async progress)."""
    if not os.path.exists(input_path):
        raise Exception(f"فایل ورودی پیدا نشد: {input_path}")

    position_map = {
        "top_right": "W-tw-20:20",
        "top_center": "(W-tw)/2:20",
        "top_left": "20:20",
        "center_right": "W-tw-20:(H-th)/2",
        "center": "(W-tw)/2:(H-th)/2",
        "center_left": "20:(H-th)/2",
        "bottom_right": "W-tw-20:H-th-20",
        "bottom_center": "(W-tw)/2:H-th-20",
        "bottom_left": "20:H-th-20"
    }

    safe_text = shlex.quote(text)
    drawtext = (
        f"drawtext=text={safe_text}:fontcolor=white@0.8:fontsize=H*{size_percent}/100:"
        f"shadowcolor=black@0.4:shadowx=2:shadowy=2:x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}"
    )

    cmd = [
        'ffmpeg', '-i', input_path, '-vf', drawtext,
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-map', '0:v:0', '-map', '0:a:0?', output_path, '-y',
        '-progress', 'pipe:1'
    ]
    
    try:
        total_ms = await get_video_duration(input_path)
        if message:
            await message.edit("⏳ در حال آماده‌سازی...")

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # Async progress task
        progress_task = None
        if message and total_ms:
            progress_task = asyncio.create_task(read_progress_async(process.stdout, total_ms, message, start_time))

        # Collect stderr async
        stderr = b''
        try:
            while True:
                chunk = await process.stderr.read(1024)
                if not chunk:
                    break
                stderr += chunk
        except Exception:
            pass  # stderr ممکنه close بشه

        await process.wait()

        if progress_task:
            await progress_task  # منتظر progress تموم بشه

        if process.returncode != 0:
            error_output = stderr.decode('utf-8', errors='ignore')
            print(f"FFmpeg Text Error Full: {error_output}")
            raise Exception(f"FFmpeg failed (Text): {error_output[:300]}...")

        if message:
            await message.edit("✅ واترمارک متنی اضافه شد!")

    except Exception as e:
        raise Exception(f"Text watermark error: {e}")

async def add_image_watermark(input_path, output_path, image_path, position, size_percent, message: Message = None, start_time: float = None):
    """افزودن واترمارک تصویری (async progress)."""
    if not os.path.exists(input_path) or not os.path.exists(image_path):
        raise Exception(f"فایل‌ها پیدا نشد: ویدیو={input_path}, تصویر={image_path}")

    position_map = {
        "top_right": "W-w-20:20",
        "top_center": "(W-w)/2:20",
        "top_left": "20:20",
        "center_right": "W-w-20:(H-h)/2",
        "center": "(W-w)/2:(H-h)/2",
        "center_left": "20:(H-h)/2",
        "bottom_right": "W-w-20:H-h-20",
        "bottom_center": "(W-w)/2:H-h-20",
        "bottom_left": "20:H-h-20"
    }

    # فیکس filter: scale + overlay + map outv
    filter_complex = (
        f"[1:v]scale=iw*{size_percent/100}:-1[wm];"
        f"[0:v][wm]overlay={position_map[position]}[outv]"
    )

    cmd = [
        'ffmpeg', '-i', input_path, '-i', image_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '0:a:0?',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', output_path, '-y',
        '-progress', 'pipe:1'
    ]

    try:
        total_ms = await get_video_duration(input_path)
        if message:
            await message.edit("⏳ در حال آماده‌سازی...")

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        progress_task = None
        if message and total_ms:
            progress_task = asyncio.create_task(read_progress_async(process.stdout, total_ms, message, start_time))

        stderr = b''
        try:
            while True:
                chunk = await process.stderr.read(1024)
                if not chunk:
                    break
                stderr += chunk
        except Exception:
            pass

        await process.wait()

        if progress_task:
            await progress_task

        if process.returncode != 0:
            error_output = stderr.decode('utf-8', errors='ignore')
            print(f"FFmpeg Image Error Full: {error_output}")
            raise Exception(f"FFmpeg failed (Image): {error_output[:300]}...")

        if message:
            await message.edit("✅ واترمارک تصویری اضافه شد!")

    except Exception as e:
        raise Exception(f"Image watermark error: {e}")
