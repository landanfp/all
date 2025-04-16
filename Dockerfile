FROM python:3.9-slim

# نصب وابستگی‌های سیستمی موردنیاز
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    libx11-6 \
    libxext6 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

# تنظیم پوشه کاری
WORKDIR /app

# کپی فایل‌های پروژه
COPY . /app

# نصب وابستگی‌های پایتون
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# اجرای برنامه
CMD ["python", "media_bot_project.py"]
