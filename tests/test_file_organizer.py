"""
Unit tests for file_organizer.py
"""
import pytest
import json
from pathlib import Path
from PIL import Image
from file_organizer import (
    FileOrganizer, CopyResult, OrganizationReport, organize_images
)
from duplicate_detector import DuplicateGroup
from hash_generator import ImageHashResult, HashGenerator


class TestFileOrganizer:
    """Test cases for FileOrganizer class."""
    
    def test_init_default_parameters(self, output_dir):
        """Test FileOrganizer initialization with default parameters."""
        organizer = FileOrganizer(str(output_dir))
        
        assert organizer.output_dir == output_dir
        assert organizer.preserve_structure is False
        assert organizer.dry_run is False
        assert len(organizer.copied_names) == 0
    
    def test_init_custom_parameters(self, output_dir):
        """Test FileOrganizer initialization with custom parameters."""
        organizer = FileOrganizer(
            str(output_dir), 
            preserve_structure=True, 
            dry_run=True
        )
        
        assert organizer.preserve_structure is True
        assert organizer.dry_run is True
    
    def test_resolve_filename_conflict_no_conflict(self, output_dir):
        """Test filename resolution when no conflict exists."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        test_path = output_dir / "test.jpg"
        resolved = organizer._resolve_filename_conflict(test_path)
        
        assert resolved == test_path
    
    def test_resolve_filename_conflict_with_tracking(self, output_dir):
        """Test filename resolution with name tracking."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        # Simulate that "test.jpg" is already copied
        organizer.copied_names.add("test.jpg")
        
        test_path = output_dir / "test.jpg"
        resolved = organizer._resolve_filename_conflict(test_path)
        
        # Should get incremented name
        assert resolved.name == "test_1.jpg"
        assert resolved.parent == output_dir
    
    def test_resolve_filename_conflict_multiple(self, output_dir):
        """Test filename resolution with multiple conflicts."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        # Simulate multiple names already taken
        organizer.copied_names.update(["test.jpg", "test_1.jpg", "test_2.jpg"])
        
        test_path = output_dir / "test.jpg"
        resolved = organizer._resolve_filename_conflict(test_path)
        
        # Should get next available increment
        assert resolved.name == "test_3.jpg"
    
    def test_copy_image_dry_run(self, sample_images_dir, output_dir):
        """Test copying image in dry-run mode."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        source_image = next(sample_images_dir.glob("*.jpg"))
        result = organizer._copy_image(source_image, sample_images_dir)
        
        assert isinstance(result, CopyResult)
        assert result.source_path == source_image
        assert result.success is True
        assert result.error is None
        assert result.bytes_copied > 0  # Should get file size even in dry run
        assert result.destination_path.parent == output_dir
    
    def test_copy_image_actual_copy(self, sample_images_dir, output_dir):
        """Test actually copying an image file."""
        organizer = FileOrganizer(str(output_dir), dry_run=False)
        
        source_image = next(sample_images_dir.glob("*.jpg"))
        result = organizer._copy_image(source_image, sample_images_dir)
        
        assert result.success is True
        assert result.error is None
        assert result.destination_path.exists()
        assert result.bytes_copied > 0
        
        # Verify file was actually copied
        assert result.destination_path.is_file()
        assert result.destination_path.stat().st_size > 0
    
    def test_copy_image_preserve_structure(self, sample_images_dir, output_dir):
        """Test copying with preserved directory structure."""
        organizer = FileOrganizer(str(output_dir), preserve_structure=True, dry_run=True)
        
        # Get image from subdirectory
        subdir_images = list(sample_images_dir.rglob("subdir/*.png"))
        if subdir_images:
            source_image = subdir_images[0]
            result = organizer._copy_image(source_image, sample_images_dir)
            
            assert result.success is True
            # Should preserve "subdir" in path
            assert "subdir" in str(result.destination_path)
    
    def test_copy_image_flatten_structure(self, sample_images_dir, output_dir):
        """Test copying with flattened directory structure."""
        organizer = FileOrganizer(str(output_dir), preserve_structure=False, dry_run=True)
        
        # Get image from subdirectory
        subdir_images = list(sample_images_dir.rglob("subdir/*.png"))
        if subdir_images:
            source_image = subdir_images[0]
            result = organizer._copy_image(source_image, sample_images_dir)
            
            assert result.success is True
            # Should be directly in output dir
            assert result.destination_path.parent == output_dir
    
    def test_organize_images_no_duplicates(self, sample_images_dir, output_dir):
        """Test organizing images when no duplicates are found."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        # Get all images
        all_images = list(sample_images_dir.rglob("*.jpg")) + list(sample_images_dir.rglob("*.png"))
        
        # No duplicate groups
        duplicate_groups = []
        
        report = organizer.organize_images(
            duplicate_groups=duplicate_groups,
            all_images=all_images,
            show_progress=False
        )
        
        assert isinstance(report, OrganizationReport)
        assert report.total_input_images == len(all_images)
        assert report.unique_images_copied == len(all_images)  # All should be copied
        assert report.duplicate_groups_found == 0
        assert len(report.copy_results) == len(all_images)
    
    def test_organize_images_with_duplicates(self, temp_dir, output_dir):
        """Test organizing images with duplicate groups."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        generator = HashGenerator()
        
        # Create test images
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Create three copies of same image
        image_paths = []
        for i in range(3):
            path = temp_dir / f"red_{i}.jpg"
            img.save(path, "JPEG")
            image_paths.append(path)
        
        # Generate hash results
        hash_results = [generator.generate_hash(p) for p in image_paths]
        
        # Create a duplicate group (all three are "duplicates")
        representative = max(hash_results, key=lambda x: x.file_size)
        duplicate_group = DuplicateGroup(images=hash_results, representative=representative)
        
        # Organize images
        report = organizer.organize_images(
            duplicate_groups=[duplicate_group],
            all_images=image_paths,
            show_progress=False
        )
        
        assert report.total_input_images == 3
        assert report.unique_images_copied == 1  # Only representative should be copied
        assert report.duplicate_groups_found == 1
        assert report.total_space_saved > 0  # Should save space by not copying duplicates
    
    def test_organize_images_mixed_scenario(self, temp_dir, output_dir):
        """Test organizing with both unique and duplicate images."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        generator = HashGenerator()
        
        from PIL import Image
        
        # Create two unique images
        red_img = Image.new('RGB', (100, 100), color='red')
        blue_img = Image.new('RGB', (100, 100), color='blue')
        
        unique1_path = temp_dir / "unique1.jpg"
        unique2_path = temp_dir / "unique2.jpg"
        red_img.save(unique1_path, "JPEG")
        blue_img.save(unique2_path, "JPEG")
        
        # Create two copies of red image (duplicates)
        dup1_path = temp_dir / "dup1.jpg"
        dup2_path = temp_dir / "dup2.png"
        red_img.save(dup1_path, "JPEG", quality=90)
        red_img.save(dup2_path, "PNG")
        
        all_paths = [unique1_path, unique2_path, dup1_path, dup2_path]
        
        # Generate hash results
        hash_results = [generator.generate_hash(p) for p in all_paths]
        
        # Create duplicate group for the red image copies
        red_results = [r for r in hash_results if 'unique1' in str(r.file_path) or 'dup' in str(r.file_path)]
        if len(red_results) >= 2:  # If detected as duplicates
            representative = max(red_results, key=lambda x: x.file_size)
            duplicate_group = DuplicateGroup(images=red_results, representative=representative)
            duplicate_groups = [duplicate_group]
        else:
            duplicate_groups = []
        
        report = organizer.organize_images(
            duplicate_groups=duplicate_groups,
            all_images=all_paths,
            show_progress=False
        )
        
        assert report.total_input_images == 4
        # Should copy unique blue + representative of red group + any non-grouped images
        assert report.unique_images_copied >= 2
    
    def test_save_report_dry_run(self, output_dir):
        """Test saving report in dry-run mode."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        # Create minimal report
        report = OrganizationReport(
            total_input_images=5,
            unique_images_copied=3,
            duplicate_groups_found=1,
            total_space_saved=1024,
            copy_results=[],
            errors=[],
            timestamp="2024-01-01T00:00:00"
        )
        
        report_path = organizer.save_report(report)
        
        # In dry-run mode, file shouldn't actually be created
        assert not report_path.exists()
        assert report_path.parent == output_dir
        assert report_path.suffix == ".json"
    
    def test_save_report_actual(self, output_dir):
        """Test actually saving a report file."""
        organizer = FileOrganizer(str(output_dir), dry_run=False)
        
        # Create minimal report
        report = OrganizationReport(
            total_input_images=5,
            unique_images_copied=3,
            duplicate_groups_found=1,
            total_space_saved=1024,
            copy_results=[],
            errors=["Test error"],
            timestamp="2024-01-01T00:00:00"
        )
        
        report_path = organizer.save_report(report)
        
        # File should be created
        assert report_path.exists()
        assert report_path.is_file()
        
        # Verify JSON content
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        assert data['summary']['total_input_images'] == 5
        assert data['summary']['unique_images_copied'] == 3
        assert data['summary']['total_space_saved_mb'] == round(1024 / 1024 / 1024, 2)
        assert len(data['errors']) == 1
        assert data['errors'][0] == "Test error"
    
    def test_print_report(self, capsys, output_dir):
        """Test printing report to stdout."""
        organizer = FileOrganizer(str(output_dir), dry_run=True)
        
        # Create test report
        report = OrganizationReport(
            total_input_images=10,
            unique_images_copied=7,
            duplicate_groups_found=2,
            total_space_saved=2048,
            copy_results=[],
            errors=["Test error 1", "Test error 2"],
            timestamp="2024-01-01T00:00:00"
        )
        
        organizer.print_report(report)
        captured = capsys.readouterr()
        
        assert "FILE ORGANIZATION REPORT" in captured.out
        assert "DRY RUN" in captured.out
        assert "10" in captured.out  # total input images
        assert "7" in captured.out   # unique images copied
        assert "2" in captured.out   # duplicate groups
        assert "Test error 1" in captured.out


class TestCopyResult:
    """Test cases for CopyResult dataclass."""
    
    def test_copy_result_creation(self, temp_dir):
        """Test CopyResult object creation."""
        source = temp_dir / "source.jpg"
        dest = temp_dir / "dest.jpg"
        
        result = CopyResult(
            source_path=source,
            destination_path=dest,
            success=True,
            bytes_copied=1024
        )
        
        assert result.source_path == source
        assert result.destination_path == dest
        assert result.success is True
        assert result.error is None
        assert result.bytes_copied == 1024


class TestOrganizationReport:
    """Test cases for OrganizationReport dataclass."""
    
    def test_organization_report_creation(self):
        """Test OrganizationReport object creation."""
        report = OrganizationReport(
            total_input_images=100,
            unique_images_copied=75,
            duplicate_groups_found=10,
            total_space_saved=5000,
            copy_results=[],
            errors=["Error 1"],
            timestamp="2024-01-01T00:00:00"
        )
        
        assert report.total_input_images == 100
        assert report.unique_images_copied == 75
        assert report.duplicate_groups_found == 10
        assert report.total_space_saved == 5000
        assert len(report.errors) == 1
        assert report.errors[0] == "Error 1"


    def test_copy_image_error_handling(self, temp_dir, output_dir):
        """Test error handling during file copy operations."""
        organizer = FileOrganizer(str(output_dir), dry_run=False)
        
        # Test copying non-existent file
        nonexistent_path = temp_dir / "does_not_exist.jpg"
        result = organizer._copy_image(nonexistent_path, temp_dir)
        
        assert not result.success
        assert result.error is not None
        assert result.bytes_copied == 0
        
    def test_copy_image_invalid_relative_path(self, temp_dir, output_dir):
        """Test handling when relative path calculation fails."""
        organizer = FileOrganizer(str(output_dir), preserve_structure=True, dry_run=True)
        
        # Create test file that will definitely cause ValueError in relative_to()
        # Use a path that has no common root with temp_dir
        import tempfile
        with tempfile.TemporaryDirectory() as external_root:
            external_path = Path(external_root)
            
            from PIL import Image
            img = Image.new('RGB', (50, 50), color='blue')
            external_file = external_path / "external.jpg"
            img.save(external_file, "JPEG")
            
            # This should trigger the ValueError exception path in relative_to()
            # because external_file is not relative to temp_dir
            result = organizer._copy_image(external_file, temp_dir)
            
            # Should fall back to flat structure (just filename)
            assert result.success
            assert result.destination_path.name == "external.jpg"
            assert result.destination_path.parent == output_dir
    
    def test_organize_images_with_file_errors(self, temp_dir, output_dir):
        """Test organization when some files have copy errors."""
        organizer = FileOrganizer(str(output_dir), dry_run=False)
        
        # Create one valid image and reference to non-existent image
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='green')
        valid_path = temp_dir / "valid.jpg"
        img.save(valid_path, "JPEG")
        
        invalid_path = temp_dir / "missing.jpg"  # Doesn't exist
        
        all_images = [valid_path, invalid_path]
        
        report = organizer.organize_images(
            duplicate_groups=[],
            all_images=all_images,
            show_progress=False
        )
        
        # Should process both but only succeed with one
        assert report.total_input_images == 2
        assert report.unique_images_copied == 1  # Only valid file copied
        assert len(report.errors) == 1  # One error reported
        assert "missing.jpg" in report.errors[0]


class TestOrganizeImagesFunction:
    """Test the convenience function organize_images."""
    
    def test_organize_images_function(self, temp_dir, output_dir):
        """Test organize_images convenience function."""
        # Create a simple test image
        from PIL import Image
        img = Image.new('RGB', (50, 50), color='green')
        img_path = temp_dir / "test.jpg"
        img.save(img_path, "JPEG")
        
        # Organize with no duplicates
        report = organize_images(
            duplicate_groups=[],
            all_images=[img_path],
            output_directory=str(output_dir),
            dry_run=True
        )
        
        assert isinstance(report, OrganizationReport)
        assert report.total_input_images == 1
        assert report.unique_images_copied == 1