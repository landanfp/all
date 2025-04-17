from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
#from plugins.database import download_and_trim_audio_upload
from plugins.database import download_and_trim_upload, download_and_trim_audio_upload

user_audio_state = {}

@Client.on_callback_query(filters.regex("cut_audio"))
async def handle_audio_cut(client: Client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.reply("لطفاً فایل صوتی خود را ارسال کنید.")
    user_audio_state[callback_query.from_user.id] = {}

@Client.on_message((filters.audio | filters.voice) & filters.private)
async def receive_audio(client: Client, message: Message):
    user_id = message.from_user.id
    file_id = message.audio.file_id if message.audio else message.voice.file_id
    user_audio_state[user_id] = {"file_id": file_id}
    await message.reply("تایم شروع را وارد کنید (hh:mm:ss):")

@Client.on_message(filters.text & filters.private)
async def receive_audio_times(client: Client, message: Message):
    user_id = message.from_user.id
    state = user_audio_state.get(user_id)

    if not state:
        return

    if "start" not in state:
        state["start"] = message.text
        await message.reply("تایم پایان را وارد کنید (hh:mm:ss):")
    elif "end" not in state:
        state["end"] = message.text
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("شروع برش", callback_data="start_audio_trim")]])
        await message.reply(f"تایم شروع: {state['start']}\nتایم پایان: {state['end']}", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("start_audio_trim"))
async def start_audio_trimming(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("در حال پردازش فایل صوتی...")
    user_id = callback_query.from_user.id
    state = user_audio_state.get(user_id)

    if not state:
        await callback_query.message.edit_text("هیچ فایل صوتی پیدا نشد.")
        return

    await callback_query.message.edit_text("در حال دانلود و برش فایل صوتی...")
    # فراخوانی تابع دانلود و برش صوت
    await download_and_trim_audio_upload(client, callback_query.message, state["file_id"], state["start"], state["end"])
    del user_audio_state[user_id]
