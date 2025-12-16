# استفاده از ایمیج رسمی Python سبک
FROM python:3.11-slim

# جلوگیری از بافر شدن خروجی (برای دیدن لاگ‌ها در زمان واقعی)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# نصب وابستگی‌های سیستم (اگر لازم شد)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# ایجاد کاربر غیرروت برای امنیت بیشتر
RUN adduser --disabled-password --gecos '' appuser

# تنظیم دایرکتوری کاری
WORKDIR /app

# کپی فایل‌های لازم
COPY requirements.txt .

# نصب وابستگی‌های پایتون
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد ربات و فایل‌های تنظیمات
COPY okru_telegram_bot.py .
#COPY .env .                  # اگر از .env استفاده می‌کنی (پیشنهاد می‌کنم)

# تغییر مالکیت فایل‌ها به کاربر غیرروت
RUN chown -R appuser:appuser /app

# سوئیچ به کاربر غیرروت
USER appuser

# دستور اجرا
CMD ["python", "okru_telegram_bot.py"]
