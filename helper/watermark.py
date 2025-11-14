import subprocess
import os


# ────────────────────────────────────────────────
#   TEXT WATERMARK
# ────────────────────────────────────────────────

async def add_text_watermark(input_path, output_path, text, position="top-left"):
    try:
        # مختصات ساده
        positions = {
            "top-left": "10:10",
            "top-right": "W-tw-10:10",
            "bottom-left": "10:H-th-10",
            "bottom-right": "W-tw-10:H-th-10",
            "center": "(W-tw)/2:(H-th)/2"
        }

        pos = positions.get(position, "10:10")

        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf",
            f"drawtext=text='{text}':fontcolor=white:fontsize=36:x={pos.split(':')[0]}:y={pos.split(':')[1]}",
            "-codec:a", "copy",
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    
    except Exception as e:
        return f"Text watermark error: {e}"




# ────────────────────────────────────────────────
#   IMAGE WATERMARK WITH FADE-IN ANIMATION
#   (100% compatible with FFmpeg Alpine)
# ────────────────────────────────────────────────

async def add_image_watermark(input_path, output_path, watermark_path, position="top-right", scale=0.25):
    try:
        # موقعیت‌ها
        positions = {
            "top-left": "10:10",
            "top-right": "main_w-overlay_w-10:10",
            "bottom-left": "10:main_h-overlay_h-10",
            "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
            "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
        }

        pos = positions.get(position, "main_w-overlay_w-10:10")

        # fade-in = لوگو در یک ثانیه اول آرام ظاهر می‌شود
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-i", watermark_path,

            "-filter_complex",
            f"[1:v]format=rgba,scale=iw*{scale}:-1,"
            f"fade=t=in:st=0:d=1:alpha=1[wm];"
            f"[0:v][wm]overlay={pos}[vout]",

            "-map", "[vout]",
            "-map", "0:a?",
            "-c:a", "copy",
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True

    except Exception as e:
        return f"Watermark image error: {e}"
