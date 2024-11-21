# Streaming Service Manager

The Streaming Service Manager is a Python-based application designed to manage video streaming workflows, including VOD downloads, video post-processing, and storage management. The application is modular and extensible, built with FastAPI for efficient API interactions.

## Features

- Twitch Integration: Download high-quality VODs using the Twitch API.
- YouTube Integration: Manage video uploads and interactions via the YouTube Data API.
- Video Post-Processing: Apply transformations to video files, such as fixing mobile portrait issues and adapting portrait in landscape formats.
- Persistent Storage: Organize and store processed videos in a structured and accessible manner.
- Ephemeral Storage: Temporarily store intermediate processing data during transformations.
- API-Driven Design: FastAPI powers the service for seamless interaction with endpoints.
- Extensible Architecture: Modular components for Twitch, YouTube, post-processing, and storage management enable easy customization and extension.

```plaintext
streaming-service/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Main application entry point
│   ├── api/                     # API-specific modules
│   │   ├── __init__.py
│   │   ├── routes.py            # FastAPI routes
│   ├── services/                # Service modules
│   │   ├── __init__.py
│   │   ├── twitch/
│   │   │   ├── __init__.py
│   │   │   ├── twitch_main.py
│   │   │   ├── twitch_api.py
│   │   │   ├── download_vod.py
│   │   ├── device_manager/
│   │   │   ├── __init__.py
│   │   │   ├── device_manager.py
│   │   │   ├── config/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── streams.yaml
│   │   ├── post_processing/
│   │       ├── __init__.py
│   │       ├── post_processing_main.py
│   │       ├── submodules/
│   │       │   ├── apply_portrait.py
│   │       │   ├── auto_fix_mobile.py
│   │       │   ├── processing_queue.py
│   │       │   ├── save_to_persistence.py
│   │       │   ├── __init__.py
│   ├── models/
│       ├── __init__.py
│       ├── base_models.py
│
├── tests/                       # Tests for the application
│   ├── __init__.py
│   ├── test_twitch.py
│   ├── test_post_processing.py
│
├── Dockerfile                   # Docker configuration
├── requirements.txt             # Dependencies
├── requirements.lock
└── README.md
```

## Getting Started

### Prerequisites

Python 3.11 or later
Docker (for containerized deployment)
FFmpeg (for video processing)
Twitch Developer Account (for API integration)
Google Cloud Account (to set up the YouTube Data API and obtain API credentials)

### Installation

Clone the repository:
git clone https://github.com/yourusername/streaming-service.git
cd streaming-service
Set up the Python environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

### Configure the application:
Edit streams.yaml in app/services/device_manager/config/ to define sources and storage settings.

Add your Twitch API credentials and YouTube API credentials to the .env file.

### Setting Up Google YouTube API

Go to the Google Cloud Console.
Create a new project or select an existing one.
Enable the "YouTube Data API v3" in the APIs & Services Library.
Create credentials for an OAuth 2.0 client:
Add http://localhost:8000 as an authorized redirect URI.
Download the credentials JSON file and save it as google_credentials.json in the project root.
Update the .env file with the credentials file path:
GOOGLE_CREDENTIALS=google_credentials.json
Running the Service

##% Start the FastAPI server:

uvicorn app.main:app --reload
Access the API at http://localhost:8000.

## API Endpoints

### VOD Management

``` 
GET /vods: List available VODs from Twitch or YouTube.
POST /vods/download: Download a Twitch VOD.
POST /vods/upload: Upload a processed video to YouTube.
Post-Processing
POST /process: Initiate post-processing for a video file.
GET /process/status: Check the status of a processing task.
Storage Management
GET /storage/persistent: List videos in persistent storage.
GET /storage/ephemeral: List temporary files in ephemeral storage.
Configuration
``` 

The service uses streams.yaml to manage source and storage configurations. Key sections include:

- Sources: Define input sources (e.g., Twitch streams, USB devices).
- Storage: Configure persistent and ephemeral storage paths.

## Deployment

### Docker

Build the Docker image:

docker build -t streaming-service .

Run the container:

docker run -p 8000:8000 --env-file .env streaming-service

### Kubernetes

Use the provided k8s/deployment.yaml to deploy the service in a Kubernetes cluster.

## Contributing

Fork the repository and create a feature branch.
Make your changes and commit them.
Submit a pull request for review.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

### Acknowledgments

- FastAPI for the API framework.
- FFmpeg for video processing.
- Twitch API and YouTube Data API for integration capabilities.
