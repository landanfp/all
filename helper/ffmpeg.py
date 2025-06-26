import asyncio
import re
import os

async def add_hardsub(input_video, input_subtitle, output_video, message):
    cmd = (
        f'ffmpeg -y -i "{input_video}" -vf subtitles="{input_subtitle}":force_style="Fontsize=24,PrimaryColour=&HFFFFFF&" '
        f'-preset ultrafast -threads 1 -f mp4 -progress pipe:1 "{output_video}"'
    )
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE  # گرفتن خطاها
    )
    
    total_duration = None
    last_progress = 0
    error_output = []

    # خواندن خروجی و خطاها
    while True:
        line = await process.stdout.readline()
        error_line = await process.stderr.readline()
        if error_line:
            error_output.append(error_line.decode().strip())
        if not line:
            break
        line = line.decode().strip()
        
        # استخراج مدت زمان کل ویدیو
        if 'Duration' in line:
            match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
            if match:
                hours, minutes, seconds, _ = map(int, match.groups())
                total_duration = hours * 3600 + minutes * 60 + seconds
        
        # استخراج زمان فعلی پردازش
        if 'out_time_ms' in line:
            match = re.search(r'out_time_ms=(\d+)', line)
            if match and total_duration:
                current_time = int(match.group(1)) / 1000000  # تبدیل به ثانیه
                percent = (current_time / total_duration) * 100
                if percent - last_progress >= 1:  # آپدیت هر ۱ درصد
                    last_progress = percent
                    await message.edit_text(
                        f"⏳ در حال چسباندن زیرنویس...\n"
                        f"[{'█' * int(percent // 5)}{'-' * (20 - int(percent // 5))}] {percent:.1f}%"
                    )
    
    await process.communicate()
    
    # اگر خطایی وجود داشت، آن را برگردان
    if error_output:
        return False, "\n".join(error_output)
    return True, None
