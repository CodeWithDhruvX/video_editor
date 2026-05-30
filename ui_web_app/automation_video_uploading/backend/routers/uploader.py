"""
YouTube Uploader Router — FastAPI endpoints for YouTube OAuth and video uploads.
"""

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import RedirectResponse, JSONResponse

from models.schemas import (
    JobStatusResponse, JobStatus, VideoUploadRequest,
    BatchUploadMetadata, UploadJobResponse, AuthStatusResponse, PlaylistInfo
)
from services.youtube_uploader import (
    get_authenticated_service, start_oauth_flow, complete_oauth_flow,
    get_all_auth_statuses, get_all_playlists, upload_video, upload_batch,
    TOKENS_DIR
)

router = APIRouter(prefix="/uploader", tags=["uploader"])

# ─────────────────────────── Stores ───────────────────────────

_upload_jobs: Dict[str, Dict[str, Any]] = {}
_ws_connections: Dict[str, WebSocket] = {}
_oauth_flows: Dict[str, Any] = {}  # state -> flow

UPLOAD_DIR = Path("uploads/yt")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REDIRECT_URI = "http://localhost:8000/uploader/auth/callback"


# ─────────────────────────── WebSocket ───────────────────────────

@router.websocket("/ws/{job_id}")
async def uploader_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    _ws_connections[job_id] = websocket
    try:
        while True:
            job = _upload_jobs.get(job_id)
            if job and job["status"] in (JobStatus.complete, JobStatus.failed, JobStatus.stopped):
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.pop(job_id, None)


async def _send_ws(job_id: str, msg_type: str, message: str, progress=None):
    """Push message to WebSocket client."""
    job = _upload_jobs.get(job_id)
    if job is not None:
        job["logs"].append(f"[{msg_type}] {message}")
        if progress is not None:
            job["progress"] = progress
        if msg_type == "COMPLETE":
            job["status"] = JobStatus.complete
        elif msg_type in ("ERROR", "FAILED"):
            job["status"] = JobStatus.failed
        elif msg_type == "STOPPED":
            job["status"] = JobStatus.stopped

    ws = _ws_connections.get(job_id)
    if ws:
        try:
            await ws.send_json({"type": msg_type, "message": message, "progress": progress})
        except Exception:
            pass


# ─────────────────────────── Auth Endpoints ───────────────────────────

@router.post("/auth/upload-secret")
async def upload_client_secret(files: list[UploadFile] = File(...)):
    """Upload client_secret.json files from the user."""
    for file in files:
        content = await file.read()
        # Save each file with its original name to support multiple
        # If it doesn't end with .json, append it
        filename = file.filename
        if not filename.endswith(".json"):
            filename += ".json"
            
        with open(filename, "wb") as f:
            f.write(content)
            
        # Also save the last uploaded one as the default 'client_secret.json'
        # so that `start_oauth_flow` works out of the box with the default expected path
        with open("client_secret.json", "wb") as f:
            f.write(content)
            
    return {"message": f"{len(files)} client_secret file(s) uploaded successfully"}


@router.get("/auth/start")
async def start_auth():
    """Initiate YouTube OAuth flow — returns auth URL for browser redirect."""
    if not os.path.exists("client_secret.json"):
        raise HTTPException(status_code=400, detail="Upload client_secret.json first")
    try:
        auth_url, flow = start_oauth_flow("client_secret.json", REDIRECT_URI)
        state = str(uuid.uuid4())
        _oauth_flows[state] = flow
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/callback")
async def auth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth callback — exchange code for credentials."""
    try:
        # Try to find flow by state or use the most recent one
        flow = None
        if state and state in _oauth_flows:
            flow = _oauth_flows.pop(state)
        elif _oauth_flows:
            # Fallback: use the last flow
            last_state = list(_oauth_flows.keys())[-1]
            flow = _oauth_flows.pop(last_state)

        if flow is None:
            raise HTTPException(status_code=400, detail="OAuth flow not found. Please restart authentication.")

        complete_oauth_flow(flow, code)
        # Redirect to frontend success page
        return RedirectResponse(url="http://localhost:5173/uploader?auth=success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e}")


@router.get("/auth/status", response_model=AuthStatusResponse)
async def auth_status():
    """Check current YouTube authentication status."""
    result = get_all_auth_statuses()
    return AuthStatusResponse(**result)


@router.delete("/auth/logout")
async def logout(channel_id: str):
    """Remove stored token to force re-authentication for a specific channel."""
    token_path = TOKENS_DIR / f"{channel_id}.json"
    meta_path = TOKENS_DIR / f"{channel_id}_meta.json"
    if token_path.exists():
        token_path.unlink()
    if meta_path.exists():
        meta_path.unlink()
    return {"message": "Logged out successfully"}


# ─────────────────────────── Upload Endpoints ───────────────────────────

@router.post("/upload/single", response_model=UploadJobResponse)
async def upload_single(
    channel_id: str = Form(...),
    video_file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    metadata_json: str = Form(...),
):
    """
    Upload a single video to YouTube.
    Accepts multipart form: video file + optional thumbnail + JSON metadata.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save video
    video_path = str(job_dir / video_file.filename)
    content = await video_file.read()
    with open(video_path, "wb") as f:
        f.write(content)

    # Save thumbnail
    thumb_path = None
    if thumbnail:
        thumb_path = str(job_dir / thumbnail.filename)
        content = await thumbnail.read()
        with open(thumb_path, "wb") as f:
            f.write(content)

    # Parse metadata
    try:
        meta = json.loads(metadata_json)
        request_data = VideoUploadRequest(**meta)
        request_data.video_file_path = video_path
        if thumb_path:
            request_data.thumbnail_path = thumb_path
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid metadata: {e}")

    # Init job
    _upload_jobs[job_id] = {
        "status": JobStatus.running,
        "progress": 0.0,
        "logs": [],
    }

    async def _run():
        try:
            token_path = str(TOKENS_DIR / f"{channel_id}.json")
            youtube = get_authenticated_service("client_secret.json", token_path)

            async def cb(msg_type, message, progress):
                await _send_ws(job_id, msg_type, message, progress)

            video_id = await upload_video(youtube, request_data, cb)
            if video_id:
                await _send_ws(job_id, "COMPLETE",
                               f"🎉 Upload complete! Video ID: {video_id}", 100.0)
            else:
                await _send_ws(job_id, "ERROR", "❌ Upload failed", None)
        except Exception as e:
            await _send_ws(job_id, "ERROR", f"❌ {e}", None)

    asyncio.create_task(_run())

    return UploadJobResponse(job_id=job_id, status=JobStatus.running, message="Upload started")


@router.post("/upload/batch", response_model=UploadJobResponse)
async def upload_batch_endpoint(
    channel_id: str = Form(...),
    metadata_file: UploadFile = File(...),
    videos_dir: str = Form(...),
):
    """
    Batch upload from a metadata JSON file.
    videos_dir: server-side directory containing all video files.
    """
    job_id = str(uuid.uuid4())

    # Load metadata
    content = await metadata_file.read()
    try:
        metadata = json.loads(content)
        batch = BatchUploadMetadata(**metadata)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid metadata JSON: {e}")

    _upload_jobs[job_id] = {
        "status": JobStatus.running,
        "progress": 0.0,
        "logs": [],
    }

    async def _run():
        try:
            token_path = str(TOKENS_DIR / f"{channel_id}.json")
            youtube = get_authenticated_service("client_secret.json", token_path)

            async def cb(msg_type, message, progress):
                await _send_ws(job_id, msg_type, message, progress)

            result = await upload_batch(youtube, batch.videos, cb)
            await _send_ws(
                job_id, "COMPLETE",
                f"🎉 Batch done: {result['successful']}/{result['total']} succeeded",
                100.0,
            )
        except Exception as e:
            await _send_ws(job_id, "ERROR", f"❌ {e}", None)

    asyncio.create_task(_run())
    return UploadJobResponse(job_id=job_id, status=JobStatus.running, message="Batch upload started")


@router.post("/upload/batch-with-files", response_model=UploadJobResponse)
async def upload_batch_with_files(
    channel_id: str = Form(...),
    videos: list[UploadFile] = File(...),
    thumbnails: list[UploadFile] = File(None),
    metadata_json: str = Form(...),
):
    """
    Batch upload with actual video files uploaded through the browser.
    Metadata JSON maps filenames to upload details.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save all uploaded videos
    video_path_map = {}
    for vid in videos:
        dest = str(job_dir / vid.filename)
        content = await vid.read()
        with open(dest, "wb") as f:
            f.write(content)
        video_path_map[vid.filename] = dest

    # Save thumbnails
    thumb_path_map = {}
    if thumbnails:
        for thumb in thumbnails:
            dest = str(job_dir / thumb.filename)
            content = await thumb.read()
            with open(dest, "wb") as f:
                f.write(content)
            thumb_path_map[thumb.filename] = dest

    # Parse metadata and match paths
    try:
        meta = json.loads(metadata_json)
        batch = BatchUploadMetadata(**meta)
        for idx, v in enumerate(batch.videos):
            # Match by explicit video_file_path if provided by frontend mapping
            if v.video_file_path and v.video_file_path in video_path_map:
                v.video_file_path = video_path_map[v.video_file_path]
            # Fallback to match by order
            elif idx < len(videos):
                vid_filename = videos[idx].filename
                if vid_filename in video_path_map:
                    v.video_file_path = video_path_map[vid_filename]
            
            if v.thumbnail_path:
                tname = Path(v.thumbnail_path).name
                if tname in thumb_path_map:
                    v.thumbnail_path = thumb_path_map[tname]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid metadata: {e}")

    _upload_jobs[job_id] = {
        "status": JobStatus.running,
        "progress": 0.0,
        "logs": [],
    }

    async def _run():
        try:
            token_path = str(TOKENS_DIR / f"{channel_id}.json")
            youtube = get_authenticated_service("client_secret.json", token_path)

            async def cb(msg_type, message, progress):
                await _send_ws(job_id, msg_type, message, progress)

            result = await upload_batch(youtube, batch.videos, cb)
            await _send_ws(
                job_id, "COMPLETE",
                f"🎉 Batch done: {result['successful']}/{result['total']} succeeded",
                100.0,
            )
        except Exception as e:
            await _send_ws(job_id, "ERROR", f"❌ {e}", None)

    asyncio.create_task(_run())
    return UploadJobResponse(job_id=job_id, status=JobStatus.running, message="Batch upload started")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_upload_status(job_id: str):
    """Poll upload job status."""
    job = _upload_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        logs=job["logs"][-50:],
    )


@router.get("/playlists")
async def list_playlists(channel_id: str):
    """List user's YouTube playlists."""
    try:
        token_path = str(TOKENS_DIR / f"{channel_id}.json")
        youtube = get_authenticated_service("client_secret.json", token_path)
        playlists = get_all_playlists(youtube)
        return playlists
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_categories():
    """Return YouTube category map."""
    from models.schemas import CATEGORY_MAP
    return [{"name": k, "id": v} for k, v in CATEGORY_MAP.items()]
