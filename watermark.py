# watermark.py
import os
import asyncio
import json
from display import convert_size, progress_bar

async def get_video_duration(video_path):
    if not video_path or not os.path.exists(video_path):
        return None
    try:
        command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", video_path
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0 and stdout:
            try:
                data = json.loads(stdout.decode())
                if 'format' in data and 'duration' in data['format']:
                    return float(data['format']['duration'])
                elif 'duration' in data:
                     return float(data['duration'])
            except json.JSONDecodeError:
                pass

        command_fallback = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        process_fallback = await asyncio.create_subprocess_exec(
            *command_fallback,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_fallback, stderr_fallback = await process_fallback.communicate()
        if process_fallback.returncode == 0 and stdout_fallback:
            try:
                return float(stdout_fallback.decode().strip())
            except ValueError:
                 pass
        else:
            pass

    except FileNotFoundError:
        pass
    except Exception:
        pass
    return None

async def get_video_dimensions(video_path):
    if not video_path or not os.path.exists(video_path):
        return 0, 0
    try:
        command = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", video_path
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0 and stdout:
            try:
                data = json.loads(stdout.decode())
                if data.get("streams") and len(data["streams"]) > 0:
                    stream_data = data["streams"][0]
                    return stream_data.get("width", 0), stream_data.get("height", 0)
            except json.JSONDecodeError:
                pass
        pass
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return 0, 0

async def generate_thumbnail(video_path, output_dir, seek_time_str="00:00:03.000"):
    if not video_path or not os.path.exists(video_path):
        return None

    thumbnail_filename = os.path.splitext(os.path.basename(video_path))[0] + ".jpg"
    thumbnail_path = os.path.join(output_dir, thumbnail_filename)

    current_seek_time = seek_time_str
    duration = await get_video_duration(video_path)

    if duration is not None and duration > 0:
        try:
            h, m, s_full = current_seek_time.split(':')
            s, ms_str = s_full.split('.') if '.' in s_full else (s_full, "0")
            seek_seconds_requested = int(h) * 3600 + int(m) * 60 + float(s) + float(ms_str) / 1000

            if seek_seconds_requested >= duration or seek_seconds_requested < 0:
                seek_seconds_actual = duration / 4.0
            else:
                seek_seconds_actual = seek_seconds_requested

            seek_s_int = int(seek_seconds_actual)
            seek_ms_int = int((seek_seconds_actual - seek_s_int) * 1000)
            current_seek_time = f"{seek_s_int // 3600:02d}:{ (seek_s_int % 3600) // 60:02d}:{seek_s_int % 60:02d}.{seek_ms_int:03d}"
        except ValueError:
            seek_seconds_default = min(3.0, duration / 4.0 if duration > 0 else 3.0)
            seek_s_def = int(seek_seconds_default)
            seek_ms_def = int((seek_seconds_default - seek_s_def) * 1000)
            current_seek_time = f"{seek_s_def // 3600:02d}:{(seek_s_def % 3600) // 60:02d}:{seek_s_def % 60:02d}.{seek_ms_def:03d}"
    else:
        pass

    command = [
        "ffmpeg", "-y",
        "-ss", current_seek_time,
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "3",
        thumbnail_path
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
        return thumbnail_path
    else:
        return None

async def process_video_with_watermark(input_path, output_path, status_message, start_time_overall):
    total_duration_seconds = await get_video_duration(input_path)

    if total_duration_seconds is None:
        total_duration_seconds = 0

    command = [
        "ffmpeg", "-hide_banner", "-i", input_path,
        "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,20)'",
        "-codec:a", "copy",
        "-progress", "pipe:1",
        "-y",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    last_update_time = time.time()

    while True:
        line_bytes = await process.stdout.readline()
        if not line_bytes:
            break
        line = line_bytes.decode('utf-8', errors='ignore').strip()
        current_time_seconds = None
        if line.startswith("out_time_us="):
            try: microseconds = int(line.split('=')[1]); current_time_seconds = microseconds / 1000000.0
            except ValueError: pass
        elif line.startswith("out_time_ms="):
            try: milliseconds = int(line.split('=')[1]); current_time_seconds = milliseconds / 1000.0
            except ValueError: pass

        if current_time_seconds is not None and total_duration_seconds > 0:
            if time.time() - last_update_time > 5.0:
                await progress_bar(current_time_seconds, total_duration_seconds, status_message, "در حال افزودن واترمارک...", start_time_overall)
                last_update_time = time.time()
        elif line.startswith("progress=end"):
            if total_duration_seconds > 0:
                await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک در حال اتمام...", start_time_overall)

    stdout_data, stderr_data = await process.communicate()

    if process.returncode != 0:
        error_message_detail = stderr_data.decode('utf-8', errors='ignore') if stderr_data else "جزئیات بیشتر در دسترس نیست."
        error_message = f"خطا در پردازش ویدیو با FFmpeg. کد بازگشت: {process.returncode}\nجزئیات: {error_message_detail[:1000]}"
        try: await status_message.edit(error_message)
        except Exception: pass
        raise Exception(error_message)
    else:
        if total_duration_seconds > 0:
            await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک کامل شد.", start_time_overall)
        else:
            final_output_size_str = ""
            if os.path.exists(output_path): final_output_size_str = f" حجم فایل خروجی: {convert_size(os.path.getsize(output_path))}"
            await status_message.edit(f"واترمارک کامل شد.{final_output_size_str}")
