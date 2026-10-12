# 成績登記手冊與規則說明

本目錄用於管理學生名冊與成績登記。

## 學生總數與班級組成（最新）
- **總人數**：68 人
- **班別組成**：
  - `114483` 系列：1 人（114483005 陳勇行）
  - `115423` 系列（碩班）：63 人
  - `115483` 系列（博一）：4 人

---

## 學號後兩碼重複對照表（共 4 組）

> 註：原本的 `11` 號博一同學已不在名冊中，目前 `11` 號僅有 `115423011 張愷文` 一人，已成為唯一號碼無需再確認！

| 後兩碼 | 碩士班同學 (`115423`) | 博士班同學 (`115483`) |
| :---: | :--- | :--- |
| **01** | `115423001` 廖宸緯 | `115483001` 陳佩妤 |
| **02** | `115423002` 曾紘杰 | `115483002` 楊博元 |
| **04** | `115423004` 郭仕彥 | `115483004` 潘振卿 |
| **07** | `115423007` 陳古智 | `115483007` 簡辰宇 |

---

## 專案結構與個資隔離設計 (Data Isolation)

本專案採「代碼與數據完全分離」設計：
- **`data/`（完全受 `.gitignore` 隔離）**：存放所有真實學生名冊（`roster.csv`）與歷次成績登記檔案（`grade_*.csv`、`grade_*.xlsx`），確保絕對不會被意外 Commit 或 Push 到 GitHub。
- **`data.example/`**：提供脫敏的範例名冊（`roster.example.csv`），供專案開源或跨環境測試。
- **根目錄**：僅保留純代碼（`grade_recorder.py`、`export_excel.py`）與說明文件。

```text
Grade/
├── data/                  # [已 Git 忽略] 真實名冊與各次成績 (.csv, .xlsx)
├── data.example/          # 脫敏名冊範例 (供測試)
├── grade_recorder.py      # 成績登記與衝突比對主程式
├── export_excel.py        # 美化版 Excel 批次導出模組
├── generate_xlsx.bat      # 雙擊一鍵轉檔批次檔
├── README.md              # 系統手冊
├── DESIGN_AND_ROADMAP.md  # 系統架構規劃
└── .gitignore             # 隔離 data/ 目錄
```

---

## 自動化登記指令碼
本目錄提供 [`grade_recorder.py`](file:///c:/Users/g1014/Documents/GitHub/Youchen/Grade/grade_recorder.py)：
- **自動對應 `data/`**：預設自動讀取 `data/roster.csv`，每次作業自動產出獨立檔案至 `data/grade_YYYYMMDD.xlsx`。
- **一人多次提交/超額防呆警報**：若單一學生或重複號碼組提交次數超額，立即跳出醒目警報，絕不默默覆蓋。
- **支援多欄複製貼上**：直接支援 Excel 複製的 `A+`、`A`、`A-` 多欄格式。
- **支援快捷標記**：支援 `1博 A+`、`1碩 A` 快捷輸入，直接精準配對免確認。

### 執行方式
```powershell
python grade_recorder.py
```
若需手動將 `data/` 下所有 CSV 批次轉為 Excel：
```powershell
python export_excel.py
```
或直接在資料夾中雙擊 [`generate_xlsx.bat`](file:///c:/Users/g1014/Documents/GitHub/Youchen/Grade/generate_xlsx.bat)。

---

## 歷史登記記錄

### 第一次登記 (2026-09-15)
- **檔案**：`grade_20260915.csv` / `grade_20260915.xlsx`
- **已登記人數**：63 人（A+: 17人、A: 40人、A-: 6人）

### 第二次登記 (2026-09-29)
- **檔案**：[`grade_20260929.csv`](file:///c:/Users/g1014/Documents/GitHub/Youchen/Grade/grade_20260929.csv) / [`grade_20260929.xlsx`](file:///c:/Users/g1014/Documents/GitHub/Youchen/Grade/grade_20260929.xlsx)
- **總學生人數**：67 人 (已同步移出退選之劉禹岑)
- **已登記人數**：65 人（A++: 1人、A+: 25人、A: 38人、A-: 1人）
- **未登記 / 缺繳同學**：2 人（59陳祈叡、82朱晉毅）

### 第三次登記 (2026-10-06)
- **檔案**：[`grade_20261006.csv`](file:///c:/Users/g1014/Documents/GitHub/Youchen/Grade/grade_20261006.csv) / [`grade_20261006.xlsx`](file:///c:/Users/g1014/Documents/GitHub/Youchen/Grade/grade_20261006.xlsx)
- **總學生人數**：67 人
- **已登記人數**：**67 人（100% 全員繳交，0 缺繳！）**
  - **A+**：42 人（含陳佩妤、楊博元、郭仕彥、簡辰宇 等）
  - **A**：23 人（含廖宸緯、曾紘杰、潘振卿 等）
  - **A-**：2 人（賴彥宏、陳古智）
