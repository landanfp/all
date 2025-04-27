from pyrogram import Client
from plugins import start, hardsub, upload

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6975247999:AAEaK2CYU4FpgZ8ruW8ZxzXfGQ9dsXuepuw'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه


app = Client(
    "hardsub_bot",
    api_id=int(os.environ.get("API_ID")),
    api_hash=os.environ.get("API_HASH"),
    bot_token=os.environ.get("BOT_TOKEN")
)

app.run()
