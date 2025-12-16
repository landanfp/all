import requests
import os
import time
import hashlib
import hmac

# اطلاعات اپلیکیشنت (همین‌هایی که دادی)
ACCESS_TOKEN = "-nIMRgTZCuU2hYBWIEn0IlBkvowUXZvgoiD8RaFFtxcOYMinTvspwiNLdXVg4swGgqSW68"
APP_ID = "512004689293"
SECRET_KEY = "6B885C7A402C8EC353638176"          # Secret Key
SESSION_SECRET_KEY = "4ee5aa4b9721d1797c439344b9a77825"  # Session secret key
APP_KEY = "COIOIMNGDIHBABABA"  # اگر داشتی، اینجا بذار (اختیاری، معمولاً لازم نیست)

def sign_request(params):
    """امضای درخواست برای متدهایی که sig لازم دارن (اختیاری)"""
    param_str = ''.join([k + '=' + str(v) for k, v in sorted(params.items())])
    sig_str = param_str + SECRET_KEY
    return hashlib.md5(sig_str.encode('utf-8')).hexdigest()

def get_upload_url():
    """گرفتن URL آپلود از OK.ru"""
    params = {
        "application_key": APP_KEY,
        "method": "video.getUploadUrl",
        "access_token": ACCESS_TOKEN,
        "format": "json"
    }
    # بعضی وقت‌ها sig لازم می‌شه
    params["sig"] = sign_request(params)

    response = requests.get("https://api.ok.ru/fb.do", params=params)
    data = response.json()

    if "error_code" in data:
        print("خطا در گرفتن URL آپلود:")
        print(data)
        return None, None

    return data["upload_url"], data["video_id"]

def upload_video(video_path, upload_url):
    """آپلود مستقیم ویدیو به URL دریافت‌شده"""
    if not os.path.exists(video_path):
        print(f"فایل پیدا نشد: {video_path}")
        return False

    print(f"در حال آپلود: {video_path} ...")
    files = {"file": open(video_path, "rb")}
    upload_response = requests.post(upload_url, files=files)

    if upload_response.status_code == 200:
        print("ویدیو با موفقیت آپلود شد!")
        return True
    else:
        print("خطا در آپلود:")
        print(upload_response.text)
        return False

def make_video_public(video_id):
    """عمومی کردن ویدیو بعد از آپلود (اختیاری)"""
    params = {
        "application_key": APP_KEY,
        "method": "video.update",
        "video_id": video_id,
        "status": "public",  # public, friends, private
        "access_token": ACCESS_TOKEN,
        "format": "json"
    }
    params["sig"] = sign_request(params)

    response = requests.get("https://api.ok.ru/fb.do", params=params)
    result = response.json()
    print("وضعیت به‌روزرسانی ویدیو:", result)

def upload_ok(video_file_path):
    """تابع اصلی ربات - فقط یک ویدیو آپلود می‌کنه"""
    print("در حال دریافت URL آپلود از OK.ru...")
    upload_url, video_id = get_upload_url()

    if not upload_url or not video_id:
        return

    print(f"Video ID موقت: {video_id}")

    if upload_video(video_file_path, upload_url):
        print("در حال عمومی کردن ویدیو...")
        time.sleep(5)  # کمی صبر تا پردازش اولیه
        make_video_public(video_id)
        print(f"ویدیو با موفقیت در پروفایلت آپلود شد! ID: {video_id}")
        print(f"لینک تقریبی: https://ok.ru/video/{video_id}")

# ========================
# نحوه استفاده
# ========================

if __name__ == "__main__":
    # مسیر ویدیویی که می‌خوای آپلود کنی (در همان فولدر یا مسیر کامل)
    video_path = "test_video.mp4"  # <-- اسم فایل خودت رو اینجا عوض کن

    upload_ok(video_path)
