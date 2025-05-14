# Base image
FROM python:3.10-slim

# Install ffmpeg and system dependencies
RUN apt update && apt install -y ffmpeg && apt clean

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source code
COPY . .

# Run the bot
CMD ["python", "main.py"]
