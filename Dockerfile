# Base image
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install dependencies
RUN apt update && apt install -y ffmpeg && \
    pip install --no-cache-dir --upgrade pip

# Copy project files
COPY . .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Start the bot
CMD ["python", "bot.py"]
