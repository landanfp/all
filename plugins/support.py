from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import app
import asyncio

# اطلاعات ربات
# آیدی عددی ادمین
admin_id = 705518424

# حافظه وضعیت
user_waiting_for_message = set()
user_last_message = {}  # پیام آخر هر کاربر -> پیام ارسالی به ادمین

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def ask_user_to_send_message(client, message):
    user_id = message.from_user.id
    user_waiting_for_message.add(user_id)
    await message.reply_text("لطفاً سوال یا درخواست خود را ارسال کنید.")

# start
@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("پیام به ادمین", callback_data="send_to_admin")]
    ])
    await message.reply_text(
        "سلام! برای ارسال پیام به ادمین، روی دکمه زیر کلیک کنید یا دستور /support را ارسال کنید.",
        reply_markup=keyboard
    )

# دکمه
@app.on_callback_query(filters.regex("send_to_admin"))
async def on_send_to_admin(client, callback_query):
    await ask_user_to_send_message(client, callback_query.message)
    await callback_query.answer()

# دستور support
@app.on_message(filters.command("support"))
async def support_command(client, message):
    await ask_user_to_send_message(client, message)

# ارسال پیام کاربر
@app.on_message(filters.private & ~filters.command(["start", "support"]))
async def forward_to_admin(client, message):
    user_id = message.from_user.id

    if user_id in user_waiting_for_message:
        user_full_name = message.from_user.first_name
        if message.from_user.last_name:
            user_full_name += f" {message.from_user.last_name}"

        caption = (
            f"پیام جدیدی دارید!\n\n"
            f"نام کاربر: {user_full_name}\n"
            f"آیدی عددی: {user_id}\n\n"
        )

        sending_message = await message.reply_text("در حال ارسال •")
        await asyncio.sleep(1)
        await sending_message.edit_text("در حال ارسال ••")
        await asyncio.sleep(1)
        await sending_message.edit_text("در حال ارسال •••")
        await asyncio.sleep(1)

        # ارسال به ادمین با quote
        sent = None
        if message.text:
            sent = await client.send_message(admin_id, caption + "\n" + f"📩 {message.text}", quote_message_id=message.message_id)
        elif message.photo:
            sent = await client.send_photo(admin_id, photo=message.photo.file_id, caption=caption + "(تصویر)", quote_message_id=message.message_id)
        elif message.video:
            sent = await client.send_video(admin_id, video=message.video.file_id, caption=caption + "(ویدیو)", quote_message_id=message.message_id)
        elif message.document:
            sent = await client.send_document(admin_id, document=message.document.file_id, caption=caption + "(فایل)", quote_message_id=message.message_id)
        else:
            sent = await client.send_message(admin_id, caption + "(پیام پشتیبانی نمی‌شود)", quote_message_id=message.message_id)

        if sent:
            # ذخیره اتصال بین پیام ادمین و کاربر
            user_last_message[sent.message_id] = user_id

        await sending_message.edit_text("✅ با موفقیت ارسال شد.")

        # بعد از ارسال، کاربر حذف بشه
        user_waiting_for_message.remove(user_id)

    else:
        # کاربر اجازه نداره بدون support
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("ارسال درخواست جدید", callback_data="send_to_admin")]
        ])
        await message.reply_text(
            "❗ برای ارسال درخواست جدید، دستور /support را بفرستید یا روی دکمه زیر کلیک کنید.",
            reply_markup=keyboard
        )

# پاسخ ادمین
@app.on_message(filters.private & filters.reply & filters.user(admin_id))
async def reply_to_user(client, message):
    replied_msg = message.reply_to_message
    replied_msg_id = replied_msg.message_id

    if replied_msg_id in user_last_message:
        user_id = user_last_message[replied_msg_id]

        if message.text:
            await client.send_message(user_id, f"ادمین به سوال یا درخواست شما پاسخ داد:\n\n{message.text}")
        elif message.photo:
            await client.send_photo(user_id, photo=message.photo.file_id, caption="ادمین به سوال یا درخواست شما پاسخ داد.")
        elif message.video:
            await client.send_video(user_id, video=message.video.file_id, caption="ادمین به سوال یا درخواست شما پاسخ داد.")
        elif message.document:
            await client.send_document(user_id, document=message.document.file_id, caption="ادمین به سوال یا درخواست شما پاسخ داد.")
        else:
            await client.send_message(user_id, "ادمین به سوال یا درخواست شما پاسخ داد.")

        await message.reply(f"✅ پیام با موفقیت به کاربر {user_id} ارسال شد.")

    else:
        await message.reply("❌ ارتباطی با این پیام پیدا نشد.")
        
