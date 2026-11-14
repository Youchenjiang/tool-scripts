# Photo Splitter - Technical Notes

This document summarizes the core architecture, layout detection heuristics, and cropping algorithms powering the `photo-splitter` suite.

---

## 1. Face Detection Pipeline

1. **YuNet (CNN-based Detector)**:
   - Primary detector loaded from `face_detection_yunet_2023mar.onnx` (automatically fetched from the OpenCV Zoo if not present locally).
   - High precision across various face angles, tilts, and expressions.
   - Filtered with a confidence threshold (`score >= 0.70`).
2. **Haar Cascades Fallback**:
   - Secondary backup detector combining frontal and profile face models with horizontal flip augmentation.
3. **Non-Maximum Suppression (NMS) & Deduping**:
   - Suppresses overlapping detection boxes (`iou_thr = 0.35`).
   - Deduplicates horizontally contiguous boxes using median face width metrics.

---

## 2. Advanced Midline Cropping Strategy

Simple bounding box expansion typically leads to adjacent neighbors being captured in the crop. `photo-splitter` employs **Horizontal Midline Splitting**:

1. **Midpoint Calculation**:
   - For all students detected in the same row, the horizontal midpoint between adjacent face centers is calculated:
     $$\text{cut}_j = \frac{x_{c, j} + x_{c, j+1}}{2}$$
   - This midpoint serves as a hard boundary limit for both neighboring students, guaranteeing that crops never horizontally overlap.
2. **Vertical Row Detection**:
   - The script detects 1-row vs. 2-row layouts by analyzing the vertical gaps between face centers:
     $$\text{gap} = y_{i+1} - y_i$$
   - When a 2-row layout is identified, horizontal partition planes are applied to prevent the upper row from cutting into the lower row's shoulder or body space.

---

## 3. Multi-Strategy Layout & Name Extraction

Matching faces to student names is challenging due to the diverse formatting of school group photos. `photo-splitter` uses a candidate-scoring multi-strategy pipeline:

1. **`label_top_bottom`**:
   - Parses explicit textual cues such as "上排由左至右" / "下排由左至右" (Top/Bottom Row from Left to Right).
2. **`geometry`**:
   - Extracts structured bounding boxes via Tesseract TSV mode.
   - Computes centroid coordinates $(x_c, y_c)$ for each detected name.
   - Aligns the horizontal centroids of text boxes with the horizontal centroids of face boxes.
3. **`strip_columns`**:
   - Divides the bottom banner area into $N$ vertical columns matching the number of detected students, running high-contrast binarized OCR on each individual strip.
4. **`blue_tags`**:
   - Uses HSV color segmentation to isolate colored name badges/cards.
5. **`easyocr_bottom` (Optional)**:
   - If `easyocr` is available, leverages PyTorch-based text detection to handle stylistic fonts, colored backgrounds, or low-resolution text.

### Strategy Scoring & Selection
Each candidate strategy is evaluated against the provided roster (or candidate density). The strategy with the highest number of valid name matches and highest average similarity ratio is chosen.

---

## 4. Roster Fuzzy Matching & Error Correction

OCR frequently misrecognizes complex Chinese characters (e.g. `好` instead of `妤`, `即` instead of `卿`).

- When a roster is supplied (via JSON or Excel/CSV), candidates are mapped using `difflib.SequenceMatcher`:
  - Surname match bonus: $+0.15$
  - Length consistency bonus: $+0.05$
- Candidates exceeding the acceptance threshold ($\ge 0.45$) are automatically corrected to the canonical roster spelling.

---

## 5. Audit & Quality Assurance Reporting

To avoid silent errors, the system outputs:
- **Execution Report (`--report <path>`)**: Summary table of all processed images, detected face counts, matched names, and strategies.
- **Low-Confidence Report (`--low-confidence-report <path>`)**: Automatically flags photos where match confidence fell below $0.65$ or where fallback strategies were triggered, directing human attention only to photos that actually require verification.

---

## 6. Student ID Mapping (`rename_by_roster.py`)

School administration systems invariably require files named by Student ID (`學號 姓名.png`).
- Smart table parsing scans `.xlsx`, `.xls`, and `.csv` files to detect ID and name columns automatically.
- Sanitizes full-width spaces and trailing symbols.
- Offers configurable formatting patterns, duplicate index handling, and dry-run preview mode.
