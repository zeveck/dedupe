"""
Pytest configuration and fixtures for image deduplication tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import numpy as np
from typing import List


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_images_dir(temp_dir):
    """Create a directory with sample test images."""
    images_dir = temp_dir / "test_images"
    images_dir.mkdir()
    
    # Create various test images
    create_test_images(images_dir)
    
    return images_dir


@pytest.fixture
def output_dir(temp_dir):
    """Create a temporary output directory."""
    out_dir = temp_dir / "output"
    out_dir.mkdir()
    return out_dir


def create_test_images(images_dir: Path) -> None:
    """Create a set of test images for testing purposes."""
    
    # Image 1: Red square with pattern (100x100) - avoid solid colors that generate identical hashes
    img1_array = np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8)  # Red base
    # Add some pattern to make hash unique
    img1_array[40:60, 40:60] = [200, 0, 0]  # Darker red square in center
    img1 = Image.fromarray(img1_array)
    img1.save(images_dir / "red_square.jpg", "JPEG", quality=95)
    
    # Image 2: Same red square but PNG format (should be detected as duplicate)
    img1.save(images_dir / "red_square.png", "PNG")
    
    # Image 3: Red square resized to 200x200 (should be detected as similar)
    img1_large = img1.resize((200, 200), Image.LANCZOS)
    img1_large.save(images_dir / "red_square_large.jpg", "JPEG", quality=95)
    
    # Image 4: Blue square with different pattern (completely different)
    img2_array = np.full((100, 100, 3), [0, 0, 255], dtype=np.uint8)  # Blue base
    img2_array[30:70, 30:70] = [0, 0, 200]  # Darker blue square in center
    img2 = Image.fromarray(img2_array)
    img2.save(images_dir / "blue_square.jpg", "JPEG", quality=95)
    
    # Image 5: Green gradient (different content)
    img3_array = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        img3_array[:, i, 1] = int((i / 100) * 255)  # Green gradient
    img3 = Image.fromarray(img3_array)
    img3.save(images_dir / "green_gradient.png", "PNG")
    
    # Image 6: Checkerboard pattern
    img4_array = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(0, 100, 10):
        for j in range(0, 100, 10):
            if (i // 10 + j // 10) % 2 == 0:
                img4_array[i:i+10, j:j+10] = [255, 255, 255]  # White
            else:
                img4_array[i:i+10, j:j+10] = [0, 0, 0]  # Black
    img4 = Image.fromarray(img4_array)
    img4.save(images_dir / "checkerboard.bmp", "BMP")
    
    # Image 7: Same checkerboard with slight compression (should be similar)
    img4.save(images_dir / "checkerboard_compressed.jpg", "JPEG", quality=70)
    
    # Create subdirectory with more images
    subdir = images_dir / "subdir"
    subdir.mkdir()
    
    # Image 8: Copy of red square in subdirectory
    img1.save(subdir / "red_copy.png", "PNG")
    
    # Image 9: Yellow circle (different shape)
    img5 = Image.new('RGB', (100, 100), color='white')
    # Draw a simple yellow circle using numpy
    center = 50
    radius = 40
    y, x = np.ogrid[:100, :100]
    mask = (x - center) ** 2 + (y - center) ** 2 <= radius ** 2
    img5_array = np.array(img5)
    img5_array[mask] = [255, 255, 0]  # Yellow
    img5 = Image.fromarray(img5_array)
    img5.save(subdir / "yellow_circle.png", "PNG")


@pytest.fixture
def mock_images() -> List[Path]:
    """Return a list of mock image paths for testing without actual files."""
    return [
        Path("test1.jpg"),
        Path("test2.png"),
        Path("test3.bmp"),
        Path("subdir/test4.jpg"),
    ]


@pytest.fixture
def corrupted_image_dir(temp_dir):
    """Create directory with some corrupted/invalid image files."""
    corrupt_dir = temp_dir / "corrupted"
    corrupt_dir.mkdir()
    
    # Create a valid image
    img = Image.new('RGB', (50, 50), color='red')
    img.save(corrupt_dir / "valid.jpg", "JPEG")
    
    # Create a corrupted image (just text data with image extension)
    with open(corrupt_dir / "corrupted.jpg", "w") as f:
        f.write("This is not an image file!")
    
    # Create an empty file
    (corrupt_dir / "empty.png").touch()
    
    # Create a non-image file
    with open(corrupt_dir / "readme.txt", "w") as f:
        f.write("This is a text file.")
    
    return corrupt_dir