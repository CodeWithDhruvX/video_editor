import os
import json
import time
from datetime import datetime
import pytz
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

CATEGORY_MAP = {
    "Film & Animation": "1",
    "Autos & Vehicles": "2",
    "Music": "10",
    "Pets & Animals": "15",
    "Sports": "17",
    "Travel & Events": "19",
    "Gaming": "20",
    "People & Blogs": "22",
    "Comedy": "23",
    "Entertainment": "24",
    "News & Politics": "25",
    "Howto & Style": "26",
    "Education": "27",
    "Science & Technology": "28",
    "Nonprofits & Activism": "29"
}

class YouTubeService:
    def __init__(self, client_secret_file=None):
        """
        Initialize YouTube service
        
        Args:
            client_secret_file: Path to OAuth client secret JSON file
        """
        self.client_secret_file = client_secret_file
        self.youtube = None
        self.creds = None
        
        if client_secret_file:
            self.authenticate()
    
    def authenticate(self, client_secret_file=None):
        """
        Authenticate with YouTube using OAuth
        
        Args:
            client_secret_file: Path to OAuth client secret JSON file
        """
        if client_secret_file:
            self.client_secret_file = client_secret_file
        
        if not self.client_secret_file:
            raise ValueError("Client secret file is required for authentication")
        
        token_file = "token.json"
        
        # Load existing credentials
        if os.path.exists(token_file):
            try:
                self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)
                logger.info("Found existing credentials")
            except Exception as e:
                logger.warning(f"Error loading existing credentials: {e}")
                if os.path.exists(token_file):
                    os.remove(token_file)
                self.creds = None
        
        # Check if credentials are valid and refresh if needed
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                logger.info("Refreshing expired credentials...")
                self.creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
                
                # Save refreshed credentials
                with open(token_file, "w") as token:
                    token.write(self.creds.to_json())
                
            except Exception as e:
                logger.warning(f"Error refreshing credentials: {e}")
                self.creds = None
                if os.path.exists(token_file):
                    os.remove(token_file)
        
        # If no valid credentials available, authentication is needed
        if not self.creds or not self.creds.valid:
            logger.info("Authentication required - no valid credentials found")
            return False
        
        # Build YouTube service
        self.youtube = build("youtube", "v3", credentials=self.creds)
        return True
    
    def get_auth_url(self):
        """
        Get OAuth authorization URL for user to authorize
        
        Returns:
            Authorization URL string
        """
        if not self.client_secret_file:
            raise ValueError("Client secret file is required")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secret_file, 
                SCOPES
            )
            # For web app, we'd use redirect_uri, but for now return flow info
            logger.info("Authentication flow prepared")
            return "https://accounts.google.com/o/oauth2/auth"
        except Exception as e:
            logger.error(f"Failed to create auth flow: {e}")
            raise
    
    def get_credentials(self, auth_code):
        """
        Exchange authorization code for credentials
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            Credentials object
        """
        if not self.client_secret_file:
            raise ValueError("Client secret file is required")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secret_file,
                SCOPES,
                redirect_uri='http://localhost:5000/youtube/callback'
            )
            
            flow.fetch_token(code=auth_code)
            self.creds = flow.credentials
            
            # Save credentials for future use
            token_file = "token.json"
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())
            
            logger.info("Credentials saved successfully")
            
            # Build YouTube service
            self.youtube = build("youtube", "v3", credentials=self.creds)
            
            return self.creds
            
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            raise
    
    def convert_ist_to_utc(self, ist_time_str):
        """
        Convert IST time to UTC format for YouTube API
        
        Args:
            ist_time_str: Time string in format "YYYY-MM-DD HH:MM:SS"
            
        Returns:
            UTC formatted time string or None if conversion fails
        """
        try:
            ist = pytz.timezone("Asia/Kolkata")
            local_time = datetime.strptime(ist_time_str, "%Y-%m-%d %H:%M:%S")
            local_time = ist.localize(local_time)
            utc_time = local_time.astimezone(pytz.utc)
            return utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            logger.error(f"Error converting time: {e}")
            return None
    
    def get_playlist_id(self, playlist_name):
        """
        Get playlist ID by name, create if doesn't exist
        
        Args:
            playlist_name: Name of the playlist
            
        Returns:
            Playlist ID string or None if failed
        """
        try:
            request = self.youtube.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            )
            response = request.execute()
            
            for playlist in response.get("items", []):
                if playlist["snippet"]["title"] == playlist_name:
                    logger.info(f"Found existing playlist: {playlist_name}")
                    return playlist["id"]
            
            logger.info(f"Creating new playlist: {playlist_name}")
            create_request = self.youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": playlist_name,
                        "description": f"Playlist for {playlist_name}",
                        "defaultLanguage": "en"
                    },
                    "status": {"privacyStatus": "public"}
                }
            )
            return create_request.execute()["id"]
            
        except Exception as e:
            logger.error(f"Error handling playlist: {e}")
            return None
    
    def add_video_to_playlist(self, video_id, playlist_id):
        """
        Add video to specified playlist
        
        Args:
            video_id: YouTube video ID
            playlist_id: YouTube playlist ID
        """
        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
            logger.info("Video added to playlist successfully")
        except Exception as e:
            logger.error(f"Failed to add video to playlist: {e}")
    
    def add_video_to_multiple_playlists(self, video_id, playlist_names):
        """
        Add video to multiple playlists
        
        Args:
            video_id: YouTube video ID
            playlist_names: List of playlist names
        """
        for pname in playlist_names:
            if not isinstance(pname, str) or not pname.strip():
                logger.warning(f"Skipping invalid playlist name: {pname}")
                continue
            playlist_id = self.get_playlist_id(pname.strip())
            if playlist_id:
                self.add_video_to_playlist(video_id, playlist_id)
    
    def upload_thumbnail(self, video_id, thumbnail_path):
        """
        Upload custom thumbnail for video
        
        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image file
        """
        if os.path.exists(thumbnail_path):
            try:
                self.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                logger.info("Thumbnail uploaded successfully")
            except Exception as e:
                logger.error(f"Failed to upload thumbnail: {e}")
        else:
            logger.error(f"Thumbnail file not found: {thumbnail_path}")
    
    def upload_video(self, video_path, title, description="", tags=None, 
                    category="22", privacy_status="private", 
                    made_for_kids=False, playlist_names=None, 
                    thumbnail_path=None, publish_at=None, task_id=None):
        """
        Upload video to YouTube with all metadata
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of video tags
            category: Video category ID
            privacy_status: Privacy status (private, public, unlisted)
            made_for_kids: Whether video is made for kids
            playlist_names: List of playlist names to add video to
            thumbnail_path: Path to custom thumbnail
            publish_at: Scheduled publish time (IST format: YYYY-MM-DD HH:MM:SS)
            task_id: Optional task ID for logging
            
        Returns:
            Dictionary with upload results including video ID
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            if not self.youtube:
                raise Exception("YouTube service not authenticated")
            
            logger.info(f"Uploading: {title}")
            
            tags = tags or []
            category_id = CATEGORY_MAP.get(category, "22")
            
            # Build request body
            request_body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id,
                    "defaultLanguage": "en",
                    "defaultAudioLanguage": "en"
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": made_for_kids,
                    "embeddable": True,
                    "publicStatsViewable": True,
                },
                "recordingDetails": {
                    "location": {"latitude": 28.6139, "longitude": 77.2090}
                }
            }
            
            # Handle scheduled publishing
            if publish_at:
                utc_publish_time = self.convert_ist_to_utc(publish_at)
                if utc_publish_time:
                    logger.info(f"Scheduling video for: {utc_publish_time}")
                    request_body["status"]["publishAt"] = utc_publish_time
                    request_body["status"]["privacyStatus"] = "private"
            
            # Upload video
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = self.youtube.videos().insert(
                part="snippet,status,recordingDetails",
                body=request_body,
                media_body=media
            )
            
            response = None
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        logger.info(f"Upload progress: {int(status.progress() * 100)}%")
                except Exception as chunk_error:
                    logger.error(f"Upload chunk error: {chunk_error}")
                    raise
            
            video_id = response["id"]
            logger.info(f"Video uploaded successfully: {video_id}")
            
            # Add to playlists if specified
            if playlist_names:
                self.add_video_to_multiple_playlists(video_id, playlist_names)
            
            # Upload thumbnail if provided
            if thumbnail_path:
                self.upload_thumbnail(video_id, thumbnail_path)
            
            return {
                'success': True,
                'video_id': video_id,
                'title': title,
                'message': 'Video uploaded successfully'
            }
            
        except Exception as e:
            logger.error(f"Video upload failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Video upload failed'
            }
    
    def get_playlists(self):
        """
        Get all user's playlists
        
        Returns:
            List of playlist dictionaries
        """
        try:
            if not self.youtube:
                raise Exception("YouTube service not authenticated")
            
            request = self.youtube.playlists().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=50
            )
            response = request.execute()
            
            playlists = []
            for playlist in response.get("items", []):
                playlists.append({
                    'id': playlist['id'],
                    'title': playlist['snippet']['title'],
                    'description': playlist['snippet'].get('description', ''),
                    'video_count': playlist['contentDetails']['itemCount']
                })
            
            logger.info(f"Retrieved {len(playlists)} playlists")
            return playlists
            
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            return []
    
    def get_video_status(self, video_id):
        """
        Get status of uploaded video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video status information
        """
        try:
            if not self.youtube:
                raise Exception("YouTube service not authenticated")
            
            request = self.youtube.videos().list(
                part="status,snippet",
                id=video_id
            )
            response = request.execute()
            
            if response.get("items"):
                video = response["items"][0]
                return {
                    'id': video['id'],
                    'title': video['snippet']['title'],
                    'privacy_status': video['status']['privacyStatus'],
                    'upload_status': video['status'].get('uploadStatus', 'unknown'),
                    'processing_status': video['status'].get('processingStatus', 'unknown')
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get video status: {e}")
            return None