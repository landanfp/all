# استفاده از پایتون نسخه 3.9 به عنوان پایه
FROM python:3.9-slim

# نصب ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# تنظیم پوشه کاری
WORKDIR /app

# کپی کردن تمام فایل‌ها به داخل کانتینر
COPY . /app

# نصب وابستگی‌ها
RUN pip install --no-cache-dir -r requirements.txt

# اجرای فایل اصلی پروژه
CMD ["python", "media_bot_project.py"]
