from obswebsocket import obsws, requests, events

# OBS WebSocket connection details
HOST = "localhost"
PORT = 4444
PASSWORD = "your_password"

ws = None  # Global WebSocket connection instance

def connect_to_obs():
    """Connect to OBS WebSocket."""
    global ws
    if ws is None:
        ws = obsws(HOST, PORT, PASSWORD)
        ws.connect()
        print("Connected to OBS WebSocket.")
    return ws

def load_scenes():
    """Load master scene configuration into OBS."""
    ws = connect_to_obs()
    for source in MASTER_SCENE_JSON["sources"]:
        ws.call(requests.CreateSource(source["name"], source["type"], "Master Scene", source["settings"]))
        ws.call(requests.SetSceneItemProperties(
            item=source["name"],
            visible=True,
            bounds={
                "x": source["transform"]["scale_x"],
                "y": source["transform"]["scale_y"],
                "alignment": source["transform"]["alignment"]
            },
            position={
                "x": source["transform"]["pos_x"],
                "y": source["transform"]["pos_y"]
            }
        ))
    print("Scenes loaded successfully.")

def manage_scene():
    """Manage OBS scene dynamically based on source activity."""
    ws = connect_to_obs()

    # Check if the main camera is active
    camera_settings = ws.call(requests.GetSourceSettings("Main Camera")).getSettings()
    camera_active = camera_settings.get("video_device") is not None

    # Check if the iPhone broadcast is active
    iphone_settings = ws.call(requests.GetSourceSettings("iPhone ScreenBroadcast")).getSettings()
    iphone_active = iphone_settings.get("source") is not None

    # Logic for managing the scene
    if iphone_active:
        ws.call(requests.SetSceneItemProperties("iPhone ScreenBroadcast", visible=True))
        ws.call(requests.SetSceneItemProperties("Main Camera", visible=True))
        ws.call(requests.SetSceneItemProperties("Adjustments Overlay", visible=True))
        ws.call(requests.SetSceneItemProperties("Default Page", visible=False))
    elif camera_active:
        ws.call(requests.SetSceneItemProperties("Main Camera", visible=True))
        ws.call(requests.SetSceneItemProperties("iPhone ScreenBroadcast", visible=False))
        ws.call(requests.SetSceneItemProperties("Adjustments Overlay", visible=True))
        ws.call(requests.SetSceneItemProperties("Default Page", visible=False))
    else:
        ws.call(requests.SetSceneItemProperties("Main Camera", visible=False))
        ws.call(requests.SetSceneItemProperties("iPhone ScreenBroadcast", visible=False))
        ws.call(requests.SetSceneItemProperties("Adjustments Overlay", visible=False))
        ws.call(requests.SetSceneItemProperties("Default Page", visible=True))

    print("Scene managed successfully.")