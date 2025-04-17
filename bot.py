from pyrogram import Client, filters
import subprocess
import os
import time

# وارد کردن مقادیر api_id، api_hash و bot_token
api_id = '3335796'  # جایگزین با api_id شما
api_hash = '138b992a0e672e8346d8439c3f42ea78'  # جایگزین با api_hash شما
bot_token = '7136875110:AAFzyr2i2FbRrmst1sklkJPN7Yz2rXJvSew'  # جایگزین با bot_token شما
# جایگزین با bot_token واقعی شما

app = Client("watermark_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# مسیر ذخیره موقت ویدیو
TEMP_PATH = "./temp_video.mp4"

@app.on_message(filters.video)
async def add_watermark(client, message):
    file = message.video.file_id
    file_name = "watermarked_video.mp4"
    download_path = os.path.join(TEMP_PATH, file_name)

    # دانلود ویدیو
    start_time = time.time()
    await message.download(download_path)

    # دریافت ابعاد ویدیو برای تنظیم سایز فونت
    ffprobe_command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'default=noprint_wrappers=1', download_path
    ]
    probe_result = subprocess.run(ffprobe_command, capture_output=True, text=True)

    # استخراج width و height از خروجی
    result_lines = probe_result.stdout.split('\n')
    width = int(result_lines[0].split('=')[1])  # استخراج عدد width
    height = int(result_lines[1].split('=')[1])  # استخراج عدد height

    # تعیین اندازه فونت بر اساس 50% از عرض ویدیو
    font_size = int(width * 0.1)  # سایز فونت معادل 10% از عرض ویدیو

    # افزودن واترمارک به ویدیو با FFmpeg
    watermark_text = "@SeriesPlus1"
    ffmpeg_command = [
        'ffmpeg', '-i', download_path, '-vf', f"drawtext=text='{watermark_text}':x='if(gte(t\,5)\,W+tw\,0)':y=H-th-10:fontsize={font_size}:fontcolor=white:alpha=0.8", 
        '-c:a', 'copy', 'output_video.mp4'
    ]
    subprocess.run(ffmpeg_command)

    # زمان گذشته برای نمایش در پیشرفت
    elapsed_time = time.time() - start_time

    # نمایش پیشرفت
    await message.reply_text(f"ویدیو با موفقیت واترمارک شد! زمان پردازش: {elapsed_time:.2f} ثانیه")

    # ارسال ویدیو به کاربر
    with open("output_video.mp4", "rb") as f:
        await message.reply_video(f, caption="ویدیو با واترمارک")

    # حذف فایل‌های موقت بعد از ارسال
    os.remove(download_path)
    os.remove("output_video.mp4")

app.run()
