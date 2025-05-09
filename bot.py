from pyrogram import Client, filters
from pyrogram.types import Message
import cv2
import face_recognition
import numpy as np
import os
import traceback

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6975247999:AAEaK2CYU4FpgZ8ruW8ZxzXfGQ9dsXuepuw'
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
            await message.reply("متأسفانه در پردازش مشکلی رخ داد. لطفاً از واضح بودن چهره‌ها اطمینان حاصل کنید.")
        else:
            await message.reply_photo(swapped_path)
            if os.path.exists(swapped_path):
                os.remove(swapped_path)

        # پاک کردن داده‌ها
        if os.path.exists(user_photos[user_id]["face"]):
            os.remove(user_photos[user_id]["face"])
        if os.path.exists(user_photos[user_id]["target"]):
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

        print(f"تعداد چهره‌های شناسایی شده در عکس چهره: {len(face_locations)}")
        print(f"تعداد چهره‌های شناسایی شده در عکس هدف: {len(target_locations)}")

        if not face_locations:
            print("خطا: هیچ چهره‌ای در عکس چهره شناسایی نشد.")
            return None
        if not target_locations:
            print("خطا: هیچ چهره‌ای در عکس هدف شناسایی نشد.")
            return None

        face_landmarks_list = face_recognition.face_landmarks(face_img_rgb, face_locations)
        target_landmarks_list = face_recognition.face_landmarks(target_img_rgb, target_locations)

        if not face_landmarks_list:
            print("خطا: نقاط کلیدی صورت در عکس چهره شناسایی نشد.")
            return None
        if not target_landmarks_list:
            print("خطا: نقاط کلیدی صورت در عکس هدف شناسایی نشد.")
            return None

        face_landmarks = face_landmarks_list[0]
        target_landmarks = target_landmarks_list[0]

        # 1. هم‌تراز کردن ساده بر اساس چشم‌ها
        def get_eye_center(landmarks, eye_key):
            if landmarks.get(eye_key):
                return np.mean(landmarks[eye_key], axis=0, dtype=np.int32)
            return None

        face_eye_left = get_eye_center(face_landmarks, 'left_eye')
        face_eye_right = get_eye_center(face_landmarks, 'right_eye')
        target_eye_left = get_eye_center(target_landmarks, 'left_eye')
        target_eye_right = get_eye_center(target_landmarks, 'right_eye')

        def transformation_matrix(eye_center_src, eye_center_dst, eye_center_right_src, eye_center_right_dst, scale=1.0):
            if eye_center_src is None or eye_center_dst is None or eye_center_right_src is None or eye_center_right_dst is None:
                print("خطا: یکی از مراکز چشم برای هم‌تراز سازی در دسترس نیست.")
                return None
            dx_src = eye_center_right_src[0] - eye_center_src[0]
            dy_src = eye_center_right_src[1] - eye_center_src[1]
            dist_src = np.sqrt(dx_src**2 + dy_src**2)
            angle_src = np.arctan2(dy_src, dx_src)

            dx_dst = eye_center_right_dst[0] - eye_center_dst[0]
            dy_dst = eye_center_right_dst[1] - eye_center_dst[1]
            dist_dst = np.sqrt(dx_dst**2 + dy_dst**2)
            angle_dst = np.arctan2(dy_dst, dx_dst)

            scale_factor = dist_dst / dist_src if dist_src > 0 else 1.0
            rotation = angle_dst - angle_src

            center_src = ((eye_center_src[0] + eye_center_right_src[0]) // 2,
                           (eye_center_src[1] + eye_center_right_src[1]) // 2)
            center_dst = ((eye_center_dst[0] + eye_center_right_dst[0]) // 2,
                           (eye_center_dst[1] + eye_center_right_dst[1]) // 2)

            M = cv2.getRotationMatrix2D(center_src, np.degrees(rotation), scale_factor * scale)
            dx = center_dst[0] - center_src[0]
            dy = center_dst[1] - center_src[1]
            M[0, 2] += dx
            M[1, 2] += dy
            return M

        M = transformation_matrix(face_eye_left, target_eye_left, face_eye_right, target_eye_right)
        if M is None:
            return None
        aligned_face = cv2.warpAffine(face_img, M, (target_img.shape[1], target_img.shape[0]))
        aligned_face_rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        aligned_face_locations = face_recognition.face_locations(aligned_face_rgb)
        if not aligned_face_locations:
            print("خطا: چهره پس از هم‌تراز سازی شناسایی نشد.")
            return None
        aligned_face_landmarks = face_recognition.face_landmarks(aligned_face_rgb, aligned_face_locations)[0]

        # 2. حذف پس‌زمینه تقریبی با ماسک بیضی
        mask = np.zeros(aligned_face.shape[:2], dtype=np.uint8)
        if aligned_face_landmarks.get('nose_bridge') is not None and aligned_face_landmarks.get('chin') is not None:
            nose_bridge = np.mean(aligned_face_landmarks['nose_bridge'], axis=0, dtype=np.int32)
            chin_points = np.array(aligned_face_landmarks['chin'], dtype=np.int32)
            min_chin = np.min(chin_points[:, 1])
            max_chin = np.max(chin_points[:, 1])
            left_eye_center = np.mean(aligned_face_landmarks.get('left_eye', [[0, 0]]), axis=0)
            right_eye_center = np.mean(aligned_face_landmarks.get('right_eye', [[0, 0]]), axis=0)
            face_width = int(np.linalg.norm(left_eye_center - right_eye_center) * 2) + 20
            face_height = int(max_chin - np.mean(aligned_face_landmarks.get('top_lip', [[0, min_chin]])[0], axis=0)[1] * 2) + 40
            center_face = (nose_bridge[0], (nose_bridge[1] + min_chin) // 2)
            axes = (face_width // 2, face_height // 2)
            if axes[0] > 0 and axes[1] > 0:
                cv2.ellipse(mask, center_face, axes, 0, 0, 360, 255, -1)
                masked_face = cv2.bitwise_and(aligned_face, aligned_face, mask=mask)
                masked_face_rgba = cv2.cvtColor(masked_face, cv2.COLOR_BGR2BGRA)
                masked_face_rgba[mask == 0] = [0, 0, 0, 0]
            else:
                masked_face_rgba = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2BGRA)
        else:
            print("خطا: نقاط کلیدی بینی یا چانه برای ایجاد ماسک یافت نشد.")
            masked_face_rgba = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2BGRA)

        # 3. جایگذاری و تطبیق روشنایی ساده
        if target_locations:
            target_top, target_right, target_bottom, target_left = target_locations[0]
            face_resized = cv2.resize(masked_face_rgba, (target_right - target_left, target_bottom - target_top))

            target_face_area = target_img[target_top:target_bottom, target_left:target_right].copy()

            face_mean_brightness = np.mean(cv2.cvtColor(face_resized[:, :, :3].astype(np.float32) / 255.0, cv2.COLOR_BGR2GRAY)) if face_resized.shape[2] == 4 and np.any(face_resized[:, :, 3] > 0) else np.mean(cv2.cvtColor(face_resized.astype(np.float32) / 255.0, cv2.COLOR_BGR2GRAY))
            target_face_mean_brightness = np.mean(cv2.cvtColor(target_face_area.astype(np.float32) / 255.0, cv2.COLOR_BGR2GRAY))

            brightness_factor = target_face_mean_brightness / (face_mean_brightness + 1e-6)
            adjusted_face = cv2.convertScaleAbs(face_resized[:, :, :3], alpha=brightness_factor, beta=0)
            final_face = adjusted_face
            if face_resized.shape[2] == 4:
                final_face = np.dstack((adjusted_face, face_resized[:, :, 3]))

            # ترکیب با در نظر گرفتن آلفا
            alpha_face = final_face[:, :, 3] / 255.0 if final_face.shape[2] == 4 else np.ones(final_face.shape[:2])
            alpha_target = 1.0 - alpha_face
            blended_face = np.zeros(target_face_area.shape, dtype=np.uint8)
            for c in range(0, 3):
                blended_face[:, :, c] = (alpha_face * final_face[:, :, c] +
                                         alpha_target * target_face_area[:, :, c])

            target_img[target_top:target_bottom, target_left:target_right] = blended_face

            swapped_path = f"swapped_advanced_{user_id}.jpg"
            cv2.imwrite(swapped_path, target_img)
            return swapped_path
        else:
            print("خطا: موقعیت چهره هدف در دسترس نیست.")
            return None

    except Exception as e:
        print("خطا در پردازش پیشرفته:", e)
        traceback.print_exc()
        return None

app.run()
