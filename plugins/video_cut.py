from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.downloader import stream_download
from helper.uploader import upload_with_progress
import os
import ffmpeg

start_button = InlineKeyboardButton("شروع برش", callback_data="start_cutting")
buttons = InlineKeyboardMarkup([[start_button]])

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "سلام! برای برش ویدیو و یا استخراج صدا، ویدیو خود را ارسال کنید.",
        reply_markup=buttons
    )

@Client.on_message(filters.video)
async def video_received(client: Client, message: Message):
    await message.reply("لطفاً تایم شروع (hh:mm:ss) را وارد کنید:")

    file_path = await stream_download(message.video.file_id, "temp/video.mp4", message)

    @Client.on_message(filters.text)
    async def handle_start_time(client: Client, start_time_msg: Message):
        start_time = start_time_msg.text
        await message.reply("لطفاً تایم پایان (hh:mm:ss) را وارد کنید:")

        @Client.on_message(filters.text)
        async def handle_end_time(client: Client, end_time_msg: Message):
            end_time = end_time_msg.text

            output_path = file_path.replace("video.mp4", "output.mp4")
            cmd = f"ffmpeg -i {file_path} -ss {start_time} -to {end_time} -c copy {output_path} -y"
            os.system(cmd)

            await message.reply("در حال آپلود ویدیو برش خورده...")

            await upload_with_progress(client, message.chat.id, output_path, message)

            os.remove(file_path)
            os.remove(output_path)