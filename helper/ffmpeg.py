import asyncio
import subprocess

async def add_hardsub_stream(client, message, input_video, input_subtitle, processing_msg):
    # تنظیمات FFmpeg برای استریم ویدیو (فایل زیرنویس روی دیسک)
    cmd = (
        f'ffmpeg -y -i "{input_video}" '
        f'-vf subtitles="{input_subtitle}":force_style="Fontsize=24,PrimaryColour=&HFFFFFF&" '
        f'-preset ultrafast -threads 1 -maxrate 2000k -bufsize 4000k '
        f'-c:v libx264 -c:a aac -b:a 128k -f mp4 pipe:'
    )
    print(f"[DEBUG] FFmpeg command: {cmd}")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # آپلود مستقیم خروجی FFmpeg به تلگرام
        await client.send_video(
            chat_id=message.chat.id,
            video=proc.stdout,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!"
        )
        print(f"[DEBUG] Video uploaded successfully")

        # گرفتن خطاهای احتمالی
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")

    except Exception as e:
        print(f"[DEBUG] FFmpeg error: {str(e)}")
        raise Exception(f"خطا در پردازش استریم FFmpeg: {str(e)}")
