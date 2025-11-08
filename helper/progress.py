# نام فایل: helper/progress.py (ابزارهای نوار پیشرفت)
import time
from pyrogram.types import Message
import asyncio  # برای threadsafe

async def progress_bar(current, total, message: Message, start, stage="در حال پردازش"):
    """آپدیت پیام در حین دانلود/آپلود/پردازش برای نمایش پیشرفت."""
    now = time.time()
    diff = now - start

    if diff == 0:
        diff = 1

    percentage = current * 100 / total if total else 0
    speed = current / diff if diff > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    filled_blocks = int(percentage // 10)
    empty_blocks = 10 - filled_blocks
    bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}]"
    
    if stage == "watermark":
        # فرمت درخواستی
        progress_text = (
            f"{percentage:.1f}% {bar}\n"
            f"مدت زمان باقی تا اتمام: **{int(eta)}s**"
        )
    else:
        progress_text = (
            f"**مرحله {stage}**: {bar} **{percentage:.1f}%**\n"
            f"📥/📤 داده: **{human_readable_size(current)}** از **{human_readable_size(total)}**\n"
            f"⚡ سرعت: **{human_readable_size(speed)}/s**\n"
            f"⏱️ زمان تخمینی: **{int(eta)}s**"
        )

    # Flood wait prevention
    if int(now - start) % 5 == 0 or percentage >= 100 or percentage == 0:
        try:
            await message.edit_text(progress_text)  # edit_text برای safety
        except Exception as e:
            print(f"Edit error: {e}")
            pass

def human_readable_size(size):
    """تبدیل بایت به واحد‌های خوانا."""
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power and n < 3:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"
