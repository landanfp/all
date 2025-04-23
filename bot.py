import os, time, subprocess
from threading import Lock
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient

# Configuration
BOT_TOKEN = '6964975788:AAH3OrL9aXHuoIUliY6TJbKqTeR__X5p4H8'
LOG_CHANNEL = -1001234567890  # مقدار دلخواه وارد کن
MONGO_URI = 'mongodb+srv://abirhasan2005:abirhasan@cluster0.i6qzp.mongodb.net/cluster0?retryWrites=true&w=majority'
API_ID = 3335796
API_HASH = '138B992A0E672E8346D8439C3F42EA78'

# Initialize MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database()
progress_col = db["progress"]

# Prepare local storage
os.makedirs("downloads", exist_ok=True)
sessions = {}
lock = Lock()

# Progress logging
def log_progress(chat_id, file_id, downloaded, total, speed, eta):
    print(f"[LOG] Progress - chat_id: {chat_id}, file_id: {file_id}, downloaded: {downloaded}, total: {total}, speed: {speed:.2f}, eta: {eta:.2f}")
    doc = {
        "chat_id": chat_id,
        "file_id": file_id,
        "timestamp": int(time.time()),
        "downloaded": downloaded,
        "total": total,
        "speed": speed,
        "eta": eta
    }
    with lock:
        progress_col.insert_one(doc)

# Format progress bar
def fmt(d, t, s, e):
    p = d/t*100 if t else 0
    f = int(20 * (d/t)) if t else 0
    b = "█"*f + "—"*(20-f)
    return f"|{b}| {p:.1f}%\n{d}/{t} bytes\nSpeed: {s:.1f} B/s\nETA: {e:.1f}s"

# Callback for download/upload progress
def progress_cb(d, t, client, msg, uid, fid):
    elapsed = time.time() - sessions[uid]["dl_start"]
    speed   = d/elapsed if elapsed > 0 else 0
    eta     = (t-d)/speed if speed > 0 else 0
    print(f"[DEBUG] Progress callback - Downloaded: {d}, Total: {t}, Speed: {speed:.2f}, ETA: {eta:.2f}")
    client.edit_message_text(uid, msg.message_id, fmt(d, t, speed, eta))
    log_progress(uid, fid, d, t, speed, eta)

VIDEO, SV, EV, AUDIO, SA, EA = range(6)
app = Client("trim", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start_cmd(c, m):
    print(f"[INFO] /start by {m.from_user.id}")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("برش ویدیو", callback_data="cut_video")],
        [InlineKeyboardButton("برش صدا", callback_data="cut_audio")]
    ])
    await m.reply("گزینه‌ای را انتخاب کنید:", reply_markup=kb)

@app.on_callback_query(filters.regex("cut_video"))
async def cut_video(c, q):
    print(f"[INFO] cut_video clicked by {q.from_user.id}")
    await q.answer()
    msg = await q.message.reply("لطفا ویدیو ارسال کنید.")
    sessions[q.from_user.id] = {"state": VIDEO, "msg": msg}

@app.on_callback_query(filters.regex("cut_audio"))
async def cut_audio(c, q):
    print(f"[INFO] cut_audio clicked by {q.from_user.id}")
    await q.answer()
    msg = await q.message.reply("لطفا فایل صوتی ارسال کنید.")
    sessions[q.from_user.id] = {"state": AUDIO, "msg": msg}

@app.on_message(filters.video | filters.audio | filters.document)
async def recv_media(c, m: Message):
    u = m.from_user.id
    s = sessions.get(u)
    if not s: return
    st = s["state"]
    fn = (m.video or m.audio or m.document).file_name
    print(f"[INFO] Received media from {u}, filename: {fn}")
    ext = fn.rsplit('.', 1)[-1].lower()
    if st == VIDEO and ext not in ["mp4", "mkv"] or st == AUDIO and ext not in ["mp3", "wav", "m4a", "ogg"]:
        await m.reply("این فایل پشتیبانی نمی‌شود")
        return
    dur = (m.video.duration if m.video else m.audio.duration) if (m.video or m.audio) else 0
    main = await m.reply(f"{dur}\n-\n-")
    s.update({
        "state": SV if st == VIDEO else SA,
        "media": m,
        "main": main,
        "dur": dur
    })
    pm = await m.reply("تایم شروع را ارسال کن")
    s["pm"] = pm

@app.on_message(filters.text)
async def recv_time(c, m: Message):
    u, s = m.from_user.id, sessions.get(m.from_user.id)
    if not s: return
    st = s["state"]
    print(f"[INFO] Received time input from {u}, text: {m.text}")
    if st in (SV, SA):
        s["start"] = float(m.text)
        await s["main"].edit(
            f"{s['dur']}\n{s['start']}\n-",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("شروع", callback_data="start_cut")]])
        )
        await m.delete(); await s["pm"].delete()
        ep = await m.reply("حالا تایم پایان را ارسال کن")
        s.update({"state": EV if st == SV else EA, "pm": ep})
    elif st in (EV, EA):
        s["end"] = float(m.text)
        await s["main"].edit(
            f"{s['dur']}\n{s['start']}\n{s['end']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("شروع", callback_data="start_cut")]])
        )
        await m.delete(); await s["pm"].delete()

@app.on_callback_query(filters.regex("start_cut"))
async def start_cut(c, q):
    u = q.from_user.id
    s = sessions[u]
    m = s["media"]
    mm = s["main"]
    st, sd, ed = s["state"], s["start"], s["end"]
    fid = (m.video or m.audio or m.document).file_id
    ext = "mp4" if st == EV else "mp3"
    inp = f"downloads/{fid}.{ext}"
    out = f"downloads/{fid}_cut.{ext}"
    s["dl_start"] = time.time()

    print(f"[INFO] Starting download for user {u}, file_id: {fid}")
    await c.download_media(m, file_name=inp, progress=lambda d, t: progress_cb(d, t, c, mm, u, fid))
    print(f"[INFO] Download complete. Starting cut: {inp} -> {out}")
    subprocess.run(["ffmpeg", "-y", "-i", inp, "-ss", str(sd), "-to", str(ed), "-c", "copy", out],
                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    send = c.send_video if st == EV else c.send_audio
    print(f"[INFO] Uploading cut file to user {u}")
    await send(u, video=out if st == EV else None, audio=out if st == EA else None,
               progress=lambda d, t: progress_cb(d, t, c, mm, u, fid))

    print(f"[INFO] Upload complete. Cleaning up files.")
    os.remove(inp)
    os.remove(out)
    await c.send_message(LOG_CHANNEL, f"{u} cut {'video' if st == EV else 'audio'} {fid} ({sd}-{ed})")
    sessions.pop(u)

app.run()
