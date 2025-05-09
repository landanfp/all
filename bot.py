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
    await message.reply("سلام! لطفاً ابتدا یک عکس واضح از چهره خود ارسال کنید.")

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
        await message.reply("در حال انجام Face Swap پیشرفته...")
        swapped_path = await do_advanced_face_swap(user_id, user_photos[user_id]["face"], user_photos[user_id]["target"])
        if swapped_path is None:
            await message.reply("متأسفانه چهره‌ها شناسایی نشدند یا در پردازش مشکلی رخ داد.")
        else:
            await message.reply_photo(swapped_path)
            os.remove(swapped_path)

        # پاک کردن داده‌ها
        os.remove(user_photos[user_id]["face"])
        os.remove(user_photos[user_id]["target"])
        del user_photos[user_id]

async def do_advanced_face_swap(user_id, face_path, target_path):
    try:
        face_img = cv2.imread(face_path)
        target_img = cv2.imread(target_path)
        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        target_img_rgb = cv2.cvtColor(target_img, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(face_img_rgb)
        target_locations = face_recognition.face_locations(target_img_rgb)

        if not face_locations or not target_locations:
            return None

        face_landmarks = face_recognition.face_landmarks(face_img_rgb, face_locations)[0]
        target_landmarks = face_recognition.face_landmarks(target_img_rgb, target_locations)[0]

        # 1. هم‌تراز کردن ساده بر اساس چشم‌ها
        face_eye_left = np.mean(face_landmarks['left_eye'], axis=0, dtype=np.int32)
        face_eye_right = np.mean(face_landmarks['right_eye'], axis=0, dtype=np.int32)
        target_eye_left = np.mean(target_landmarks['left_eye'], axis=0, dtype=np.int32)
        target_eye_right = np.mean(target_landmarks['right_eye'], axis=0, dtype=np.int32)

        def transformation_matrix(eye_center_src, eye_center_dst, scale=1.0):
            dx_src = eye_center_right[0] - eye_center_src[0]
            dy_src = eye_center_right[1] - eye_center_src[1]
            dist_src = np.sqrt(dx_src**2 + dy_src**2)
            angle_src = np.arctan2(dy_src, dx_src)

            dx_dst = eye_center_right[0] - eye_center_dst[0]
            dy_dst = eye_center_right[1] - eye_center_dst[1]
            dist_dst = np.sqrt(dx_dst**2 + dy_dst**2)
            angle_dst = np.arctan2(dy_dst, dx_dst)

            scale_factor = dist_dst / dist_src
            rotation = angle_dst - angle_src

            center_src = ((eye_center_src[0] + eye_center_right[0]) // 2,
                           (eye_center_src[1] + eye_center_right[1]) // 2)
            center_dst = ((eye_center_dst[0] + eye_center_right[0]) // 2,
                           (eye_center_dst[1] + eye_center_right[1]) // 2)

            M = cv2.getRotationMatrix2D(center_src, np.degrees(rotation), scale_factor * scale)
            dx = center_dst[0] - center_src[0]
            dy = center_dst[1] - center_src[1]
            M[0, 2] += dx
            M[1, 2] += dy
            return M

        M = transformation_matrix(face_eye_left, target_eye_left)
        aligned_face = cv2.warpAffine(face_img, M, (target_img.shape[1], target_img.shape[0]))
        aligned_face_rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        aligned_face_locations = face_recognition.face_locations(aligned_face_rgb)
        if not aligned_face_locations:
            return None
        aligned_face_landmarks = face_recognition.face_landmarks(aligned_face_rgb, aligned_face_locations)[0]

        # 2. حذف پس‌زمینه تقریبی با ماسک بیضی
        mask = np.zeros(aligned_face.shape[:2], dtype=np.uint8)
        nose_bridge = np.mean(aligned_face_landmarks['nose_bridge'], axis=0, dtype=np.int32)
        chin_points = np.array(aligned_face_landmarks['chin'], dtype=np.int32)
        min_chin = np.min(chin_points[:, 1])
        max_chin = np.max(chin_points[:, 1])
        face_width = int(np.linalg.norm(np.array(aligned_face_landmarks['left_eye'])[0] - np.array(aligned_face_landmarks['right_eye'])[0]) * 2)
        face_height = int(max_chin - np.mean(aligned_face_landmarks['top_lip'], axis=0)[1] * 2)
        center_face = (nose_bridge[0], (nose_bridge[1] + min_chin) // 2)
        axes = (face_width // 2 + 10, face_height // 2 + 20)
        cv2.ellipse(mask, center_face, axes, 0, 0, 360, 255, -1)
        masked_face = cv2.bitwise_and(aligned_face, aligned_face, mask=mask)

        # اضافه کردن کانال آلفا و تنظیم پس زمینه به شفاف
        masked_face_rgba = cv2.cvtColor(masked_face, cv2.COLOR_BGR2BGRA)
        masked_face_rgba[mask == 0] = [0, 0, 0, 0]

        # 3. جایگذاری و تطبیق روشنایی ساده
        target_top, target_right, target_bottom, target_left = target_locations[0]
        face_resized = cv2.resize(masked_face_rgba, (target_right - target_left, target_bottom - target_top))

        target_face_area = target_img[target_top:target_bottom, target_left:target_right].copy()

        # تطبیق روشنایی (بسیار ساده - میانگین)
        face_mean_brightness = np.mean(cv2.cvtColor(face_resized[:, :, :3], cv2.COLOR_BGR2GRAY))
        target_face_mean_brightness = np.mean(cv2.cvtColor(target_face_area, cv2.COLOR_BGR2GRAY))
        brightness_factor = target_face_mean_brightness / (face_mean_brightness + 1e-6)
        adjusted_face = cv2.convertScaleAbs(face_resized[:, :, :3], alpha=brightness_factor, beta=0)
        face_resized_with_adjusted_brightness = np.dstack((adjusted_face, face_resized[:, :, 3]))

        # ترکیب با در نظر گرفتن آلفا
        alpha_face = face_resized_with_adjusted_brightness[:, :, 3] / 255.0
        alpha_target = 1.0 - alpha_face
        blended_face = np.zeros(target_face_area.shape, dtype=np.uint8)
        for c in range(0, 3):
            blended_face[:, :, c] = (alpha_face * face_resized_with_adjusted_brightness[:, :, c] +
                                     alpha_target * target_face_area[:, :, c])

        target_img[target_top:target_bottom, target_left:target_right] = blended_face

        swapped_path = f"swapped_advanced_{user_id}.jpg"
        cv2.imwrite(swapped_path, target_img)
        return swapped_path

    except Exception as e:
        print("خطا در پردازش پیشرفته:", e)
        return None

app.run()
