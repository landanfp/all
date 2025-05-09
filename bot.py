from pyrogram import Client, filters
from pyrogram.types import Message
import cv2
import face_recognition
import numpy as np
import os
import traceback

API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '1396293494:AAE6YAY-Vog3QPvSNCo8x80FsIue9FJGWh8' # توکن خود را جایگزین کنید
LOG_CHANNEL = -1001792962793  # شناسه کانال لاگ خود را وارد کنید (اختیاری)

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ذخیره عکس‌ها به صورت موقت
user_photos = {}

# تابع اصلی شما برای محاسبه ماتریس تبدیل (بدون تغییر فرض شده است)
def transformation_matrix(eye_center_src, eye_center_dst, eye_center_right_src, eye_center_right_dst, scale=1.0):
    if eye_center_src is None or eye_center_dst is None or eye_center_right_src is None or eye_center_right_dst is None:
        print("خطا: یکی از مراکز چشم برای هم‌تراز سازی در دسترس نیست.")
        return None
    dx_src = eye_center_right_src[0] - eye_center_src[0]
    dy_src = eye_center_right_src[1] - eye_center_src[1]
    
    # جلوگیری از تقسیم بر صفر اگر چشم‌ها روی هم باشند (بسیار نادر)
    if dx_src == 0 and dy_src == 0: # اگر فاصله بین چشم‌ها صفر باشد
        dist_src = 1e-6 # یک مقدار کوچک برای جلوگیری از خطا
    else:
        dist_src = np.sqrt(dx_src**2 + dy_src**2)
    angle_src = np.arctan2(dy_src, dx_src)

    dx_dst = eye_center_right_dst[0] - eye_center_dst[0]
    dy_dst = eye_center_right_dst[1] - eye_center_dst[1]

    if dx_dst == 0 and dy_dst == 0:
        dist_dst = 1e-6
    else:
        dist_dst = np.sqrt(dx_dst**2 + dy_dst**2)
    angle_dst = np.arctan2(dy_dst, dx_dst)

    scale_factor = dist_dst / dist_src if dist_src > 1e-7 else 1.0 # dist_src باید بزرگتر از یک مقدار کوچک باشد
    rotation = angle_dst - angle_src

    center_src = (int((eye_center_src[0] + eye_center_right_src[0]) // 2),
                   int((eye_center_src[1] + eye_center_right_src[1]) // 2))
    center_dst = (int((eye_center_dst[0] + eye_center_right_dst[0]) // 2),
                   int((eye_center_dst[1] + eye_center_right_dst[1]) // 2))

    M = cv2.getRotationMatrix2D(center_src, np.degrees(rotation), scale_factor * scale)
    
    # محاسبه جابجایی (translation)
    # ابتدا چرخش و تغییر مقیاس را روی مرکز مبدا اعمال می‌کنیم تا ببینیم به کجا منتقل می‌شود
    rotated_scaled_center_src_x = M[0,0] * center_src[0] + M[0,1] * center_src[1]
    rotated_scaled_center_src_y = M[1,0] * center_src[0] + M[1,1] * center_src[1]

    # سپس مقدار جابجایی لازم را برای رساندن آن به مرکز مقصد محاسبه می‌کنیم
    dx_translate = center_dst[0] - rotated_scaled_center_src_x
    dy_translate = center_dst[1] - rotated_scaled_center_src_y
    
    M[0, 2] += dx_translate # جابجایی در راستای x
    M[1, 2] += dy_translate # جابجایی در راستای y
    return M

async def do_advanced_face_swap(user_id, face_path, target_path):
    try:
        print(f"شروع پردازش برای face_path: {face_path}, target_path: {target_path}")

        face_img = cv2.imread(face_path)
        target_img = cv2.imread(target_path)

        if face_img is None:
            print(f"خطا: فایل عکس چهره در مسیر '{face_path}' بارگذاری نشد یا فرمت نامعتبر دارد.")
            return None
        if target_img is None:
            print(f"خطا: فایل عکس هدف در مسیر '{target_path}' بارگذاری نشد یا فرمت نامعتبر دارد.")
            return None

        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        target_img_rgb = cv2.cvtColor(target_img, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(face_img_rgb, model="hog") # 'cnn' دقیق‌تر اما کندتر
        target_locations = face_recognition.face_locations(target_img_rgb, model="hog")

        print(f"تعداد چهره‌های شناسایی شده در عکس چهره: {len(face_locations)}")
        print(f"تعداد چهره‌های شناسایی شده در عکس هدف: {len(target_locations)}")

        if not face_locations:
            print("خطا: چهره‌ای در عکس اصلی (چهره شما) شناسایی نشد.")
            return None
        if not target_locations:
            print("خطا: چهره‌ای در عکس هدف شناسایی نشد.")
            return None

        face_landmarks_list = face_recognition.face_landmarks(face_img_rgb, face_locations)
        target_landmarks_list = face_recognition.face_landmarks(target_img_rgb, target_locations)

        if not face_landmarks_list:
            print("خطا: نقاط کلیدی صورت (landmarks) در عکس چهره شناسایی نشد.")
            return None
        if not target_landmarks_list:
            print("خطا: نقاط کلیدی صورت (landmarks) در عکس هدف شناسایی نشد.")
            return None

        face_landmarks = face_landmarks_list[0]
        target_landmarks = target_landmarks_list[0]

        def get_eye_center(landmarks, eye_key):
            if landmarks.get(eye_key) and len(landmarks[eye_key]) > 0:
                return np.mean(landmarks[eye_key], axis=0, dtype=np.int32)
            print(f"هشدار: نقاط کلیدی چشم '{eye_key}' یافت نشد.")
            return None

        face_eye_left = get_eye_center(face_landmarks, 'left_eye')
        face_eye_right = get_eye_center(face_landmarks, 'right_eye')
        target_eye_left = get_eye_center(target_landmarks, 'left_eye')
        target_eye_right = get_eye_center(target_landmarks, 'right_eye')

        if not (face_eye_left is not None and face_eye_right is not None and \
                target_eye_left is not None and target_eye_right is not None):
            print("خطا: تمام نقاط مرکزی چشم برای هم‌تراز سازی یافت نشدند.")
            return None

        M = transformation_matrix(face_eye_left, target_eye_left, face_eye_right, target_eye_right)

        if M is None:
            print("خطا: ماتریس تبدیل (M) برای هم‌تراز سازی محاسبه نشد.")
            return None
        
        h_target, w_target = target_img.shape[:2]
        aligned_face = cv2.warpAffine(face_img, M, (w_target, h_target), borderMode=cv2.BORDER_REPLICATE)
        
        aligned_face_rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        aligned_face_locations = face_recognition.face_locations(aligned_face_rgb)

        if not aligned_face_locations:
            print("خطا: چهره پس از هم‌تراز سازی اولیه شناسایی نشد.")
            return None
            
        aligned_face_landmarks_list = face_recognition.face_landmarks(aligned_face_rgb, aligned_face_locations)
        if not aligned_face_landmarks_list:
            print("خطا: نقاط کلیدی چهره هم‌تراز شده شناسایی نشد.")
            return None
        aligned_face_landmarks = aligned_face_landmarks_list[0]

        mask = np.zeros(aligned_face.shape[:2], dtype=np.uint8)
        
        # ایجاد ماسک با استفاده از نقاط کلیدی مهم یا Convex Hull برای پایداری بیشتر
        points_for_hull = []
        # نقاط کلیدی معمول برای تشکیل یک ماسک خوب دور صورت
        landmark_keys_for_mask = ['chin', 'left_eyebrow', 'right_eyebrow'] 
        for key in landmark_keys_for_mask:
            if aligned_face_landmarks.get(key):
                points_for_hull.extend(aligned_face_landmarks[key])
        
        if len(points_for_hull) >= 3: # Convex Hull حداقل به 3 نقطه نیاز دارد
            hull_pts = cv2.convexHull(np.array(points_for_hull, dtype=np.int32))
            cv2.drawContours(mask, [hull_pts], 0, 255, -1)
            # کمی بزرگ کردن ماسک برای پوشش بهتر لبه‌ها
            mask = cv2.dilate(mask, np.ones((10,10), np.uint8), iterations=2) # iterations و kernel size قابل تنظیم
        else:
            print("هشدار: نقاط کلیدی کافی برای ایجاد ماسک با convex hull یافت نشد. از bounding box چهره هم‌تراز شده استفاده می‌شود.")
            (top, right, bottom, left) = aligned_face_locations[0]
            h_mask, w_mask = mask.shape
            top = max(0, top - 10) # کمی حاشیه
            left = max(0, left - 10)
            bottom = min(h_mask, bottom + 10)
            right = min(w_mask, right + 10)
            if top < bottom and left < right:
                 cv2.rectangle(mask, (left, top), (right, bottom), 255, -1)
            else:
                 print("خطا: ابعاد bounding box برای ماسک نامعتبر است.")
                 mask.fill(255) # اگر هیچ چیز دیگری کار نکرد، کل ماسک را سفید کن

        # نرم کردن لبه‌های ماسک
        mask = cv2.GaussianBlur(mask, (15, 15), 0) # اندازه کرنل بلور قابل تنظیم است

        masked_aligned_face = cv2.bitwise_and(aligned_face, aligned_face, mask=mask)
        masked_aligned_face_rgba = cv2.cvtColor(masked_aligned_face, cv2.COLOR_BGR2BGRA)
        masked_aligned_face_rgba[mask == 0] = [0, 0, 0, 0] # شفاف کردن پس‌زمینه

        target_top, target_right, target_bottom, target_left = target_locations[0]
        
        target_face_width = target_right - target_left
        target_face_height = target_bottom - target_top

        if target_face_width <= 0 or target_face_height <= 0:
            print(f"خطا: ابعاد چهره هدف نامعتبر است. Width: {target_face_width}, Height: {target_face_height}")
            return None

        # **FIXED RESIZE BUG HERE**
        resized_face_rgba = cv2.resize(masked_aligned_face_rgba, (target_face_width, target_face_height), interpolation=cv2.INTER_AREA)

        output_img = target_img.copy()
        
        # استخراج کانال آلفا و کانال‌های رنگی
        alpha_s = resized_face_rgba[:, :, 3] / 255.0 # نرمال‌سازی آلفا بین 0 و 1
        # برای جلوگیری از لبه‌های تیز، می‌توان آلفا را کمی محو کرد
        # alpha_s = cv2.GaussianBlur(alpha_s, (7,7), 0) 

        # تصحیح رنگ ساده (تطبیق روشنایی میانگین)
        face_bgr_resized = resized_face_rgba[:, :, :3]
        target_face_roi_bgr = target_img[target_top:target_bottom, target_left:target_right]

        # محاسبه روشنایی فقط برای پیکسل‌های قابل مشاهده چهره منبع
        visible_face_pixels_gray = cv2.cvtColor(face_bgr_resized, cv2.COLOR_BGR2GRAY)[alpha_s > 0.1] # آستانه برای آلفا
        if visible_face_pixels_gray.size > 0:
            mean_brightness_face = np.mean(visible_face_pixels_gray)
        else:
            mean_brightness_face = 128 # مقدار پیش‌فرض اگر چهره کاملا شفاف باشد (نباید اتفاق بیفتد)

        mean_brightness_target_roi = np.mean(cv2.cvtColor(target_face_roi_bgr, cv2.COLOR_BGR2GRAY))
        
        brightness_factor = mean_brightness_target_roi / (mean_brightness_face + 1e-6) # جلوگیری از تقسیم بر صفر
        
        # اعمال ضریب روشنایی و اطمینان از اینکه مقادیر در محدوده 0-255 باقی می‌مانند
        corrected_face_bgr = np.clip(face_bgr_resized.astype(np.float32) * brightness_factor, 0, 255).astype(np.uint8)
        
        # ترکیب آلفا
        for c in range(0, 3): # برای هر کانال رنگی B, G, R
            output_img[target_top:target_bottom, target_left:target_right, c] = \
                (alpha_s * corrected_face_bgr[:, :, c]) + \
                ((1 - alpha_s) * target_face_roi_bgr[:, :, c])

        # استفاده از seamlessClone برای ترکیب طبیعی‌تر (اختیاری و ممکن است کندتر باشد)
        # center_pt = (target_left + target_face_width // 2, target_top + target_face_height // 2)
        # try:
        #     # seamlessClone به ماسک باینری (0 و 255) نیاز دارد، نه ماسک آلفا
        #     binary_mask_for_clone = (alpha_s * 255).astype(np.uint8)
        #     # اطمینان از اینکه ماسک فقط یک کانال دارد
        #     if binary_mask_for_clone.ndim == 3 and binary_mask_for_clone.shape[2] == 1:
        #        binary_mask_for_clone = binary_mask_for_clone[:,:,0]
        #     elif binary_mask_for_clone.ndim != 2:
        #        print("خطا: ماسک برای seamlessClone ابعاد نامناسبی دارد.")
        #        raise ValueError("ابعاد نامناسب ماسک")

        #     # اطمینان از اینکه corrected_face_bgr هم 3 کاناله است
        #     if corrected_face_bgr.shape[2] !=3 :
        #        print("خطا: تصویر منبع برای seamlessClone باید 3 کاناله باشد.")
        #        raise ValueError("تصویر منبع باید 3 کاناله باشد.")

        #     if np.any(binary_mask_for_clone) and binary_mask_for_clone.shape == corrected_face_bgr.shape[:2]: # اگر ماسک خالی نباشد و ابعاد درست باشد
        #         output_img = cv2.seamlessClone(corrected_face_bgr, target_img, binary_mask_for_clone, center_pt, cv2.NORMAL_CLONE)
        #     else:
        #         print("هشدار: ماسک برای seamlessClone نامعتبر است یا خالی است. از ترکیب آلفای دستی استفاده شد.")
        # except Exception as e_sc:
        #     print(f"خطا در seamlessClone: {e_sc}. از ترکیب آلفای دستی استفاده می‌شود.")
        #     # اگر seamlessClone شکست خورد، نتیجه ترکیب آلفای دستی که قبلا محاسبه شده، استفاده می‌شود.
        
        swapped_path = f"swapped_advanced_{user_id}.jpg"
        cv2.imwrite(swapped_path, output_img)
        print(f"عکس ترکیب شده با موفقیت در {swapped_path} ذخیره شد.")
        return swapped_path

    except Exception as e:
        print(f"خطای عمومی در پردازش پیشرفته: {e}")
        error_details = traceback.format_exc()
        print(error_details)
        try:
            # ارسال خطا به کانال لاگ (اگر تعریف شده باشد)
            if LOG_CHANNEL:
                await app.send_message(LOG_CHANNEL, f"خطا در Face Swap برای کاربر {user_id}:\n\nPath چهره: {face_path}\nPath هدف: {target_path}\n\n```\n{error_details}\n```")
        except Exception as log_e:
            print(f"خطا در ارسال لاگ به تلگرام: {log_e}")
        return None

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

    # از file_id برای جلوگیری از دانلود مجدد در صورت امکان استفاده کنید (اختیاری)
    photo_path = await message.download(file_name=f"temp_{user_id}_{message.photo.file_unique_id}.jpg")


    if user_photos[user_id]["face"] is None:
        user_photos[user_id]["face"] = photo_path
        await message.reply("عکس چهره دریافت شد. حالا عکسی را بفرستید که می‌خواهید چهره روی آن قرار بگیرد.")
    else:
        user_photos[user_id]["target"] = photo_path
        processing_msg = await message.reply("در حال انجام Face Swap پیشرفته... لطفاً کمی صبر کنید.")
        
        swapped_path = await do_advanced_face_swap(user_id, user_photos[user_id]["face"], user_photos[user_id]["target"])
        
        if swapped_path is None:
            await processing_msg.edit_text("متأسفانه در پردازش مشکلی رخ داد. لطفاً از واضح بودن چهره‌ها در هر دو عکس اطمینان حاصل کنید و دوباره تلاش کنید. \n(نکته: چهره‌ها باید مستقیم و بدون پوشش زیاد باشند)")
        else:
            try:
                await message.reply_photo(swapped_path, caption="چهره با موفقیت جایگزین شد!")
                if os.path.exists(swapped_path):
                    os.remove(swapped_path)
            except Exception as e:
                print(f"خطا در ارسال عکس نتیجه: {e}")
                await message.reply("خطایی در ارسال عکس نتیجه رخ داد. فایل در سرور پردازش شده است.")


        # پاک کردن داده‌ها پس از اتمام کار یا بروز خطا
        if user_photos[user_id].get("face") and os.path.exists(user_photos[user_id]["face"]):
            os.remove(user_photos[user_id]["face"])
        if user_photos[user_id].get("target") and os.path.exists(user_photos[user_id]["target"]):
            os.remove(user_photos[user_id]["target"])
        if user_id in user_photos: # بررسی مجدد برای اطمینان
            del user_photos[user_id]

if __name__ == "__main__":
    print("ربات در حال اجرا است...")
    app.run()
