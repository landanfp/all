from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.downloader import stream_download
from helper.uploader import upload_with_progress
import os
import ffmpeg

start_button = InlineKeyboardButton("شروع استخراج صدا", callback_data="start_audio_extraction")
buttons = InlineKeyboardMarkup([[start_button]])

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "سلام! برای استخراج صدا از ویدیو، ویدیو خود را ارسال کنید.",
        reply_markup=buttons
    )

@Client.on_message(filters.video)
async def video_received(client: Client, message: Message):
    await message.reply("در حال استخراج صدا از ویدیو...")

    file_path = await stream_download(message.video.file_id, "temp/video.mp4", message)

    output_audio_path = file_path.replace("video.mp4", "audio.mp3")
    cmd = f"ffmpeg -i {file_path} -vn -acodec libmp3lame -y {output_audio_path}"
    os.system(cmd)

    await message.reply("در حال آپلود فایل صوتی...")

    await upload_with_progress(client, message.chat.id, output_audio_path, message, as_audio=True)

    os.remove(file_path)
    os.remove(output_audio_path)