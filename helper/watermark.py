async def add_text_watermark(input_path, output_path, text, position, size_percent):
    """افزودن واترمارک متنی متحرک و محوشونده به ویدیو (با تکرار حلقوی)."""
    
    # 1. تنظیمات زمان‌بندی انیمیشن (ورود 2، مکث 4، خروج 1.5)
    MOVE_IN_DURATION = 2
    PAUSE_DURATION = 4
    MOVE_OUT_DURATION = 1.5 
    CYCLE_DURATION = MOVE_IN_DURATION + PAUSE_DURATION + MOVE_OUT_DURATION
    MOD_T = f"mod({T},{CYCLE_DURATION})"
    T_REL_IN = f"{MOD_T}/{MOVE_IN_DURATION}" # نسبت زمان در فاز ورود
    
    # 2. محاسبه مختصات نهایی در مرحله مکث (هدف: بالا-راست)
    FINAL_X_PAUSE = "main_w-text_w-20" 
    FINAL_Y_PAUSE = "20" 
    
    # 3. محاسبه مختصات شروع برای ورود (بالا-وسط)
    X_START_IN = "(main_w-text_w)/2"
    Y_START_IN = "(-text_h)" # شروع از بالای کادر

    # 4. تعریف انیمیشن (Expressionها)
    
    # A. موقعیت X: ورود از بالا-وسط، توقف در راست
    X_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            # حرکت از X_START_IN به FINAL_X_PAUSE
            f"({X_START_IN}) * (1 - {T_REL_IN}) + ({FINAL_X_PAUSE}) * {T_REL_IN}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_X_PAUSE}, "
            # در فاز خروج، موقعیت X ثابت می‌ماند
            f"{FINAL_X_PAUSE})" 
        ")"
    )

    # B. موقعیت Y: ورود از بالا-وسط به بالا-راست، ثابت در زمان خروج
    Y_EXPRESSION = (
        f"if(lt({MOD_T},{MOVE_IN_DURATION}), " 
            # حرکت از Y_START_IN به FINAL_Y_PAUSE
            f"({Y_START_IN}) * (1 - {T_REL_IN}) + ({FINAL_Y_PAUSE}) * {T_REL_IN}, "
        f"if(lt({MOD_T},{MOVE_IN_DURATION + PAUSE_DURATION}), " 
            f"{FINAL_Y_PAUSE}, "
            # در فاز خروج، موقعیت Y ثابت می‌ماند
            f"{FINAL_Y_PAUSE})"
        ")"
    )
    
    # C. محو شدن Alpha: محو شدن سریعتر (این قسمت نیازی به تغییر ندارد)
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
