# config.py

import os
from pyrogram import Client
from datetime import timedelta

# --- تنظیمات (Configuration) ---
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '8189638115:AAEYMDvummCXAPgdpavZbYHa3YuXpOzkRBY'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه

# --- متغیرهای مشترک ---
app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_state = {}

def seconds_to_hms(seconds):
    """تبدیل ثانیه به فرمت زمان (hh:mm:ss)."""
    return str(timedelta(seconds=seconds))
