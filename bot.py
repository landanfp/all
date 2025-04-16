import logging
from pyrogram import Client
from plugins.video_cut import start_command
from plugins.video_to_audio import start_command

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5088657122:AAHdusGDuWfBpSDWkcX-qU1_fgzij4w8Lzk'

logging.basicConfig(level=logging.INFO)

app = Client("video_processing_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message()
async def on_message(client, message):
    pass  # Add more functionality as needed

app.run()
