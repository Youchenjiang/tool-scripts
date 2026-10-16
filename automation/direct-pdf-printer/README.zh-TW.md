# Windows 底層直接列印工具 (Direct PDF Printer)

專門解決 Chrome / Edge 瀏覽器在列印超大型 PDF、多頁高解析度掃描檔時，因 Chromium 列印預覽行程記憶體溢位（OOM）而卡死、當機或另存 0 KB 的問題。

## 運作原理

- 不經過任何瀏覽器的 Print Preview 預覽視窗。
- 透過 `PyMuPDF` 快速提取頁面影像，並使用 Windows .NET 的 `System.Drawing.Printing.PrintDocument` 底層通道**逐頁**發送至印表機。
- 記憶體佔用極低（僅單頁暫存），徹底避免列印佇列緩衝區溢位。

## 使用方法

### 方式 1：拖曳列印（最簡單）
直接用滑鼠將任意 PDF 檔案**拖曳並放到 `print.bat` 圖示上放開**，即會自動調用預設印表機進行列印。

### 方式 2：命令列執行
```powershell
powershell -ExecutionPolicy Bypass -File direct_print.ps1 -PdfPath "目標文件.pdf"
```

指定特定印表機：
```powershell
powershell -ExecutionPolicy Bypass -File direct_print.ps1 -PdfPath "目標文件.pdf" -PrinterName "HP LaserJet MFP M227fdw"
```
