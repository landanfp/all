# نام فایل: helper/watermark.py (منطق اصلی FFmpeg)
import asyncio
import os
import subprocess
import shlex 

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی به ویدیو با استفاده از FFmpeg."""
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

    # **حذف چک فونت و fontfile – استفاده از پیش‌فرض FFmpeg**
    
    # استفاده از shlex.quote برای ایمن سازی متن
    safe_text = shlex.quote(text)
    
    # **اصلاح: drawtext بدون fontfile (پیش‌فرض استفاده می‌شه)**
    drawtext = (
        f"drawtext=text={safe_text}:fontcolor=white@0.8:"
        f"fontsize=h*{size_percent}/100:ft_quality=3:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # اجرای ایمن FFmpeg با shlex.split
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
             error_output = stderr.decode()
             print(f"FFmpeg Error (Text): {error_output}")
             raise Exception(f"FFmpeg failed: {error_output[:200]}...")

    except FileNotFoundError:
        # اگر خطا مربوط به خود دستور ffmpeg باشد (نه فونت)
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        raise Exception(f"Error during text watermark processing: {e}")

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    """افزودن واترمارک تصویری به ویدیو با استفاده از FFmpeg."""
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

    # فیلتر برای مقیاس‌بندی تصویر و اعمال واترمارک
    filter_complex = (
        f"[1]scale=iw*{size_percent/100}:-1[wm];"
        f"[0][wm]overlay={position_map[position]}"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # اجرای ایمن FFmpeg
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            print(f"FFmpeg Error (Image): {error_output}")
            raise Exception(f"FFmpeg failed: {error_output[:200]}...")

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        raise Exception(f"Error during image watermark processing: {e}")
