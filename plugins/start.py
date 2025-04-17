print(">>> start.py loaded")
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command("ping") & filters.private)
async def ping(client, message: Message):
    await message.reply("pong!")

"""
@Client.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("برش ویدیو", callback_data="cut_video"),
         InlineKeyboardButton("برش صدا", callback_data="cut_audio")],
        
        [InlineKeyboardButton("ادغام ویدیو", callback_data="merge_video"),
         InlineKeyboardButton("ادغام صدا", callback_data="merge_audio")],
        
        [InlineKeyboardButton("استخراج صدای ویدیو", callback_data="extract_audio"),
         InlineKeyboardButton("افزودن واترمارک", callback_data="add_watermark")],
        
        [InlineKeyboardButton("کم‌حجم کردن ویدیو", callback_data="compress_video"),
         InlineKeyboardButton("تبدیل MKV به MP4", callback_data="convert_mkv_to_mp4")],
        
        [InlineKeyboardButton("افزودن زیرنویس", callback_data="add_subtitle"),
         InlineKeyboardButton("گرفتن اسکرین‌شات", callback_data="take_screenshot")],
        
        [InlineKeyboardButton("تغییر نام فایل", callback_data="rename_file"),
         InlineKeyboardButton("زیپ کردن فایل‌ها", callback_data="zip_files")],
        
        [InlineKeyboardButton("تبدیل فایل به ویدیو", callback_data="file_to_video"),
         InlineKeyboardButton("تبدیل ویدیو به فایل", callback_data="video_to_file")]
    ])
    await message.reply("سلام! لطفاً یک گزینه را انتخاب کنید:", reply_markup=keyboard)
"""
