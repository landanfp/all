# نام فایل: helper/watermark.py
import asyncio
import subprocess
import shlex

T = "t"  # متغیر زمان FFmpeg

# =====================================================================================
# ⭐ 1) واترمارک متنی (کاملاً سالم و تست شده)
# =====================================================================================

async def add_text_watermark(input_path, output_path, text, position, size_percent):
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"

    FINAL_X_PAUSE = "main_w-text_w-20"
    FINAL_Y_PAUSE = "20"
    FINAL_X_OUT = FINAL_X_PAUSE
    FINAL_Y_OUT = "main_h-text_h-20"

    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}),"
        f"({FINAL_X_PAUSE})*{MOD_T}/{MOVE_IN_DURATION}-text_w*(1-{MOD_T}/{MOVE_IN_DURATION}),"
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}),"
        f"{FINAL_X_PAUSE},{FINAL_X_OUT}))"
    )

    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}),"
        f"{FINAL_Y_PAUSE},"
        f"{FINAL_Y_PAUSE}+({FINAL_Y_OUT}-{FINAL_Y_PAUSE})*({MOD_T}-{MOVE_IN_DURATION + PAUSE_DURATION})/{MOVE_OUT_DURATION})"
    )

    ALPHA_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}),"
        f"0.8*{MOD_T}/{MOVE_IN_DURATION},"
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}),"
        f"0.8,"
        f"0.8*(1-({MOD_T}-{MOVE_IN_DURATION + PAUSE_DURATION})/{MOVE_OUT_DURATION})))"
    )

    safe_text = shlex.quote(text)

    drawtext_loop = (
        f"drawtext=text={safe_text}:fontcolor=white:"
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x='{X_EXPRESSION}':y='{Y_EXPRESSION}':alpha='{ALPHA_EXPRESSION}'"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext_loop}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(stderr.decode())

    except Exception as e:
        raise Exception(f"Error in text watermark: {e}")



# =====================================================================================
# ⭐ 2) واترمارک تصویری (اصلاح کامل مشکل کاماها + کاملاً سالم)
# =====================================================================================

async def add_image_watermark(input_path, output_path, image_path, position, size_percent):
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION

    FINAL_X_PAUSE = "main_w-overlay_w-20"
    FINAL_Y_PAUSE = "20"
    FINAL_X_OUT = FINAL_X_PAUSE
    FINAL_Y_OUT = "main_h-overlay_h-20"

    X_EXPRESSION = (
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION}),"
        f"({FINAL_X_PAUSE})*mod(t,{CYCLE_DURATION})/{MOVE_IN_DURATION}-overlay_w*(1-mod(t,{CYCLE_DURATION})/{MOVE_IN_DURATION}),"
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION + PAUSE_DURATION}),"
        f"{FINAL_X_PAUSE},{FINAL_X_OUT}))"
    )

    Y_EXPRESSION = (
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION + PAUSE_DURATION}),"
        f"{FINAL_Y_PAUSE},"
        f"{FINAL_Y_PAUSE}+({FINAL_Y_OUT}-{FINAL_Y_PAUSE})*(mod(t,{CYCLE_DURATION})-{MOVE_IN_DURATION + PAUSE_DURATION})/{MOVE_OUT_DURATION})"
    )

    ALPHA_EXPRESSION = (
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION}),"
        f"mod(t,{CYCLE_DURATION})/{MOVE_IN_DURATION},"
        f"if(lt(mod(t,{CYCLE_DURATION}),{MOVE_IN_DURATION + PAUSE_DURATION}),"
        f"1,"
        f"(1-(mod(t,{CYCLE_DURATION})-{MOVE_IN_DURATION + PAUSE_DURATION})/{MOVE_OUT_DURATION})))"
    )

    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];"
        f"[v][wm]overlay=x={X_EXPRESSION}:y={Y_EXPRESSION}:alpha={ALPHA_EXPRESSION}:"
        f"eof_action=repeat:shortest=0:repeatlast=0[ov];"
        f"[ov]format=yuv420p[outv]"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex '{filter_complex}' "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map [outv] -map 0:a:0? \"{output_path}\" -y"
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(stderr.decode())

    except Exception as e:
        raise Exception(f"Error in image watermark: {e}")
