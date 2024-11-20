from typing import Callable, List, Tuple
from models import VideoMetadata, ProcessingResult

def video_processing_queue(
    tasks: List[Tuple[Callable[[VideoMetadata], ProcessingResult], VideoMetadata]]
) -> List[ProcessingResult]:
    results = []
    for func, video in tasks:
        print(f"Processing {video.title} with {func.__name__}...")
        result = func(video)
        results.append(result)
    return results