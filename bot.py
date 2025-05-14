import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageFilter

# تنظیمات ربات - مقادیر خودت رو جایگزین کن
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'


app = Client("image_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ذخیره اطلاعات کاربران
user_data = {}  # ساختار: {user_id: {"path": "file.jpg", "actions": set()}}

# هندل پیام عکس
@app.on_message(filters.photo)
async def handle_photo(client, message):
    user_id = message.from_user.id
    file_path = f"{user_id}_original.jpg"
    await message.download(file_path)
    
    user_data[user_id] = {"path": file_path, "actions": set()}

    # دکمه‌ها
    buttons = [
        [InlineKeyboardButton("افزایش کیفیت", callback_data="upscale")],
        [InlineKeyboardButton("تبدیل به Marvel", callback_data="marvel")],
        [InlineKeyboardButton("حذف پس‌زمینه", callback_data="remove_bg")],
        [InlineKeyboardButton("کارتونی کن", callback_data="cartoon")],
    ]
    await message.reply(
        "کدام عملیات‌ها را می‌خواهی انجام دهم؟",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# هندل کلیک روی دکمه‌ها
@app.on_callback_query()
async def handle_callback(client, callback_query):
    user_id = callback_query.from_user.id
    action = callback_query.data

    if user_id not in user_data:
        await callback_query.answer("اول باید عکسی بفرستی.")
        return

    if action == "start":
        await start_processing(client, callback_query)
        return

    user_data[user_id]["actions"].add(action)
    await callback_query.answer("اضافه شد.")

    # دکمه شروع نمایش بده
    if len(user_data[user_id]["actions"]) >= 1:
        await callback_query.message.reply(
            "برای شروع پردازش، روی دکمه زیر کلیک کن:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("شروع پردازش", callback_data="start")]])
        )

# پردازش عکس
async def start_processing(client, callback_query):
    user_id = callback_query.from_user.id
    data = user_data.get(user_id)

    if not data:
        await callback_query.answer("خطا در پردازش.")
        return

    input_path = data["path"]
    actions = data["actions"]
    current_path = input_path

    await callback_query.message.reply("در حال پردازش تصویر...")

    try:
        # افزایش کیفیت (نمونه ساده)
        if "upscale" in actions:
            img = Image.open(current_path)
            img = img.resize((img.width * 2, img.height * 2))
            current_path = f"{user_id}_upscaled.jpg"
            img.save(current_path)

        # حذف پس‌زمینه (نمونه ساده با سفیدبُری)
        if "remove_bg" in actions:
            img = Image.open(current_path).convert("RGBA")
            datas = img.getdata()
            new_data = []
            for item in datas:
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            current_path = f"{user_id}_nobg.png"
            img.save(current_path)

        # کارتونی کردن (نمونه ساده)
        if "cartoon" in actions:
            img = Image.open(current_path).convert("RGB")
            img = img.filter(ImageFilter.EDGE_ENHANCE)
            current_path = f"{user_id}_cartoon.jpg"
            img.save(current_path)

        # تبدیل به Marvel (در آینده می‌تونی Stable Diffusion وصل کنی)
        if "marvel" in actions:
            img = Image.open(current_path)
            current_path = f"{user_id}_marvel.jpg"
            img.save(current_path)

        # ارسال فایل نهایی
        await client.send_document(user_id, current_path, caption="پردازش کامل شد!")

    except Exception as e:
        await callback_query.message.reply(f"خطا در پردازش: {e}")
    
    # پاکسازی فایل‌ها
    try:
        os.remove(data["path"])
        os.remove(current_path)
    except:
        pass
    del user_data[user_id]

# اجرای ربات
app.run()
