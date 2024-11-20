from submodules.auto_fix_mobile import auto_fix_mobile_portrait
from submodules.apply_portrait import apply_portrait_in_landscape
from submodules.processing_queue import video_processing_queue
from models import VideoMetadata

def main():
    # Example: Video to process
    video = VideoMetadata(
        video_id="12345",
        title="Test Video",
        input_path="/path/to/video.mp4",
        resolution="1920x1080",
        duration=120.0,
    )

    # Process video
    queue = [
        (auto_fix_mobile_portrait, video),
        (apply_portrait_in_landscape, video),
    ]

    results = video_processing_queue(queue)

    for result in results:
        print(f"Processing result: {result}")

if __name__ == "__main__":
    main()