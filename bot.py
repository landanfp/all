import os
import time
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import Message
import humanize
import asyncio

# Bot configuration with optimized settings
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '7136875110:AAGr1EREy_qPMgxVbuE4B0cHGVcwWudOrus'
#LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
   # max_concurrent_transmissions=20,  # Increase concurrent transmissions
    #download_chunk_size=1048576,  # 1MB chunks for faster download
    #upload_chunk_size=1048576  # 1MB chunks for faster upload
)

# Function to add watermarks to video using ffmpeg
async def add_watermarks_to_video(video_path, output_path):
    try:
        # Ensure watermark images exist
        if not os.path.exists("1.jpg") or not os.path.exists("2.jpg"):
            return False

        # Input video stream
        video = ffmpeg.input(video_path)

        # Watermark 1: Top-right, 30px width
        watermark1 = ffmpeg.input("1.jpg").filter("scale", 30, -1)  # Scale to 30px width
        # Watermark 2: Bottom-center
        watermark2 = ffmpeg.input("2.jpg").filter("scale", -1, -1)  # Keep original size or adjust as needed

        # Get video dimensions
        probe = ffmpeg.probe(video_path)
        video_width = int(probe['streams'][0]['width'])
        video_height = int(probe['streams'][0]['height'])

        # Overlay watermark1 at top-right (10px padding from edges)
        video = ffmpeg.overlay(video, watermark1, x=video_width-40, y=10)

        # Overlay watermark2 at bottom-center
        video = ffmpeg.overlay(video, watermark2, x=(video_width-ffmpeg.probe("2.jpg")['streams'][0]['width'])//2, y=video_height-ffmpeg.probe("2.jpg")['streams'][0]['height']-10)

        # Output the video with watermarks (fast encoding with lower quality for speed)
        ffmpeg.output(video, output_path, c='copy', vcodec='libx264', preset='ultrafast', crf=28, acodec='aac').run(overwrite_output=True)
        return True
    except Exception as e:
        print(f"Error in watermarking: {e}")
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
    # Update progress only every 3 seconds to reduce overhead
    if current_time - last_update < 3:
        return
    last_update = current_time

    elapsed = current_time - start_time
    speed = current / elapsed if elapsed > 0 else 0
    downloaded = humanize.naturalsize(current)
    total_size = humanize.naturalsize(total)
    bar = progress_bar(current, total)
    text = f"Downloading: {downloaded}/{total_size} | Speed: {humanize.naturalsize(speed)}/s\n{bar}"
    try:
        await message.edit_text(text)
    except:
        pass

# Upload progress callback
async def upload_progress(current, total, message):
    global last_update
    current_time = time.time()
    # Update progress only every 3 seconds
    if current_time - last_update < 3:
        return
    last_update = current_time

    bar = progress_bar(current, total)
    text = f"Uploading:\n{bar}"
    try:
        await message.edit_text(text)
    except:
        pass

# Start command handler
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply_text("Hello! I'm a video watermarking bot. Send me a video, and I'll download it, add watermarks (1.jpg at top-right, 2.jpg at bottom-center), and upload it back.")

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
        await message.download(
            file_name=video_path,
            progress=download_progress,
            progress_args=(status_message, start_time)
        )
    except Exception as e:
        await status_message.edit_text(f"Download failed: {e}")
        return

    await status_message.edit_text("Download complete. Adding watermarks...")
    
    # Add watermarks
    output_path = f"downloads/{message.video.file_id}_watermarked.mp4"
    if not await add_watermarks_to_video(video_path, output_path):
        await status_message.edit_text("Failed to add watermarks.")
        return

    await status_message.edit_text("Watermarking complete. Starting upload...")
    
    # Upload video
    try:
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            progress=upload_progress,
            progress_args=(status_message,)
        )
        await status_message.edit_text("Upload complete!")
    except Exception as e:
        await status_message.edit_text(f"Upload failed: {e}")
    finally:
        # Clean up
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# Run the bot
app.run()
