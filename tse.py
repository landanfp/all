کد فایل bot.py : 
from pyrogram import Client, idle
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
#ایمپورت کردن توابع
from plugins.image_watermark import (

ask_image,

handle_image_upload,

set_image_position,

set_image_size,

process_image_watermark,

)

from plugins.text_watermark import (

ask_text,

handle_text_input,

set_position,

set_size,

handle_video,

)

from plugins.start import start_handler
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

#توکن‌ها و شناسه‌ها (لطفاً این مقادیر را با مقادیر واقعی خود جایگزین کنید)

BOT_TOKEN = '1396293494:AAFY7RXygNEZPFPXfmoJ66SljlXeCSilXG0'
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'

app = Client("watermark_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

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


#جریان شروع و انتخاب

app.add_handler(MessageHandler(start_handler, filters.command("start")))

app.add_handler(CallbackQueryHandler(ask_text, filters.regex("text_wm")))

app.add_handler(CallbackQueryHandler(ask_image, filters.regex("image_wm")))

#جریان واترمارک متنی

app.add_handler(MessageHandler(handle_text_input, filters.text & filters.private))

app.add_handler(CallbackQueryHandler(set_position, filters.regex("^text_pos_")))
app.add_handler(CallbackQueryHandler(set_size, filters.regex("^text_size_")))

#جریان واترمارک تصویری

#فیکس: handler برای photo + handler برای document (بدون mime_type در filter)

app.add_handler(MessageHandler(handle_image_upload, filters.photo & filters.private))
app.add_handler(MessageHandler(handle_image_upload, filters.document & filters.private)) # همه documentها، mime داخل handler چک می‌شه

app.add_handler(CallbackQueryHandler(set_image_position, filters.regex("^image_pos_")))
app.add_handler(CallbackQueryHandler(set_image_size, filters.regex("^image_size_")))

#هندلرهای دریافت ویدیو: آرگومان 'group' به متد add_handler منتقل شد.

app.add_handler(MessageHandler(handle_video, filters.video & filters.private), group=1) # واترمارک متنی

app.add_handler(MessageHandler(process_image_watermark, filters.video & filters.private), group=2) # واترمارک تصویری

if __name__ == "__main__":
    # 1. سرور Health Check را در یک Thread جداگانه شروع می‌کنیم.
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True
    health_thread.start()
print("Bot started. Press Ctrl+C to exit.")

app.run()

کد فایل plugins/text_watermark.py : 
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

  کد فایل plugins/image_watermark.py :
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

# (لیست سایزها از اینجا حذف شد و به تابع set_image_position منتقل شد)

async def ask_image(client, query: CallbackQuery):
    """درخواست تصویر واترمارک."""
    user_id = query.from_user.id
    await query.message.edit("لطفا تصویری برای واترمارک ارسال کنید (فقط jpg یا png):")
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
    """دریافت موقعیت و درخواست سایز. (کد اصلاح شده طبق درخواست شما)"""
    user_id = query.from_user.id
    if get_state(user_id, "step") != "position":
        await query.answer("لطفا مراحل را به ترتیب طی کنید.")
        return

    position = query.data.split("_", 2)[-1]  # فیکس: maxsplit=2
    set_state(user_id, "position", position)
    set_state(user_id, "step", "size")

    # **** تغییر ۱: اضافه کردن 5 به لیست سایزها ****
    sizes = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

    # **** تغییر ۲: اطمینان از چیدمان ۵تایی (چپ به راست) ****
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
    """دریافت ویدیو، پردازش و ارسال خروجی (واترمارک تصویری). (کد اصلاح شده با نوار پیشرفت)"""
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

        # مرحله افزودن واترمارک (پیام قبلی حذف شد)
        # **** تغییر کلیدی: پاس دادن msg ****
        await add_image_watermark(input_path, output_file, image, position, size, msg)

        if not os.path.exists(output_file):
                raise Exception("فایل خروجی FFmpeg تولید نشد. (احتمالاً خطای فایل یا کدک)")

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

  کد فایل plugins/start.py :
# نام فایل: plugins/start.py (هندلر  /start)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

async def start_handler(client, message: Message):
    """هندلر دستور /start."""
    await message.reply(
        "👋 سلام! من یک ربات برای افزودن واترمارک متنی یا تصویری به ویدیوها هستم.\nیکی از گزینه‌های زیر را انتخاب کن تا شروع کنیم:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖋️ واترمارک متنی", callback_data="text_wm")],
            [InlineKeyboardButton("🖼️ واترمارک تصویری", callback_data="image_wm")]
        ])
    )

کد فایل helper/watermark.py :
# نام فایل: helper/watermark.py (منطق اصلی FFmpeg - نسخه پیشرفته با نمایش پیشرفت)
import asyncio
import os
import subprocess
import shlex
import re
import time
from pyrogram.types import Message

# --- توابع کمکی جدید ---

async def get_video_duration(video_path):
    """
    مدت زمان کل ویدیو را با ffprobe به ثانیه برمی‌گرداند.
    """
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{video_path}\""
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0 and stdout:
            return float(stdout.decode().strip())
        else:
            print(f"FFprobe Error: {stderr.decode()}")
            return 0.0
    except Exception as e:
        print(f"Error getting duration: {e}")
        return 0.0

def parse_ffmpeg_time(time_str):
    """
    رشته زمان 'HH:MM:SS.ms' را به ثانیه تبدیل می‌کند.
    """
    parts = time_str.split(':')
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    return (hours * 3600) + (minutes * 60) + seconds

def human_readable_time(seconds):
    """
    ثانیه را به فرمت خوانا (M:SS یا H:MM:SS) تبدیل می‌کند.
    """
    if seconds < 0:
        return "0:00"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

# --- Regex برای پارس کردن خروجی FFmpeg ---
TIME_REGEX = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

# --- توابع اصلی واترمارک (اصلاح شده) ---

async def add_text_watermark(input_path, output_path, text, position, size_percent, msg: Message):
    """
    افزودن واترمارک متنی با نمایش پیشرفت زنده.
    """
    
    # 1. گرفتن مدت زمان کل ویدیو
    total_duration = await get_video_duration(input_path)
    if total_duration == 0.0:
        raise Exception("خطا در خواندن مدت زمان ویدیو. (فایل ورودی خراب است؟)")

    position_map = {
        "top_right": "main_w-text_w-20:20", "top_center": "(main_w-text_w)/2:20", "top_left": "20:20",
        "center_right": "main_w-text_w-20:(main_h-text_h)/2", "center": "(main_w-text_w)/2:(main_h-text_h)/2", "center_left": "20:(main_h-text_h)/2",
        "bottom_right": "main_w-text_w-20:main_h-text_h-20", "bottom_center": "(main_w-text_w)/2:main_h-text_h-20", "bottom_left": "20:main_h-text_h-20"
    }
    safe_text = shlex.quote(text)
    
    drawtext = (
        f"drawtext=text={safe_text}:fontcolor=white@0.8:"
        f"fontsize=h*{size_percent}/100:shadowcolor=black@0.4:shadowx=2:shadowy=2:"
        f"x={position_map[position].split(':')[0]}:y={position_map[position].split(':')[1]}"
    )

    cmd = (
        f"ffmpeg -i \"{input_path}\" -vf \"{drawtext}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "
        f"-map 0:v:0 -map 0:a:0? \"{output_path}\" -y"
    )

    # 2. اجرای FFmpeg با stderr=PIPE تا بتوانیم خروجی را بخوانیم
    process = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stderr=asyncio.subprocess.PIPE
    )

    last_update = 0
    processing_start = time.time()
    error_output = ""

    # 3. حلقه خواندن خروجی FFmpeg
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8').strip()
        error_output += line_str # ذخیره خروجی برای دیباگ در صورت خطا
        
        match = TIME_REGEX.search(line_str)
        if match:
            current_time_str = match.group(1)
            current_time_sec = parse_ffmpeg_time(current_time_str)
            
            # جلوگیری از آپدیت‌های مکرر (هر 3 ثانیه یکبار)
            now = time.time()
            if now - last_update > 3: # (این ۳ ثانیه برای پردازش FFmpeg است، نه دانلود/آپلود)
                percentage = (current_time_sec / total_duration) * 100
                
                # محاسبه زمان باقیمانده (ETA)
                elapsed_time = now - processing_start
                speed_factor = current_time_sec / elapsed_time if elapsed_time > 0 else 0
                remaining_video_time = total_duration - current_time_sec
                eta_seconds = (remaining_video_time / speed_factor) if speed_factor > 0 else 0
                
                # ساخت نوار پیشرفت
                filled_blocks = int(percentage // 10)
                bar = f"[{'█' * filled_blocks}{'░' * (10 - filled_blocks)}]"
                
                # فرمت دلخواه شما
                progress_text = (
                    f"**⚙️ در حال پردازش واترمارک...**\n"
                    f"{percentage:.1f}% {bar}\n"
                    f"مدت زمان باقی تا اتمام: {human_readable_time(eta_seconds)}"
                )
                
                try:
                    await msg.edit(progress_text)
                    last_update = now
                except Exception:
                    pass # نادیده گرفتن خطای ویرایش (مثلا اگر پیام پاک شده باشد)

    await process.wait()

    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {error_output[-500:]}") # نمایش 500 کاراکتر آخر خطا


async def add_image_watermark(input_path, output_path, image_path, position, size_percent, msg: Message):
    """
    افزودن واترمارک تصویری با نمایش پیشرفت زنده.
    """
    
    # 1. گرفتن مدت زمان کل ویدیو
    total_duration = await get_video_duration(input_path)
    if total_duration == 0.0:
        raise Exception("خطا در خواندن مدت زمان ویدیو. (فایل ورودی خراب است؟)")

    position_map = {
        "top_right": "main_w-overlay_w-20:20", "top_center": "(main_w-overlay_w)/2:20", "top_left": "20:20",
        "center_right": "main_w-overlay_w-20:(main_h-overlay_h)/2", "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2", "center_left": "20:(main_h-overlay_h)/2",
        "bottom_right": "main_w-overlay_w-20:main_h-overlay_h-20", "bottom_center": "(main_w-overlay_w)/2:main_h-overlay_h-20", "bottom_left": "20:main_h-overlay_h-20"
    }

    filter_complex = (
        f"[0:v]scale=iw*sar:ih,setsar=1[v];"
        f"[1:v]scale=iw*{size_percent/100}:-1,format=yuva420p[wm];"
        f"[v][wm]overlay={position_map[position]}[ov];"
        f"[ov]format=yuv420p[outv]"
    )

    cmd = (
        f"ffmpeg -noautorotate -i \"{input_path}\" -i \"{image_path}\" "
        f"-filter_complex \"{filter_complex}\" "
        f"-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -vsync 1 "
        f"-profile:v high -level:v 4.0 -g 30 -keyint_min 1 -movflags +faststart "
        f"-map [outv] -map 0:a:0? -metadata:s:v:0 rotate=0 \"{output_path}\" -y"
    )

    # 2. اجرای FFmpeg با stderr=PIPE
    process = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stderr=asyncio.subprocess.PIPE
    )

    last_update = 0
    processing_start = time.time()
    error_output = ""

    # 3. حلقه خواندن خروجی FFmpeg
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8').strip()
        error_output += line_str
        
        match = TIME_REGEX.search(line_str)
        if match:
            current_time_str = match.group(1)
            current_time_sec = parse_ffmpeg_time(current_time_str)
            
            now = time.time()
            if now - last_update > 3: # (این ۳ ثانیه برای پردازش FFmpeg است، نه دانلود/آپلود)
                percentage = (current_time_sec / total_duration) * 100
                
                elapsed_time = now - processing_start
                speed_factor = current_time_sec / elapsed_time if elapsed_time > 0 else 0
                remaining_video_time = total_duration - current_time_sec
                eta_seconds = (remaining_video_time / speed_factor) if speed_factor > 0 else 0
                
                filled_blocks = int(percentage // 10)
                bar = f"[{'█' * filled_blocks}{'░' * (10 - filled_blocks)}]"
                
                progress_text = (
                    f"**⚙️ در حال پردازش واترمارک...**\n"
                    f"{percentage:.1f}% {bar}\n"
                    f"مدت زمان باقی تا اتمام: {human_readable_time(eta_seconds)}"
                )
                
                try:
                    await msg.edit(progress_text)
                    last_update = now
                except Exception:
                    pass

    await process.wait()

    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {error_output[-500:]}")

  کد فایل helper/state.py :
# نام فایل: helper/state.py (مدیریت وضعیت کاربر)
# وضعیت مرحله‌ای کاربران به‌صورت موقت (در یک دیکشنری در حافظه)
user_states = {}

def set_state(user_id, key, value):
    """تنظیم یک وضعیت خاص برای یک کاربر."""
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id][key] = value

def get_state(user_id, key, default=None):
    """دریافت وضعیت خاص یک کاربر."""
    return user_states.get(user_id, {}).get(key, default)

def clear_state(user_id):
    """حذف تمام وضعیت‌های ذخیره شده برای یک کاربر."""
    if user_id in user_states:
        user_states.pop(user_id)

  کد فایل helper/progress.py :
# نام فایل: helper/progress.py (ابزارهای نوار پیشرفت)
import time
from pyrogram.types import Message

# اضافه شدن آرگومان 'stage' برای مدیریت نمایش مراحل مختلف
async def progress_bar(current, total, message: Message, start, stage="در حال پردازش"):
    """آپدیت پیام در حین دانلود/آپلود برای نمایش پیشرفت."""
    now = time.time()
    diff = now - start

    if diff == 0:
        diff = 1

    percentage = current * 100 / total
    speed = current / diff
    eta = (total - current) / speed

    filled_blocks = int(percentage // 10)
    empty_blocks = 10 - filled_blocks
    bar = f"[{'█' * filled_blocks}{'░' * empty_blocks}]"
    
    progress_text = (
        f"**مرحله {stage}**: {bar} **{percentage:.1f}%**\n"
        f"📥/📤 داده: **{human_readable_size(current)}** از **{human_readable_size(total)}**\n"
        f"⚡ سرعت: **{human_readable_size(speed)}/s**\n"
        f"⏱️ زمان تخمینی: **{int(eta)}s**"
    )

    # **** تغییر کلیدی برای افزایش سرعت: ****
    # جلوگیری از Flood Wait: آپدیت هر 8 ثانیه یکبار (به جای 5 ثانیه)
    # این کار تعداد وقفه‌ها برای ادیت پیام را کاهش داده و سرعت انتقال را "کمی" افزایش می‌دهد
    if int(diff) % 8 == 0 or percentage == 100 or percentage == 0:
        try:
            await message.edit(progress_text)
        except Exception:
            pass # نادیده گرفتن خطاهای ویرایش

def human_readable_size(size):
    """تبدیل بایت به واحد‌های خوانا (KB, MB, GB)."""
    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power and n < 3:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"
