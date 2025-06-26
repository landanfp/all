from pyrogram import Client, filters
from helper.progress import progress_bar
from loader import app

@app.on_message(filters.document & filters.private)
async def catch_subtitle(client, message):
    if message.document.file_size > 10 * 1024 * 1024:  # حداکثر ۱۰ مگابایت
        await message.reply_text("⚠️ فایل زیرنویس بیش از حد بزرگ است (حداکثر ۱۰ مگابایت).")
        return

    await message.download(file_name=f"subtitle_{message.from_user.id}.srt", progress=progress_bar, progress_args=("دانلود زیرنویس", message))
    await message.reply_text("✅ زیرنویس دریافت شد. حالا ویدیوت رو هم بفرست!")
