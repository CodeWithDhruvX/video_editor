from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# ─────────────────────────── Enums ───────────────────────────

class PrivacyStatus(str, Enum):
    public = "public"
    unlisted = "unlisted"
    private = "private"


class SubtitleMode(str, Enum):
    single = "single"
    multiple = "multiple"
    mixed = "mixed"


class SubtitlePosition(str, Enum):
    bottom = "bottom"
    top = "top"
    center = "center"


class QualityPreset(str, Enum):
    ultrafast = "ultrafast"
    fast = "fast"
    medium = "medium"
    slow = "slow"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
    stopped = "stopped"


# ─────────────────────────── Video Editor Schemas ───────────────────────────

class MixedFontSettings(BaseModel):
    enable_random_fonts: bool = True
    enable_random_colors: bool = True
    enable_random_sizes: bool = True
    enable_effects: bool = True


class SubtitleSettings(BaseModel):
    color: str = "#FFFFFF"
    font_family: str = "Arial"
    mode: SubtitleMode = SubtitleMode.mixed
    size: int = Field(default=24, ge=12, le=48)
    words_count: int = Field(default=3, ge=2, le=10)
    enable_borders: bool = True
    border_color: str = "#000000"
    border_thickness: int = Field(default=3, ge=1, le=8)
    position: SubtitlePosition = SubtitlePosition.bottom
    mixed_font_settings: MixedFontSettings = Field(default_factory=MixedFontSettings)
    language: str = Field(default="en", description="Language code for transcription (e.g., 'en', 'es', 'fr', 'hi')")


class VideoEditConfig(BaseModel):
    quality_preset: QualityPreset = QualityPreset.fast
    music_volume: float = Field(default=0.30, ge=0.0, le=0.5)
    enable_gpu: bool = True
    enable_auto_edit: bool = False
    enable_ducking: bool = True
    enable_merge: bool = False
    subtitle_settings: SubtitleSettings = Field(default_factory=SubtitleSettings)
    edited_transcripts: Optional[Dict[str, List[Dict[str, Any]]]] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    logs: List[str] = []
    output_files: List[str] = []
    error: Optional[str] = None


# ─────────────────────────── YouTube Uploader Schemas ───────────────────────────

CATEGORY_MAP: Dict[str, str] = {
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
    "Nonprofits & Activism": "29",
}


class VideoUploadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    tags: List[str] = []
    category_name: str = "Entertainment"
    privacy_status: PrivacyStatus = PrivacyStatus.public
    made_for_kids: bool = False
    playlist_names: List[str] = []
    publish_at: Optional[str] = None  # "YYYY-MM-DD HH:MM:SS" in IST
    video_file_path: Optional[str] = None   # server-side path after upload
    thumbnail_path: Optional[str] = None


class BatchUploadMetadata(BaseModel):
    videos: List[VideoUploadRequest]


class UploadJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class ChannelInfo(BaseModel):
    channel_id: str
    channel_name: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    channels: List[ChannelInfo] = []
    message: str


class PlaylistInfo(BaseModel):
    id: str
    title: str
    description: str
    video_count: int = 0


class WebSocketMessage(BaseModel):
    type: str   # "LOG" | "PROGRESS" | "STATUS" | "COMPLETE" | "ERROR" | "STOPPED"
    message: str
    progress: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
