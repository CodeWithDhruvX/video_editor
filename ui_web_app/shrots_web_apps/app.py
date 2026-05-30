from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import os
import threading
import queue
import uuid
import json
from datetime import datetime

# Import services
from services.video_processor import VideoProcessor
from services.youtube_service import YouTubeService

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'outputs')

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize services
video_processor = VideoProcessor()
youtube_service = YouTubeService()

# Store for background tasks
background_tasks = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video-processor')
def video_processor_page():
    return render_template('video_processor.html')

@app.route('/youtube-uploader')
def youtube_uploader_page():
    return render_template('youtube_uploader.html')

# API Routes
@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """Handle single video file upload"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        task_id = str(uuid.uuid4())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'task_id': task_id,
            'filepath': filepath
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/upload-multiple-videos', methods=['POST'])
def upload_multiple_videos():
    """Handle multiple video file uploads"""
    if 'videos' not in request.files:
        return jsonify({'error': 'No video files provided'}), 400
    
    files = request.files.getlist('videos')
    uploaded_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            task_id = str(uuid.uuid4())
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
            file.save(filepath)
            uploaded_files.append({
                'filename': filename,
                'task_id': task_id,
                'filepath': filepath
            })
    
    return jsonify({
        'success': True,
        'files': uploaded_files,
        'count': len(uploaded_files)
    })

@app.route('/api/process-video', methods=['POST'])
def process_video():
    """Process video with effects, subtitles, etc."""
    try:
        data = request.json
        task_id = str(uuid.uuid4())
        
        # Validate required fields
        if not data.get('video_path'):
            return jsonify({'error': 'Video path is required'}), 400
        
        # Create background task
        def process_task():
            try:
                background_tasks[task_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'message': 'Starting video processing',
                    'result': None,
                    'error': None
                }
                
                result = video_processor.process_video(
                    video_path=data['video_path'],
                    options=data.get('options', {}),
                    task_id=task_id
                )
                
                background_tasks[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Video processing completed',
                    'result': result,
                    'error': None
                }
            except Exception as e:
                background_tasks[task_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': 'Video processing failed',
                    'result': None,
                    'error': str(e)
                }
        
        # Start background task
        thread = threading.Thread(target=process_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Video processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/merge-videos', methods=['POST'])
def merge_videos():
    """Merge multiple videos"""
    try:
        data = request.json
        task_id = str(uuid.uuid4())
        
        if not data.get('video_paths') or not isinstance(data['video_paths'], list):
            return jsonify({'error': 'Video paths list is required'}), 400
        
        def merge_task():
            try:
                background_tasks[task_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'message': 'Starting video merge',
                    'result': None,
                    'error': None
                }
                
                result = video_processor.merge_videos(
                    video_paths=data['video_paths'],
                    extra_video=data.get('extra_video'),
                    background_music=data.get('background_music'),
                    output_path=os.path.join(app.config['OUTPUT_FOLDER'], f"merged_{task_id}.mp4"),
                    task_id=task_id
                )
                
                background_tasks[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Video merge completed',
                    'result': result,
                    'error': None
                }
            except Exception as e:
                background_tasks[task_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': 'Video merge failed',
                    'result': None,
                    'error': str(e)
                }
        
        thread = threading.Thread(target=merge_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Video merge started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-subtitles', methods=['POST'])
def add_subtitles():
    """Generate subtitles using Whisper"""
    try:
        data = request.json
        task_id = str(uuid.uuid4())
        
        if not data.get('video_path'):
            return jsonify({'error': 'Video path is required'}), 400
        
        def subtitle_task():
            try:
                background_tasks[task_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'message': 'Starting subtitle generation',
                    'result': None,
                    'error': None
                }
                
                result = video_processor.generate_subtitles(
                    video_path=data['video_path'],
                    language=data.get('language', 'en'),
                    output_path=os.path.join(app.config['OUTPUT_FOLDER'], f"subtitles_{task_id}.srt"),
                    task_id=task_id
                )
                
                background_tasks[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Subtitle generation completed',
                    'result': result,
                    'error': None
                }
            except Exception as e:
                background_tasks[task_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': 'Subtitle generation failed',
                    'result': None,
                    'error': str(e)
                }
        
        thread = threading.Thread(target=subtitle_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Subtitle generation started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# YouTube API Routes
@app.route('/api/youtube/authenticate', methods=['POST'])
def authenticate_youtube():
    """YouTube OAuth authentication"""
    try:
        data = request.json
        client_secret_file = data.get('client_secret_file')
        
        if not client_secret_file:
            return jsonify({'error': 'Client secret file is required'}), 400
        
        # Handle file upload if it's a file
        if 'client_secret_file' in request.files:
            file = request.files['client_secret_file']
            client_secret_file = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(client_secret_file)
        
        youtube_service = YouTubeService(client_secret_file)
        auth_url = youtube_service.get_auth_url()
        
        return jsonify({
            'success': True,
            'auth_url': auth_url,
            'message': 'Authentication URL generated'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/youtube/callback', methods=['POST'])
def youtube_callback():
    """Handle YouTube OAuth callback"""
    try:
        data = request.json
        auth_code = data.get('auth_code')
        client_secret_file = data.get('client_secret_file')
        
        if not auth_code:
            return jsonify({'error': 'Authorization code is required'}), 400
        
        youtube_service = YouTubeService(client_secret_file)
        credentials = youtube_service.get_credentials(auth_code)
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'credentials': {
                'authenticated': True,
                'email': credentials.get('email', 'N/A')
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/youtube/upload', methods=['POST'])
def upload_to_youtube():
    """Upload processed video to YouTube"""
    try:
        data = request.json
        task_id = str(uuid.uuid4())
        
        if not data.get('video_path'):
            return jsonify({'error': 'Video path is required'}), 400
        
        def upload_task():
            try:
                background_tasks[task_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'message': 'Starting YouTube upload',
                    'result': None,
                    'error': None
                }
                
                result = youtube_service.upload_video(
                    video_path=data['video_path'],
                    title=data.get('title', 'My Video'),
                    description=data.get('description', ''),
                    tags=data.get('tags', []),
                    category=data.get('category', '22'),
                    privacy_status=data.get('privacy_status', 'private'),
                    playlist_names=data.get('playlist_names', []),
                    thumbnail_path=data.get('thumbnail_path'),
                    publish_at=data.get('publish_at'),
                    task_id=task_id
                )
                
                background_tasks[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'YouTube upload completed',
                    'result': result,
                    'error': None
                }
            except Exception as e:
                background_tasks[task_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': 'YouTube upload failed',
                    'result': None,
                    'error': str(e)
                }
        
        thread = threading.Thread(target=upload_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'YouTube upload started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/youtube/playlists', methods=['GET'])
def get_playlists():
    """Get user playlists"""
    try:
        playlists = youtube_service.get_playlists()
        return jsonify({
            'success': True,
            'playlists': playlists
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Get processing status"""
    if task_id in background_tasks:
        return jsonify(background_tasks[task_id])
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/config/save', methods=['POST'])
def save_config():
    """Save current configuration"""
    try:
        data = request.json
        config_path = os.path.join(app.config['OUTPUT_FOLDER'], 'config.json')
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully',
            'path': config_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/load', methods=['GET'])
def load_config():
    """Load current configuration"""
    try:
        config_path = os.path.join(app.config['OUTPUT_FOLDER'], 'config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            return jsonify({
                'success': True,
                'config': config
            })
        else:
            return jsonify({
                'success': True,
                'config': {},
                'message': 'No saved configuration found'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed files"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)