"""
Quality assessment module for evaluating and comparing image quality.
"""
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import math
from hash_generator import ImageHashResult
from PIL import Image
import numpy as np


@dataclass
class QualityScore:
    """Quality assessment result for an image."""
    file_path: Path
    overall_score: float
    format_score: float
    resolution_score: float
    size_score: float
    sharpness_score: float
    has_watermark: bool
    watermark_confidence: float


class QualityAssessor:
    """Assesses image quality using multiple criteria."""
    
    def __init__(self):
        """Initialize quality assessor with default weights."""
        self.format_weights = {
            'PSD': 100,    # Highest - uncompressed, editable
            'PNG': 90,     # High - lossless compression
            'TIFF': 85,    # High - lossless, professional
            'TIF': 85,     # Same as TIFF
            'BMP': 80,     # Uncompressed but inefficient
            'WEBP': 70,    # Good compression, modern
            'JPG': 60,     # Lossy compression
            'JPEG': 60,    # Same as JPG
            'GIF': 40,     # Limited colors, old format
        }
        
        # Weights for combining different quality aspects
        self.score_weights = {
            'format': 0.30,      # 30% - file format quality
            'resolution': 0.25,   # 25% - image dimensions
            'size': 0.20,        # 20% - file size (larger often better for same format)
            'sharpness': 0.20,   # 20% - image sharpness
            'watermark': 0.05,   # 5% - watermark penalty
        }
    
    def assess_image_quality(self, hash_result: ImageHashResult) -> QualityScore:
        """
        Assess the quality of a single image.
        
        Args:
            hash_result: Image hash result with metadata
            
        Returns:
            QualityScore object with detailed assessment
        """
        if hash_result.error:
            return QualityScore(
                file_path=hash_result.file_path,
                overall_score=0.0,
                format_score=0.0,
                resolution_score=0.0,
                size_score=0.0,
                sharpness_score=0.0,
                has_watermark=False,
                watermark_confidence=0.0
            )
        
        # Calculate individual quality scores
        format_score = self._assess_format_quality(hash_result.format)
        resolution_score = self._assess_resolution_quality(hash_result.image_width, hash_result.image_height)
        size_score = self._assess_size_quality(hash_result.file_size, hash_result.format)
        
        # Advanced assessments requiring image loading
        try:
            with Image.open(hash_result.file_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                sharpness_score = self._assess_sharpness(img)
                has_watermark, watermark_confidence = self._detect_watermark(img)
        except:
            sharpness_score = 50.0  # Neutral score if can't analyze
            has_watermark = False
            watermark_confidence = 0.0
        
        # Apply watermark penalty
        watermark_penalty = watermark_confidence if has_watermark else 0.0
        
        # Calculate overall weighted score
        overall_score = (
            format_score * self.score_weights['format'] +
            resolution_score * self.score_weights['resolution'] +
            size_score * self.score_weights['size'] +
            sharpness_score * self.score_weights['sharpness'] -
            watermark_penalty * self.score_weights['watermark'] * 100  # Convert to penalty
        )
        
        return QualityScore(
            file_path=hash_result.file_path,
            overall_score=max(0.0, overall_score),  # Ensure non-negative
            format_score=format_score,
            resolution_score=resolution_score,
            size_score=size_score,
            sharpness_score=sharpness_score,
            has_watermark=has_watermark,
            watermark_confidence=watermark_confidence
        )
    
    def compare_images(self, images: List[ImageHashResult]) -> ImageHashResult:
        """
        Compare multiple images and return the highest quality one.
        
        Args:
            images: List of similar images to compare
            
        Returns:
            The highest quality image from the list
        """
        if len(images) == 1:
            return images[0]
        
        scores = [self.assess_image_quality(img) for img in images]
        best_score = max(scores, key=lambda s: s.overall_score)
        
        # Find the corresponding ImageHashResult
        for img in images:
            if img.file_path == best_score.file_path:
                return img
        
        # Fallback to first image if something went wrong
        return images[0]
    
    def _assess_format_quality(self, format_name: str) -> float:
        """Assess quality based on image format."""
        return self.format_weights.get(format_name.upper(), 30)  # Default for unknown formats
    
    def _assess_resolution_quality(self, width: int, height: int) -> float:
        """
        Assess quality based on image resolution.
        
        Higher resolution generally means better quality.
        Uses logarithmic scale to prevent extremely large images from dominating.
        """
        if width <= 0 or height <= 0:
            return 0.0
        
        total_pixels = width * height
        
        # Logarithmic scale: log10(pixels) normalized to 0-100
        # 1MP = ~6 points, 4MP = ~12 points, 16MP = ~24 points, etc.
        if total_pixels <= 1:
            return 0.0
        
        log_pixels = math.log10(total_pixels)
        # Normalize: assume 100MP (log10(100M) ≈ 8) as maximum for scoring
        normalized_score = (log_pixels / 8.0) * 100
        return min(100.0, normalized_score)
    
    def _assess_size_quality(self, file_size: int, format_name: str) -> float:
        """
        Assess quality based on file size relative to format.
        
        Larger files often indicate less compression/higher quality,
        but this varies significantly by format.
        """
        if file_size <= 0:
            return 0.0
        
        # Different formats have different size expectations
        format_multipliers = {
            'PSD': 1.0,    # PSD files are naturally large
            'PNG': 1.2,    # PNG can be large due to lossless compression
            'TIFF': 1.0,   # Similar to PSD
            'TIF': 1.0,
            'BMP': 0.8,    # BMP is large but not necessarily high quality
            'WEBP': 1.5,   # WebP is efficient, smaller files can be high quality
            'JPG': 2.0,    # JPG compression means size matters more
            'JPEG': 2.0,
            'GIF': 1.0,    # GIF has limited colors anyway
        }
        
        multiplier = format_multipliers.get(format_name.upper(), 1.0)
        
        # Logarithmic scale for file size (in bytes)
        # 100KB = ~10 points, 1MB = ~20 points, 10MB = ~30 points
        log_size = math.log10(max(1, file_size))
        normalized_score = (log_size / 8.0) * 100 * multiplier  # Assume 100MB as max
        return min(100.0, normalized_score)
    
    def _assess_sharpness(self, img: Image.Image) -> float:
        """
        Assess image sharpness using Laplacian variance.
        
        Higher variance indicates more edges/details, suggesting sharper image.
        """
        try:
            # Convert to grayscale for sharpness analysis
            gray_img = img.convert('L')
            
            # Resize if image is very large to speed up processing
            if max(gray_img.size) > 1000:
                ratio = 1000 / max(gray_img.size)
                new_size = (int(gray_img.width * ratio), int(gray_img.height * ratio))
                gray_img = gray_img.resize(new_size, Image.LANCZOS)
            
            # Convert to numpy array
            img_array = np.array(gray_img)
            
            # Apply Laplacian filter to detect edges
            # Simple approximation of Laplacian: center - average of neighbors
            laplacian = np.zeros_like(img_array, dtype=np.float64)
            laplacian[1:-1, 1:-1] = (
                4 * img_array[1:-1, 1:-1] - 
                img_array[0:-2, 1:-1] - img_array[2:, 1:-1] - 
                img_array[1:-1, 0:-2] - img_array[1:-1, 2:]
            )
            
            # Calculate variance of Laplacian
            variance = np.var(laplacian)
            
            # Normalize to 0-100 scale
            # Based on empirical testing, variance around 1000 is quite sharp
            normalized_score = min(100.0, (variance / 1000.0) * 100)
            return normalized_score
            
        except Exception:
            return 50.0  # Neutral score if analysis fails
    
    def _detect_watermark(self, img: Image.Image) -> tuple[bool, float]:
        """
        Simple watermark detection in image corners.
        
        Looks for patterns that might indicate watermarks or signatures.
        This is a basic implementation - more sophisticated detection would
        use machine learning or template matching.
        
        Returns:
            Tuple of (has_watermark, confidence)
        """
        try:
            # Convert to grayscale for analysis
            gray_img = img.convert('L')
            width, height = gray_img.size
            
            # Define corner regions (10% of image size in each corner)
            corner_size_x = int(width * 0.1)
            corner_size_y = int(height * 0.1)
            
            if corner_size_x < 10 or corner_size_y < 10:
                return False, 0.0  # Image too small to analyze
            
            # Extract corner regions
            corners = [
                gray_img.crop((0, 0, corner_size_x, corner_size_y)),                    # Top-left
                gray_img.crop((width-corner_size_x, 0, width, corner_size_y)),          # Top-right
                gray_img.crop((0, height-corner_size_y, corner_size_x, height)),        # Bottom-left
                gray_img.crop((width-corner_size_x, height-corner_size_y, width, height)) # Bottom-right
            ]
            
            watermark_indicators = 0
            total_corners = len(corners)
            
            for corner in corners:
                corner_array = np.array(corner)
                
                # Look for signs of watermarks:
                # 1. High contrast text/logos (high edge density)
                # 2. Consistent patterns (low variance might indicate overlay)
                
                # Calculate edge density using simple gradient
                if corner_array.shape[0] > 1 and corner_array.shape[1] > 1:
                    grad_x = np.abs(np.diff(corner_array, axis=1))
                    grad_y = np.abs(np.diff(corner_array, axis=0))
                    edge_density = (np.mean(grad_x) + np.mean(grad_y)) / 2
                    
                    # High edge density might indicate text/logos
                    if edge_density > 15:  # Threshold based on empirical testing
                        watermark_indicators += 1
            
            # Calculate confidence based on how many corners show watermark signs
            confidence = watermark_indicators / total_corners
            has_watermark = confidence > 0.25  # At least one corner shows signs
            
            return has_watermark, confidence
            
        except Exception:
            return False, 0.0  # Return no watermark if analysis fails


def assess_image_quality(hash_result: ImageHashResult) -> QualityScore:
    """
    Convenience function to assess single image quality.
    
    Args:
        hash_result: Image hash result with metadata
        
    Returns:
        QualityScore object
    """
    assessor = QualityAssessor()
    return assessor.assess_image_quality(hash_result)


if __name__ == "__main__":
    # Test the quality assessor
    import sys
    from image_scanner import scan_for_images
    from hash_generator import generate_image_hashes
    
    if len(sys.argv) != 2:
        print("Usage: python quality_assessor.py <directory_path>")
        sys.exit(1)
    
    directory = sys.argv[1]
    try:
        print("Scanning for images...")
        images = scan_for_images(directory)
        
        if not images:
            print("No images found")
            sys.exit(0)
        
        print(f"Generating hashes for {len(images[:5])} test images...")
        hash_results = generate_image_hashes(images[:5])  # Test first 5
        
        print("Assessing image quality...")
        assessor = QualityAssessor()
        
        for hash_result in hash_results:
            if not hash_result.error:
                quality = assessor.assess_image_quality(hash_result)
                print(f"\n{quality.file_path.name}:")
                print(f"  Overall Score: {quality.overall_score:.1f}")
                print(f"  Format: {quality.format_score:.1f}")
                print(f"  Resolution: {quality.resolution_score:.1f}")
                print(f"  Size: {quality.size_score:.1f}")
                print(f"  Sharpness: {quality.sharpness_score:.1f}")
                print(f"  Watermark: {quality.has_watermark} (confidence: {quality.watermark_confidence:.2f})")
            else:
                print(f"\nERROR - {hash_result.file_path.name}: {hash_result.error}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)