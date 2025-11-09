# نام فایل: helper/progress.py (ابزارهای نوار پیشرفت)
import time
from pyrogram.types import Message
import logging

logger = logging.getLogger(__name__)

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
        except Exception as e:
            logger.warning(f"Failed to edit progress message: {e}")

def human_readable_size(size):
    """تبدیل بایت به واحد‌های خوانا (KB, MB, GB)."""
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power and n < 3:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"
