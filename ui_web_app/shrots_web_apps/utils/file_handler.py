import os
import shutil
import uuid
from pathlib import Path
import logging
from typing import Optional, List
from werkzeug.utils import secure_filename

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileHandler:
    def __init__(self, upload_dir='uploads', output_dir='outputs', allowed_extensions=None):
        """
        Initialize file handler
        
        Args:
            upload_dir: Directory for uploaded files
            output_dir: Directory for output files
            allowed_extensions: Set of allowed file extensions
        """
        self.upload_dir = Path(upload_dir)
        self.output_dir = Path(output_dir)
        self.allowed_extensions = allowed_extensions or {'mp4', 'mov', 'avi', 'mkv', 'webm', 'wav', 'mp3', 'jpg', 'png', 'jpeg'}
        
        # Create directories if they don't exist
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def save_uploaded_file(self, file, subfolder=None) -> dict:
        """
        Save uploaded file with unique name
        
        Args:
            file: File object from request.files
            subfolder: Optional subfolder within upload directory
            
        Returns:
            Dictionary with file information
        """
        try:
            if not file or not file.filename:
                raise ValueError("No file provided")
            
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = Path(original_filename).suffix.lower()
            
            if file_extension not in self.allowed_extensions:
                raise ValueError(f"File type not allowed: {file_extension}")
            
            unique_id = str(uuid.uuid4())
            unique_filename = f"{unique_id}_{original_filename}"
            
            # Determine save path
            save_dir = self.upload_dir
            if subfolder:
                save_dir = self.upload_dir / subfolder
                save_dir.mkdir(exist_ok=True)
            
            save_path = save_dir / unique_filename
            
            # Save file
            file.save(str(save_path))
            
            logger.info(f"File saved: {save_path}")
            
            return {
                'success': True,
                'original_filename': original_filename,
                'unique_filename': unique_filename,
                'filepath': str(save_path),
                'size': os.path.getsize(save_path),
                'extension': file_extension,
                'task_id': unique_id
            }
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_multiple_files(self, files, subfolder=None) -> dict:
        """
        Save multiple uploaded files
        
        Args:
            files: List of file objects from request.files.getlist()
            subfolder: Optional subfolder within upload directory
            
        Returns:
            Dictionary with saved files information
        """
        saved_files = []
        errors = []
        
        for file in files:
            result = self.save_uploaded_file(file, subfolder)
            if result.get('success'):
                saved_files.append(result)
            else:
                errors.append(result.get('error'))
        
        return {
            'success': len(saved_files) > 0,
            'files': saved_files,
            'count': len(saved_files),
            'errors': errors
        }
    
    def get_file_info(self, filepath) -> Optional[dict]:
        """
        Get information about a file
        
        Args:
            filepath: Path to file
            
        Returns:
            Dictionary with file information or None if file not found
        """
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return None
            
            return {
                'name': file_path.name,
                'stem': file_path.stem,
                'suffix': file_path.suffix,
                'size': file_path.stat().st_size,
                'created': file_path.stat().st_ctime,
                'modified': file_path.stat().st_mtime,
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir()
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return None
    
    def delete_file(self, filepath) -> bool:
        """
        Delete a file
        
        Args:
            filepath: Path to file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(filepath)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {filepath}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    def move_file(self, source, destination) -> bool:
        """
        Move file from source to destination
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_path), str(dest_path))
            logger.info(f"File moved from {source} to {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False
    
    def copy_file(self, source, destination) -> bool:
        """
        Copy file from source to destination
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(str(source_path), str(dest_path))
            logger.info(f"File copied from {source} to {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    def cleanup_old_files(self, days=7, directory=None) -> int:
        """
        Clean up files older than specified days
        
        Args:
            days: Number of days after which files should be deleted
            directory: Directory to clean (defaults to upload_dir)
            
        Returns:
            Number of files deleted
        """
        try:
            cleanup_dir = Path(directory) if directory else self.upload_dir
            deleted_count = 0
            current_time = os.path.getmtime('.')
            
            for file_path in cleanup_dir.glob('*'):
                if file_path.is_file():
                    file_age = (current_time - file_path.stat().st_mtime) / (24 * 3600)
                    if file_age > days:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old file: {file_path}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0
    
    def get_directory_size(self, directory=None) -> int:
        """
        Get total size of directory in bytes
        
        Args:
            directory: Directory to measure (defaults to upload_dir)
            
        Returns:
            Total size in bytes
        """
        try:
            target_dir = Path(directory) if directory else self.upload_dir
            total_size = 0
            
            for file_path in target_dir.glob('**/*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to get directory size: {e}")
            return 0
    
    def list_files(self, directory=None, pattern='*') -> List[dict]:
        """
        List files in directory matching pattern
        
        Args:
            directory: Directory to list (defaults to upload_dir)
            pattern: File pattern to match
            
        Returns:
            List of file information dictionaries
        """
        try:
            target_dir = Path(directory) if directory else self.upload_dir
            files = []
            
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    files.append(self.get_file_info(file_path))
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def is_allowed_file(self, filename) -> bool:
        """
        Check if file has allowed extension
        
        Args:
            filename: Filename to check
            
        Returns:
            True if allowed, False otherwise
        """
        return Path(filename).suffix.lower() in self.allowed_extensions
    
    def format_file_size(self, size_bytes) -> str:
        """
        Format file size in human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def create_temp_directory(self) -> Path:
        """
        Create temporary directory for processing
        
        Returns:
            Path to temporary directory
        """
        temp_dir = self.upload_dir / f"temp_{uuid.uuid4()}"
        temp_dir.mkdir(exist_ok=True)
        return temp_dir
    
    def cleanup_temp_directory(self, temp_dir) -> bool:
        """
        Remove temporary directory and all contents
        
        Args:
            temp_dir: Path to temporary directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            temp_path = Path(temp_dir)
            if temp_path.exists() and temp_path.is_dir():
                shutil.rmtree(temp_path)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup temporary directory: {e}")
            return False