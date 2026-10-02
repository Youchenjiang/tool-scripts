# Slide Deck Auditor (投影片排版與語意自動審查工具)

`slide-deck-auditor` 是一款專為現代簡報、講義與前端 UI 卡片設計的靜態語意與版面防護審查工具。

旨在解決投影片開發中常見的 **「垂直死空間 (Dead Space)」、「電梯井陷阱 (Elevator Shaft Trap)」、「黑底截圖無效 Letterbox」**，以及資安演講中最忌諱的 **「語意色彩倒置 (紅色防禦)」** 與 **「空泛 AI 宣傳浮誇腔」**。

---

## ✨ 核心檢測引擎

本工具內建五大靜態審查引擎：

| 規則代碼 (Rule ID) | 嚴重等級 | 說明與檢測標的 |
| :--- | :---: | :--- |
| `elevator_shaft` | **ERROR** | **電梯井死空間**：檢測在同一卡片或容器中，縱向排列（`flex-col` / `column`）同時搭配 `space-between`，在垂直內容少時會將上下推開，中間留下 >40% 的巨大空白空洞。 |
| `letterboxing_void` | **ERROR** | **黑底無效截圖**：檢測圖片容器設定黑底（`#000`、`bg-black`）搭配 `objectFit: contain`。當非 16:9（如 2.32:1 寬螢幕截圖）放進高容器時，會產生高達 300px+ 的黑邊無效死空間。 |
| `semantic_color_inversion` | **ERROR** | **語意色彩倒置**：檢測防禦（Mitigation）、修復（Patch）、加固等安全處置區塊，錯誤使用象徵威脅與漏洞的紅色調（`c.accent`, `red`），違反防禦即綠色的資安視覺語意。 |
| `ai_fluff` | **WARN** | **空泛 AI 虛詞**：過濾「科學驗證法則」、「震撼發現」、「驚人心智模型」、「破案地圖」等空洞宣傳腔調，確保演講講稿維持工程師專業口吻。 |
| `typography_floor` | **WARN** | **字級地板保護**：在 1080p 投影標準下，警示標題 < 32px 或內文 < 22px 的過小文字，避免演講現場後排學員無法閱讀。 |

---

## 🚀 快速開始

### 環境需求
- Python 3.8+（**零第三方依賴**，純使用標準函式庫）

### 執行掃描

```bash
# 掃描當前目錄所有投影片與組件
python slide_deck_auditor.py

# 掃描指定目錄或檔案（支援 .tsx, .jsx, .vue, .html, .css, .md）
python slide_deck_auditor.py path/to/slides/

# 輸出為 GitHub Actions 註解格式
python slide_deck_auditor.py path/to/slides/ --format github

# 輸出為 JSON 報告（供 CI 系統整合）
python slide_deck_auditor.py path/to/slides/ --format json

# 當有任何 WARN 時也中斷並回傳非 0 狀態碼
python slide_deck_auditor.py path/to/slides/ --fail-on warn
```

---

## ⚙️ 自訂規則設定 (`rules.json`)

工具支援載入自訂規則設定：

```json
{
  "rules": {
    "elevator_shaft": { "enabled": true, "severity": "ERROR" },
    "letterboxing_void": { "enabled": true, "severity": "ERROR" },
    "semantic_color_inversion": { "enabled": true, "severity": "ERROR" },
    "ai_fluff": { "enabled": true, "severity": "WARN" },
    "typography_floor": { "enabled": true, "severity": "WARN" }
  },
  "ai_fluff_keywords": [
    "科學驗證法則",
    "驚人心智模型",
    "震撼發現"
  ]
}
```

使用自訂設定檔：
```bash
python slide_deck_auditor.py -c my-rules.json src/
```

---

## 🛡️ 行內忽略機制 (Inline Suppression)

在少數特殊版面若需特例放行，可在代碼該行或前一行加入行內註解：

```tsx
// 忽略特定規則
// slide-audit-ignore: elevator_shaft
<div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
  ...
</div>

// 忽略該區塊所有規則
// slide-audit-ignore: all
```

---

## 🧪 單元測試

本工具具備完整的自動化單元測試套件：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🔗 方法學與工程規範連結

`slide-deck-auditor` 是 **「資安實戰教材三位一體研發生命週期（Triangular Pedagogy Lifecycle）」** 的官方 **Phase 4 自動化品質防護閘門**。

有關完整的四大研發階段、英雄視覺放大法、實體裁切標準與反模式禁區，請參見：
- [`workflow_lab-deck-engineering.md`](../../../Method-List/resources/agent-rules/workflow_lab-deck-engineering.md)

