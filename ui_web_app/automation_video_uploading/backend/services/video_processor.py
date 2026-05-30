"""
Video Processor Service
Ported from short_gui_v8.py — adapted for FastAPI with async progress callbacks.
Handles: Whisper transcription, subtitle generation (.ass), FFmpeg processing,
audio ducking, video merging, background music.
"""

import os
import subprocess
import json
import logging
import asyncio
import tempfile
import random
import shutil
import traceback
from pathlib import Path
from typing import Optional, List, Callable, Awaitable, Dict, Any

logger = logging.getLogger(__name__)

# Type alias
ProgressCallback = Callable[[str, str, Optional[float]], Awaitable[None]]

# ─────────────────────────── Constants ───────────────────────────

FONT_FAMILIES = [
    "Impact", "Arial Black", "Tahoma", "Verdana", "Comic Sans MS",
    "Trebuchet MS", "Georgia", "Palatino Linotype",
]

AVAILABLE_COLORS = [
    "&H00FFFFFF", "&H0000FFFF", "&H0000FF00", "&H000000FF",
    "&H00FF00FF", "&H0000A5FF", "&H00FF69B4", "&H0033FF57",
]


# ─────────────────────────── Helpers ───────────────────────────

def hex_to_ass_color(hex_color: str) -> str:
    """Convert #RRGGBB hex to ASS &H00BBGGRR format."""
    hex_color = hex_color.lstrip("#")
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H00{b}{g}{r}"


def run_ffmpeg(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run an ffmpeg command and capture output."""
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def get_video_duration(video_path: str) -> float:
    """Return video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return float(stream.get("duration", 0))
    except Exception:
        pass
    return 0.0


# ─────────────────────────── Whisper Transcription ───────────────────────────

async def transcribe_video(
    video_path: str,
    progress_cb: ProgressCallback,
) -> List[Dict[str, Any]]:
    """
    Transcribe video audio using faster-whisper.
    Returns list of word-level segments: [{word, start, end}, ...]
    """
    await progress_cb("LOG", "🎙️ Loading Whisper model...", None)

    loop = asyncio.get_event_loop()

    def _transcribe():
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(video_path, word_timestamps=True, language="en")
            words = []
            for segment in segments:
                if hasattr(segment, "words") and segment.words:
                    for word in segment.words:
                        words.append({
                            "word": word.word.strip(),
                            "start": word.start,
                            "end": word.end,
                        })
                else:
                    # Fallback: treat whole segment as one word
                    words.append({
                        "word": segment.text.strip(),
                        "start": segment.start,
                        "end": segment.end,
                    })
            return words
        except ImportError:
            return []  # faster_whisper not installed

    words = await loop.run_in_executor(None, _transcribe)
    await progress_cb("LOG", f"✅ Transcribed {len(words)} words", None)
    return words


# ─────────────────────────── ASS Subtitle Generation ───────────────────────────

def build_ass_header(subtitle_color: str, subtitle_size: int, border_color: str, border_thickness: int) -> str:
    ass_color = hex_to_ass_color(subtitle_color)
    border_ass_color = hex_to_ass_color(border_color)
    return f"""[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{subtitle_size},{ass_color},&H00FFFFFF,{border_ass_color},&H00000000,-1,0,0,0,100,100,0,0,1,{border_thickness},0,2,30,30,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:06.3f}".replace(".", "\\.")


def format_time_ass(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s % 1) * 100)
    s = int(s)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_subtitles(
    words: List[Dict],
    subtitle_settings: Dict,
    output_path: str,
) -> None:
    """Generate an .ass subtitle file from word timestamps."""
    mode = subtitle_settings.get("mode", "mixed")
    subtitle_color = subtitle_settings.get("color", "#FFFFFF")
    subtitle_size = subtitle_settings.get("size", 24)
    border_color = subtitle_settings.get("border_color", "#000000")
    border_thickness = subtitle_settings.get("border_thickness", 3)
    words_count = subtitle_settings.get("words_count", 3)
    mixed_settings = subtitle_settings.get("mixed_font_settings", {})

    header = build_ass_header(subtitle_color, subtitle_size, border_color, border_thickness)
    events = []

    if mode == "single":
        for w in words:
            start = format_time_ass(w["start"])
            end = format_time_ass(w["end"])
            color = hex_to_ass_color(subtitle_color)
            text = f"{{\\c{color}}}{w['word']}"
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    elif mode == "multiple":
        groups = [words[i:i + words_count] for i in range(0, len(words), words_count)]
        for group in groups:
            if not group:
                continue
            start = format_time_ass(group[0]["start"])
            end = format_time_ass(group[-1]["end"])
            text = " ".join(w["word"] for w in group)
            color = hex_to_ass_color(subtitle_color)
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\c{color}}}{text}")

    elif mode == "mixed":
        groups = [words[i:i + words_count] for i in range(0, len(words), words_count)]
        for group in groups:
            if not group:
                continue
            start = format_time_ass(group[0]["start"])
            end = format_time_ass(group[-1]["end"])
            parts = []
            for w in group:
                tags = []
                if mixed_settings.get("enable_random_fonts", True):
                    font = random.choice(FONT_FAMILIES)
                    tags.append(f"\\fn{font}")
                if mixed_settings.get("enable_random_colors", True):
                    color = random.choice(AVAILABLE_COLORS)
                    tags.append(f"\\c{color}")
                if mixed_settings.get("enable_random_sizes", True):
                    size = random.randint(subtitle_size - 4, subtitle_size + 8)
                    tags.append(f"\\fs{size}")
                if mixed_settings.get("enable_effects", True):
                    if random.random() > 0.5:
                        tags.append("\\b1")
                    if random.random() > 0.7:
                        tags.append("\\i1")
                tag_str = "{" + "".join(tags) + "}" if tags else ""
                parts.append(f"{tag_str}{w['word']}")
            text = " ".join(parts)
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))


# ─────────────────────────── FFmpeg Processing ───────────────────────────

async def process_video(
    input_path: str,
    output_path: str,
    extra_video: Optional[str],
    background_music: Optional[str],
    ass_path: Optional[str],
    config: Dict[str, Any],
    progress_cb: ProgressCallback,
    _gpu_fallback: bool = False,
) -> bool:
    """
    Apply FFmpeg processing pipeline to a single video:
    - Optional merge with extra video
    - Add background music with optional ducking
    - Burn in .ass subtitles
    - Quality/GPU settings
    Returns True on success.
    """
    success = False
    quality = config.get("quality_preset", "fast")
    music_volume = config.get("music_volume", 0.3)
    enable_gpu = config.get("enable_gpu", True)
    enable_ducking = config.get("enable_ducking", True)

    name = Path(input_path).name
    await progress_cb("STATUS", f"🎬 Starting pipeline for: {name}", None)
    await progress_cb("LOG", f"  ├─ Quality preset : {quality}", None)
    await progress_cb("LOG", f"  ├─ GPU encoding   : {'Yes (h264_nvenc)' if enable_gpu else 'No  (libx264)'}", None)
    await progress_cb("LOG", f"  ├─ Music volume   : {music_volume}", None)
    await progress_cb("LOG", f"  └─ Smart ducking  : {'enabled' if enable_ducking else 'disabled'}", None)

    loop = asyncio.get_event_loop()

    # ── Async FFmpeg runner that streams stderr ──────────────────────────────
    async def _run_streaming(cmd: List[str], label: str, timeout: int = 300) -> tuple[bool, str]:
        """Run an ffmpeg command and stream stderr to the WebSocket."""
        await progress_cb("LOG", f"▶ Running: {label}", None)
        
        loop = asyncio.get_running_loop()
        stderr_lines = []

        def _sync_run():
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            
            try:
                for line in iter(proc.stderr.readline, ''):
                    if not line:
                        break
                    line = line.rstrip()
                    if line:
                        stderr_lines.append(line)
                        if any(kw in line for kw in ("frame=", "fps=", "size=", "time=", "speed=", "Error", "error", "Warning", "Invalid", "Cannot", "No such")):
                            asyncio.run_coroutine_threadsafe(progress_cb("FFMPEG", line, None), loop)
                
                proc.wait(timeout=timeout)
                return proc.returncode == 0
            except Exception as e:
                proc.kill()
                raise e

        try:
            success = await asyncio.to_thread(_sync_run)
            return success, "\n".join(stderr_lines)
        except Exception as e:
            return False, f"FFmpeg process error: {str(e)}"

    # ── Synchronous helper (used for concat which is fast) ───────────────────
    def _sync_ffmpeg(cmd: List[str]) -> tuple[bool, str]:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
        return result.returncode == 0, result.stderr

    # ── Build temp dir (we keep it for the duration of the async pipeline) ───
    tmp_dir = tempfile.mkdtemp()
    try:
        current_input = input_path

        # Step 1: Merge videos if needed
        if extra_video and os.path.exists(extra_video):
            await progress_cb("STATUS", "🔗 Step 1/3 — Merging videos…", None)
            concat_list = os.path.join(tmp_dir, "concat.txt")
            merged = os.path.join(tmp_dir, "merged.mp4")
            with open(concat_list, "w") as f:
                abs_current = os.path.abspath(current_input).replace('\\', '/')
                abs_extra = os.path.abspath(extra_video).replace('\\', '/')
                f.write(f"file '{abs_current}'\nfile '{abs_extra}'\n")
            ok, err = _sync_ffmpeg([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", merged,
            ])
            if ok:
                await progress_cb("LOG", "  ✅ Merge complete", None)
                current_input = merged
            else:
                await progress_cb("LOG", f"  ⚠️ Merge warning (continuing anyway)", None)
                for l in err.splitlines()[-5:]:
                    if l.strip():
                        await progress_cb("FFMPEG", l, None)
        else:
            await progress_cb("STATUS", "⚙️ Step 1/3 — No merge needed", None)

        # Step 2: Build FFmpeg filter graph
        await progress_cb("STATUS", "⚙️ Step 2/3 — Building filter graph…", None)
        inputs = ["-i", current_input]
        filter_parts = []
        audio_label = "[0:a]"
        video_label = "[0:v]"

        if background_music and os.path.exists(background_music):
            await progress_cb("LOG", "  ├─ Background music : enabled", None)
            inputs += ["-i", background_music]
            music_idx = 1
            if enable_ducking:
                filter_parts.append(
                    f"[0:a]asplit=2[speech][sidechain];"
                    f"[{music_idx}:a]volume={music_volume}[music_vol];"
                    f"[music_vol][sidechain]sidechaincompress=threshold=0.003:ratio=20:attack=5:release=50[ducked_music];"
                    f"[speech][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                )
                await progress_cb("LOG", "  ├─ Audio ducking    : sidechaincompress-style", None)
            else:
                filter_parts.append(
                    f"[{music_idx}:a]volume={music_volume}[music_vol];"
                    f"[0:a][music_vol]amix=inputs=2:duration=first[aout]"
                )
            audio_label = "[aout]"
        else:
            await progress_cb("LOG", "  ├─ Background music : none", None)

        if ass_path and os.path.exists(ass_path):
            safe_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
            filter_parts.append(f"{video_label}ass='{safe_path}'[vout]")
            video_label = "[vout]"
            await progress_cb("LOG", "  └─ Subtitles        : burning in .ass overlay", None)
        else:
            await progress_cb("LOG", "  └─ Subtitles        : none (no words transcribed)", None)

        if enable_gpu:
            vcodec = ["-c:v", "h264_nvenc", "-preset", "fast"]
        else:
            vcodec = ["-c:v", "libx264", "-preset", quality, "-crf", "23"]

        cmd = ["ffmpeg", "-y"] + inputs
        if filter_parts:
            cmd += ["-filter_complex", ";".join(filter_parts)]
            cmd += ["-map", video_label if video_label != "[0:v]" else "0:v"]
            cmd += ["-map", audio_label if audio_label != "[0:a]" else "0:a"]
        else:
            cmd += ["-map", "0:v", "-map", "0:a"]
        cmd += vcodec + ["-c:a", "aac", "-b:a", "192k", output_path]

        # Step 3: Encode
        encoder_name = "h264_nvenc (GPU)" if enable_gpu else f"libx264 (CPU, {quality})"
        await progress_cb("STATUS", f"🎞️ Step 3/3 — Encoding with {encoder_name}…", None)
        await progress_cb("LOG", f"  FFmpeg cmd: {' '.join(cmd[:6])} … [{len(cmd)} args total]", None)

        success, stderr = await _run_streaming(cmd, f"encode → {Path(output_path).name}")

    finally:
        # Clean up temp dir
        try:
            import shutil as _sh
            _sh.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    if success:
        await progress_cb("LOG", f"✅ Processed: {Path(output_path).name}", None)
    else:
        if _gpu_fallback:
            await progress_cb("LOG", f"❌ CPU encode also failed: {Path(input_path).name}", None)
        else:
            await progress_cb("WARN", f"⚠️ GPU encode failed, retrying with CPU…", None)
            config_cpu = dict(config)
            config_cpu["enable_gpu"] = False
            return await process_video(
                input_path, output_path, extra_video,
                background_music, ass_path, config_cpu, progress_cb,
                _gpu_fallback=True,
            )

    return success



# ─────────────────────────── Main Processor ───────────────────────────

async def process_all_videos(
    input_videos: List[str],
    extra_video: Optional[str],
    output_dir: str,
    background_music: Optional[str],
    config: Dict[str, Any],
    subtitle_settings: Dict[str, Any],
    progress_cb: ProgressCallback,
    stop_event: asyncio.Event,
) -> List[str]:
    """
    Process all input videos and return list of output file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_files = []
    total = len(input_videos)

    await progress_cb("STATUS", f"📋 Job started — {total} video(s) to process", 0.0)

    for i, video_path in enumerate(input_videos):
        if stop_event.is_set():
            await progress_cb("STOPPED", "🛑 Processing stopped by user", None)
            break

        pct = round((i / total) * 100, 1)
        name = Path(video_path).name
        size_mb = os.path.getsize(video_path) / (1024 * 1024) if os.path.exists(video_path) else 0
        duration = get_video_duration(video_path)

        await progress_cb("STATUS", f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", pct)
        await progress_cb("STATUS", f"📹 Video {i + 1}/{total}: {name}", pct)
        await progress_cb("LOG",    f"  ├─ File size : {size_mb:.1f} MB", None)
        await progress_cb("LOG",    f"  └─ Duration  : {duration:.1f}s", None)

        base_name = Path(video_path).stem
        output_path = os.path.join(output_dir, f"{base_name}_processed.mp4")

        # Transcribe
        words = []
        ass_path = None
        if subtitle_settings.get("mode") in ("single", "multiple", "mixed"):
            await progress_cb("STATUS", f"🎙️ Transcribing audio with Whisper…", None)
            words = await transcribe_video(video_path, progress_cb)
        else:
            await progress_cb("LOG", "  ⏭ Skipping transcription (subtitle mode: none)", None)

        # Generate subtitles
        if words:
            await progress_cb("STATUS", f"📝 Generating {subtitle_settings.get('mode','mixed')} subtitles…", None)
            with tempfile.NamedTemporaryFile(suffix=".ass", delete=False, mode="w") as tmp_ass:
                ass_path = tmp_ass.name
            generate_ass_subtitles(words, subtitle_settings, ass_path)
            await progress_cb("LOG", f"  ✅ Subtitles: {len(words)} words → {subtitle_settings.get('mode','mixed')} mode", None)
        else:
            await progress_cb("LOG", "  ℹ️ No words found — subtitles skipped", None)

        # Process video
        success = await process_video(
            video_path, output_path, extra_video,
            background_music, ass_path, config, progress_cb
        )

        # Cleanup temp ass file
        if ass_path and os.path.exists(ass_path):
            os.remove(ass_path)

        if success and os.path.exists(output_path):
            output_files.append(output_path)
            out_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            await progress_cb("LOG", f"💾 Output saved: {Path(output_path).name} ({out_size_mb:.1f} MB)", None)
        else:
            await progress_cb("ERROR", f"❌ Failed to process: {name}", None)

        overall = round(((i + 1) / total) * 100, 1)
        await progress_cb("PROGRESS", f"{overall}", overall)

    await progress_cb("STATUS", f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 100.0)
    return output_files

