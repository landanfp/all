# نام فایل: plugins/start.py (هندلر  /start)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

async def start_handler(client, message: Message):
    """هندلر دستور /start."""
    await message.reply(
        "👋 سلام! من یک ربات برای افزودن واترمارک متنی یا تصویری به ویدیوها هستم.\nیکی از گزینه‌های زیر را انتخاب کن تا شروع کنیم:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖋️ واترمارک متنی", callback_data="text_wm")],
            [InlineKeyboardButton("🖼️ واترمارک تصویری", callback_data="image_wm")]
        ])
    )
