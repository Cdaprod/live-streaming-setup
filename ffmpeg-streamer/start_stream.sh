#!/bin/bash

# Environment Variables:
# ESP32_CAM_URL: The HTTP URL of the ESP32-CAM stream
# RTMP_SERVER_URL: The RTMP URL to push the stream to

# Retry logic in case of connection issues
while true; do
    echo "Starting FFmpeg stream from $ESP32_CAM_URL to $RTMP_SERVER_URL"
    ffmpeg -re -i "$ESP32_CAM_URL" -c:v copy -f flv "$RTMP_SERVER_URL"
    
    echo "FFmpeg stream ended. Restarting in 5 seconds..."
    sleep 5
done