from pyrogram import Client, filters
import asyncio
import os
from helper.ffmpeg import add_hardsub
from helper.progress import progress_bar

@Client.on_message(filters.video)
async def process_video(client, message):
    if message.video.file_size > 300 * 1024 * 1024:
        await message.reply_text("حجم ویدیو بیش از حد مجازه! (حداکثر 300MB)")
        return

    await message.reply_text("درحال دانلود ویدیو...")
    video_path = await message.download(file_name="input_video.mp4", progress=progress_bar, progress_args=("دانلود ویدیو", message))
    
    if not os.path.exists("subtitle.srt"):
        await message.reply_text("اول زیرنویس .srt رو بفرست بعد ویدیو!")
        return
    
    output_path = "output_video.mp4"
    await add_hardsub(video_path, "subtitle.srt", output_path)

    await message.reply_video(
        video=output_path,
        caption="ویدیو با زیرنویس چسبیده آماده شد!",
        progress=progress_bar,
        progress_args=("آپلود ویدیو", message)
    )
    os.remove(video_path)
    os.remove(output_path)
    os.remove("subtitle.srt")