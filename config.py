# config.py

import os
from pyrogram import Client
from datetime import timedelta

# --- تنظیمات (Configuration) ---
# NOTE: امنیت! توکن و هش شما در حالت عمومی قرار گرفته است. 
# برای محیط‌های واقعی، از متغیرهای محیطی (os.environ) استفاده کنید.
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '8189638115:AAEYMDvummCXAPgdpavZbYHa3YuXpOzkRBY'
#LOG_CHANNEL = -1001792962793 

# --- متغیرهای مشترک ---
app = Client("trim_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_state = {}

def seconds_to_hms(seconds):
    """تبدیل ثانیه به فرمت زمان (hh:mm:ss)."""
    # اطمینان از اینکه ثانیه‌ها منفی نیستند
    if seconds < 0:
        return "00:00:00"
    
    # استفاده از str(timedelta) برای سادگی
    # اگر زمان بیشتر از 24 ساعت باشد، ساعت را به درستی نمایش می‌دهد
    hms = str(timedelta(seconds=seconds))
    if seconds < 3600:
        # اگر کمتر از 1 ساعت باشد، "H:MM:SS" را به "0:MM:SS" یا "MM:SS" تبدیل می‌کند، 
        # لذا اطمینان حاصل می‌کنیم که حداقل "00:" اول را داشته باشد.
        parts = hms.split(':')
        if len(parts) == 3:
            # hh:mm:ss
            return hms
        elif len(parts) == 2:
            # mm:ss
            return f"0:{hms}"
        else:
            # s.ms
            return f"0:00:{float(seconds):.2f}"
    
    return hms
