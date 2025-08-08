"""
Unit tests for quality_assessor.py
"""
import pytest
from pathlib import Path
import numpy as np
import math
from PIL import Image
from quality_assessor import QualityAssessor, QualityScore, assess_image_quality
from hash_generator import ImageHashResult, HashGenerator


class TestQualityAssessor:
    """Test cases for QualityAssessor class."""
    
    def test_init_default_weights(self):
        """Test QualityAssessor initialization with default weights."""
        assessor = QualityAssessor()
        
        # Check format weights exist
        assert assessor.format_weights['PSD'] == 100
        assert assessor.format_weights['PNG'] == 90
        assert assessor.format_weights['JPG'] == 60
        
        # Check score weights sum to reasonable total
        total_weight = sum(assessor.score_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Should sum to ~1.0
    
    def test_assess_format_quality(self):
        """Test format quality assessment."""
        assessor = QualityAssessor()
        
        assert assessor._assess_format_quality('PSD') == 100
        assert assessor._assess_format_quality('PNG') == 90
        assert assessor._assess_format_quality('JPG') == 60
        assert assessor._assess_format_quality('UNKNOWN') == 30  # Default
        
        # Test case insensitivity
        assert assessor._assess_format_quality('png') == 90
        assert assessor._assess_format_quality('Jpg') == 60
    
    def test_assess_resolution_quality(self):
        """Test resolution quality assessment."""
        assessor = QualityAssessor()
        
        # Test specific known values to validate logarithmic formula
        score_small = assessor._assess_resolution_quality(100, 100)  # 0.01MP
        score_medium = assessor._assess_resolution_quality(1000, 1000)  # 1MP
        score_large = assessor._assess_resolution_quality(4000, 4000)  # 16MP
        
        # Verify logarithmic scaling formula: (log10(pixels) / 8.0) * 100
        import math
        expected_small = (math.log10(10000) / 8.0) * 100  # ~50 points
        expected_medium = (math.log10(1000000) / 8.0) * 100  # ~75 points
        expected_large = (math.log10(16000000) / 8.0) * 100  # ~90 points
        
        assert abs(score_small - expected_small) < 0.1, f"Expected {expected_small}, got {score_small}"
        assert abs(score_medium - expected_medium) < 0.1, f"Expected {expected_medium}, got {score_medium}"
        assert abs(score_large - expected_large) < 0.1, f"Expected {expected_large}, got {score_large}"
        
        # Verify ordering (as secondary check)
        assert score_large > score_medium > score_small
        assert all(0 <= score <= 100 for score in [score_small, score_medium, score_large])
        
        # Test edge cases
        assert assessor._assess_resolution_quality(0, 100) == 0
        assert assessor._assess_resolution_quality(100, 0) == 0
    
    def test_assess_size_quality(self):
        """Test file size quality assessment."""
        assessor = QualityAssessor()
        
        # Test with JPG format (higher multiplier)
        score_small = assessor._assess_size_quality(10000, 'JPG')  # 10KB
        score_large = assessor._assess_size_quality(1000000, 'JPG')  # 1MB
        
        # Larger file should have higher score
        assert score_large > score_small
        assert all(0 <= score <= 100 for score in [score_small, score_large])
        
        # Test with PNG format (different multiplier)
        score_png = assessor._assess_size_quality(500000, 'PNG')
        assert 0 <= score_png <= 100
        
        # Test edge case
        assert assessor._assess_size_quality(0, 'JPG') == 0
    
    def test_assess_sharpness_simple_image(self, temp_dir):
        """Test sharpness assessment with simple images."""
        assessor = QualityAssessor()
        
        # Create a sharp image (checkerboard pattern)
        sharp_array = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(0, 100, 10):
            for j in range(0, 100, 10):
                if (i // 10 + j // 10) % 2 == 0:
                    sharp_array[i:i+10, j:j+10] = [255, 255, 255]
        sharp_img = Image.fromarray(sharp_array)
        
        # Create a blurry image (solid color)
        blur_img = Image.new('RGB', (100, 100), color='gray')
        
        sharp_score = assessor._assess_sharpness(sharp_img)
        blur_score = assessor._assess_sharpness(blur_img)
        
        # Sharp image should have higher sharpness score
        assert sharp_score > blur_score
        assert all(0 <= score <= 100 for score in [sharp_score, blur_score])
    
    def test_detect_watermark_basic(self, temp_dir):
        """Test basic watermark detection."""
        assessor = QualityAssessor()
        
        # Create image without watermark (solid color)
        clean_img = Image.new('RGB', (200, 200), color='blue')
        
        # Create image with text in corner (simulated watermark)
        watermark_img = Image.new('RGB', (200, 200), color='blue')
        # Add some high-contrast patterns in corner
        watermark_array = np.array(watermark_img)
        watermark_array[10:30, 10:30] = [255, 255, 255]  # White square in corner
        watermark_array[15:25, 15:25] = [0, 0, 0]        # Black square inside
        watermark_img = Image.fromarray(watermark_array)
        
        has_watermark_clean, conf_clean = assessor._detect_watermark(clean_img)
        has_watermark_marked, conf_marked = assessor._detect_watermark(watermark_img)
        
        # Verify return types and ranges
        assert 0 <= conf_clean <= 1
        assert 0 <= conf_marked <= 1
        assert isinstance(has_watermark_clean, bool)
        assert isinstance(has_watermark_marked, bool)
        
        # Watermarked image should have higher confidence (due to high contrast pattern in corner)
        assert conf_marked >= conf_clean, f"Watermarked image should have higher confidence: {conf_marked} >= {conf_clean}"
    
    def test_assess_image_quality_valid_image(self, sample_images_dir):
        """Test quality assessment for valid images."""
        assessor = QualityAssessor()
        generator = HashGenerator()
        
        # Get a valid image and generate hash result
        image_path = next(sample_images_dir.glob("*.jpg"))
        hash_result = generator.generate_hash(image_path)
        
        quality = assessor.assess_image_quality(hash_result)
        
        assert isinstance(quality, QualityScore)
        assert quality.file_path == image_path
        assert 0 <= quality.overall_score <= 100
        assert 0 <= quality.format_score <= 100
        assert 0 <= quality.resolution_score <= 100
        assert 0 <= quality.size_score <= 100
        assert 0 <= quality.sharpness_score <= 100
        assert isinstance(quality.has_watermark, bool)
        assert 0 <= quality.watermark_confidence <= 1
    
    def test_assess_image_quality_with_error(self, corrupted_image_dir):
        """Test quality assessment for corrupted image."""
        assessor = QualityAssessor()
        
        # Create a hash result with error
        corrupted_path = corrupted_image_dir / "corrupted.jpg"
        hash_result = ImageHashResult(
            file_path=corrupted_path,
            ahash="", dhash="", phash="",
            file_size=0, image_width=0, image_height=0,
            format="", error="Test error"
        )
        
        quality = assessor.assess_image_quality(hash_result)
        
        assert quality.overall_score == 0.0
        assert all(score == 0.0 for score in [quality.format_score, quality.resolution_score, 
                                              quality.size_score, quality.sharpness_score])
        assert quality.has_watermark is False
        assert quality.watermark_confidence == 0.0
    
    def test_compare_images_single(self, sample_images_dir):
        """Test comparing single image."""
        assessor = QualityAssessor()
        generator = HashGenerator()
        
        image_path = next(sample_images_dir.glob("*.jpg"))
        hash_result = generator.generate_hash(image_path)
        
        best = assessor.compare_images([hash_result])
        assert best == hash_result
    
    def test_compare_images_multiple(self, temp_dir):
        """Test comparing multiple images."""
        assessor = QualityAssessor()
        generator = HashGenerator()
        
        # Create two images - one PNG (higher format score), one larger JPG
        from PIL import Image
        
        # Small PNG
        small_png = Image.new('RGB', (100, 100), color='red')
        png_path = temp_dir / "small.png"
        small_png.save(png_path, "PNG")
        
        # Large JPG
        large_jpg = Image.new('RGB', (500, 500), color='red')
        jpg_path = temp_dir / "large.jpg"
        large_jpg.save(jpg_path, "JPEG", quality=95)
        
        png_result = generator.generate_hash(png_path)
        jpg_result = generator.generate_hash(jpg_path)
        
        best = assessor.compare_images([png_result, jpg_result])
        
        # Should be one of the input images
        assert best in [png_result, jpg_result]
        # PNG format vs larger JPG - depends on scoring weights
        assert isinstance(best, ImageHashResult)
    
    def test_format_priority_ordering(self, temp_dir):
        """Test that format priority works as expected."""
        assessor = QualityAssessor()
        generator = HashGenerator()
        
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Create same image in different formats
        jpg_path = temp_dir / "test.jpg"
        png_path = temp_dir / "test.png"
        
        img.save(jpg_path, "JPEG", quality=95)
        img.save(png_path, "PNG")
        
        jpg_result = generator.generate_hash(jpg_path)
        png_result = generator.generate_hash(png_path)
        
        # PNG should be preferred over JPG for same content
        best = assessor.compare_images([jpg_result, png_result])
        
        # Given same resolution and similar size, PNG should win
        assert best.format == "PNG"
    
    def test_overall_score_weighting(self, temp_dir):
        """Test that overall score combines components correctly using known inputs."""
        assessor = QualityAssessor()
        
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        test_path = temp_dir / "test.jpg"
        img.save(test_path, "JPEG", quality=95)
        
        from hash_generator import ImageHashResult
        hash_result = ImageHashResult(
            file_path=test_path,
            ahash="abcd1234", dhash="efgh5678", phash="ijkl9012",
            file_size=10000, image_width=100, image_height=100,
            format="JPEG", error=None
        )
        
        quality = assessor.assess_image_quality(hash_result)
        
        # Calculate expected score manually to validate weighting
        expected_format = 60  # JPEG score from format_weights
        expected_resolution = (math.log10(10000) / 8.0) * 100  # Resolution formula
        expected_size = (math.log10(10000) / 10.0) * 100 * 2.0  # Size formula with JPEG multiplier
        # Sharpness and watermark vary, so we'll just verify the structure
        
        # Verify individual components are reasonable
        assert 50 <= quality.format_score <= 70, f"Format score should be ~60 for JPEG, got {quality.format_score}"
        assert quality.resolution_score > 0, "Resolution score should be positive"
        assert quality.size_score > 0, "Size score should be positive"
        assert 0 <= quality.sharpness_score <= 100, "Sharpness score should be 0-100"
        
        # Verify overall score is within expected range based on weights
        min_expected = (expected_format * 0.30 + expected_resolution * 0.25) * 0.8  # Conservative estimate
        max_expected = (expected_format * 0.30 + expected_resolution * 0.25 + 100 * 0.45)  # Optimistic estimate
        
        assert min_expected <= quality.overall_score <= max_expected, \
            f"Overall score {quality.overall_score} not in expected range [{min_expected}, {max_expected}]"


class TestQualityScore:
    """Test cases for QualityScore dataclass."""
    
    def test_quality_score_creation(self, temp_dir):
        """Test QualityScore object creation."""
        test_path = temp_dir / "test.jpg"
        
        score = QualityScore(
            file_path=test_path,
            overall_score=85.5,
            format_score=90.0,
            resolution_score=80.0,
            size_score=85.0,
            sharpness_score=88.0,
            has_watermark=False,
            watermark_confidence=0.1
        )
        
        assert score.file_path == test_path
        assert score.overall_score == 85.5
        assert score.format_score == 90.0
        assert score.has_watermark is False
        assert score.watermark_confidence == 0.1


    def test_assess_sharpness_large_image(self, temp_dir):
        """Test sharpness analysis with large image requiring resize."""
        assessor = QualityAssessor()
        
        # Create large image (>1000px) to trigger resize code path
        from PIL import Image
        import numpy as np
        
        # Create 1500x1500 image with pattern
        large_array = np.zeros((1500, 1500, 3), dtype=np.uint8)
        # Add checkerboard pattern to create edges for sharpness detection
        for i in range(0, 1500, 100):
            for j in range(0, 1500, 100):
                if (i // 100 + j // 100) % 2 == 0:
                    large_array[i:i+100, j:j+100] = [255, 255, 255]
        
        large_img = Image.fromarray(large_array)
        
        # Should handle large image without error and resize internally
        sharpness_score = assessor._assess_sharpness(large_img)
        
        assert 0 <= sharpness_score <= 100
        assert isinstance(sharpness_score, float)
    
    def test_assess_image_quality_rgb_conversion(self, temp_dir):
        """Test quality assessment with non-RGB image requiring conversion."""
        assessor = QualityAssessor()
        generator = HashGenerator()
        
        # Create RGBA image
        from PIL import Image
        rgba_img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))  # Semi-transparent red
        rgba_path = temp_dir / "test_rgba.png"
        rgba_img.save(rgba_path, "PNG")
        
        # Generate hash result
        hash_result = generator.generate_hash(rgba_path)
        
        # Should successfully assess quality despite RGBA format
        quality = assessor.assess_image_quality(hash_result)
        
        assert not hash_result.error
        assert quality.overall_score > 0
        assert 0 <= quality.sharpness_score <= 100


class TestAssessImageQualityFunction:
    """Test the convenience function assess_image_quality."""
    
    def test_assess_image_quality_function(self, sample_images_dir):
        """Test assess_image_quality convenience function."""
        generator = HashGenerator()
        image_path = next(sample_images_dir.glob("*.jpg"))
        hash_result = generator.generate_hash(image_path)
        
        quality = assess_image_quality(hash_result)
        
        assert isinstance(quality, QualityScore)
        assert quality.file_path == image_path
        assert 0 <= quality.overall_score <= 100