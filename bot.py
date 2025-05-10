import cv2
import face_recognition
import numpy as np
import os
import traceback
from pyrogram import Client, filters
from pyrogram.types import Message

# ... (API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL مانند قبل) ...
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8' # توکن خود را جایگزین کنید
LOG_CHANNEL = -1001792962793  # شناسه کانال لاگ خود را وارد کنید

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_photos = {}

# --- تابع transformation_matrix (بدون تغییر نسبت به نسخه شما) ---
def transformation_matrix(eye_center_src, eye_center_dst, eye_center_right_src, eye_center_right_dst, scale=1.0):
    if any(p is None for p in [eye_center_src, eye_center_dst, eye_center_right_src, eye_center_right_dst]):
        print("خطا در transformation_matrix: یکی از مراکز چشم None است.", flush=True)
        return None

    try:
        eye_center_src = np.array(eye_center_src, dtype=np.float32)
        eye_center_dst = np.array(eye_center_dst, dtype=np.float32)
        eye_center_right_src = np.array(eye_center_right_src, dtype=np.float32)
        eye_center_right_dst = np.array(eye_center_right_dst, dtype=np.float32)

        dx_src = eye_center_right_src[0] - eye_center_src[0]
        dy_src = eye_center_right_src[1] - eye_center_src[1]
        dist_src = np.sqrt(dx_src**2 + dy_src**2)
        if dist_src < 1e-6:
            print("هشدار در transformation_matrix: فاصله چشم‌های مبدا بسیار کم است.", flush=True)
            dist_src = 1e-6
        angle_src = np.arctan2(dy_src, dx_src)

        dx_dst = eye_center_right_dst[0] - eye_center_dst[0]
        dy_dst = eye_center_right_dst[1] - eye_center_dst[1]
        dist_dst = np.sqrt(dx_dst**2 + dy_dst**2)
        if dist_dst < 1e-6:
            print("هشدار در transformation_matrix: فاصله چشم‌های مقصد بسیار کم است. از مقیاس پیش‌فرض استفاده می‌شود.", flush=True)
            dist_dst = dist_src
            if dist_dst < 1e-6: dist_dst = 1e-6
        angle_dst = np.arctan2(dy_dst, dx_dst)

        effective_scale = (dist_dst / dist_src) * scale
        rotation_rad = angle_dst - angle_src

        center_src_calc = ((eye_center_src[0] + eye_center_right_src[0]) / 2.0,
                           (eye_center_src[1] + eye_center_right_src[1]) / 2.0)

        M = cv2.getRotationMatrix2D(center_src_calc, np.degrees(rotation_rad), effective_scale)

        transformed_center_src_x = M[0,0] * center_src_calc[0] + M[0,1] * center_src_calc[1] + M[0,2]
        transformed_center_src_y = M[1,0] * center_src_calc[0] + M[1,1] * center_src_calc[1] + M[1,2]

        center_dst_calc = ((eye_center_dst[0] + eye_center_right_dst[0]) / 2.0,
                           (eye_center_dst[1] + eye_center_right_dst[1]) / 2.0)
        
        translation_x = center_dst_calc[0] - transformed_center_src_x
        translation_y = center_dst_calc[1] - transformed_center_src_y

        M[0,2] += translation_x
        M[1,2] += translation_y

        return M
    except Exception as e_tm:
        print(f"خطای استثنا در transformation_matrix: {e_tm}", flush=True)
        traceback.print_exc()
        return None


async def do_advanced_face_swap(user_id, face_path, target_path):
    try:
        print(f"DEBUG: شروع do_advanced_face_swap برای کاربر {user_id}.", flush=True)
        # ... (بررسی‌های اولیه فایل‌ها مانند قبل) ...
        if not face_path or not os.path.exists(face_path):
            print(f"خطا: مسیر عکس چهره '{face_path}' نامعتبر یا فایل وجود ندارد.", flush=True)
            return None
        if not target_path or not os.path.exists(target_path):
            print(f"خطا: مسیر عکس هدف '{target_path}' نامعتبر یا فایل وجود ندارد.", flush=True)
            return None

        face_img = cv2.imread(face_path)
        target_img = cv2.imread(target_path)

        if face_img is None:
            print(f"خطا: cv2.imread نتوانست عکس چهره را از مسیر '{face_path}' بخواند.", flush=True)
            return None
        if target_img is None:
            print(f"خطا: cv2.imread نتوانست عکس هدف را از مسیر '{target_path}' بخواند.", flush=True)
            return None
        
        print(f"DEBUG: عکس چهره با موفقیت بارگذاری شد، ابعاد: {face_img.shape}", flush=True)
        print(f"DEBUG: عکس هدف با موفقیت بارگذاری شد، ابعاد: {target_img.shape}", flush=True)

        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        target_img_rgb = cv2.cvtColor(target_img, cv2.COLOR_BGR2RGB)
        print("DEBUG: تبدیل تصاویر به RGB انجام شد.", flush=True)

        face_locations = face_recognition.face_locations(face_img_rgb, model="hog")
        # target_locations برای استفاده مستقیم در تغییر اندازه دیگر لازم نیست، اما برای بررسی اولیه خوب است
        target_locations_original = face_recognition.face_locations(target_img_rgb, model="hog") 
        print(f"DEBUG: تعداد چهره در عکس چهره: {len(face_locations)}, در عکس هدف (اصلی): {len(target_locations_original)}", flush=True)

        if not face_locations:
            print("خطا: چهره‌ای در عکس اصلی (چهره شما) شناسایی نشد.", flush=True)
            return None
        if not target_locations_original: # بررسی وجود چهره در هدف همچنان مهم است
            print("خطا: چهره‌ای در عکس هدف شناسایی نشد.", flush=True)
            return None

        face_landmarks_list = face_recognition.face_landmarks(face_img_rgb, face_locations)
        target_landmarks_list = face_recognition.face_landmarks(target_img_rgb, target_locations_original)
        print("DEBUG: تشخیص نقاط کلیدی (landmarks) انجام شد.", flush=True)

        if not face_landmarks_list:
            print("خطا: نقاط کلیدی صورت (landmarks) در عکس چهره شناسایی نشد.", flush=True)
            return None
        if not target_landmarks_list:
            print("خطا: نقاط کلیدی صورت (landmarks) در عکس هدف شناسایی نشد.", flush=True)
            return None

        face_landmarks = face_landmarks_list[0]
        target_landmarks = target_landmarks_list[0] # نقاط کلیدی از اولین چهره شناسایی شده در هدف
        print("DEBUG: اولین مجموعه نقاط کلیدی استخراج شد.", flush=True)

        def get_eye_center(landmarks, eye_key):
            if landmarks.get(eye_key) and len(landmarks[eye_key]) > 0:
                return np.mean(landmarks[eye_key], axis=0, dtype=np.int32) # np.int بدون dtype=np.int32
            print(f"هشدار: نقاط کلیدی چشم '{eye_key}' یافت نشد.", flush=True)
            return None

        face_eye_left = get_eye_center(face_landmarks, 'left_eye')
        face_eye_right = get_eye_center(face_landmarks, 'right_eye')
        target_eye_left = get_eye_center(target_landmarks, 'left_eye')
        target_eye_right = get_eye_center(target_landmarks, 'right_eye')
        print(f"DEBUG: مراکز چشم: چهره(چپ:{face_eye_left}, راست:{face_eye_right}), هدف(چپ:{target_eye_left}, راست:{target_eye_right})", flush=True)

        if not (face_eye_left is not None and face_eye_right is not None and \
                target_eye_left is not None and target_eye_right is not None):
            print("خطا: تمام نقاط مرکزی چشم برای هم‌تراز سازی یافت نشدند.", flush=True)
            return None

        M = transformation_matrix(face_eye_left, target_eye_left, face_eye_right, target_eye_right)
        print(f"DEBUG: ماتریس تبدیل M: {M}", flush=True)

        if M is None:
            print("خطا: ماتریس تبدیل (M) برای هم‌تراز سازی محاسبه نشد (None).", flush=True)
            return None
        
        h_target, w_target = target_img.shape[:2]
        # warpAffine چهره منبع را به ابعاد تصویر هدف تبدیل می‌کند و مقیاس و موقعیت را بر اساس M تنظیم می‌کند
        aligned_face = cv2.warpAffine(face_img, M, (w_target, h_target), borderMode=cv2.BORDER_REPLICATE)
        print("DEBUG: هم‌تراز سازی اولیه (warpAffine) انجام شد. ابعاد aligned_face:", aligned_face.shape, flush=True)
        
        aligned_face_rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        # حالا روی aligned_face (که هم‌اندازه با تصویر هدف است) چهره را پیدا می‌کنیم
        aligned_face_locations = face_recognition.face_locations(aligned_face_rgb, model="hog")
        print(f"DEBUG: تعداد چهره شناسایی شده پس از هم‌ترازسازی: {len(aligned_face_locations)}", flush=True)

        if not aligned_face_locations:
            print("خطا: چهره پس از هم‌تراز سازی اولیه شناسایی نشد. این ممکن است به دلیل ماتریس تبدیل نامناسب باشد.", flush=True)
            # اینجا می‌توانید تصویری از aligned_face را برای دیباگ ذخیره کنید
            # cv2.imwrite(f"debug_aligned_face_no_face_{user_id}.jpg", aligned_face)
            return None
            
        aligned_face_landmarks_list = face_recognition.face_landmarks(aligned_face_rgb, aligned_face_locations)
        if not aligned_face_landmarks_list:
            print("خطا: نقاط کلیدی چهره هم‌تراز شده شناسایی نشد.", flush=True)
            return None
        aligned_face_landmarks = aligned_face_landmarks_list[0]
        print("DEBUG: نقاط کلیدی چهره هم‌تراز شده استخراج شد.", flush=True)

        # ایجاد ماسک بر اساس نقاط کلیدی چهره هم‌تراز شده
        # ماسک هم‌اندازه با aligned_face (و در نتیجه تصویر هدف) خواهد بود
        mask = np.zeros(aligned_face.shape[:2], dtype=np.uint8)
        points_for_hull = []
        landmark_keys_for_mask = ['chin', 'left_eyebrow', 'right_eyebrow'] 
        for key in landmark_keys_for_mask:
            if aligned_face_landmarks.get(key) and len(aligned_face_landmarks[key]) > 0:
                points_for_hull.extend(aligned_face_landmarks[key])
        
        print(f"DEBUG: تعداد نقاط برای convex hull ماسک: {len(points_for_hull)}", flush=True)
        if len(points_for_hull) >= 3:
            hull_pts = cv2.convexHull(np.array(points_for_hull, dtype=np.int32))
            cv2.drawContours(mask, [hull_pts], 0, 255, -1)
            # دیلاته کردن ماسک برای پوشش بهتر لبه‌ها
            mask = cv2.dilate(mask, np.ones((15,15), np.uint8), iterations=3) # کمی افزایش دیلاته
            print("DEBUG: ماسک با convex hull ایجاد شد.", flush=True)
        else:
            print("هشدار: نقاط کلیدی کافی برای convex hull نبود. استفاده از bounding box چهره هم‌تراز شده.", flush=True)
            (top, right, bottom, left) = aligned_face_locations[0] # از چهره هم‌تراز شده
            margin = 15 # کمی افزایش حاشیه
            h_mask_img, w_mask_img = mask.shape
            top = max(0, top - margin)
            left = max(0, left - margin)
            bottom = min(h_mask_img, bottom + margin)
            right = min(w_mask_img, right + margin)
            if top < bottom and left < right:
                 cv2.rectangle(mask, (left, top), (right, bottom), 255, -1)
                 print("DEBUG: ماسک با bounding box ایجاد شد.", flush=True)
            else:
                 print("خطا: ابعاد bounding box برای ماسک نامعتبر است. استفاده از ماسک کامل.", flush=True)
                 mask.fill(255) # ماسک کامل در صورت خطا

        mask = cv2.GaussianBlur(mask, (25, 25), 0) # افزایش بلور برای لبه‌های نرم‌تر
        print("DEBUG: ماسک بلور شد.", flush=True)

        # اعمال ماسک روی چهره هم‌تراز شده
        masked_aligned_face = cv2.bitwise_and(aligned_face, aligned_face, mask=mask)
        # تبدیل به RGBA و شفاف کردن پس‌زمینه
        masked_aligned_face_rgba = cv2.cvtColor(masked_aligned_face, cv2.COLOR_BGR2BGRA)
        masked_aligned_face_rgba[mask == 0] = [0, 0, 0, 0] # پیکسل‌های خارج از ماسک کاملاً شفاف می‌شوند
        print("DEBUG: پس‌زمینه چهره هم‌تراز شده شفاف شد.", flush=True)

        # ***** تغییرات کلیدی از اینجا شروع می‌شود *****
        # دیگر نیازی به تغییر اندازه (resize) بر اساس target_face_width/height نیست
        # masked_aligned_face_rgba حالا در مقیاس و موقعیت صحیح در یک قاب هم‌اندازه با تصویر هدف قرار دارد.

        # استخراج کانال آلفا و BGR از چهره هم‌تراز شده (که هم‌اندازه با تصویر هدف است)
        alpha_s = masked_aligned_face_rgba[:, :, 3] / 255.0 # شکل: (h_target, w_target)
        face_bgr_warped = masked_aligned_face_rgba[:, :, :3] # شکل: (h_target, w_target, 3)

        # تطبیق روشنایی:
        # ناحیه ROI در تصویر هدف را بر اساس مکان چهره هم‌تراز شده (aligned_face_locations) تعریف می‌کنیم
        (al_top, al_right, al_bottom, al_left) = aligned_face_locations[0]
        # اطمینان از اینکه مختصات داخل مرزهای تصویر هدف هستند
        al_top = max(0, al_top)
        al_left = max(0, al_left)
        al_bottom = min(h_target, al_bottom)
        al_right = min(w_target, al_right)

        target_face_roi_bgr = target_img.copy() # مقدار پیش‌فرض در صورت عدم وجود ناحیه معتبر
        if al_bottom > al_top and al_right > al_left:
            target_face_roi_bgr = target_img[al_top:al_bottom, al_left:al_right]
            print(f"DEBUG: ROI برای تطبیق روشنایی از تصویر هدف استخراج شد: ({al_top},{al_left}) تا ({al_bottom},{al_right})", flush=True)
        else:
            print(f"هشدار: bounding box چهره هم‌تراز شده برای ROI تطبیق روشنایی نامعتبر است. از کل تصویر هدف استفاده می‌شود.", flush=True)


        # محاسبه روشنایی متوسط برای پیکسل‌های قابل مشاهده چهره هم‌تراز شده
        visible_face_pixels_gray = cv2.cvtColor(face_bgr_warped, cv2.COLOR_BGR2GRAY)[alpha_s > 0.1]
        if visible_face_pixels_gray.size > 0:
            mean_brightness_face = np.mean(visible_face_pixels_gray)
        else:
            mean_brightness_face = 128.0 # مقدار پیش‌فرض اگر چهره کاملاً شفاف باشد
        
        if target_face_roi_bgr.size > 0 and target_face_roi_bgr.shape[0] > 0 and target_face_roi_bgr.shape[1] > 0:
             mean_brightness_target_roi = np.mean(cv2.cvtColor(target_face_roi_bgr, cv2.COLOR_BGR2GRAY))
        else:
            print("هشدار: target_face_roi_bgr برای محاسبه روشنایی خالی یا نامعتبر است. از مقدار پیش‌فرض استفاده می‌شود.", flush=True)
            mean_brightness_target_roi = 128.0 # مقدار پیش‌فرض

        brightness_factor = mean_brightness_target_roi / (mean_brightness_face + 1e-6) # جلوگیری از تقسیم بر صفر
        print(f"DEBUG: ضریب روشنایی محاسبه‌شده: {brightness_factor}", flush=True)
        
        # اعمال ضریب روشنایی به کل چهره هم‌تراز شده
        # باید روی مقادیر float انجام شود و سپس به uint8 تبدیل شود
        corrected_face_bgr_float = face_bgr_warped.astype(np.float32) * brightness_factor
        corrected_face_bgr = np.clip(corrected_face_bgr_float, 0, 255).astype(np.uint8)
        print("DEBUG: تطبیق روشنایی روی چهره هم‌تراز شده انجام شد.", flush=True)
        
        # ترکیب مستقیم چهره اصلاح‌شده با تصویر هدف
        output_img = target_img.copy()
        
        # تبدیل به float برای ترکیب دقیق‌تر
        output_img_float = output_img.astype(np.float32)
        target_img_float = target_img.astype(np.float32) # برای بخش (1-alpha)
        # corrected_face_bgr از مرحله قبل float است و کلیپ شده، پس دوباره به float تبدیل می‌کنیم
        # corrected_face_bgr_float در بالا محاسبه شده است.

        for c in range(3): # برای هر کانال رنگی B, G, R
            output_img_float[:,:,c] = (alpha_s * corrected_face_bgr_float[:,:,c]) + \
                                      ((1 - alpha_s) * target_img_float[:,:,c])

        output_img = np.clip(output_img_float, 0, 255).astype(np.uint8)
        print("DEBUG: ترکیب آلفا (مستقیم) انجام شد.", flush=True)
        
        swapped_path = f"swapped_advanced_{user_id}.jpg"
        cv2.imwrite(swapped_path, output_img)
        print(f"عکس ترکیب شده با موفقیت در {swapped_path} ذخیره شد.", flush=True)
        return swapped_path

    except Exception as e:
        print(f"خطای عمومی استثنا در do_advanced_face_swap برای کاربر {user_id}: {e}", flush=True)
        error_details = traceback.format_exc()
        print(error_details, flush=True)
        try:
            if LOG_CHANNEL: 
                await app.send_message(LOG_CHANNEL, f"خطا در Face Swap برای کاربر {user_id}:\n\nPath چهره: {face_path}\nPath هدف: {target_path}\n\n```\n{error_details}\n```")
        except Exception as log_e:
            print(f"خطا در ارسال لاگ به تلگرام: {log_e}", flush=True)
        return None

# ... (کدهای @app.on_message و راه‌اندازی ربات مانند قبل باقی می‌مانند) ...
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_photos[message.from_user.id] = {"face": None, "target": None}
    await message.reply("سلام! لطفاً ابتدا یک عکس واضح از چهره خود ارسال کنید.")
    print(f"DEBUG: کاربر {message.from_user.id} دستور /start را اجرا کرد.", flush=True)

@app.on_message(filters.photo)
async def handle_photo(client, message: Message):
    user_id = message.from_user.id
    print(f"DEBUG: عکس دریافت شد از کاربر {user_id}.", flush=True)

    if user_id not in user_photos:
        print(f"DEBUG: کاربر {user_id} هنوز /start را نزده است.", flush=True)
        await message.reply("لطفاً ابتدا دستور /start را ارسال کنید.")
        return

    download_dir = "temp_photos" 
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"DEBUG: پوشه {download_dir} ایجاد شد.", flush=True)

    file_name = f"{download_dir}/user_{user_id}_photo_{message.photo.file_unique_id}.jpg"
    photo_path = await message.download(file_name=file_name)
    
    print(f"DEBUG: عکس در مسیر '{photo_path}' دانلود شد. بررسی وجود: {os.path.exists(photo_path)}", flush=True)

    if not photo_path or not os.path.exists(photo_path):
        print(f"خطا: دانلود عکس ناموفق بود یا فایل در مسیر '{photo_path}' وجود ندارد.", flush=True)
        await message.reply("مشکلی در دانلود عکس رخ داد. لطفاً دوباره تلاش کنید.")
        return
    try:
        img_check = cv2.imread(photo_path)
        if img_check is None:
            print(f"DEBUG: OpenCV نتوانست عکس دانلود شده '{photo_path}' را بلافاصله بخواند. حجم فایل: {os.path.getsize(photo_path) if os.path.exists(photo_path) else 'N/A'}", flush=True)
            await message.reply("عکس دریافت شده قابل پردازش نیست. لطفاً عکس دیگری ارسال کنید.")
            if os.path.exists(photo_path): os.remove(photo_path) 
            if user_id in user_photos and user_photos[user_id].get("face") == photo_path : user_photos[user_id]["face"] = None
            return
        else:
            print(f"DEBUG: OpenCV عکس '{photo_path}' را با موفقیت خواند. ابعاد: {img_check.shape}", flush=True)
    except Exception as e_cv_read:
        print(f"DEBUG: استثنا در خواندن عکس '{photo_path}' با OpenCV: {e_cv_read}", flush=True)
        await message.reply("خطایی در پردازش اولیه عکس رخ داد.")
        if os.path.exists(photo_path): os.remove(photo_path)
        if user_id in user_photos and user_photos[user_id].get("face") == photo_path : user_photos[user_id]["face"] = None
        return

    if user_photos[user_id]["face"] is None:
        user_photos[user_id]["face"] = photo_path
        await message.reply("عکس چهره دریافت شد. حالا عکسی را بفرستید که می‌خواهید چهره روی آن قرار بگیرد.")
        print(f"DEBUG: عکس چهره کاربر {user_id} در '{photo_path}' ذخیره شد.", flush=True)
    else:
        user_photos[user_id]["target"] = photo_path
        print(f"DEBUG: عکس هدف کاربر {user_id} در '{photo_path}' ذخیره شد.", flush=True)
        
        face_file_to_check = user_photos[user_id]["face"]
        if not face_file_to_check or not os.path.exists(face_file_to_check):
            print(f"خطا: فایل عکس چهره کاربر {user_id} ('{face_file_to_check}') قبل از پردازش یافت نشد!", flush=True)
            await message.reply("مشکلی در دسترسی به عکس اولیه چهره رخ داد. لطفاً با /start مجدداً شروع کنید.")
            if user_id in user_photos: del user_photos[user_id] 
            return
        
        img_check_face = cv2.imread(face_file_to_check)
        if img_check_face is None:
            print(f"خطا: OpenCV نتوانست عکس چهره ذخیره شده '{face_file_to_check}' را بخواند!", flush=True)
            await message.reply("عکس اولیه چهره قابل پردازش نیست. لطفاً با /start مجدداً شروع کنید و عکس واضح‌تری ارسال کنید.")
            if os.path.exists(face_file_to_check): os.remove(face_file_to_check)
            if user_id in user_photos: del user_photos[user_id]
            return

        processing_msg = await message.reply("در حال انجام Face Swap پیشرفته... لطفاً کمی صبر کنید.")
        
        swapped_path = await do_advanced_face_swap(user_id, user_photos[user_id]["face"], user_photos[user_id]["target"])
        
        if swapped_path is None:
            await processing_msg.edit_text("متأسفانه در پردازش مشکلی رخ داد. لطفاً از واضح بودن چهره‌ها در هر دو عکس اطمینان حاصل کنید و دوباره تلاش کنید. \n(نکته: چهره‌ها باید مستقیم و بدون پوشش زیاد باشند)")
            print(f"DEBUG: Face swap برای کاربر {user_id} ناموفق بود (swapped_path is None).", flush=True)
        else:
            try:
                await message.reply_photo(swapped_path, caption="چهره با موفقیت جایگزین شد!")
                print(f"DEBUG: عکس نتیجه برای کاربر {user_id} ارسال شد.", flush=True)
            except Exception as e_send:
                print(f"خطا در ارسال عکس نتیجه برای کاربر {user_id}: {e_send}", flush=True)
                await message.reply("خطایی در ارسال عکس نتیجه رخ داد. فایل در سرور پردازش شده است.")
            finally: 
                if os.path.exists(swapped_path):
                    os.remove(swapped_path)
                    print(f"DEBUG: فایل نتیجه '{swapped_path}' پاک شد.", flush=True)

        face_file_to_delete = user_photos[user_id].get("face")
        if face_file_to_delete and os.path.exists(face_file_to_delete):
            try:
                os.remove(face_file_to_delete)
                print(f"DEBUG: فایل موقت چهره '{face_file_to_delete}' پاک شد.", flush=True)
            except Exception as e_del_face:
                print(f"خطا در پاک کردن فایل موقت چهره '{face_file_to_delete}': {e_del_face}", flush=True)

        target_file_to_delete = user_photos[user_id].get("target")
        if target_file_to_delete and os.path.exists(target_file_to_delete):
            try:
                os.remove(target_file_to_delete)
                print(f"DEBUG: فایل موقت هدف '{target_file_to_delete}' پاک شد.", flush=True)
            except Exception as e_del_target:
                print(f"خطا در پاک کردن فایل موقت هدف '{target_file_to_delete}': {e_del_target}", flush=True)
        
        if user_id in user_photos:
            del user_photos[user_id]
            print(f"DEBUG: اطلاعات کاربر {user_id} از user_photos پاک شد.", flush=True)

if __name__ == "__main__":
    print("ربات در حال اجرا است...", flush=True)
    if not os.path.exists("logs"):
        os.makedirs("logs")
    if not os.path.exists("temp_photos"):
        os.makedirs("temp_photos")
        print("پوشه temp_photos ایجاد شد.", flush=True)

    print(f"cv2 version: {cv2.__version__}", flush=True)
    print(f"face_recognition version: {face_recognition.__version__}", flush=True)
    
    app.run()
