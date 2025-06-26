import time
import asyncio
from tqdm import tqdm

async def progress_bar(current, total, text, message):
    now = time.time()
    percent = current * 100 / total
    filled = int(20 * percent // 100)
    bar = '█' * filled + '-' * (20 - filled)
    
    speed = current / (now - message.date.timestamp()) if (now - message.date.timestamp()) > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    
    new_text = (
        f"{text}\n"
        f"[{bar}] {percent:.1f}%\n"
        f"{current / 1024 / 1024:.2f} MB از {total / 1024 / 1024:.2f} MB\n"
        f"سرعت: {speed / 1024:.2f} KB/s\n"
        f"زمان باقی‌مانده: {eta:.1f} ثانیه"
    )
    
    if not hasattr(message, '_last_text') or message._last_text != new_text:
        try:
            await message.edit_text(new_text)
            message._last_text = new_text
            await asyncio.sleep(1)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                print(f"خطا در ویرایش پیام پیشرفت: {e}")
