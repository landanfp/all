from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
# فرض بر وجود فایل loader.py و شیء app است
from loader import app 
import asyncio
import time
import subprocess
import os
import re
import math

# ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه

def human_readable_size(size: int) -> str:
    """تبدیل بایت به واحد خوانا (B, KB, MB, GB, TB)."""
    if size == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

async def progress_callback(current: int, total: int, message: Message, progress_data: dict, phase: str):
    """
    تابع کال‌بک برای نمایش نوار پیشرفت دانلود یا آپلود.
    """
    
    # برای جلوگیری از ویرایش بیش از حد
    if time.time() - progress_data.get('last_update_time', 0) < 3:
        return
    
    percent = (current * 100) / total
    bar_length = 10
    filled_length = int(bar_length * percent // 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    time_elapsed = time.time() - progress_data.get('last_update_time', progress_data['start_time'])
    bytes_transferred_since_last_update = current - progress_data.get('last_transferred_size', 0)
    
    if time_elapsed > 0:
        speed = bytes_transferred_since_last_update / time_elapsed
        speed_str = human_readable_size(speed) + "/s"
    else:
        speed_str = "N/A"
        
    progress_text = (
        f"**{phase}**\n"
        f"**[{percent:.1f}%]** **{bar}**\n"
        f"**✅ حجم انجام شده:** `{human_readable_size(current)}`\n"
        f"**💽 حجم کل فایل:** `{human_readable_size(total)}`\n"
        f"**🚀 سرعت:** `{speed_str}`"
    )
    
    try:
        await message.edit_text(progress_text)
        progress_data['last_update_time'] = time.time()
        progress_data['last_transferred_size'] = current
    except Exception:
        pass


@app.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        user_id = message.from_user.id
        now = time.time()

        user_sessions[user_id] = {
            'srt_file_id': message.document.file_id,
            'timestamp': now,
            'ffmpeg_running': False # وضعیت اولیه: در انتظار ویدیو
        }

        await message.reply_text("✅ فایل زیرنویس دریافت شد. حالا لطفاً ویدیوی خود را ارسال کنید.")
        asyncio.create_task(expire_session(user_id))

async def expire_session(user_id):
    await asyncio.sleep(SESSION_TIMEOUT)
    session = user_sessions.get(user_id)
    # اگر سشن وجود داشت و هنوز تبدیل به عملیات FFmpeg فعال نشده بود، آن را حذف کن.
    if session and (time.time() - session['timestamp'] >= SESSION_TIMEOUT) and not session.get('ffmpeg_running', False):
        user_sessions.pop(user_id, None)

async def read_ffmpeg_output(stdout_stream, progress_data):
    """تسک: خروجی FFmpeg را از stdout می‌خواند و داده‌ها را ذخیره می‌کند."""
    while True:
        try:
            line = await stdout_stream.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8')
            
            if '=' in line_str:
                key, value = line_str.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'out_time_ms':
                    try:
                        ms = int(value)
                        seconds = ms // 1000000
                        minutes = seconds // 60
                        hours = minutes // 60
                        seconds = seconds % 60
                        
                        progress_data['time'] = f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}.{ms % 1000000 // 10000:02}"
                    except ValueError:
                        pass
                elif key == 'speed':
                    progress_data['speed'] = value
        except asyncio.CancelledError:
            break
        except Exception:
            break

async def update_message_periodically(processing_msg, progress_data):
    """تسک: پیام را هر ۳ ثانیه با آخرین داده‌ها به‌روزرسانی می‌کند."""
    last_message_text = ""
    while True:
        # مطمئن می‌شویم که progress_data حاوی کلیدهای مورد نیاز است
        current_time = progress_data.get('time', "00:00:00.00")
        current_speed = progress_data.get('speed', "0.00x")
        
        new_message_text = (
            f"⏳ در حال هاردساب... \n"
            f"مدت زمان هاردساب شده: **{current_time}** \n"
            f"سرعت: **{current_speed}**"
        )
        
        if new_message_text != last_message_text:
            try:
                await processing_msg.edit_text(new_message_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_hardsub")]]))
                last_message_text = new_message_text
            except Exception:
                # اگر پیام حذف شده یا خطایی در ویرایش رخ داد، از تسک خارج شو
                break
        
        try:
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
            
@app.on_message(filters.video & filters.private)
async def handle_video_file(client, message: Message):
    user_id = message.from_user.id
    
    # اطمینان از اینکه عملیات قبلی وجود ندارد
    if user_id in user_sessions and user_sessions[user_id].get('ffmpeg_running', False):
        await message.reply_text("⚠️ یک عملیات در حال اجرا دارید. لطفاً صبر کنید یا آن را لغو کنید.")
        return

    if user_id not in user_sessions or 'srt_file_id' not in user_sessions[user_id]:
        await message.reply_text("⚠️ ابتدا باید فایل زیرنویس (.srt) را ارسال کنید.")
        return

    # مسیرهای موقت فایل
    video_path = None
    srt_path = None
    output_path = f"hardsub_{user_id}.mp4"
    processing_msg = None

    try:
        # 1. دانلود فایل‌ها
        processing_msg = await message.reply_text("⏳ در حال دانلود فایل‌ها...")
        download_progress_data = {'start_time': time.time(), 'last_update_time': 0, 'last_transferred_size': 0}

        srt_file_id = user_sessions[user_id]['srt_file_id']
        srt_path = await client.download_media(srt_file_id)
        
        video_path = await client.download_media(
            message,
            progress=progress_callback,
            progress_args=(processing_msg, download_progress_data, "⏳ در حال دانلود...")
        )

        await processing_msg.edit_text(
            "⏳ در حال هاردساب... لطفاً صبر کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_hardsub")]])
        )

        # 2. شروع فرآیند FFmpeg
        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path, '-vf', f'subtitles={srt_path}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'aac', '-b:a', '128k',
            '-y', output_path, '-nostats', '-progress', 'pipe:1'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        
        # ثبت وضعیت فرآیند
        user_sessions[user_id]['ffmpeg_process'] = process
        user_sessions[user_id]['ffmpeg_running'] = True # شروع عملیات

        
        progress_data = {'time': "00:00:00.00", 'speed': "0.00x"}
        
        reader_task = asyncio.create_task(read_ffmpeg_output(process.stdout, progress_data))
        updater_task = asyncio.create_task(update_message_periodically(processing_msg, progress_data))
        
        # منتظر می‌مانیم تا فرآیند خاتمه یابد
        exit_code = await process.wait()
        
        # لغو تسک‌های مانیتورینگ
        reader_task.cancel()
        updater_task.cancel()
        
        try:
            await asyncio.gather(reader_task, updater_task)
        except asyncio.CancelledError:
            pass
            
        await asyncio.sleep(1)
        
        # 3. بررسی وضعیت نهایی و تصمیم‌گیری برای آپلود
        
        # اگر کاربر دکمه لغو را فشار داده باشد، 'ffmpeg_running' باید False شده باشد
        user_cancelled = not user_sessions.get(user_id, {}).get('ffmpeg_running', True)
        
        if user_cancelled:
            # حالت ۱: لغو توسط کاربر
            await processing_msg.delete()
            await message.reply_text("✅ عملیات با موفقیت لغو شد و فایل آپلود نشد.")
            
        elif exit_code != 0:
            # حالت ۲: شکست FFmpeg با کد خروج غیر صفر (و لغو نشده)
            await processing_msg.edit_text(f"❌ هاردساب ناموفق بود. FFmpeg با کد خروج `{exit_code}` خاتمه یافت. لطفاً زیرنویس یا ویدیو را بررسی کنید.")
            
        else:
            # حالت ۳: موفقیت (exit_code == 0 و user_cancelled == False)
            upload_progress_data = {'start_time': time.time(), 'last_update_time': 0, 'last_transferred_size': 0}
            
            # برای آپلود از پیام در حال پردازش استفاده می‌کنیم
            await client.send_video(
                chat_id=message.chat.id,
                video=output_path,
                caption="✅ ویدیو با زیرنویس اضافه شده آماده است!",
                progress=progress_callback,
                progress_args=(processing_msg, upload_progress_data, "⬆️ در حال آپلود...")
            )
            
            await processing_msg.delete()


    except Exception as e:
        if processing_msg:
            await processing_msg.edit_text(f"❌ خطایی رخ داد: {type(e).__name__}\n\nجزئیات خطا:\n`{e}`")
        else:
            await message.reply_text(f"❌ خطایی رخ داد: {type(e).__name__}\n\nجزئیات خطا:\n`{e}`")
        print(f"An error occurred: {type(e).__name__} - {e}")

    finally:
        # پاکسازی فایل‌ها و اطلاعات سشن
        user_sessions.pop(user_id, None)
        for path in [video_path, srt_path, output_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"خطا در پاکسازی فایل‌ها: {e}")

@app.on_callback_query(filters.regex("cancel_hardsub"))
async def cancel_hardsub_handler(client, callback_query):
    user_id = callback_query.from_user.id
    
    # پاسخ دادن به کال‌بک (نمایش پیام موقت برای کاربر)
    await callback_query.answer("در حال لغو عملیات...")
    
    if user_id in user_sessions:
        # این مهم‌ترین خط است: وضعیت را به "لغو شده" تغییر می‌دهد
        user_sessions[user_id]['ffmpeg_running'] = False

        if 'ffmpeg_process' in user_sessions[user_id] and user_sessions[user_id]['ffmpeg_process'].returncode is None:
            process = user_sessions[user_id]['ffmpeg_process']
            try:
                # پایان دادن به فرآیند
                process.terminate()
                await process.wait()
                
                # تابع اصلی (handle_video_file) پس از اتمام فرآیند، پیام موفقیت‌آمیز لغو را نمایش خواهد داد.
                # اینجا فقط پیام فعلی را ویرایش می‌کنیم تا کاربر ببیند لغو انجام شده است.
                await callback_query.message.edit_text("✅ درخواست لغو دریافت شد. منتظر پاکسازی...")
            except ProcessLookupError:
                await callback_query.message.edit_text("⚠️ عملیات قبلاً متوقف شده بود.")
            except Exception as e:
                await callback_query.message.edit_text(f"❌ خطایی در هنگام لغو رخ داد: {e}")
        else:
            await callback_query.message.edit_text("⚠️ هیچ عملیات فعالی برای لغو وجود ندارد.")
    else:
        await callback_query.message.edit_text("⚠️ هیچ عملیات فعالی برای لغو وجود ندارد.")
