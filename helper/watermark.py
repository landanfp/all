# نام فایل: helper/watermark.py (نسخه نهایی با MoviePy - فیکس broken pipe و validate)
import asyncio
import os
import subprocess
import shlex
import numpy as np  # برای np.mod و mask array
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
            
            # چک duration با ffprobe (برای moov atom)
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", input_path]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0 or '"duration"' not in process.stdout or float(process.stdout.split('"duration":')[1].split(',')[0]) == 0:
                raise Exception("فایل ویدیو corrupt است (moov atom not found). لطفا فایل سالم ارسال کنید.")
            
            # ۱. لود ویدیو (با error handling)
            try:
                video = VideoFileClip(input_path)
            except Exception as load_e:
                raise Exception(f"خطا در لود ویدیو (corrupt file): {str(load_e)}")
            
            video_w, video_h = video.size
            duration = video.duration
            fps = video.fps
            
            # ۲. لود و تنظیم تصویر واترمارک (transparent برای PNG)
            is_transparent = image_path.lower().endswith('.png')
            wm_base = ImageClip(image_path, transparent=is_transparent).resize(height=video_h * size_percent / 100)
            wm_base = wm_base.set_format('RGBA')  # RGBA برای blending
            wm_w, wm_h = wm_base.size
            
            # ۳. تنظیمات انیمیشن
            MOVE_IN = 2.0
            PAUSE = 4.0
            MOVE_OUT = 1.5
            CYCLE = MOVE_IN + PAUSE + MOVE_OUT
            ALPHA_MAX = 0.6
            
            get_cycle_time = lambda t: np.mod(t, CYCLE)
            
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
            x_base, y_base = pos_base.get(position, (video_w - wm_w - 10, 10))
            
            x_out, y_out = x_base, video_h - wm_h - 10
            
            x_pos = lambda t: np.where(
                get_cycle_time(t) < MOVE_IN,
                x_base * (get_cycle_time(t) / MOVE_IN) - wm_w * (1 - get_cycle_time(t) / MOVE_IN),
                np.where(
                    get_cycle_time(t) < MOVE_IN + PAUSE,
                    x_base,
                    x_out
                )
            )
            
            y_pos = lambda t: np.where(
                get_cycle_time(t) < MOVE_IN + PAUSE,
                y_base,
                y_base + (y_out - y_base) * ((get_cycle_time(t) - (MOVE_IN + PAUSE)) / MOVE_OUT)
            )
            
            def get_opacity(t):
                c_t = get_cycle_time(t)
                if c_t < MOVE_IN:
                    return ALPHA_MAX * (c_t / MOVE_IN)
                elif c_t < MOVE_IN + PAUSE:
                    return ALPHA_MAX
                else:
                    return ALPHA_MAX * (1 - ((c_t - (MOVE_IN + PAUSE)) / MOVE_OUT))
            
            def mask_frame(t):
                alpha = get_opacity(t)
                frame = np.full((wm_h, wm_w), int(alpha * 255), dtype=np.uint8)
                return frame
            
            mask_clip = (ColorClip(size=(wm_w, wm_h), color=0, duration=duration, ismask=True)
                         .set_make_frame(mask_frame))
            
            wm = (wm_base
                  .set_duration(duration)
                  .set_position(lambda t: (x_pos(t), y_pos(t)))
                  .set_mask(mask_clip))
            
            # ۵. کامپوزیت و export (فیکس: catch broken pipe)
            final = CompositeVideoClip([video, wm], size=video.size)
            try:
                final.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    preset='medium',
                    bitrate='2000k',
                    verbose=False,
                    logger=None,
                    threads=1
                )
            except BrokenPipeError:
                raise Exception("FFmpeg pipe fail (broken pipe) - احتمالاً فایل corrupt. لطفا ویدیو سالم ارسال کنید.")
            except Exception as pipe_e:
                raise Exception(f"Export error (broken pipe or FFmpeg fail): {str(pipe_e)}")
            
            video.close()
            wm_base.close()
            mask_clip.close()
            wm.close()
            final.close()
            
            if not os.path.exists(output_path):
                raise Exception("فایل خروجی تولید نشد!")
                
        except Exception as e:
            raise Exception(f"MoviePy error: {str(e)}")
    
    await asyncio.to_thread(process_sync)
