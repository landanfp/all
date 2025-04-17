import os
from moviepy.editor import VideoFileClip
from pyrogram import Client, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from plugins.database import download_file, upload_file

async def video_cut(client, message):
    # ارسال پیام درخواست ویدیو
    await message.reply("لطفاً ویدیو مورد نظر را ارسال کنید.")

async def handle_video_cut(client, message):
    # بررسی اینکه آیا پیام شامل ویدیو است یا نه
    if message.video:
        video_file = message.video.file_id
        # دانلود ویدیو
        file_path = await download_file(client, video_file)
        
        # ارسال پیام برای دریافت زمان شروع
        await message.reply("لطفاً زمان شروع را وارد کنید (فرمت: hh:mm:ss).")

        # زمان شروع و پایان
        start_time = None
        end_time = None

        def set_start_time(client, message):
            nonlocal start_time
            start_time = message.text
            # درخواست زمان پایان
            await message.reply("لطفاً زمان پایان را وارد کنید (فرمت: hh:mm:ss).")

        def set_end_time(client, message):
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

        def cut_video(client, callback_query):
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

    else:
        await message.reply("این پیام حاوی ویدیو نیست.")

# تبدیل زمان به ثانیه
def convert_to_seconds(time_str):
    hours, minutes, seconds = map(int, time_str.split(":"))
    return hours * 3600 + minutes * 60 + seconds

# هندلرهای پیام‌ها و دکمه‌های پاسخ
start_handler = MessageHandler(video_cut, filters.command("start"))
video_cut_handler = CallbackQueryHandler(handle_video_cut, filters.regex("start_cut"))

# اضافه کردن هندلرها به ربات
app.add_handler(start_handler)
app.add_handler(video_cut_handler)
