# tests/test_integration.py
import pytest
import requests
import websocket
import docker
import time
import os
import json
from pathlib import Path
import asyncio
import aiohttp
import ffmpeg

class TestStreamingSetup:
    @pytest.fixture(scope="session")
    def docker_client(self):
        return docker.from_env()

    @pytest.fixture(scope="session")
    def compose_project(self, docker_client):
        # Start the entire docker-compose stack
        os.system('docker-compose up -d')
        time.sleep(10)  # Wait for services to be ready
        
        yield
        
        # Cleanup
        os.system('docker-compose down -v')

    @pytest.fixture
    def api_base_url(self):
        return "http://localhost:8000/api"

    @pytest.fixture
    def rtmp_url(self):
        return "rtmp://localhost:1935/live"

    @pytest.mark.asyncio
    async def test_service_health(self, compose_project):
        """Test that all services are healthy"""
        services = {
            'rtmp-server': 'http://localhost:8080/health',
            'api-router': 'http://localhost:8000/health',
            'web-server': 'http://localhost:3000/health'
        }
        
        async with aiohttp.ClientSession() as session:
            for service, url in services.items():
                async with session.get(url) as response:
                    assert response.status == 200, f"{service} is not healthy"

    @pytest.mark.asyncio
    async def test_rtmp_stream_workflow(self, compose_project, rtmp_url):
        """Test complete RTMP streaming workflow"""
        # Start a test stream using FFmpeg
        stream_key = "test_stream"
        test_video = "tests/assets/test_video.mp4"
        
        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-re',  # Read input at native framerate
            '-i', test_video,
            '-c', 'copy',
            '-f', 'flv',
            f'{rtmp_url}/{stream_key}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for stream to start
        await asyncio.sleep(5)
        
        # Check stream status via API
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://localhost:8000/api/streams/{stream_key}') as response:
                assert response.status == 200
                data = await response.json()
                assert data['status'] == 'streaming'
        
        # Stop the stream
        process.terminate()
        await process.wait()
        
        # Verify recording was created
        recording_path = Path('/data/recordings')
        recordings = list(recording_path.glob(f'*{stream_key}*.mp4'))
        assert len(recordings) > 0, "No recording was created"

    @pytest.mark.asyncio
    async def test_device_manager(self, compose_project, api_base_url):
        """Test device manager functionality"""
        async with aiohttp.ClientSession() as session:
            # Check device list
            async with session.get(f'{api_base_url}/devices') as response:
                assert response.status == 200
                devices = await response.json()
                assert isinstance(devices, list)

            # Test device reconnection
            test_device = "test_device"
            async with session.post(
                f'{api_base_url}/devices/{test_device}/reconnect'
            ) as response:
                assert response.status in [200, 404]

    @pytest.mark.asyncio
    async def test_websocket_updates(self, compose_project):
        """Test WebSocket real-time updates"""
        ws_url = "ws://localhost:8000/ws"
        messages_received = []
        
        async def receive_messages(websocket):
            try:
                while True:
                    message = await websocket.receive_json()
                    messages_received.append(message)
            except Exception as e:
                print(f"WebSocket error: {e}")
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as websocket:
                receive_task = asyncio.create_task(receive_messages(websocket))
                await asyncio.sleep(5)  # Wait for some messages
                receive_task.cancel()
        
        assert len(messages_received) > 0, "No WebSocket messages received"

    @pytest.mark.asyncio
    async def test_recording_management(self, compose_project, api_base_url):
        """Test recording management functionality"""
        async with aiohttp.ClientSession() as session:
            # List recordings
            async with session.get(f'{api_base_url}/recordings') as response:
                assert response.status == 200
                recordings = await response.json()
                assert isinstance(recordings, list)
            
            # Create clip
            clip_data = {
                "stream_key": "test_stream",
                "duration": 30
            }
            async with session.post(
                f'{api_base_url}/clips', 
                json=clip_data
            ) as response:
                assert response.status in [200, 404]

    @pytest.mark.asyncio
    async def test_quality_monitoring(self, compose_project, api_base_url):
        """Test stream quality monitoring"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{api_base_url}/quality/test_stream') as response:
                assert response.status == 200
                quality_data = await response.json()
                assert 'bitrate' in quality_data
                assert 'fps' in quality_data
                assert 'resolution' in quality_data

if __name__ == "__main__":
    pytest.main(["-v", "test_integration.py"])