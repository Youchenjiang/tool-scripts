# 學生照片自動分割與學號重命名工具 (Photo Splitter)

本工具是一套專為學校、系所與班級設計的電腦視覺批次處理套件，能自動從合照中識別人物、智慧推斷排版與姓名、以無重疊中線裁切出個人肖像，並支援依名冊 Excel/CSV 自動對應學號重命名。

---

## 核心特點

- **高精度人臉偵測 (OpenCV YuNet)**：採用 CNN 深度學習人臉偵測模型（首次執行自動下載，並具備 Haar Cascade 自動備援）。
- **智慧中線裁切演算法**：自動計算相鄰人臉水平中點作為裁切分界線，確保同排同學彼此不互相重疊，且保留適當身形高度。
- **多策略排版與姓名辨識**：
  - `label_top_bottom`：解析「上排由左至右」、「下排由左至右」等常見排版文字標記。
  - `geometry`：計算文字方塊與人臉方塊的空間中心座標，自動幾何對齊。
  - `strip_columns`：將標籤帶投影分割成多個欄位獨立進行高對比 OCR。
  - `blue_tags`：透過 HSV 顏色遮罩辨識常見的藍底姓名標籤條。
  - `easyocr_bottom`：支援選用深度學習 OCR（EasyOCR）補強藝術字體或模糊文字。
- **名冊模糊比對與錯字自動校正**：使用 `difflib.SequenceMatcher` 自動將 OCR 辨識出來的同音/形似錯字修正為正式名冊中的學生姓名。
- **質檢報告與低信心覆核清單**：自動產出 Markdown 執行報告，主動列出匹配率偏低或觸發降級的照片，讓人工覆核一目了然。
- **學號批次重命名工具 (`rename_by_roster.py`)**：一鍵將裁切後的照片（如 `01_林妤蓁.png`）對照名冊表格重命名為學號格式（如 `114001 林妤蓁.png`）。

---

## 安裝與系統依賴

### 1. 系統依賴 (Tesseract OCR)

本工具使用 **Tesseract OCR** 進行文字識別。請確認系統已安裝並將其加入環境變數 `PATH`：
- **Windows**: [下載安裝檔](https://github.com/UB-Mannheim/tesseract/wiki)（安裝時請務必勾選 **Traditional Chinese (繁體中文)** 語系包 `chi_tra`）。
- **Ubuntu / Debian**:
  ```bash
  sudo apt install tesseract-ocr tesseract-ocr-chi-tra
  ```
- **macOS**:
  ```bash
  brew install tesseract tesseract-lang
  ```

### 2. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

*(選用：若希望使用深度學習加強版文字辨識，可另外安裝：`pip install easyocr`)*

---

## 使用教學

### 步驟一：合照人物分割與裁切

```bash
python split_students.py --input-dir <圖片目錄路徑> --output-dir split_students_output
```

#### 常見選用參數：
- `--roster <路徑>`：傳入班級名冊檔案（`.xlsx`、`.xls`、`.csv` 或 `.json`），啟用 OCR 錯字自動校正。
- `--use-easyocr`：若本機有安裝 EasyOCR，啟用高精度文字偵測。
- `--report <路徑.md>`：產出處理結果彙總 Markdown 報告。
- `--low-confidence-report <路徑.md>`：產出低信心度清單，標示建議人工檢查的合照。
- `--debug-dir <路徑>`：除錯檢查圖目錄（標示綠色人臉框與藍色裁切框）。

---

### 步驟二：對照名冊自動批次重命名為學號 (選用)

若教務系統、作業系統需要以 `學號 姓名.png` 格式建檔：

```bash
python rename_by_roster.py \
  --input-dir split_students_output \
  --roster 2025_碩士班MIS_分組名單.xlsx \
  --output-dir renamed_students_output
```

#### 重命名工具功能亮點：
- **智慧欄位探測**：自動識別名冊表格中含有「學號」與「姓名」特徵的欄位，亦可手動透過 `--id-col` 與 `--name-col` 指定。
- **彈性命名格式**：支援 `--format "{id} {name}{ext}"` 自訂檔名。
- **安全預覽模式**：支援 `--dry-run` 參數，在不實際移動/複製檔案的情況下先預覽所有對應結果。

---

## 技術細節與原理解析

詳細演算法公式、中線切分計算方式與多策略匹配流程請參考：[docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md)。
