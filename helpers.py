import math
import time

async def progress_bar(current, total, message, status_text):
    now = time.time()
    diff = now - getattr(message, 'last_progress', now)
    if diff < 1:
        return

    percentage = current * 100 / total
    bar_length = 20
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)

    speed = current / diff / 1024  # KB/s
    elapsed = int(diff)
    try:
        eta = int((total - current) / (current / elapsed))
    except:
        eta = 0

    await status_text.edit(
        f"{message.text}\n"
        f"[{bar}] {percentage:.2f}%\n"
        f"📦 {human_readable(current)} / {human_readable(total)}\n"
        f"⚡️ {speed:.2f} KB/s | ⏳ {eta}s"
    )

    message.last_progress = now

def human_readable(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024**3:
        return f"{size / 1024**2:.2f} MB"
    else:
        return f"{size / 1024**3:.2f} GB"
