import os
import time
import aiohttp
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from tqdm import tqdm

# دانلود فایل به‌صورت استریم
async def download_file(client: Client, message: Message, url: str, filename: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                total_size = int(response.headers['Content-Length'])
                with open(filename, 'wb') as f:
                    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)
                    downloaded = 0
                    async for chunk in response.content.iter_any():
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress_bar.update(len(chunk))
                        progress_bar.set_postfix(speed=f"{downloaded / (time.time() - start_time):.2f} B/s")
                    progress_bar.close()
    except Exception as e:
        print(f"Error downloading file: {e}")

# آپلود فایل به کانال لاگ
async def upload_file_to_channel(client: Client, message: Message, filename: str, log_channel: str):
    try:
        with open(filename, 'rb') as f:
            file = await client.send_document(log_channel, f)
            return file
    except Exception as e:
        print(f"Error uploading file: {e}")

# حذف فایل از سرور بعد از اتمام
async def delete_file(filename: str):
    if os.path.exists(filename):
        os.remove(filename)
        print(f"File {filename} deleted from server.")
