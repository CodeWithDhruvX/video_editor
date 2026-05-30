import os
import logging
from faster_whisper import WhisperModel
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WhisperService:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        """
        Initialize Whisper service for speech recognition
        
        Args:
            model_size: Model size (tiny, base, small, medium, large)
            device: Device to run model on (cpu, cuda, auto)
            compute_type: Compute type (int8, float16, float32)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model"""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(self, audio_path, language="en", task="transcribe", word_timestamps=True):
        """
        Transcribe audio file using Whisper
        
        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en')
            task: Task type (transcribe or translate)
            word_timestamps: Whether to include word timestamps
            
        Returns:
            Tuple of (segments, info) where segments contains transcription results
        """
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            logger.info(f"Transcribing audio: {audio_path}")
            
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                word_timestamps=word_timestamps
            )
            
            # Convert to list for multiple iterations
            segments_list = list(segments)
            
            logger.info(f"Transcription completed. Detected language: {info.language} with probability {info.language_probability:.2f}")
            
            return segments_list, info
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_with_timestamps(self, audio_path, language="en"):
        """
        Transcribe audio with detailed timestamps
        
        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en')
            
        Returns:
            Dictionary with transcription results including timestamps
        """
        try:
            segments, info = self.transcribe(audio_path, language, word_timestamps=True)
            
            result = {
                'language': info.language,
                'language_probability': info.language_probability,
                'duration': info.duration,
                'segments': []
            }
            
            for segment in segments:
                segment_data = {
                    'id': segment.id,
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text,
                    'words': []
                }
                
                if hasattr(segment, 'words'):
                    for word in segment.words:
                        word_data = {
                            'start': word.start,
                            'end': word.end,
                            'word': word.word,
                            'probability': word.probability
                        }
                        segment_data['words'].append(word_data)
                
                result['segments'].append(segment_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription with timestamps failed: {e}")
            raise
    
    def generate_srt(self, audio_path, output_path, language="en"):
        """
        Generate SRT subtitle file from audio
        
        Args:
            audio_path: Path to audio file
            output_path: Path to output SRT file
            language: Language code (default: 'en')
        """
        try:
            segments, _ = self.transcribe(audio_path, language, word_timestamps=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    # SRT format: index, time range, text
                    start_time = self._format_srt_time(segment.start)
                    end_time = self._format_srt_time(segment.end)
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment.text.strip()}\n\n")
            
            logger.info(f"SRT file generated: {output_path}")
            
        except Exception as e:
            logger.error(f"SRT generation failed: {e}")
            raise
    
    def generate_vtt(self, audio_path, output_path, language="en"):
        """
        Generate WebVTT subtitle file from audio
        
        Args:
            audio_path: Path to audio file
            output_path: Path to output VTT file
            language: Language code (default: 'en')
        """
        try:
            segments, _ = self.transcribe(audio_path, language, word_timestamps=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for segment in segments:
                    # WebVTT format: time range, text
                    start_time = self._format_vtt_time(segment.start)
                    end_time = self._format_vtt_time(segment.end)
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment.text.strip()}\n\n")
            
            logger.info(f"VTT file generated: {output_path}")
            
        except Exception as e:
            logger.error(f"VTT generation failed: {e}")
            raise
    
    def detect_language(self, audio_path):
        """
        Detect language of audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (language_code, probability)
        """
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            logger.info(f"Detecting language for: {audio_path}")
            
            # Run transcription without specifying language to auto-detect
            segments, info = self.model.transcribe(
                audio_path,
                task="transcribe",
                word_timestamps=False
            )
            
            # Consume segments to complete detection
            list(segments)
            
            logger.info(f"Detected language: {info.language} with probability {info.language_probability:.2f}")
            
            return info.language, info.language_probability
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise
    
    def _format_srt_time(self, seconds):
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _format_vtt_time(self, seconds):
        """Format seconds to WebVTT time format (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    def get_supported_languages(self):
        """
        Get list of supported languages
        
        Returns:
            Dictionary of language codes to language names
        """
        # Common language codes supported by Whisper
        return {
            'af': 'Afrikaans',
            'am': 'Amharic',
            'ar': 'Arabic',
            'as': 'Assamese',
            'az': 'Azerbaijani',
            'ba': 'Bashkir',
            'be': 'Belarusian',
            'bg': 'Bulgarian',
            'bn': 'Bengali',
            'bo': 'Tibetan',
            'br': 'Breton',
            'bs': 'Bosnian',
            'ca': 'Catalan',
            'cs': 'Czech',
            'cy': 'Welsh',
            'da': 'Danish',
            'de': 'German',
            'el': 'Greek',
            'en': 'English',
            'es': 'Spanish',
            'et': 'Estonian',
            'eu': 'Basque',
            'fa': 'Persian',
            'fi': 'Finnish',
            'fo': 'Faroese',
            'fr': 'French',
            'gl': 'Galician',
            'gu': 'Gujarati',
            'ha': 'Hausa',
            'haw': 'Hawaiian',
            'he': 'Hebrew',
            'hi': 'Hindi',
            'hr': 'Croatian',
            'ht': 'Haitian',
            'hu': 'Hungarian',
            'hy': 'Armenian',
            'id': 'Indonesian',
            'is': 'Icelandic',
            'it': 'Italian',
            'ja': 'Japanese',
            'jw': 'Javanese',
            'ka': 'Georgian',
            'kk': 'Kazakh',
            'km': 'Khmer',
            'kn': 'Kannada',
            'ko': 'Korean',
            'la': 'Latin',
            'lb': 'Luxembourgish',
            'lo': 'Lao',
            'lt': 'Lithuanian',
            'lv': 'Latvian',
            'mg': 'Malagasy',
            'mi': 'Maori',
            'mk': 'Macedonian',
            'ml': 'Malayalam',
            'mn': 'Mongolian',
            'mr': 'Marathi',
            'ms': 'Malay',
            'mt': 'Maltese',
            'my': 'Burmese',
            'ne': 'Nepali',
            'nl': 'Dutch',
            'nn': 'Norwegian Nynorsk',
            'no': 'Norwegian',
            'oc': 'Occitan',
            'pa': 'Punjabi',
            'pl': 'Polish',
            'ps': 'Pashto',
            'pt': 'Portuguese',
            'ro': 'Romanian',
            'ru': 'Russian',
            'sa': 'Sanskrit',
            'sd': 'Sindhi',
            'si': 'Sinhala',
            'sk': 'Slovak',
            'sl': 'Slovenian',
            'sn': 'Shona',
            'so': 'Somali',
            'sq': 'Albanian',
            'sr': 'Serbian',
            'su': 'Sundanese',
            'sv': 'Swedish',
            'sw': 'Swahili',
            'ta': 'Tamil',
            'te': 'Telugu',
            'tg': 'Tajik',
            'th': 'Thai',
            'tk': 'Turkmen',
            'tl': 'Tagalog',
            'tr': 'Turkish',
            'tt': 'Tatar',
            'uk': 'Ukrainian',
            'ur': 'Urdu',
            'uz': 'Uzbek',
            'vi': 'Vietnamese',
            'yi': 'Yiddish',
            'yo': 'Yoruba',
            'zh': 'Chinese'
        }