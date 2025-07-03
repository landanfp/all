import time

async def progress_bar(current, total, msg_type, message):
    now = time.time()
    if not hasattr(progress_bar, "last_time"):
        progress_bar.last_time = now

    if now - progress_bar.last_time > 1:
        progress_bar.last_time = now
        percent = current * 100 / total
        bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
        speed = current / (now - message.date.timestamp() + 1)
        eta = (total - current) / speed if speed != 0 else 0
        await message.reply_text(
            f"{msg_type}...\n"
            f"{bar} {percent:.2f}%\n"
            f"{human_readable(current)} / {human_readable(total)}\n"
            f"📶 سرعت: {human_readable(speed)}/s\n"
            f"⏳ زمان باقی‌مانده: {int(eta)} ثانیه", 
            quote=True
        )

def human_readable(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"
