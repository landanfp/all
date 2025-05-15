import time
from pyrogram.types import Message

async def progress_bar(current, total, message: Message, start):
    now = time.time()
    diff = now - start

    if diff == 0:
        diff = 1

    percentage = current * 100 / total
    speed = current / diff
    eta = (total - current) / speed

    bar = f"[{'█' * int(percentage // 10)}{' ' * (10 - int(percentage // 10))}]"
    progress_text = (
        f"{bar} {percentage:.1f}%\n"
        f"Downloaded: {human_readable_size(current)} of {human_readable_size(total)}\n"
        f"Speed: {human_readable_size(speed)}/s\n"
        f"ETA: {int(eta)}s"
    )

    try:
        await message.edit(progress_text)
    except:
        pass

def human_readable_size(size):
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"
