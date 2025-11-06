# نام فایل: helper/progress.py (ابزارهای نوار پیشرفت)
import time
from pyrogram.types import Message

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

    # **** تغییر کلیدی برای افزایش سرعت: ****
    # جلوگیری از Flood Wait: آپدیت هر 8 ثانیه یکبار (به جای 5 ثانیه)
    # این کار تعداد وقفه‌ها برای ادیت پیام را کاهش داده و سرعت انتقال را "کمی" افزایش می‌دهد
    if int(diff) % 8 == 0 or percentage == 100 or percentage == 0:
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
