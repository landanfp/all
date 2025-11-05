# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - نسخه متعادل)
import asyncio
import os
import subprocess
import shlex

# مسیر فونت را تعریف می‌کنیم (فرض می‌کنیم در پوشه fonts کنار bot.py است)
# **نکته مهم: مطمئن شو این فایل وجود دارد!**
FONT_PATH = "fonts/font.ttf"

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی به ویدیو با استفاده از FFmpeg (نسخه متعادل)."""
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
    
    # استفاده از فونت مشخص برای پایداری
    drawtext = (
        f"drawtext=text={safe_text}:fontfile={FONT_PATH}:fontcolor=white@0.8:"
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}:"
        f"ft_quality=high"
    )

    # تنظیمات متعادل: preset veryfast و crf 23
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # اجرای ایمن FFmpeg با shlex.split
    try:
        # بررسی وجود فونت قبل از اجرا
        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError(f"فونت در مسیر {FONT_PATH} پیدا نشد! لطفا فونت را دانلود و در پوشه fonts قرار دهید.")

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

    except FileNotFoundError as e:
        if "ffmpeg" in str(e):
            raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
        else:
            raise e
    except Exception as e:
        raise Exception(f"Error during text watermark processing: {e}")

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
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

    # فیکس فرمت (از قبل اعمال شده)
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva420p[wm];" 
        f"[v][wm]overlay={position_map[position]}[ov];"
        f"[ov]format=yuv420p"
    )

    # **فیکس نهایی سازگاری با تلگرام:**
    # 1. -profile:v high -level:v 4.0 (اجبار به استانداردترین پارامترهای H.264)
    # 2. -map [ov] (نقشه‌برداری صریح خروجی فیلتر)
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " # اضافه شده
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [ov] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y" # تغییر map
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
