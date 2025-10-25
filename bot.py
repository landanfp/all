import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAEE8OIOqLYxbnwesF3ki2sOsXr03Q90JiI'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    return str(timedelta(seconds=seconds))

@app.on_message(filters.command("start"))
async def start(_, message):
    user_id = message.from_user.id
    # اگر کاربر از قبل در وضعیتی بوده، آن را پاک می‌کنیم
    if user_id in user_state:
        del user_state[user_id]
        
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✂️ شروع برش", callback_data="start_cutting")]]
    )
    await message.reply("سلام! من ربات برش ویدیو هستم.\n\n"
                      "برای شروع، روی دکمه زیر کلیک کن و ویدیوی خود را ارسال نما.", 
                      reply_markup=keyboard)

@app.on_callback_query()
async def handle_callback(_, callback_query):
    user_id = callback_query.from_user.id

    if callback_query.data == "start_cutting":
        user_state[user_id] = {
            "step": "awaiting_video"
        }
        await callback_query.message.edit("لطفاً ویدیوی موردنظر را ارسال کنید.")
        await callback_query.answer()

    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state:
            await callback_query.answer("خطا: وضعیت شما یافت نشد. لطفاً از /start شروع کنید.", show_alert=True)
            return

        # تعریف مسیر فایل‌های موقت
        temp_input = f"{user_id}_input.mp4"
        temp_output = f"{user_id}_cut.mp4"
        
        try:
            # 1. اطلاع‌رسانی و شروع دانلود
            await callback_query.answer("⏳ در حال دانلود ویدیو...", show_alert=False)
            
            # اطمینان از اینکه پیام اصلی دکمه "شروع برش" را از دست ندهد
            await callback_query.message.edit_reply_markup(None)
            
            video_msg = await app.get_messages(callback_query.message.chat.id, state["video_msg_id"])
            
            if not video_msg.video:
                 await callback_query.message.reply("❌ خطای داخلی: پیام ذخیره شده ویدیو نیست. لطفاً /start را بزنید.")
                 return # user_state در 'finally' پاک می‌شود

            # دانلود ویدیو
            downloaded_file_path = await video_msg.download(file_name=temp_input)

            # بررسی اینکه آیا فایل واقعا دانلود شده است
            if downloaded_file_path is None or not os.path.exists(downloaded_file_path):
                await callback_query.message.reply("❌ خطا در دانلود ویدیو: فایل پس از دانلود پیدا نشد. لطفاً ویدیو را دوباره ارسال کنید.")
                return # user_state در 'finally' پاک می‌شود

            # 2. اطلاع‌رسانی و شروع برش
            status_msg = await callback_query.message.reply("🔄 در حال پردازش و برش ویدیو... (این ممکن است کمی طول بکشد)")
            
            start = state["start_time"]
            end = state["end_time"]

            # اجرای دستور ffmpeg
            (
                ffmpeg
                .input(downloaded_file_path, ss=start)
                .output(temp_output, to=end, **{'c:v': 'libx264', 'preset': 'medium', 'crf': 23, 'c:a': 'aac'})
                .run(overwrite_output=True)
            )
            
            if not os.path.exists(temp_output):
                await status_msg.edit("❌ خطا در پردازش ویدیو: فایل خروجی ایجاد نشد.")
                return # user_state در 'finally' پاک می‌شود

            # 3. اطلاع‌رسانی و آپلود
            await status_msg.edit("📤 در حال آپلود ویدیوی برش خورده...")
            await app.send_video(
                callback_query.message.chat.id, 
                temp_output,
                caption=f"✅ برش موفق!\nاز: {start}\nتا: {end}",
                reply_to_message_id=callback_query.message.id
            )
            
            # 4. پیام نهایی
            await status_msg.delete() # پیام وضعیت را پاک می‌کنیم
            # پیام اصلی که زمان‌ها را نشان می‌داد را ویرایش می‌کنیم
            await app.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=state["video_edit_msg"],
                text=f"✅ عملیات با موفقیت انجام شد.\n\n"
                     f"⏱ زمان ویدیو: {state['duration']}\n"
                     f"⏳ تایم شروع: {state['start_time']}\n"
                     f"⏳ تایم پایان: {state['end_time']}",
                reply_markup=None # دکمه‌ها را حذف کن
            )

        except Exception as e:
            # گرفتن هرگونه خطا (دانلود، ffmpeg، آپلود و ...)
            error_message = f"❌ یک خطای غیرمنتظره رخ داد:\n`{e}`\n\nلطفاً دوباره با /start تلاش کنید."
            await callback_query.message.reply(error_message)
            print(f"Error during cut_now for user {user_id}: {e}") # لاگ خطا در کنسول
        
        finally:
            # 5. پاک‌سازی فایل‌های موقت و وضعیت کاربر
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            if user_id in user_state:
                del user_state[user_id]

@app.on_message(filters.video)
async def handle_video(_, message):
    user_id = message.from_user.id

    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    duration = seconds_to_hms(message.video.duration)
    duration_sec = message.video.duration

    text = (
        f"⏱ کل زمان ویدیو: {duration}\n"
        f"⏳ تایم شروع: (هنوز وارد نشده)\n"
        f"⏳ تایم پایان: (هنوز وارد نشده)"
    )
    # پیامی که زمان‌ها را نشان می‌دهد
    sent_msg = await message.reply(text)

    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id, # آیدی پیام ویدیوی اصلی
        "video_edit_msg": sent_msg.id, # آیدی پیامی که ویرایش می‌شود
        "duration": duration,
        "duration_sec": duration_sec,
        "start_time": None,
        "end_time": None
    })

    await message.reply("لطفاً تایم شروع را ارسال کنید.\n"
                      "فرمت: `hh:mm:ss` (ساعت:دقیقه:ثانیه) یا فقط ثانیه (مثلاً `30` برای ثانیه ۳۰)")

@app.on_message(filters.text & filters.private)
async def handle_time(_, message):
    user_id = message.from_user.id
    state = user_state.get(user_id)

    # اگر کاربر دستوری مثل /start را وارد کرد، نادیده بگیر
    if message.text.startswith("/"):
        return
        
    if not state:
        return

    # TODO: در اینجا باید اعتبارسنجی بهتری برای ورودی زمان انجام شود
    # اما فعلاً به سادگی متن ورودی را قبول می‌کنیم

    if state["step"] == "awaiting_start":
        user_state[user_id]["start_time"] = message.text
        state["step"] = "awaiting_end" # بروزرسانی state محلی

        video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
        new_text = (
            f"⏱ کل زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: (هنوز وارد نشده)"
        )
        await video_msg.edit(new_text)
        await message.reply("عالی. حالا تایم پایان را وارد کنید (مثلاً `00:01:30` یا `90`)")

    elif state["step"] == "awaiting_end":
        user_state[user_id]["end_time"] = message.text
        state["step"] = "ready" # بروزرسانی state محلی

        video_msg = await app.get_messages(message.chat.id, state["video_edit_msg"])
        new_text = (
            f"⏱ کل زمان ویدیو: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
...
