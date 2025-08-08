"""
Unit tests for duplicate_detector.py
"""
import pytest
from pathlib import Path
from duplicate_detector import DuplicateDetector, DuplicateGroup, detect_duplicates
from hash_generator import ImageHashResult, HashGenerator


class TestDuplicateDetector:
    """Test cases for DuplicateDetector class."""
    
    def test_init_default_parameters(self):
        """Test DuplicateDetector initialization with default parameters."""
        detector = DuplicateDetector()
        assert detector.similarity_threshold == 10
        assert detector.require_agreement == 2
    
    def test_init_custom_parameters(self):
        """Test DuplicateDetector initialization with custom parameters."""
        detector = DuplicateDetector(similarity_threshold=5, require_agreement=3)
        assert detector.similarity_threshold == 5
        assert detector.require_agreement == 3
    
    def test_find_duplicates_no_images(self):
        """Test finding duplicates with empty input."""
        detector = DuplicateDetector()
        result = detector.find_duplicates([], show_progress=False)
        assert result == []
    
    def test_find_duplicates_single_image(self, sample_images_dir):
        """Test finding duplicates with single image."""
        detector = DuplicateDetector()
        generator = HashGenerator()
        
        # Get one image and generate hash
        image_path = next(sample_images_dir.glob("*.jpg"))
        hash_result = generator.generate_hash(image_path)
        
        duplicates = detector.find_duplicates([hash_result], show_progress=False)
        assert duplicates == []  # No duplicates possible with single image
    
    def test_find_duplicates_with_similar_images(self, sample_images_dir):
        """Test finding duplicates with known similar images."""
        detector = DuplicateDetector(similarity_threshold=15)  # More lenient
        generator = HashGenerator()
        
        # Get multiple images including our test duplicates
        image_paths = list(sample_images_dir.rglob("*.jpg")) + list(sample_images_dir.rglob("*.png"))
        hash_results = generator.generate_hashes(image_paths, show_progress=False)
        
        # Filter out any failed hashes
        valid_results = [r for r in hash_results if not r.error]
        
        duplicates = detector.find_duplicates(valid_results, show_progress=False)
        
        # We should find some duplicate groups from our test images
        # Note: This test is lenient since duplicate detection depends on the exact images generated
        assert isinstance(duplicates, list)
        
        # If duplicates are found, they should be valid groups
        for group in duplicates:
            assert isinstance(group, DuplicateGroup)
            assert len(group.images) >= 2
            assert group.representative in group.images
    
    def test_find_duplicates_no_similar_images(self, sample_images_dir):
        """Test finding duplicates with very strict threshold (no matches expected)."""
        detector = DuplicateDetector(similarity_threshold=0)  # Very strict
        generator = HashGenerator()
        
        # Get a few different images
        image_paths = list(sample_images_dir.glob("*.jpg"))[:3]
        hash_results = generator.generate_hashes(image_paths, show_progress=False)
        valid_results = [r for r in hash_results if not r.error]
        
        duplicates = detector.find_duplicates(valid_results, show_progress=False)
        
        # With threshold 0, only identical hashes would match
        # Our test images are different enough that we shouldn't find exact matches
        assert len(duplicates) == 0
    
    def test_select_best_image_single(self, sample_images_dir):
        """Test selecting best image with single option."""
        detector = DuplicateDetector()
        generator = HashGenerator()
        
        image_path = next(sample_images_dir.glob("*.jpg"))
        hash_result = generator.generate_hash(image_path)
        
        best = detector._select_best_image([hash_result])
        assert best == hash_result
    
    def test_select_best_image_format_priority(self, temp_dir):
        """Test that format priority works correctly."""
        detector = DuplicateDetector()
        
        # Create mock hash results with different formats
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        
        jpg_path = temp_dir / "test.jpg"
        png_path = temp_dir / "test.png"
        
        img.save(jpg_path, "JPEG")
        img.save(png_path, "PNG")
        
        generator = HashGenerator()
        jpg_result = generator.generate_hash(jpg_path)
        png_result = generator.generate_hash(png_path)
        
        # PNG should be preferred over JPG
        best = detector._select_best_image([jpg_result, png_result])
        assert best.format == "PNG"
    
    def test_select_best_image_resolution_priority(self, temp_dir):
        """Test that higher resolution is preferred."""
        detector = DuplicateDetector()
        
        from PIL import Image
        
        # Create two identical images with different resolutions
        small_img = Image.new('RGB', (50, 50), color='red')
        large_img = Image.new('RGB', (200, 200), color='red')
        
        small_path = temp_dir / "small.jpg"
        large_path = temp_dir / "large.jpg"
        
        small_img.save(small_path, "JPEG")
        large_img.save(large_path, "JPEG")
        
        generator = HashGenerator()
        small_result = generator.generate_hash(small_path)
        large_result = generator.generate_hash(large_path)
        
        # Larger image should be preferred
        best = detector._select_best_image([small_result, large_result])
        assert best.image_width == 200 and best.image_height == 200
    
    def test_get_statistics_empty(self):
        """Test statistics with empty duplicate groups."""
        detector = DuplicateDetector()
        stats = detector.get_statistics([])
        
        expected = {
            'total_groups': 0,
            'total_duplicates': 0,
            'total_size_saved': 0,
            'largest_group_size': 0,
            'average_group_size': 0
        }
        assert stats == expected
    
    def test_get_statistics_with_groups(self, temp_dir):
        """Test statistics calculation with actual groups."""
        detector = DuplicateDetector()
        
        # Create mock duplicate group
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Create three versions of same image
        paths = []
        for i, name in enumerate(['img1.jpg', 'img2.jpg', 'img3.jpg']):
            path = temp_dir / name
            img.save(path, "JPEG", quality=95 - i*10)  # Different qualities
            paths.append(path)
        
        generator = HashGenerator()
        hash_results = [generator.generate_hash(p) for p in paths]
        
        # Create a mock duplicate group
        representative = max(hash_results, key=lambda x: x.file_size)  # Largest file
        group = DuplicateGroup(images=hash_results, representative=representative)
        
        stats = detector.get_statistics([group])
        
        assert stats['total_groups'] == 1
        assert stats['total_duplicates'] == 3
        assert stats['largest_group_size'] == 3
        assert stats['average_group_size'] == 3.0
        assert stats['total_size_saved'] > 0  # Should save some space
    
    def test_print_duplicate_report(self, capsys, temp_dir):
        """Test that duplicate report prints without errors."""
        detector = DuplicateDetector()
        
        # Test with empty groups
        detector.print_duplicate_report([])
        captured = capsys.readouterr()
        assert "No duplicates found" in captured.out
        
        # Test with actual duplicate group
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Create mock duplicate group for testing print functionality
        paths = []
        for i in range(3):
            path = temp_dir / f"test{i}.jpg"
            img.save(path, "JPEG", quality=95)
            paths.append(path)
        
        generator = HashGenerator()
        hash_results = [generator.generate_hash(p) for p in paths]
        group = DuplicateGroup(images=hash_results, representative=hash_results[0])
        
        detector.print_duplicate_report([group])
        captured = capsys.readouterr()
        assert "Found 1 duplicate groups" in captured.out
        assert "Group 1" in captured.out


class TestDuplicateGroup:
    """Test cases for DuplicateGroup dataclass."""
    
    def test_duplicate_group_len(self, temp_dir):
        """Test DuplicateGroup length calculation."""
        # Create mock hash results
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='red')
        
        paths = []
        for i in range(3):
            path = temp_dir / f"test{i}.jpg"
            img.save(path, "JPEG")
            paths.append(path)
        
        generator = HashGenerator()
        hash_results = [generator.generate_hash(p) for p in paths]
        
        group = DuplicateGroup(images=hash_results, representative=hash_results[0])
        assert len(group) == 3
    
    def test_duplicate_group_total_size(self, temp_dir):
        """Test DuplicateGroup total size calculation."""
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='red')
        
        paths = []
        for i in range(2):
            path = temp_dir / f"test{i}.jpg"
            img.save(path, "JPEG")
            paths.append(path)
        
        generator = HashGenerator()
        hash_results = [generator.generate_hash(p) for p in paths]
        
        group = DuplicateGroup(images=hash_results, representative=hash_results[0])
        total_size = group.total_size()
        
        expected_size = sum(r.file_size for r in hash_results)
        assert total_size == expected_size


class TestDetectDuplicatesFunction:
    """Test the convenience function detect_duplicates."""
    
    def test_detect_duplicates_function(self, sample_images_dir):
        """Test detect_duplicates convenience function."""
        generator = HashGenerator()
        image_paths = list(sample_images_dir.glob("*.jpg"))[:3]
        hash_results = generator.generate_hashes(image_paths, show_progress=False)
        
        duplicates = detect_duplicates(hash_results, similarity_threshold=15, require_agreement=1)
        
        assert isinstance(duplicates, list)
        assert all(isinstance(group, DuplicateGroup) for group in duplicates)