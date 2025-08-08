#!/usr/bin/env python3
"""
Image Deduplication Tool

Scans directories for duplicate images using perceptual hashing and organizes
unique images into a target directory, keeping the highest quality versions.
"""
import sys
from pathlib import Path
import click
from typing import List, Optional


@click.command()
@click.argument('input_directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('output_directory', type=click.Path(file_okay=False, dir_okay=True))
@click.option('--threshold', '-t', default=10, type=int, 
              help='Similarity threshold (0-64, lower = more strict). Default: 10')
@click.option('--agreement', '-a', default=2, type=int,
              help='Number of hash algorithms that must agree (1-3). Default: 2')
@click.option('--extensions', '-e', multiple=True,
              help='Additional file extensions to include (e.g., -e .raw -e .cr2)')
@click.option('--preserve-structure', '-p', is_flag=True,
              help='Preserve directory structure in output')
@click.option('--dry-run', '-n', is_flag=True,
              help='Show what would be done without actually copying files')
@click.option('--report', '-r', type=click.Path(),
              help='Save detailed report to specified file')
@click.option('--quiet', '-q', is_flag=True,
              help='Suppress progress bars and verbose output')
@click.option('--hash-size', default=8, type=int,
              help='Hash size for perceptual hashing (8 or 16). Default: 8')
@click.option('--sample', type=int,
              help='Process only the first N images (for testing/debugging)')
@click.option('--verbose-errors', is_flag=True,
              help='Show all errors in console output (not just first 10)')
@click.help_option("-h", "--help")
def main(input_directory: str, output_directory: str, threshold: int, agreement: int,
         extensions: tuple, preserve_structure: bool, dry_run: bool, 
         report: Optional[str], quiet: bool, hash_size: int, 
         sample: Optional[int], verbose_errors: bool):
    """
    Image Deduplication Tool
    
    Scan INPUT_DIRECTORY for duplicate images and copy unique images to OUTPUT_DIRECTORY.
    Uses perceptual hashing to detect visually similar images and keeps the highest
    quality version from each group of duplicates.
    
    Examples:
    
        # Basic usage
        python dedupe.py /path/to/images /path/to/output
        
        # Dry run to see what would happen
        python dedupe.py /path/to/images /path/to/output --dry-run
        
        # More strict similarity (fewer duplicates detected)
        python dedupe.py /path/to/images /path/to/output --threshold 5
        
        # Preserve directory structure
        python dedupe.py /path/to/images /path/to/output --preserve-structure
        
        # Include additional file types
        python dedupe.py /path/to/images /path/to/output -e .raw -e .cr2
    """
    # Import our modules here to avoid import errors when just showing help
    try:
        from image_scanner import ImageScanner
        from hash_generator import HashGenerator
        from duplicate_detector import DuplicateDetector
        from quality_assessor import QualityAssessor
        from file_organizer import FileOrganizer
    except ImportError as e:
        click.echo(f"Error: Missing dependencies. Please run: pip install -r requirements.txt", err=True)
        click.echo(f"Import error: {e}", err=True)
        sys.exit(1)
    
    try:
        # Validate parameters
        if not (1 <= agreement <= 3):
            click.echo("Error: Agreement must be between 1 and 3", err=True)
            sys.exit(1)
        
        if not (0 <= threshold <= 64):
            click.echo("Error: Threshold must be between 0 and 64", err=True)
            sys.exit(1)
        
        if hash_size not in (8, 16):
            click.echo("Error: Hash size must be 8 or 16", err=True)
            sys.exit(1)
        
        # Initialize components
        scanner = ImageScanner()
        hash_generator = HashGenerator(hash_size=hash_size)
        duplicate_detector = DuplicateDetector(
            similarity_threshold=threshold,
            require_agreement=agreement
        )
        file_organizer = FileOrganizer(
            output_directory=output_directory,
            preserve_structure=preserve_structure,
            dry_run=dry_run
        )
        
        # Add any additional extensions
        if extensions:
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                scanner.add_extension(ext)
        
        # Step 1: Scan for images
        if not quiet:
            click.echo("Scanning for images...")
        
        try:
            image_paths = scanner.scan_directory(input_directory, show_progress=not quiet)
        except Exception as e:
            click.echo(f"Error scanning directory: {e}", err=True)
            sys.exit(1)
        
        if not image_paths:
            click.echo("No images found in input directory.")
            sys.exit(0)
        
        if not quiet:
            click.echo(f"Found {len(image_paths)} images")
        
        # Apply sample limit if specified
        if sample and sample < len(image_paths):
            if not quiet:
                click.echo(f"SAMPLE MODE: Processing first {sample} of {len(image_paths)} images")
            image_paths = image_paths[:sample]
        
        # Step 2: Generate perceptual hashes
        if not quiet:
            click.echo("Generating perceptual hashes...")
        
        try:
            hash_results = hash_generator.generate_hashes(image_paths, show_progress=not quiet)
        except Exception as e:
            click.echo(f"Error generating hashes: {e}", err=True)
            sys.exit(1)
        
        # Report any images that failed to process
        failed_images = [r for r in hash_results if r.error]
        if failed_images and not quiet:
            # Create error log file
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_log_path = f"dedupe_errors_{timestamp}.log"
            
            # Write full error log
            with open(error_log_path, 'w') as f:
                f.write(f"Image Deduplication Error Log\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Errors: {len(failed_images)}\n\n")
                
                for result in failed_images:
                    f.write(f"{result.file_path}: {result.error}\n")
                
                # Error summary
                error_types = {}
                for result in failed_images:
                    error_msg = str(result.error).split(':')[0] if ':' in str(result.error) else str(result.error)
                    error_types[error_msg] = error_types.get(error_msg, 0) + 1
                
                f.write(f"\nERROR SUMMARY:\n")
                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{error_type}: {count} occurrences\n")
            
            # Console output
            click.echo(f"WARNING: Failed to process {len(failed_images)} images:")
            display_count = len(failed_images) if verbose_errors else min(10, len(failed_images))
            
            for i, result in enumerate(failed_images[:display_count]):
                click.echo(f"   {result.file_path.name}: {result.error}")
            
            if len(failed_images) > display_count:
                click.echo(f"   ... and {len(failed_images) - display_count} more")
            
            click.echo(f"Full error details saved to: {error_log_path}")
        
        # Step 3: Detect duplicates
        if not quiet:
            click.echo("Detecting duplicate images...")
        
        try:
            duplicate_groups = duplicate_detector.find_duplicates(hash_results, show_progress=not quiet)
        except Exception as e:
            click.echo(f"Error detecting duplicates: {e}", err=True)
            sys.exit(1)
        
        # Step 4: Show duplicate detection results
        if not quiet:
            duplicate_detector.print_duplicate_report(duplicate_groups)
        
        if not duplicate_groups:
            if not quiet:
                click.echo("No duplicate images found! All images are unique.")
            # Still organize files (just copies everything)
        
        # Step 5: Organize files
        action = "Simulating file organization..." if dry_run else "Organizing files..."
        if not quiet:
            click.echo(action)
        
        try:
            organization_report = file_organizer.organize_images(
                duplicate_groups=duplicate_groups,
                all_images=image_paths,
                show_progress=not quiet
            )
        except Exception as e:
            click.echo(f"Error organizing files: {e}", err=True)
            sys.exit(1)
        
        # Step 6: Show organization results
        if not quiet:
            file_organizer.print_report(organization_report)
        
        # Step 7: Save detailed report if requested
        if report:
            try:
                report_path = file_organizer.save_report(organization_report, Path(report))
                if not quiet:
                    click.echo(f"Detailed report saved to: {report_path}")
            except Exception as e:
                click.echo(f"Warning: Failed to save report: {e}", err=True)
        
        # Step 8: Final summary
        if not quiet:
            click.echo(f"\n{'Simulation' if dry_run else 'Operation'} completed successfully!")
            if dry_run:
                click.echo("Run without --dry-run to actually copy the files.")
        else:
            # Quiet mode: just print essential stats
            click.echo(f"Processed {len(image_paths)} images, "
                      f"found {len(duplicate_groups)} duplicate groups, "
                      f"{'would copy' if dry_run else 'copied'} {organization_report.unique_images_copied} unique images")
    
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if not quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--threshold', '-t', default=10, type=int,
              help='Similarity threshold (0-64). Default: 10')
@click.option('--agreement', '-a', default=2, type=int,
              help='Number of algorithms that must agree (1-3). Default: 2')
@click.help_option("-h", "--help")
def analyze(directory: str, threshold: int, agreement: int):
    """
    Analyze a directory for duplicates without organizing files.
    
    This command only scans and reports duplicates without copying any files.
    Useful for understanding what duplicates exist before running the full deduplication.
    """
    # Import our modules here to avoid import errors when just showing help
    try:
        from image_scanner import ImageScanner
        from hash_generator import HashGenerator
        from duplicate_detector import DuplicateDetector
        from quality_assessor import QualityAssessor
        from file_organizer import FileOrganizer
    except ImportError as e:
        click.echo(f"Error: Missing dependencies. Please run: pip install -r requirements.txt", err=True)
        click.echo(f"Import error: {e}", err=True)
        sys.exit(1)
    
    try:
        # Initialize components
        scanner = ImageScanner()
        hash_generator = HashGenerator()
        duplicate_detector = DuplicateDetector(
            similarity_threshold=threshold,
            require_agreement=agreement
        )
        
        # Scan and analyze
        click.echo("🔍 Scanning for images...")
        image_paths = scanner.scan_directory(directory)
        
        if not image_paths:
            click.echo("No images found.")
            return
        
        click.echo(f"📊 Generating hashes for {len(image_paths)} images...")
        hash_results = hash_generator.generate_hashes(image_paths)
        
        click.echo("🔍 Analyzing for duplicates...")
        duplicate_groups = duplicate_detector.find_duplicates(hash_results)
        
        duplicate_detector.print_duplicate_report(duplicate_groups)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Create a Click group to support multiple commands
@click.group()
@click.version_option(version="1.0.0", prog_name="Image Deduplicator")
@click.help_option("-h", "--help")
def cli():
    """Image Deduplication Tool - Remove duplicate images intelligently."""
    pass


# Add commands to the group
cli.add_command(main, name="dedupe")
cli.add_command(analyze, name="analyze")


if __name__ == "__main__":
    # For backwards compatibility, if called directly with arguments, run main command
    # Handle help flags specially to avoid import issues
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        # Show main help
        sys.argv = [sys.argv[0], '--help']
    elif len(sys.argv) > 1 and not sys.argv[1] in ['dedupe', 'analyze', '--help', '--version', '-h']:
        # Insert 'dedupe' command for backwards compatibility
        sys.argv.insert(1, 'dedupe')
    
    cli()