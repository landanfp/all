import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.database import download_file_stream
from moviepy.editor import VideoFileClip
from plugins.database progress_for_pyrogram
user_states = {}

def time_to_seconds(time_str):
    try:
        h, m, s = map(int, time_str.strip().split(":"))
        return h * 3600 + m * 60 + s
    except:
        return None

@Client.on_message(filters.command("start"))
async def start_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("برش ویدیو", callback_data="cut_video")],
        [InlineKeyboardButton("برش صدا", callback_data="cut_audio")]
    ])
    await message.reply("سلام! یکی از گزینه‌ها رو انتخاب کن:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("cut_video"))
async def handle_cut_video(client, callback_query: CallbackQuery):
    user_states[callback_query.from_user.id] = {"step": "awaiting_video"}
    await callback_query.message.reply("لطفا ویدیو خود را ارسال کنید (فقط mp4 یا mkv).")

@Client.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state or state.get("step") != "awaiting_video":
        return

    if message.video and message.video.mime_type in ["video/mp4", "video/x-matroska"]:
        duration = message.video.duration
        file_id = message.video.file_id
    elif message.document and message.document.mime_type in ["video/mp4", "video/x-matroska"]:
        duration = message.document.attributes[0].duration
        file_id = message.document.file_id
    else:
        await message.reply("این فایل پشتیبانی نمی‌شود.")
        return

    user_states[user_id] = {
        "step": "awaiting_start_time",
        "duration": duration,
        "file_id": file_id
    }

    text = f"""تایم فایل ویدیویی شما: {duration} ثانیه
تایم شروع : {{-}} هنوز انتخاب نکردید
تایم پایان : {{-}} هنوز انتخاب نکردید"""
    await message.reply(text)
    await message.reply("تایم شروع را ارسال کن (فرمت hh:mm:ss)")

@Client.on_message(filters.text)
async def handle_time_input(client, message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state:
        return

    if state.get("step") == "awaiting_start_time":
        user_states[user_id]["start"] = message.text
        user_states[user_id]["step"] = "awaiting_end_time"
        await message.reply("حالا تایم پایان را ارسال کن (فرمت hh:mm:ss)")

    elif state.get("step") == "awaiting_end_time":
        user_states[user_id]["end"] = message.text
        state["step"] = "ready"

        text = f"""تایم فایل ویدیویی شما: {state['duration']} ثانیه
تایم شروع : {state['start']}
تایم پایان : {state['end']}"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("شروع", callback_data="start_cutting")]
        ])
        await message.reply(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("start_cutting"))
async def start_cutting_process(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    state = user_states.get(user_id)
    if not state:
        return

    await callback_query.answer("در حال دانلود فایل...")

    file_id = state["file_id"]
    original_path = await download_file_stream(client, file_id, user_id, callback_query.message)

    start_time = time_to_seconds(state["start"])
    end_time = time_to_seconds(state["end"])

    if start_time is None or end_time is None or end_time <= start_time:
        await callback_query.message.reply("فرمت تایم صحیح نیست یا تایم پایان کوچکتر از شروع است.")
        return

    await callback_query.message.reply("در حال برش ویدیو...")

    cut_path = f"{user_id}_cut.mp4"

    try:
        clip = VideoFileClip(original_path)
        clip_duration = clip.duration  # Getting the duration of the video

        # Ensure that the cut times are within the video duration range
        if start_time < 0 or end_time > clip_duration:
            await callback_query.message.reply("تایم برش خارج از محدوده ویدیو است.")
            return

        # Cut the video from start_time to end_time
        cut_clip = clip.subclip(start_time, end_time)
        cut_clip.write_videofile(cut_path, codec="libx264", audio_codec="aac")
        cut_clip.close()
        clip.close()

    except Exception as e:
        await callback_query.message.reply(f"خطا در برش ویدیو: {str(e)}")
        return
    finally:
        if os.path.exists(original_path):
            os.remove(original_path)

    await callback_query.message.reply("در حال ارسال فایل برش خورده...")
    
    # ارسال فایل برش خورده به کاربر
    await client.send_document(user_id, document=cut_path, caption="فایل برش خورده شما")

    os.remove(cut_path)
    await callback_query.message.reply("فایل با موفقیت برش خورد و برای شما ارسال شد.")
