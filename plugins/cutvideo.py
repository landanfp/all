from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
import os
import asyncio
from moviepy.editor import VideoFileClip

user_trim_state = {}

@Client.on_callback_query(filters.regex("^cut_video$"))
async def cut_video_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.reply("لطفاً ویدیوی مورد نظر برای برش را ارسال کنید.")
    user_trim_state[callback_query.from_user.id] = {
        "video_msg_id": None,
        "video_duration": None,
        "start_time": None,
        "end_time": None,
        "info_msg_id": None,
        "ask_start_msg_id": None,
        "ask_end_msg_id": None
    }

@Client.on_message(filters.video & filters.private)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_trim_state:
        return

    video = message.video
    duration = video.duration  # in seconds
    video_msg_id = message.id

    user_trim_state[user_id]["video_msg_id"] = video_msg_id
    user_trim_state[user_id]["video_duration"] = duration

    readable_time = str(asyncio.timedelta(seconds=duration))

    text = (
        f"حله بریم برای برش ویدیو...\n"
        f"تایم ویدیو : {readable_time}\n"
        f"تایم شروع : {{تنظیم نشده}}\n"
        f"تایم پایان : {{تنظیم نشده}}"
    )

    info_msg = await message.reply(text)
    ask_start = await message.reply("لطفاً تایم شروع را به فرمت hh:mm:ss ارسال کنید:")

    user_trim_state[user_id]["info_msg_id"] = info_msg.id
    user_trim_state[user_id]["ask_start_msg_id"] = ask_start.id

@Client.on_message(filters.text & filters.private)
async def handle_time_inputs(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_trim_state:
        return

    state = user_trim_state[user_id]

    def to_seconds(hms):
        try:
            h, m, s = map(int, hms.split(":"))
            return h * 3600 + m * 60 + s
        except:
            return None

    time_in_sec = to_seconds(message.text)
    if time_in_sec is None:
        await message.reply("فرمت اشتباه است! لطفاً زمان را به صورت hh:mm:ss وارد کنید.")
        return

    if state["start_time"] is None:
        # set start time
        state["start_time"] = message.text
        await client.delete_messages(message.chat.id, state["ask_start_msg_id"])

        updated = (
            f"حله بریم برای برش ویدیو...\n"
            f"تایم ویدیو : {str(asyncio.timedelta(seconds=state['video_duration']))}\n"
            f"تایم شروع : {state['start_time']}\n"
            f"تایم پایان : {{تنظیم نشده}}"
        )
        await client.edit_message_text(message.chat.id, state["info_msg_id"], updated)
        ask_end = await message.reply("لطفاً تایم پایان را به فرمت hh:mm:ss ارسال کنید:")
        state["ask_end_msg_id"] = ask_end.id
    elif state["end_time"] is None:
        state["end_time"] = message.text
        await client.delete_messages(message.chat.id, state["ask_end_msg_id"])

        updated = (
            f"حله بریم برای برش ویدیو...\n"
            f"تایم ویدیو : {str(asyncio.timedelta(seconds=state['video_duration']))}\n"
            f"تایم شروع : {state['start_time']}\n"
            f"تایم پایان : {state['end_time']}"
        )
        await client.edit_message_text(
            message.chat.id,
            state["info_msg_id"],
            updated,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("شروع برش", callback_data="start_cut")]
            ])
        )
