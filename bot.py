import os
import asyncio
import ffmpeg
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.handlers import MessageHandler

# <<< ایمپورت متغیرهای مشترک و توابع مورد نیاز >>>
from config import API_ID, API_HASH, BOT_TOKEN, app, user_state, seconds_to_hms
from audio_trimmer import handle_audio_file, cut_audio_action # این دو تابع از audio_trimmer ایمپورت می‌شوند

# ===============================================
# --- بخش Health Check ---
# ===============================================

class HealthCheckHandler(BaseHTTPRequestHandler):
    """پاسخ دهنده ساده به درخواست‌های HTTP برای بررسی سلامت."""
    def do_GET(self):
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
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✂️ شروع برش ویدیو", callback_data="start_cutting")],
            [InlineKeyboardButton("🎧 شروع برش صدا", callback_data="start_audio_cutting")]
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
            "media_type": "video" 
        }
        prompt_msg = await callback_query.message.reply("لطفاً ویدیوی موردنظر را ارسال کنید.")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id
        await callback_query.answer()
    
    elif callback_query.data == "start_audio_cutting":
        user_state[user_id] = {
            "step": "awaiting_audio",
            "media_type": "audio" 
        }
        prompt_msg = await callback_query.message.reply("لطفاً فایل صوتی موردنظر را ارسال کنید (مانند MP3 یا M4A).")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id
        await callback_query.answer()

    # <<< مدیریت برش ویدیو (با اصلاح Duration) >>>
    elif callback_query.data == "cut_now":
        state = user_state.get(user_id)
        if not state or state.get("media_type") != "video":
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
            video_msg = await app.get_messages(chat_id, state["video_msg_id"])
            
            processing_msg = await callback_query.message.reply("🔄 در حال دانلود ویدیو...")
            downloaded_file_path = await video_msg.download(expected_input_filename)
            
            if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                raise Exception("دانلود ویدیو ناموفق بود یا فایل ورودی پیدا نشد.")

            start = state["start_time"]
            end = state["end_time"]

            # --- محاسبه Duration برای برش دقیق ---
            # تبدیل Start و End به ثانیه
            start_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], start.split(':')))
            end_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], end.split(':')))

            # محاسبه Duration (مدت زمان برش)
            duration_seconds = end_seconds - start_seconds
            
            # Duration را به رشته hh:mm:ss تبدیل می‌کنیم
            duration_hms = seconds_to_hms(duration_seconds)
            # ------------------------------------

            await processing_msg.edit_text("⚡️ در حال برش سریع (کپی جریان)...")

            # --- برش با FFmpeg: استفاده از Stream Copy و پارامتر Duration (t) ---
            ffmpeg_process = (
                ffmpeg
                .input(downloaded_file_path, ss=start) 
                .output(temp_output, t=duration_hms, c="copy", loglevel="error")
            )
            
            # اجرای FFmpeg به صورت غیر-بلاک
            await asyncio.to_thread(ffmpeg_process.run, overwrite_output=True)

            await processing_msg.edit_text("📤 در حال ارسال ویدیوی برش‌خورده...")
            await app.send_video(chat_id, temp_output)
            await processing_msg.edit_text("✅ تمام شد! ویدیوی برش‌خورده ارسال شد.")

        except ffmpeg.Error as e:
            error_details = e.stderr.decode('utf8', errors='ignore') if e.stderr else "جزئیات خطا نامشخص است."
            await app.send_message(chat_id, f"❌ خطای FFmpeg رخ داد: \n`{error_details}`")
        except Exception as e:
            await app.send_message(chat_id, f"❌ یک خطای غیرمنتظره رخ داد: دانلود یا پردازش با مشکل مواجه شد. `{e}`")
        finally:
            if downloaded_file_path and os.path.exists(downloaded_file_path):
                os.remove(downloaded_file_path)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
            if user_id in user_state:
                del user_state[user_id]
    
    # <<< مدیریت برش صدا (فراخوانی از فایل جداگانه) >>>
    elif callback_query.data == "cut_audio_now":
        await cut_audio_action(client, callback_query)


@app.on_message(filters.video)
async def handle_video(_, message):
    """دریافت ویدیو و ذخیره وضعیت."""
    user_id = message.from_user.id
    
    if user_id not in user_state or user_state[user_id].get("step") != "awaiting_video":
        return

    if "prompt_msg_id" in user_state[user_id]:
        try:
            await app.delete_messages(message.chat.id, user_state[user_id]["prompt_msg_id"])
        except Exception:
            pass

    # این بخش مدت زمان کلی ویدیو را نمایش می‌دهد و تحت تأثیر قرار نگرفته است
    duration = seconds_to_hms(message.video.duration)

    text = (
        f"⏱ زمان ویدیو: {duration}\n"
        f"⏳ تایم شروع: ...\n"
        f"⏳ تایم پایان: ..."
    )
    sent_msg = await message.reply(text)
    
    user_state[user_id].update({
        "step": "awaiting_start",
        "media_type": "video",
        "video_msg_id": message.id,
        "media_edit_msg": sent_msg.id,
        "duration": duration,
        "start_time": None,
        "end_time": None
    })

    prompt_msg = await message.reply("لطفاً تایم شروع را ارسال کنید (hh:mm:ss)")
    user_state[user_id]["prompt_msg_id"] = prompt_msg.id


@app.on_message(filters.text)
async def handle_time(_, message):
    """دریافت زمان شروع و پایان و به‌روزرسانی پیام اصلی."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    state = user_state.get(user_id)

    if not state or state.get("step") not in ["awaiting_start", "awaiting_end"]:
        return

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
    
    media_type = state.get("media_type", "video") 
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
        await video_msg.edit_text(new_text, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("شروع برش", callback_data=callback_data)]]
        ))

# ===============================================
# --- ثبت هندلرها و شروع برنامه اصلی ---
# ===============================================

app.add_handler(MessageHandler(handle_audio_file, filters.audio))


if __name__ == "__main__":
    # 1. سرور Health Check را در یک Thread جداگانه شروع می‌کنیم.
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True
    health_thread.start()

    # 2. ربات Pyrogram را شروع می‌کنیم.
    print("🚀 Bot starting...")
    app.run()
