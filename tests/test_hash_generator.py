"""
Unit tests for hash_generator.py
"""
import pytest
from pathlib import Path
import numpy as np
from hash_generator import HashGenerator, ImageHashResult, generate_image_hashes


class TestHashGenerator:
    """Test cases for HashGenerator class."""
    
    def test_init_default_hash_size(self):
        """Test HashGenerator initialization with default hash size."""
        generator = HashGenerator()
        assert generator.hash_size == 8
    
    def test_init_custom_hash_size(self):
        """Test HashGenerator initialization with custom hash size."""
        generator = HashGenerator(hash_size=16)
        assert generator.hash_size == 16
    
    def test_generate_hash_valid_image(self, sample_images_dir):
        """Test generating hash for a valid image."""
        generator = HashGenerator()
        image_path = next(sample_images_dir.glob("*.jpg"))
        
        result = generator.generate_hash(image_path)
        
        assert isinstance(result, ImageHashResult)
        assert result.file_path == image_path
        assert result.error is None
        
        # Validate hash format and length (8x8 = 64 bits = 16 hex chars for default hash_size=8)
        expected_length = generator.hash_size * generator.hash_size // 4
        assert len(result.ahash) == expected_length, f"aHash should be {expected_length} chars, got {len(result.ahash)}"
        assert len(result.dhash) == expected_length, f"dHash should be {expected_length} chars, got {len(result.dhash)}"
        assert len(result.phash) == expected_length, f"pHash should be {expected_length} chars, got {len(result.phash)}"
        
        # Validate hashes are proper hexadecimal
        assert all(c in '0123456789abcdef' for c in result.ahash.lower()), "aHash should be hexadecimal"
        assert all(c in '0123456789abcdef' for c in result.dhash.lower()), "dHash should be hexadecimal"
        assert all(c in '0123456789abcdef' for c in result.phash.lower()), "pHash should be hexadecimal"
        
        # Validate metadata
        assert result.file_size > 0
        assert result.image_width > 0
        assert result.image_height > 0
        assert result.format in ['JPEG', 'PNG', 'GIF', 'BMP', 'TIFF', 'WEBP'], f"Unexpected format: {result.format}"
    
    def test_generate_hash_corrupted_image(self, corrupted_image_dir):
        """Test generating hash for a corrupted image."""
        generator = HashGenerator()
        corrupted_path = corrupted_image_dir / "corrupted.jpg"
        
        result = generator.generate_hash(corrupted_path)
        
        assert isinstance(result, ImageHashResult)
        assert result.file_path == corrupted_path
        assert result.error is not None
        assert result.ahash == ""
        assert result.dhash == ""
        assert result.phash == ""
    
    def test_generate_hashes_multiple_images(self, sample_images_dir):
        """Test generating hashes for multiple images."""
        generator = HashGenerator()
        image_paths = list(sample_images_dir.rglob("*.jpg"))[:3]  # First 3 JPG images
        
        results = generator.generate_hashes(image_paths, show_progress=False)
        
        assert len(results) == len(image_paths)
        assert all(isinstance(r, ImageHashResult) for r in results)
        
        # Check that valid images have hashes
        valid_results = [r for r in results if not r.error]
        assert len(valid_results) >= 1
        for result in valid_results:
            assert len(result.ahash) > 0
            assert len(result.dhash) > 0
            assert len(result.phash) > 0
    
    def test_hash_hamming_distance(self):
        """Test Hamming distance calculation between hashes."""
        generator = HashGenerator()
        
        # Test identical hashes
        hash1 = "abcd1234"
        hash2 = "abcd1234"
        assert generator.hash_hamming_distance(hash1, hash2) == 0
        
        # Test completely different hashes (all bits different)
        hash3 = "0000"
        hash4 = "ffff"
        distance = generator.hash_hamming_distance(hash3, hash4)
        assert distance == 16  # 4 hex digits * 4 bits each = 16 bits all different
    
    def test_hash_hamming_distance_different_lengths(self):
        """Test Hamming distance with different length hashes."""
        generator = HashGenerator()
        
        with pytest.raises(ValueError, match="Hash strings must be the same length"):
            generator.hash_hamming_distance("abc", "abcdef")
    
    def test_are_similar_identical_hashes(self):
        """Test similarity check with identical hashes."""
        generator = HashGenerator()
        hash1 = "abcd1234"
        hash2 = "abcd1234"
        
        assert generator.are_similar(hash1, hash2, threshold=10)
    
    def test_are_similar_different_thresholds(self):
        """Test similarity check with different thresholds."""
        generator = HashGenerator()
        
        # Hashes that differ by a few bits
        hash1 = "0000"
        hash2 = "0001"  # Differs by 1 bit
        
        assert generator.are_similar(hash1, hash2, threshold=5)
        assert not generator.are_similar(hash1, hash2, threshold=0)
    
    def test_are_similar_empty_hashes(self):
        """Test similarity check with empty hashes."""
        generator = HashGenerator()
        
        assert not generator.are_similar("", "abcd")
        assert not generator.are_similar("abcd", "")
        assert not generator.are_similar("", "")
    
    def test_get_consensus_similarity(self, sample_images_dir):
        """Test consensus similarity between two images."""
        generator = HashGenerator()
        
        # Get two different images
        image_paths = list(sample_images_dir.glob("*.jpg"))
        if len(image_paths) >= 2:
            result1 = generator.generate_hash(image_paths[0])
            result2 = generator.generate_hash(image_paths[1])
            
            # Test consensus with different agreement requirements
            similarity1 = generator.get_consensus_similarity(result1, result2, threshold=10, require_agreement=1)
            similarity2 = generator.get_consensus_similarity(result1, result2, threshold=10, require_agreement=3)
            
            # With require_agreement=1, it's easier to be similar
            # With require_agreement=3, all algorithms must agree
            assert isinstance(similarity1, bool)
            assert isinstance(similarity2, bool)
    
    def test_get_consensus_similarity_with_errors(self, corrupted_image_dir):
        """Test consensus similarity when one result has an error."""
        generator = HashGenerator()
        
        valid_path = corrupted_image_dir / "valid.jpg"
        corrupted_path = corrupted_image_dir / "corrupted.jpg"
        
        result1 = generator.generate_hash(valid_path)
        result2 = generator.generate_hash(corrupted_path)
        
        # Should return False when one result has an error
        similarity = generator.get_consensus_similarity(result1, result2)
        assert similarity is False
    
    def test_identical_images_different_formats(self, temp_dir):
        """Test that identical images in different formats have similar hashes."""
        generator = HashGenerator()
        
        # Create identical image in different formats
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='red')
        
        jpg_path = temp_dir / "test.jpg"
        png_path = temp_dir / "test.png"
        
        img.save(jpg_path, "JPEG", quality=95)
        img.save(png_path, "PNG")
        
        result1 = generator.generate_hash(jpg_path)
        result2 = generator.generate_hash(png_path)
        
        # Should be very similar despite different formats
        assert generator.get_consensus_similarity(result1, result2, threshold=5, require_agreement=1)
    
    def test_hash_consistency(self, sample_images_dir):
        """Test that generating hashes for the same image twice gives identical results."""
        generator = HashGenerator()
        image_path = next(sample_images_dir.glob("*.jpg"))
        
        result1 = generator.generate_hash(image_path)
        result2 = generator.generate_hash(image_path)
        
        # Hash consistency is critical for duplicate detection
        assert result1.ahash == result2.ahash, "aHash must be deterministic"
        assert result1.dhash == result2.dhash, "dHash must be deterministic"
        assert result1.phash == result2.phash, "pHash must be deterministic"
        
        # Verify hashes are not just empty or default values
        assert result1.ahash != "0" * len(result1.ahash), "aHash should not be all zeros"
        assert result1.dhash != "f" * len(result1.dhash), "dHash should not be all ones"
        assert result1.phash != result1.ahash, "Different algorithms should produce different hashes"
        
        # Metadata should also be consistent
        assert result1.file_size == result2.file_size
        assert result1.image_width == result2.image_width
        assert result1.image_height == result2.image_height


    def test_generate_hash_non_rgb_modes(self, temp_dir):
        """Test hash generation with non-RGB image modes."""
        generator = HashGenerator()
        
        from PIL import Image
        
        # Create images in different modes
        base_img = Image.new('RGB', (50, 50), color='red')
        
        # Test RGBA mode
        rgba_img = base_img.convert('RGBA')
        rgba_path = temp_dir / "test_rgba.png"
        rgba_img.save(rgba_path, "PNG")
        
        # Test P mode (palette)
        p_img = base_img.convert('P')
        p_path = temp_dir / "test_p.png" 
        p_img.save(p_path, "PNG")
        
        # Test L mode (grayscale)
        l_img = base_img.convert('L')
        l_path = temp_dir / "test_l.png"
        l_img.save(l_path, "PNG")
        
        # Generate hashes for all modes
        rgba_result = generator.generate_hash(rgba_path)
        p_result = generator.generate_hash(p_path)
        l_result = generator.generate_hash(l_path)
        
        # All should succeed (get converted to RGB internally)
        assert not rgba_result.error
        assert not p_result.error  
        assert not l_result.error
        
        # All should have valid hash strings
        for result in [rgba_result, p_result, l_result]:
            assert len(result.ahash) > 0
            assert len(result.dhash) > 0
            assert len(result.phash) > 0
    
    def test_hash_hamming_distance_invalid_hex(self):
        """Test fallback Hamming distance calculation with invalid hex strings."""
        generator = HashGenerator()
        
        # Test with non-hex characters (should use fallback character comparison)
        hash1 = "abcdxyzg"  # Contains non-hex chars
        hash2 = "abcdxyzy"  # Similar with 1 char different
        
        # Should not raise exception, should use character-wise comparison
        distance = generator.hash_hamming_distance(hash1, hash2)
        assert distance == 1  # Only last character differs
        
        # Test with completely invalid strings of same length
        hash3 = "notahexstring"  # 13 chars
        hash4 = "alsonotahex12"  # 13 chars (same length)
        
        distance2 = generator.hash_hamming_distance(hash3, hash4)
        assert isinstance(distance2, int)
        assert distance2 >= 0
    
    def test_perceptual_similarity_validation(self, temp_dir):
        """Test that perceptually similar images have similar hashes."""
        generator = HashGenerator()
        
        # Create base image with checkerboard pattern
        from PIL import Image
        base_img = Image.new('RGB', (100, 100), color='white')
        base_array = np.array(base_img)
        for i in range(0, 100, 10):
            for j in range(0, 100, 10):
                if (i // 10 + j // 10) % 2 == 0:
                    base_array[i:i+10, j:j+10] = [255, 0, 0]  # Red squares
        base_img = Image.fromarray(base_array)
        
        base_path = temp_dir / "base.jpg"
        base_img.save(base_path, "JPEG", quality=95)
        
        # Create similar image (slightly brighter)
        similar_array = base_array.copy()
        similar_array = np.clip(similar_array.astype(int) + 20, 0, 255).astype(np.uint8)
        similar_img = Image.fromarray(similar_array)
        similar_path = temp_dir / "similar.jpg"
        similar_img.save(similar_path, "JPEG", quality=95)
        
        # Create very different image (different pattern)
        different_img = Image.new('RGB', (100, 100), color='white')
        different_array = np.array(different_img)
        for i in range(100):  # Diagonal stripes
            for j in range(100):
                if (i + j) % 20 < 10:
                    different_array[i, j] = [0, 0, 255]  # Blue diagonal stripes
        different_img = Image.fromarray(different_array)
        different_path = temp_dir / "different.jpg"
        different_img.save(different_path, "JPEG", quality=95)
        
        # Generate hashes
        base_result = generator.generate_hash(base_path)
        similar_result = generator.generate_hash(similar_path)
        different_result = generator.generate_hash(different_path)
        
        # Test similarity detection
        assert generator.get_consensus_similarity(base_result, similar_result, threshold=15, require_agreement=2), \
            "Similar images should be detected as duplicates"
        
        assert not generator.get_consensus_similarity(base_result, different_result, threshold=10, require_agreement=2), \
            "Different images should not be detected as duplicates"
        
        # Verify individual hash differences make sense
        base_similar_dist = generator.hash_hamming_distance(base_result.ahash, similar_result.ahash)
        base_different_dist = generator.hash_hamming_distance(base_result.ahash, different_result.ahash)
        
        assert base_similar_dist < base_different_dist, \
            f"Similar images should have smaller hash distance ({base_similar_dist}) than different images ({base_different_dist})"


class TestGenerateImageHashesFunction:
    """Test the convenience function generate_image_hashes."""
    
    def test_generate_image_hashes_default(self, sample_images_dir):
        """Test generate_image_hashes with default parameters."""
        image_paths = list(sample_images_dir.glob("*.jpg"))[:2]
        
        results = generate_image_hashes(image_paths)
        
        assert len(results) == len(image_paths)
        assert all(isinstance(r, ImageHashResult) for r in results)
    
    def test_generate_image_hashes_custom_size(self, sample_images_dir):
        """Test generate_image_hashes with custom hash size."""
        image_paths = list(sample_images_dir.glob("*.jpg"))[:1]
        
        results = generate_image_hashes(image_paths, hash_size=16)
        
        assert len(results) == 1
        # With hash_size=16, hashes should be longer than with size=8
        result = results[0]
        if not result.error:
            # 16x16 = 256 bits = 64 hex chars (vs 8x8 = 64 bits = 16 hex chars)
            assert len(result.ahash) > 16