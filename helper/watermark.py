import asyncio
import subprocess
import shlex


#############################################
# 1) WATERMARK TEXT
#############################################

async def add_text_watermark(input_path, output_path, text, position, font_size=40, color="white"):
    """
    واترمارک متنی کاملاً پایدار
    """
    pos_map = {
        "top-left":     "10:10",
        "top-right":    "(W-tw-10):10",
        "bottom-left":  "10:(H-th-10)",
        "bottom-right": "(W-tw-10):(H-th-10)",
        "center":       "(W-tw)/2:(H-th)/2"
    }

    x, y = pos_map.get(position, pos_map["bottom-right"])

    filter_complex = (
        f"drawtext=text='{text}':"
        f"fontsize={font_size}:fontcolor={color}:"
        f"x={x}:y={y}"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" "
        f"-vf \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-c:a copy \"{output_path}\" -y"
    )

    process = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(stderr.decode())


#############################################
# 2) WATERMARK IMAGE (نسخه کاملاً سالم برای Alpine)
#############################################

async def add_image_watermark(input_path, output_path, image_path, position="top-right", size_percent=20):
    """
    واترمارک تصویری با fade-in و fade-out + انیمیشن ورود از راست.
    بدون IF های تو‌در‌تو و کاملاً سازگار با FFmpeg Alpine.
    """

    # پوزیشن‌های ثابت
    pos_map = {
        "top-left":     ("20", "20"),
        "top-right":    ("W-w-20", "20"),
        "bottom-left":  ("20", "H-h-20"),
        "bottom-right": ("W-w-20", "H-h-20"),
        "center":       ("(W-w)/2", "(H-h)/2")
    }

    base_x, base_y = pos_map.get(position, pos_map["top-right"])

    # افکت – از راست وارد شود
    X = f"{base_x} - (1-t)*80"   # حرکت نرم
    Y = base_y

    # fade in + fade out بسیار سازگار
    FADE_IN  = "if(lte(t,1), t/1, 1)"          # ورود ۱ ثانیه
    FADE_OUT = "if(gte(t,7), (8-t)/1, 1)"      # خروج ۱ ثانیه
    ALPHA = f"{FADE_IN}*{FADE_OUT}"

    filter_complex = (
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva444p[wm];"
        f"[0:v][wm]overlay=x={X}:y={Y}:alpha={ALPHA}[outv]"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex '{filter_complex}' "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map [outv] -map 0:a:0? \"{output_path}\" -y"
    )

    process = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception("Watermark image error: " + stderr.decode())



#############################################
# 3) تست عمومی (اختیاری)
#############################################

async def test():
    await add_image_watermark(
        "input.mp4",
        "out.mp4",
        "logo.png",
        position="top-right",
        size_percent=25
    )
    print("DONE")


# asyncio.run(test())
