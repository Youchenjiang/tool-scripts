# PDF Contrast Enhancer

A tool designed for scanned documents, contracts, and application forms to dramatically enhance text contrast and darken faint handwriting/signatures. Particularly solves the issue where **monochrome laser printers** render blue ballpoint pen or light signatures as washed-out halftone dots.

## Key Features

1. **Darken Faint Signatures**: Specifically detects and boosts handwriting and blue ballpoint pen strokes via dynamic level mapping and non-linear gamma curves into rich, solid black toner.
2. **Automatic Background Whitening**: Detects background highlights and clips scan shadows, creases, and noise to pure white.
3. **Format Standardization & Repair**: Re-distills malformed PDF streams (e.g. non-standard CCITTFax / PDFsharp streams) into 100% compliant PDFs compatible with any printer or kiosk (e.g. 7-11 ibon).

## Requirements

- Python 3.8+
- `pymupdf`
- `numpy`

```bash
pip install -r requirements.txt
```

## Usage

```bash
python enhance_contrast.py <input_pdf_path> [-o <output_pdf_path>] [--dpi 200] [--gamma 2.2]
```

### Examples

**Basic usage (outputs `<name>_enhanced.pdf`):**
```bash
python enhance_contrast.py form.pdf
```

**Custom output filename with 300 DPI:**
```bash
python enhance_contrast.py contract.pdf -o contract_clean.pdf --dpi 300
```
