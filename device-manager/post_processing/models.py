from dataclasses import dataclass
from typing import Optional, List

@dataclass
class VideoMetadata:
    video_id: str
    title: str
    input_path: str
    output_path: Optional[str] = None
    resolution: Optional[str] = None
    duration: Optional[float] = None

@dataclass
class ProcessingResult:
    success: bool
    message: str
    output_path: Optional[str] = None
    errors: Optional[List[str]] = None