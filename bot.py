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

# --- تابع transformation_matrix (بدون تغییر) ---
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
            dist_src = 1e-6
        angle_src = np.arctan2(dy_src, dx_src)

        dx_dst = eye_center_right_dst[0] - eye_center_dst[0]
        dy_dst = eye_center_right_dst[1] - eye_center_dst[1]
        dist_dst = np.sqrt(dx_dst**2 + dy_dst**2)
        if dist_dst < 1e-6:
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

def match_histograms(source_img, template_img, mask=None):
    """
    تصویر منبع را برای تطابق با هیستوگرام رنگ تصویر الگو تنظیم می‌کند.
    از ماسک برای در نظر گرفتن فقط ناحیه چهره در تصویر منبع استفاده می‌شود.
    """
    print("DEBUG: شروع match_histograms.", flush=True)
    output = source_img.copy()
    
    # اگر ماسک وجود دارد، فقط روی ناحیه ماسک شده عمل می‌کنیم
    # در غیر این صورت، روی کل تصویر
    source_pixels_for_hist = source_img
    if mask is not None:
        # اطمینان از اینکه ماسک تک کاناله و باینری است
        if len(mask.shape) == 3:
            mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        else:
            mask_gray = mask
        _, binary_mask = cv2.threshold(mask_gray, 127, 255, cv2.THRESH_BINARY)
        
        # اگر هیچ پیکسلی در ماسک نیست، منبع را برگردان
        if cv2.countNonZero(binary_mask) == 0:
            print("هشدار: ماسک در match_histograms خالی است.", flush=True)
            return output
        source_pixels_for_hist = cv2.bitwise_and(source_img, source_img, mask=binary_mask)

    # تبدیل به فضای رنگی مناسب (مثلاً LAB برای تطابق بهتر روشنایی و رنگ)
    source_lab = cv2.cvtColor(source_pixels_for_hist, cv2.COLOR_BGR2LAB)
    template_lab = cv2.cvtColor(template_img, cv2.COLOR_BGR2LAB)

    for i in range(3): # L, A, B channels
        hist_src, _ = np.histogram(source_lab[:,:,i][binary_mask > 0 if mask is not None else source_lab[:,:,i] > 0].flatten(), 256, [0,256])
        hist_template, _ = np.histogram(template_lab[:,:,i].flatten(), 256, [0,256])

        # محاسبه تابع توزیع تجمعی (CDF)
        cdf_src = hist_src.cumsum()
        cdf_template = hist_template.cumsum()

        # نرمال سازی CDF
        cdf_src = (cdf_src - cdf_src.min()) * 255 / (cdf_src.max() - cdf_src.min() + 1e-6) # جلوگیری از تقسیم بر صفر
        cdf_src = np.ma.filled(cdf_src, 0).astype('uint8') # پر کردن مقادیر ماسک شده

        cdf_template = (cdf_template - cdf_template.min()) * 255 / (cdf_template.max() - cdf_template.min() + 1e-6)
        cdf_template = np.ma.filled(cdf_template, 0).astype('uint8')

        # ایجاد جدول جستجو (LUT)
        lut = np.zeros(256, dtype='uint8')
        j = 0
        for k in range(256):
            while j < 255 and cdf_src[k] > cdf_template[j]:
                j += 1
            lut[k] = j
        
        # اعمال LUT به کانال مربوطه در تصویر منبع اصلی (نه فقط پیکسل‌های ماسک شده)
        # این اطمینان می‌دهد که تغییرات رنگ به طور یکنواخت اعمال می‌شود و سپس توسط seamless clone ترکیب می‌شود.
        source_lab_channel_original = cv2.cvtColor(source_img, cv2.COLOR_BGR2LAB)[:,:,i]
        output_lab_channel = cv2.LUT(source_lab_channel_original, lut)
        
        current_output_lab = cv2.cvtColor(output, cv2.COLOR_BGR2LAB)
        current_output_lab[:,:,i] = output_lab_channel
        output = cv2.cvtColor(current_output_lab, cv2.COLOR_LAB2BGR)

    print("DEBUG: پایان match_histograms.", flush=True)
    return output


async def do_advanced_face_swap(user_id, face_path, target_path):
    try:
        print(f"DEBUG: شروع do_advanced_face_swap برای کاربر {user_id}.", flush=True)
        # ... (بررسی‌های اولیه فایل‌ها مانند قبل) ...
        if not face_path or not os.path.exists(face_path): return None
        if not target_path or not os.path.exists(target_path): return None
        face_img = cv2.imread(face_path)
        target_img = cv2.imread(target_path)
        if face_img is None or target_img is None: return None

        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        target_img_rgb = cv2.cvtColor(target_img, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(face_img_rgb, model="hog")
        target_locations_original = face_recognition.face_locations(target_img_rgb, model="hog")

        if not face_locations or not target_locations_original:
            print("خطا: چهره در یکی از تصاویر شناسایی نشد.", flush=True)
            return None

        face_landmarks_list = face_recognition.face_landmarks(face_img_rgb, face_locations)
        target_landmarks_list = face_recognition.face_landmarks(target_img_rgb, target_locations_original)

        if not face_landmarks_list or not target_landmarks_list:
            print("خطا: نقاط کلیدی صورت (landmarks) شناسایی نشد.", flush=True)
            return None

        face_landmarks = face_landmarks_list[0]
        target_landmarks = target_landmarks_list[0]

        def get_eye_center(landmarks, eye_key):
            if landmarks.get(eye_key) and len(landmarks[eye_key]) > 0:
                return np.mean(landmarks[eye_key], axis=0).astype(int)
            return None

        face_eye_left = get_eye_center(face_landmarks, 'left_eye')
        face_eye_right = get_eye_center(face_landmarks, 'right_eye')
        target_eye_left = get_eye_center(target_landmarks, 'left_eye')
        target_eye_right = get_eye_center(target_landmarks, 'right_eye')

        if not all([face_eye_left, face_eye_right, target_eye_left, target_eye_right]):
            print("خطا: تمام نقاط مرکزی چشم برای هم‌تراز سازی یافت نشدند.", flush=True)
            return None

        M = transformation_matrix(face_eye_left, target_eye_left, face_eye_right, target_eye_right)
        if M is None: return None
        
        h_target, w_target = target_img.shape[:2]
        aligned_face = cv2.warpAffine(face_img, M, (w_target, h_target), borderMode=cv2.BORDER_REPLICATE)
        
        aligned_face_rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        aligned_face_locations = face_recognition.face_locations(aligned_face_rgb, model="hog")

        if not aligned_face_locations:
            print("خطا: چهره پس از هم‌تراز سازی اولیه شناسایی نشد.", flush=True)
            return None
            
        aligned_face_landmarks_list = face_recognition.face_landmarks(aligned_face_rgb, aligned_face_locations)
        if not aligned_face_landmarks_list:
            print("خطا: نقاط کلیدی چهره هم‌تراز شده شناسایی نشد.", flush=True)
            return None
        aligned_face_landmarks = aligned_face_landmarks_list[0]

        # --- ایجاد ماسک باینری دقیق‌تر برای seamlessClone ---
        mask_for_seamless = np.zeros(aligned_face.shape[:2], dtype=np.uint8)
        points_for_hull = []
        # لیست نقاط کلیدی برای کانتور بیرونی چهره
        keys_for_outer_contour = ['chin', 'left_eyebrow', 'right_eyebrow']
        for key in keys_for_outer_contour:
            if aligned_face_landmarks.get(key):
                points_for_hull.extend(aligned_face_landmarks[key])
        
        # اضافه کردن نقاط کلیدی بیشتر برای دقت بهتر (مثلا نقاط بیرونی چشم‌ها اگر لازم باشد)
        # if aligned_face_landmarks.get('left_eye'): points_for_hull.append(aligned_face_landmarks['left_eye'][0])
        # if aligned_face_landmarks.get('right_eye'): points_for_hull.append(aligned_face_landmarks['right_eye'][3])

        if len(points_for_hull) >= 3:
            hull_pts = cv2.convexHull(np.array(points_for_hull, dtype=np.int32))
            cv2.drawContours(mask_for_seamless, [hull_pts], 0, 255, -1)
            # دیلاته کردن ماسک برای پوشش کامل‌تر لبه‌ها، اما نه بیش از حد
            kernel_dilate = np.ones((7,7), np.uint8) # کرنل کوچکتر برای دیلاته
            mask_for_seamless = cv2.dilate(mask_for_seamless, kernel_dilate, iterations=1) 
        else:
            print("هشدار: نقاط کافی برای convex hull نبود. استفاده از bounding box.", flush=True)
            (top, right, bottom, left) = aligned_face_locations[0]
            cv2.rectangle(mask_for_seamless, (left, top), (right, bottom), 255, -1)

        # --- تطبیق رنگ و روشنایی با تطبیق هیستوگرام ---
        (al_top, al_right, al_bottom, al_left) = aligned_face_locations[0]
        target_face_roi_for_hist_match = target_img[max(0,al_top):min(h_target,al_bottom), max(0,al_left):min(w_target,al_right)]
        
        if target_face_roi_for_hist_match.size == 0:
            print("هشدار: ROI هدف برای تطبیق هیستوگرام خالی است. از تطبیق رنگ صرف‌نظر می‌شود.", flush=True)
            aligned_face_color_corrected = aligned_face.copy()
        else:
            print("DEBUG: انجام تطبیق هیستوگرام رنگ.", flush=True)
            # تطبیق رنگ aligned_face با ناحیه چهره در تصویر هدف
            # ماسک مورد استفاده برای تطبیق هیستوگرام باید مربوط به aligned_face باشد
            aligned_face_color_corrected = match_histograms(aligned_face, target_face_roi_for_hist_match, mask=mask_for_seamless)
            print("DEBUG: تطبیq هیستوگرام رنگ انجام شد.", flush=True)


        # --- ترکیب با cv2.seamlessClone ---
        center_x = (al_left + al_right) // 2
        center_y = (al_top + al_bottom) // 2
        center_for_seamless = (center_x, center_y)

        if not (0 <= center_for_seamless[0] < w_target and 0 <= center_for_seamless[1] < h_target):
            print(f"هشدار: مرکز ({center_for_seamless}) برای seamlessClone خارج از محدوده است. استفاده از مرکز تصویر.", flush=True)
            center_for_seamless = (w_target // 2, h_target // 2)
        
        output_img = target_img.copy()
        try:
            # استفاده از MIXED_CLONE برای ترکیب بهتر بافت‌ها
            print("DEBUG: تلاش برای ترکیب با cv2.seamlessClone (MIXED_CLONE).", flush=True)
            output_img = cv2.seamlessClone(aligned_face_color_corrected, target_img, mask_for_seamless, center_for_seamless, cv2.MIXED_CLONE)
            print("DEBUG: ترکیب با cv2.seamlessClone (MIXED_CLONE) موفقیت آمیز بود.", flush=True)
        except cv2.error as e_seamless:
            print(f"خطا در cv2.seamlessClone (MIXED_CLONE): {e_seamless}", flush=True)
            print("تلاش مجدد با cv2.NORMAL_CLONE.", flush=True)
            try:
                output_img = cv2.seamlessClone(aligned_face_color_corrected, target_img, mask_for_seamless, center_for_seamless, cv2.NORMAL_CLONE)
                print("DEBUG: ترکیب با cv2.seamlessClone (NORMAL_CLONE) موفقیت آمیز بود.", flush=True)
            except cv2.error as e_seamless_normal:
                print(f"خطا در cv2.seamlessClone (NORMAL_CLONE): {e_seamless_normal}", flush=True)
                print("بازگشت به ترکیب آلفای دستی.", flush=True)
                # --- Fallback: ترکیب آلفا ---
                alpha_mask_blurred = cv2.GaussianBlur(mask_for_seamless, (35, 35), 0)
                corrected_face_rgba = cv2.cvtColor(aligned_face_color_corrected, cv2.COLOR_BGR2BGRA)
                corrected_face_rgba[:, :, 3] = alpha_mask_blurred
                
                alpha_s = corrected_face_rgba[:, :, 3] / 255.0
                face_bgr_for_alpha = corrected_face_rgba[:, :, :3]

                output_img_float = target_img.astype(np.float32)
                face_bgr_for_alpha_float = face_bgr_for_alpha.astype(np.float32)

                for c_idx in range(3):
                    output_img_float[:,:,c_idx] = (alpha_s * face_bgr_for_alpha_float[:,:,c_idx]) + \
                                              ((1 - alpha_s) * output_img_float[:,:,c_idx]) # استفاده از output_img_float برای بخش (1-alpha)
                output_img = np.clip(output_img_float, 0, 255).astype(np.uint8)
        
        swapped_path = f"swapped_advanced_{user_id}.jpg"
        cv2.imwrite(swapped_path, output_img)
        print(f"عکس ترکیب شده با موفقیت در {swapped_path} ذخیره شد.", flush=True)
        return swapped_path

    except Exception as e:
        print(f"خطای عمومی استثنا در do_advanced_face_swap برای کاربر {user_id}: {e}", flush=True)
        error_details = traceback.format_exc()
        print(error_details, flush=True)
        # ... (ارسال لاگ خطا مانند قبل) ...
        return None

# ... (کدهای @app.on_message و راه‌اندازی ربات مانند قبل باقی می‌مانند) ...
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

    download_dir = "temp_photos" 
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    file_name = f"{download_dir}/user_{user_id}_photo_{message.photo.file_unique_id}.jpg"
    photo_path = await message.download(file_name=file_name)
    
    if not photo_path or not os.path.exists(photo_path):
        await message.reply("مشکلی در دانلود عکس رخ داد. لطفاً دوباره تلاش کنید.")
        return
    try:
        img_check = cv2.imread(photo_path)
        if img_check is None:
            await message.reply("عکس دریافت شده قابل پردازش نیست. لطفاً عکس دیگری ارسال کنید.")
            if os.path.exists(photo_path): os.remove(photo_path) 
            if user_id in user_photos and user_photos[user_id].get("face") == photo_path : user_photos[user_id]["face"] = None
            return
    except Exception as e_cv_read:
        await message.reply("خطایی در پردازش اولیه عکس رخ داد.")
        if os.path.exists(photo_path): os.remove(photo_path)
        if user_id in user_photos and user_photos[user_id].get("face") == photo_path : user_photos[user_id]["face"] = None
        return

    if user_photos[user_id]["face"] is None:
        user_photos[user_id]["face"] = photo_path
        await message.reply("عکس چهره دریافت شد. حالا عکسی را بفرستید که می‌خواهید چهره روی آن قرار بگیرد.")
    else:
        user_photos[user_id]["target"] = photo_path
        
        face_file_to_check = user_photos[user_id]["face"]
        if not face_file_to_check or not os.path.exists(face_file_to_check):
            await message.reply("مشکلی در دسترسی به عکس اولیه چهره رخ داد. لطفاً با /start مجدداً شروع کنید.")
            if user_id in user_photos: del user_photos[user_id] 
            return
        
        img_check_face = cv2.imread(face_file_to_check)
        if img_check_face is None:
            await message.reply("عکس اولیه چهره قابل پردازش نیست. لطفاً با /start مجدداً شروع کنید و عکس واضح‌تری ارسال کنید.")
            if os.path.exists(face_file_to_check): os.remove(face_file_to_check)
            if user_id in user_photos: del user_photos[user_id]
            return

        processing_msg = await message.reply("در حال انجام Face Swap پیشرفته... (استفاده از تطبیق هیستوگرام و Seamless Cloning)")
        
        swapped_path = await do_advanced_face_swap(user_id, user_photos[user_id]["face"], user_photos[user_id]["target"])
        
        if swapped_path is None:
            await processing_msg.edit_text("متأسفانه در پردازش مشکلی رخ داد. لطفاً از واضح بودن چهره‌ها در هر دو عکس اطمینان حاصل کنید و دوباره تلاش کنید.")
        else:
            try:
                await message.reply_photo(swapped_path, caption="چهره با موفقیت جایگزین شد!")
            except Exception as e_send:
                await message.reply("خطایی در ارسال عکس نتیجه رخ داد. فایل در سرور پردازش شده است.")
            finally: 
                if os.path.exists(swapped_path): os.remove(swapped_path)

        # پاک کردن فایل‌های موقت
        for key in ["face", "target"]:
            file_to_delete = user_photos[user_id].get(key)
            if file_to_delete and os.path.exists(file_to_delete):
                try:
                    os.remove(file_to_delete)
                except Exception as e_del:
                    print(f"خطا در پاک کردن فایل موقت '{file_to_delete}': {e_del}", flush=True)
        
        if user_id in user_photos:
            del user_photos[user_id]

if __name__ == "__main__":
    print("ربات در حال اجرا است...", flush=True)
    if not os.path.exists("logs"): os.makedirs("logs")
    if not os.path.exists("temp_photos"): os.makedirs("temp_photos")
    print(f"cv2 version: {cv2.__version__}", flush=True)
    print(f"face_recognition version: {face_recognition.__version__}", flush=True)
    app.run()
