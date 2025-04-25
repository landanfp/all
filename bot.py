import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAHoidc0x6nM3g2JHmb7xhWKmwGJOoKFNXY'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    return str(timedelta(seconds=seconds))

@app.on_message(filters.command("start"))
async def start(_, message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✂️", callback_data="start_cutting")]]
    )
    await message.reply("سلام! برای برش ویدیو روی دکمه زیر کلیک کن:", reply_markup=keyboard)

@app.on_callback_query()
async def handle_callback(_, callback_query):
    user_id = callback_query.from_user.id

    if callback_query.data == "start_cutting":
        user_state[user_id] = {
            "step": "awaiting_video"
        }
        await callback_query.message.reply("لطفاً ویدیوی موردنظر را ارسال کنید.")

    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state:
            return

        await callback_query.answer("در حال برش...")

        # دانلود ویدیو
        video_msg = await app.get_messages(callback_query.message.chat.id, state["video_msg_id"])
        temp_input = f"{user_id}_input.mp4"
        temp_output = f"{user_id}_cut.mp4"
        await video_msg.download(temp_input)

        start = state["start_time"]
        end = state["end_time"]

        await callback_query.message.reply("در حال پردازش ویدیو...")

        (
            ffmpeg
            .input(temp_input, ss=start, to=end)
            .output(temp_output)
            .run(overwrite_output=True)
        )

        await app.send_video(callback_query.message.chat.id, temp_output)
        await callback_query.message.edit("تمام شد!")

        os.remove(temp_input)
        os.remove(temp_output)
        del user_state[user_id]

@app.on_message(filters.video)
async def handle_video(_, message):
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    duration = seconds_to_hms(message.video.duration)

    text = (
        f"⏱ زمان ویدیو: {duration}\n"
        f"⏳ تایم شروع: {{}}\n"
        f"⏳ تایم پایان: {{}}"
    )
    sent_msg = await message.reply(text)

    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id,
        "video_edit_msg": sent_msg.id,
        "duration": duration,
        "start_time": None,
        "end_time": None
    })

    await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")

@app.on_message(filters.text)
async def handle_time(_, message):
    user_id = message.from_user.id
    state = user_state.get(user_id)

    if not state:
        return

    if state["step"] == "awaiting_start":
        user_state[user_id]["start_time"] = message.text
        state["step"] = "awaiting_end"

        video_msg = await message.chat.get_message(state["video_edit_msg"])
        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {{}}"
        )
        await video_msg.edit(new_text)
        await message.reply("حالا تایم پایان را وارد کنید (hh:mm:ss)")

    elif state["step"] == "awaiting_end":
        user_state[user_id]["end_time"] = message.text
        state["step"] = "ready"

        video_msg = await message.chat.get_message(state["video_edit_msg"])
        new_text = (
            f"⏱ زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {state['end_time']}"
        )
        await video_msg.edit(new_text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("شروع برش", callback_data="cut_now")]]
        ))

app.run()
