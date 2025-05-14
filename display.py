# display.py
import time
import math

# تبدیل حجم
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    try:
        i = int(math.floor(math.log(size_bytes, 1024)))
        if i < 0: i = 0
    except ValueError:
        i = 0
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# نوار پیشرفت
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
        size_text_line = f"• حجم: {convert_size(current_val)} / {convert_size(total_val)}"
    elif display_bytes_current is not None and display_bytes_total is not None and display_bytes_total > 0:
         current_bytes_to_display = min(display_bytes_current, display_bytes_total)
         size_text_line = f"• حجم: {convert_size(current_bytes_to_display)} / {convert_size(display_bytes_total)}"

    if size_text_line:
        lines.append(size_text_line)

    lines.extend([
        f"• سرعت: {convert_size(speed)}/s",
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
