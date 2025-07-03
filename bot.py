from pyrogram import Client, filters
from pyrogram.types import Message
import os
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from helpers import progress_bar

bot = Client("watermark_bot",
             api_id=123456,  # جایگزین با API ID
             api_hash="your_api_hash",  # جایگزین با API Hash
             bot_token="your_bot_token")  # جایگزین با توکن ربات

WATERMARK_FILE = "1.jpg"

@bot.on_message(filters.video)
async def watermark_handler(client, message: Message):
    user_id = message.from_user.id
    video = message.video

    download_path = f"{user_id}_input.mp4"
    output_path = f"{user_id}_watermarked.mp4"

    # دانلود فایل با نمایش پیشرفت
    await message.reply("⬇️ در حال دانلود ویدیو...")
    await client.download_media(message, file_name=download_path, progress=progress_bar, progress_args=("⬇️ دانلود", message))

    # اضافه کردن واترمارک
    await message.reply("🛠 در حال افزودن واترمارک...")
    try:
        video_clip = VideoFileClip(download_path)
        watermark = (ImageClip(WATERMARK_FILE)
                     .resize(height=30)  # سایز واترمارک
                     .set_position(("right", "top"))
                     .set_duration(video_clip.duration))

        final = CompositeVideoClip([video_clip, watermark])
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=2, logger=None)

    except Exception as e:
        await message.reply(f"❌ خطا در هنگام افزودن واترمارک:\n{e}")
        return

    # آپلود فایل
    await message.reply("⬆️ در حال آپلود فایل واترمارک‌شده...")
    await message.reply_video(
        output_path,
        caption="✅ واترمارک با موفقیت اضافه شد!",
        progress=progress_bar,
        progress_args=("⬆️ آپلود", message)
    )

    os.remove(download_path)
    os.remove(output_path)

bot.run()
