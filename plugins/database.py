import os
import aiofiles
import time
from pyrogram.types import Message

async def download_file_stream(client, file_id, user_id, message: Message):
    file_path = f"{user_id}_original.mp4"

    async def progress(current, total):
        percent = current * 100 / total
        done = int(percent / 5)
        await message.edit_text(
            f"در حال دانلود: {percent:.1f}%
"
            f"حجم: {current / (1024*1024):.2f}MB / {total / (1024*1024):.2f}MB"
        )

    file = await client.download_media(file_id, file_name=file_path, progress=progress)
    return file

async def upload_to_log_channel(client, file_path, user_id, message: Message):
    async def progress(current, total):
        percent = current * 100 / total
        await message.edit_text(
            f"در حال آپلود: {percent:.1f}%
"
            f"حجم: {current / (1024*1024):.2f}MB / {total / (1024*1024):.2f}MB"
        )

    await client.send_document("me", document=file_path, caption="برش ویدیو کاربر")
