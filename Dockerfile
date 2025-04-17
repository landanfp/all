FROM python:3.9-slim

# نصب ابزارهای مورد نیاز
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
RUN pip install moviepy==1.0.3 imageio-ffmpeg==0.4.5

# نصب سایر وابستگی‌ها
RUN pip install --no-cache-dir -r requirements.txt

# تست نصب moviepy (اختیاری ولی مفیده برای لاگ)
RUN python -c "from moviepy.editor import VideoFileClip; print('MoviePy installed successfully.')"

# اجرای برنامه اصلی
CMD ["python3", "bot.py"]
