# نام فایل: plugins/start.py (هندلر /start)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)

async def start_handler(client, message: Message):
    """هندلر دستور /start."""
    try:
        await message.reply(
            "👋 سلام! من یک ربات برای افزودن واترمارک متنی یا تصویری به ویدیوها هستم.\nیکی از گزینه‌های زیر را انتخاب کن تا شروع کنیم:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖋️ واترمارک متنی", callback_data="text_wm")],
                [InlineKeyboardButton("🖼️ واترمارک تصویری", callback_data="image_wm")]
            ])
        )
        logger.info(f"Start command handled for user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in start_handler for user {message.from_user.id}: {e}")
        await message.reply("خطایی رخ داد. لطفا دوباره /start را امتحان کنید.")
