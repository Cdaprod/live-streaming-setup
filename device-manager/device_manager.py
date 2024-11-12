import asyncio
import logging
import json
import aiohttp
import pyudev
import v4l2
import fcntl
import time
from typing import Dict, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from zeroconf import ServiceBrowser, Zeroconf
from bonjour_discovery import BonjourServiceListener

@dataclass
class DeviceInfo:
    id: str
    type: str  # 'usb', 'network', 'prism'
    name: str
    status: str
    address: str
    last_seen: float
    reconnect_attempts: int = 0

class CameraDeviceManager:
    def __init__(self):
        self.logger = logging.getLogger('CameraDeviceManager')
        self.devices: Dict[str, DeviceInfo] = {}
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='video4linux')
        self.zeroconf = Zeroconf()
        self.bonjour_listener = BonjourServiceListener()
        self.obs_ws = None  # Will be initialized later
        
        # Known devices configuration
        self.known_devices = {
            'cda_ios': {
                'type': 'prism',
                'service_name': '_prism._tcp.local.',
                'friendly_name': 'iOS Main Device'
            },
            'cda_ios_14': {
                'type': 'prism',
                'service_name': '_prism._tcp.local.',
                'friendly_name': 'iOS Secondary Device'
            },
            'nikon_z7': {
                'type': 'usb',
                'vendor_id': '0x04b0',  # Nikon vendor ID
                'product_id': '0x0000',  # Replace with actual Z7 product ID
                'friendly_name': 'Nikon Z7'
            }
        }

    async def start(self):
        """Start device monitoring and discovery"""
        self.logger.info("Starting device manager...")
        
        # Start USB device monitoring
        asyncio.create_task(self.monitor_usb_devices())
        
        # Start network device discovery
        asyncio.create_task(self.discover_network_devices())
        
        # Start device health check
        asyncio.create_task(self.check_device_health())
        
        # Start OBS WebSocket connection
        await self.connect_obs()

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

    async def discover_network_devices(self):
        """Discover network-based camera devices (Prism mobile streams)"""
        self.logger.info("Starting network device discovery...")
        
        # Browse for Prism services
        browser = ServiceBrowser(
            self.zeroconf,
            "_prism._tcp.local.",
            self.bonjour_listener
        )
        
        # Handle Prism device discovery
        def on_prism_device_found(name, address, port):
            device_info = DeviceInfo(
                id=name,
                type='prism',
                name=name,
                status='discovered',
                address=f"{address}:{port}",
                last_seen=time.time()
            )
            self.devices[name] = device_info
            asyncio.create_task(self.connect_prism_device(device_info))

        self.bonjour_listener.add_callback(on_prism_device_found)

    async def connect_prism_device(self, device_info: DeviceInfo):
        """Connect to a discovered Prism device"""
        try:
            # Implement Prism-specific connection logic
            if device_info.id in ['cda_ios', 'cda_ios_14']:
                # Update OBS source settings
                await self.update_obs_source(
                    source_name=self.known_devices[device_info.id]['friendly_name'],
                    settings={
                        'url': f'http://{device_info.address}/stream',
                        'reconnect': True,
                        'reconnect_delay_sec': 2
                    }
                )
                device_info.status = 'connected'
                self.logger.info(f"Connected to Prism device: {device_info.name}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Prism device: {e}")
            device_info.status = 'error'
            device_info.reconnect_attempts += 1

    async def handle_device_added(self, device):
        """Handle new USB video device connection"""
        try:
            # Check if this is a known device
            for device_id, config in self.known_devices.items():
                if config['type'] == 'usb':
                    if (device.get('ID_VENDOR_ID') == config['vendor_id'] and
                        device.get('ID_MODEL_ID') == config['product_id']):
                        
                        device_info = DeviceInfo(
                            id=device_id,
                            type='usb',
                            name=config['friendly_name'],
                            status='connected',
                            address=device.device_node,
                            last_seen=time.time()
                        )
                        
                        self.devices[device_id] = device_info
                        await self.update_obs_source(
                            source_name=config['friendly_name'],
                            settings={
                                'device': device.device_node,
                                'input_format': 'mjpeg',  # Adjust based on your capture card
                                'resolution': '3840x2160',  # 4K for Z7
                                'fps': 30
                            }
                        )
                        self.logger.info(f"Added USB device: {config['friendly_name']}")
                        
        except Exception as e:
            self.logger.error(f"Error handling device addition: {e}")

    async def handle_device_removed(self, device):
        """Handle USB video device disconnection"""
        for device_id, device_info in list(self.devices.items()):
            if device_info.type == 'usb' and device_info.address == device.device_node:
                device_info.status = 'disconnected'
                self.logger.info(f"Device removed: {device_info.name}")
                await self.trigger_reconnect(device_info)

    async def check_device_health(self):
        """Periodic health check for all devices"""
        while True:
            try:
                current_time = time.time()
                for device_id, device_info in list(self.devices.items()):
                    if device_info.status != 'connected':
                        if current_time - device_info.last_seen > 30:  # 30 seconds timeout
                            await self.trigger_reconnect(device_info)
                    
                    # Check streaming status for connected devices
                    if device_info.status == 'connected':
                        await self.verify_device_streaming(device_info)
                        
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds

    async def verify_device_streaming(self, device_info: DeviceInfo):
        """Verify if a device is actually streaming data"""
        try:
            if device_info.type == 'usb':
                # Check USB device streaming status
                with open(device_info.address, 'rb') as f:
                    try:
                        fcntl.ioctl(f, v4l2.VIDIOC_G_FMT, v4l2.v4l2_format())
                    except:
                        await self.trigger_reconnect(device_info)
                        
            elif device_info.type == 'prism':
                # Check Prism stream health
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'http://{device_info.address}/health') as resp:
                        if resp.status != 200:
                            await self.trigger_reconnect(device_info)
                            
        except Exception as e:
            self.logger.error(f"Error verifying device streaming: {e}")
            await self.trigger_reconnect(device_info)

    async def trigger_reconnect(self, device_info: DeviceInfo):
        """Handle device reconnection"""
        device_info.reconnect_attempts += 1
        self.logger.info(f"Attempting to reconnect {device_info.name} (attempt {device_info.reconnect_attempts})")
        
        if device_info.type == 'prism':
            await self.connect_prism_device(device_info)
        elif device_info.type == 'usb':
            # USB devices will be automatically handled by monitor_usb_devices
            pass

    async def update_obs_source(self, source_name: str, settings: dict):
        """Update OBS source settings"""
        if self.obs_ws and self.obs_ws.is_connected():
            try:
                await self.obs_ws.call('SetSourceSettings', {
                    'sourceName': source_name,
                    'sourceSettings': settings
                })
            except Exception as e:
                self.logger.error(f"Failed to update OBS source: {e}")

async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start device manager
    manager = CameraDeviceManager()
    await manager.start()
    
    try:
        # Keep the manager running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        manager.zeroconf.close()

if __name__ == "__main__":
    asyncio.run(main())