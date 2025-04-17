import os
from pyrogram.types import Message

async def download_file_stream(client, file_id, user_id, message: Message):
    file_path = f"{user_id}_original.mp4"

    async def progress(current, total):
        # نمایش حجم دانلود شده و کل حجم
        await message.edit_text(
            f"در حال دانلود...\n"
            f"حجم: {current / (1024*1024):.2f}MB / {total / (1024*1024):.2f}MB"
        )

    file = await client.download_media(file_id, file_name=file_path, progress=progress)
    return file

# حذف بخش ارسال فایل به کانال لاگ
async def upload_to_log_channel(client, file_path, user_id, message: Message):
    # این تابع حذف شد، چون نیازی به ارسال فایل به کانال لاگ نیست.
    pass
