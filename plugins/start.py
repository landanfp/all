
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("برش ویدیو", callback_data="cut_video")],
        [InlineKeyboardButton("برش صدا", callback_data="cut_audio")]
    ])
    await message.reply("سلام! لطفاً یک گزینه را انتخاب کنید:", reply_markup=keyboard)
