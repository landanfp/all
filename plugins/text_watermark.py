# نام فایل: plugins/text_watermark.py (هندلرهای واترمارک متنی)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.state import set_state, get_state, clear_state
from helper.watermark import add_text_watermark
from helper.progress import progress_bar
import os
import time

# لیست موقعیت‌ها
positions = [
    ("top_right", "بالا راست"),
    ("top_center", "بالا وسط"),
    ("top_left", "بالا چپ"),
    ("center_right", "وسط راست"),
    ("center", "وسط"),
    ("center_left", "وسط چپ"),
    ("bottom_right", "پایین راست"),
    ("bottom_center", "پایین وسط"),
    ("bottom_left", "پایین چپ")
]
# (لیست سایزها از اینجا حذف شد و به تابع set_position منتقل شد)


async def ask_text(client, query: CallbackQuery):
    """درخواست متن واترمارک."""
    await query.message.edit("لطفا متن واترمارک را ارسال کنید:")
    set_state(query.from_user.id, "step", "text_input")

async def handle_text_input(client, message: Message):
    """دریافت متن و درخواست موقعیت."""
    user_id = message.from_user.id
    if get_state(user_id, "step") == "text_input":
        
        if not message.text or len(message.text.strip()) == 0:
            await message.reply("لطفا یک متن معتبر برای واترمارک ارسال کنید.")
            return

        set_state(user_id, "text", message.text.strip())
        set_state(user_id, "step", "position")
        
        # ساخت دکمه‌ها: هر ردیف 3 دکمه، ترتیب معکوس برای سازگاری با RTL تلگرام
        buttons = []
        for i in range(0, len(positions), 3):
            row_positions = positions[i:i+3]
            # معکوس کردن ترتیب دکمه‌ها برای نمایش درست از راست به چپ
            buttons_row = [InlineKeyboardButton(pos[1], callback_data=f"text_pos_{pos[0]}") for pos in reversed(row_positions)]
            buttons.append(buttons_row)
        
        await message.reply("موقعیت واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(buttons))

async def set_position(client, query: CallbackQuery):
    """دریافت موقعیت و درخواست سایز. (کد اصلاح شده طبق درخواست شما)"""
    user_id = query.from_user.id
    position = query.data.split("_", 2)[-1]  # فیکس: maxsplit=2

    if get_state(user_id, "step") != "position":
        await query.answer("لطفا مراحل را به ترتیب طی کنید.")
        return

    set_state(user_id, "position", position)
    set_state(user_id, "step", "size")
    
    # **** تغییر کلیدی: ساخت دکمه‌ها به صورت دستی طبق چیدمان درخواستی (چپ به راست) ****
    size_buttons = [
        # ردیف اول: 5% 10% 15%
        [
            InlineKeyboardButton("5%", callback_data="text_size_5"),
            InlineKeyboardButton("10%", callback_data="text_size_10"),
            InlineKeyboardButton("15%", callback_data="text_size_15")
        ],
        # ردیف دوم: 15% 20% 30%
        [
            InlineKeyboardButton("15%", callback_data="text_size_15"),
            InlineKeyboardButton("20%", callback_data="text_size_20"),
            InlineKeyboardButton("30%", callback_data="text_size_30")
        ]
    ]
    
    await query.message.edit("سایز واترمارک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(size_buttons))

async def set_size(client, query: CallbackQuery):
    """دریافت سایز و آماده‌سازی برای ویدیو."""
    user_id = query.from_user.id
    if get_state(user_id, "step") != "size":
        await query.answer("لطفا مراحل را به ترتیب طی کنید.")
        return

    size = int(query.data.split("_")[-1])
    set_state(user_id, "size", size)
    set_state(user_id, "step", "ready")
    await query.message.edit("✅ همه‌چیز آماده‌ست! حالا ویدیوی موردنظر را ارسال کن تا واترمارک متنی اضافه شود.")

async def handle_video(client, message: Message):
    """دریافت ویدیو، پردازش و ارسال خروجی. (کد اصلاح شده با نوار پیشرفت)"""
    user_id = message.from_user.id

    if get_state(user_id, "step") != "ready":
        return

    text = get_state(user_id, "text")
    position = get_state(user_id, "position")
    size = get_state(user_id, "size")
    
    if not text:
        await message.reply("❌ واترمارک متنی پیدا نشد. لطفا برای تنظیم مجدد، /start را ارسال کنید.")
        clear_state(user_id)
        return

    msg = await message.reply("⏳ در حال دانلود ویدیو...")

    # استفاده از یک نام محلی برای دانلود
    input_path_placeholder = f"{message.video.file_id}_{user_id}.mp4"
    output_file = f"wm_{message.video.file_id}_{user_id}.mp4"
    start = time.time()
    input_path = None # مسیر واقعی دانلود شده
    
    try:
        # **اصلاح ۱: گرفتن مسیر واقعی فایل دانلود شده**
        input_path = await message.download(file_name=input_path_placeholder, progress=progress_bar, progress_args=(msg, start, "دانلود"))

        # مرحله افزودن واترمارک (پیام قبلی "در حال افزودن واترمارک" حذف شد)
        # **** تغییر کلیدی: پاس دادن msg ****
        await add_text_watermark(input_path, output_file, text, position, size, msg) # استفاده از مسیر واقعی
        
        if not os.path.exists(output_file):
            raise Exception("فایل خروجی FFmpeg تولید نشد. (احتمالاً خطای فونت یا کدک)")

        # مرحله آپلود 
        await msg.edit("⬆️ در حال آپلود فایل...")
        await message.reply_video(
            output_file, 
            caption=f"ویدیوی واترمارک‌خورده شما با متن: {text}",
            progress=progress_bar, 
            progress_args=(msg, start, "آپلود"),
            supports_streaming=True
        )
        
        # **اصلاح ۲: حذف پیام پیشرفت در صورت موفقیت**
        await msg.delete()

    except Exception as e:
        print(f"Text Watermark Error: {e}")
        # در صورت خطا، پیام را ویرایش می‌کنیم و آن را حذف نمی‌کنیم.
        await msg.edit(f"❌ یک خطا رخ داد: {e}")

    finally:
        # **اصلاح ۳: حذف msg.delete() و فقط پاکسازی فایل‌ها**
        # پاکسازی فایل‌ها با استفاده از مسیر واقعی
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_file):
            os.remove(output_file)
        clear_state(user_id)
