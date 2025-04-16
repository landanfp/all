from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("تبدیل صدا به ویس", callback_data="audio_to_speech"),
         InlineKeyboardButton("تبدیل ویس به صدا", callback_data="speech_to_audio")],
        [InlineKeyboardButton("برش صدا", callback_data="audio_cut"),
         InlineKeyboardButton("ادغام صدا", callback_data="audio_merge")],
        [InlineKeyboardButton("تبدیل ویدیو به صدا", callback_data="video_to_audio"),
         InlineKeyboardButton("زیپ کردن فایل‌ها", callback_data="zip_files")],
        [InlineKeyboardButton("برش ویدیو", callback_data="video_cut"),
         InlineKeyboardButton("افزودن زیرنویس به ویدیو", callback_data="add_subtitles")],
        [InlineKeyboardButton("ادغام ویدیوها", callback_data="merge_videos"),
         InlineKeyboardButton("افزودن صدا به ویدیو", callback_data="add_audio_to_video")],
        [InlineKeyboardButton("گرفتن اسکرین‌شات", callback_data="take_screenshot")]
    ])
    await message.reply_text(
        "به ربات خوش آمدید! انتخاب کنید که می‌خواهید چه کاری انجام دهید:",
        reply_markup=keyboard
    )
