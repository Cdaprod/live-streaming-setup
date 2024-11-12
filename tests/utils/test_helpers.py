# tests/utils/test_helpers.py
import asyncio
import ffmpeg
import tempfile
import os
from pathlib import Path

class StreamSimulator:
    """Helper class to simulate various stream sources"""
    
    def __init__(self, rtmp_url: str):
        self.rtmp_url = rtmp_url
        self.processes = {}

    async def start_test_stream(self, stream_key: str, video_file: str):
        """Start a test stream using FFmpeg"""
        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-re',
            '-i', video_file,
            '-c', 'copy',
            '-f', 'flv',
            f'{self.rtmp_url}/{stream_key}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.processes[stream_key] = process
        return process

    async def stop_test_stream(self, stream_key: str):
        """Stop a test stream"""
        if stream_key in self.processes:
            process = self.processes[stream_key]
            process.terminate()
            await process.wait()
            del self.processes[stream_key]

    @staticmethod
    async def create_test_video(duration: int = 10):
        """Create a test video file"""
        temp_dir = Path(tempfile.gettempdir())
        output_file = temp_dir / "test_video.mp4"
        
        # Create test video using FFmpeg
        await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'testsrc=duration={duration}:size=1920x1080:rate=30',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            str(output_file)
        )
        
        return str(output_file)

class RecordingValidator:
    """Helper class to validate recordings"""
    
    @staticmethod
    def get_video_info(file_path: str) -> dict:
        """Get video file information"""
        probe = ffmpeg.probe(file_path)
        return {
            'duration': float(probe['format']['duration']),
            'size': int(probe['format']['size']),
            'bitrate': int(probe['format']['bit_rate']),
            'format': probe['format']['format_name'],
            'video_codec': next(s['codec_name'] for s in probe['streams'] if s['codec_type'] == 'video'),
            'resolution': f"{probe['streams'][0]['width']}x{probe['streams'][0]['height']}"
        }

    @staticmethod
    def validate_recording(file_path: str, expected_duration: int) -> bool:
        """Validate a recording meets expected criteria"""
        info = RecordingValidator.get_video_info(file_path)
        return (
            abs(info['duration'] - expected_duration) < 1.0 and
            info['video_codec'] == 'h264' and
            info['bitrate'] > 2000000  # Minimum 2 Mbps
        )