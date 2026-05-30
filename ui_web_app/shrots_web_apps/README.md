# Video Processor Pro - Web Application

A web-based video processing application that combines the functionality of video editing and YouTube uploading, featuring speech recognition capabilities.

## Features

### Video Processing
- Upload and process multiple videos
- Merge multiple videos together
- Add background music with volume control
- AI-powered subtitle generation using Whisper
- Add text effects and overlays
- Customizable output formats (MP4, AVI, MOV, WebM)
- Real-time processing status and progress tracking
- Configuration save/load functionality

### YouTube Integration
- OAuth authentication with YouTube
- Direct video upload to YouTube
- Custom video metadata (title, description, tags, category)
- Playlist management (auto-create if needed)
- Custom thumbnail upload
- Scheduled publishing
- Privacy status control
- Made for kids compliance

## Project Structure

```
shrots_web_apps/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── README.md                       # This file
├── templates/                      # HTML templates
│   ├── base.html                   # Base template
│   ├── index.html                  # Home page
│   ├── video_processor.html        # Video processing interface
│   └── youtube_uploader.html       # YouTube upload interface
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css              # Custom styles
│   └── js/
│       └── main.js                # JavaScript utilities
├── services/                       # Business logic
│   ├── video_processor.py         # Video processing service
│   ├── youtube_service.py         # YouTube API service
│   └── whisper_service.py         # Speech recognition service
├── utils/                          # Utility modules
│   ├── config_manager.py          # Configuration management
│   ├── file_handler.py            # File upload/download handling
│   └── logger.py                  # Logging utilities
└── config/                         # Configuration files
    ├── settings.py                # Application settings
    └── __init__.py
└── uploads/                       # Uploaded files directory
└── outputs/                       # Processed files directory
```

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed and accessible from command line
- pip package manager

### Setup

1. Navigate to the project directory:
```bash
cd shrots_web_apps
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Install FFmpeg:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt install ffmpeg`

6. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Running the Application

1. Start the Flask application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Configuration

### Environment Variables

Edit the `.env` file to configure the application:

- `SECRET_KEY`: Flask secret key for session management
- `DEBUG`: Enable debug mode (True/False)
- `MAX_FILE_SIZE_MB`: Maximum upload file size in MB
- `WHISPER_MODEL_SIZE`: Whisper model size (tiny, base, small, medium, large)
- `DEFAULT_PRIVACY_STATUS`: Default YouTube privacy status

### YouTube Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: http://localhost:5000/youtube/callback
5. Download the client secret JSON file
6. Upload it through the YouTube Uploader interface

## Usage

### Video Processing

1. Navigate to "Video Processor" page
2. Upload one or more videos
3. Configure processing options:
   - Enable video merging
   - Add background music
   - Generate subtitles
   - Add text effects
4. Click "Process Video" or "Merge Videos"
5. Monitor progress in the status panel
6. Download processed videos when complete

### YouTube Upload

1. Navigate to "YouTube Uploader" page
2. Authenticate with YouTube (first time only)
3. Select video file to upload
4. Enter video metadata:
   - Title (required)
   - Description
   - Tags (comma-separated)
   - Category
   - Privacy status
5. Configure advanced options:
   - Custom thumbnail
   - Scheduled publishing
   - Playlist addition
6. Click "Upload to YouTube"
7. Monitor upload progress
8. View uploaded video on YouTube

## API Endpoints

### Video Processing
- `POST /api/upload-video` - Upload single video
- `POST /api/upload-multiple-videos` - Upload multiple videos
- `POST /api/process-video` - Process video with effects
- `POST /api/merge-videos` - Merge multiple videos
- `POST /api/add-subtitles` - Generate subtitles
- `GET /api/status/<task_id>` - Get processing status

### YouTube
- `POST /api/youtube/authenticate` - YouTube OAuth authentication
- `POST /api/youtube/callback` - OAuth callback handler
- `POST /api/youtube/upload` - Upload video to YouTube
- `GET /api/youtube/playlists` - Get user playlists

### Configuration
- `POST /api/config/save` - Save current configuration
- `GET /api/config/load` - Load saved configuration

### File Download
- `GET /download/<filename>` - Download processed files

## Troubleshooting

### FFmpeg not found
- Ensure FFmpeg is installed and added to system PATH
- Test with `ffmpeg -version` in command line

### Whisper model download fails
- Check internet connection
- Ensure sufficient disk space for model download
- Try smaller model size in settings

### YouTube authentication fails
- Verify client secret JSON file is correct
- Check redirect URI matches: http://localhost:5000/youtube/callback
- Ensure YouTube Data API v3 is enabled in Google Cloud Console

### Large file uploads fail
- Increase `MAX_CONTENT_LENGTH` in app.py
- Check available disk space
- Verify file size doesn't exceed limits

## Development

### Adding New Features

1. Add routes in `app.py`
2. Create service functions in `services/`
3. Add UI components in `templates/`
4. Update JavaScript in `static/js/main.js`

### Testing

Run tests (if available):
```bash
pytest
```

### Code Style

Follow PEP 8 guidelines for Python code.
Use existing patterns for consistency.

## License

This project combines functionality from original GUI applications and has been converted to a web-based interface.

## Credits

Based on:
- `short_gui_v8.py` - Original Tkinter-based video processor
- `video_uploading_v7.py` - Original YouTube upload script

Technologies used:
- Flask - Web framework
- faster-whisper - Speech recognition
- ffmpeg-python - Video processing
- google-api-python-client - YouTube API
- Bootstrap - UI framework