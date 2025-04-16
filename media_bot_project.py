
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
from PIL import Image
import os
import shutil
from pyrogram.types import InputMediaVideo
#import ffmpeg
api_id = "3335796"  # جایگزین کنید با api_id خود
api_hash = "138b992a0e672e8346d8439c3f42ea78"  # جایگزین کنید با api_hash خود
bot_token = "7136875110:AAFzyr2i2FbRrmst1sklkJPN7Yz2rXJvSew"  # جایگزین کنید با bot_token خود

app = Client("media_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)


# مسیر ذخیره فایل‌ها در سرور
UPLOAD_FOLDER = "uploads/"

# اطمینان از وجود پوشه ذخیره‌سازی
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# تابع برای دانلود فایل‌ها از تلگرام
async def download_file(file_id, file_name):
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    file = await app.download_media(file_id, file_path)
    return file_path

# تابع برای حذف فایل‌ها بعد از پردازش
def remove_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

# تابع تبدیل صدا به متن
def audio_to_text(audio_file):
    # اینجا می‌توانید الگوریتم تبدیل صدا به متن را قرار دهید
    return "متن استخراج شده از صدا"

# تابع تبدیل متن به صدا
def text_to_audio(text, output_file="output_audio.mp3"):
    # تبدیل متن به صدا و ذخیره آن
    from gtts import gTTS
    tts = gTTS(text)
    tts.save(output_file)
    return output_file

# تابع برش صدا
def cut_audio(audio_file, start_time, end_time, output_file="cut_audio.mp3"):
    from pydub import AudioSegment
    audio = AudioSegment.from_mp3(audio_file)
    cut_audio = audio[start_time * 1000:end_time * 1000]  # میلی‌ثانیه
    cut_audio.export(output_file, format="mp3")
    return output_file

# تابع ادغام صدا
def merge_audio(audio_files, output_file="merged_audio.mp3"):
    from pydub import AudioSegment
    merged_audio = AudioSegment.empty()
    for audio_file in audio_files:
        audio = AudioSegment.from_mp3(audio_file)
        merged_audio += audio
    merged_audio.export(output_file, format="mp3")
    return output_file

# تابع تبدیل ویدیو به صدا
def video_to_audio(video_file, output_file="video_audio.mp3"):
    video = VideoFileClip(video_file)
    audio = video.audio
    audio.write_audiofile(output_file)
    return output_file

# تابع برش ویدیو
def cut_video(video_file, start_time, end_time, output_file="cut_video.mp4"):
    video = VideoFileClip(video_file).subclip(start_time, end_time)
    video.write_videofile(output_file, codec="libx264")
    return output_file

# تابع زیپ کردن فایل‌ها
def zip_files(files, output_file="files.zip"):
    import zipfile
    with zipfile.ZipFile(output_file, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return output_file

# تابع افزودن زیرنویس به ویدیو
def add_subtitles_to_video(video_file, subtitles_file, output_file="video_with_subtitles.mp4"):
    from moviepy.editor import TextClip, CompositeVideoClip
    video = VideoFileClip(video_file)
    subtitles = TextClip(subtitles_file, fontsize=24, color='white')
    subtitles = subtitles.set_pos('bottom').set_duration(video.duration)
    video_with_subtitles = CompositeVideoClip([video, subtitles])
    video_with_subtitles.write_videofile(output_file, codec="libx264")
    return output_file

# تابع ادغام ویدیوها
def merge_videos(video_files, output_file="merged_video.mp4"):
    video_clips = [VideoFileClip(file) for file in video_files]
    final_video = concatenate_videoclips(video_clips)
    final_video.write_videofile(output_file, codec="libx264")
    return output_file

# تابع افزودن صدا به ویدیو
def add_audio_to_video(video_file, audio_file, output_file="video_with_audio.mp4"):
    video = VideoFileClip(video_file)
    audio = AudioFileClip(audio_file)
    
    if audio.duration < video.duration:
        audio = audio.fx(vfx.loop, duration=video.duration)
    
    video_with_audio = video.set_audio(audio)
    video_with_audio.write_videofile(output_file, codec="libx264")
    return output_file

# تابع گرفتن اسکرین‌شات از ویدیو
def take_screenshot_from_video(video_file, time=1, output_file="screenshot.jpg"):
    video = VideoFileClip(video_file)
    screenshot = video.get_frame(time)  # زمان به ثانیه
    image = Image.fromarray(screenshot)
    image.save(output_file)
    return output_file

# پیام خوشامدگویی
@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("تبدیل صدا به ویس", callback_data="audio_to_speech"),
         InlineKeyboardButton("تبدیل ویس به صدا", callback_data="speech_to_audio")],
        [InlineKeyboardButton("برش صدا", callback_data="audio_cut"),
         InlineKeyboardButton("اذغام صدا", callback_data="audio_merge")],
        [InlineKeyboardButton("تبدیل ویدیو به صدا", callback_data="video_to_audio"),
         InlineKeyboardButton("زیپ کردن فایل‌ها", callback_data="zip_files")],
        [InlineKeyboardButton("برش ویدیو", callback_data="video_cut"),
         InlineKeyboardButton("افزودن زیرنویس به ویدیو", callback_data="add_subtitles")],
        [InlineKeyboardButton("اذغام ویدیوها", callback_data="merge_videos"),
         InlineKeyboardButton("افزودن صدا به ویدیو", callback_data="add_audio_to_video")],
        [InlineKeyboardButton("گرفتن اسکرین شات", callback_data="take_screenshot")]
    ])
    await message.reply("به ربات خوش آمدید! انتخاب کنید که می‌خواهید چه کاری انجام دهید:", reply_markup=keyboard)

# مدیریت دکمه‌ها
@app.on_callback_query(filters.regex("audio_to_text"))
async def handle_audio_to_text(client, callback_query):
    await callback_query.answer("لطفا فایل صوتی ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل صوتی شما هستم.")
    await message.edit_text("لطفا فایل صوتی خود را ارسال کنید.")

@app.on_callback_query(filters.regex("text_to_audio"))
async def handle_text_to_audio(client, callback_query):
    await callback_query.answer("لطفا متن خود را ارسال کنید.")
    message = await callback_query.message.reply("منتظر متن شما هستم.")
    await message.edit_text("لطفا متن خود را ارسال کنید.")

@app.on_callback_query(filters.regex("cut_audio"))
async def handle_cut_audio(client, callback_query):
    await callback_query.answer("لطفا فایل صوتی و زمان شروع و پایان را ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل صوتی شما هستم.")

@app.on_callback_query(filters.regex("merge_audio"))
async def handle_merge_audio(client, callback_query):
    await callback_query.answer("لطفا فایل‌های صوتی برای ادغام ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل‌های صوتی شما هستم.")

@app.on_callback_query(filters.regex("video_to_audio"))
async def handle_video_to_audio(client, callback_query):
    await callback_query.answer("لطفا فایل ویدیویی ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل ویدیویی شما هستم.")

@app.on_callback_query(filters.regex("cut_video"))
async def handle_cut_video(client, callback_query):
    await callback_query.answer("لطفا فایل ویدیویی و زمان شروع و پایان را ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل ویدیویی شما هستم.")

@app.on_callback_query(filters.regex("zip_files"))
async def handle_zip_files(client, callback_query):
    await callback_query.answer("لطفا فایل‌ها را برای زیپ کردن ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل‌های شما هستم.")

@app.on_callback_query(filters.regex("add_subtitles"))
async def handle_add_subtitles(client, callback_query):
    await callback_query.answer("لطفا فایل ویدیویی و فایل زیرنویس ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل‌های شما هستم.")

@app.on_callback_query(filters.regex("merge_videos"))
async def handle_merge_videos(client, callback_query):
    await callback_query.answer("لطفا فایل‌های ویدیویی برای ادغام ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل‌های ویدیویی شما هستم.")

@app.on_callback_query(filters.regex("add_audio_to_video"))
async def handle_add_audio_to_video(client, callback_query):
    await callback_query.answer("لطفا فایل ویدیویی و فایل صوتی ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل‌های شما هستم.")

@app.on_callback_query(filters.regex("take_screenshot"))
async def handle_take_screenshot(client, callback_query):
    await callback_query.answer("لطفا فایل ویدیویی ارسال کنید.")
    message = await callback_query.message.reply("منتظر فایل ویدیویی شما هستم.")

# مدیریت دریافت فایل‌ها
@app.on_message(filters.video)
async def handle_video(client, message):
    video_file_path = await download_file(message.video.file_id, "video.mp4")
    # انجام عملیات مربوط به ویدیو (برش، تبدیل، ویدیو به صدا و ...)
    # پس از انجام عملیات، فایل ویدیو حذف می‌شود
    remove_file(video_file_path)

@app.on_message(filters.audio)
async def handle_audio(client, message):
    audio_file_path = await download_file(message.audio.file_id, "audio.mp3")
    # انجام عملیات مربوط به صدا (برش، ادغام، تبدیل صدا به متن و ...)
    # پس از انجام عملیات، فایل صوتی حذف می‌شود
    remove_file(audio_file_path)

# شروع ربات
app.run()
