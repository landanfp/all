# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - نسخه متعادل با Progress Bar)
import asyncio
import os
import subprocess
import shlex
import json
import threading
from pyrogram.types import Message

async def get_video_duration(input_path):
    """استخراج duration ویدیو با ffprobe (به میلی‌ثانیه)."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'json', input_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        data = json.loads(stdout.decode())
        duration = float(data['format']['duration']) * 1000  # به ms
        return duration
    except Exception:
        return None  # fallback بدون progress

async def add_text_watermark(input_path, output_path, text, position, size_percent, message: Message = None, start_time: float = None):
    """افزودن واترمارک متنی به ویدیو با استفاده از FFmpeg (با Progress Bar)."""
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

    cmd_base = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y -progress pipe:1"
    )
    
    # اجرای ایمن FFmpeg با Progress
    try:
        # اول duration رو بگیریم
        total_ms = await get_video_duration(input_path)
        if message and start_time and total_ms:
            await message.edit("⏳ در حال استخراج اطلاعات ویدیو...")

        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd_base), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Async reader برای stderr (progress)
        async def read_progress():
            current_ms = 0
            last_update = 0
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                if line_str.startswith('out_time_ms='):
                    try:
                        current_ms = float(line_str.split('=')[1])
                        now = time.time()
                        diff = now - start_time
                        if (now - last_update) >= 5 or current_ms >= total_ms:  # هر 5 ثانیه
                            await progress_bar(current_ms, total_ms, message, start_time, "watermark")
                            last_update = now
                    except ValueError:
                        pass
        
        # شروع reader در thread جدا (چون async readline blocking نیست اما برای سادگی)
        progress_task = asyncio.create_task(read_progress())
        
        stdout, stderr = await process.communicate()
        await progress_task
        
        if process.returncode != 0:
            error_output = stderr.decode()
            print(f"FFmpeg Error (Text): {error_output}")
            raise Exception(f"FFmpeg failed: {error_output[:200]}...") 

        # Update نهایی به 100%
        if message:
            await message.edit("✅ واترمارک اضافه شد!")

    except FileNotFoundError as e:
        if "ffmpeg" in str(e) or "ffprobe" in str(e):
            raise FileNotFoundError("FFmpeg یا ffprobe پیدا نشد. لطفاً FFmpeg را نصب کنید.")
        else:
            raise e
    except Exception as e:
        raise Exception(f"Error during text watermark processing: {e}")

async def add_image_watermark(input_path, output_path, image_path, position, size_percent, message: Message = None, start_time: float = None):
    """افزودن واترمارک تصویری به ویدیو با استفاده از FFmpeg (با Progress Bar)."""
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

    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva420p[wm];" 
        f"[v][wm]overlay={position_map[position]}[ov];"
        f"[ov]format=yuv420p[outv]" 
    )

    cmd_base = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " 
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y -progress pipe:1"
    )
    
    # اجرای ایمن FFmpeg با Progress (مشابه text)
    try:
        total_ms = await get_video_duration(input_path)
        if message and start_time and total_ms:
            await message.edit("⏳ در حال استخراج اطلاعات ویدیو...")

        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd_base), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        async def read_progress():
            current_ms = 0
            last_update = 0
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                if line_str.startswith('out_time_ms='):
                    try:
                        current_ms = float(line_str.split('=')[1])
                        now = time.time()
                        diff = now - start_time
                        if (now - last_update) >= 5 or current_ms >= total_ms:
                            await progress_bar(current_ms, total_ms, message, start_time, "watermark")
                            last_update = now
                    except ValueError:
                        pass
        
        progress_task = asyncio.create_task(read_progress())
        
        stdout, stderr = await process.communicate()
        await progress_task
        
        if process.returncode != 0:
            error_output = stderr.decode()
            print(f"FFmpeg Error (Image): {error_output}")
            raise Exception(f"FFmpeg failed: {error_output[:200]}...")

        if message:
            await message.edit("✅ واترمارک اضافه شد!")

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg یا ffprobe پیدا نشد. لطفاً FFmpeg را نصب کنید.")
    except Exception as e:
        raise Exception(f"Error during image watermark processing: {e}")
