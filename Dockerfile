# استفاده از Debian 10 (Buster) برای اطمینان از نصب FFmpeg نسخه قدیمی‌تر و پایدارتر
FROM python:3.8-slim-buster

# نصب ابزارهای مورد نیاز
# این دستور حالا باید FFmpeg نسخه 4.x را نصب کند.
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    libx11-6 \
    libxext6 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

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
