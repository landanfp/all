import os, time, subprocess
from threading import Lock
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient

MONGO_URI = 'mongodb+srv://abirhasan2005:abirhasan@cluster0.i6qzp.mongodb.net/cluster0?retryWrites=true&w=majority'
API_ID = '3335796'
API_HASH = '138b992a0e672e8346d8439c3f42ea78'
BOT_TOKEN = '5355055672:AAHoidc0x6nM3g2JHmb7xhWKmwGJOoKFNXY'
LOG_CHANNEL = -1001234567890  # مقدار دلخواه

app = Client("watermark_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database()
progress_col = db["progress"]

os.makedirs("downloads", exist_ok=True)
sessions = {}
lock = Lock()

def log_progress(chat_id, file_id, downloaded, total, speed, eta):
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

def fmt(d, t, s, e):
    p = d/t*100 if t else 0
    f = int(20 * (d/t)) if t else 0
    b = "█"*f + "—"*(20-f)
    return f"|{b}| {p:.1f}%\n{d}/{t} bytes\nSpeed: {s:.1f} B/s\nETA: {e:.1f}s"

def progress_cb(d, t, client, msg, uid, fid):
    elapsed = time.time() - sessions[uid]["dl_start"]
    speed = d/elapsed if elapsed > 0 else 0
    eta = (t-d)/speed if speed > 0 else 0
    client.edit_message_text(uid, msg.message_id, fmt(d, t, speed, eta))
    log_progress(uid, fid, d, t, speed, eta)

def hms_to_seconds(hms):
    try:
        parts = list(map(int, hms.strip().split(":")))
        while len(parts) < 3:
            parts.insert(0, 0)
        h, m, s = parts
        return h * 3600 + m * 60 + s
    except:
        return None

VIDEO, SV, EV, AUDIO, SA, EA = range(6)

@app.on_message(filters.command("start"))
async def start_cmd(c, m):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("برش ویدیو", callback_data="cut_video")],
        [InlineKeyboardButton("برش صدا", callback_data="cut_audio")]
    ])
    await m.reply("گزینه‌ای را انتخاب کنید:", reply_markup=kb)

@app.on_callback_query(filters.regex("cut_video"))
async def cut_video(c, q):
    await q.answer()
    msg = await q.message.reply("لطفا ویدیو ارسال کنید.")
    sessions[q.from_user.id] = {"state": VIDEO, "msg": msg}

@app.on_callback_query(filters.regex("cut_audio"))
async def cut_audio(c, q):
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
    ext = fn.rsplit('.', 1)[-1].lower()
    if st == VIDEO and ext not in ["mp4", "mkv"] or st == AUDIO and ext not in ["mp3", "wav", "m4a", "ogg"]:
        await m.reply("این فایل پشتیبانی نمی‌شود")
        return
    dur = (m.video.duration if m.video else m.audio.duration) if (m.video or m.audio) else 0
    main = await m.reply(f"{dur}s\nشروع: -\nپایان: -")
    s.update({
        "state": SV if st == VIDEO else SA,
        "media": m,
        "main": main,
        "dur": dur
    })
    pm = await m.reply("تایم شروع را به فرمت hh:mm:ss ارسال کن")
    s["pm"] = pm

@app.on_message(filters.text)
async def recv_time(c, m: Message):
    u, s = m.from_user.id, sessions.get(m.from_user.id)
    if not s: return
    st = s["state"]
    if st in (SV, SA):
        seconds = hms_to_seconds(m.text)
        if seconds is None:
            await m.reply("فرمت زمان نادرست است. لطفاً به صورت hh:mm:ss ارسال کنید.")
            return
        s["start"] = seconds
        await s["pm"].delete(); await m.delete()
        ep = await m.reply("تایم پایان را به فرمت hh:mm:ss ارسال کن")
        s.update({"state": EV if st == SV else EA, "pm": ep})
        await s["main"].edit_text(
            f"{s['dur']}s\nشروع: {m.text}\nپایان: -",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("شروع", callback_data="start_cut")]])
        )
    elif st in (EV, EA):
        seconds = hms_to_seconds(m.text)
        if seconds is None:
            await m.reply("فرمت زمان نادرست است. لطفاً به صورت hh:mm:ss ارسال کنید.")
            return
        s["end"] = seconds
        await s["pm"].delete(); await m.delete()
        await s["main"].edit_text(
            f"{s['dur']}s\nشروع: {s['start']}s\nپایان: {seconds}s",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("شروع", callback_data="start_cut")]])
        )

@app.on_callback_query(filters.regex("start_cut"))
async def start_cut(c, q):
    await q.answer()
    u = q.from_user.id
    s = sessions.get(u)
    if not s:
        await q.message.edit("جلسه‌ای برای شما پیدا نشد.")
        return
    if "start" not in s or "end" not in s:
        await q.message.edit("زمان شروع یا پایان ناقصه.")
        return
    if s["state"] not in (EV, EA):
        await q.message.edit("حالت نهایی نادرسته. لطفاً زمان‌ها رو مجدد وارد کنید.")
        return

    m = s["media"]
    mm = s["main"]
    st, sd, ed = s["state"], s["start"], s["end"]
    fid = (m.video or m.audio or m.document).file_id
    ext = "mp4" if st == EV else "mp3"
    inp = f"downloads/{fid}.{ext}"
    out = f"downloads/{fid}_cut.{ext}"
    s["dl_start"] = time.time()

    # نمایش پیشرفت دانلود
    await c.download_media(m, file_name=inp, progress=lambda d, t: progress_cb(d, t, c, mm, u, fid))
    subprocess.run(["ffmpeg", "-y", "-i", inp, "-ss", str(sd), "-to", str(ed), "-c", "copy", out],
                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    send = c.send_video if st == EV else c.send_audio
    await send(u, video=out if st == EV else None, audio=out if st == EA else None,
               progress=lambda d, t: progress_cb(d, t, c, mm, u, fid))

    os.remove(inp)
    os.remove(out)
    await c.send_message(LOG_CHANNEL, f"{u} cut {'video' if st == EV else 'audio'} {fid} ({sd}-{ed})")
    sessions.pop(u)

app.run()
