# Video Editor & Transcription Tool

A powerful Python-based video editing and transcription tool that uses Whisper AI for fast speech-to-text conversion with advanced subtitle generation capabilities.

## 🚀 Features

### Core Functionality
- **Fast Video Transcription** - Uses `faster_whisper` with optimized models (large-v3, small, tiny fallback)
- **GPU Acceleration** - NVENC support for faster processing
- **Multiple Subtitle Modes**:
  - Word-by-word display
  - Grouped subtitles (customizable word count)
  - Mixed font styling with effects
- **Smart Audio Processing** - Music ducking during speech segments
- **Batch Processing** - Handle multiple videos simultaneously

### Advanced Features
- **Speech Border Boxes** - Visual highlighting of spoken words
- **Audio Extraction/Replacement** - Extract audio from videos or replace audio tracks
- **YouTube Integration** - Upload videos and manage playlists
- **PPT Generation** - Create presentations from video content
- **Multiple GUI Interfaces** - Choose from different UI versions

## 📋 Prerequisites

### Python Requirements
```bash
pip install faster-whisper
pip install moviepy
pip install ffmpeg-python
pip install tkinter
pip install google-auth-oauthlib
pip install google-api-python-client
pip install python-pptx
pip install beautifulsoup4
pip install markdown2
pip install pyperclip
```

### System Requirements
- **Python 3.8+**
- **FFmpeg** (must be installed and in system PATH)
- **GPU** (optional, for faster transcription with CUDA)

#### Installing FFmpeg
**Windows:**
```bash
# Using chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
# Add to system PATH
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

## 🚀 Quick Start

### Main Entry Point (Recommended)
```bash
cd "v1/editors"
python short_gui_final.py
```

### Alternative GUI Options
```bash
# Version 8 GUI
python short_gui_v8.py

# Version 16/17 GUI  
python v16.py
python v17.py

# Audio Tools
python audio_replacer.py

# YouTube Upload
python video_uploading_gui_v2.py

# Playlist Manager
python playlist_gui_v1.py
```

## 🎯 Usage Guide

### For Video Transcription
1. **Launch the GUI**: Run `short_gui_final.py`
2. **Select Videos**: Click "Select Videos" to choose your video files
3. **Configure Settings**:
   - Enable "GPU Acceleration" if available
   - Choose subtitle mode (word-by-word, grouped, mixed)
   - Set speech borders and visual effects
   - Adjust subtitle size and colors
4. **Start Processing**: Click "Start Processing" to begin transcription
5. **Output**: Transcribed subtitles will be saved in your chosen output directory

### For Audio Operations
1. **Launch Audio Tool**: Run `audio_replacer.py`
2. **Extract Audio**: Use "Extract Audio from Videos" to get audio files
3. **Replace Audio**: Use "Replace Audio in Videos" to swap audio tracks
4. **Merge Videos**: Combine multiple video files

### For YouTube Integration
1. **Launch Upload GUI**: Run `video_uploading_gui_v2.py`
2. **Authenticate**: Connect your YouTube account
3. **Upload Videos**: Select videos and add metadata
4. **Manage Playlists**: Use `playlist_gui_v1.py` for playlist organization

## ⚡ Performance Tips

### For Faster Transcription
- **Use GPU acceleration** (NVENC) if available
- **Start with "small" Whisper model** for speed, upgrade to "large-v3" for accuracy
- **Process videos in batches** to optimize resource usage
- **Close other applications** to free up memory
- **Use SSD storage** for faster file I/O

### Model Selection
- **tiny**: Fastest, lower accuracy
- **small**: Good balance of speed and accuracy
- **large-v3**: Highest accuracy, slower processing

## 🔧 Configuration

### Transcription Settings
- **Language**: Auto-detect or specify (default: English)
- **Beam Size**: 1 for speed, higher for accuracy
- **Word Timestamps**: Enabled for precise subtitle timing
- **Conditional Text**: Disabled for faster processing

### Subtitle Customization
- **Font Styles**: Impact, Arial Black, Comic Sans MS, Times New Roman
- **Effects**: Bold, italic, border boxes
- **Colors**: Customizable text and border colors
- **Position**: Adjustable subtitle placement

## 📁 Project Structure

```
video_editor/
├── v1/
│   ├── editors/           # Main GUI applications
│   │   ├── short_gui_final.py    # Primary transcription tool
│   │   ├── short_gui_v8.py       # Alternative GUI
│   │   ├── v16.py, v17.py        # Version variants
│   │   ├── audio_replacer.py     # Audio extraction/replacement
│   │   ├── video_uploading_gui_v2.py  # YouTube upload
│   │   └── playlist_gui_v1.py    # Playlist management
│   ├── prompt/           # AI prompts and templates
│   └── generation/       # Content generation tools
└── shortcuts/            # Quick access scripts
```

## 🐛 Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Verify installation
ffmpeg -version

# Add to PATH if not found
# Windows: Add to System Environment Variables
# Linux/macOS: Add to ~/.bashrc or ~/.zshrc
```

**GPU not detected:**
- Install CUDA toolkit from NVIDIA
- Update GPU drivers
- Check CUDA compatibility with PyTorch

**Memory errors:**
- Process smaller video files
- Close other applications
- Use "tiny" or "small" Whisper models
- Increase system RAM or use swap file

**Slow transcription:**
- Enable GPU acceleration
- Use smaller Whisper models
- Reduce video quality before processing
- Process one video at a time

### Error Messages

**"Required tools not found":**
- Install FFmpeg and ensure it's in PATH
- Install all Python dependencies

**"Whisper model loading failed":**
- Check internet connection for first-time download
- Try smaller model (tiny, small)
- Verify sufficient disk space

**"GPU acceleration not available":**
- Install CUDA-compatible PyTorch
- Check GPU driver compatibility
- Fall back to CPU processing

## 📝 License

This project is for educational and personal use. Please respect the licenses of all dependencies.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Ensure FFmpeg is properly configured
4. Test with a small video file first
