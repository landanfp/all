# نام فایل: helper/watermark.py (نسخه نهایی - رفع مشکل سینتکسی FFmpeg)
import asyncio
import os
import subprocess
import shlex

# تعریف ثابت‌ها برای جلوگیری از تکرار و اشتباه
MOVE_IN_DURATION = 2
PAUSE_DURATION = 4
MOVE_OUT_DURATION = 3
CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
MOD_TIME = f"mod(t,{CYCLE_DURATION})" # عبارت اصلی حلقوی

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # متغیرهای ثابت زمانی
    T = "t"
    C = CYCLE_DURATION
    MOD_T = MOD_TIME

    # 1. محاسبه مختصات و آلفا با استفاده از f-string و MOD_T
    
    # مختصات X: ورود از چپ (0 تا 2)، توقف (2 تا 6)، خروج به راست (6 تا 9)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"((main_w-text_w)/2) * {MOD_T} / {MOVE_IN_DURATION} - text_w * (1 - {MOD_T} / {MOVE_IN_DURATION}), "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"(main_w-text_w)/2, "
            f"(main_w-text_w)/2 + (main_w-text_w-20 - (main_w-text_w)/2) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
        ")"
    )

    # مختصات Y: توقف در بالا (0 تا 6)، خروج به پایین (6 تا 9)
    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"20, "
            f"20 + (main_h-text_h-20 - 20) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    # آلفا: ورود تدریجی (0 تا 2)، ثابت (2 تا 6)، خروج تدریجی (6 تا 9)
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"0.8 * {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), "
            f"0.8, "
            f"0.8 * (1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    safe_text = shlex.quote(text)
    
    drawtext_loop = (
        f"drawtext=text={safe_text}:fontcolor=white:" 
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"alpha='{ALPHA_EXPRESSION}'" 
    )

    # 2. ساخت دستور FFmpeg (بدون تغییر)
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext_loop}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # 3. اجرای ایمن FFmpeg (کوتاه کردن پیام خطا)
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_output = stderr.decode()
            # کوتاه کردن پیام خطا برای جلوگیری از خطای MESSAGE_TOO_LONG تلگرام
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
    """افزودن واترمارک تصویری متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # متغیرهای ثابت زمانی
    T = "t"
    C = CYCLE_DURATION
    MOD_T = MOD_TIME

    # 1. محاسبه مختصات و آلفا با استفاده از f-string و MOD_T
    
    # مختصات X: ورود از چپ (0 تا 2)، توقف (2 تا 6)، خروج به راست (6 تا 9)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"((main_w-overlay_w)/2) * {MOD_T} / {MOVE_IN_DURATION} - overlay_w * (1 - {MOD_T} / {MOVE_IN_DURATION}), "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"(main_w-overlay_w)/2, "
            f"(main_w-overlay_w)/2 + (main_w-overlay_w-20 - (main_w-overlay_w)/2) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
        ")"
    )

    # مختصات Y: توقف در بالا (0 تا 6)، خروج به پایین (6 تا 9)
    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"20, "
            f"20 + (main_h-overlay_h-20 - 20) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    # آلفا: ورود تدریجی (0 تا 2)، ثابت (2 تا 6)، خروج تدریجی (6 تا 9)
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"{MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"1, "
            f"(1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 2. ساخت فیلتر `filter_complex`
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];" 
        
        # اعمال آلفا بر اساس زمان
        f"[wm]colorchannelmixer=aa='{ALPHA_EXPRESSION}'[wma];" 
        
        # اعمال انیمیشن X و Y در فیلتر overlay
        f"[v][wma]overlay=x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"eof_action=repeat[ov];" 
        f"[ov]format=yuv420p[outv]" 
    )

    # 3. ساخت دستور FFmpeg (بدون تغییر)
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " 
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y" 
    )
    
    # 4. اجرای ایمن FFmpeg (کوتاه کردن پیام خطا)
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            # کوتاه کردن پیام خطا برای جلوگیری از خطای MESSAGE_TOO_LONG تلگرام
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
             raise Exception(f"Error during animated image watermark processing: {e}")
