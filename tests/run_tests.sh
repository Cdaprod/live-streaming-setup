#!/bin/bash
# tests/run_tests.sh

# Create test video if it doesn't exist
if [ ! -f "tests/assets/test_video.mp4" ]; then
    ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=30 -c:v libx264 -preset ultrafast tests/assets/test_video.mp4
fi

# Install test dependencies
pip install -r requirements-test.txt

# Run the tests
pytest -v tests/test_integration.py