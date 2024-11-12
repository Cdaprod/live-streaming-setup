#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define image names
RTMP_SERVER_IMAGE=cdaprod/rtmp-server:latest
FFMPEG_STREAMER_IMAGE=cdaprod/ffmpeg-streamer:latest

# Build RTMP Server image
echo "Building RTMP Server image..."
docker build -t $RTMP_SERVER_IMAGE ./rtmp-server

# Build FFmpeg Streamer image
echo "Building FFmpeg Streamer image..."
docker build -t $FFMPEG_STREAMER_IMAGE ./ffmpeg-streamer

# Push images to local registry
echo "Pushing RTMP Server image to cdaprod..."
docker push $RTMP_SERVER_IMAGE

echo "Pushing FFmpeg Streamer image to cdaprod..."
docker push $FFMPEG_STREAMER_IMAGE

echo "Build and push completed successfully."