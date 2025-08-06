# Image Deduplication Tool

A Python tool that intelligently removes duplicate images from directories using perceptual hashing. It detects visually similar images (not just exact duplicates) and keeps the highest quality version from each group.

## Features

- **Visual Similarity Detection**: Uses multiple perceptual hashing algorithms (aHash, dHash, pHash)
- **Quality-Based Selection**: Automatically keeps the best version based on format, resolution, file size, and sharpness
- **Watermark Detection**: Identifies and prefers images without signatures/watermarks
- **Format Priority**: Prefers PSD > PNG > JPG > other formats
- **Dry Run Mode**: Preview operations before making changes
- **Progress Tracking**: Real-time progress bars and detailed reporting
- **Flexible CLI**: Multiple options for customization

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Basic deduplication
python dedupe.py /path/to/images /path/to/output

# Dry run to see what would happen
python dedupe.py /path/to/images /path/to/output --dry-run

# Analyze only (no file copying)
python dedupe.py analyze /path/to/images
```

## Usage Examples

### Command Syntax

```bash
python dedupe.py dedupe INPUT_DIR OUTPUT_DIR [OPTIONS]
python dedupe.py analyze INPUT_DIR [OPTIONS]
```

### Common Operations

```bash
# Basic deduplication with dry run
python dedupe.py /Photos /Photos_Deduplicated --dry-run

# More strict similarity detection (fewer duplicates)
python dedupe.py /Photos /Photos_Deduplicated --threshold 5

# Preserve directory structure in output
python dedupe.py /Photos /Photos_Deduplicated --preserve-structure

# Include additional file types
python dedupe.py /Photos /Photos_Deduplicated -e .raw -e .cr2

# Save detailed report
python dedupe.py /Photos /Photos_Deduplicated --report dedup_report.json

# Quiet mode (minimal output)
python dedupe.py /Photos /Photos_Deduplicated --quiet

# Analyze directory without organizing files
python dedupe.py analyze /Photos --threshold 8
```

## How It Works

1. **Scanning**: Recursively finds all image files in the input directory
2. **Hashing**: Generates perceptual hashes using three algorithms:
   - **Average Hash (aHash)**: Fast, good for basic similarity
   - **Difference Hash (dHash)**: Robust to brightness changes
   - **Perceptual Hash (pHash)**: Most accurate, uses DCT frequency analysis
3. **Comparison**: Compares all images pairwise using Hamming distance
4. **Grouping**: Groups similar images together (requires 2+ algorithms to agree)
5. **Selection**: Chooses best image from each group based on:
   - File format priority (PSD > PNG > JPG)
   - Image resolution
   - File size
   - Sharpness analysis
   - Absence of watermarks
6. **Organization**: Copies unique images to output directory

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--threshold` | 10 | Similarity threshold (0-64, lower = more strict) |
| `--agreement` | 2 | Number of hash algorithms that must agree (1-3) |
| `--preserve-structure` | False | Maintain directory structure in output |
| `--dry-run` | False | Show what would be done without copying |
| `--quiet` | False | Suppress progress bars and verbose output |
| `--hash-size` | 8 | Hash size for perceptual hashing (8 or 16) |

## Supported Formats

- **Standard**: JPG, JPEG, PNG, GIF, BMP, TIFF, TIF, WEBP
- **Professional**: PSD, RAW, CR2, NEF, ARW, DNG
- **Custom**: Add more with `-e .extension`

## Understanding Similarity Thresholds

The similarity threshold controls how strict duplicate detection is:

- **0-5**: Very strict - only nearly identical images
- **6-10**: Moderate - good balance of accuracy (recommended)
- **11-15**: Loose - may catch more variations but more false positives
- **16+**: Very loose - not recommended for most use cases

## Output and Reports

### Standard Output
- Progress bars during processing
- Summary of duplicates found
- Space savings calculation
- List of duplicate groups with recommendations

### JSON Reports
Save detailed reports with `--report filename.json`:
- Complete list of all operations
- File paths and sizes
- Error details
- Timestamps

### File Organization
- Unique images copied to output directory
- Filename conflicts resolved automatically (adds _1, _2, etc.)
- Optional directory structure preservation
- Detailed logging of all operations

## Examples by Use Case

### Professional Photo Workflow
```bash
# Strict deduplication preserving RAW files
python dedupe.py ~/Photos/Import ~/Photos/Unique -t 5 -e .raw -e .cr2 --preserve-structure
```

### Social Media Cleanup
```bash
# Moderate deduplication for downloaded images
python dedupe.py ~/Downloads/Images ~/Pictures/Cleaned -t 10 --dry-run
```

### Archive Organization
```bash
# Comprehensive analysis with detailed reporting
python dedupe.py ~/Archive/Photos ~/Archive/Cleaned -t 8 --report archive_report.json
```

## Troubleshooting

### Common Issues

**"No images found"**
- Check that the input directory exists and contains supported image formats
- Add custom extensions with `-e .extension` if needed

**"Permission denied"**
- Ensure you have read access to input directory and write access to output directory
- Check that images aren't currently open in other applications

**"Memory error with large collections"**
- The tool is optimized for thousands of images
- For very large collections (>10K images), consider processing in batches

### Performance Notes

- Processing time scales with O(n²) for similarity comparisons
- Typical performance: ~1000 images in 30-60 seconds
- Memory usage stays reasonable due to streaming processing
- Use `--hash-size 8` for faster processing of large collections

## Technical Details

### Quality Assessment Criteria

1. **Format Score** (30% weight)
   - PSD: 100 points (uncompressed, editable)
   - PNG: 90 points (lossless)
   - TIFF: 85 points (professional)
   - JPG: 60 points (lossy compression)

2. **Resolution Score** (25% weight)
   - Logarithmic scale based on total pixels
   - Higher resolution preferred

3. **File Size Score** (20% weight)
   - Larger files often indicate less compression
   - Adjusted by format expectations

4. **Sharpness Score** (20% weight)
   - Laplacian variance analysis
   - Detects image detail and focus quality

5. **Watermark Penalty** (5% weight)
   - Corner analysis for signatures/logos
   - Prefers images without watermarks

### Hash Algorithms Details

- **Hash Size**: 64-bit hashes (8x8) by default, 256-bit (16x16) for higher precision
- **Similarity Metric**: Hamming distance (number of differing bits)
- **Consensus Logic**: Requires agreement between multiple algorithms to reduce false positives

## License

This tool is provided as-is for personal and educational use. Please respect copyright laws when deduplicating images.

---

## Credits

**Created by:** Rich Conlan  
**Code Development:** Entirely written by Claude Code (Anthropic's AI coding assistant)