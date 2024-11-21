from twitchAPI.twitch import Twitch
from typing import Optional

class TwitchVODManager:
    def __init__(self, client_id: str, client_secret: str):
        self.twitch = Twitch(client_id, client_secret)
        self.twitch.authenticate_app([])

    def get_vod_url(self, vod_id: str) -> Optional[str]:
        try:
            vod = self.twitch.get_videos(video_id=vod_id)
            return vod['data'][0]['url'] if 'data' in vod else None
        except Exception as e:
            print(f"Error fetching VOD URL: {e}")
            return None