from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from plugins.database import download_file, upload_file_to_channel, delete_file
import re

start_time = None
end_time = None

# درخواست تایم شروع برش
async def cut_video(client, message: Message):
    # درخواست تایم شروع از کاربر
    await message.reply("لطفاً زمان شروع برش (به فرمت hh:mm:ss) را وارد کنید:")

# پردازش تایم شروع
async def process_start_time(client, message: Message):
    global start_time
    time_format = r"^\d{2}:\d{2}:\d{2}$"
    if re.match(time_format, message.text):
        start_time = message.text
        await message.reply("تایم شروع ذخیره شد. حالا زمان پایان (به فرمت hh:mm:ss) را وارد کنید:")
    else:
        await message.reply("فرمت تایم اشتباه است. لطفاً دوباره تایم شروع رو به فرمت صحیح وارد کنید (hh:mm:ss).")

# پردازش تایم پایان
async def process_end_time(client, message: Message):
    global end_time
    time_format = r"^\d{2}:\d{2}:\d{2}$"
    if re.match(time_format, message.text):
        end_time = message.text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("شروع برش", callback_data="start_cutting")]
        ])
        await message.reply(
            f"تایم شروع: {start_time}\nتایم پایان: {end_time}",
            reply_markup=keyboard
        )
    else:
        await message.reply("فرمت تایم اشتباه است. لطفاً دوباره تایم پایان رو به فرمت صحیح وارد کنید (hh:mm:ss).")

# شروع برش ویدیو
async def start_cutting(client: Client, callback_query: CallbackQuery):
    # دریافت لینک ویدیو یا فایل برای دانلود
    video_url = "some_video_url"  # لینک ویدیو یا فایل باید از کاربر گرفته بشه
    file_name = "downloaded_video.mp4"  # نام فایل به صورت موقت
    await callback_query.message.edit_text("در حال دانلود فایل...")

    # دانلود فایل به صورت استریم
    await download_file(client, callback_query.message, video_url, file_name)

    # آپلود فایل به کانال لاگ
    log_channel = "@log_channel"  # نام کانال لاگ
    uploaded_file = await upload_file_to_channel(client, callback_query.message, file_name, log_channel)

    # حذف فایل از سرور بعد از اتمام آپلود
    await delete_file(file_name)

    # ارسال لینک فایل آپلود شده به کاربر
    await callback_query.message.edit_text(f"فایل آپلود شد: {uploaded_file.link}")

# هندلرها
cut_video_handler = CallbackQueryHandler(cut_video, filters.regex("cut_video"))
start_time_handler = MessageHandler(process_start_time, filters.text & filters.regex(r"^\d{2}:\d{2}:\d{2}$"))
end_time_handler = MessageHandler(process_end_time, filters.text & filters.regex(r"^\d{2}:\d{2}:\d{2}$"))
start_cutting_handler = CallbackQueryHandler(start_cutting, filters.regex("start_cutting"))

def setup_handlers(app):
    app.add_handler(cut_video_handler)
    app.add_handler(start_time_handler)
    app.add_handler(end_time_handler)
    app.add_handler(start_cutting_handler)
