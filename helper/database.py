import time
import math

async def progress_for_pyrogram(current, total, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 5) == 0:  # فقط هر 5 ثانیه بروزرسانی کنه
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff)
        time_to_completion = round((total - current) / speed) if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        bar_length = 20
        filled_length = int(bar_length * current // total)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        speed_mb = speed / (1024 * 1024)

        text = f"""
⬇️ **در حال پردازش...**

`[{bar}]` **{percentage:.2f}%**

**حجم دانلود شده:** {current_mb:.2f} MB
**حجم کل:** {total_mb:.2f} MB
**سرعت:** {speed_mb:.2f} MB/s
**زمان باقی‌مانده:** {time_to_completion} ثانیه
        """

        try:
            await message.edit(text)
        except:
            pass
