# Use a lightweight FFmpeg image
FROM jrottenberg/ffmpeg:latest

# Install any additional dependencies if needed
RUN apt-get update && apt-get install -y bash

# Copy the streaming script
COPY start_stream.sh /usr/local/bin/start_stream.sh

# Make the script executable
RUN chmod +x /usr/local/bin/start_stream.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/start_stream.sh"]