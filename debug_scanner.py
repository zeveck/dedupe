#!/usr/bin/env python3
"""
Debug scanner to investigate high image count.
"""
import sys
from pathlib import Path
from collections import Counter
from image_scanner import ImageScanner

def debug_scan(directory_path: str, max_depth: int = 3, sample_size: int = 20):
    """
    Debug scan that shows what files are being detected and where.
    """
    directory = Path(directory_path)
    if not directory.exists():
        print(f"Directory not found: {directory_path}")
        return
    
    scanner = ImageScanner()
    
    # Count files by extension
    extension_counts = Counter()
    directory_counts = Counter()
    sample_files = []
    
    print(f"Scanning: {directory_path}")
    print(f"Supported extensions: {sorted(scanner.supported_extensions)}")
    print()
    
    # Manual scan to debug
    total_files_checked = 0
    image_files_found = 0
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            total_files_checked += 1
            extension = file_path.suffix.lower()
            
            if scanner._is_image_file(file_path):
                image_files_found += 1
                extension_counts[extension] += 1
                
                # Track which directories have the most images
                relative_path = file_path.relative_to(directory)
                if len(relative_path.parts) > 0:
                    top_dir = relative_path.parts[0]
                    directory_counts[top_dir] += 1
                
                # Keep sample files
                if len(sample_files) < sample_size:
                    sample_files.append(file_path)
        
        # Show progress every 10,000 files
        if total_files_checked % 10000 == 0:
            print(f"Checked {total_files_checked} files, found {image_files_found} images so far...")
    
    # Results
    print(f"\nScan Results:")
    print(f"Total files checked: {total_files_checked:,}")
    print(f"Image files found: {image_files_found:,}")
    print(f"Percentage: {image_files_found/total_files_checked*100:.1f}%")
    
    print(f"\nTop 10 Image Extensions:")
    for ext, count in extension_counts.most_common(10):
        print(f"  {ext}: {count:,}")
    
    print(f"\nTop 10 Directories with Most Images:")
    for dir_name, count in directory_counts.most_common(10):
        print(f"  {dir_name}: {count:,}")
    
    print(f"\nSample Files (first {len(sample_files)}):")
    for i, file_path in enumerate(sample_files):
        rel_path = file_path.relative_to(directory)
        print(f"  {i+1:2d}. {rel_path}")
        if i >= 9:  # Show first 10
            break
    
    # Check for suspiciously common patterns
    print(f"\nSuspicious Patterns Check:")
    if extension_counts.get('.jpg', 0) > 40000:
        print("  WARNING: Very high .jpg count - check for thumbnails/cache directories")
    if extension_counts.get('.png', 0) > 10000:
        print("  WARNING: Very high .png count - check for app icons/thumbnails")
    if any(count > 5000 for count in directory_counts.values()):
        print("  WARNING: Some directories have >5000 images - possible cache/thumbnail dirs")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_scanner.py <directory_path>")
        print("This will analyze what files are being counted as images.")
        sys.exit(1)
    
    debug_scan(sys.argv[1])