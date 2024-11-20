from typing import Callable, List, Tuple
from models import VideoMetadata, ProcessingResult
import os

def video_processing_queue(
    tasks: List[Tuple[Callable[[VideoMetadata], ProcessingResult], VideoMetadata]]
) -> List[ProcessingResult]:
    results = []
    for func, video in tasks:
        print(f"Processing {video.title} with {func.__name__}...")
        result = func(video)
        results.append(result)

        # Clean up ephemeral data
        if result.success and video.input_path:
            print(f"Removing ephemeral file: {video.input_path}")
            os.remove(video.input_path)
    return results