#!/usr/bin/env python3
"""
Enhanced Device Manager for Live Streaming Setup
Handles USB cameras, RTMP streams, and network devices
Author: @Cdaprod
"""

import asyncio
import logging
import json
import aiohttp
import pyudev
import v4l2
import fcntl
import time
import yaml
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from zeroconf import ServiceBrowser, Zeroconf
from obswebsocket import obsws, requests as obsrequests
from pathlib import Path

class StreamType(Enum):
    """Enumeration of supported stream types"""
    RTMP = "rtmp"
    USB = "usb"
    NETWORK = "network"

class DeviceStatus(Enum):
    """Enumeration of possible device statuses"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    STREAMING = "streaming"

@dataclass
class DeviceInfo:
    """Data class for storing device information"""
    id: str
    type: StreamType
    name: str
    status: DeviceStatus
    address: str
    stream_key: Optional[str] = None
    last_seen: float = 0
    reconnect_attempts: int = 0
    settings: Dict[str, Any] = None
    error_message: Optional[str] = None

class StreamQuality:
    """Stream quality metrics and thresholds"""
    def __init__(self, config: dict):
        self.bitrate: int = 0
        self.fps: float = 0
        self.resolution: str = ""
        self.min_bitrate = config.get('bitrate_min', 2000000)
        self.min_fps = config.get('framerate_min', 24)
        self.min_resolution = config.get('resolution_min', '1920x1080')

    def is_acceptable(self) -> bool:
        """Check if current quality meets minimum thresholds"""
        if self.bitrate < self.min_bitrate:
            return False
        if self.fps < self.min_fps:
            return False
        width, height = map(int, self.resolution.split('x'))
        min_width, min_height = map(int, self.min_resolution.split('x'))
        if width < min_width or height < min_height:
            return False
        return True

class EnhancedDeviceManager:
    """Main device manager class"""
    def __init__(self, config_path: str = "/app/config/streams.yaml"):
        self.logger = logging.getLogger('EnhancedDeviceManager')
        self.devices: Dict[str, DeviceInfo] = {}
        self.stream_qualities: Dict[str, StreamQuality] = {}
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Set up device monitoring
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='video4linux')
        
        # Set up network discovery
        self.zeroconf = Zeroconf()
        
        # Set up OBS WebSocket connection
        self.obs_ws = None
        self.obs_config = self.config.get('obs', {})
        
        # Set up storage manager
        self.storage_config = self.config.get('storage', {})
        self.recording_path = Path(self.storage_config.get('mount_point', '/data/recordings'))

    def load_config(self, path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                self.logger.info("Successfully loaded configuration")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load config from {path}: {e}")
            return {}

    async def connect_obs(self):
        """Connect to OBS via WebSocket"""
        try:
            host = self.obs_config.get('host', 'localhost')
            port = self.obs_config.get('port', 4444)
            password = self.obs_config.get('password', '')
            
            self.obs_ws = obsws(host, port, password)
            await self.obs_ws.connect()
            self.logger.info("Successfully connected to OBS WebSocket")
        except Exception as e:
            self.logger.error(f"Failed to connect to OBS WebSocket: {e}")

    async def start(self):
        """Start all monitoring and management tasks"""
        self.logger.info("Starting enhanced device manager...")
        
        # Connect to OBS
        await self.connect_obs()
        
        # Start monitoring tasks
        tasks = [
            self.monitor_usb_devices(),
            self.monitor_rtmp_streams(),
            self.check_device_health(),
            self.monitor_storage()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in device manager: {e}")
            raise

    async def monitor_usb_devices(self):
        """Monitor USB video devices"""
        self.logger.info("Starting USB device monitoring...")
        
        def handle_udev_event(device):
            if device.action == 'add':
                asyncio.create_task(self.handle_device_added(device))
            elif device.action == 'remove':
                asyncio.create_task(self.handle_device_removed(device))

        observer = pyudev.MonitorObserver(self.monitor, handle_udev_event)
        observer.start()

        # Initial device scan
        for device in self.context.list_devices(subsystem='video4linux'):
            await self.handle_device_added(device)

    async def monitor_rtmp_streams(self):
        """Monitor RTMP streams and their health"""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    url = 'http://localhost:8080/stat'
                    async with session.get(url) as response:
                        if response.status == 200:
                            stats_xml = await response.text()
                            await self.process_rtmp_stats(stats_xml)
            except Exception as e:
                self.logger.error(f"Error monitoring RTMP streams: {e}")
            
            await asyncio.sleep(5)

    async def process_rtmp_stats(self, stats_xml: str):
        """Process RTMP statistics from nginx-rtmp"""
        try:
            root = ET.fromstring(stats_xml)
            for stream in root.findall(".//stream"):
                stream_key = stream.find("name").text
                if stream_key in self.devices:
                    device_info = self.devices[stream_key]
                    device_info.status = DeviceStatus.STREAMING
                    device_info.last_seen = time.time()
                    
                    # Update quality metrics
                    bw_in = stream.find("bw_in")
                    if bw_in is not None:
                        quality = self.stream_qualities.get(stream_key, StreamQuality(self.config))
                        quality.bitrate = int(bw_in.text)
                        if not quality.is_acceptable():
                            self.logger.warning(f"Stream quality below threshold: {stream_key}")
        except Exception as e:
            self.logger.error(f"Error processing RTMP stats: {e}")

    async def handle_device_added(self, device):
        """Handle new USB video device connection"""
        try:
            vendor_id = device.get('ID_VENDOR_ID')
            product_id = device.get('ID_MODEL_ID')
            
            # Check against known devices in config
            for device_id, config in self.config.get('sources', {}).items():
                if config['type'] == 'usb':
                    if (config['vendor_id'] == vendor_id and
                        config['product_id'] == product_id):
                        
                        device_info = DeviceInfo(
                            id=device_id,
                            type=StreamType.USB,
                            name=config['name'],
                            status=DeviceStatus.CONNECTED,
                            address=device.device_node,
                            settings=config.get('settings', {}),
                            last_seen=time.time()
                        )
                        
                        self.devices[device_id] = device_info
                        await self.update_obs_source(device_info)
                        self.logger.info(f"Added USB device: {device_info.name}")
        
        except Exception as e:
            self.logger.error(f"Error handling device addition: {e}")

    async def update_obs_source(self, device_info: DeviceInfo):
        """Update OBS source settings"""
        if self.obs_ws and self.obs_ws.is_connected():
            try:
                settings = device_info.settings or {}
                if device_info.type == StreamType.USB:
                    settings.update({
                        'device': device_info.address,
                        'input_format': settings.get('input_format', 'mjpeg'),
                        'resolution': settings.get('resolution', '3840x2160'),
                        'fps': settings.get('fps', 30)
                    })
                elif device_info.type == StreamType.RTMP:
                    settings.update({
                        'url': f'rtmp://localhost:1935/live/{device_info.stream_key}',
                        'reconnect': True,
                        'reconnect_delay_sec': 2
                    })
                
                await self.obs_ws.call(obsrequests.SetSourceSettings(
                    sourceName=device_info.name,
                    sourceSettings=settings
                ))
                self.logger.info(f"Updated OBS source: {device_info.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to update OBS source: {e}")

    async def check_device_health(self):
        """Periodic health check for all devices"""
        while True:
            try:
                current_time = time.time()
                for device_id, device_info in list(self.devices.items()):
                    if device_info.status != DeviceStatus.CONNECTED:
                        if current_time - device_info.last_seen > 30:
                            await self.trigger_reconnect(device_info)
                    
                    if device_info.status == DeviceStatus.CONNECTED:
                        await self.verify_device_streaming(device_info)
                        
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
            
            await asyncio.sleep(5)

    async def monitor_storage(self):
        """Monitor NAS storage space and manage recordings"""
        while True:
            try:
                space = self.recording_path.stat().st_free
                total = self.recording_path.stat().st_size
                used_percent = (total - space) / total * 100
                
                if used_percent > 90:
                    self.logger.warning(f"Storage space critical: {used_percent:.1f}% used")
                    await self.cleanup_old_recordings()
                    
            except Exception as e:
                self.logger.error(f"Error monitoring storage: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes

    async def cleanup_old_recordings(self):
        """Clean up old recordings when storage is low"""
        try:
            # Get all recordings sorted by modification time
            recordings = sorted(
                self.recording_path.glob('**/*.mp4'),
                key=lambda p: p.stat().st_mtime
            )
            
            # Remove oldest recordings until we're below 80% usage
            while len(recordings) > 0:
                space = self.recording_path.stat().st_free
                total = self.recording_path.stat().st_size
                if (total - space) / total * 100 < 80:
                    break
                    
                oldest = recordings.pop(0)
                oldest.unlink()
                self.logger.info(f"Removed old recording: {oldest}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up recordings: {e}")

    async def create_clip(self, stream_key: str, duration: int = 30):
        """Create a clip from the current stream"""
        try:
            device_info = self.devices.get(stream_key)
            if not device_info:
                raise ValueError(f"Unknown stream: {stream_key}")
                
            if device_info.status != DeviceStatus.STREAMING:
                raise ValueError(f"Stream not active: {stream_key}")
                
            # Create clip directory
            clip_path = self.recording_path / 'clips' / stream_key
            clip_path.mkdir(parents=True, exist_ok=True)
            
            # Generate clip filename
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            clip_file = clip_path / f"clip_{timestamp}.mp4"
            
            # Create clip using ffmpeg
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-i', f'rtmp://localhost:1935/live/{stream_key}',
                '-t', str(duration),
                '-c', 'copy',
                str(clip_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            if process.returncode == 0:
                self.logger.info(f"Created clip: {clip_file}")
                return str(clip_file)
            else:
                raise RuntimeError("Failed to create clip")
                
        except Exception as e:
            self.logger.error(f"Error creating clip: {e}")
            raise

async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start device manager
    manager = EnhancedDeviceManager()
    await manager.start()
    
    try:
        # Keep the manager running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        manager.zeroconf.close()
        if manager.obs_ws:
            await manager.obs_ws.disconnect()

if __name__ == "__main__":
    asyncio.run(main())