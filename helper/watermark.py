import subprocess
import os

# ────────────────────────────────────────────────
#   TEXT WATERMARK
# ────────────────────────────────────────────────
async def add_text_watermark(input_path, output_path, text, position="top-left", fontsize=36):
    """
    افزودن واترمارک متنی ساده روی ویدیو با بررسی مسیرها
    """
    if not os.path.isfile(input_path):
        return f"Error: Input file does not exist: {input_path}"

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            return f"Error: Cannot create output directory: {output_dir}, {e}"

    try:
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
            f"drawtext=text='{text}':fontcolor=white:fontsize={fontsize}:x={pos.split(':')[0]}:y={pos.split(':')[1]}",
            "-codec:a", "copy",
            "-y",
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            return f"Error: Output file is empty or not created: {output_path}"

    except subprocess.CalledProcessError as e:
        return f"Text watermark FFmpeg error: {e.stderr.decode()}"
    except Exception as e:
        return f"Text watermark error: {str(e)}"


# ────────────────────────────────────────────────
#   IMAGE WATERMARK
# ────────────────────────────────────────────────
async def add_image_watermark(input_path, output_path, watermark_path, position="top-right", scale=0.25):
    """
    افزودن واترمارک تصویری ساده روی ویدیو با بررسی مسیرها
    """
    if not os.path.isfile(input_path):
        return f"Error: Input file does not exist: {input_path}"
    if not os.path.isfile(watermark_path):
        return f"Error: Watermark image does not exist: {watermark_path}"

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            return f"Error: Cannot create output directory: {output_dir}, {e}"

    try:
        positions = {
            "top-left": "10:10",
            "top-right": "main_w-overlay_w-10:10",
            "bottom-left": "10:main_h-overlay_h-10",
            "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
            "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
        }
        pos = positions.get(position, "main_w-overlay_w-10:10")

        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-i", watermark_path,
            "-filter_complex",
            f"[1:v]scale=iw*{scale}:-1[wm];[0:v][wm]overlay={pos}",
            "-codec:a", "copy",
            "-y",
            output_path
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            return f"Error: Output file is empty or not created: {output_path}"

    except subprocess.CalledProcessError as e:
        return f"Image watermark FFmpeg error: {e.stderr.decode()}"
    except Exception as e:
        return f"Image watermark error: {str(e)}"


# ────────────────────────────────────────────────
#   نمونه اجرا (Test)
# ────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    async def test():
        video_in = "input.mp4"
        video_out_text = "output_text.mp4"
        video_out_image = "output_image.mp4"
        watermark_img = "logo.png"

        # واترمارک متنی
        result1 = await add_text_watermark(video_in, video_out_text, "Hello World", position="bottom-right")
        print(result1)

        # واترمارک تصویری
        result2 = await add_image_watermark(video_in, video_out_image, watermark_img, position="top-left", scale=0.2)
        print(result2)

    asyncio.run(test())
