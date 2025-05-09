# Use an official Python image as a base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set noninteractive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (OpenCV, face-recognition, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
    make \
    libgl1 \
    libglib2.0-0 \
    libgthread-2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run the application
CMD ["python", "bot.py"]
