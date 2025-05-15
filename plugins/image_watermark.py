from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.state import set_state, get_state, clear_state
from helper.watermark import add_image_watermark
from helper.progress import progress_bar
import os
import time

@Client.on_callback_query(filters.regex("image_wm"))
async def ask_image(client, query: CallbackQuery):
    await query.message.edit("لطفا تصویری برای واترمارک ارسال کنید (فقط jpg یا png):")
    set_state(query.from_user.id, "step", "image_upload")

@Client.on_message(filters.private & filters.photo)
async def handle_image_upload(client, message: Message):
    if get_state(message.from_user.id, "step") != "image_upload":
        return

    file = await message.download()
    if not file.endswith((".jpg", ".png")):
        await message.reply("لطفا فقط فایل با فرمت png یا jpg ارسال کنید.")
        return

    set_state(message.from_user.id, "image_path", file)
    set_state(message.from_user.id, "step", "position")
    buttons = [[InlineKeyboardButton(pos[1], callback_data=f"image_pos_{pos[0]}")] for pos in positions]
    await message.reply("موقعیت تصویر واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^image_pos_"))
async def set_image_position(client, query: CallbackQuery):
    position = query.data.split("_")[-1]
    set_state(query.from_user.id, "position", position)
    set_state(query.from_user.id, "step", "size")
    size_buttons = [
        [InlineKeyboardButton(f"{s}%", callback_data=f"image_size_{s}") for s in sizes[i:i+5]]
        for i in range(0, len(sizes), 5)
    ]
    await query.message.edit("سایز تصویر واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(size_buttons))

@Client.on_callback_query(filters.regex("^image_size_"))
async def set_image_size(client, query: CallbackQuery):
    size = int(query.data.split("_")[-1])
    set_state(query.from_user.id, "size", size)
    set_state(query.from_user.id, "step", "ready_img")
    await query.message.edit("حالا ویدیوی موردنظر برای افزودن تصویر را ارسال کنید:")

@Client.on_message(filters.video & filters.private)
async def process_image_watermark(client, message: Message):
    if get_state(message.from_user.id, "step") != "ready_img":
        return

    image = get_state(message.from_user.id, "image_path")
    position = get_state(message.from_user.id, "position")
    size = get_state(message.from_user.id, "size")

    msg = await message.reply("در حال دانلود ویدیو...")

    input_file = f"{message.video.file_unique_id}.mp4"
    output_file = f"imgwm_{input_file}"
    start = time.time()

    await message.download(file_name=input_file, progress=progress_bar, progress_args=(msg, start))

    await msg.edit("در حال افزودن تصویر واترمارک...")
    await add_image_watermark(input_file, output_file, image, position, size)

    await msg.edit("در حال آپلود فایل نهایی...")
    await message.reply_video(output_file, caption="ویدیوی نهایی آماده شد!")

    os.remove(input_file)
    os.remove(output_file)
    os.remove(image)
    clear_state(message.from_user.id)
    await msg.delete()
