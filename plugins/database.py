import os
import math
import time
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

# تابع دانلود فایل
async def download_file_stream(client: Client, file_id: str, user_id: int, message: Message):
    file_path = f"{user_id}_original.mp4"
    start = time.time()

    async def progress(current, total):
        # فراخوانی تابع برای نمایش پیشرفت دانلود
        await progress_for_pyrogram(current, total, "در حال دانلود", message, start)

    # دانلود فایل با استفاده از Pyrogram
    file = await client.download_media(file_id, file_name=file_path, progress=progress)
    return file

# تابع نمایش پیشرفت دانلود
async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start

    # فقط هر 10 ثانیه یا زمانی که دانلود تمام شده باشد، بروزرسانی می‌شود
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        # فرمت کردن زمان به شکل خوانا
        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        # ساخت پروگرس بار برای نمایش
        progress = "[{0}{1}] \n**📊 درصد انجام شده : {2}% **\n".format(
            ''.join(["**▓**" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))

        tmp = progress + "**✅ میزان حجم دانلود شده : {0} \n📀 حجم فایل : {1}\n🚀 سرعت : {2}/s\n⌚ تایم : {3} **\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )

        # دکمه متوقف کردن دانلود
        cancel_button = InlineKeyboardButton("✖️ متوقف کردن ✖️", callback_data="cancel")

        try:
            # بروزرسانی پیام با اطلاعات جدید
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",
                reply_markup=InlineKeyboardMarkup([[cancel_button]])
            )
        except Exception:
            pass

# تابع تبدیل بایت به فرمت خوانا
def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

# تابع فرمت کردن زمان
def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]
