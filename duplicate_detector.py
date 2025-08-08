"""
Duplicate detection module for finding similar images using perceptual hashes.
"""
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from hash_generator import ImageHashResult, HashGenerator
from tqdm import tqdm


@dataclass
class DuplicateGroup:
    """A group of duplicate/similar images."""
    images: List[ImageHashResult]
    representative: ImageHashResult  # Best quality image in the group
    
    def __len__(self):
        return len(self.images)
    
    def total_size(self) -> int:
        """Total file size of all images in group."""
        return sum(img.file_size for img in self.images)


class DuplicateDetector:
    """Detects duplicate images using perceptual hash comparison."""
    
    def __init__(self, similarity_threshold: int = 10, require_agreement: int = 2):
        """
        Initialize duplicate detector.
        
        Args:
            similarity_threshold: Maximum Hamming distance for similarity
            require_agreement: Number of hash algorithms that must agree (1-3)
        """
        self.similarity_threshold = similarity_threshold
        self.require_agreement = require_agreement
        self.hash_generator = HashGenerator()
    
    def find_duplicates(self, hash_results: List[ImageHashResult], 
                       show_progress: bool = True) -> List[DuplicateGroup]:
        """
        Find duplicate groups among image hash results.
        
        Args:
            hash_results: List of image hash results
            show_progress: Whether to show progress bar
            
        Returns:
            List of DuplicateGroup objects, each containing similar images
        """
        # Filter out failed hash results
        valid_results = [r for r in hash_results if not r.error]
        
        if len(valid_results) < 2:
            return []
        
        # Track which images have been assigned to groups
        assigned = set()
        duplicate_groups = []
        
        # Progress bar setup
        total_comparisons = len(valid_results) * (len(valid_results) - 1) // 2
        if show_progress:
            pbar = tqdm(total=total_comparisons, desc="Finding duplicates", unit="comparisons")
        
        # Compare each image with every other image
        for i, result1 in enumerate(valid_results):
            if id(result1) in assigned:
                continue
            
            # Start a new group with this image
            current_group = [result1]
            assigned.add(id(result1))
            
            # Compare with all remaining images
            for j, result2 in enumerate(valid_results[i+1:], i+1):
                if show_progress:
                    pbar.update(1)
                
                if id(result2) in assigned:
                    continue
                
                # Check if images are similar
                if self._are_images_similar(result1, result2):
                    current_group.append(result2)
                    assigned.add(id(result2))
            
            # Only keep groups with multiple images (actual duplicates)
            if len(current_group) > 1:
                # Find the best representative image in the group
                representative = self._select_best_image(current_group)
                duplicate_groups.append(DuplicateGroup(
                    images=current_group,
                    representative=representative
                ))
        
        if show_progress:
            pbar.close()
        
        # Sort groups by size (largest first) for easier review
        duplicate_groups.sort(key=len, reverse=True)
        
        return duplicate_groups
    
    def _are_images_similar(self, result1: ImageHashResult, result2: ImageHashResult) -> bool:
        """Check if two image results represent similar images."""
        return self.hash_generator.get_consensus_similarity(
            result1, result2, 
            threshold=self.similarity_threshold,
            require_agreement=self.require_agreement
        )
    
    def _select_best_image(self, images: List[ImageHashResult]) -> ImageHashResult:
        """
        Select the best quality image from a group of similar images.
        
        Priority order:
        1. File format (PSD > PNG > JPG > others)
        2. Image resolution (width * height)
        3. File size
        
        Args:
            images: List of similar images
            
        Returns:
            The best quality image from the group
        """
        if len(images) == 1:
            return images[0]
        
        # Define format priority (higher number = better)
        format_priority = {
            'PSD': 100,
            'PNG': 90,
            'TIFF': 80,
            'TIF': 80,
            'BMP': 70,
            'WEBP': 60,
            'JPG': 50,
            'JPEG': 50,
            'GIF': 40
        }
        
        def score_image(img: ImageHashResult) -> tuple:
            """Score an image for quality comparison."""
            format_score = format_priority.get(img.format.upper(), 30)
            resolution_score = img.image_width * img.image_height
            size_score = img.file_size
            
            return (format_score, resolution_score, size_score)
        
        # Return the image with the highest score
        return max(images, key=score_image)
    
    def get_statistics(self, duplicate_groups: List[DuplicateGroup]) -> Dict[str, any]:
        """
        Get statistics about detected duplicates.
        
        Args:
            duplicate_groups: List of duplicate groups
            
        Returns:
            Dictionary with statistics
        """
        if not duplicate_groups:
            return {
                'total_groups': 0,
                'total_duplicates': 0,
                'total_size_saved': 0,
                'largest_group_size': 0,
                'average_group_size': 0
            }
        
        total_groups = len(duplicate_groups)
        total_duplicates = sum(len(group) for group in duplicate_groups)
        total_size_saved = sum(
            group.total_size() - group.representative.file_size 
            for group in duplicate_groups
        )
        largest_group_size = max(len(group) for group in duplicate_groups)
        average_group_size = total_duplicates / total_groups if total_groups > 0 else 0
        
        return {
            'total_groups': total_groups,
            'total_duplicates': total_duplicates,
            'total_size_saved': total_size_saved,
            'largest_group_size': largest_group_size,
            'average_group_size': round(average_group_size, 2)
        }
    
    def print_duplicate_report(self, duplicate_groups: List[DuplicateGroup]) -> None:
        """Print a detailed report of found duplicates."""
        stats = self.get_statistics(duplicate_groups)
        
        print(f"\n=== DUPLICATE DETECTION REPORT ===")
        print(f"Found {stats['total_groups']} duplicate groups")
        print(f"Total duplicate images: {stats['total_duplicates']}")
        print(f"Largest group size: {stats['largest_group_size']} images")
        print(f"Average group size: {stats['average_group_size']} images")
        print(f"Potential space saved: {stats['total_size_saved']:,} bytes ({stats['total_size_saved']/1024/1024:.1f} MB)")
        
        if not duplicate_groups:
            print("No duplicates found.")
            return
        
        print(f"\nDuplicate groups (showing first 10):")
        for i, group in enumerate(duplicate_groups[:10], 1):
            print(f"\nGroup {i} ({len(group)} images):")
            print(f"  KEEP: {group.representative.file_path.name} "
                  f"({group.representative.image_width}x{group.representative.image_height}, "
                  f"{group.representative.file_size:,} bytes, {group.representative.format})")
            
            for img in group.images:
                if img != group.representative:
                    print(f"    DELETE: {img.file_path.name} "
                          f"({img.image_width}x{img.image_height}, "
                          f"{img.file_size:,} bytes, {img.format})")


def detect_duplicates(hash_results: List[ImageHashResult], 
                     similarity_threshold: int = 10,
                     require_agreement: int = 2) -> List[DuplicateGroup]:
    """
    Convenience function to detect duplicates from hash results.
    
    Args:
        hash_results: List of image hash results
        similarity_threshold: Maximum Hamming distance for similarity
        require_agreement: Number of hash algorithms that must agree
        
    Returns:
        List of DuplicateGroup objects
    """
    detector = DuplicateDetector(similarity_threshold, require_agreement)
    return detector.find_duplicates(hash_results)


if __name__ == "__main__":
    # Test the duplicate detector
    import sys
    from image_scanner import scan_for_images
    from hash_generator import generate_image_hashes
    
    if len(sys.argv) != 2:
        print("Usage: python duplicate_detector.py <directory_path>")
        sys.exit(1)
    
    directory = sys.argv[1]
    try:
        print("Scanning for images...")
        images = scan_for_images(directory)
        
        if len(images) < 2:
            print("Need at least 2 images to detect duplicates")
            sys.exit(0)
        
        print(f"Generating hashes for {len(images)} images...")
        hash_results = generate_image_hashes(images)
        
        print("Detecting duplicates...")
        detector = DuplicateDetector()
        duplicate_groups = detector.find_duplicates(hash_results)
        
        detector.print_duplicate_report(duplicate_groups)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)