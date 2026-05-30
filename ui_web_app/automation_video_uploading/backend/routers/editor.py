"""
Video Editor Router — FastAPI endpoints for video processing jobs.
"""

import asyncio
import json
import os
import uuid
import traceback
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from models.schemas import JobStatusResponse, JobStatus, VideoEditConfig
from services.video_processor import process_all_videos, transcribe_video

router = APIRouter(prefix="/editor", tags=["editor"])

# ─────────────────────────── In-Memory Job Store ───────────────────────────

_jobs: Dict[str, Dict[str, Any]] = {}
_ws_connections: Dict[str, WebSocket] = {}

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────── WebSocket ───────────────────────────

@router.websocket("/ws/{job_id}")
async def editor_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    _ws_connections[job_id] = websocket
    try:
        # Keep alive until job finishes or client disconnects
        while True:
            job = _jobs.get(job_id)
            if job and job["status"] in (JobStatus.complete, JobStatus.failed, JobStatus.stopped):
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.pop(job_id, None)


async def _send_ws(job_id: str, msg_type: str, message: str, progress=None):
    """Push a message to the WebSocket client for a job."""
    job = _jobs.get(job_id)
    if job is not None:
        job["logs"].append(f"[{msg_type}] {message}")
        if progress is not None:
            job["progress"] = progress

        # Update status based on type
        if msg_type == "COMPLETE":
            job["status"] = JobStatus.complete
        elif msg_type in ("ERROR", "FAILED"):
            job["status"] = JobStatus.failed
        elif msg_type == "STOPPED":
            job["status"] = JobStatus.stopped

    ws = _ws_connections.get(job_id)
    if ws:
        try:
            await ws.send_json({
                "type": msg_type,
                "message": message,
                "progress": progress,
            })
        except Exception:
            pass


# ─────────────────────────── Endpoints ───────────────────────────

@router.post("/transcribe")
async def transcribe_video_endpoint(video: UploadFile = File(...)):
    """
    Transcribe a single video file and return the word-level transcript.
    """
    import tempfile
    
    # Save uploaded video to temp file
    suffix = Path(video.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name
        
    try:
        # Dummy progress callback
        async def dummy_cb(msg_type: str, msg: str, prog: float = None):
            pass
            
        words = await transcribe_video(tmp_path, dummy_cb)
        return {"words": words}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/process", response_model=JobStatusResponse)
async def start_processing(
    videos: list[UploadFile] = File(...),
    extra_video: UploadFile = File(None),
    background_music: UploadFile = File(None),
    config_json: str = Form("{}"),
):
    """
    Start a video editing job.
    Accepts multipart form data with video files and a JSON config string.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    output_job_dir = OUTPUT_DIR / job_id
    output_job_dir.mkdir(parents=True, exist_ok=True)

    # Parse config
    try:
        raw_config = json.loads(config_json)
        edit_config = VideoEditConfig(**raw_config)
    except Exception:
        edit_config = VideoEditConfig()

    # Save uploaded video files
    video_paths = []
    for vid in videos:
        dest = job_dir / vid.filename
        content = await vid.read()
        dest.write_bytes(content)
        video_paths.append(str(dest))

    extra_path = None
    if extra_video:
        dest = job_dir / extra_video.filename
        content = await extra_video.read()
        dest.write_bytes(content)
        extra_path = str(dest)

    music_path = None
    if background_music:
        dest = job_dir / background_music.filename
        content = await background_music.read()
        dest.write_bytes(content)
        music_path = str(dest)

    stop_event = asyncio.Event()

    # Init job record
    _jobs[job_id] = {
        "status": JobStatus.running,
        "progress": 0.0,
        "logs": [],
        "output_files": [],
        "stop_event": stop_event,
    }

    # Launch processing in background
    async def _run():
        try:
            async def cb(msg_type, message, progress):
                await _send_ws(job_id, msg_type, message, progress)

            output_files = await process_all_videos(
                input_videos=video_paths,
                extra_video=extra_path if edit_config.enable_merge else None,
                output_dir=str(output_job_dir),
                background_music=music_path,
                config=edit_config.model_dump(),
                subtitle_settings=edit_config.subtitle_settings.model_dump(),
                progress_cb=cb,
                stop_event=stop_event,
            )
            _jobs[job_id]["output_files"] = [Path(f).name for f in output_files]
            await _send_ws(job_id, "COMPLETE", "🎉 All videos processed successfully!", 100.0)
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[CRITICAL ERROR] Background processing failed:\n{tb}")
            await _send_ws(job_id, "ERROR", f"❌ Processing failed: {e}\n{tb}", None)

    asyncio.create_task(_run())

    return JobStatusResponse(
        job_id=job_id,
        status=JobStatus.running,
        progress=0.0,
        logs=[],
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll job status (alternative to WebSocket)."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        logs=job["logs"][-50:],  # last 50 log entries
        output_files=job.get("output_files", []),
    )


@router.post("/stop/{job_id}")
async def stop_job(job_id: str):
    """Request stop for a running job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if "stop_event" in job:
        job["stop_event"].set()
        
    job["stop_requested"] = True
    return {"message": "Stop requested"}


@router.get("/download/{job_id}/{filename}")
async def download_output(job_id: str, filename: str):
    """Download a processed output video."""
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/jobs")
async def list_jobs():
    """List all jobs with their statuses."""
    return [
        {
            "job_id": jid,
            "status": job["status"],
            "progress": job["progress"],
            "output_count": len(job.get("output_files", [])),
        }
        for jid, job in _jobs.items()
    ]
