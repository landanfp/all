import aiohttp
import os
import time
from pyrogram.types import Message
from helper.utils import readable_size, progress_bar

async def stream_download(url: str, path: str, message: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            total_size = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            start_time = time.time()
            last_edit_time = start_time

            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 256):  # 256KB
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_edit_time > 1.5 or downloaded == total_size:
                            percent = downloaded * 100 / total_size
                            speed = downloaded / (now - start_time)
                            eta = (total_size - downloaded) / speed if speed > 0 else 0

                            bar = progress_bar(percent)
                            text = (
                                f"{bar} {percent:.1f}%
"
                                f"حجم انجام شده: {readable_size(downloaded)}
"
                                f"حجم کل فایل: {readable_size(total_size)}
"
                                f"سرعت: {readable_size(speed)}/s
"
                                f"زمان باقی‌مانده: {int(eta)} ثانیه"
                            )
                            await message.edit(text)
                            last_edit_time = now