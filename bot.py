from pyrogram import Client, filters
import os, time, asyncio, subprocess, requests

# فقط این خط رو عوض کن (توکنی که با گوشی گرفتی رو اینجا بذار)
REFRESH_TOKEN = "1//04xY... اینجا توکنت رو بذار ..."

def get_access_token():
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": "639995293542-jppkvbshu1eo4ueh4m78l61kahdtkh0l.apps.googleusercontent.com",
        "client_secret": "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z9",
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    r = requests.post(url, data=data).json()
    return r["access_token"]

def upload_to_drive(file_path):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # شروع آپلود
    metadata = {"name": os.path.basename(file_path)}
    res = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
        headers=headers, json=metadata
    )
    upload_url = res.headers["Location"]
    
    # آپلود فایل
    with open(file_path, "rb") as f:
        requests.put(upload_url, headers={"Content-Type": "video/mp4"}, data=f)
    
    # گرفتن آیدی فایل
    file_id = requests.get("https://www.googleapis.com/drive/v3/files?q=name='" + os.path.basename(file_path) + "'", headers=headers).json()["files"][0]["id"]
    
    # عمومی کردن
    requests.post(f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions", headers=headers, json={"role": "reader", "type": "anyone"})
    
    return f"https://drive.google.com/file/d/{file_id}/view"

# ================= ربات تلگرام =================
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '1943275919:AAGldhig163Xa2RwoGf3pa6MFt2EGqJqLdU'

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def progress(current, total, msg, start):
    if time.time() - start > 1:
        try:
            await msg.edit_text(f"در حال دانلود... {(current/total)*100:.1f}%")
        except: pass

@app.on_message(filters.video & filters.private)
async def video_handler(c, m):
    status = await m.reply("در حال دانلود ویدیو...")
    start = time.time()
    
    file_path = await m.download_media(progress=progress, progress_args=(status, start))
    
    await status.edit("در حال تبدیل به 720p...")
    output = "output.mp4"
    subprocess.run(f'ffmpeg -i "{file_path}" -vf "scale=-2:720" -c:v libx264 -preset fast -c:a aac -y "{output}"', shell=True)
    
    await status.edit("در حال آپلود به گوگل درایو...")
    link = upload_to_drive(output)
    
    await status.edit(f"تموم شد!\n\nلینک دانلود:\n{link}")
    
    # پاک کردن فایل‌ها
    os.remove(file_path); os.remove(output)

app.run()
