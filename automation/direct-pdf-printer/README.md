# Direct PDF Printer for Windows

A reliable Windows CLI printing tool designed to bypass Chrome / Edge browser print preview crashes and OOM errors when printing huge, multi-page scanned PDF documents.

## How it works

- Bypasses Chromium's memory-heavy print preview pipeline completely.
- Uses `PyMuPDF` for fast page rendering and streams pages sequentially via Windows .NET `System.Drawing.Printing.PrintDocument`.
- Tiny memory footprint, preventing Windows Print Spooler buffer overflows and 0 KB print failures.

## Usage

### Method 1: Drag & Drop
Simply **drag and drop any PDF file onto `print.bat`** to immediately dispatch it to your default printer.

### Method 2: Python CLI
```bash
python direct_print.py "path/to/document.pdf"
```

### Method 3: PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File direct_print.ps1 -PdfPath "path/to/document.pdf"
```

Specify a custom printer:
```powershell
powershell -ExecutionPolicy Bypass -File direct_print.ps1 -PdfPath "path/to/document.pdf" -PrinterName "HP LaserJet MFP M227fdw"
```
