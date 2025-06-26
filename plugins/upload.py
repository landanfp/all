from pyrogram import Client, filters
from helper.progress import progress_bar
from loader import app

@app.on_message(filters.document)
async def catch_subtitle(client, message):
    processing_msg = await message.reply_text("⏳ در حال دانلود زیرنویس...")
    await message.download(file_name="subtitle.srt", progress=progress_bar, progress_args=("دانلود زیرنویس", processing_msg))
    await processing_msg.edit_text("✅ زیرنویس دریافت شد. حالا ویدیوت رو هم بفرست!")
