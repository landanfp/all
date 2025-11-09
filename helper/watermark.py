# نام فایل: helper/watermark.py (نسخه نهایی با اصلاح مسیر و موقعیت)
import asyncio
import os
import subprocess
import shlex
import logging

logger = logging.getLogger(__name__)

# تعریف ثابت‌ها برای جلوگیری از تکرار و اشتباه
# NOTE: از آنجایی که CYCLE_DURATION در هر تابع تغییر می‌کند، باید داخل توابع تعریف شود.
T = "t"  # متغیر زمان اصلی در FFmpeg

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    try:
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
            f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y -loglevel warning"
        )
        
        logger.info(f"Executing FFmpeg command for text watermark: {cmd}")
        
        # 7. اجرای ایمن FFmpeg (کوتاه کردن پیام خطا)
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_output = stderr.decode()
            logger.error(f"FFmpeg stdout: {stdout.decode()}")
            logger.error(f"FFmpeg stderr: {error_output}")
            short_error = error_output.split("Error reinitializing filters!")[-1].strip().split("\n")[0]
            if not short_error:
                 short_error = error_output.split("Input #0, mov,mp4,m4a,3gp,3g2,mj2, from ")[0].strip()
            raise Exception(f"FFmpeg failed: {short_error[:250]}...") 

        logger.info(f"Text watermark added successfully to {output_path}")

    except FileNotFoundError:
        logger.error("FFmpeg command not found. Please install FFmpeg.")
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        logger.error(f"Error during animated text watermark processing: {e}")
        if "FFmpeg failed" in str(e):
             raise e
        else:
             raise Exception(f"Error during animated text watermark processing: {e}")

# ----------------------------------------------------------------------------------

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    """افزودن واترمارک تصویری متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    try:
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

        # 4. تعریف انیمیشن (Expressionها) - alpha رو مثل متن 0.8 کن
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
        
        ALPHA_EXPRESSION = (  # فیکس: 0.8 در fade و pause
            f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
                f"0.8 * {MOD_T} / {MOVE_IN_DURATION}, "
            f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
                f"0.8, "
                f"0.8 * (1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
            ")"
        )

        # 5. فیکس: Escape کاماها برای shell (خارج از f-string)
        escaped_X = X_EXPRESSION.replace(',', r'\,')
        escaped_Y = Y_EXPRESSION.replace(',', r'\,')
        escaped_alpha = ALPHA_EXPRESSION.replace(',', r'\,')

        # 5. ساخت فیلتر `filter_complex` - فیکس scale به main_h و format=yuv444p برای smooth
        filter_complex = (
            f"[0:v]scale=iw*sar:ih,setsar=1[v];"
            f"[1:v]scale={size_percent/100}*main_h:-1,format=yuva444p[wm];"  # فیکس: main_h به جای iw
           
            # اعمال آلفا بر اساس زمان
            f"[wm]colorchannelmixer=aa='{escaped_alpha}'[wma];" 
           
            # اعمال انیمیشن X و Y در فیلتر overlay
            f"[v][wma]overlay=x='{escaped_X}':"
            f"y='{escaped_Y}':"
            f"eof_action=repeat,format=yuv444p[ov];"  # فیکس: yuv444p برای smooth animation
            f"[ov]format=yuv420p[outv]" 
        )

        # 6. ساخت دستور FFmpeg - اضافه -loglevel warning برای debug
        cmd = (
            f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
            f"-filter_complex \"{filter_complex}\" "
            f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
            f"-profile:v high -level:v 4.0 " 
            f"-g 30 -keyint_min 1 -movflags +faststart "
            f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y -loglevel warning"  
        )
        
        logger.info(f"Executing FFmpeg command for image watermark: {cmd}")
        
        # 7. اجرای ایمن FFmpeg
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            logger.error(f"FFmpeg stdout: {stdout.decode()}")
            logger.error(f"FFmpeg stderr: {error_output}")
            short_error = error_output.split("Error reinitializing filters!")[-1].strip().split("\n")[0]
            if not short_error:
                 short_error = error_output.split("Input #0, mov,mp4,m4a,3gp,3g2,mj2, from ")[0].strip()
            raise Exception(f"FFmpeg failed: {short_error[:250]}...")

        logger.info(f"Image watermark added successfully to {output_path}")

    except FileNotFoundError:
        logger.error("FFmpeg command not found. Please install FFmpeg.")
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        logger.error(f"Error during animated image watermark processing: {e}")
        if "FFmpeg failed" in str(e):
             raise e
        else:
             raise Exception(f"Error during animated image watermark processing: {e}")
