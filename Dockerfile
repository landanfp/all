# مرحله 1: تصویر پایه
FROM python:3.11-slim

# تنظیم متغیر محیطی برای جلوگیری از خطای interactive
ENV DEBIAN_FRONTEND=noninteractive

# نصب وابستگی‌های سیستمی مورد نیاز برای ffmpeg و moviepy
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ایجاد فولدر کاری
WORKDIR /app

# کپی کردن فایل‌های پروژه
COPY . /app

# نصب وابستگی‌های پایتون
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pyrogram tgcrypto moviepy

# اجرای ربات
CMD ["python", "bot.py"]
