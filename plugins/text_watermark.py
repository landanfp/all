from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.state import set_state, get_state, clear_state
from helper.watermark import add_text_watermark
from helper.progress import progress_bar
import os
import time

positions = [
    ("top_right", "بالا راست"), ("top_center", "بالا وسط"), ("top_left", "بالا چپ"),
    ("center_right", "وسط راست"), ("center", "وسط"), ("center_left", "وسط چپ"),
    ("bottom_right", "پایین راست"), ("bottom_center", "پایین وسط"), ("bottom_left", "پایین چپ")
]

sizes = [10, 15, 20, 25, 30, 35, 40, 45, 50]

@Client.on_callback_query(filters.regex("text_wm"))
async def ask_text(client, query: CallbackQuery):
    await query.message.edit("لطفا متن واترمارک را ارسال کنید:")
    set_state(query.from_user.id, "step", "text_input")

@Client.on_message(filters.text & filters.private)
async def handle_text_input(client, message: Message):
    if get_state(message.from_user.id, "step") == "text_input":
        set_state(message.from_user.id, "text", message.text)
        set_state(message.from_user.id, "step", "position")
        buttons = [[InlineKeyboardButton(pos[1], callback_data=f"text_pos_{pos[0]}")] for pos in positions]
        await message.reply("موقعیت واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^text_pos_"))
async def set_position(client, query: CallbackQuery):
    position = query.data.split("_")[-1]
    set_state(query.from_user.id, "position", position)
    set_state(query.from_user.id, "step", "size")
    size_buttons = [
        [InlineKeyboardButton(f"{s}%", callback_data=f"text_size_{s}") for s in sizes[i:i+5]]
        for i in range(0, len(sizes), 5)
    ]
    await query.message.edit("سایز واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(size_buttons))

@Client.on_callback_query(filters.regex("^text_size_"))
async def set_size(client, query: CallbackQuery):
    size = int(query.data.split("_")[-1])
    set_state(query.from_user.id, "size", size)
    set_state(query.from_user.id, "step", "ready")
    await query.message.edit("همه‌چیز آماده‌ست! حالا ویدیوی موردنظر را ارسال کن:")

@Client.on_message(filters.video & filters.private)
async def handle_video(client, message: Message):
    if get_state(message.from_user.id, "step") != "ready":
        return

    text = get_state(message.from_user.id, "text")
    position = get_state(message.from_user.id, "position")
    size = get_state(message.from_user.id, "size")

    msg = await message.reply("در حال دانلود ویدیو...")

    input_file = f"{message.video.file_unique_id}.mp4"
    output_file = f"wm_{input_file}"
    start = time.time()

    await message.download(file_name=input_file, progress=progress_bar, progress_args=(msg, start))

    await msg.edit("در حال افزودن واترمارک...")
    await add_text_watermark(input_file, output_file, text, position, size)

    await msg.edit("آپلود فایل...")
    await message.reply_video(output_file, caption="ویدیوی واترمارک‌خورده آماده شد!")

    os.remove(input_file)
    os.remove(output_file)
    clear_state(message.from_user.id)
    await msg.delete()
