from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.cutvid import setup_handlers  # تغییر به cutvid

گ
app = Client(
    "media_cutter_bot",
    api_id=3335796,  # جایگزین کن با API ID واقعی
    api_hash="138b992a0e672e8346d8439c3f42ea78",  # جایگزین کن با API Hash واقعی
    bot_token="7136875110:AAFzyr2i2FbRrmst1sklkJPN7Yz2rXJvSew",  # جایگزین کن با Bot Token واقعی
    plugins=dict(root="plugins")  # لود اتوماتیک از پوشه plugins
)

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
