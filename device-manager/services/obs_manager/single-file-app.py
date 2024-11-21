from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from obswebsocket import obsws, requests, events
from pathlib import Path
from typing import Optional

# OBS WebSocket connection details
HOST = "localhost"
PORT = 4444
PASSWORD = "your_password"

EPHEMERAL_STORAGE = "/data/ephemeral"
PERSISTENT_STORAGE = "/data/recordings"

ws = None  # Global WebSocket connection instance

# FastAPI app setup
app = FastAPI(
    title="Streaming Service Manager",
    version="1.0",
    description="A service for managing Twitch VODs and OBS scenes."
)

router = APIRouter()

# OBS WebSocket Functions
def connect_to_obs():
    """Connect to OBS WebSocket."""
    global ws
    if ws is None:
        ws = obsws(HOST, PORT, PASSWORD)
        ws.connect()
        print("Connected to OBS WebSocket.")
    return ws


MASTER_SCENE_JSON = {
    "sources": [
        {
            "name": "Main Camera",
            "type": "input",
            "settings": {"video_device": "Nikon Z7"},
            "transform": {"pos_x": 0, "pos_y": 0, "scale_x": 1920, "scale_y": 1440, "alignment": 5},
        },
        {
            "name": "iPhone ScreenBroadcast",
            "type": "input",
            "settings": {"source": "iPhone 15 Pro Max"},
            "transform": {"pos_x": 640, "pos_y": 0, "scale_x": 640, "scale_y": 1080, "alignment": 5},
        },
        {
            "name": "Default Page",
            "type": "image_source",
            "settings": {"file_path": "./default_image.webp"},
            "transform": {"pos_x": 0, "pos_y": 0, "scale_x": 1920, "scale_y": 1080, "alignment": 5},
        },
    ]
}


def load_scenes():
    """Load master scene configuration into OBS."""
    ws = connect_to_obs()
    for source in MASTER_SCENE_JSON["sources"]:
        ws.call(requests.CreateSource(source["name"], source["type"], "Master Scene", source["settings"]))
        ws.call(
            requests.SetSceneItemProperties(
                item=source["name"],
                visible=True,
                bounds={"x": source["transform"]["scale_x"], "y": source["transform"]["scale_y"]},
                position={"x": source["transform"]["pos_x"], "y": source["transform"]["pos_y"]},
            )
        )
    print("Scenes loaded successfully.")


def manage_scene():
    """Manage OBS scene dynamically based on source activity."""
    ws = connect_to_obs()
    camera_settings = ws.call(requests.GetSourceSettings("Main Camera")).getSettings()
    camera_active = camera_settings.get("video_device") is not None
    iphone_settings = ws.call(requests.GetSourceSettings("iPhone ScreenBroadcast")).getSettings()
    iphone_active = iphone_settings.get("source") is not None

    if iphone_active:
        ws.call(requests.SetSceneItemProperties("iPhone ScreenBroadcast", visible=True))
        ws.call(requests.SetSceneItemProperties("Main Camera", visible=True))
        ws.call(requests.SetSceneItemProperties("Default Page", visible=False))
    elif camera_active:
        ws.call(requests.SetSceneItemProperties("Main Camera", visible=True))
        ws.call(requests.SetSceneItemProperties("iPhone ScreenBroadcast", visible=False))
        ws.call(requests.SetSceneItemProperties("Default Page", visible=False))
    else:
        ws.call(requests.SetSceneItemProperties("Main Camera", visible=False))
        ws.call(requests.SetSceneItemProperties("iPhone ScreenBroadcast", visible=False))
        ws.call(requests.SetSceneItemProperties("Default Page", visible=True))

    print("Scene managed successfully.")


# FastAPI Endpoints
@router.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Service is running!"}


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


# Add routes to the app
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)