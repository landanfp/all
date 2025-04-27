import time

async def progress_bar(current, total, text, message):
    now = time.time()
    percent = current * 100 / total
    speed = current / (now - message.date.timestamp())
    eta = (total - current) / speed if speed > 0 else 0
    await message.edit_text(f"{text}\n"
                             f"{percent:.1f}% انجام شده\n"
                             f"{current / 1024 / 1024:.2f} MB از {total / 1024 / 1024:.2f} MB\n"
                             f"سرعت: {speed / 1024:.2f} KB/s\n"
                             f"زمان باقی‌مانده: {eta:.1f} ثانیه")