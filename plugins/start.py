from pyrogram import Client, filters

@Client.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("سلام! ویدیوت رو بفرست و زیرنویس .srt رو هم بفرست تا بچسبونم.")