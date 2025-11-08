# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - نسخه متحرک)
import asyncio
import os
import subprocess
import shlex

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # 1. تنظیمات زمان‌بندی انیمیشن (ورود 2، مکث 4، خروج 3)
    MOVE_IN_DURATION = 2  # مدت زمان ورود از چپ (ثانیه)
    PAUSE_DURATION = 4    # مدت زمان توقف در موقعیت نهایی (ثانیه)
    MOVE_OUT_DURATION = 3 # مدت زمان خروج به پایین-راست و محو شدن (ثانیه)
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION # مدت کل یک چرخه (9 ثانیه)

    # 2. محاسبه مختصات نهایی در مرحله مکث (وسط-بالا)
    FINAL_X_PAUSE = "(main_w-text_w)/2" # افقی: وسط
    FINAL_Y_PAUSE = "20" # عمودی: 20 پیکسل از بالا

    # 3. محاسبه مختصات نهایی برای خروج (پایین-راست)
    FINAL_X_OUT = "main_w-text_w-20" # افقی: 20 پیکسل از راست
    FINAL_Y_OUT = "main_h-text_h-20" # عمودی: 20 پیکسل از پایین

    # 4. تعریف انیمیشن (Expressionها)
    # متغیر t با mod(t, CYCLE_DURATION) جایگزین می‌شود تا حلقه تکرار ایجاد شود.

    # A. موقعیت X (ورود از چپ، توقف، خروج به راست)
    X_EXPRESSION = (
        f"if(lt(t,{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * t / {MOVE_IN_DURATION} - text_w * (1 - t / {MOVE_IN_DURATION}), "
        f"if(lt(t,{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            f"{FINAL_X_PAUSE} + ({FINAL_X_OUT} - {FINAL_X_PAUSE}) * (t - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
        ")"
    )

    # B. موقعیت Y (توقف، خروج به پایین)
    Y_EXPRESSION = (
        f"if(lt(t,{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + ({FINAL_Y_OUT} - {FINAL_Y_PAUSE}) * (t - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    # C. محو شدن Alpha (ورود تدریجی، ثابت، خروج تدریجی)
    ALPHA_EXPRESSION = (
        f"if(lt(t,{MOVE_IN_DURATION}), " 
            f"0.8 * t / {MOVE_IN_DURATION}, "
        f"if(lt(t,{MOVE_IN_DURATION + PAUSE_DURATION}), "
            f"0.8, "
            f"0.8 * (1 - (t - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 5. تعریف فیلتر Drawtext با اعمال حلقه تکرار
    safe_text = shlex.quote(text)
    
    drawtext_loop = (
        f"drawtext=text={safe_text}:fontcolor=white:" 
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x='{X_EXPRESSION.replace('t', f'mod(t,{CYCLE_DURATION})')}':"
        f"y='{Y_EXPRESSION.replace('t', f'mod(t,{CYCLE_DURATION})')}':"
        f"alpha='{ALPHA_EXPRESSION.replace('t', f'mod(t,{CYCLE_DURATION})')}'" 
    )

    # 6. ساخت دستور FFmpeg
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext_loop}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # 7. اجرای ایمن FFmpeg
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_output = stderr.decode()
            raise Exception(f"FFmpeg failed: {error_output}") 

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        raise Exception(f"Error during animated text watermark processing: {e}")

# ----------------------------------------------------------------------------------

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    """افزودن واترمارک تصویری متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # 1. تنظیمات زمان‌بندی انیمیشن (ورود 2، مکث 4، خروج 3)
    MOVE_IN_DURATION = 2  # مدت زمان ورود از چپ (ثانیه)
    PAUSE_DURATION = 4    # مدت زمان توقف در موقعیت نهایی (ثانیه)
    MOVE_OUT_DURATION = 3 # مدت زمان خروج به پایین-راست و محو شدن (ثانیه)
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION # مدت کل یک چرخه (9 ثانیه)

    # 2. محاسبه مختصات نهایی در مرحله مکث (وسط-بالا)
    FINAL_X_PAUSE = "(main_w-overlay_w)/2" # افقی: وسط
    FINAL_Y_PAUSE = "20" # عمودی: 20 پیکسل از بالا

    # 3. محاسبه مختصات نهایی برای خروج (پایین-راست)
    FINAL_X_OUT = "main_w-overlay_w-20" # افقی: 20 پیکسل از راست
    FINAL_Y_OUT = "main_h-overlay_h-20" # عمودی: 20 پیکسل از پایین

    # 4. تعریف انیمیشن (Expressionها)
    X_EXPRESSION = (
        f"if(lt(t,{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * t / {MOVE_IN_DURATION} - overlay_w * (1 - t / {MOVE_IN_DURATION}), "
        f"if(lt(t,{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            f"{FINAL_X_PAUSE} + ({FINAL_X_OUT} - {FINAL_X_PAUSE}) * (t - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
        ")"
    )

    Y_EXPRESSION = (
        f"if(lt(t,{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + ({FINAL_Y_OUT} - {FINAL_Y_PAUSE}) * (t - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    ALPHA_EXPRESSION = (
        f"if(lt(t,{MOVE_IN_DURATION}), " 
            f"t / {MOVE_IN_DURATION}, "
        f"if(lt(t,{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"1, "
            f"(1 - (t - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 5. ساخت فیلتر `filter_complex` با اعمال حلقه تکرار
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];" 
        
        # اعمال آلفا بر اساس زمان
        f"[wm]colorchannelmixer=aa='{ALPHA_EXPRESSION.replace('t', f'mod(t,{CYCLE_DURATION})')}'[wma];" 
        
        # اعمال انیمیشن X و Y در فیلتر overlay
        f"[v][wma]overlay=x='{X_EXPRESSION.replace('t', f'mod(t,{CYCLE_DURATION})')}':"
        f"y='{Y_EXPRESSION.replace('t', f'mod(t,{CYCLE_DURATION})')}':"
        f"eof_action=repeat[ov];" 
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
    
    # 7. اجرای ایمن FFmpeg
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            # این خط برای نمایش کل پیام خطا اصلاح شده است
            raise Exception(f"FFmpeg failed: {error_output}") 

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        # در اینجا نیز برای رفع مشکل قبلی، فقط به پیام خود FFmpeg ارجاع می‌دهیم
        if "FFmpeg failed" in str(e):
             raise e
        else:
             raise Exception(f"Error during animated image watermark processing: {e}")
