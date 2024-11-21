import os
import asyncio
import logging
import subprocess
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Callable, Tuple
from dataclasses import dataclass, field

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from obswebsocket import obsws, requests as obs_requests
from twitchAPI.twitch import Twitch
import aiohttp
import pyudev
from zeroconf import ServiceBrowser, Zeroconf

# Initialize Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StreamingServiceManager")

# Configuration Loading
CONFIG_PATH = "config.yaml"

def load_config(path: str) -> Dict:
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info("Configuration loaded successfully.")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {}

config = load_config(CONFIG_PATH)

# OBS Manager
class OBSManager:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        self.connect()

    def connect(self):
        try:
            self.ws = obsws(self.host, self.port, self.password)
            self.ws.connect()
            logger.info("Connected to OBS WebSocket.")
        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")

    def load_scenes(self, scenes: List[Dict]):
        if not self.ws:
            self.connect()
        try:
            for source in scenes:
                self.ws.call(obs_requests.CreateSource(
                    sourceName=source["name"],
                    sourceKind=source["type"],
                    sceneName="Master Scene",
                    sourceSettings=source.get("settings", {})
                ))
                self.ws.call(obs_requests.SetSceneItemProperties(
                    item=source["name"],
                    visible=True,
                    bounds={"x": source["transform"]["scale_x"], "y": source["transform"]["scale_y"]},
                    position={"x": source["transform"]["pos_x"], "y": source["transform"]["pos_y"]},
                ))
            logger.info("Scenes loaded successfully into OBS.")
        except Exception as e:
            logger.error(f"Error loading scenes into OBS: {e}")

    def manage_scene(self, active_sources: List[str]):
        if not self.ws:
            self.connect()
        try:
            # Set visibility based on active sources
            all_sources = [source["name"] for source in config["obs"]["master_scene"]["sources"]]
            for source in all_sources:
                visible = source in active_sources
                self.ws.call(obs_requests.SetSceneItemProperties(
                    item=source,
                    visible=visible
                ))
            logger.info(f"Scene managed based on active sources: {active_sources}")
        except Exception as e:
            logger.error(f"Error managing scene in OBS: {e}")

# Twitch VOD Manager
class TwitchVODManager:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.twitch = Twitch(client_id, client_secret)
        self.twitch.authenticate_app([])
        logger.info("Authenticated with Twitch API.")

    async def get_vod_url(self, vod_id: str) -> Optional[str]:
        try:
            vods = self.twitch.get_videos(video_id=vod_id)
            if vods['data']:
                return vods['data'][0]['url']
            else:
                logger.warning(f"No VOD found for ID: {vod_id}")
                return None
        except Exception as e:
            logger.error(f"Error fetching VOD URL: {e}")
            return None

    async def download_vod(self, vod_url: str, output_path: str) -> bool:
        try:
            logger.info(f"Starting download of VOD from {vod_url} to {output_path}")
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-i', vod_url,
                '-c', 'copy',
                output_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info(f"Successfully downloaded VOD to {output_path}")
                return True
            else:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"Error downloading VOD: {e}")
            return False

# Post-Processing
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

def auto_fix_mobile_portrait(video: VideoMetadata) -> ProcessingResult:
    try:
        logger.info(f"Auto-fixing mobile portrait for {video.title}")
        output_path = video.input_path.replace(".mp4", "_fixed.mp4")
        # Example FFmpeg command to rotate video if needed
        subprocess.run(
            ["ffmpeg", "-i", video.input_path, "-vf", "transpose=1", output_path],
            check=True
        )
        return ProcessingResult(
            success=True,
            message="Mobile portrait fixed.",
            output_path=output_path
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in auto_fix_mobile_portrait: {e}")
        return ProcessingResult(
            success=False,
            message="Failed to fix mobile portrait.",
            errors=[str(e)]
        )

def apply_portrait_in_landscape(video: VideoMetadata) -> ProcessingResult:
    try:
        logger.info(f"Applying portrait in landscape for {video.title}")
        output_path = video.input_path.replace(".mp4", "_landscape.mp4")
        # Example FFmpeg command to add padding for landscape
        subprocess.run(
            ["ffmpeg", "-i", video.input_path, "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2", output_path],
            check=True
        )
        return ProcessingResult(
            success=True,
            message="Portrait applied in landscape.",
            output_path=output_path
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in apply_portrait_in_landscape: {e}")
        return ProcessingResult(
            success=False,
            message="Failed to apply portrait in landscape.",
            errors=[str(e)]
        )

def video_processing_queue(tasks: List[Tuple[Callable[[VideoMetadata], ProcessingResult], VideoMetadata]]) -> List[ProcessingResult]:
    results = []
    for func, video in tasks:
        logger.info(f"Processing {video.title} with {func.__name__}")
        result = func(video)
        results.append(result)
        if result.success and video.input_path:
            try:
                os.remove(video.input_path)
                logger.info(f"Removed ephemeral file: {video.input_path}")
            except Exception as e:
                logger.error(f"Failed to remove file {video.input_path}: {e}")
    return results

def process_video(input_path: str) -> str:
    video = VideoMetadata(
        video_id="unknown",
        title=os.path.basename(input_path),
        input_path=input_path
    )

    queue = [
        (auto_fix_mobile_portrait, video),
        (apply_portrait_in_landscape, video),
    ]

    results = video_processing_queue(queue)

    for result in reversed(results):
        if result.success and result.output_path:
            return result.output_path

    raise Exception("All post-processing steps failed.")

def save_to_persistence(processed_path: str, persistent_path: str):
    try:
        video_file = Path(processed_path)
        date = datetime.now().strftime("%Y-%m-%d")
        dest_dir = Path(persistent_path) / date
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / video_file.name
        subprocess.run(
            ["mv", processed_path, str(dest_path)],
            check=True
        )
        logger.info(f"Saved processed video to {dest_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error saving to persistence: {e}")
        raise

# Device Manager
class DeviceManager:
    def __init__(self):
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='video4linux')
        self.observers = []
        self.active_sources = []
        self.obs_manager = None

    def set_obs_manager(self, obs_manager: OBSManager):
        self.obs_manager = obs_manager

    async def monitor_devices(self):
        logger.info("Starting device monitoring...")
        observer = pyudev.MonitorObserver(self.monitor, callback=self.device_event)
        observer.start()
        self.observers.append(observer)

        # Initial device scan
        for device in self.context.list_devices(subsystem='video4linux'):
            self.handle_device_added(device)

    def device_event(self, action, device):
        if action == 'add':
            asyncio.create_task(self.handle_device_added(device))
        elif action == 'remove':
            asyncio.create_task(self.handle_device_removed(device))

    async def handle_device_added(self, device):
        try:
            device_name = device.get('ID_MODEL') or device.get('NAME') or device.device_node
            logger.info(f"Device added: {device_name}")
            self.active_sources.append(device_name)
            if self.obs_manager:
                self.obs_manager.manage_scene(self.active_sources)
        except Exception as e:
            logger.error(f"Error handling device addition: {e}")

    async def handle_device_removed(self, device):
        try:
            device_name = device.get('ID_MODEL') or device.get('NAME') or device.device_node
            logger.info(f"Device removed: {device_name}")
            if device_name in self.active_sources:
                self.active_sources.remove(device_name)
            if self.obs_manager:
                self.obs_manager.manage_scene(self.active_sources)
        except Exception as e:
            logger.error(f"Error handling device removal: {e}")

# Storage Manager
class StorageManager:
    def __init__(self, persistent_path: str, ephemeral_path: str):
        self.persistent_path = Path(persistent_path)
        self.ephemeral_path = Path(ephemeral_path)
        self.persistent_path.mkdir(parents=True, exist_ok=True)
        self.ephemeral_path.mkdir(parents=True, exist_ok=True)

    async def monitor_storage(self):
        logger.info("Starting storage monitoring...")
        while True:
            try:
                total, used, free = shutil.disk_usage(self.persistent_path)
                used_percent = (used / total) * 100
                logger.info(f"Storage usage: {used_percent:.2f}%")

                if used_percent > 90:
                    logger.warning("Storage space critical. Initiating cleanup.")
                    self.cleanup_old_recordings()
            except Exception as e:
                logger.error(f"Error monitoring storage: {e}")
            await asyncio.sleep(300)  # Check every 5 minutes

    def cleanup_old_recordings(self):
        try:
            recordings = sorted(
                self.persistent_path.glob('**/*.mp4'),
                key=lambda p: p.stat().st_mtime
            )
            while recordings:
                oldest = recordings.pop(0)
                oldest.unlink()
                logger.info(f"Removed old recording: {oldest}")
                # Recalculate usage
                total, used, free = shutil.disk_usage(self.persistent_path)
                used_percent = (used / total) * 100
                if used_percent < 80:
                    logger.info("Storage usage back to safe levels.")
                    break
        except Exception as e:
            logger.error(f"Error cleaning up recordings: {e}")

# FastAPI Models
class VideoRequest(BaseModel):
    vod_id: str
    output_name: str

# Initialize Managers
obs_config = config.get("obs", {})
obs_manager = OBSManager(
    host=obs_config.get("host", "localhost"),
    port=obs_config.get("port", 4444),
    password=obs_config.get("password", "your_password")
)
obs_manager.load_scenes(config["obs"]["master_scene"]["sources"])

twitch_config = config.get("twitch", {})
twitch_manager = TwitchVODManager(
    client_id=twitch_config.get("client_id", "your_client_id"),
    client_secret=twitch_config.get("client_secret", "your_client_secret")
)

device_manager = DeviceManager()
device_manager.set_obs_manager(obs_manager)

storage_config = config.get("storage", {})
storage_manager = StorageManager(
    persistent_path=storage_config.get("persistent", {}).get("mount_point", "/data/recordings"),
    ephemeral_path=storage_config.get("ephemeral", {}).get("temp_path", "/data/ephemeral")
)

# Initialize FastAPI
app = FastAPI(
    title="Streaming Service Manager",
    version="1.0",
    description="A service for managing Twitch VODs, OBS scenes, and video post-processing."
)
router = APIRouter()

# API Endpoints
@router.get("/", tags=["Health"])
async def root():
    return {"message": "Streaming Service Manager is running."}

@router.post("/obs/connect", tags=["OBS"])
async def connect_obs():
    try:
        obs_manager.connect()
        return {"status": "Connected to OBS WebSocket"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/obs/load-scenes", tags=["OBS"])
async def load_obs_scenes():
    try:
        obs_manager.load_scenes(config["obs"]["master_scene"]["sources"])
        return {"status": "Scenes loaded successfully into OBS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/obs/manage-scene", tags=["OBS"])
async def manage_obs_scene(active_sources: List[str]):
    try:
        obs_manager.manage_scene(active_sources)
        return {"status": "Scene managed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vods/fetch-and-process", tags=["VOD Management"])
async def fetch_and_process(video_request: VideoRequest, background_tasks: BackgroundTasks):
    ephemeral_path = Path(storage_manager.ephemeral_path) / f"{video_request.output_name}.mp4"
    persistent_path = Path(storage_manager.persistent_path) / "twitch"

    background_tasks.add_task(handle_video_processing, video_request.vod_id, str(ephemeral_path), str(persistent_path))
    return {"message": f"Processing started for VOD ID: {video_request.vod_id}"}

async def handle_video_processing(vod_id: str, ephemeral_path: str, persistent_path: str):
    try:
        vod_url = await twitch_manager.get_vod_url(vod_id)
        if not vod_url:
            logger.error(f"VOD URL not found for ID: {vod_id}")
            return

        success = await twitch_manager.download_vod(vod_url, ephemeral_path)
        if not success:
            logger.error(f"Failed to download VOD ID: {vod_id}")
            return

        processed_path = process_video(ephemeral_path)
        save_to_persistence(processed_path, persistent_path)
    except Exception as e:
        logger.error(f"Error during video processing: {e}")

# Add Router to App
app.include_router(router)

# Background Tasks
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Streaming Service Manager...")
    asyncio.create_task(device_manager.monitor_devices())
    asyncio.create_task(storage_manager.monitor_storage())
    logger.info("Background tasks initiated.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Streaming Service Manager...")
    if obs_manager.ws:
        obs_manager.ws.disconnect()
        logger.info("Disconnected from OBS WebSocket.")
    for observer in device_manager.observers:
        observer.stop()
    logger.info("Device monitoring stopped.")

# Additional Dependencies for Storage Manager
import shutil

# Ensure Config Exists
if not config:
    logger.error("Configuration not found. Exiting application.")
    exit(1)