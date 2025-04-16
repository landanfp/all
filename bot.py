import logging
from pyrogram import Client
from plugins.video_cut import start_command
from plugins.video_to_audio import start_command

API_ID = 'your_api_id'
API_HASH = 'your_api_hash'
BOT_TOKEN = 'your_bot_token'

logging.basicConfig(level=logging.INFO)

app = Client("video_processing_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message()
async def on_message(client, message):
    pass  # Add more functionality as needed

app.run()