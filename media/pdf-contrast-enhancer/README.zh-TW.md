# PDF 筆跡加深與對比度增強工具 (PDF Contrast Enhancer)

專為掃描文件、手寫合約與表單設計的對比度自動強化工具。特別能解決**黑白雷射印表機**在列印藍色原子筆或淺灰手寫簽名時，因半色調網點淡化導致字跡發虛看不清的問題。

## 核心功能

1. **簽名筆跡加深**：針對手寫筆跡與藍色原子筆墨水進行專門黑度拉伸（色階重對應與非線性伽馬曲線），使列印時具有飽滿深黑碳粉濃度。
2. **紙張背景自動漂白**：智慧分析高光背景白點，消除掃描陰影、髒污折痕與灰色雜訊。
3. **格式標準化與修復**：重新封裝異常的 PDF 串流（如 PDFsharp 異常的 CCITTFax 傳真編碼），確保可在任何瀏覽器、印表機與超商機台（7-11 ibon / 全家 FamiPort）順利列印。

## 環境需求

- Python 3.8+
- `pymupdf`
- `numpy`

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
python enhance_contrast.py <輸入PDF路徑> [-o 輸出PDF路徑] [--dpi 200] [--gamma 2.2]
```

### 範例

**基本使用（自動產生 `_enhanced.pdf`）：**
```bash
python enhance_contrast.py "報名表.pdf"
```

**自訂輸出檔名與更高解析度：**
```bash
python enhance_contrast.py "合約.pdf" -o "合約_清晰版.pdf" --dpi 300
```
