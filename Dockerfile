# استفاده از نسخه سبک پایتون
FROM python:3.10-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب پکیج‌های سیستمی لازم
RUN apt-get update && apt-get install -y \\
    git \\
    ffmpeg \\
    libgl1-mesa-glx \\
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌های پروژه به کانتینر
COPY requirements.txt .

# نصب پکیج‌های پایتون
RUN pip install --no-cache-dir -r requirements.txt

# کپی باقی فایل‌ها (مثل bot.py)
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
