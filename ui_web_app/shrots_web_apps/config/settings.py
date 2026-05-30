import os
from pathlib import Path

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    TESTING = os.environ.get('TESTING', 'False') == 'True'
    
    # Application paths
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
    OUTPUT_FOLDER = str(BASE_DIR / 'outputs')
    CONFIG_FOLDER = str(BASE_DIR / 'config')
    LOGS_FOLDER = str(BASE_DIR / 'logs')
    
    # File settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'wav', 'mp3', 'jpg', 'png', 'jpeg'}
    
    # Video processing settings
    DEFAULT_OUTPUT_FORMAT = 'mp4'
    DEFAULT_OUTPUT_QUALITY = 'high'
    ENABLE_SUBTITLE_GENERATION = False
    DEFAULT_SUBTITLE_LANGUAGE = 'en'
    WHISPER_MODEL_SIZE = 'base'
    WHISPER_DEVICE = 'cpu'
    WHISPER_COMPUTE_TYPE = 'int8'
    
    # YouTube settings
    DEFAULT_PRIVACY_STATUS = 'private'
    DEFAULT_CATEGORY = '22'
    MADE_FOR_KIDS_DEFAULT = False
    YOUTUBE_TOKEN_FILE = 'token.json'
    
    # Background processing
    MAX_CONCURRENT_TASKS = 2
    TASK_TIMEOUT = 3600  # 1 hour
    CLEANUP_INTERVAL = 3600  # 1 hour
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT = 5
    LOG_RETENTION_DAYS = 30
    
    # UI settings
    THEME = 'light'
    LANGUAGE = 'en'
    SHOW_ADVANCED_OPTIONS = False
    COMPACT_MODE = False
    
    @classmethod
    def init_directories(cls):
        """Initialize required directories"""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.OUTPUT_FOLDER,
            cls.CONFIG_FOLDER,
            cls.LOGS_FOLDER
        ]
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @classmethod
    def validate(cls):
        """Validate production configuration"""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in production")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    UPLOAD_FOLDER = str(Path(__file__).parent.parent / 'test_uploads')
    OUTPUT_FOLDER = str(Path(__file__).parent.parent / 'test_outputs')


def get_config(config_name=None):
    """
    Get configuration based on environment
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return config_map.get(config_name, DevelopmentConfig)


# Initialize directories
Config.init_directories()