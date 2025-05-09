# Use an official Python image as a base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including libGL)
RUN apt-get update && apt-get install -y \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run the application
CMD ["python", "bot.py"]
