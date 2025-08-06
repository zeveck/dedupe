# Image Deduplication App Implementation Plan

## Overview
Build a Python application that scans directory trees for images, detects visual duplicates, and outputs unique images to a target directory while preserving the highest quality versions.

## Core Architecture

### 1. Image Processing Pipeline
- **Scanner Module**: Recursively traverse input directories to find image files (JPG, PNG, PSD, etc.)
- **Hasher Module**: Generate perceptual hashes for each image using multiple algorithms
- **Comparator Module**: Compare hashes to detect similar images with configurable thresholds
- **Selector Module**: Apply quality-based prioritization rules to choose which duplicates to keep

### 2. Duplicate Detection Strategy

#### What is Perceptual Hashing?
Perceptual hashing creates a "fingerprint" of an image based on its visual content, not the raw pixel data. Unlike cryptographic hashes that completely change with any pixel modification, perceptual hashes remain similar for visually similar images. They work by analyzing structural features like brightness patterns, edges, and frequency distributions.

**Key Properties:**
- Robust to minor modifications (compression, brightness, contrast adjustments)
- Similar images produce similar hash values
- Measured using Hamming distance (number of differing bits)
- Typically 64-bit hashes for efficient comparison

#### Hash Algorithms We'll Use:

**Average Hash (aHash)** - Fastest but least accurate:
1. Resize image to 8x8 pixels (64 total)
2. Convert to grayscale
3. Calculate average brightness
4. Each pixel gets 1 bit: brighter than average = 1, darker = 0
5. Result: 64-bit hash

**Difference Hash (dHash)** - Good balance of speed and accuracy:
1. Resize to 9x8 pixels (72 total)
2. Compare each pixel with its right neighbor
3. Brighter than neighbor = 1, darker = 0
4. Focuses on gradients, robust to brightness changes
5. Result: 64-bit hash

**Perceptual Hash (pHash)** - Most accurate but slower:
1. Resize to 32x32 pixels
2. Convert to grayscale
3. Apply Discrete Cosine Transform (DCT) - converts to frequency domain
4. Extract top-left 8x8 DCT coefficients (lowest frequencies)
5. Compare each coefficient to median value
6. Result: 64-bit hash representing image structure

#### Detection Process:
- **Primary**: Use ImageHash library with multiple algorithms above
- **Secondary**: EXIF metadata analysis for file size, dimensions, creation date
- **Threshold**: Hamming distance ≤ 10 for similarity detection (96%+ similarity)
- **Multi-algorithm validation**: Require agreement between 2+ algorithms to reduce false positives

### 3. Quality Prioritization System
**File Format Priority**: PSD > PNG > JPG > others

**Quality Metrics**:
- File size (larger generally better for same format)
- Image dimensions (higher resolution preferred)
- Absence of signatures/watermarks (detect using edge detection in corner regions)
- EXIF quality indicators (if available)

### 4. Key Components
- `image_scanner.py`: Directory traversal and file discovery
- `hash_generator.py`: Perceptual hash calculation
- `duplicate_detector.py`: Similarity comparison and grouping
- `quality_assessor.py`: Image quality evaluation and selection
- `file_organizer.py`: Output directory management and file copying
- `dedupe.py`: CLI interface and orchestration

### 5. Technical Implementation Details

#### Core Libraries:
- **PIL/Pillow**: Image loading, processing, and format support
- **ImageHash**: Perceptual hashing algorithms (aHash, dHash, pHash)
- **Pathlib**: Modern file system operations
- **Click/Argparse**: CLI interface and argument parsing
- **tqdm**: Progress bars and user feedback

#### What is FAISS?
FAISS (Facebook AI Similarity Search) is an open-source library for efficient similarity search and clustering of dense vectors. For our image deduplication use case:

**Why FAISS for Image Deduplication:**
- **Scale**: Can handle billions of vectors (image hashes) efficiently
- **Speed**: 8.5x faster than traditional nearest-neighbor search
- **Memory**: Optimized for both RAM-resident and disk-based datasets
- **Binary Support**: IndexBinaryFlat optimized for 64-bit binary hashes
- **Hamming Distance**: Built-in support for our hash comparison metric

**For Our Use Case (1000s of images):**
Since we're targeting collections of thousands (not tens of thousands) of images, **FAISS is unnecessary complexity**. Simple pairwise comparison will be:
- **Fast enough**: O(n²) comparison manageable for <5000 images
- **Simpler**: No external dependencies or index building
- **Easier to debug**: Straightforward comparison logic
- **Memory efficient**: Process images in batches as needed

**Simplified Approach:**
1. Generate perceptual hashes for all images
2. Compare each image hash against all others (pairwise)
3. Group images with Hamming distance ≤ threshold
4. Apply quality selection within each group

#### Optional Advanced Libraries:
- **opencv-python**: Advanced image analysis for watermark detection (if needed)
- **exifread**: EXIF metadata extraction for quality assessment

#### Performance Considerations:
- Configuration file for thresholds and preferences
- Dry-run mode to preview actions before execution
- Batch processing for memory efficiency
- Caching of computed hashes to avoid recomputation

### 6. Output Structure
- Preserve original filename when possible
- Handle naming conflicts with incremental suffixes
- Optional: Create report of detected duplicates and actions taken
- Maintain folder structure option vs flat output

### 7. CLI Interface
```bash
python dedupe.py --input /path/to/images --output /path/to/deduplicated --threshold 10 --dry-run
```

**Arguments**:
- `--input`: Source directory to scan
- `--output`: Target directory for unique images
- `--threshold`: Similarity threshold (default: 10)
- `--dry-run`: Preview actions without copying files
- `--preserve-structure`: Maintain directory structure in output
- `--report`: Generate detailed duplicate report

## Implementation Phases

### Phase 1: Core Infrastructure
1. Set up project structure and dependencies
2. Implement image scanner for file discovery
3. Basic hash generation using ImageHash
4. Simple duplicate detection with basic quality selection

### Phase 2: Enhanced Detection
1. Multi-algorithm hash comparison
2. EXIF metadata extraction and analysis
3. Quality assessment scoring system
4. Signature/watermark detection in image corners

### Phase 3: User Interface & Features
1. CLI interface with comprehensive options
2. Progress reporting and logging
3. Dry-run mode for safe testing
4. Duplicate report generation

### Phase 4: Performance & Polish
1. Optimize for large image collections
2. Memory-efficient processing
3. Error handling and edge cases
4. Documentation and testing

## Concerns & Considerations
- **Performance**: Large image collections may require batch processing and caching
- **Memory Usage**: Process images in chunks, don't load all into memory
- **Edge Cases**: Corrupted files, unsupported formats, permission issues
- **Accuracy**: Balance between false positives (missing real duplicates) and false negatives (flagging non-duplicates)
- **Signature Detection**: May need computer vision techniques to detect watermarks/signatures in corners

## Dependencies
**Core Requirements:**
- `Pillow` (PIL) for image processing
- `imagehash` for perceptual hashing
- `click` for CLI interface
- `tqdm` for progress bars
- `pathlib` for file system operations (built-in)

**Optional Enhancements:**
- `opencv-python` for advanced image analysis (watermark detection)
- `exifread` for detailed EXIF metadata extraction

## Expected Challenges
1. **Visual Similarity Detection**: Balancing sensitivity vs specificity
2. **Watermark Detection**: Identifying signatures without false positives
3. **Performance at Scale**: Handling thousands of images efficiently
4. **Format Support**: Ensuring compatibility with various image formats including PSD
5. **Quality Assessment**: Objective metrics for subjective image quality

This approach leverages proven perceptual hashing techniques while addressing your specific requirements for quality-based selection and handling of modified images.