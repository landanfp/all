# نام فایل: helper/watermark.py (نسخه نهایی با MoviePy - فیکس set_format و duration parse)
import asyncio
import os
import subprocess
import shlex
import numpy as np  # برای np.mod و mask array
import json  # برای json parse duration
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip

# تعریف ثابت‌ها برای جلوگیری از تکرار و اشتباه
T = "t"  # متغیر زمان اصلی در FFmpeg

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # 1. تنظیمات زمان‌بندی انیمیشن (ورود 2، مکث 4، خروج 1.5)
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"
    
    # 2. محاسبه مختصات نهایی در مرحله مکث (هدف: بالا-راست)
    FINAL_X_PAUSE = "main_w-text_w-20" 
    FINAL_Y_PAUSE = "20" 
    
    # 3. محاسبه مختصات نهایی برای خروج (مستقیم به پایین)
    FINAL_X_OUT = FINAL_X_PAUSE 
    FINAL_Y_OUT = "main_h-text_h-20" 

    # 4. تعریف انیمیشن (Expressionها)
    
    # A. موقعیت X: ورود از چپ، توقف در راست، ثابت تا خروج
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * {MOD_T} / {MOVE_IN_DURATION} - text_w * (1 - {MOD_T} / {MOVE_IN_DURATION}), "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            f"{FINAL_X_OUT})" 
        ")"
    )

    # B. موقعیت Y: توقف در بالا، حرکت مستقیم به پایین در زمان خروج
    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + ({FINAL_Y_OUT} - {FINAL_Y_PAUSE}) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    # C. محو شدن Alpha: محو شدن سریعتر
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"0.8 * {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), "
            f"0.8, "
            f"0.8 * (1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 5. تعریف فیلتر Drawtext
    safe_text = shlex.quote(text)
    
    drawtext_loop = (
        f"drawtext=text={safe_text}:fontcolor=white:" 
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"alpha='{ALPHA_EXPRESSION}'" 
    )

    # 6. ساخت دستور FFmpeg
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext_loop}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # 7. اجرای ایمن FFmpeg (کوتاه کردن پیام خطا)
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_output = stderr.decode()
            short_error = error_output.split("Error reinitializing filters!")[-1].strip().split("\n")[0]
            if not short_error:
                    short_error = error_output.split("Input #0, mov,mp4,m4a,3gp,3g2,mj2, from ")[0].strip()
            raise Exception(f"FFmpeg failed: {short_error[:250]}...") 

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        if "FFmpeg failed" in str(e):
            raise e
        else:
            raise Exception(f"Error during animated text watermark processing: {e}")

# ----------------------------------------------------------------------------------

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    """افزودن واترمارک تصویری متحرک و محوشونده به ویدیو (با تکرار حلقوی) با MoviePy."""
    
    def process_sync():
        """تابع sync برای MoviePy (در thread جداگانه اجرا می‌شه)."""
        try:
            # Validate input_path قبل لود (size + ffprobe duration)
            if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
                raise Exception("فایل ویدیو ناقص است.")
            
            # چک duration با ffprobe (json parse فیکس)
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", input_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                raise Exception("ffprobe fail - فایل corrupt.")
            
            try:
                data = json.loads(process.stdout)
                duration_str = data['format'].get('duration', '0')
                duration_float = float(duration_str) if duration_str else 0
                if duration_float == 0:
                    raise Exception("فایل ویدیو corrupt است (duration 0).")
            except (json.JSONDecodeError, ValueError) as parse_e:
                raise Exception(f"Parse error in ffprobe: {str(parse_e)}")
            
            # ۱. لود ویدیو (با error handling)
            try:
                video = VideoFileClip(input_path)
            except Exception as load_e:
                raise Exception(f"خطا در لود ویدیو (corrupt file): {str(load_e)}")
            
            video_w, video_h = video.size
            duration = video.duration
            fps = video.fps
            
            # ۲. لود و تنظیم تصویر واترمارک (transparent برای PNG، بدون set_format)
            is_transparent = image_path.lower().endswith('.png')
            wm_base = ImageClip(image_path, transparent=is_transparent).resize(height=video_h * size_percent / 100)
            # فیکس: بدون set_format (فقط RGBA برای PNG default)
            wm_w, wm_h = wm_base.size
            
            # ۳. تنظیمات انیمیشن (مثل FFmpeg)
            MOVE_IN = 2.0  # float برای safety
            PAUSE = 4.0
            MOVE_OUT = 1.5
            CYCLE = MOVE_IN + PAUSE + MOVE_OUT
            ALPHA_MAX = 0.6  # کمتر کدر برای visibility بهتر
            
            # Lambda برای cycle time (با np.mod برای np.array t)
            get_cycle_time = lambda t: np.mod(t, CYCLE)
            
            # محاسبه موقعیت پایه بر اساس position (margin کمتر برای visibility)
            pos_base = {
                "top_right": (video_w - wm_w - 10, 10),
                "top_center": ((video_w - wm_w) / 2, 10),
                "top_left": (10, 10),
                "center_right": (video_w - wm_w - 10, (video_h - wm_h) / 2),
                "center": ((video_w - wm_w) / 2, (video_h - wm_h) / 2),
                "center_left": (10, (video_h - wm_h) / 2),
                "bottom_right": (video_w - wm_w - 10, video_h - wm_h - 10),
                "bottom_center": ((video_w - wm_w) / 2, video_h - wm_h - 10),
                "bottom_left": (10, video_h - wm_h - 10)
            }
            x_base, y_base = pos_base.get(position, (video_w - wm_w - 10, 10))  # default top_right
            
            # موقعیت خروج (همیشه به پایین)
            x_out, y_out = x_base, video_h - wm_h - 10
            
            # Lambda برای x_pos (np.where برای vectorized)
            x_pos = lambda t: np.where(
                get_cycle_time(t) < MOVE_IN,
                x_base * (get_cycle_time(t) / MOVE_IN) - wm_w * (1 - get_cycle_time(t) / MOVE_IN),
                np.where(
                    get_cycle_time(t) < MOVE_IN + PAUSE,
                    x_base,
                    x_out
                )
            )
            
            # Lambda برای y_pos
            y_pos = lambda t: np.where(
                get_cycle_time(t) < MOVE_IN + PAUSE,
                y_base,
                y_base + (y_out - y_base) * ((get_cycle_time(t) - (MOVE_IN + PAUSE)) / MOVE_OUT)
            )
            
            # Function برای opacity scalar (0-ALPHA_MAX)
            # *** این تابع اکنون مستقیماً توسط set_opacity استفاده خواهد شد ***
            def get_opacity(t):
                c_t = get_cycle_time(t)
                if c_t < MOVE_IN:
                    return ALPHA_MAX * (c_t / MOVE_IN)
                elif c_t < MOVE_IN + PAUSE:
                    return ALPHA_MAX
                else:
                    return ALPHA_MAX * (1 - ((c_t - (MOVE_IN + PAUSE)) / MOVE_OUT))
            
            # ۴. اعمال انیمیشن به واترمارک (position lambda + set_opacity)
            wm = (wm_base
                  .set_duration(duration)
                  .set_position(lambda t: (x_pos(t), y_pos(t)))
                  .set_opacity(get_opacity)) # <-- **استفاده از set_opacity (که قبلاً اضافه کردیم)**
            
            # ۵. کامپوزیت و export (medium preset + bitrate برای کیفیت بهتر)
            final = CompositeVideoClip([video, wm], size=video.size)
            
            # --- شروع تغییرات ---
            
            # **فیکس (1): تخصیص صریح صدا برای جلوگیری از خطای میکس**
            final.audio = video.audio
            
            final.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='medium',  # کیفیت بهتر، کمتر artifact
                bitrate='2000k',  # bitrate بالاتر برای sharpness
                
                # **فیکس (2): فعال کردن لاگ‌ها برای دیباگ**
                verbose=True,   # <-- تغییر از False
                logger='bar',   # <-- تغییر از None
                
                threads=1  # disable multiprocessing (طبق کد شما)
            )
            
            # --- پایان تغییرات ---

            # بستن کلیپ‌ها برای free memory
            video.close()
            wm_base.close()
            # mask_clip.close() # (این خط قبلا حذف شده بود، درست است)
            wm.close()
            final.close()
            
            if not os.path.exists(output_path):
                raise Exception("فایل خروجی تولید نشد!")
                
        except Exception as e:
            raise Exception(f"MoviePy error: {str(e)}")
    
    # اجرا در thread جداگانه (چون MoviePy CPU-intensiveه)
    await asyncio.to_thread(process_sync)
