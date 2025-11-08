# نام فایل: helper/progress.py (ابزارهای نوار پیشرفت)
import time
from pyrogram.types import Message
import re # اضافه شد

# اضافه شدن آرگومان 'stage' برای مدیریت نمایش مراحل مختلف
async def progress_bar(current, total, message: Message, start, stage="در حال پردازش"):
    """آپدیت پیام در حین دانلود/آپلود برای نمایش پیشرفت."""
    now = time.time()
    diff = now - start

    if diff == 0:
        diff = 1

    percentage = current * 100 / total
    speed = current / diff
    eta = (total - current) / speed

    filled_blocks = int(percentage // 10)
    empty_blocks = 10 - filled_blocks
    bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}]"
    
    progress_text = (
        f"**مرحله {stage}**: {bar} **{percentage:.1f}%**\n"
        f"📥/📤 داده: **{human_readable_size(current)}** از **{human_readable_size(total)}**\n"
        f"⚡ سرعت: **{human_readable_size(speed)}/s**\n"
        f"⏱️ زمان تخمینی: **{int(eta)}s**"
    )

    # جلوگیری از Flood Wait: تنها اگر 5 ثانیه از آخرین ویرایش گذشته باشد یا درصد کامل شده باشد
    if int(diff) % 5 == 0 or percentage == 100 or percentage == 0:
        try:
            await message.edit(progress_text)
        except Exception:
            pass # نادیده گرفتن خطاهای ویرایش

def human_readable_size(size):
    """تبدیل بایت به واحد‌های خوانا (KB, MB, GB)."""
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power and n < 3:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

# تابع جدید برای نمایش پیشرفت واترمارک‌گذاری (بر اساس زمان ویدیو)
def time_to_seconds(time_str):
    """تبدیل رشته زمان (HH:MM:SS.ms) FFmpeg به ثانیه."""
    if not time_str:
        return 0
    try:
        parts = time_str.split(':')
        seconds = float(parts[-1])
        if len(parts) > 1:
            seconds += int(parts[-2]) * 60
        if len(parts) > 2:
            seconds += int(parts[-3]) * 3600
        return seconds
    except:
        return 0
        
def format_time_progress(current_seconds, total_seconds, start_time):
    """Generates the progress text for FFmpeg processing based on time."""
    if total_seconds == 0:
        return "**0.0%** [░░░░░░░░░░]\nمدت زمان باقی تا اتمام : ..."

    now = time.time()
    elapsed_real = now - start_time
    
    # محاسبه درصد بر اساس زمان ویدیو
    percentage = (current_seconds / total_seconds) * 100
    percentage = max(0, min(100, percentage))

    # محاسبه ETA
    if current_seconds > 0 and elapsed_real > 0:
        video_time_rate = current_seconds / elapsed_real
        remaining_video_time = total_seconds - current_seconds
        eta_seconds = remaining_video_time / video_time_rate
    else:
        eta_seconds = 0

    filled_blocks = int(percentage // 10)
    empty_blocks = 10 - filled_blocks
    bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}]"
    
    # فرمت ETA به MM:SS یا HH:MM:SS
    if percentage >= 99.9: # 100%
        eta_formatted = "00:00"
    elif eta_seconds > 3600:
        eta_formatted = time.strftime('%H:%M:%S', time.gmtime(int(eta_seconds)))
    elif eta_seconds > 0:
        eta_formatted = time.strftime('%M:%S', time.gmtime(int(eta_seconds)))
    else:
        eta_formatted = "..."

    # فرمت درخواستی شما
    progress_text = (
        f"**{percentage:.1f}%** {bar}\n"
        f"مدت زمان باقی تا اتمام : **{eta_formatted}**"
    )

    return progress_text
