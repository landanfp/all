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
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]

