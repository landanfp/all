from pyrogram import Client, filters
from helper.progress import progress_bar
from loader import app
import os

@app.on_message(filters.document)
async def catch_subtitle(client, message):
    processing_msg = await message.reply_text("⏳ در حال دانلود زیرنویس...")
    try:
        srt_path = await message.download(file_name="subtitle.srt", progress=progress_bar, progress_args=("دانلود زیرنویس", processing_msg))
        
        # بررسی وجود و حجم فایل
        if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
            await processing_msg.edit_text("❌ خطا: فایل زیرنویس دانلود نشد یا خالی است. لطفاً دوباره امتحان کنید.")
            return

        await processing_msg.edit_text("✅ زیرنویس دریافت شد. حالا ویدیوت رو هم بفرست!")
    except Exception as e:
        await processing_msg.edit_text(f"❌ خطایی در دانلود زیرنویس رخ داد: {str(e)}")
        print(f"خطا در دانلود زیرنویس: {str(e)}")
