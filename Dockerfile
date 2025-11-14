# استفاده از Alpine Linux برای تضمین یک محیط کوچک و پایدار
FROM python:3.10-alpine

# نصب ابزارهای مورد نیاز از طریق apk (مدیر پکیج Alpine)
# FFmpeg از apk، و build deps برای numpy/pillow/MoviePy
RUN apk add --no-cache \
    ffmpeg \
    imagemagick \
    ttf-dejavu \
    # Build deps برای pip install (numpy, pillow)
    && apk add --no-cache --virtual .build-deps \
        gcc \
        g++ \
        musl-dev \
        zlib-dev \
        jpeg-dev \
        libffi-dev \
    # Clean cache
    && rm -rf /var/cache/apk/*

# تنظیم مسیر کاری
WORKDIR /app

# کپی requirements اول (برای cache Docker layers)
COPY requirements.txt .

# نصب MoviePy و وابستگی‌ها (با build deps)
RUN pip install --upgrade pip
# فیکس: Pillow 9.x برای سازگاری با MoviePy 1.0.3
RUN pip install --no-cache-dir pillow==9.5.0
RUN pip install --no-cache-dir moviepy==1.0.3
RUN pip install --no-cache-dir -r requirements.txt

# Clean up build deps (image کوچیک‌تر)
RUN apk del .build-deps

# کپی بقیه پروژه
COPY . /app

# تنظیم ENV برای MoviePy (استفاده از system FFmpeg) و لاگ‌ها
ENV FFMPEG_BINARY=ffmpeg
ENV PYTHONUNBUFFERED=1

# تست نصب moviepy (فیکس: import بدون instantiation + چک FFmpeg)
RUN python -c "from moviepy.editor import VideoFileClip; print('MoviePy imported successfully.')" \
    && ffmpeg -version > /dev/null 2>&1 \
    && echo "FFmpeg OK." \
    || (echo "FFmpeg failed!" && exit 1)

# اجرای برنامه اصلی
CMD ["python", "bot.py"]
