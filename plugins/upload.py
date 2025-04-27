from pyrogram import Client, filters
from helper.progress import progress_bar

@Client.on_message(filters.document)
async def catch_subtitle(client, message):
    # فرض بر اینه که فایل srt باشه و تو مرحله بعد hardsub بشه
    await message.download(file_name="subtitle.srt", progress=progress_bar, progress_args=("دانلود زیرنویس", message))
    await message.reply_text("زیرنویس دریافت شد. حالا ویدیوت رو هم بفرست!")
