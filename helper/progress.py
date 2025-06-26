import time
from tqdm import tqdm

async def progress_bar(current, total, text, message, bar_length=20):
    percent = current * 100 / total
    filled = int(bar_length * percent // 100)
    bar = '█' * filled + '-' * (bar_length - filled)
    
    speed = current / (time.time() - message.date.timestamp()) if (time.time() - message.date.timestamp()) > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    
    await message.edit_text(
        f"{text}\n"
        f"[{bar}] {percent:.1f}%\n"
        f"{current / 1024 / 1024:.2f} MB از {total / 1024 / 1024:.2f} MB\n"
        f"سرعت: {speed / 1024:.2f} KB/s\n"
        f"زمان باقی‌مانده: {eta:.1f} ثانیه"
    )
