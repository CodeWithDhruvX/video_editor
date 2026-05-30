"""
YouTube Uploader Service
Ported from video_uploading_v7.py — adapted for FastAPI with async progress callbacks.
"""

import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable, Awaitable

import pytz
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from models.schemas import CATEGORY_MAP, VideoUploadRequest

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

TOKEN_FILE = "token.json"

# Type alias for progress callbacks
ProgressCallback = Callable[[str, str, Optional[float]], Awaitable[None]]


# ─────────────────────────── Auth Helpers ───────────────────────────

def get_authenticated_service(client_secret_path: str) -> object:
    """
    Build and return an authenticated YouTube service object.
    Handles token refresh and OAuth flow via browser redirect.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        except Exception:
            creds = None
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)

    if not creds or not creds.valid:
        raise RuntimeError("Not authenticated. Please complete OAuth flow first.")

    return build("youtube", "v3", credentials=creds)


def start_oauth_flow(client_secret_path: str, redirect_uri: str) -> tuple[str, object]:
    """
    Start OAuth flow and return (auth_url, flow) for browser redirect.
    """
    flow = Flow.from_client_secrets_file(
        client_secret_path,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return auth_url, flow


def complete_oauth_flow(flow: object, auth_code: str) -> None:
    """
    Exchange auth code for credentials and save to token.json.
    """
    flow.fetch_token(code=auth_code)
    creds = flow.credentials
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())


def check_auth_status() -> dict:
    """Return authentication status dict."""
    if not os.path.exists(TOKEN_FILE):
        return {"authenticated": False, "channel_name": None, "message": "No token found. Please authenticate."}
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        if creds.valid:
            youtube = build("youtube", "v3", credentials=creds)
            ch = youtube.channels().list(part="snippet", mine=True).execute()
            items = ch.get("items", [])
            name = items[0]["snippet"]["title"] if items else "Unknown"
            return {"authenticated": True, "channel_name": name, "message": "Authenticated"}
        return {"authenticated": False, "channel_name": None, "message": "Credentials expired. Re-authenticate."}
    except Exception as e:
        return {"authenticated": False, "channel_name": None, "message": str(e)}


# ─────────────────────────── Time Conversion ───────────────────────────

def convert_ist_to_utc(ist_time_str: str) -> Optional[str]:
    """Convert IST datetime string to UTC RFC3339 format."""
    try:
        ist = pytz.timezone("Asia/Kolkata")
        local_time = datetime.strptime(ist_time_str, "%Y-%m-%d %H:%M:%S")
        local_time = ist.localize(local_time)
        utc_time = local_time.astimezone(pytz.utc)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


# ─────────────────────────── Playlist Helpers ───────────────────────────

def get_playlist_id(youtube, playlist_name: str) -> Optional[str]:
    """Get playlist ID by name; create if it doesn't exist."""
    try:
        response = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
        for playlist in response.get("items", []):
            if playlist["snippet"]["title"] == playlist_name:
                return playlist["id"]

        # Create new playlist
        created = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_name,
                    "description": f"Playlist for {playlist_name}",
                    "defaultLanguage": "en",
                },
                "status": {"privacyStatus": "public"},
            },
        ).execute()
        return created["id"]
    except Exception:
        return None


def add_video_to_playlist(youtube, video_id: str, playlist_id: str) -> None:
    """Add a video to a playlist."""
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()


def add_video_to_multiple_playlists(youtube, video_id: str, playlist_names: List[str]) -> None:
    for name in playlist_names:
        if not isinstance(name, str) or not name.strip():
            continue
        pid = get_playlist_id(youtube, name.strip())
        if pid:
            add_video_to_playlist(youtube, video_id, pid)


def get_all_playlists(youtube) -> List[dict]:
    """Return list of user's YouTube playlists."""
    try:
        response = youtube.playlists().list(
            part="snippet,contentDetails", mine=True, maxResults=50
        ).execute()
        return [
            {
                "id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
                "video_count": item["contentDetails"].get("itemCount", 0),
            }
            for item in response.get("items", [])
        ]
    except Exception:
        return []


def upload_thumbnail(youtube, video_id: str, thumbnail_path: str) -> None:
    """Upload a custom thumbnail for a video."""
    if os.path.exists(thumbnail_path):
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()


# ─────────────────────────── Core Upload Logic ───────────────────────────

async def upload_video(
    youtube,
    video_data: VideoUploadRequest,
    progress_cb: ProgressCallback,
) -> Optional[str]:
    """
    Upload a single video to YouTube with full metadata.
    Returns video_id on success, None on failure.
    Calls progress_cb(type, message, progress%) for real-time updates.
    """
    video_file = video_data.video_file_path
    if not video_file or not os.path.exists(video_file):
        await progress_cb("ERROR", f"❌ Video file not found: {video_file}", None)
        return None

    await progress_cb("LOG", f"📄 Uploading: {video_data.title}", None)

    category_id = CATEGORY_MAP.get(video_data.category_name, "22")

    request_body = {
        "snippet": {
            "title": video_data.title,
            "description": video_data.description,
            "tags": video_data.tags,
            "categoryId": category_id,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": video_data.privacy_status.value,
            "selfDeclaredMadeForKids": video_data.made_for_kids,
            "embeddable": True,
            "publicStatsViewable": True,
        },
    }

    if video_data.publish_at:
        utc_time = convert_ist_to_utc(video_data.publish_at)
        if utc_time:
            await progress_cb("LOG", f"📅 Scheduling for: {utc_time}", None)
            request_body["status"]["publishAt"] = utc_time
            request_body["status"]["privacyStatus"] = "private"

    try:
        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media,
        )

        response = None
        loop = asyncio.get_event_loop()

        def _do_chunk():
            return request.next_chunk()

        while response is None:
            status, response = await loop.run_in_executor(None, _do_chunk)
            if status:
                pct = round(status.progress() * 100, 1)
                await progress_cb("PROGRESS", f"🚀 Upload Progress: {pct}%", pct)

        video_id = response["id"]
        await progress_cb("LOG", f"✅ Uploaded: {video_data.title} (ID: {video_id})", None)

        # Upload thumbnail
        if video_data.thumbnail_path and os.path.exists(video_data.thumbnail_path):
            await progress_cb("LOG", "🖼️ Uploading thumbnail...", None)
            await loop.run_in_executor(
                None, lambda: upload_thumbnail(youtube, video_id, video_data.thumbnail_path)
            )
            await progress_cb("LOG", "✅ Thumbnail uploaded", None)

        # Add to playlists
        if video_data.playlist_names:
            await progress_cb("LOG", f"📋 Adding to playlists: {video_data.playlist_names}", None)
            await loop.run_in_executor(
                None,
                lambda: add_video_to_multiple_playlists(youtube, video_id, video_data.playlist_names),
            )

        return video_id

    except Exception as e:
        await progress_cb("ERROR", f"❌ Upload failed: {e}", None)
        return None


async def upload_batch(
    youtube,
    videos: List[VideoUploadRequest],
    progress_cb: ProgressCallback,
) -> dict:
    """Upload multiple videos sequentially with progress reporting."""
    total = len(videos)
    successful, failed = 0, 0

    for i, video in enumerate(videos, 1):
        overall_pct = round(((i - 1) / total) * 100, 1)
        await progress_cb(
            "STATUS",
            f"📦 Processing video {i}/{total}: {video.title}",
            overall_pct,
        )

        video_id = await upload_video(youtube, video, progress_cb)
        if video_id:
            successful += 1
        else:
            failed += 1

        if i < total:
            await progress_cb("LOG", "⏳ Waiting 10 seconds before next upload...", None)
            await asyncio.sleep(10)

    await progress_cb("LOG", f"📊 Done: {successful} succeeded, {failed} failed", 100.0)
    return {"successful": successful, "failed": failed, "total": total}
