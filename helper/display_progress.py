import math
import time
from pyrogram.types import Message


# تبدیل حجم
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

# نوار پیشرفت (اصلاح شده برای دریافت status_message)
async def progress_bar(
    current_val, total_val, status_message, action, start,
    display_bytes_current=None, display_bytes_total=None
):
    now = time.time()
    diff = now - start if now - start > 0 else 0.001
    percentage = current_val * 100 / total_val if total_val > 0 else 0
    speed = current_val / diff if diff > 0 else 0

    elapsed_time = round(diff)
    eta = round((total_val - current_val) / speed) if speed > 0 and total_val > 0 else 0

    if current_val >= total_val and total_val > 0 :
        percentage = 100.00
        eta = 0

    bar_length = 15
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    lines = [
        action,
        f"[{bar}] {percentage:.2f}%"
    ]

    size_text_line = ""
    if (action.startswith("در حال دانلود") or action.startswith("در حال آپلود")) and total_val > 0:
        size_text_line = f"• حجم: {humanbytes(current_val)} / {humanbytes(total_val)}"
    elif display_bytes_current is not None and display_bytes_total is not None and display_bytes_total > 0:
         current_bytes_to_display = min(display_bytes_current, display_bytes_total)
         size_text_line = f"• حجم: {humanbytes(current_bytes_to_display)} / {humanbytes(display_bytes_total)}"

    if size_text_line:
        lines.append(size_text_line)

    lines.extend([
        f"• سرعت: {humanbytes(speed)}/s",
        f"• زمان سپری‌شده: {elapsed_time}s",
        f"• زمان باقی‌مانده: {eta}s"
    ])
    text = "\n".join(lines)

    try:
        if hasattr(status_message, 'text') and status_message.text != text:
            await status_message.edit(text)
        elif not hasattr(status_message, 'text'):
             await status_message.edit(text)
    except Exception:
        pass

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

async def progress_for_pyrogram(current, total, ud_type, message: Message, logs_msg: Message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion
        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \n".format(
            ''.join(["●" for i in range(math.floor(percentage / 5))]),
            ''.join(["○" for i in range(20 - math.floor(percentage / 5))])
            )

        tmp = progress + "در حال {}:\n{} از {}\nسرعت: {}/s\nزمان باقی مانده: {}".format(
            ud_type,
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text="**{}**\n\n {}".format(
                    ud_type,
                    tmp
                ),
                parse_mode='markdown'
            )
        except:
            pass
        try:
            await logs_msg.edit(
                text="**{}**\n\n {}".format(ud_type, tmp)
            )
        except:
            pass
