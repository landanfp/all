import os
from moviepy.editor import VideoFileClip
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import MessageHandler

# دانلود فایل
async def download_file(client: Client, file_id: str) -> str:
    file_path = f"downloads/{file_id}.mp4"
    file = await client.download_media(file_id, file_path)
    return file_path

# ارسال پیام شروع
async def start_message(client, message: Message):
    await message.reply(
        "سلام! لطفاً ویدیو خود را ارسال کنید که می‌خواهید آن را برش دهید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("برش ویدیو", callback_data="cut_video")]
        ])
    )

# برش ویدیو
async def video_cut(client: Client, message: Message):
    if message.video:
        # دانلود ویدیو
        video_file = message.video.file_id
        file_path = await download_file(client, video_file)

        # درخواست زمان شروع
        await message.reply("لطفاً زمان شروع را وارد کنید (فرمت: hh:mm:ss).")

        # زمان شروع و پایان به صورت متغیر
        start_time = None
        end_time = None

        # تابع برای تنظیم زمان شروع
        async def set_start_time(client, message):
            nonlocal start_time
            start_time = message.text
            # درخواست زمان پایان
            await message.reply("لطفاً زمان پایان را وارد کنید (فرمت: hh:mm:ss).")

        # تابع برای تنظیم زمان پایان
        async def set_end_time(client, message):
            nonlocal end_time
            end_time = message.text
            # بروزرسانی پیام
            await message.reply(f"تایم شروع: {start_time}\nتایم پایان: {end_time}")
            # دکمه شروع را اضافه کنید
            await message.reply(
                "برای شروع برش، دکمه 'شروع' را بزنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("شروع", callback_data="start_cut")]
                ])
            )

        # تبدیل زمان به ثانیه
        def convert_to_seconds(time_str):
            hours, minutes, seconds = map(int, time_str.split(":"))
            return hours * 3600 + minutes * 60 + seconds

        # برش ویدیو
        async def cut_video(client, callback_query):
            if start_time and end_time:
                # تبدیل زمان‌ها به ثانیه
                start_seconds = convert_to_seconds(start_time)
                end_seconds = convert_to_seconds(end_time)

                # برش ویدیو
                video = VideoFileClip(file_path)
                video = video.subclip(start_seconds, end_seconds)

                # ذخیره ویدیو جدید
                output_path = f"output_{message.video.file_id}.mp4"
                video.write_videofile(output_path, codec="libx264")

                # ارسال ویدیو برش داده شده
                await client.send_video(message.chat.id, output_path)

                # حذف فایل‌ها بعد از ارسال
                os.remove(file_path)
                os.remove(output_path)
            else:
                await message.reply("لطفاً ابتدا زمان شروع و پایان را وارد کنید.")
