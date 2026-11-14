# Photo Splitter

A robust, intelligent computer vision toolkit for extracting individual student portraits from group photos, performing automatic layout inference, and renaming outputs using class rosters.

---

## Key Features

- **Automated Face Detection (OpenCV YuNet)**: High-precision CNN-based face detector (automatically fetched from OpenCV Zoo; includes Haar Cascades fallback).
- **Smart Midline Cropping**: Automatically computes horizontal midpoints between adjacent students, preventing crop overlap while preserving body proportions.
- **Multi-Strategy Layout Inference**:
  - `label_top_bottom`: Parses explicit row indicators ("上排由左至右" / "下排由左至右").
  - `geometry`: Aligns spatial centroids of OCR text boxes with face coordinates.
  - `strip_columns`: Slices photo strips into columns mapped directly to face positions.
  - `blue_tags`: Segment colored name badges using HSV color filtering.
  - `easyocr_bottom`: Optional deep-learning OCR boost for artistic or blurry fonts.
- **Fuzzy Name Correction**: Utilizes `difflib.SequenceMatcher` to correct OCR typos against official class rosters.
- **QA & Audit Reporting**: Outputs Markdown summary tables and flags low-confidence photos needing manual inspection.
- **Student ID Renamer (`rename_by_roster.py`)**: Batches and renames cropped portraits with Student IDs from `.xlsx`, `.xls`, or `.csv` files.

---

## Installation & Prerequisites

### 1. System Dependencies (Tesseract OCR)

This toolkit utilizes **Tesseract OCR** for text detection. Ensure it is installed and present in your system `PATH`:
- **Windows**: [UB-Mannheim Tesseract Installer](https://github.com/UB-Mannheim/tesseract/wiki) (Ensure **Traditional Chinese** (`chi_tra`) is checked during installation).
- **Ubuntu/Debian**:
  ```bash
  sudo apt install tesseract-ocr tesseract-ocr-chi-tra
  ```
- **macOS**:
  ```bash
  brew install tesseract tesseract-lang
  ```

### 2. Python Dependencies

```bash
pip install -r requirements.txt
```

*(Optional: Install `easyocr` for deep-learning enhanced text recognition: `pip install easyocr`)*

---

## Usage Guide

### Step 1: Split & Crop Group Photos

```bash
python split_students.py --input-dir <path_to_photos> --output-dir split_students_output
```

#### Optional Arguments:
- `--roster <path>`: Path to a class roster (`.xlsx`, `.xls`, `.csv`, or `.json`) to enable automatic typo correction.
- `--use-easyocr`: Enable EasyOCR for higher OCR accuracy on complex fonts.
- `--report <path.md>`: Generate a Markdown execution summary report.
- `--low-confidence-report <path.md>`: Generate a review list of low-confidence predictions.
- `--debug-dir <path>`: Folder for visual inspection images containing face and crop bounding boxes.

### Step 2: Batch Rename by Student ID (Optional)

If your school administration or grading system requires photos formatted as `學號 姓名.png` (e.g. `114001 林妤蓁.png`):

```bash
python rename_by_roster.py \
  --input-dir split_students_output \
  --roster 2025_MIS_roster.xlsx \
  --output-dir renamed_students_output
```

#### Renamer Features:
- Automatically detects columns named `學號` / `Student ID` and `姓名` / `Name`.
- Customizable naming templates via `--format "{id} {name}{ext}"`.
- Supports `--dry-run` to preview file mapping before execution.

---

## Technical Details

For an in-depth explanation of the geometry matching heuristics, midline cropping calculations, and confidence scoring, see [docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md).
