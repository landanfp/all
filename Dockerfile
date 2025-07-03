# Use official Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot script and watermark images
COPY bot.py .
COPY 1.jpg .
COPY 2.jpg .

# Command to run the bot
CMD ["python", "bot.py"]
