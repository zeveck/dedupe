"""
Unit tests for image_scanner.py
"""
import pytest
from pathlib import Path
from image_scanner import ImageScanner, scan_for_images


class TestImageScanner:
    """Test cases for ImageScanner class."""
    
    def test_init_default_extensions(self):
        """Test ImageScanner initialization with default extensions."""
        scanner = ImageScanner()
        expected_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', 
            '.webp', '.psd', '.raw', '.cr2', '.nef', '.arw', '.dng'
        }
        assert scanner.supported_extensions == expected_extensions
    
    def test_init_custom_extensions(self):
        """Test ImageScanner initialization with custom extensions."""
        custom_extensions = {'.jpg', '.png', '.custom'}
        scanner = ImageScanner(custom_extensions)
        assert scanner.supported_extensions == {'.jpg', '.png', '.custom'}
    
    def test_scan_directory_basic(self, sample_images_dir):
        """Test basic directory scanning functionality."""
        scanner = ImageScanner()
        images = scanner.scan_directory(str(sample_images_dir), show_progress=False)
        
        # Should find all test images we created (9 total: 6 in main dir + 2 in subdir + 1 checkerboard)
        assert len(images) == 9
        assert all(isinstance(path, Path) for path in images)
        assert all(path.exists() for path in images)
    
    def test_scan_directory_recursive(self, sample_images_dir):
        """Test that scanning finds images in subdirectories."""
        scanner = ImageScanner()
        images = scanner.scan_directory(str(sample_images_dir), show_progress=False)
        
        # Should find images in subdirectory too
        subdir_images = [img for img in images if 'subdir' in str(img)]
        assert len(subdir_images) == 2  # Exactly 2 images in subdir
    
    def test_scan_nonexistent_directory(self):
        """Test scanning a directory that doesn't exist."""
        scanner = ImageScanner()
        with pytest.raises(FileNotFoundError):
            scanner.scan_directory("/nonexistent/directory")
    
    def test_scan_file_instead_of_directory(self, sample_images_dir):
        """Test scanning a file path instead of directory."""
        scanner = ImageScanner()
        # Get first image file
        images = scanner.scan_directory(str(sample_images_dir), show_progress=False)
        first_image = images[0]
        
        with pytest.raises(NotADirectoryError):
            scanner.scan_directory(str(first_image))
    
    def test_is_image_file(self, sample_images_dir):
        """Test _is_image_file method."""
        scanner = ImageScanner()
        images = scanner.scan_directory(str(sample_images_dir), show_progress=False)
        
        # All returned images should pass the image file test
        for img in images:
            assert scanner._is_image_file(img)
        
        # Test with non-image file
        text_file = sample_images_dir / "test.txt"
        text_file.write_text("not an image")
        assert not scanner._is_image_file(text_file)
    
    def test_add_remove_extension(self):
        """Test adding and removing file extensions."""
        scanner = ImageScanner()
        initial_count = len(scanner.supported_extensions)
        
        # Add new extension
        scanner.add_extension('.xyz')
        assert '.xyz' in scanner.supported_extensions
        assert len(scanner.supported_extensions) == initial_count + 1
        
        # Remove extension
        scanner.remove_extension('.xyz')
        assert '.xyz' not in scanner.supported_extensions
        assert len(scanner.supported_extensions) == initial_count
    
    def test_get_supported_extensions(self):
        """Test getting supported extensions returns a copy."""
        scanner = ImageScanner()
        extensions = scanner.get_supported_extensions()
        
        # Modify returned set
        extensions.add('.test')
        
        # Original should be unchanged
        assert '.test' not in scanner.supported_extensions
    
    def test_case_insensitive_extensions(self, temp_dir):
        """Test that extensions are handled case-insensitively."""
        scanner = ImageScanner()
        
        # Create files with different case extensions
        (temp_dir / "test.JPG").touch()
        (temp_dir / "test.Png").touch()
        (temp_dir / "test.TIFF").touch()
        
        images = scanner.scan_directory(str(temp_dir), show_progress=False)
        assert len(images) == 3
    
    def test_custom_extensions_filtering(self, temp_dir):
        """Test scanning with custom extensions."""
        # Create various files
        (temp_dir / "image.jpg").touch()
        (temp_dir / "image.png").touch()
        (temp_dir / "image.xyz").touch()
        (temp_dir / "document.pdf").touch()
        
        # Scan with only .xyz extension
        scanner = ImageScanner({'.xyz'})
        images = scanner.scan_directory(str(temp_dir), show_progress=False)
        
        assert len(images) == 1
        assert images[0].name == "image.xyz"


class TestScanForImagesFunction:
    """Test the convenience function scan_for_images."""
    
    def test_scan_for_images_default(self, sample_images_dir):
        """Test scan_for_images with default parameters."""
        images = scan_for_images(str(sample_images_dir))
        assert len(images) == 9
        assert all(isinstance(path, Path) for path in images)
    
    def test_scan_for_images_custom_extensions(self, temp_dir):
        """Test scan_for_images with custom extensions."""
        # Create test files
        (temp_dir / "test.jpg").touch()
        (temp_dir / "test.custom").touch()
        (temp_dir / "test.other").touch()
        
        images = scan_for_images(str(temp_dir), {'.custom'})
        assert len(images) == 1
        assert images[0].name == "test.custom"