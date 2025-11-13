# نام فایل: helper/watermark.py (نسخه نهایی و عملیاتی با استراتژی پیشرفته نمایش خطا)
import asyncio
import os
import subprocess
import shlex

# تعریف ثابت‌ها برای جلوگیری از تکرار و اشتباه
T = "t" # متغیر زمان اصلی در FFmpeg

# --- تابع add_text_watermark (بدون تغییر) ---
async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # 1. تنظیمات زمان‌بندی انیمیشن 
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"
    
    # 2. محاسبه مختصات نهایی 
    FINAL_X_PAUSE = "main_w-text_w-20" 
    FINAL_Y_PAUSE = "20" 
    FINAL_X_OUT = FINAL_X_PAUSE 
    FINAL_Y_OUT = "main_h-text_h-20" 

    # 3. تعریف انیمیشن (Expressionها) 
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * {MOD_T} / {MOVE_IN_DURATION} - text_w * (1 - {MOD_T} / {MOVE_IN_DURATION}), "
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
    
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"0.8 * {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), "
            f"0.8, "
            f"0.8 * (1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 4. تعریف فیلتر Drawtext
    safe_text = shlex.quote(text)
    
    drawtext_loop = (
        f"drawtext=text={safe_text}:fontcolor=white:" 
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"alpha='{ALPHA_EXPRESSION}'" 
    )

    # 5. ساخت دستور FFmpeg
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext_loop}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # 6. اجرای ایمن FFmpeg 
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_output = stderr.decode()
            # مدیریت خطای کوتاه برای ربات
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
    
    # 1. تنظیمات زمان‌بندی انیمیشن (بدون تغییر)
    T = "t"
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    
    # 2. محاسبه مختصات نهایی (بدون تغییر)
    FINAL_X_PAUSE = "main_w-overlay_w-20"
    FINAL_Y_PAUSE = "20" 
    FINAL_X_OUT = FINAL_X_PAUSE
    FINAL_Y_OUT = "main_h-overlay_h-20" 

    # 3. تعریف انیمیشن (Expressionها) - **اصلاحات نهایی نحوی FFmpeg اعمال شده**
    
    # X_EXPRESSION: (ورود: 0 تا 2) (مکث: 2 تا 6) (خروج: 6 تا 7.5)
    X_EXPRESSION = (
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * mod(t,{CYCLE_DURATION}) / {MOVE_IN_DURATION} - overlay_w * (1 - mod(t,{CYCLE_DURATION}) / {MOVE_IN_DURATION}), "
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            f"{FINAL_X_OUT})"
        ")"
    )

    # Y_EXPRESSION: (مکث: 0 تا 6) (حرکت: 6 تا 7.5)
    Y_EXPRESSION = (
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + ({FINAL_Y_OUT} - {FINAL_Y_PAUSE}) * (mod(t,{CYCLE_DURATION}) - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    )
    
    # ALPHA_EXPRESSION: (ورود: 0 تا 2) (مکث: 2 تا 6) (خروج: 6 تا 7.5)
    ALPHA_EXPRESSION = (
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION}), " 
            f"mod(t,{CYCLE_DURATION}) / {MOVE_IN_DURATION}, "
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"1, "
            f"(1 - (mod(t,{CYCLE_DURATION}) - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
        ")"
    )

    # 4. ساخت فیلتر `filter_complex` (با آخرین اصلاحات منطقی FFmpeg)
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];"  
        
        # اعمال آلفا بر اساس زمان
        f"[wm]colorchannelmixer=aa='{ALPHA_EXPRESSION}'[wma];" 
        
        # اعمال انیمیشن X و Y در فیلتر overlay
        f"[v][wma]overlay=x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"eof_action=repeat:shortest=0:repeatlast=0[ov];" 
        f"[ov]format=yuv420p[outv]" 
    )

    # 5. ساخت دستور FFmpeg (بدون تغییر)
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " 
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y" 
    )
    
    # 6. اجرای ایمن FFmpeg (با استراتژی پاکسازی خطا)
    try:
        cmd_list = shlex.split(cmd) 
        
        process = await asyncio.create_subprocess_exec(
            *cmd_list, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode()
            
            # 🚨 استراتژی جدید: حذف سربرگ‌های طولانی برای نمایش خطای واقعی 🚨
            cleaned_error = error_output
            
            # پاکسازی سربرگ FFmpeg
            if "ffmpeg version" in cleaned_error:
                cleaned_error = cleaned_error.split('Configuration:')[-1].strip()
            
            # پاکسازی جزئیات کتابخانه
            cleaned_error = cleaned_error.split('libpostproc')[-1].strip()
            
            # تلاش برای گرفتن خطای اصلی (احتمالا در پایان)
            if not cleaned_error.strip():
                # اگر باز هم خالی بود، سربرگ FFmpeg را می گیریم و کوتاه می کنیم
                cleaned_error = error_output.split("Input #0, mov,mp4,m4a,3gp,3g2,mj2, from ")[0].strip()

            raise Exception(f"❌ FFmpeg failed (RC: {process.returncode}). Error:\n{cleaned_error[:500]}...")


    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg command not found. Please install FFmpeg.")
    except Exception as e:
        if "FFmpeg failed" in str(e):
             raise e
        else:
             raise Exception(f"Error during animated image watermark processing: {e}")
