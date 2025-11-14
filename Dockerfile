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
RUN pip install --no-cache-dir moviepy==1.0.3
RUN pip install --no-cache-dir -r requirements.txt

# Clean up build deps (image کوچیک‌تر)
RUN apk del .build-deps

# کپی بقیه پروژه
COPY . /app

# تنظیم ENV برای MoviePy (استفاده از system FFmpeg)
ENV FFMPEG_BINARY=ffmpeg

# تست نصب moviepy (بهبود: تست write ساده برای چک FFmpeg)
RUN python -c "from moviepy.editor import VideoFileClip; \
    clip = VideoFileClip(''); clip.close(); \
    print('MoviePy and FFmpeg installed successfully.')"

# اجرای برنامه اصلی
CMD ["python", "bot.py"]
