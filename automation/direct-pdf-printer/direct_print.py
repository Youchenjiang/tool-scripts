"""
Direct PDF Printer for Windows (底層直接送印工具)
完全繞過瀏覽器列印預覽，使用 Windows .NET 底層逐頁向指定印表機發送實體列印工作。
"""

import os
import sys
import subprocess
import pymupdf

def print_pdf(pdf_path, printer_name="print (HP LaserJet MFP M227fdw)", dpi=200):
    if not os.path.exists(pdf_path):
        print(f"[!] 錯誤：找不到檔案 '{pdf_path}'", file=sys.stderr)
        return False
        
    abs_path = os.path.abspath(pdf_path)
    doc_name = os.path.splitext(os.path.basename(abs_path))[0]
    
    # 建立獨立暫存目錄
    temp_dir = os.path.join(os.environ.get("TEMP", "."), f"DirectPrint_{os.getpid()}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        doc = pymupdf.open(abs_path)
        page_count = len(doc)
        print(f"[*] 正在解析 '{doc_name}' (共 {page_count} 頁，解析度: {dpi} DPI)...")
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            pix.save(os.path.join(temp_dir, f"page_{i+1:03d}.jpg"))
        doc.close()
        
        # 產生標準 .NET PrintDocument 傳輸腳本
        ps_script = os.path.join(temp_dir, "print_job.ps1")
        ps_content = f"""Add-Type -AssemblyName System.Drawing
$printerName = '{printer_name}'
$imgFolder = '{temp_dir}'
$files = Get-ChildItem (Join-Path $imgFolder 'page_*.jpg') | Sort-Object Name

$doc = New-Object System.Drawing.Printing.PrintDocument
$doc.PrinterSettings.PrinterName = $printerName
$doc.DocumentName = '{doc_name}'

foreach ($paper in $doc.PrinterSettings.PaperSizes) {{
    if ($paper.Kind -eq [System.Drawing.Printing.PaperKind]::A4) {{
        $doc.DefaultPageSettings.PaperSize = $paper
        break
    }}
}}
$doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
$doc.OriginAtMargins = $false

$script:index = 0
$doc.add_PrintPage({{
    param($sender, $e)
    if ($script:index -lt $files.Count) {{
        $file = $files[$script:index].FullName
        $img = [System.Drawing.Image]::FromFile($file)
        $e.Graphics.DrawImage($img, $e.PageBounds)
        $img.Dispose()
        $script:index++
        $e.HasMorePages = ($script:index -lt $files.Count)
        Write-Host "    -> 傳輸進度: $($script:index) / $($files.Count) 頁"
    }} else {{
        $e.HasMorePages = $false
    }}
}})

$doc.Print()
"""
        with open(ps_script, "w", encoding="utf-8-sig") as f:
            f.write(ps_content)
            
        print(f"[*] 正在將列印工作發送至 '{printer_name}'...")
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.stdout:
            print(res.stdout.strip())
        if res.returncode != 0:
            print("[!] 列印失敗:", res.stderr, file=sys.stderr)
            return False
            
        print(f"[+] '{doc_name}' 全部 {page_count} 頁已成功送入印表機！\n")
        return True
    finally:
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except Exception:
            pass

def main():
    if len(sys.argv) < 2:
        print("使用方式: python direct_print.py <PDF檔案1> [PDF檔案2 ...]")
        return
        
    for p in sys.argv[1:]:
        print_pdf(p)

if __name__ == "__main__":
    main()
