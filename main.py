from pyrogram import Client
from plugins import start, hardsub, upload

app = Client(
    "hardsub_bot",
    api_id=int(os.environ.get("API_ID")),
    api_hash=os.environ.get("API_HASH"),
    bot_token=os.environ.get("BOT_TOKEN")
)

app.run()