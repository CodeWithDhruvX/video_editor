import os
import json
import time
from datetime import datetime
import pytz
from tkinter import Tk, filedialog, messagebox
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Constants
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
CATEGORY_MAP = {
    "Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10", "Pets & Animals": "15",
    "Sports": "17", "Travel & Events": "19", "Gaming": "20", "People & Blogs": "22", "Comedy": "23",
    "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26", "Education": "27",
    "Science & Technology": "28", "Nonprofits & Activism": "29"
}

def select_file_dialog(title="Select File"):
    try:
        root = Tk()
        root.withdraw()           # Hide the main window
        root.attributes('-topmost', True)  # Bring dialog to front
        root.update()             # Ensure window appears
        file_path = filedialog.askopenfilename(title=title)
        root.destroy()
        
        if not file_path:
            messagebox.showerror("Error", f"{title} not selected!")
            exit()
        return file_path

    except Exception as e:
        print(f"❌ Failed to open file dialog: {e}")
        exit()


def get_authenticated_service(client_secret_file):
    """Enhanced authentication with proper token refresh handling"""
    creds = None
    token_file = "token.json"

    # Load existing credentials
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            print("📋 Found existing credentials")
        except Exception as e:
            print(f"⚠️ Error loading existing credentials: {e}")
            # Remove corrupted token file
            if os.path.exists(token_file):
                os.remove(token_file)
            creds = None

    # Check if credentials are valid and refresh if needed
    if creds and creds.expired and creds.refresh_token:
        try:
            print("🔄 Refreshing expired credentials...")
            creds.refresh(Request())
            print("✅ Credentials refreshed successfully")

            # Save refreshed credentials
            with open(token_file, "w") as token:
                token.write(creds.to_json())

        except Exception as e:
            print(f"⚠️ Error refreshing credentials: {e}")
            creds = None
            # Remove failed token file
            if os.path.exists(token_file):
                os.remove(token_file)

    # If no valid credentials available, run the OAuth flow
    if not creds or not creds.valid:
        print("🔐 Running authentication flow...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0, prompt='consent')

            # Save the credentials for the next run
            with open(token_file, "w") as token:
                token.write(creds.to_json())
            print("✅ New credentials saved successfully")

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            exit()

    return build("youtube", "v3", credentials=creds)

def convert_ist_to_utc(ist_time_str):
    """Convert IST time to UTC format for YouTube API"""
    try:
        ist = pytz.timezone("Asia/Kolkata")
        local_time = datetime.strptime(ist_time_str, "%Y-%m-%d %H:%M:%S")
        local_time = ist.localize(local_time)
        utc_time = local_time.astimezone(pytz.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        print(f"⚠️ Error converting time: {e}")
        return None

def get_playlist_id(youtube, playlist_name):
    """Get playlist ID by name, create if doesn't exist"""
    try:
        request = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
        response = request.execute()

        for playlist in response.get("items", []):
            if playlist["snippet"]["title"] == playlist_name:
                print(f"📋 Found existing playlist: {playlist_name}")
                return playlist["id"]

        print(f"🌟 Creating new playlist: {playlist_name}")
        create_request = youtube.playlists().insert(
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
        print(f"❌ Error handling playlist: {e}")
        return None

def add_video_to_playlist(youtube, video_id, playlist_id):
    """Add video to specified playlist"""
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}
                }
            }
        ).execute()
        print(f"✅ Video added to playlist successfully")
    except Exception as e:
        print(f"❌ Failed to add video to playlist: {e}")

def add_video_to_multiple_playlists(youtube, video_id, playlist_names):
    """Add video to multiple playlists"""
    for pname in playlist_names:
        if not isinstance(pname, str) or not pname.strip():
            print(f"⚠️ Skipping invalid playlist name: {pname}")
            continue
        playlist_id = get_playlist_id(youtube, pname.strip())
        if playlist_id:
            add_video_to_playlist(youtube, video_id, playlist_id)

def upload_thumbnail(youtube, video_id, thumbnail_path):
    """Upload custom thumbnail for video"""
    if os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print(f"✅ Thumbnail uploaded successfully")
        except Exception as e:
            print(f"❌ Failed to upload thumbnail: {e}")
    else:
        print(f"❌ Thumbnail file not found: {thumbnail_path}")

def upload_video(youtube, video_data):
    """Upload a single video with all metadata"""
    video_file = video_data["videoFile"]
    if not os.path.exists(video_file):
        print(f"❌ Video file not found: {video_file}")
        return None

    print(f"📄 Uploading: {video_data['title']}")
    category_id = CATEGORY_MAP.get(video_data["categoryName"], "22")

    request_body = {
        "snippet": {
            "title": video_data["title"],
            "description": video_data["description"],
            "tags": video_data.get("tags", []),
            "categoryId": category_id,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en"
        },
        "status": {
            "privacyStatus": video_data["privacyStatus"],
            "selfDeclaredMadeForKids": video_data.get("madeForKids", False),
            "embeddable": True,
            "publicStatsViewable": True,
        },
        "recordingDetails": {
            "location": {"latitude": 28.6139, "longitude": 77.2090}
        }
    }

    # Handle scheduled publishing
    if video_data.get("publishAt"):
        utc_publish_time = convert_ist_to_utc(video_data["publishAt"])
        if utc_publish_time:
            print(f"📅 Scheduling video for: {utc_publish_time}")
            request_body["status"]["publishAt"] = utc_publish_time
            request_body["status"]["privacyStatus"] = "private"

    try:
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status,recordingDetails",
            body=request_body,
            media_body=media
        )

        response = None
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"🚀 Upload Progress: {int(status.progress() * 100)}%")
            except Exception as e:
                print(f"❌ Upload error: {e}")
                return None

        video_id = response["id"]
        print(f"✅ Video uploaded successfully: {video_data['title']} (ID: {video_id})")

        # Upload thumbnail if provided
        if "thumbnail" in video_data and video_data["thumbnail"]:
            upload_thumbnail(youtube, video_id, video_data["thumbnail"])

        # Add to multiple playlists if specified
        playlist_names = (
            video_data.get("playlistNames") or
            video_data.get("playlistName") or
            video_data.get("playlists") or
            []
        )
        if isinstance(playlist_names, str):
            playlist_names = [playlist_names]

        if isinstance(playlist_names, list) and playlist_names:
            add_video_to_multiple_playlists(youtube, video_id, playlist_names)

        return video_id

    except Exception as e:
        print(f"❌ Failed to upload video: {e}")
        return None

def main():
    print("🚀 YouTube Bulk Uploader Started")
    print("=" * 50)

    # Select client secret file
    print("📁 Please select your client_secret.json file")
    client_secret_file = select_file_dialog("Select client_secret.json")

    # Select metadata file
    print("📁 Please select your metadata JSON file")
    metadata_file = select_file_dialog("Select metadata.json")

    # Load metadata
    try:
        with open(metadata_file, "r", encoding="utf-8") as file:
            metadata = json.load(file)
    except Exception as e:
        print(f"❌ Error reading metadata file: {e}")
        exit()

    if "videos" not in metadata or not metadata["videos"]:
        print("❌ No videos found in metadata file!")
        exit()

    print(f"📊 Found {len(metadata['videos'])} video(s) to upload")

    # Authenticate once
    try:
        youtube = get_authenticated_service(client_secret_file)
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        exit()

    # Upload videos
    successful_uploads = 0
    failed_uploads = 0

    for i, video in enumerate(metadata["videos"], 1):
        print(f"\n🎩 Processing video {i}/{len(metadata['videos'])}")
        print("-" * 30)

        video_id = upload_video(youtube, video)
        if video_id:
            successful_uploads += 1
        else:
            failed_uploads += 1

        # Wait between uploads to avoid rate limiting
        if i < len(metadata["videos"]):
            print("⏳ Waiting 10 seconds before next upload...")
            time.sleep(10)

    # Final summary
    print("\n" + "=" * 50)
    print("📊 UPLOAD SUMMARY")
    print(f"✅ Successful uploads: {successful_uploads}")
    print(f"❌ Failed uploads: {failed_uploads}")
    print(f"📋 Total videos processed: {len(metadata['videos'])}")
    print("🎉 Bulk upload completed!")

if __name__ == "__main__":
    main()