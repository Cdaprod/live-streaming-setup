import asyncio
from pathlib import Path
import subprocess

def download_vod(vod_url: str, output_path: str) -> bool:
    try:
        print(f"Downloading VOD from {vod_url} to {output_path}")
        subprocess.run(
            ["ffmpeg", "-i", vod_url, "-c", "copy", output_path],
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during download: {e}")
        return False