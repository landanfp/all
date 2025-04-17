
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.database import download_and_trim_upload

user_video_state = {}

@Client.on_callback_query(filters.regex("cut_video"))
async def handle_video_cut(client: Client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.reply("لطفاً ویدیو خود را ارسال کنید.")
    user_video_state[callback_query.from_user.id] = {}

@Client.on_message(filters.video & filters.private)
async def receive_video(client: Client, message: Message):
    user_id = message.from_user.id
    file_id = message.video.file_id
    user_video_state[user_id] = {"file_id": file_id}
    await message.reply("تایم شروع را وارد کنید (hh:mm:ss):")

@Client.on_message(filters.text & filters.private)
async def receive_video_times(client: Client, message: Message):
    user_id = message.from_user.id
    state = user_video_state.get(user_id)

    if not state:
        return

    if "start" not in state:
        state["start"] = message.text
        await message.reply("تایم پایان را وارد کنید (hh:mm:ss):")
    elif "end" not in state:
        state["end"] = message.text
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("شروع", callback_data="start_trim")]])
        await message.reply(f"تایم شروع: {state['start']}
تایم پایان: {state['end']}", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("start_trim"))
async def start_trimming(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("در حال پردازش...")
    user_id = callback_query.from_user.id
    state = user_video_state.get(user_id)

    if not state:
        await callback_query.message.edit_text("هیچ فایل ویدیویی پیدا نشد.")
        return

    await callback_query.message.edit_text("در حال دانلود و برش ویدیو...")
    await download_and_trim_upload(client, callback_query.message, state["file_id"], state["start"], state["end"])
    del user_video_state[user_id]
