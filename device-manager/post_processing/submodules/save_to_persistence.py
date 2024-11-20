from datetime import datetime

def save_to_persistent(video: VideoMetadata, base_dir: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    output_path = Path(base_dir) / date / video.title
    output_path.mkdir(parents=True, exist_ok=True)
    return str(output_path / f"{video.video_id}.mp4")