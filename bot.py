import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
from datetime import timedelta
# --- واردات جدید برای رفع خطای Health Check ---
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# <<< واردات جدید برای برش صدا >>>
# دو تابع اصلی را از فایل audio_trimmer.py ایمپورت می‌کنیم.
from audio_trimmer import handle_audio_file, cut_audio_action 


# --- تنظیمات (Configuration) ---
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '8189638115:AAEYMDvummCXAPgdpavZbYHa3YuXpOzkRBY'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}

def seconds_to_hms(seconds):
    """تبدیل ثانیه به فرمت زمان (hh:mm:ss)."""
    return str(timedelta(seconds=seconds))

# ===============================================
# --- بخش Health Check ---
# (بدون تغییر)
# ===============================================

class HealthCheckHandler(BaseHTTPRequestHandler):
    """پاسخ دهنده ساده به درخواست‌های HTTP برای بررسی سلامت."""
    def do_GET(self):
        # پاسخ 200 OK
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_health_server():
    """شروع سرور HTTP در پورت 8000."""
    server_address = ('0.0.0.0', 8000)
    try:
        httpd = HTTPServer(server_address, HealthCheckHandler)
        print("✅ Health Check Server started on port 8000.")
        httpd.serve_forever()
    except Exception as e:
        print(f"❌ Failed to start Health Check Server: {e}")

# ===============================================
# --- توابع ربات ---
# ===============================================

@app.on_message(filters.command("start"))
async def start(_, message):
    """پاسخ به دستور /start و نمایش دکمه شروع."""
    # <<< دکمه برش صدا اضافه شد >>>
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✂️ شروع برش ویدیو", callback_data="start_cutting")],
            [InlineKeyboardButton("🎧 شروع برش صدا", callback_data="start_audio_cutting")] # دکمه جدید
        ]
    )
    await message.reply("سلام! برای برش ویدیو یا صدا روی دکمه موردنظر کلیک کن:", reply_markup=keyboard)

@app.on_callback_query()
async def handle_callback(client, callback_query):
    """مدیریت دکمه‌های شیشه‌ای."""
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    if callback_query.data == "start_cutting":
        user_state[user_id] = {
            "step": "awaiting_video",
            "media_type": "video" # اضافه کردن نوع مدیا
        }
        prompt_msg = await callback_query.message.reply("لطفاً ویدیوی موردنظر را ارسال کنید.")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id
        await callback_query.answer()
    
    # <<< مدیریت دکمه جدید برش صدا >>>
    elif callback_query.data == "start_audio_cutting":
        user_state[user_id] = {
            "step": "awaiting_audio", # تغییر استپ برای فایل صوتی
            "media_type": "audio" # اضافه کردن نوع مدیا
        }
        prompt_msg = await callback_query.message.reply("لطفاً فایل صوتی (MP3) موردنظر را ارسال کنید.")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id
        await callback_query.answer()

    # <<< مدیریت برش ویدیو (قبلی) >>>
    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state or state.get("media_type") != "video": # چک کردن نوع مدیا
            await callback_query.answer("فرآیند برش منقضی شده است. دوباره شروع کنید.", show_alert=True)
            return

        await callback_query.answer("در حال برش ویدیو...")
        
        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        expected_input_filename = f"{user_id}_input.mp4"
        temp_output = f"{user_id}_cut.mp4"
        downloaded_file_path = None

        try:
            # --- دانلود ویدیو (مسیر واقعی فایل را دریافت می‌کنیم) ---
            video_msg = await app.get_messages(chat_id, state["video_msg_id"])
            
            processing_msg = await callback_query.message.reply("🔄 در حال دانلود ویدیو...")
            downloaded_file_path = await video_msg.download(expected_input_filename)
            
            if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                raise Exception("دانلود ویدیو ناموفق بود یا فایل ورودی پیدا نشد.")

            start = state["start_time"]
            end = state["end_time"]

            await processing_msg.edit_text("⚡️ در حال برش سریع (کپی جریان)...")

            # --- برش با FFmpeg: استفاده از Stream Copy (فوق سریع) ---
            (
                ffmpeg
                .input(downloaded_file_path, ss=start) 
                .output(temp_output, to=end, c="copy", loglevel="error")
                .run(overwrite_output=True)
            )

            # --- آپلود و ارسال نتیجه ---
            await processing_msg.edit_text("📤 در حال ارسال ویدیوی برش‌خورده...")
            await app.send_video(chat_id, temp_output)
            await processing_msg.edit_text("✅ تمام شد! ویدیوی برش‌خورده ارسال شد.")

        except ffmpeg.Error as e:
            error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است."
            await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`\n\n**توجه:** این خطا ممکن است به دلیل عدم امکان برش دقیق در نقطه زمانی درخواستی (Keyframe) رخ داده باشد. اگر ادامه داشت، باید از روش کندتر استفاده کرد.")
        except Exception as e:
            await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: دانلود یا پردازش با مشکل مواجه شد. `{e}`")
        finally:
            # --- پاکسازی فایل‌ها و وضعیت ---
            if downloaded_file_path and os.path.exists(downloaded_file_path):
                os.remove(downloaded_file_path)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
            if user_id in user_state:
                del user_state[user_id]
    
    # <<< مدیریت برش صدا (جدید - از فایل جداگانه فراخوانی می‌شود) >>>
    elif callback_query.data == "cut_audio_now":
        # فراخوانی تابع برش صدا از فایل جداگانه
        await cut_audio_action(client, callback_query)


@app.on_message(filters.video)
async def handle_video(_, message):
    """دریافت ویدیو و ذخیره وضعیت."""
    user_id = message.from_user.id
    
    # <<< اطمینان از اینکه کاربر در حالت انتظار ویدیو است >>>
    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    if "prompt_msg_id" in user_state[user_id]:
        try:
            await app.delete_messages(message.chat.id, user_state[user_id]["prompt_msg_id"])
        except Exception:
            pass

    duration = seconds_to_hms(message.video.duration)

    text = (
        f"⏱ زمان ویدیو: {duration}\n"
        f"⏳ تایم شروع: ...\n"
        f"⏳ تایم پایان: ..."
    )
    sent_msg = await message.reply(text)
    
    # <<< استفاده از media_edit_msg برای هماهنگی با handle_time >>>
    user_state[user_id].update({
        "step": "awaiting_start",
        "video_msg_id": message.id,
        "media_edit_msg": sent_msg.id, # تغییر نام برای هماهنگی با handle_time
        "duration": duration,
        "start_time": None,
        "end_time": None
    })

    prompt_msg = await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")
    user_state[user_id]["prompt_msg_id"] = prompt_msg.id

# <<< اضافه کردن هندلر فایل صوتی از فایل جداگانه >>>
# این خط، تابع handle_audio_file از audio_trimmer.py را برای فیلتر filters.audio فعال می‌کند.
app.add_handler(handle_audio_file)


@app.on_message(filters.text)
async def handle_time(_, message):
    """دریافت زمان شروع و پایان و به‌روزرسانی پیام اصلی."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    state = user_state.get(user_id)

    if not state or state.get("step") not in ["awaiting_start", "awaiting_end"]:
        return

    # <<< استفاده از media_edit_msg به جای video_edit_msg >>>
    try:
        video_msg = await app.get_messages(chat_id, state["media_edit_msg"])
    except Exception:
        return

    user_message_id = message.id
    prompt_message_id = state.pop("prompt_msg_id", None)

    if prompt_message_id:
        try:
            await app.delete_messages(chat_id, [user_message_id, prompt_message_id])
        except Exception:
            pass
    
    # تعیین نوع مدیا برای پیام‌ها و دکمه نهایی
    media_type = state.get("media_type", "video") # پیش‌فرض ویدیو
    media_label = "ویدیو" if media_type == "video" else "فایل صوتی"
    callback_data = "cut_now" if media_type == "video" else "cut_audio_now"
    
    if state["step"] == "awaiting_start":
        user_state[user_id]["start_time"] = message.text
        state["step"] = "awaiting_end"

        new_text = (
            f"⏱ زمان {media_label}: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: ..."
        )
        await video_msg.edit_text(new_text)
        
        prompt_msg = await message.reply("حالا تایم پایان را وارد کنید (hh:mm:ss)")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id

    elif state["step"] == "awaiting_end":
        user_state[user_id]["end_time"] = message.text
        state["step"] = "ready"

        new_text = (
            f"⏱ زمان {media_label}: {state['duration']}\n"
            f"⏳ تایم شروع: {state['start_time']}\n"
            f"⏳ تایم پایان: {state['end_time']}"
        )
        # <<< استفاده از callback_data صحیح >>>
        await video_msg.edit_text(new_text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("شروع برش", callback_data=callback_data)]]
        ))

# ===============================================
# --- شروع برنامه اصلی ---
# ===============================================

if __name__ == "__main__":
    # 1. سرور Health Check را در یک Thread جداگانه شروع می‌کنیم.
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True 
    health_thread.start()

    # 2. ربات Pyrogram را شروع می‌کنیم.
    app.run()
