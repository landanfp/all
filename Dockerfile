
FROM python:3.10

# 

# ساخت دایرکتوری اپ
WORKDIR /app

# کپی فایل‌های پروژه به داخل کانتینر
COPY . /app

# نصب وابستگی‌ها
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg

# باز کردن پورت (اختیاری، مثلا اگه یه API داری)
# EXPOSE 8000

# اجرای برنامه
CMD ["python", "main.py"]

