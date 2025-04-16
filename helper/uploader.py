import os
import time
from pyrogram import Client
from pyrogram.types import Message
from helper.utils import readable_size, progress_bar

async def upload_with_progress(client: Client, chat_id: int, file_path: str, message: Message, caption=None, as_audio=False):
    total_size = os.path.getsize(file_path)
    uploaded = 0
    start_time = time.time()

    async def progress(current, total):
        nonlocal uploaded
        uploaded = current
        now = time.time()
        percent = current * 100 / total
        speed = current / (now - start_time)
        eta = (total - current) / speed if speed > 0 else 0

        bar = progress_bar(percent)
        text = (
            f"{bar} {percent:.1f}%
"
            f"حجم انجام شده: {readable_size(current)}
"
            f"حجم کل فایل: {readable_size(total)}
"
            f"سرعت: {readable_size(speed)}/s
"
            f"زمان باقی‌مانده: {int(eta)} ثانیه"
        )
        try:
            await message.edit(text)
        except:
            pass

    if as_audio:
        await client.send_audio(
            chat_id=chat_id,
            audio=file_path,
            caption=caption,
            progress=progress
        )
    else:
        await client.send_video(
            chat_id=chat_id,
            video=file_path,
            caption=caption,
            progress=progress
        )

    os.remove(file_path)