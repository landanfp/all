import asyncio
import subprocess

async def add_hardsub(input_video, input_subtitle, output_video):
    # تنظیمات FFmpeg برای ذخیره خروجی روی دیسک
    cmd = (
        f'ffmpeg -y -i "{input_video}" '
        f'-vf subtitles="{input_subtitle}":force_style="Fontsize=24,PrimaryColour=&HFFFFFF&" '
        f'-preset ultrafast -threads 1 -maxrate 2000k -bufsize 4000k '
        f'-c:v libx264 -c:a aac -b:a 128k -f mp4 "{output_video}"'
    )
    print(f"[DEBUG] FFmpeg command: {cmd}")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")
        print(f"[DEBUG] FFmpeg completed successfully")
    except Exception as e:
        print(f"[DEBUG] FFmpeg error: {str(e)}")
        raise Exception(f"خطا در پردازش FFmpeg: {str(e)}")
