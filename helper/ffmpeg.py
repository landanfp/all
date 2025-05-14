
# (c) @AbirHasan2005

# This is Telegram Video Watermark Adder Bot's Source Code.
# I Hardly Made This. So Don't Forget to Give Me Credits.
# Done this Huge Task for Free. If you guys not support me,
# I will stop making such things!

# Edit anything at your own risk!

# Don't forget to help me if I done any mistake in the codes.
# Support Group: @JoinOT

import os
import math
import re
import json
import subprocess
import time
import shlex
import asyncio
#from configs import Config
from typing import Tuple
from humanfriendly import format_timespan
from display_progress import TimeFormatter
from pyrogram.errors.exceptions.flood_420 import FloodWait


async def vidmark(the_media, message, working_dir, watermark_path, output_vid, total_time, logs_msg, status, mode, position, size):
    file_genertor_command = [
        "ffmpeg", "-hide_banner", "-loglevel", "quiet", "-progress", working_dir, "-i", the_media, "-i", watermark_path,
        "-filter_complex", f"[1][0]scale2ref=w='iw*{size}/100':h='ow/mdar'[wm][vid];[vid][wm]overlay={position}",
        "-c:v", "copy", "-preset", mode, "-crf", "0", "-c:a", "copy", output_vid
    ]
    COMPRESSION_START_TIME = time.time()
    process = await asyncio.create_subprocess_exec(
        *file_genertor_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    with open(status, 'r+') as f:
        statusMsg = json.load(f)
        statusMsg['pid'] = process.pid
        f.seek(0)
        json.dump(statusMsg, f, indent=2)
    while process.returncode != 0:
        await asyncio.sleep(5)
        with open(working_dir, 'r+') as file:
            text = file.read()
            frame = re.findall("frame=(\d+)", text)
            time_in_us=re.findall("out_time_ms=(\d+)", text)
            progress=re.findall("progress=(\w+)", text)
            speed=re.findall("speed=(\d+\.?\d*)", text)
            if len(frame):
                frame = int(frame[-1])
            else:
                frame = 1;
            if len(speed):
                speed = speed[-1]
            else:
                speed = 1;
            if len(time_in_us):
                time_in_us = time_in_us[-1]
            else:
                time_in_us = 1;
            if len(progress):
                if progress[-1] == "end":
                    break
            execution_time = TimeFormatter((time.time() - COMPRESSION_START_TIME)*1000)
            elapsed_time = int(time_in_us)/1000000
            difference = math.floor( (total_time - elapsed_time) / float(speed) )
            ETA = "-"
            if difference > 0:
                ETA = TimeFormatter(difference*1000)
            percentage = math.floor(elapsed_time * 100 / total_time)
            progress_str = "📊 **Progress:** {0}%\n`[{1}{2}]`".format(
                round(percentage, 2),
                ''.join(["▓" for i in range(math.floor(percentage / 10))]),
                ''.join(["░" for i in range(10 - math.floor(percentage / 10))])
                )
            stats = f'📦️ **Adding Watermark [Preset: `{mode}`]**\n\n' \
                    f'⏰️ **ETA:** `{ETA}`\n❇️ **Position:** `{position}`\n🔰 **PID:** `{process.pid}`\n🔄 **Duration: `{format_timespan(total_time)}`**\n\n' \
                    f'{progress_str}\n'
            try:
                await logs_msg.edit(text=stats)
                await message.edit(text=stats)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                pass
            except:
                pass

    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    print(e_response)
    print(t_response)
    if os.path.lexists(output_vid):
        return output_vid
    else:
        return None

async def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = output_directory + \
        "/" + str(time.time()) + ".jpg"
    file_genertor_command = [
        "ffmpeg",
        "-ss",
        str(ttl),
        "-i",
        video_file,
        "-vframes",
        "1",
        out_put_file_name
    ]
    process = await asyncio.create_subprocess_exec(
        *file_genertor_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    if os.path.lexists(out_put_file_name):
        return out_put_file_name
    else:
        return None

async def get_video_duration(video_path):
    if not video_path or not os.path.exists(video_path):
        print(f"فایل ویدیو برای get_video_duration یافت نشد: {video_path}")
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
                elif 'duration' in data: # برای برخی فرمت‌های json دیگر
                     return float(data['duration'])
            except json.JSONDecodeError:
                print(f"خطا در تجزیه JSON از ffprobe (duration): {stdout.decode()}")

        # Fallback if JSON parsing fails or no duration found
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
                 print(f"خطا در تبدیل خروجی ffprobe (default) به float: {stdout_fallback.decode().strip()}")
        else:
            # پرینت stderr اصلی اگر fallback هم شکست خورد
            print(f"خطا در دریافت مدت زمان با ffprobe (default): {stderr.decode() if stderr else (stderr_fallback.decode() if stderr_fallback else 'N/A')}")

    except FileNotFoundError:
        print("خطا: ffprobe پیدا نشد. لطفاً از نصب بودن FFmpeg (شامل ffprobe) و در دسترس بودن آن در PATH اطمینان حاصل کنید.")
    except Exception as e:
        print(f"استثنا در get_video_duration ({video_path}): {e}")
    return None

async def get_video_dimensions(video_path):
    if not video_path or not os.path.exists(video_path):
        print(f"فایل ویدیو برای get_video_dimensions یافت نشد: {video_path}")
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
                print(f"خطا در تجزیه JSON از ffprobe (dimensions): {stdout.decode()}")
        print(f"خطا در دریافت ابعاد ویدیو (ffprobe json): {stderr.decode() if stderr else 'N/A'}")
    except FileNotFoundError:
        print("خطا: ffprobe پیدا نشد.")
    except Exception as e:
        print(f"استثنا در get_video_dimensions ({video_path}): {e}")
    return 0, 0

async def generate_thumbnail(video_path, output_dir, seek_time_str="00:00:03.000"):
    if not video_path or not os.path.exists(video_path):
        print(f"فایل ویدیو برای generate_thumbnail یافت نشد: {video_path}")
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
            print(f"فرمت seek_time نامعتبر: {current_seek_time}. استفاده از مقدار پیش‌فرض یا ۱/۴ مدت زمان.")
            seek_seconds_default = min(3.0, duration / 4.0 if duration > 0 else 3.0)
            seek_s_def = int(seek_seconds_default)
            seek_ms_def = int((seek_seconds_default - seek_s_def) * 1000)
            current_seek_time = f"{seek_s_def // 3600:02d}:{(seek_s_def % 3600) // 60:02d}:{seek_s_def % 60:02d}.{seek_ms_def:03d}"
    else:
        print("امکان دریافت مدت زمان ویدیو برای تامبنیل نبود، از زمان جستجوی پیش‌فرض استفاده می‌شود.")

    command = [
        "ffmpeg", "-y",
        "-ss", current_seek_time,
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "3",
        thumbnail_path
    ]
    print(f"در حال تولید تامبنیل با دستور: {' '.join(command)}")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
        print(f"تامبنیل با موفقیت تولید شد: {thumbnail_path}")
        return thumbnail_path
    else:
        print(f"خطا در تولید تامبنیل برای {video_path}:")
        if stdout: print(f"FFmpeg STDOUT: {stdout.decode(errors='ignore')}")
        if stderr: print(f"FFmpeg STDERR: {stderr.decode(errors='ignore')}")
        return None

async def process_video_with_watermark(input_path, output_path, status_message, start_time_overall):
    total_duration_seconds = await get_video_duration(input_path)

    if total_duration_seconds is None:
        total_duration_seconds = 0
        print("هشدار: دریافت مدت زمان ویدیو ممکن نبود.")

    command = [
        "ffmpeg", "-hide_banner", "-i", input_path,
        "-vf", "drawtext=text='@SeriesPlus1':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,20)'",
        "-codec:a", "copy",
        "-progress", "pipe:1",
        "-y",
        output_path
    ]

    print(f"دستور FFmpeg: {' '.join(command)}")
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
            except ValueError: print(f"ناتوان در تجزیه out_time_us: {line}")
        elif line.startswith("out_time_ms="):
            try: milliseconds = int(line.split('=')[1]); current_time_seconds = milliseconds / 1000.0
            except ValueError: print(f"ناتوان در تجزیه out_time_ms: {line}")

        if current_time_seconds is not None and total_duration_seconds > 0:
            if time.time() - last_update_time > 5.0:
                await progress_bar(current_time_seconds, total_duration_seconds, status_message, "در حال افزودن واترمارک...", start_time_overall)
                last_update_time = time.time()
        elif line.startswith("progress=end"):
            if total_duration_seconds > 0:
                await progress_bar(total_duration_seconds, total_duration_seconds, status_message, "واترمارک در حال اتمام...", start_time_overall)
            print("پیشرفت FFmpeg پایان یافت.")

    stdout_data, stderr_data = await process.communicate()
    if stderr_data: print(f"FFmpeg STDERR: {stderr_data.decode('utf-8', errors='ignore')}")

    if process.returncode != 0:
        error_message_detail = stderr_data.decode('utf-8', errors='ignore') if stderr_data else "جزئیات بیشتر در دسترس نیست."
        error_message = f"خطا در پردازش ویدیو با FFmpeg. کد
