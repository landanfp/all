# نام فایل: helper/watermark.py (نسخه نهایی و ایمن شده برای FFmpeg)
import asyncio
import os
import subprocess
import shlex

# تعریف متغیر زمان اصلی FFmpeg
T = "t" 

# توابع کمکی برای تولید و ایمن‌سازی Expressionهای FFmpeg
def create_text_expressions():
    """ایجاد Expressionهای FFmpeg برای واترمارک متنی با نقل‌قول‌گذاری ایمن."""
    
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"
    
    FINAL_X_PAUSE = "main_w-text_w-20" 
    FINAL_Y_PAUSE = "20" 
    START_X_IN = "(main_w-text_w)/2"
    START_Y_IN = "-text_h"

    FADE_OUT_START_TIME = MOVE_IN_DURATION + PAUSE_DURATION + (MOVE_OUT_DURATION * 0.5)
    
    # 1. X_EXPRESSION (ورود از بالا-وسط، توقف در راست)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), {START_X_IN}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), {FINAL_X_PAUSE}, {FINAL_X_PAUSE}))"
    ).replace('\'', '\\\'')

    # 2. Y_EXPRESSION (ورود از بالای صفحه به بالا، حرکت مستقیم به پایین)
    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), "
            f"{START_Y_IN} + ({FINAL_Y_PAUSE} - {START_Y_IN}) * {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), {FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + (main_h-text_h-20 - {FINAL_Y_PAUSE}) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
    ).replace('\'', '\\\'')
    
    # 3. ALPHA_EXPRESSION (محو شدن زودتر در خروج)
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), 0.8 * {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), 0.8, "
        f"if(lt({MOD_T},{FADE_OUT_START_TIME}), 0.8, "
        f"0.8 * (1 - ({MOD_T} - {FADE_OUT_START_TIME}) / ({CYCLE_DURATION} - {FADE_OUT_START_TIME}))))"
    ).replace('\'', '\\\'')
    
    return X_EXPRESSION, Y_EXPRESSION, ALPHA_EXPRESSION

def create_image_expressions():
    """ایجاد Expressionهای FFmpeg برای واترمارک تصویری با نقل‌قول‌گذاری ایمن."""

    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"
    
    FINAL_X_PAUSE = "main_w-overlay_w-20"
    FINAL_Y_PAUSE = "20" 

    # 1. X_EXPRESSION (ورود از چپ، توقف در راست)
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            f"({FINAL_X_PAUSE}) * {MOD_T} / {MOVE_IN_DURATION} - overlay_w * (1 - {MOD_T} / {MOVE_IN_DURATION}), "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            f"{FINAL_X_PAUSE})"
        ")"
    ).replace('\'', '\\\'')

    # 2. Y_EXPRESSION (ورود، توقف در بالا، حرکت مستقیم به پایین)
    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            f"{FINAL_Y_PAUSE} + (main_h-overlay_h-20 - {FINAL_Y_PAUSE}) * ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION})"
    ).replace('\'', '\\\'')
    
    # 3. ALPHA_EXPRESSION (محو شدن)
    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), {MOD_T} / {MOVE_IN_DURATION}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), 1, "
        f"(1 - ({MOD_T} - {MOVE_IN_DURATION + PAUSE_DURATION}) / {MOVE_OUT_DURATION}))"
    ).replace('\'', '\\\'')
    
    return X_EXPRESSION, Y_EXPRESSION, ALPHA_EXPRESSION


async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    X_EXPRESSION, Y_EXPRESSION, ALPHA_EXPRESSION = create_text_expressions()
    
    safe_text = shlex.quote(text)
    
    # تعریف فیلتر Drawtext
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
    
    X_EXPRESSION, Y_EXPRESSION, ALPHA_EXPRESSION = create_image_expressions()

    # ساخت فیلتر `filter_complex`
    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];" 
        
        f"[v][wm]overlay=x='{X_EXPRESSION}':"
        f"y='{Y_EXPRESSION}':"
        f"alpha='{ALPHA_EXPRESSION}':" 
        f"eof_action=repeat[ov];" 
        f"[ov]format=yuv420p[outv]" 
    )

    # ساخت دستور FFmpeg
    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 " 
        f"-g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y" 
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
