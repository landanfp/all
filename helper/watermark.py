# نام فایل: helper/watermark.py (نسخه نهایی با لاگ دستورات)
import asyncio
import os
import subprocess
import shlex

# تعریف ثابت‌ها
T = "t" # متغیر زمان اصلی در FFmpeg

# ----------------------------------------------------------------------------------
## تابع واترمارک متنی
# ----------------------------------------------------------------------------------

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"
    
    FINAL_X_PAUSE = "main_w-text_w-20" 
    FINAL_Y_PAUSE = "20" 
    
    FINAL_X_OUT = FINAL_X_PAUSE 
    FINAL_Y_OUT = "main_h-text_h-20" 

    # تعریف انیمیشن (Expressionهای فشرده)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}),({FINAL_X_PAUSE})*{MOD_T}/{MOVE_IN_DURATION}-text_w*(1-{MOD_T}/{MOVE_IN_DURATION})," 
        f"if(lt({MOD_T},{MOVE_IN_DURATION+PAUSE_DURATION}),{FINAL_X_PAUSE},{FINAL_X_OUT}))"
    )

    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION+PAUSE_DURATION}),{FINAL_Y_PAUSE},"
        f"{FINAL_Y_PAUSE}+({FINAL_Y_OUT}-{FINAL_Y_PAUSE})*({MOD_T}-{MOVE_IN_DURATION+PAUSE_DURATION})/{MOVE_OUT_DURATION})"
    )
    
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}),0.8*{MOD_T}/{MOVE_IN_DURATION},"
        f"if(lt({MOD_T},{MOVE_IN_DURATION+PAUSE_DURATION}),0.8,0.8*(1-({MOD_T}-{MOVE_IN_DURATION+PAUSE_DURATION})/{MOVE_OUT_DURATION})))"
    )

    # تعریف فیلتر Drawtext
    safe_text = shlex.quote(text)
    
    drawtext_loop = (
        f"drawtext=text={safe_text}:fontcolor=white:" 
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"alpha='{ALPHA_EXPRESSION}'" 
    )

    # ساخت دستور FFmpeg
    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext_loop}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )
    
    # 🌟 لاگ دستور کامل FFmpeg
    print(f"--- FFmpeg CMD (Text Watermark):\n{cmd}\n---")
    
    # اجرای ایمن FFmpeg
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # بهبود گزارش خطا
        if process.returncode != 0:
            error_output = stderr.decode()
            error_lines = error_output.strip().splitlines()
            short_error = "\n".join(error_lines[-5:]) 
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
## تابع واترمارک تصویری (اصلاح نهایی با Alpha Extract/Merge)
# ----------------------------------------------------------------------------------

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    """افزودن واترمارک تصویری متحرک و محوشونده به ویدیو."""
    
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"

    FINAL_X_PAUSE = "main_w-overlay_w-20"
    FINAL_Y_PAUSE = "20" 

    FINAL_X_OUT = FINAL_X_PAUSE
    FINAL_Y_OUT = "main_h-overlay_h-20" 

    # تعریف انیمیشن (Expressionهای فشرده)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}),({FINAL_X_PAUSE})*{MOD_T}/{MOVE_IN_DURATION}-overlay_w*(1-{MOD_T}/{MOVE_IN_DURATION}),"
        f"if(lt({MOD_T},{MOVE_IN_DURATION+PAUSE_DURATION}),{FINAL_X_PAUSE},{FINAL_X_OUT}))"
    )

    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION+PAUSE_DURATION}),{FINAL_Y_PAUSE},"
        f"{FINAL_Y_PAUSE}+({FINAL_Y_OUT}-{FINAL_Y_PAUSE})*({MOD_T}-{MOVE_IN_DURATION+PAUSE_DURATION})/{MOVE_OUT_DURATION})"
    )
    
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}),0.8*{MOD_T}/{MOVE_IN_DURATION},"
        f"if(lt({MOD_T},{MOVE_IN_DURATION+PAUSE_DURATION}),0.8,0.8*(1-({MOD_T}-{MOVE_IN_DURATION+PAUSE_DURATION})/{MOVE_OUT_DURATION})))"
    )

    # 5. ساخت فیلتر `filter_complex` 
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v_main];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm_scaled];" 
        
        # 1. اعمال انیمیشن X/Y با کوتیشن سینگل
        f"[v_main][wm_scaled]overlay=x='{X_EXPRESSION}':y='{Y_EXPRESSION}':eof_action=repeat:shortest=1[moved_wm];"
        
        # 2. استخراج کانال شفافیت
        f"[moved_wm]alphaextract[alpha_channel];"
        
        # 3. FIX: حذف کوتیشن سینگل از اطراف عبارت LUM در فیلتر GEQ
        f"[alpha_channel]geq=lum={ALPHA_EXPRESSION}*255:cr=128:cb=128[faded_alpha];"
        
        # 4. برگرداندن کانال شفافیت جدید
        f"[moved_wm][faded_alpha]alphamerge[faded_wm_final];"

        # 5. ادغام واترمارک نهایی
        f"[v_main][faded_wm_final]overlay[ov];"
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
    
    # 🌟 لاگ دستور کامل FFmpeg
    print(f"--- FFmpeg CMD (Image Watermark):\n{cmd}\n---")
    
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
            error_lines = error_output.strip().splitlines()
            short_error = "\n".join(error_lines[-5:])
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


# ----------------------------------------------------------------------------------
## تابع تشخیصی FFmpeg
# ----------------------------------------------------------------------------------

async def get_ffmpeg_version():
    """اجرای دستور 'ffmpeg -version' و برگرداندن خط اول خروجی."""
    cmd = "ffmpeg -version"
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        # فقط خط اول که شامل شماره نسخه است را برمی‌گرداند
        return stdout.decode().split('\n')[0]
    except FileNotFoundError:
        return "❌ برنامه FFmpeg در مسیرهای سیستمی یافت نشد."
    except Exception as e:
        return f"❌ خطای اجرای دستور: {e}"
