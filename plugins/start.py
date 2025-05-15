from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply(
        "سلام! یکی از گزینه‌های واترمارک را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("واترمارک متنی", callback_data="text_wm")],
            [InlineKeyboardButton("واترمارک تصویری", callback_data="image_wm")]
        ])
    )
