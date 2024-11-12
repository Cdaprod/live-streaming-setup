# Cdaprod's live-streaming-setup

Implementation of my local development to live stream my content over multiple broadcasted devices and cameras with my local network attached storage as an archive.

## Prerequisites

- Docker and Docker Compose installed on your desktop (`192.168.0.25`).
- NAS (`192.168.0.19`) properly mounted on the desktop.
- ESP32-CAMs configured and accessible on the local network.

## Setup Steps

#### 1. **Clone the Repository:**

   ```bash
   git clone <your-repo-url>
   cd streaming-setup
   ``` 

#### 2. **Configure NAS Mount:**
Ensure the NAS is mounted at /mnt/data/rtmp_recordings.

#### 3.	**Update ESP32-CAM URLs:**
Edit docker-compose.yml to replace <esp32-cam-ip> with your ESP32-CAM’s actual IP addresses.

#### 4. **Build & Push:**

   ```bash
   cd scripts
   ./build_and_push.sh
   ``` 
   
#### 5. **Start Services:** 
   
   ```bash
   cd ..
   docker-compose up -d
   ``` 
   
#### **6.	Verify Setup:**

	•	Access RTMP streams at rtmp://192.168.0.25:1935/live/
	•	Check recordings on your NAS at /volume1/videos

## Managing Docker Images

Use the provided build_and_push.sh script to build and push images to your local Docker registry (cdaprod/).

## Troubleshooting

	•	Logs:
	•	RTMP Server: docker logs rtmp_server
	•	FFmpeg Streamer: docker logs esp32_cam_streamer
	•	Common Issues:
	•	Incorrect ESP32-CAM URL.
	•	NAS not mounted or permissions issues.
	•	Firewall blocking necessary ports.
	
## Adding More Cameras

#### **To add more ESP32-CAMs:**

1.	Duplicate the esp32_cam_streamer service in docker-compose.yml.
2.	Update the ESP32_CAM_URL and RTMP_SERVER_URL accordingly.
3.	Rebuild and restart services:
	
	```bash
	./scripts/build_and_push.sh
	docker-compose up -d
	```

##### License

MIT License