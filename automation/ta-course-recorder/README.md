# TA 課程紀錄表自動化補全工具 (TA Course Recorder)

本工具專門用於自動化產生與補全「**AI融入課程教學紀錄表**」，支援一次產生全學期（Week 1 ~ Week 18）的所有週次紀錄，並存為單一 Excel 活頁簿。

---

## 核心特色與保證

1. **樣板格式 100% 遵守**：
   - 原樣板檔案僅以「唯讀」方式載入，絕對不更動或覆寫原樣板。
   - 複製出的各週分頁完整保留原表的 **29 組合併儲存格**、**欄寬**、**列高** 與 **框線樣式**。
   - 所有文字均強制套用標準字型（**標楷體 DFKai-SB**）、對應字級與自動換行，表格完全不跑版。
2. **自動推算與條件判定**：
   - 依據開學第一週日期，自動推算 18 週各週上課年月日。
   - 自動相減開始與結束時間計算課程長度（分鐘）。
   - 支援假日或考試週判定（`is_holiday: true`），自動將出席勾選框切換為「☑否」並補上說明。
3. **靈活設定檔 (`config.yaml`)**：
   - 課程名稱、教師、TA 姓名、上課時間等全域設定集中管理。
   - 提供「預設通用範本」，未填寫的週次自動帶入符合資安課程情境的高品質紀錄；已規劃的週次則可獨立自訂。

---

## 目錄結構

```text
automation/ta-course-recorder/
├── config.yaml          # 全域課程設定、預設內容與每週自訂紀錄
├── recorder.py          # openpyxl 格式維護與工作表複製核心引擎
├── run.py               # CLI 執行入口
└── README.md            # 使用指南
```

---

## 快速使用

### 1. 安裝相依套件
本工具僅需要標準的 `openpyxl` 與 `pyyaml`：
```bash
pip install openpyxl pyyaml
```

### 2. 執行產生全學期紀錄表
在 `automation/ta-course-recorder` 目錄下執行：
```bash
python run.py
```
或指定週數：
```bash
python run.py --weeks 18
```

產出的全學期檔案預設將儲存於專案根目錄：
`AI輔助教學TA補助計畫課程紀錄表-全學期.xlsx`

---

## 設定檔說明 (`config.yaml`)

```yaml
course:
  semester_title: "115學年度第一學期AI融入課程教學紀錄表"
  course_name: "電腦網路安全"
  teacher_name: "陳奕明"
  ta_name: "蔣侑宸"
  start_date: "2026-09-04"   # 第一週日期
  start_time: "14:07"
  end_time: "16:50"

# 每週特定主題
weeks:
  7:
    objective: "協助同學上手CTF平台 - Cylab，並完成實作"
    platform: "Antigravity (Gemini 3.8 Flash)\nClaude Code"
    pre_class: "預習：登入 Cylab 平台並熟悉題目分類"
    in_class: "帶領同學練習 Web / Reverse 題目，引導使用 AI 解釋加密演算法邏輯"
    post_class: "撰寫並提交第一題 Challenge 之 Writeup"
    reflection: "學生在面對陌生題目時，透過 AI 獲得解題思路引導，解題意願與課堂互動頻率顯著提高。"
  9:
    is_holiday: true
    holiday_reason: "期中考試週，無課堂觀課需求"
```
