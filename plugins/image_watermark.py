# نام فایل: plugins/image_watermark.py (هندلرهای واترمارک تصویری - فیکس Pyrogram edit error)
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified  # فیکس import برای except
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
    user_id = query.from_user.id
    try:
        await query.message.edit("لطفا تصویری برای واترمارک ارسال کنید (فقط jpg یا png):")
    except MessageNotModified:
        pass  # ignore اگر message همون باشه (چندبار callback)
    set_state(user_id, "step", "image_upload")
    print(f"Debug: Set step to 'image_upload' for user {user_id}")  # لاگ set state

async def handle_image_upload(client, message: Message):
    """دریافت تصویر واترمارک و درخواست موقعیت (پشتیبانی از photo و document)."""
    user_id = message.from_user.id
    current_step = get_state(user_id, "step")
    msg_type = 'photo' if message.photo else ('document' if message.document else 'unknown')
    print(f"Debug: Image handler triggered for user {user_id}, current step: {current_step}, type: {msg_type}")  # لاگ trigger
    
    if current_step != "image_upload":
        print(f"Debug: Wrong step for user {user_id}, skipping.")  # لاگ skip
        await message.reply("❌ لطفا ابتدا گزینه '🖼️ واترمارک تصویری' را انتخاب کنید و مراحل را به ترتیب طی کنید. (/start)")
        return

    # **چک mime_type برای document (فقط image/jpeg یا image/png)**
    if message.document:
        mime_type = message.document.mime_type
        if not mime_type or mime_type not in ['image/jpeg', 'image/png']:
            print(f"Debug: Invalid mime_type for user {user_id}: {mime_type}")
            await message.reply("❌ لطفا فقط فایل jpg یا png (به عنوان تصویر) ارسال کنید.")
            return

    # **فیکس: گرفتن file_name از photo (file_unique_id) یا document (file_name)**
    file_name = None
    if message.photo:
        file_name = f"{message.photo.file_unique_id}.jpg"  # photo همیشه jpg
    elif message.document:
        file_name = message.document.file_name or f"{message.document.file_unique_id}.jpg"
    
    file_extension = file_name.split('.')[-1].lower() if file_name and '.' in file_name else "jpg"
    
    temp_path = f"{getattr(message.photo, 'file_unique_id', getattr(message.document, 'file_unique_id', 'unknown'))}_{user_id}.{file_extension}"
    try:
        image_file = await message.download(file_name=temp_path)
        print(f"Debug: Image downloaded to {image_file}")  # لاگ دانلود
    except Exception as e:
        print(f"Download Error for user {user_id}: {e}")
        await message.reply("❌ خطا در دانلود تصویر. لطفا دوباره امتحان کنید.")
        return

    # چک فرمت بعد دانلود (اضافی برای امنیت)
    if not image_file.lower().endswith((".jpg", ".png", ".jpeg")):
        await message.reply("لطفا فقط فایل با فرمت png، jpg یا jpeg ارسال کنید.")
        if os.path.exists(image_file):
            os.remove(image_file)
        return

    set_state(user_id, "image_path", image_file)
    set_state(user_id, "step", "position")
    
    # ساخت دکمه‌ها: هر ردیف 3 دکمه، ترتیب معکوس برای سازگاری با RTL تلگرام
    buttons = []
    for i in range(0, len(positions), 3):
        row_positions = positions[i:i+3]
        # معکوس کردن ترتیب دکمه‌ها برای نمایش درست از راست به چپ
        buttons_row = [InlineKeyboardButton(pos[1], callback_data=f"image_pos_{pos[0]}") for pos in reversed(row_positions)]
        buttons.append(buttons_row)
    await message.reply("موقعیت تصویر واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))
    print(f"Debug: Image processed, set step to 'position' for user {user_id}")  # لاگ موفقیت

async def set_image_position(client, query: CallbackQuery):
    """دریافت موقعیت و درخواست سایز."""
    user_id = query.from_user.id
    if get_state(user_id, "step") != "position":
        await query.answer("لطفا مراحل را به ترتیب طی کنید.")
        return

    position = query.data.split("_", 2)[-1]  # فیکس: maxsplit=2 برای گرفتن کل 'top_right'
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
        if image and os.path.exists(image): os.remove(image)
        clear_state(user_id)
        return

    msg = await message.reply("⏳ در حال دانلود ویدیو...")

    input_path_placeholder = f"{message.video.file_id}_{user_id}.mp4"
    output_file = f"imgwm_{message.video.file_id}_{user_id}.mp4"
    start = time.time()
    input_path = None # مسیر واقعی دانلود شده

    try:
        # **اصلاح ۱: گرفتن مسیر واقعی فایل دانلود شده**
        input_path = await message.download(file_name=input_path_placeholder, progress=progress_bar, progress_args=(msg, start, "دانلود"))

        # مرحله افزودن واترمارک
        await msg.edit("⚙️ در حال افزودن تصویر واترمارک...")
        await add_image_watermark(input_path, output_file, image, position, size)

        if not os.path.exists(output_file):
             raise Exception("فایل خروجی MoviePy تولید نشد. (احتمالاً خطای فایل یا کدک)")

        # مرحله آپلود
        await msg.edit("⬆️ در حال آپلود فایل نهایی...")
        await message.reply_video(
            output_file, 
            caption="ویدیوی نهایی با واترمارک تصویری آماده شد!",
            progress=progress_bar,
            progress_args=(msg, start, "آپلود"),
            supports_streaming=True
        )
        
        # **اصلاح ۲: حذف پیام پیشرفت در صورت موفقیت**
        await msg.delete()

    except Exception as e:
        print(f"Image Watermark Error: {e}")
        # در صورت خطا، پیام را ویرایش می‌کنیم و آن را حذف نمی‌کنیم.
        await msg.edit(f"❌ یک خطا رخ داد: {e}")

    finally:
        # **اصلاح ۳: حذف msg.delete() و فقط پاکسازی فایل‌ها**
        # پاکسازی فایل‌ها با استفاده از مسیر واقعی
        if input_path and os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_file): os.remove(output_file)
        if os.path.exists(image): os.remove(image) # حذف تصویر واترمارک
        clear_state(user_id)
