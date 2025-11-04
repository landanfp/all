# نام فایل: plugins/image_watermark.py (هندلرهای واترمارک تصویری)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.state import set_state, get_state, clear_state
from helper.watermark import add_image_watermark
from helper.progress import progress_bar
import os
import time

positions = [
    ("top_right", "بالا راست"), ("top_center", "بالا وسط"), ("top_left", "بالا چپ"),
    ("center_right", "وسط راست"), ("center", "وسط"), ("center_left", "وسط چپ"),
    ("bottom_right", "پایین راست"), ("bottom_center", "پایین وسط"), ("bottom_left", "پایین چپ")
]

sizes = [10, 15, 20, 25, 30, 35, 40, 45, 50]

async def ask_image(client, query: CallbackQuery):
    """درخواست تصویر واترمارک."""
    await query.message.edit("لطفا تصویری برای واترمارک ارسال کنید (فقط jpg یا png):")
    set_state(query.from_user.id, "step", "image_upload")

async def handle_image_upload(client, message: Message):
    """دریافت تصویر واترمارک و درخواست موقعیت."""
    user_id = message.from_user.id
    if get_state(user_id, "step") != "image_upload":
        return

    # برای جلوگیری از خطای AttributeError اگر فایل نام نداشته باشد.
    file_extension = "jpg"
    if message.photo.file_name and '.' in message.photo.file_name:
         file_extension = message.photo.file_name.split('.')[-1].lower()
    
    temp_path = f"{message.photo.file_unique_id}_{user_id}.{file_extension}"
    image_file = await message.download(file_name=temp_path)

    if not image_file.lower().endswith((".jpg", ".png", ".jpeg")):
        await message.reply("لطفا فقط فایل با فرمت png، jpg یا jpeg ارسال کنید.")
        os.remove(image_file)
        return

    set_state(user_id, "image_path", image_file)
    set_state(user_id, "step", "position")
    
    buttons = [[InlineKeyboardButton(pos[1], callback_data=f"image_pos_{pos[0]}")] for pos in positions]
    await message.reply("موقعیت تصویر واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))

async def set_image_position(client, query: CallbackQuery):
    """دریافت موقعیت و درخواست سایز."""
    user_id = query.from_user.id
    if get_state(user_id, "step") != "position":
        await query.answer("لطفا مراحل را به ترتیب طی کنید.")
        return

    position = query.data.split("_")[-1]
    set_state(user_id, "position", position)
    set_state(user_id, "step", "size")

    size_buttons = [
        [InlineKeyboardButton(f"{s}%", callback_data=f"image_size_{s}") for s in sizes[i:i+5]]
        for i in range(0, len(sizes), 5)
    ]
    await query.message.edit("سایز تصویر واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(size_buttons))

async def set_image_size(client, query: CallbackQuery):
    """دریافت سایز و آماده‌سازی برای ویدیو."""
    user_id = query.from_user.id
    if get_state(user_id, "step") != "size":
        await query.answer("لطفا مراحل را به ترتیب طی کنید.")
        return

    size = int(query.data.split("_")[-1])
    set_state(user_id, "size", size)
    set_state(user_id, "step", "ready_img")
    await query.message.edit("✅ همه‌چیز آماده‌ست! حالا ویدیوی موردنظر برای افزودن تصویر را ارسال کنید:")

async def process_image_watermark(client, message: Message):
    """دریافت ویدیو، پردازش و ارسال خروجی (واترمارک تصویری)."""
    user_id = message.from_user.id

    if get_state(user_id, "step") != "ready_img":
        return

    image = get_state(user_id, "image_path")
    position = get_state(user_id, "position")
    size = get_state(user_id, "size")

    if not image or not os.path.exists(image):
        await message.reply("❌ مسیر تصویر واترمارک پیدا نشد. لطفا دوباره شروع کنید.")
        # تصویر قبلی (اگر وجود داشت) حذف می‌شود
        if image and os.path.exists(image): os.remove(image)
        clear_state(user_id)
        return

    msg = await message.reply("⏳ در حال دانلود ویدیو...")

    input_file = f"{message.video.file_id}_{user_id}.mp4"
    output_file = f"imgwm_{message.video.file_id}_{user_id}.mp4"
    start = time.time()

    try:
        # مرحله دانلود
        await message.download(file_name=input_file, progress=progress_bar, progress_args=(msg, start, "دانلود"))

        # مرحله افزودن واترمارک
        await msg.edit("⚙️ در حال افزودن تصویر واترمارک...")
        await add_image_watermark(input_file, output_file, image, position, size)

        if not os.path.exists(output_file):
             await msg.edit("❌ عملیات واترمارک‌گذاری ناموفق بود. (خطای FFmpeg)")
             return

        # مرحله آپلود
        await msg.edit("⬆️ در حال آپلود فایل نهایی...")
        await message.reply_video(
            output_file, 
            caption="ویدیوی نهایی با واترمارک تصویری آماده شد!",
            progress=progress_bar, 
            progress_args=(msg, start, "آپلود"),
            supports_streaming=True
        )

    except Exception as e:
        print(f"Image Watermark Error: {e}")
        await msg.edit(f"❌ یک خطا رخ داد: {e}")

    finally:
        # حذف فایل‌ها و پاکسازی وضعیت
        await msg.delete()
        if os.path.exists(input_file): os.remove(input_file)
        if os.path.exists(output_file): os.remove(output_file)
        if os.path.exists(image): os.remove(image) # حذف تصویر واترمارک
        clear_state(user_id)
