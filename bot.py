import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from helpers import progress_bar  # فرض بر اینه که فایل helpers.py داری برای نمایش پیشرفت

# ─────── تنظیمات ─────── #
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '1396293494:AAFY7RXygNEZPFPXfmoJ66SljlXeCSilXG0'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه

bot = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

WATERMARK_IMAGE = "1.jpg"  # تصویر واترمارک

# ─────── ساخت کلاینت ─────── #

# ─────── هندلر پیام ویدیو ─────── #
@bot.on_message(filters.video & filters.private)
async def watermark_handler(client: Client, message: Message):
    user_id = message.from_user.id
    BASE_PATH = os.path.abspath(os.path.dirname(__file__))
    input_path = os.path.join(BASE_PATH, f"{user_id}_input.mp4")
    output_path = os.path.join(BASE_PATH, f"{user_id}_watermarked.mp4")

    status = await message.reply("📥 در حال دانلود ویدیو...")

    try:
        # دانلود فایل ویدیو با نوار پیشرفت
        await client.download_media(
            message,
            file_name=input_path,
            progress=progress_bar,
            progress_args=("⬇️ در حال دانلود", status),
        )

        # بررسی وجود فایل
        if not os.path.exists(input_path):
            await status.edit("❌ خطا: فایل ویدیو پیدا نشد.")
            return

        await status.edit("⚙️ در حال افزودن واترمارک...")

        # لود ویدیو و تصویر واترمارک
        video = VideoFileClip(input_path)
        watermark = (
            ImageClip(WATERMARK_IMAGE)
            .resize(height=750)  # سایز واترمارک 30 پیکسل
            .set_position(("right", "top"))  # بالا سمت راست
            .set_duration(video.duration)
        )

        # ترکیب واترمارک با ویدیو
        final = CompositeVideoClip([video, watermark])
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")

        await status.edit("📤 در حال آپلود ویدیو واترمارک شده...")

        # ارسال ویدیو خروجی
        await message.reply_video(
            video=output_path,
            caption="✅ ویدیو با واترمارک ارسال شد!",
            progress=progress_bar,
            progress_args=("⬆️ در حال آپلود", status),
        )

    except Exception as e:
        await status.edit(f"❌ خطا در هنگام افزودن واترمارک:\n`{str(e)}`")
    finally:
        # پاکسازی فایل‌ها
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)


# ─────── اجرای ربات ─────── #
if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.run()
