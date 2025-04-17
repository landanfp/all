# استفاده از تصویر پایه Python
FROM python:3.9-slim

# تنظیم کار دایرکتوری در کانتینر
WORKDIR /app

# کپی کردن requirements.txt به کانتینر
COPY requirements.txt .

# نصب وابستگی‌ها
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن فایل‌های ربات به کانتینر
COPY . .

# تنظیم فرمان اجرا
CMD ["python3", "bot.py"]
