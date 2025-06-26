from pyrogram import Client, filters
from helper.progress import progress_bar
from loader import app
import os

@app.on_message(filters.document & filters.private)
async def catch_subtitle(client, message):
    user_id = message.from_user.id

    if user_id in user_sessions:
        await message.reply_text("⚠️ شما قبلاً یک فایل زیرنویس ارسال کرده‌اید. لطفاً ویدیوی خود را ارسال کنید.")
        return

    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        processing_msg = await message.reply_text("⏳ در حال دانلود زیرنویس...")
        try:
            srt_path = await message.download(
                file_name=f"subtitle_{user_id}.srt",
                progress=progress_bar,
                progress_args=("دانلود زیرنویس", processing_msg)
            )
            
            if not srt_path or not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
                await processing_msg.edit_text("❌ خطا: فایل زیرنویس دانلود نشد یا خالی است. لطفاً فایل معتبر دیگری ارسال کنید.")
                return

            user_sessions[user_id] = {
                'srt_path': srt_path,
                'timestamp': time.time()
            }

            await processing_msg.edit_text("✅ زیرنویس دریافت شد. حالا ویدیوت رو هم بفرست!")
        except Exception as e:
            await processing_msg.edit_text(f"❌ خطایی در دانلود زیرنویس رخ داد: {str(e)}")
            print(f"خطا در دانلود زیرنویس برای کاربر {user_id}: {str(e)}")
    else:
        await message.reply_text("⚠️ لطفاً فقط فایل زیرنویس با فرمت .srt ارسال کنید.")
