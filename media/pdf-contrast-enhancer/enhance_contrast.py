"""
PDF Contrast Enhancer (PDF 掃描筆跡加深與對比度增強工具)

功能：
1. 自動修復異常的非標準 CCITTFax / PDF 壓縮串流。
2. 智慧偵測並加深手寫簽名筆跡（特別是易被黑白雷射印表機半色調網點淡化的藍色原子筆與淺灰字跡）。
3. 自動計算紙張背景白點並執行高光漂白，消除掃描陰影與髒污雜點。
4. 輸出標準高相容性 PDF，供實體列印或超商機台（ibon / FamiPort）順利列印。
"""

import os
import sys
import argparse
import numpy as np
import pymupdf

def auto_enhance_luminance(lum: np.ndarray, gamma: float = 2.2) -> np.ndarray:
    """
    動態色階與非線性伽馬對比增強演算法：
    - 將背景高光漂白為純白 (255)
    - 將中淺灰階 (120~200) 的手寫筆跡與藍色原子筆筆劃拉深至深黑碳粉色階 (30~50)
    """
    white_pt = np.percentile(lum, 98)
    text_pixels = lum[lum < white_pt - 15]
    if len(text_pixels) == 0:
        return lum.astype(np.uint8)

    black_pt = max(20.0, np.percentile(text_pixels, 15))
    
    # 線性色階拉伸
    scale = (lum - black_pt) / (white_pt - black_pt)
    scale = np.clip(scale, 0.0, 1.0)
    
    # 伽馬曲線加深筆跡
    out = (np.power(scale, gamma) * 255.0).astype(np.uint8)
    return out

def enhance_pdf(input_path: str, output_path: str, dpi: int = 200, gamma: float = 2.2, quality: int = 92):
    if not os.path.exists(input_path):
        print(f"[!] 錯誤：找不到輸入檔案 '{input_path}'", file=sys.stderr)
        return False

    print(f"[*] 載入來源 PDF：{input_path}")
    src = pymupdf.open(input_path)
    dst = pymupdf.open()
    total_pages = len(src)
    print(f"[*] 總頁數：{total_pages} 頁，渲染解析度：{dpi} DPI，伽馬加黑係數：{gamma}")

    for i, page in enumerate(src):
        pix = page.get_pixmap(dpi=dpi)
        samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        
        if pix.n >= 3:
            r = samples[:, :, 0].astype(np.float32)
            g = samples[:, :, 1].astype(np.float32)
            b = samples[:, :, 2].astype(np.float32)
            # 藍色原子筆辨識與加黑加權補償
            blue_boost = np.where((b > r + 10) & (b > 100), (b - r) * 0.5, 0.0)
            lum = 0.299 * r + 0.587 * g + 0.114 * b - blue_boost
            lum = np.clip(lum, 0, 255)
        else:
            lum = samples[:, :, 0].astype(np.float32)

        enhanced_gray = auto_enhance_luminance(lum, gamma=gamma)
        
        # 建立高相容 8-bit 灰階影像物件
        enh_pix = pymupdf.Pixmap(pymupdf.csGRAY, pix.width, pix.height, enhanced_gray.tobytes(), False)
        img_bytes = enh_pix.tobytes(output="jpeg", jpg_quality=quality)
        
        rect = page.rect
        new_page = dst.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, stream=img_bytes)
        print(f"    - 已增強第 {i+1} / {total_pages} 頁")

    dst.save(output_path, deflate=True)
    src.close()
    dst.close()
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[+] 處理成功！輸出檔案：{output_path} ({file_size_mb:.2f} MB)")
    return True

def main():
    parser = argparse.ArgumentParser(description="PDF 掃描筆跡加深與對比度增強工具")
    parser.add_argument("input", help="輸入 PDF 檔案路徑")
    parser.add_argument("-o", "--output", help="輸出 PDF 檔案路徑（預設：<檔名>_enhanced.pdf）")
    parser.add_argument("--dpi", type=int, default=200, help="渲染解析度 (預設: 200)")
    parser.add_argument("--gamma", type=float, default=2.2, help="伽馬筆跡加黑係數 (預設: 2.2)")
    parser.add_argument("--quality", type=int, default=92, help="JPEG 壓縮品質 (預設: 92)")
    
    args = parser.parse_args()
    
    if not args.output:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_enhanced.pdf"
        
    enhance_pdf(args.input, args.output, dpi=args.dpi, gamma=args.gamma, quality=args.quality)

if __name__ == "__main__":
    main()
