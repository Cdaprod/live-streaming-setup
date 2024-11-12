FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    udev \
    libv4l-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app

# Copy application code
COPY device_manager.py .
COPY known_devices.json .

# Run with privileged access for USB devices
CMD ["python", "device_manager.py"]