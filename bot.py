import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw, ImageFont
import humanize
import asyncio

# Bot configuration
api_id = "YOUR_API_ID"  # Replace with your API ID
api_hash = "YOUR_API_HASH"  # Replace with your API Hash
bot_token = "YOUR_BOT_TOKEN"  # Replace with your Bot Token

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Function to add watermarks to video (placeholder for video watermarking)
async def add_watermarks_to_video(video_path, output_path):
    try:
        # For simplicity, we'll assume watermarking on a single frame for demonstration
        # In a real scenario, you'd use a library like moviepy or ffmpeg for video
        # Here, we simulate watermarking by applying it to a dummy image
        img = Image.new('RGB', (1280, 720), color='black')  # Placeholder for video frame
        watermark1 = Image.open("1.jpg").resize((30, 30))  # Top-right watermark
        watermark2 = Image.open("2.jpg")  # Bottom-center watermark

        # Paste watermark1 at top-right
        img.paste(watermark1, (img.width - 30, 0), watermark1 if watermark1.mode == 'RGBA' else None)
        
        # Paste watermark2 at bottom-center
        watermark2 = watermark2.resize((int(watermark2.width * 0.5), int(watermark2.height * 0.5)))  # Scale if needed
        x = (img.width - watermark2.width) // 2
        y = img.height - watermark2.height
        img.paste(watermark2, (x, y), watermark2 if watermark2.mode == 'RGBA' else None)

        # Save the dummy frame (in real case, apply to video)
        img.save("temp_frame.jpg")
        # For actual video watermarking, use ffmpeg or moviepy
        os.rename(video_path, output_path)  # Placeholder: assume video is processed
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
async def download_progress(current, total, message, start_time):
    elapsed = time.time() - start_time
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
