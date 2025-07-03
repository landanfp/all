import os
import time
import logging
#import cv2
import numpy as np
from PIL import Image
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from humanfriendly import format_size
import motor.motor_asyncio
import aiofiles
import aiohttp
import dns.resolver
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB setup with provided URI
mongo_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://abirhasan2005:abirhasan@cluster0.i6qzp.mongodb.net/cluster0?retryWrites=true&w=majority")
db = mongo_client["telegram_bot"]
log_collection = db["logs"]

# Bot configuration with optimized settings
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '7136875110:AAGr1EREy_qPMgxVbuE4B0cHGVcwWudOrus'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client(
    "my_bot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token,
    max_concurrent_transmissions=100,  # Max concurrent connections
    #download_chunk_size=4194304,  # 4MB chunks
    upload_chunk_size=4194304,  # 4MB chunks
    workers=100  # Max workers for parallel processing
)

# Function to resolve faster Telegram server using dnspython
async def resolve_fastest_dc():
    try:
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve("api.telegram.org", "A")
        fastest_ip = min(answers, key=lambda x: x.time).address
        logger.info(f"Fastest Telegram DC IP: {fastest_ip}")
        return fastest_ip
    except Exception as e:
        logger.error(f"DNS resolution failed: {e}")
        return None

# Function to test network speed using aiohttp
async def test_network_speed():
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.get("http://speedtest.ftp.otenet.gr/files/test100k.db") as response:
                data = await response.read()
                elapsed = time.time() - start_time
                speed = len(data) / elapsed
                logger.info(f"Network speed: {format_size(speed)}/s")
                return speed
    except Exception as e:
        logger.error(f"Network speed test failed: {e}")
        return 0

# Function to monitor system resources using psutil
async def check_resources():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    logger.info(f"CPU Usage: {cpu_usage}% | Memory: {format_size(memory.used)}/{format_size(memory.total)} | Disk: {format_size(disk.used)}/{format_size(disk.total)}")
    return cpu_usage < 80 and memory.percent < 80 and disk.percent < 80

# Function to get video metadata using hachoir
async def get_video_metadata(video_path):
    try:
        parser = createParser(video_path)
        if not parser:
            return None
        metadata = extractMetadata(parser)
        if not metadata:
            return None
        meta_dict = {item.key: item.values[0].value for item in metadata}
        parser.close()
        logger.info(f"Video metadata: {meta_dict}")
        return meta_dict
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return None

# Function to add watermarks using Pillow and OpenCV
async def add_watermarks_to_video(video_path, output_path):
    try:
        logger.info("Starting watermark process")
        start_time = time.time()
        # Ensure watermark images exist
        if not os.path.exists("1.jpg") or not os.path.exists("2.jpg"):
            logger.error("Watermark images not found")
            return False

        # Load watermarks with Pillow
        async with aiofiles.open("1.jpg", mode='rb') as f:
            watermark1 = Image.open(f)
            watermark1 = watermark1.resize((30, int(30 * watermark1.height / watermark1.width)))
        async with aiofiles.open("2.jpg", mode='rb') as f:
            watermark2 = Image.open(f)

        # Convert Pillow images to OpenCV format
        watermark1_cv = cv2.cvtColor(np.array(watermark1), cv2.COLOR_RGB2BGR)
        watermark2_cv = cv2.cvtColor(np.array(watermark2), cv2.COLOR_RGB2BGR)

        # Open video with OpenCV
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Failedto open video")
            return False

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        fourcc = cv2.VideoWriter_fourcc(*'X264')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # Process frames
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Add watermark1 (top-right, 10px padding)
            wm1_h, wm1_w = watermark1_cv.shape[:2]
            if watermark1.mode == 'RGBA':
                alpha = np.array(watermark1)[:, :, 3] / 255.0
                for c in range(0, 3):
                    frame[10:10+wm1_h, width-40:width-40+wm1_w, c] = \
                        frame[10:10+wm1_h, width-40:width-40+wm1_w, c] * (1 - alpha) + \
                        watermark1_cv[:, :, c] * alpha
            else:
                frame[10:10+wm1_h, width-40:width-40+wm1_w] = watermark1_cv

            # Add watermark2 (bottom-center)
            wm2_h, wm2_w = watermark2_cv.shape[:2]
            x = (width - wm2_w) // 2
            y = height - wm2_h - 10
            if watermark2.mode == 'RGBA':
                alpha = np.array(watermark2)[:, :, 3] / 255.0
                for c in range(0, 3):
                    frame[y:y+wm2_h, x:x+wm2_w, c] = \
                        frame[y:y+wm2_h, x:x+wm2_w, c] * (1 - alpha) + \
                        watermark2_cv[:, :, c] * alpha
            else:
                frame[y:y+wm2_h, x:x+wm2_w] = watermark2_cv

            out.write(frame)

        cap.release()
        out.release()
        logger.info(f"Watermarking completed in {time.time() - start_time:.2f} seconds")
        # Log to MongoDB
        await log_collection.insert_one({"action": "watermark", "video_path": video_path, "duration": time.time() - start_time})
        return True
    except Exception as e:
        logger.error(f"Error in watermarking: {e}")
        return False

# Progress bar generator
def progress_bar(current, total):
    percentage = (current / total) * 100
    bar_length = 20
    filled = int(bar_length * percentage // 100)
    bar = '█' * filled + '-' * (bar_length - filled)
    return f"[{bar}] {percentage:.1f}%"

# Download progress callback
last_update = 0
async def download_progress(current, total, message, start_time):
    global last_update
    current_time = time.time()
    # Update progress only every 5 seconds to reduce overhead
    if current_time - last_update < 5:
        return
    last_update = current_time

    elapsed = current_time - start_time
    speed = current / elapsed if elapsed > 0 else 0
    downloaded = format_size(current)
    total_size = format_size(total)
    bar = progress_bar(current, total)
    text = f"Downloading: {downloaded}/{total_size} | Speed: {format_size(speed)}/s\n{bar}"
    try:
        await message.edit_text(text)
        logger.info(f"Download progress: {downloaded}/{total_size}, Speed: {format_size(speed)}/s")
        await log_collection.insert_one({"action": "download_progress", "current": current, "total": total, "speed": speed})
    except:
        pass

# Upload progress callback
async def upload_progress(current, total, message):
    global last_update
    current_time = time.time()
    # Update progress only every 5 seconds
    if current_time - last_update < 5:
        return
    last_update = current_time

    bar = progress_bar(current, total)
    text = f"Uploading:\n{bar}"
    try:
        await message.edit_text(text)
        logger.info(f"Upload progress: {format_size(current)}/{format_size(total)}")
        await log_collection.insert_one({"action": "upload_progress", "current": current, "total": total})
    except:
        pass

# Start command handler
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    # Check resources
    if not await check_resources():
        await message.reply_text("Server resources are overloaded. Please try again later.")
        return
    # Test network speed
    speed = await test_network_speed()
    await message.reply_text(f"Hello! I'm a video watermarking bot. Network speed: {format_size(speed)}/s. Send me a video, and I'll add watermarks (1.jpg at top-right, 2.jpg at bottom-center).")

# Video handler
@app.on_message(filters.video)
async def handle_video(client, message: Message):
    global last_update
    last_update = time.time()
    status_message = await message.reply_text("Starting download...")
    start_time = time.time()
    
    # Download video
    video_path = f"downloads/{message.video.file_id}.mp4"
    os.makedirs("downloads", exist_ok=True)
    try:
        logger.info("Starting video download")
        async with aiofiles.open(video_path, mode='wb') as f:
            await message.download(
                file_name=video_path,
                progress=download_progress,
                progress_args=(status_message, start_time)
            )
        logger.info(f"Download completed in {time.time() - start_time:.2f} seconds")
        await log_collection.insert_one({"action": "download", "video_path": video_path, "duration": time.time() - start_time})
    except Exception as e:
        logger.error(f"Download failed: {e}")
        await status_message.edit_text(f"Download failed: {e}")
        return

    # Get metadata
    metadata = await get_video_metadata(video_path)
    if metadata:
        await status_message.edit_text(f"Download complete. Metadata: {metadata.get('width', 'N/A')}x{metadata.get('height', 'N/A')}. Adding watermarks...")
    else:
        await status_message.edit_text("Download complete. Adding watermarks...")

    # Add watermarks
    output_path = f"downloads/{message.video.file_id}_watermarked.mp4"
    if not await add_watermarks_to_video(video_path, output_path):
        await status_message.edit_text("Failed to add watermarks.")
        return

    await status_message.edit_text("Watermarking complete. Starting upload...")
    
    # Upload video
    try:
        logger.info("Starting video upload")
        upload_start = time.time()
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            progress=upload_progress,
            progress_args=(status_message,)
        )
        logger.info(f"Upload completed in {time.time() - upload_start:.2f} seconds")
        await log_collection.insert_one({"action": "upload", "video_path": output_path, "duration": time.time() - upload_start})
        await status_message.edit_text("Upload complete!")
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        await status_message.edit_text(f"Upload failed: {e}")
    finally:
        # Clean up
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# Run the bot
if __name__ == "__main__":
    asyncio.run(resolve_fastest_dc())  # Resolve fastest Telegram DC
    app.run()
