FROM python:3.9-slim

# نصب پکیج‌های سیستمی مورد نیاز
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

# نمایش محتویات پوشه برای دیباگ
RUN ls -l /app

# نصب پکیج‌ها + نمایش وضعیت moviepy
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip show moviepy || (echo "moviepy نصب نشد!" && exit 1)

# اجرای برنامه
CMD ["python", "media_bot_project.py"]
