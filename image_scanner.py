"""
Image scanner module for recursively discovering image files in directories.
"""
import os
from pathlib import Path
from typing import List, Set
from tqdm import tqdm

class ImageScanner:
    """Scans directories recursively to find image files."""
    
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', 
        '.webp', '.psd', '.raw', '.cr2', '.nef', '.arw', '.dng'
    }
    
    def __init__(self, supported_extensions: Set[str] = None):
        """Initialize scanner with optional custom extensions."""
        if supported_extensions:
            self.supported_extensions = {ext.lower() for ext in supported_extensions}
        else:
            self.supported_extensions = self.SUPPORTED_EXTENSIONS
    
    def scan_directory(self, directory_path: str, show_progress: bool = True) -> List[Path]:
        """
        Recursively scan directory for image files.
        
        Args:
            directory_path: Path to directory to scan
            show_progress: Whether to show progress bar
            
        Returns:
            List of Path objects for found image files
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")
        
        # First pass: count total files for progress bar
        if show_progress:
            print("Counting files...")
            total_files = sum(1 for _ in directory.rglob('*') if _.is_file())
        else:
            total_files = None
        
        # Second pass: find image files
        image_files = []
        
        file_iterator = directory.rglob('*')
        if show_progress and total_files:
            file_iterator = tqdm(file_iterator, 
                               total=total_files,
                               desc="Scanning for images",
                               unit="files")
        
        for file_path in file_iterator:
            if self._is_image_file(file_path):
                image_files.append(file_path)
        
        if show_progress:
            print(f"Found {len(image_files)} image files")
        
        return image_files
    
    def _is_image_file(self, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        if not file_path.is_file():
            return False
        
        extension = file_path.suffix.lower()
        return extension in self.supported_extensions
    
    def get_supported_extensions(self) -> Set[str]:
        """Return set of supported file extensions."""
        return self.supported_extensions.copy()
    
    def add_extension(self, extension: str) -> None:
        """Add a new supported file extension."""
        self.supported_extensions.add(extension.lower())
    
    def remove_extension(self, extension: str) -> None:
        """Remove a supported file extension."""
        self.supported_extensions.discard(extension.lower())


def scan_for_images(directory_path: str, extensions: Set[str] = None) -> List[Path]:
    """
    Convenience function to scan for image files.
    
    Args:
        directory_path: Path to directory to scan
        extensions: Optional set of file extensions to look for
        
    Returns:
        List of Path objects for found image files
    """
    scanner = ImageScanner(extensions)
    return scanner.scan_directory(directory_path)


if __name__ == "__main__":
    # Test the scanner
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python image_scanner.py <directory_path>")
        sys.exit(1)
    
    directory = sys.argv[1]
    try:
        images = scan_for_images(directory)
        print(f"\nFound {len(images)} images:")
        for img in images[:10]:  # Show first 10
            print(f"  {img}")
        if len(images) > 10:
            print(f"  ... and {len(images) - 10} more")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)