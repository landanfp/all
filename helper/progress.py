import time
import asyncio

async def progress_bar(current, total, text, message):
    now = time.time()
    if now - message.date.timestamp() < 1:  # به‌روزرسانی هر ۱ ثانیه
        return

    percent = current * 100 / total if total > 0 else 0
    speed = current / (now - message.date.timestamp()) if (now - message.date.timestamp()) > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    
    await message.edit_text(
        f"{text}\n"
        f"{percent:.1f}% انجام شده\n"
        f"{current / 1024 / 1024:.2f} MB از {total / 1024 / 1024:.2f} MB\n"
        f"سرعت: {speed / 1024:.2f} KB/s\n"
        f"زمان باقی‌مانده: {eta:.1f} ثانیه"
    )
    await asyncio.sleep(1)  # جلوگیری از به‌روزرسانی بیش از حد
