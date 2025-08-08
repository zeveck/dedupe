"""
Perceptual hash generation module for creating image fingerprints.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import imagehash
from PIL import Image
from dataclasses import dataclass
from tqdm import tqdm
import os


@dataclass
class ImageHashResult:
    """Result of hashing an image with metadata."""
    file_path: Path
    ahash: str
    dhash: str
    phash: str
    file_size: int
    image_width: int
    image_height: int
    format: str
    error: Optional[str] = None


class HashGenerator:
    """Generates perceptual hashes for images using multiple algorithms."""
    
    def __init__(self, hash_size: int = 8):
        """
        Initialize hash generator.
        
        Args:
            hash_size: Size of the hash (8 = 64-bit hash, 16 = 256-bit hash)
        """
        self.hash_size = hash_size
    
    def generate_hashes(self, image_paths: List[Path], show_progress: bool = True) -> List[ImageHashResult]:
        """
        Generate perceptual hashes for a list of image files.
        
        Args:
            image_paths: List of image file paths
            show_progress: Whether to show progress bar
            
        Returns:
            List of ImageHashResult objects
        """
        results = []
        
        iterator = image_paths
        if show_progress:
            iterator = tqdm(image_paths, desc="Generating hashes", unit="images")
        
        for image_path in iterator:
            result = self.generate_hash(image_path)
            results.append(result)
        
        return results
    
    def generate_hash(self, image_path: Path) -> ImageHashResult:
        """
        Generate perceptual hashes for a single image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            ImageHashResult with hashes and metadata
        """
        try:
            # Get file size
            file_size = os.path.getsize(image_path)
            
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Generate three types of perceptual hashes
                ahash = str(imagehash.average_hash(img, hash_size=self.hash_size))
                dhash = str(imagehash.dhash(img, hash_size=self.hash_size))
                phash = str(imagehash.phash(img, hash_size=self.hash_size))
                
                # Get image dimensions and format
                width, height = img.size
                image_format = img.format or image_path.suffix.upper()[1:]
                
                return ImageHashResult(
                    file_path=image_path,
                    ahash=ahash,
                    dhash=dhash,
                    phash=phash,
                    file_size=file_size,
                    image_width=width,
                    image_height=height,
                    format=image_format
                )
                
        except Exception as e:
            # Return result with error for failed images
            return ImageHashResult(
                file_path=image_path,
                ahash="",
                dhash="",
                phash="",
                file_size=0,
                image_width=0,
                image_height=0,
                format="",
                error=str(e)
            )
    
    def hash_hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hash strings.
        
        Args:
            hash1: First hash string
            hash2: Second hash string
            
        Returns:
            Hamming distance (number of differing bits)
        """
        if len(hash1) != len(hash2):
            raise ValueError("Hash strings must be the same length")
        
        # Convert hex strings to integers and XOR them
        try:
            h1_int = int(hash1, 16)
            h2_int = int(hash2, 16)
            xor_result = h1_int ^ h2_int
            
            # Count set bits (Hamming distance)
            return bin(xor_result).count('1')
        except ValueError:
            # Fallback to character comparison if hex conversion fails
            return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    
    def are_similar(self, hash1: str, hash2: str, threshold: int = 10) -> bool:
        """
        Check if two hashes represent similar images.
        
        Args:
            hash1: First hash string
            hash2: Second hash string
            threshold: Maximum Hamming distance for similarity
            
        Returns:
            True if images are considered similar
        """
        if not hash1 or not hash2:
            return False
        
        distance = self.hash_hamming_distance(hash1, hash2)
        return distance <= threshold
    
    def get_consensus_similarity(self, result1: ImageHashResult, result2: ImageHashResult, 
                                threshold: int = 10, require_agreement: int = 2) -> bool:
        """
        Check similarity using multiple hash algorithms for better accuracy.
        
        Args:
            result1: First image hash result
            result2: Second image hash result
            threshold: Maximum Hamming distance for similarity
            require_agreement: Number of algorithms that must agree (1-3)
            
        Returns:
            True if enough algorithms agree the images are similar
        """
        if result1.error or result2.error:
            return False
        
        agreements = 0
        
        # Check each hash type
        if self.are_similar(result1.ahash, result2.ahash, threshold):
            agreements += 1
        if self.are_similar(result1.dhash, result2.dhash, threshold):
            agreements += 1
        if self.are_similar(result1.phash, result2.phash, threshold):
            agreements += 1
        
        return agreements >= require_agreement


def generate_image_hashes(image_paths: List[Path], hash_size: int = 8) -> List[ImageHashResult]:
    """
    Convenience function to generate hashes for image files.
    
    Args:
        image_paths: List of image file paths
        hash_size: Size of hash to generate
        
    Returns:
        List of ImageHashResult objects
    """
    generator = HashGenerator(hash_size)
    return generator.generate_hashes(image_paths)


if __name__ == "__main__":
    # Test the hash generator
    import sys
    from image_scanner import scan_for_images
    
    if len(sys.argv) != 2:
        print("Usage: python hash_generator.py <directory_path>")
        sys.exit(1)
    
    directory = sys.argv[1]
    try:
        # Scan for images
        images = scan_for_images(directory)
        if not images:
            print("No images found")
            sys.exit(0)
        
        # Generate hashes for first few images
        test_images = images[:5]  # Test with first 5 images
        print(f"\nGenerating hashes for {len(test_images)} test images...")
        
        generator = HashGenerator()
        results = generator.generate_hashes(test_images)
        
        print("\nResults:")
        for result in results:
            if result.error:
                print(f"ERROR - {result.file_path.name}: {result.error}")
            else:
                print(f"{result.file_path.name}:")
                print(f"  Size: {result.file_size} bytes, {result.image_width}x{result.image_height}")
                print(f"  aHash: {result.ahash}")
                print(f"  dHash: {result.dhash}")
                print(f"  pHash: {result.phash}")
                print()
        
        # Test similarity if we have multiple images
        if len(results) >= 2 and not results[0].error and not results[1].error:
            r1, r2 = results[0], results[1]
            similar = generator.get_consensus_similarity(r1, r2)
            print(f"Similarity test between {r1.file_path.name} and {r2.file_path.name}: {similar}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)