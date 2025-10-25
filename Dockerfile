FROM python:3.9-slim

# نصب ابزار ffmpeg
# این خود برنامه ffmpeg هست که کتابخونه پایتون ازش استفاده می‌کنه
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# تنظیم مسیر کاری
WORKDIR /app

# کپی کردن فایل نیازمندی‌ها
COPY requirements.txt /app/

# نصب کتابخانه‌های پایتون
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن بقیه پروژه
COPY . /app

# اجرای برنامه اصلی
CMD ["python", "bot.py"]
