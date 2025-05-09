from pyrogram import Client, filters
from pyrogram.types import Message
import cv2
import face_recognition
import numpy as np
import os

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAHoidc0x6nM3g2JHmb7xhWKmwGJOoKFNXY'
LOG_CHANNEL = -1001792962793  # مقدار دلخواه

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ذخیره عکس‌ها به صورت موقت
user_photos = {}

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_photos[message.from_user.id] = {"face": None, "target": None}
    await message.reply("سلام! لطفاً ابتدا یک عکس از چهره خود ارسال کنید.")

@app.on_message(filters.photo)
async def handle_photo(client, message: Message):
    user_id = message.from_user.id

    if user_id not in user_photos:
        await message.reply("لطفاً ابتدا دستور /start را ارسال کنید.")
        return

    photo_path = await message.download()
    
    if user_photos[user_id]["face"] is None:
        user_photos[user_id]["face"] = photo_path
        await message.reply("عکس چهره دریافت شد. حالا عکسی را بفرستید که می‌خواهید چهره روی آن قرار بگیرد.")
    else:
        user_photos[user_id]["target"] = photo_path
        await message.reply("در حال انجام Face Swap...")
        swapped = do_face_swap(user_photos[user_id]["face"], user_photos[user_id]["target"])
        if swapped is None:
            await message.reply("متأسفانه چهره‌ها شناسایی نشدند.")
        else:
            swapped_path = f"swapped_{user_id}.jpg"
            cv2.imwrite(swapped_path, swapped)
            await message.reply_photo(swapped_path)
            os.remove(swapped_path)
        
        # پاک کردن داده‌ها
        os.remove(user_photos[user_id]["face"])
        os.remove(user_photos[user_id]["target"])
        del user_photos[user_id]

def do_face_swap(face_path, target_path):
    try:
        face_img = face_recognition.load_image_file(face_path)
        target_img = face_recognition.load_image_file(target_path)

        face_locations = face_recognition.face_locations(face_img)
        target_locations = face_recognition.face_locations(target_img)

        if not face_locations or not target_locations:
            return None

        face_encoding = face_recognition.face_encodings(face_img, face_locations)[0]
        face_crop = face_img[face_locations[0][0]:face_locations[0][2], face_locations[0][3]:face_locations[0][1]]

        top, right, bottom, left = target_locations[0]
        height, width, _ = face_crop.shape
        face_resized = cv2.resize(face_crop, (right - left, bottom - top))

        target_img_cv = cv2.cvtColor(target_img, cv2.COLOR_RGB2BGR)
        target_img_cv[top:bottom, left:right] = face_resized

        return target_img_cv
    except Exception as e:
        print("خطا:", e)
        return None

app.run()
