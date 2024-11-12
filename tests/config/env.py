# device-manager/config/env.py
import os
from typing import Dict, Any
from dotenv import load_dotenv

class EnvConfig:
    """Environment configuration handler"""
    
    def __init__(self):
        # Load .env file from root directory
        load_dotenv(dotenv_path='../.env')
        
        self.required_vars = [
            'OBS_WS_PASSWORD',
            'JWT_SECRET',
            'NAS_HOST',
            'NAS_PATH'
        ]
        
        # Verify required variables
        self._verify_required_vars()
    
    def _verify_required_vars(self):
        """Verify all required environment variables are set"""
        missing = [var for var in self.required_vars 
                  if not os.getenv(var)]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please check your .env file."
            )
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return {
            'obs': {
                'host': os.getenv('LOCAL_IP', '192.168.0.187'),
                'port': int(os.getenv('OBS_WS_PORT', '4444')),
                'password': os.getenv('OBS_WS_PASSWORD')
            },
            'storage': {
                'nas_host': os.getenv('NAS_HOST'),
                'nas_path': os.getenv('NAS_PATH'),
                'mount_point': '/data/recordings'
            },
            'rtmp': {
                'server_url': os.getenv('RTMP_SERVER_URL', 
                                      'rtmp://192.168.0.187:1935/live')
            },
            'api': {
                'jwt_secret': os.getenv('JWT_SECRET'),
                'base_url': os.getenv('DEVICE_MANAGER_URL', 
                                    'http://localhost:5000')
            }
        }

# Usage in device_manager.py
from config.env import EnvConfig

env_config = EnvConfig()
config = env_config.config