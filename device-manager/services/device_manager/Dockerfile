# device-manager/Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    udev \
    libv4l-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and config
COPY device_manager.py .
COPY config/ ./config/

# Create directory for recordings
RUN mkdir -p /data/recordings

# Run with privileged access for USB devices
CMD ["python", "device_manager.py"]