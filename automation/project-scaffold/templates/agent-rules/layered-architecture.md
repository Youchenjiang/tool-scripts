# 逐層架構調查與相依拓撲規範 (Layered Architecture Guidelines)

當使用者要求「畫架構圖」、「整理分層」、「檢視某一層相依關係」、「分析模組呼叫」或「進行架構重構前調查」時，所有 AI Agent 均須嚴格恪守本規範。

---

## 1. 核心原則與底線

1. **真實呼叫為準，絕不預設「理想架構」**：
   - 繪製架構圖的目標不是畫出「教科書上的理想架構」，而是**把程式碼現況真實的呼叫與相依關係精準呈現**。
   - 唯有將真實關係畫出，違規跳層、重複邏輯、孤兒死碼與循環依賴才能一目了然。
2. **證據為本 (Evidence-based)**：
   - 每一條相依線條、每一個節點檔名，都必須有具體的 `import`、`using` 或靜態分析證據。沒查過的不畫；畫錯比不畫更糟。
   - 可優先使用 `python tools/architecture_graph.py` 自動提取 AST 相依拓撲。
3. **逐層推進 (One Layer at a Time)**：
   - 一次只調查並呈現一層，經使用者確認後再往下一層推進，避免一次產出巨型大圖造成認知負擔。
4. **只讀程式碼，未經授權不擅自修改**：
   - 調查階段僅讀取代碼；發現的問題一律整理為待辦問題清單（Action Items），修改交由後續獨立授權的任務執行。

---

## 2. 標準分層定義 (L0 ~ L4)

| 層級 | 層級名稱 | 涵蓋內容 | 判斷依據與證據來源 |
|---|---|---|---|
| **L0** | **入口層 (Entry)** | 使用者或系統觸發點（CLI 命令列、GUI 啟動檔、Main 進入點、API 路由進入點、Web index.html） | `main.py`, `app.ts`, `Program.cs`, `Package.appxmanifest` |
| **L1** | **展示層 (Presentation)** | 畫面元件、控制器、UI 視圖、CLI 格式化輸出、交互狀態 | `views/`, `components/`, `controllers/`, `pages/` |
| **L2** | **應用層 (Application)** | 核心業務用例、應用服務、流程編排、協調器 | `services/`, `usecases/`, `workflows/`, `handlers/` |
| **L3** | **領域與基礎設施 (Infra / Core)** | 資料庫存取、外部 API 客戶端、檔案系統、演算法核心、共用工具庫 | `core/`, `domain/`, `infra/`, `db/`, `repositories/` |
| **L4** | **模組內部拓撲 (Internal)** | 特定大型模組內部的檔案間引用與型別流轉 | 單一模組資料夾內部 AST 引用圖 |

---

## 3. 架構異常檢查清單

調查過程中，Agent 須重點檢視並在報告中標註以下 4 類架構壞味道：

1. **循環相依 (Circular Dependencies)**：
   - 模組 A 引用 B，B 又直接或間接引用 A。
   - 執行 `python tools/architecture_graph.py --check` 進行全域檢測。
2. **跳層呼叫 (Layer Skipping / Inversion)**：
   - 上層直接穿透中間層呼叫底層實作，或底層反向依賴上層展示層（如 L3 領域層引用 L1 視圖元件）。
3. **上帝檔案 (God Files / Classes)**：
   - 單一檔案行數龐大、職責過多。
   - 執行 `python tools/file_lines.py --top 10 --max-lines 500` 標註超標檔案。
4. **孤兒模組 (Orphan Modules)**：
   - 在專案內部既無人引用、亦不引用內部模組的孤島代碼（可能是殘留死碼）。

---

## 4. 輸出產物規範

1. **視覺圖表**：使用 Mermaid 流程圖語法輸出（`flowchart TD`），支援標籤清晰、箭頭方向正確。
2. **待辦問題清單 (Architecture Action Items)**：
   包含：問題編號、優先級（🔴 高 / 🟡 中 / ⚪ 低）、問題描述、檔案位置與行號、改善建議。
