from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
#from plugins import video_cut, audio_cut  

app = Client(
    "media_cutter_bot",
    api_id=3335796,  # جایگزین کن با API ID واقعی
    api_hash="138b992a0e672e8346d8439c3f42ea78",  # جایگزین کن با API Hash واقعی
    bot_token="6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8",  # جایگزین کن با Bot Token واقعی
    plugins=dict(root="plugins")  # لود اتوماتیک از پوشه plugins
)

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
