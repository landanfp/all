from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# اطلاعات رباتت رو وارد کن
api_id = "3335796"  # جایگزین کنید با api_id خود
api_hash = "138b992a0e672e8346d8439c3f42ea78"  # جایگزین کنید با api_hash خود
bot_token = "7136875110:AAFzyr2i2FbRrmst1sklkJPN7Yz2rXJvSew"  # جایگزین کنید با bot_token خود

app = Client("media_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "سلام! به ربات خوش اومدی.\nبرای شروع استفاده از ربات، دکمه زیر رو بزن:",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("شروع", callback_data="start_using_bot")]
            ]
        )
    )

@app.on_callback_query()
async def handle_callback(client, callback_query):
    if callback_query.data == "start_using_bot":
        await callback_query.message.edit_text("استفاده از ربات آغاز شد!")

app.run()
