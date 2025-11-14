# نام فایل: helper/watermark.py (نسخه نهایی با MoviePy - فیکس multiprocessing و lambda)
import asyncio
import os
import subprocess
import shlex
import numpy as np  # برای np.mod در cycle time (safety با np.array t)
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# تعریف ثابت‌ها برای جلوگیری از تکرار و اشتباه
# NOTE: از آنجایی که CYCLE_DURATION در هر تابع تغییر می‌کند، باید داخل توابع تعریف شود.
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
            # ۱. لود ویدیو
            video = VideoFileClip(input_path)
            video_w, video_h = video.size
            duration = video.duration
            
            # ۲. لود و تنظیم تصویر واترمارک
            wm_base = ImageClip(image_path).resize(height=video_h * size_percent / 100)
            wm_w, wm_h = wm_base.size
            
            # ۳. تنظیمات انیمیشن (مثل FFmpeg)
            MOVE_IN = 2.0  # float برای safety
            PAUSE = 4.0
            MOVE_OUT = 1.5
            CYCLE = MOVE_IN + PAUSE + MOVE_OUT
            
            # Lambda برای cycle time (با np.mod برای np.array t)
            get_cycle_time = lambda t: np.mod(t, CYCLE)
            
            # محاسبه موقعیت پایه بر اساس position
            pos_base = {
                "top_right": (video_w - wm_w - 20, 20),
                "top_center": ((video_w - wm_w) / 2, 20),
                "top_left": (20, 20),
                "center_right": (video_w - wm_w - 20, (video_h - wm_h) / 2),
                "center": ((video_w - wm_w) / 2, (video_h - wm_h) / 2),
                "center_left": (20, (video_h - wm_h) / 2),
                "bottom_right": (video_w - wm_w - 20, video_h - wm_h - 20),
                "bottom_center": ((video_w - wm_w) / 2, video_h - wm_h - 20),
                "bottom_left": (20, video_h - wm_h - 20)
            }
            x_base, y_base = pos_base.get(position, (video_w - wm_w - 20, 20))  # default top_right
            
            # موقعیت خروج (همیشه به پایین)
            x_out, y_out = x_base, video_h - wm_h - 20
            
            # Lambda برای x_pos (nested np.where برای vectorized if/else - pickle-friendly و safe با np.array)
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
            
            # Lambda برای opacity
            opacity = lambda t: np.where(
                get_cycle_time(t) < MOVE_IN,
                0.8 * (get_cycle_time(t) / MOVE_IN),
                np.where(
                    get_cycle_time(t) < MOVE_IN + PAUSE,
                    0.8,
                    0.8 * (1 - ((get_cycle_time(t) - (MOVE_IN + PAUSE)) / MOVE_OUT))
                )
            )
            
            # ۴. اعمال انیمیشن به واترمارک (lambdaها مستقیم پاس می‌شن)
            wm = (wm_base
                  .set_duration(duration)
                  .set_position(lambda t: (x_pos(t), y_pos(t)))
                  .set_opacity(opacity))
            
            # ۵. کامپوزیت و export (فیکس: threads=1 برای disable multiprocessing و حل pickle/type error)
            final = CompositeVideoClip([video, wm], size=video.size)
            final.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='ultrafast',  # سریع برای Koyeb
                verbose=False,  # کمتر لاگ
                logger=None,
                threads=1  # فیکس کلیدی: جلوگیری از multiprocessing pickle issues
            )
            
            # بستن کلیپ‌ها برای free memory
            video.close()
            wm_base.close()
            wm.close()
            final.close()
            
            if not os.path.exists(output_path):
                raise Exception("فایل خروجی تولید نشد!")
                
        except Exception as e:
            raise Exception(f"MoviePy error: {str(e)}")
    
    # اجرا در thread جداگانه (چون MoviePy CPU-intensiveه)
    await asyncio.to_thread(process_sync)
