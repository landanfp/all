from pyrogram import Client, filters
from pyrogram.types import Message
from loader import app
import asyncio
import time
import os
from helper.ffmpeg import add_hardsub
from helper.progress import progress_bar

# ذخیره وضعیت کاربران
user_sessions = {}
SESSION_TIMEOUT = 300  # ۵ دقیقه

@app.on_message(filters.document & filters.private)
async def handle_srt_file(client, message: Message):
    user_id = message.from_user.id

    if user_id in user_sessions:
        await message.reply_text("⚠️ شما قبلاً یک فایل زیرنویس ارسال کرده‌اید. لطفاً ویدیوی خود را ارسال کنید.")
        return

    if message.document.mime_type == "application/x-subrip" or message.document.file_name.endswith(".srt"):
        processing_msg = await message.reply_text("⏳ در حال دانلود زیرنویس...")
        try:
            srt_path = await client.download_media(
                message.document.file_id,
                file_name=f"subtitle_{user_id}.srt",  # نام منحصربه‌فرد
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

            await processing_msg.edit_text("✅ فایل زیرنویس دریافت شد. حالا لطفاً ویدیوی خود را ارسال کنید.")
            asyncio.create_task(expire_session(user_id))

        except Exception as e:
            await processing_msg.edit_text(f"❌ خطایی در دانلود زیرنویس رخ داد: {str(e)}")
            print(f"خطا در دانلود زیرنویس برای کاربر {user_id}: {str(e)}")
    else:
        await message.reply_text("⚠️ لطفاً فقط فایل زیرنویس با فرمت .srt ارسال کنید.")

async def expire_session(user_id):
    await asyncio.sleep(SESSION_TIMEOUT)
    session = user_sessions.get(user_id)
    if session and (time.time() - session['timestamp'] >= SESSION_TIMEOUT):
        try:
            if os.path.exists(session['srt_path']):
                os.remove(session['srt_path'])
        except Exception as e:
            print(f"خطا در پاکسازی فایل زیرنویس: {e}")
        user_sessions.pop(user_id, None)

@app.on_message(filters.video & filters.private)
async def handle_video_file(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_sessions or 'srt_path' not in user_sessions[user_id]:
        await message.reply_text("⚠️ ابتدا باید فایل زیرنویس (.srt) را ارسال کنید.")
        return

    processing_msg = await message.reply_text("⏳ در حال دانلود ویدیو...")

    try:
        srt_path = user_sessions[user_id]['srt_path']
        video_path = await client.download_media(
            message,
            file_name=f"video_{user_id}.mp4",  # نام منحصربه‌فرد
            progress=progress_bar,
            progress_args=("دانلود ویدیو", processing_msg)
        )

        if not video_path or not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            await processing_msg.edit_text("❌ خطا: فایل ویدیویی دانلود نشد یا خالی است. لطفاً دوباره امتحان کنید.")
            return

        output_path = f"hardsub_{user_id}.mp4"

        await processing_msg.edit_text("⏳ در حال چسباندن زیرنویس...")
        success, ffmpeg_error = await add_hardsub(video_path, srt_path, output_path, processing_msg)

        if not success:
            await processing_msg.edit_text(f"❌ خطا در پردازش ffmpeg: {ffmpeg_error}")
            print(f"خطای ffmpeg برای کاربر {user_id}: {ffmpeg_error}")
            return

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            await processing_msg.edit_text("❌ خطا: فایل خروجی تولید نشد یا خالی است.")
            print(f"خطا: فایل خروجی {output_path} تولید نشد یا خالی است.")
            return

        await processing_msg.edit_text("⏳ در حال آپلود ویدیو...")
        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با زیرنویس اضافه شده آماده است!",
            progress=progress_bar,
            progress_args=("آپلود ویدیو", processing_msg)
        )

        await processing_msg.delete()

    except Exception as e:
        await processing_msg.edit_text(f"❌ خطایی رخ داد: {str(e)}")
        print(f"خطا برای کاربر {user_id}: {str(e)}")

    finally:
        user_sessions.pop(user_id, None)
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(srt_path):
                os.remove(srt_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            print(f"خطا در پاکسازی فایل‌ها: {e}")
