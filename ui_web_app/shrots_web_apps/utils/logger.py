import logging
import os
from pathlib import Path
from datetime import datetime
import colorlog
from logging.handlers import RotatingFileHandler
import queue
import threading

class AppLogger:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, log_dir='logs', app_name='VideoProcessorPro'):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize(log_dir, app_name)
            return cls._instance
    
    def _initialize(self, log_dir, app_name):
        """Initialize the logger instance"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.app_name = app_name
        
        # Create log file with date
        log_filename = f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"
        self.log_file = self.log_dir / log_filename
        
        # Set up main logger
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler with colors
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Queue handler for web interface
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        self.queue_handler.setLevel(logging.INFO)
        queue_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.queue_handler.setFormatter(queue_formatter)
        self.logger.addHandler(self.queue_handler)
        
        self.logger.info(f"Logger initialized for {app_name}")
    
    def get_logger(self):
        """Get the configured logger instance"""
        return self.logger
    
    def get_log_queue(self):
        """Get the log queue for web interface"""
        return self.log_queue
    
    def get_log_file_path(self):
        """Get the current log file path"""
        return str(self.log_file)
    
    def get_recent_logs(self, lines=100):
        """Get recent log entries from file"""
        try:
            if not self.log_file.exists():
                return []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
                return log_lines[-lines:] if len(log_lines) > lines else log_lines
        except Exception as e:
            self.logger.error(f"Failed to read log file: {e}")
            return []
    
    def cleanup_old_logs(self, days=30):
        """Clean up log files older than specified days"""
        try:
            current_time = datetime.now()
            deleted_count = 0
            
            for log_file in self.log_dir.glob(f"{self.app_name}_*.log"):
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                age_days = (current_time - file_time).days
                
                if age_days > days:
                    log_file.unlink()
                    deleted_count += 1
                    self.logger.info(f"Deleted old log file: {log_file}")
            
            return deleted_count
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            return 0


class QueueHandler(logging.Handler):
    """Custom logging handler that puts log messages into a queue"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        """Put log record into the queue"""
        try:
            self.log_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': self.format(record),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            })
        except Exception:
            self.handleError(record)


def setup_logging(log_dir='logs', app_name='VideoProcessorPro', level=logging.INFO):
    """
    Setup logging for the application
    
    Args:
        log_dir: Directory for log files
        app_name: Name of the application
        level: Logging level
        
    Returns:
        Logger instance
    """
    app_logger = AppLogger(log_dir, app_name)
    logger = app_logger.get_logger()
    logger.setLevel(level)
    return logger


def get_logger(app_name='VideoProcessorPro'):
    """
    Get existing logger instance or create new one
    
    Args:
        app_name: Name of the application
        
    Returns:
        Logger instance
    """
    app_logger = AppLogger(app_name=app_name)
    return app_logger.get_logger()