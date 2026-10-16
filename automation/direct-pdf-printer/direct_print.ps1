<#
.SYNOPSIS
    Direct PDF Printer for Windows (底層直接送印工具)
.DESCRIPTION
    完全繞過 Chrome / Edge 瀏覽器容易因大圖、多頁而記憶體溢位卡死的預覽視窗，
    使用 Windows .NET 底層逐頁向指定或預設印表機發送圖檔列印工作。
#>

param(
    [Parameter(Position=0, Mandatory=$false)]
    [string]$PdfPath,
    [Parameter(Position=1, Mandatory=$false)]
    [string]$PrinterName
)

# 若未指定檔案，顯示選擇檔案或提示
if (-not $PdfPath) {
    Write-Host "請提供 PDF 檔案路徑，或將 PDF 檔案拖曳至本腳本上執行。" -ForegroundColor Yellow
    $PdfPath = Read-Host "請輸入 PDF 檔案完整路徑"
}

if (-not (Test-Path $PdfPath)) {
    Write-Error "找不到指定檔案: $PdfPath"
    exit 1
}

# 取得預設印表機（若未指定）
if (-not $PrinterName) {
    $defaultPrinter = Get-CimInstance Win32_Printer | Where-Object { $_.Default -eq $true } | Select-Object -ExpandProperty Name
    $PrinterName = $defaultPrinter
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Windows 系統底層直接列印工具" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[*] 列印目標: $PdfPath"
Write-Host "[*] 使用印表機: $PrinterName"

# 暫存圖檔目錄
$TempFolder = Join-Path $env:TEMP ("DirectPdfPrint_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TempFolder -Force | Out-Null

try {
    Write-Host "[*] 正在透過 PyMuPDF 擷取頁面影像..."
    $PyCmd = "import pymupdf, sys, os; doc = pymupdf.open(sys.argv[1]); [page.get_pixmap(dpi=200).save(os.path.join(sys.argv[2], f'page_{i+1:03d}.jpg')) for i, page in enumerate(doc)]; print(f'Extracted {len(doc)} pages.')"
    python -c $PyCmd "$PdfPath" "$TempFolder"

    $files = Get-ChildItem (Join-Path $TempFolder "page_*.jpg") | Sort-Object Name
    if ($files.Count -eq 0) {
        Write-Error "無法擷取 PDF 頁面影像，請確認 Python 環境已安裝 pymupdf。"
        exit 1
    }

    Write-Host "[+] 成功解析 $($files.Count) 頁，逐頁送入列印通道..." -ForegroundColor Green

    Add-Type -AssemblyName System.Drawing

    $doc = New-Object System.Drawing.Printing.PrintDocument
    $doc.PrinterSettings.PrinterName = $PrinterName
    $doc.DocumentName = [System.IO.Path]::GetFileNameWithoutExtension($PdfPath)

    # 預設套用 A4 紙張
    foreach ($paper in $doc.PrinterSettings.PaperSizes) {
        if ($paper.Kind -eq [System.Drawing.Printing.PaperKind]::A4) {
            $doc.DefaultPageSettings.PaperSize = $paper
            break
        }
    }
    $doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
    $doc.OriginAtMargins = $false

    $script:index = 0
    $doc.add_PrintPage({
        param($sender, $e)
        if ($script:index -lt $files.Count) {
            $file = $files[$script:index].FullName
            $img = [System.Drawing.Image]::FromFile($file)
            $e.Graphics.DrawImage($img, $e.PageBounds)
            $img.Dispose()
            $script:index++
            $e.HasMorePages = ($script:index -lt $files.Count)
            Write-Host "    -> 已傳輸第 $($script:index) / $($files.Count) 頁至印表機..."
        } else {
            $e.HasMorePages = $false
        }
    })

    Write-Host "[*] 正在發送列印工作..." -ForegroundColor Yellow
    $doc.Print()

    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "[+] 列印工作已成功遞交！" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
}
finally {
    Remove-Item $TempFolder -Recurse -Force -ErrorAction SilentlyContinue
}
