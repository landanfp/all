# نام فایل: helper/watermark.py (نسخه نهایی با اصلاح انیمیشن تصویر و گزارش خطا)
import asyncio
import os
import subprocess
import shlex

# تعریف ثابت‌ها برای جلوگیری از تکرار و اشتباه
T = "t" # متغیر زمان اصلی در FFmpeg

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
    
    # 7. اجرای ایمن FFmpeg (با گزارش خطای بهبود یافته)
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # [FIX] بهبود گزارش خطا
        if process.returncode != 0:
            error_output = stderr.decode()
            error_lines = error_output.strip().splitlines()
            short_error = "\n".join(error_lines[-5:]) # دریافت ۵ خط آخر
            if not short_error:
                short_error = error_output[:250] 
            raise Exception(f"FFmpeg failed:\n{short_error}...")

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        if "FFmpeg failed" in str(e):
             raise e
        else:
             raise Exception(f"Error during animated text watermark processing: {e}")

# ----------------------------------------------------------------------------------

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    """[FIXED] افزودن واترمارک تصویری متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # 1. تنظیمات زمان‌بندی انیمیشن (ورود 2، مکث 4، خروج 1.5)
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"

    # 2. محاسبه مختصات نهایی در مرحله مکث (هدف: بالا-راست)
    FINAL_X_PAUSE = "main_w-overlay_w-20"
    FINAL_Y_PAUSE = "20" 

    # 3. محاسبه مختصات نهایی برای خروج (مستقیم به پایین)
    FINAL_X_OUT = FINAL_X_PAUSE
    FINAL_Y_OUT = "main_h-overlay_h-20" 

    # 4. تعریف انیمیشن (Expressionها)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * {MOD_T} / {MOVE_IN_DURATION} - overlay_w * (1 - {MOD_T} / {MOVE_IN_DURATION}), "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            f"{FINAL_X_OUT})"
        ")"
    )

    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + ({FINAL_Y_OUT} - {FINAL_Y_PAUSE}) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    # انیمیشن آلفا (80% شفافیت)
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"0.8 * {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"0.8, "
            f"0.8 * (1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 5. [FIX] ساخت فیلتر `filter_complex` اصلاح شده (رفع مشکل t=0)
    filter_complex = (
        # 1. ویدیو اصلی را آماده و به دو شاخه تقسیم کنید
        f"[0:v]scale=iw*sar:ih,setsar=1,split[v_main][v_canvas];"
        # 2. تصویر واترمارک را آماده کنید
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];"
        # 3. از شاخه 'v_canvas' یک بوم شفاف با تایم‌لاین ویدیو بسازید
        f"[v_canvas]colorchannelmixer=aa=0[canvas];"
        # 4. واترمارک را با انیمیشن X/Y روی بوم شفاف قرار دهید (t از [canvas] می‌آید)
        f"[canvas][wm]overlay=x='{X_EXPRESSION}':y='{Y_EXPRESSION}':eof_action=repeat[moved_wm];"
        # 5. واترمارک متحرک را با انیمیشن آلفا محو کنید (t از [moved_wm] می‌آید)
        f"[moved_wm]colorchannelmixer=aa='{ALPHA_EXPRESSION}'[faded_wm];"
        # 6. واترمارک نهایی (متحرک و محو شده) را روی ویدیوی اصلی قرار دهید
        f"[v_main][faded_wm]overlay[ov];"
        # 7. فرمت خروجی نهایی
        f"[ov]format=yuv420p[outv]"
    )

    # 6. ساخت دستور FFmpeg 
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " 
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y" 
    )
    
    # 7. اجرای ایمن FFmpeg (با گزارش خطای بهبود یافته)
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        # [FIX] بهبود گزارش خطا
        if process.returncode != 0:
            error_output = stderr.decode()
            error_lines = error_output.strip().splitlines()
            short_error = "\n".join(error_lines[-5:]) # دریافت ۵ خط آخر
            if not short_error:
                short_error = error_output[:250] 
            raise Exception(f"FFmpeg failed:\n{short_error}...")

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        if "FFmpeg failed" in str(e):
             raise e
        else:
             raise Exception(f"Error during animated image watermark processing: {e}")
