# bot.py (فقط بخش‌های کلیدی تغییر یافته‌اند)

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import ffmpeg
# --- واردات جدید برای رفع خطای Health Check و MessageHandler ---
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from pyrogram.handlers import MessageHandler # برای ثبت صحیح هندلر صدا

# <<< ایمپورت از config.py >>>
from config import API_ID, API_HASH, BOT_TOKEN, app, user_state, seconds_to_hms 
from audio_trimmer import handle_audio_file, cut_audio_action 

# ... (بخش Health Check بدون تغییر)

# @app.on_callback_query()
async def handle_callback(client, callback_query):
    # ... (کد قبلی)
    
    # <<< مدیریت دکمه جدید برش صدا >>>
    elif callback_query.data == "start_audio_cutting":
        user_state[user_id] = {
            "step": "awaiting_audio",
            "media_type": "audio" 
        }
        # <<< پیام پرامپت به‌روزرسانی شد >>>
        prompt_msg = await callback_query.message.reply("لطفاً فایل صوتی موردنظر را ارسال کنید (مانند MP3 یا M4A).")
        user_state[user_id]["prompt_msg_id"] = prompt_msg.id
        await callback_query.answer()
    
    # ... (بقیه کد callback_query)


# ... (بخش handle_video و handle_time بدون تغییر)


# <<< ثبت هندلر فایل صوتی >>>
# این خط، تابع handle_audio_file از audio_trimmer.py را برای فیلتر filters.audio فعال می‌کند.
app.add_handler(MessageHandler(handle_audio_file, filters.audio))


# ... (بخش if __name__ == "__main__": بدون تغییر)
