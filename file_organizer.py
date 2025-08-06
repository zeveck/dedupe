"""
File organization module for copying unique images to output directory.
"""
from pathlib import Path
from typing import List, Dict, Optional, Set
import shutil
from dataclasses import dataclass
from tqdm import tqdm
import json
from datetime import datetime
from duplicate_detector import DuplicateGroup


@dataclass
class CopyResult:
    """Result of copying a file to the output directory."""
    source_path: Path
    destination_path: Path
    success: bool
    error: Optional[str] = None
    bytes_copied: int = 0


@dataclass
class OrganizationReport:
    """Report of the file organization process."""
    total_input_images: int
    unique_images_copied: int
    duplicate_groups_found: int
    total_space_saved: int
    copy_results: List[CopyResult]
    errors: List[str]
    timestamp: str


class FileOrganizer:
    """Organizes and copies unique images to output directory."""
    
    def __init__(self, output_directory: str, preserve_structure: bool = False, 
                 dry_run: bool = False):
        """
        Initialize file organizer.
        
        Args:
            output_directory: Target directory for unique images
            preserve_structure: Whether to maintain directory structure from source
            dry_run: If True, simulate operations without actually copying files
        """
        self.output_dir = Path(output_directory)
        self.preserve_structure = preserve_structure
        self.dry_run = dry_run
        self.copied_names = set()  # Track copied filenames to handle conflicts
    
    def organize_images(self, duplicate_groups: List[DuplicateGroup], 
                       all_images: List[Path],
                       show_progress: bool = True) -> OrganizationReport:
        """
        Organize images by copying unique ones to output directory.
        
        Args:
            duplicate_groups: Groups of duplicate images
            all_images: All discovered images
            show_progress: Whether to show progress bar
            
        Returns:
            OrganizationReport with results of the operation
        """
        # Create output directory if it doesn't exist
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get set of images that are representatives of duplicate groups
        representatives = {group.representative.file_path for group in duplicate_groups}
        
        # Get set of all images in duplicate groups
        duplicate_images = set()
        for group in duplicate_groups:
            duplicate_images.update(img.file_path for img in group.images)
        
        # Images to copy: representatives + images not in any duplicate group
        images_to_copy = []
        for img_path in all_images:
            if img_path in representatives or img_path not in duplicate_images:
                images_to_copy.append(img_path)
        
        # Copy the images
        copy_results = []
        errors = []
        
        iterator = images_to_copy
        if show_progress:
            action = "Simulating copy" if self.dry_run else "Copying"
            iterator = tqdm(images_to_copy, desc=f"{action} unique images", unit="files")
        
        for source_path in iterator:
            try:
                result = self._copy_image(source_path, all_images[0].parent if all_images else None)
                copy_results.append(result)
                if not result.success:
                    errors.append(f"Failed to copy {source_path}: {result.error}")
            except Exception as e:
                error_msg = f"Unexpected error copying {source_path}: {e}"
                errors.append(error_msg)
                copy_results.append(CopyResult(
                    source_path=source_path,
                    destination_path=Path(),
                    success=False,
                    error=str(e)
                ))
        
        # Calculate statistics
        successful_copies = [r for r in copy_results if r.success]
        total_bytes_copied = sum(r.bytes_copied for r in successful_copies)
        
        # Calculate space saved from duplicates
        total_space_saved = sum(
            sum(img.file_size for img in group.images) - group.representative.file_size
            for group in duplicate_groups
        )
        
        return OrganizationReport(
            total_input_images=len(all_images),
            unique_images_copied=len(successful_copies),
            duplicate_groups_found=len(duplicate_groups),
            total_space_saved=total_space_saved,
            copy_results=copy_results,
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    def _copy_image(self, source_path: Path, source_root: Optional[Path] = None) -> CopyResult:
        """
        Copy a single image to the output directory.
        
        Args:
            source_path: Source image file path
            source_root: Root directory of source (for preserving structure)
            
        Returns:
            CopyResult indicating success/failure
        """
        try:
            # Determine destination path
            if self.preserve_structure and source_root:
                # Preserve directory structure
                try:
                    relative_path = source_path.relative_to(source_root)
                    dest_path = self.output_dir / relative_path
                except ValueError:
                    # Fallback if can't make relative path
                    dest_path = self.output_dir / source_path.name
            else:
                # Flat structure
                dest_path = self.output_dir / source_path.name
            
            # Handle filename conflicts
            dest_path = self._resolve_filename_conflict(dest_path)
            
            # Create destination directory if needed
            if not self.dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            bytes_copied = 0
            if self.dry_run:
                # Simulate copy by getting file size
                try:
                    bytes_copied = source_path.stat().st_size
                except:
                    bytes_copied = 0
            else:
                # Actually copy the file
                shutil.copy2(source_path, dest_path)
                bytes_copied = dest_path.stat().st_size
            
            # Track the copied filename
            self.copied_names.add(dest_path.name)
            
            return CopyResult(
                source_path=source_path,
                destination_path=dest_path,
                success=True,
                bytes_copied=bytes_copied
            )
            
        except Exception as e:
            return CopyResult(
                source_path=source_path,
                destination_path=Path(),
                success=False,
                error=str(e)
            )
    
    def _resolve_filename_conflict(self, dest_path: Path) -> Path:
        """
        Resolve filename conflicts by adding incremental numbers.
        
        Args:
            dest_path: Desired destination path
            
        Returns:
            Path that doesn't conflict with existing files
        """
        if dest_path.name not in self.copied_names:
            # Check if file actually exists (for non-dry-run mode)
            if self.dry_run or not dest_path.exists():
                return dest_path
        
        # Generate alternative names with incrementing numbers
        counter = 1
        stem = dest_path.stem
        suffix = dest_path.suffix
        
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = dest_path.parent / new_name
            
            if new_name not in self.copied_names:
                if self.dry_run or not new_path.exists():
                    return new_path
            
            counter += 1
            if counter > 9999:  # Prevent infinite loop
                raise ValueError(f"Too many filename conflicts for {dest_path.name}")
    
    def save_report(self, report: OrganizationReport, report_path: Optional[Path] = None) -> Path:
        """
        Save organization report to JSON file.
        
        Args:
            report: Organization report to save
            report_path: Optional custom path for report file
            
        Returns:
            Path where report was saved
        """
        if not report_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.output_dir / f"dedup_report_{timestamp}.json"
        
        # Convert report to JSON-serializable format
        report_data = {
            'summary': {
                'total_input_images': report.total_input_images,
                'unique_images_copied': report.unique_images_copied,
                'duplicate_groups_found': report.duplicate_groups_found,
                'total_space_saved_bytes': report.total_space_saved,
                'total_space_saved_mb': round(report.total_space_saved / 1024 / 1024, 2),
                'timestamp': report.timestamp
            },
            'copy_results': [
                {
                    'source_path': str(result.source_path),
                    'destination_path': str(result.destination_path),
                    'success': result.success,
                    'error': result.error,
                    'bytes_copied': result.bytes_copied
                }
                for result in report.copy_results
            ],
            'errors': report.errors
        }
        
        if not self.dry_run:
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)
        
        return report_path
    
    def print_report(self, report: OrganizationReport) -> None:
        """Print a human-readable organization report."""
        print(f"\n=== FILE ORGANIZATION REPORT ===")
        print(f"Operation: {'DRY RUN' if self.dry_run else 'ACTUAL COPY'}")
        print(f"Input images processed: {report.total_input_images}")
        print(f"Unique images copied: {report.unique_images_copied}")
        print(f"Duplicate groups found: {report.duplicate_groups_found}")
        print(f"Space saved by deduplication: {report.total_space_saved:,} bytes ({report.total_space_saved/1024/1024:.1f} MB)")
        
        successful_copies = [r for r in report.copy_results if r.success]
        if successful_copies:
            total_copied = sum(r.bytes_copied for r in successful_copies)
            print(f"Total data copied: {total_copied:,} bytes ({total_copied/1024/1024:.1f} MB)")
        
        if report.errors:
            print(f"\nErrors encountered ({len(report.errors)}):")
            for error in report.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(report.errors) > 10:
                print(f"  ... and {len(report.errors) - 10} more errors")
        else:
            print("No errors encountered.")
        
        print(f"Timestamp: {report.timestamp}")


def organize_images(duplicate_groups: List[DuplicateGroup], all_images: List[Path],
                   output_directory: str, preserve_structure: bool = False,
                   dry_run: bool = False) -> OrganizationReport:
    """
    Convenience function to organize images.
    
    Args:
        duplicate_groups: Groups of duplicate images
        all_images: All discovered images
        output_directory: Target directory for unique images
        preserve_structure: Whether to maintain directory structure
        dry_run: If True, simulate operations without copying
        
    Returns:
        OrganizationReport with results
    """
    organizer = FileOrganizer(output_directory, preserve_structure, dry_run)
    return organizer.organize_images(duplicate_groups, all_images)


if __name__ == "__main__":
    # Test the file organizer
    import sys
    from image_scanner import scan_for_images
    from hash_generator import generate_image_hashes
    from duplicate_detector import detect_duplicates
    
    if len(sys.argv) != 3:
        print("Usage: python file_organizer.py <input_directory> <output_directory>")
        sys.exit(1)
    
    input_dir, output_dir = sys.argv[1], sys.argv[2]
    
    try:
        print("Scanning for images...")
        images = scan_for_images(input_dir)
        
        if not images:
            print("No images found")
            sys.exit(0)
        
        print(f"Generating hashes for {len(images)} images...")
        hash_results = generate_image_hashes(images)
        
        print("Detecting duplicates...")
        duplicate_groups = detect_duplicates(hash_results)
        
        print("Organizing files (DRY RUN)...")
        organizer = FileOrganizer(output_dir, dry_run=True)
        report = organizer.organize_images(duplicate_groups, images)
        organizer.print_report(report)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)