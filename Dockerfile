# استفاده از Alpine Linux برای تضمین یک محیط کوچک و پایدار
FROM python:3.10-alpine

# نصب ابزارهای مورد نیاز از طریق apk (مدیر پکیج Alpine)
# این کار معمولاً یک FFmpeg نسخه 4.x یا 5.x را نصب می‌کند که پایدارتر است.
RUN apk add --no-cache \
    ffmpeg \
    imagemagick \
    libx11 \
    libxext \
    libsm \
    # نیاز به این پکیج‌ها برای MoviePy و Pillow در Alpine
    ttf-dejavu \
    && rm -rf /var/cache/apk/*

# تنظیم مسیر کاری
WORKDIR /app

# کپی پروژه داخل کانتینر
COPY . /app

# نصب MoviePy و پکیج‌های مورد نیازش
RUN pip install --upgrade pip
RUN pip install moviepy==1.0.3 imageio-ffmpeg==0.5.1

# نصب سایر وابستگی‌ها
RUN pip install --no-cache-dir -r requirements.txt

# تست نصب moviepy (اختیاری ولی مفیده برای لاگ)
RUN python -c "from moviepy.editor import VideoFileClip; print('MoviePy installed successfully.')"

# اجرای برنامه اصلی
CMD ["python", "bot.py"]
