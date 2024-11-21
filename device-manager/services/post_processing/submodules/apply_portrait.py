from models import VideoMetadata, ProcessingResult

def apply_portrait_in_landscape(video: VideoMetadata) -> ProcessingResult:
    try:
        print(f"Applying portrait in landscape for {video.title}...")
        output_path = video.input_path.replace(".mp4", "_landscape.mp4")
        # Perform actual processing here (e.g., FFmpeg resizing and padding)
        return ProcessingResult(
            success=True,
            message="Portrait applied in landscape.",
            output_path=output_path,
        )
    except Exception as e:
        return ProcessingResult(
            success=False,
            message="Failed to apply portrait in landscape.",
            errors=[str(e)],
        )