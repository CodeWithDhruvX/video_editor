import json
import os
from pathlib import Path
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_dir='config'):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory to store configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.default_config_file = self.config_dir / 'default_config.json'
        self.user_config_file = self.config_dir / 'user_config.json'
        
        # Initialize default configuration
        self._init_default_config()
    
    def _init_default_config(self):
        """Initialize default configuration file"""
        default_config = {
            "video_processing": {
                "default_output_format": "mp4",
                "default_output_quality": "high",
                "enable_subtitle_generation": False,
                "default_subtitle_language": "en",
                "default_subtitle_style": "simple"
            },
            "youtube_upload": {
                "default_privacy_status": "private",
                "default_category": "22",
                "made_for_kids_default": False,
                "enable_auto_playlist": False,
                "default_playlist_name": "My Videos"
            },
            "app_settings": {
                "max_file_size_mb": 500,
                "max_concurrent_uploads": 2,
                "enable_auto_save": True,
                "enable_logging": True,
                "log_level": "INFO"
            },
            "ui_settings": {
                "theme": "light",
                "language": "en",
                "show_advanced_options": False,
                "compact_mode": False
            }
        }
        
        if not self.default_config_file.exists():
            with open(self.default_config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info("Default configuration file created")
    
    def load_config(self, config_file=None) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Args:
            config_file: Optional path to configuration file
            
        Returns:
            Dictionary with configuration data
        """
        try:
            config_path = Path(config_file) if config_file else self.user_config_file
            
            if not config_path.exists():
                logger.info(f"Configuration file not found: {config_path}, using defaults")
                return self.load_default_config()
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Configuration loaded from: {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return self.load_default_config()
    
    def load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        try:
            with open(self.default_config_file, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load default configuration: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any], config_file=None) -> bool:
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save
            config_file: Optional path to configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config_path = Path(config_file) if config_file else self.user_config_file
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Configuration saved to: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def merge_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user configuration with default configuration
        
        Args:
            user_config: User configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        default_config = self.load_default_config()
        return self._deep_merge(default_config, user_config)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_setting(self, key_path: str, default=None):
        """
        Get a specific setting using dot notation
        
        Args:
            key_path: Dot-separated path to setting (e.g., 'video_processing.default_output_format')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        config = self.load_config()
        keys = key_path.split('.')
        
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set_setting(self, key_path: str, value: Any) -> bool:
        """
        Set a specific setting using dot notation
        
        Args:
            key_path: Dot-separated path to setting (e.g., 'video_processing.default_output_format')
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self.load_config()
            keys = key_path.split('.')
            
            current = config
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[keys[-1]] = value
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Failed to set setting: {e}")
            return False
    
    def reset_config(self) -> bool:
        """
        Reset user configuration to defaults
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.user_config_file.exists():
                self.user_config_file.unlink()
            logger.info("Configuration reset to defaults")
            return True
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")
            return False
    
    def export_config(self, export_path: str) -> bool:
        """
        Export current configuration to file
        
        Args:
            export_path: Path to export configuration to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self.load_config()
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Configuration exported to: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """
        Import configuration from file
        
        Args:
            import_path: Path to import configuration from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import_file = Path(import_path)
            
            if not import_file.exists():
                logger.error(f"Import file not found: {import_path}")
                return False
            
            with open(import_file, 'r') as f:
                config = json.load(f)
            
            # Validate configuration structure
            if self._validate_config(config):
                return self.save_config(config)
            else:
                logger.error("Invalid configuration structure")
                return False
                
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation - can be expanded
        required_sections = ['video_processing', 'youtube_upload', 'app_settings']
        
        for section in required_sections:
            if section not in config:
                logger.warning(f"Missing required section: {section}")
                return False
        
        return True
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration
        
        Returns:
            Dictionary with configuration summary
        """
        config = self.load_config()
        
        return {
            'video_processing': {
                'output_format': config.get('video_processing', {}).get('default_output_format'),
                'subtitle_generation': config.get('video_processing', {}).get('enable_subtitle_generation')
            },
            'youtube_upload': {
                'privacy_status': config.get('youtube_upload', {}).get('default_privacy_status'),
                'category': config.get('youtube_upload', {}).get('default_category')
            },
            'app_settings': {
                'max_file_size': config.get('app_settings', {}).get('max_file_size_mb'),
                'auto_save': config.get('app_settings', {}).get('enable_auto_save')
            }
        }