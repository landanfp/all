# plugins/cut.py

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from helper.database import progress_for_pyrogram
from io import BytesIO
import subprocess
import time

user_data = {}

@Client.on_callback_query(filters.regex("video_cut"))
async def video_cut_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_data[user_id] = {}
    await callback_query.message.edit("ویدیوی خود را ارسال کنید.")
    user_data[user_id]["step"] = "awaiting_video"

@Client.on_message(filters.video | filters.document)
async def receive_video(client: Client, message: Message):
    user_id = message.from_user.id
    if user_data.get(user_id, {}).get("step") != "awaiting_video":
        return

    user_data[user_id]["file"] = message
    user_data[user_id]["step"] = "awaiting_start"
    await message.reply_text("لطفاً تایم **شروع** ویدیو را ارسال کنید (hh:mm:ss)")

@Client.on_message(filters.text)
async def receive_time(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if user_data[user_id]["step"] == "awaiting_start":
        user_data[user_id]["start_time"] = message.text
        user_data[user_id]["step"] = "awaiting_end"
        sent = await message.reply_text(f"""✅ تایم شروع انتخاب شده: `{message.text}`
حالا لطفاً تایم **پایان** ویدیو را ارسال کنید (hh:mm:ss)""")
        user_data[user_id]["edit_message"] = sent

    elif user_data[user_id]["step"] == "awaiting_end":
        user_data[user_id]["end_time"] = message.text
        start = user_data[user_id]["start_time"]
        end = user_data[user_id]["end_time"]
        msg = user_data[user_id]["edit_message"]
        await msg.edit(f"""حالا بزن بریم...

تایم شروع: `{start}`
تایم پایان: `{end}`""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("شروع برش ویدیو", callback_data="start_cut")]
        ]))
        user_data[user_id]["step"] = "ready_to_cut"

@Client.on_callback_query(filters.regex("start_cut"))
async def cut_video(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = user_data.get(user_id)
    if not data:
        return await callback_query.message.edit("خطا: اطلاعات ناقص است.")

    await callback_query.message.edit("در حال دانلود و برش ویدیو...")

    # استریم فایل از تلگرام
    input_stream = BytesIO()
    start_time = time.time()
    await data["file"].download_to_memory(
        input_stream,
        progress=progress_for_pyrogram,
        progress_args=(callback_query.message, start_time)
    )
    input_stream.seek(0)

    # اجرای FFmpeg با استریم ورودی و خروجی
    output_stream = BytesIO()
    start = data["start_time"]
    end = data["end_time"]

    cmd = [
        "ffmpeg", "-i", "pipe:0",
        "-ss", start, "-to", end,
        "-c:v", "copy", "-c:a", "copy",
        "-f", "mp4", "pipe:1"
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    out, err = process.communicate(input=input_stream.read())
    output_stream.write(out)
    output_stream.name = "cut_video.mp4"
    output_stream.seek(0)

    # آپلود و ارسال ویدیو
    await callback_query.message.edit("در حال آپلود فایل برش‌خورده...")
    start_time = time.time()
    await client.send_video(
        chat_id=callback_query.message.chat.id,
        video=output_stream,
        caption="ویدیوی برش‌خورده آماده است!",
        progress=progress_for_pyrogram,
        progress_args=(callback_query.message, start_time)
    )

    # پاکسازی
    user_data.pop(user_id, None)
