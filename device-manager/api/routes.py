from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.base_models import VideoRequest
from app.services.obs_manager import connect_to_obs, load_scenes, manage_scene
from app.services.twitch.twitch_main import get_video_on_demand
from app.services.post_processing.post_processing_main import process_video
from app.services.post_processing.submodules.save_to_persistence import save_to_persistence
from pathlib import Path

router = APIRouter()

EPHEMERAL_STORAGE = "/data/ephemeral"
PERSISTENT_STORAGE = "/data/recordings"

@router.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Service is running!"}

router = APIRouter()

@router.post("/obs/connect")
async def connect_obs():
    """Connect to OBS WebSocket."""
    try:
        connect_to_obs()
        return {"status": "Connected to OBS WebSocket"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to OBS: {e}")

@router.post("/obs/load-scenes")
async def load_obs_scenes():
    """Load scenes into OBS."""
    try:
        load_scenes()
        return {"status": "Scenes loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenes: {e}")

@router.post("/obs/manage-scene")
async def manage_obs_scene():
    """Manage OBS scene dynamically."""
    try:
        manage_scene()
        return {"status": "Scene managed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to manage scene: {e}")

@router.post("/fetch-and-process")
async def fetch_and_process(video_request: VideoRequest, background_tasks: BackgroundTasks):
    """Fetches Twitch VOD, processes it, and saves to persistence."""
    vod_id = video_request.vod_id
    output_name = video_request.output_name

    ephemeral_path = Path(EPHEMERAL_STORAGE) / f"{output_name}.mp4"
    persistent_path = Path(PERSISTENT_STORAGE) / "twitch"

    try:
        background_tasks.add_task(
            handle_video_processing, vod_id, str(ephemeral_path), str(persistent_path)
        )
        return {"message": f"Processing started for VOD ID: {vod_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_video_processing(vod_id: str, ephemeral_path: str, persistent_path: str):
    """Handles full video workflow: fetch, process, save."""
    try:
        get_video_on_demand(vod_id, ephemeral_path)
        processed_path = process_video(ephemeral_path)
        save_to_persistence(processed_path, persistent_path)
    except Exception as e:
        print(f"Error during video processing: {e}")
        
