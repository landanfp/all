from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

@Client.on_callback_query(filters.regex("^video_cut$"))
async def handle_video_cut(client, callback_query: CallbackQuery):
    await callback_query.answer(show_alert=False)
    await callback_query.message.reply_text("به ابزار برش ویدیو خوش آمدید!")
