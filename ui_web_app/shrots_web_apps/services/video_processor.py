import os
import subprocess
import json
import tempfile
from pathlib import Path
import logging
import shutil
from faster_whisper import WhisperModel
import ffmpeg

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, output_dir='outputs'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.whisper_model = None
        
    def _load_whisper_model(self):
        """Load Whisper model for speech recognition"""
        if self.whisper_model is None:
            try:
                self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise
    
    def process_video(self, video_path, options=None, task_id=None):
        """
        Process video with various effects and options
        
        Args:
            video_path: Path to input video
            options: Dictionary of processing options
            task_id: Optional task ID for logging
            
        Returns:
            Dictionary with processing results
        """
        try:
            options = options or {}
            logger.info(f"Processing video: {video_path}")
            
            # Create temporary working directory
            temp_dir = tempfile.mkdtemp()
            
            # Build processing chain based on options
            processed_video = video_path
            
            # Add background music if enabled
            if options.get('enable_music') and options.get('background_music'):
                processed_video = self._add_background_music(
                    processed_video, 
                    options['background_music'],
                    options.get('music_volume', 30),
                    temp_dir
                )
            
            # Add text effects if enabled
            if options.get('enable_text_effects') and options.get('text_content'):
                processed_video = self._add_text_effects(
                    processed_video,
                    options['text_content'],
                    options.get('text_font', 'Arial'),
                    options.get('font_size', 24),
                    options.get('text_color', '#ffffff'),
                    temp_dir
                )
            
            # Generate subtitles if enabled
            if options.get('enable_subtitles'):
                subtitle_path = self.generate_subtitles(
                    processed_video,
                    options.get('subtitle_language', 'en'),
                    os.path.join(temp_dir, 'subtitles.srt'),
                    task_id
                )
                processed_video = self._burn_subtitles(processed_video, subtitle_path, temp_dir)
            
            # Prepare output path
            output_filename = options.get('output_filename', 'output')
            output_format = options.get('output_format', 'mp4')
            output_path = self.output_dir / f"{output_filename}.{output_format}"
            
            # Copy final result to output location
            shutil.copy(processed_video, output_path)
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
            logger.info(f"Video processing completed: {output_path}")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'message': 'Video processed successfully'
            }
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Video processing failed'
            }
    
    def merge_videos(self, video_paths, extra_video=None, background_music=None, 
                    output_path=None, task_id=None):
        """
        Merge multiple videos together
        
        Args:
            video_paths: List of video file paths
            extra_video: Optional extra video to merge
            background_music: Optional background music
            output_path: Output file path
            task_id: Optional task ID for logging
            
        Returns:
            Dictionary with merge results
        """
        try:
            logger.info(f"Merging {len(video_paths)} videos")
            
            if output_path is None:
                output_path = self.output_dir / "merged_video.mp4"
            
            # Create temporary working directory
            temp_dir = tempfile.mkdtemp()
            
            # Create concat file for ffmpeg
            concat_file = os.path.join(temp_dir, 'concat.txt')
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            # Merge videos using ffmpeg
            merged_video = os.path.join(temp_dir, 'merged.mp4')
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                merged_video
            ]
            
            logger.info(f"Running ffmpeg merge command")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Add extra video if provided
            if extra_video:
                merged_video = self._merge_extra_video(merged_video, extra_video, temp_dir)
            
            # Add background music if provided
            if background_music:
                merged_video = self._add_background_music(
                    merged_video,
                    background_music,
                    30,  # default volume
                    temp_dir
                )
            
            # Copy final result to output location
            shutil.copy(merged_video, output_path)
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
            logger.info(f"Video merge completed: {output_path}")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'message': 'Videos merged successfully'
            }
            
        except Exception as e:
            logger.error(f"Video merge failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Video merge failed'
            }
    
    def generate_subtitles(self, video_path, language='en', output_path=None, task_id=None):
        """
        Generate subtitles using Whisper speech recognition
        
        Args:
            video_path: Path to video file
            language: Language code (default: 'en')
            output_path: Output SRT file path
            task_id: Optional task ID for logging
            
        Returns:
            Path to generated subtitle file
        """
        try:
            logger.info(f"Generating subtitles for: {video_path}")
            
            if output_path is None:
                output_path = str(self.output_dir / f"{Path(video_path).stem}_subtitles.srt")
            
            # Load Whisper model
            self._load_whisper_model()
            
            # Extract audio from video
            audio_path = self._extract_audio(video_path)
            
            # Transcribe audio
            segments, info = self.whisper_model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                word_timestamps=True
            )
            
            # Generate SRT format
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    # SRT format: index, time range, text
                    start_time = self._format_srt_time(segment.start)
                    end_time = self._format_srt_time(segment.end)
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment.text.strip()}\n\n")
            
            # Clean up audio file
            os.remove(audio_path)
            
            logger.info(f"Subtitles generated: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            raise
    
    def _extract_audio(self, video_path):
        """Extract audio from video file"""
        output_path = tempfile.mktemp(suffix='.wav')
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return output_path
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise
    
    def _format_srt_time(self, seconds):
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _add_background_music(self, video_path, music_path, volume=30, temp_dir=None):
        """Add background music to video"""
        try:
            output_path = os.path.join(temp_dir or tempfile.mkdtemp(), 'with_music.mp4')
            
            # Normalize volume (0-1)
            volume_norm = volume / 100.0
            
            (
                ffmpeg
                .input(video_path)
                .input(music_path)
                .output(
                    output_path,
                    vcodec='copy',
                    acodec='aac',
                    audio_bitrate='192k',
                    filter_complex=f"[1:a]volume={volume_norm}[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
                    map=['0:v', '[out]']
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return output_path
        except Exception as e:
            logger.error(f"Background music addition failed: {e}")
            raise
    
    def _add_text_effects(self, video_path, text, font='Arial', font_size=24, 
                         color='#ffffff', temp_dir=None):
        """Add text overlay to video"""
        try:
            output_path = os.path.join(temp_dir or tempfile.mkdtemp(), 'with_text.mp4')
            
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    vf=f"drawtext=text='{text}':fontfile=/Windows/Fonts/arial.ttf:fontsize={font_size}:fontcolor={color}:x=(w-text_w)/2:y=(h-text_h)/2",
                    vcodec='libx264',
                    acodec='copy'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return output_path
        except Exception as e:
            logger.error(f"Text effects addition failed: {e}")
            raise
    
    def _burn_subtitles(self, video_path, subtitle_path, temp_dir=None):
        """Burn subtitles into video"""
        try:
            output_path = os.path.join(temp_dir or tempfile.mkdtemp(), 'with_subtitles.mp4')
            
            # Fix path for ffmpeg (replace backslashes with forward slashes)
            subtitle_path_fixed = subtitle_path.replace('\\', '/')
            
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    vf=f"subtitles='{subtitle_path_fixed}'",
                    vcodec='libx264',
                    acodec='copy'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return output_path
        except Exception as e:
            logger.error(f"Subtitle burning failed: {e}")
            raise
    
    def _merge_extra_video(self, main_video, extra_video, temp_dir):
        """Merge extra video with main video"""
        try:
            output_path = os.path.join(temp_dir, 'merged_with_extra.mp4')
            
            (
                ffmpeg
                .input(main_video)
                .input(extra_video)
                .output(
                    output_path,
                    filter_complex="[0:v][1:v]concat=n=2:v=1[outv];[0:a][1:a]concat=n=2:a=1[outa]",
                    map=['[outv]', '[outa]'],
                    vcodec='libx264',
                    acodec='aac'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return output_path
        except Exception as e:
            logger.error(f"Extra video merge failed: {e}")
            raise
    
    def get_video_info(self, video_path):
        """Get video information using ffprobe"""
        try:
            probe = ffmpeg.probe(video_path)
            video_info = probe['streams'][0] if probe['streams'] else {}
            
            return {
                'duration': float(probe['format'].get('duration', 0)),
                'width': int(video_info.get('width', 0)),
                'height': int(video_info.get('height', 0)),
                'codec': video_info.get('codec_name', 'unknown'),
                'bitrate': int(probe['format'].get('bit_rate', 0)),
                'size': int(probe['format'].get('size', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None