# ADR-0001: 採用架構決策記錄 (ADR) 框架與多方案優缺點比對

* **狀態 (Status)**: 已採納 (Accepted)
* **決策日期 (Date)**: 專案初始化
* **參與者 (Deciders)**: 專案維護者, AI 代理人 (Antigravity)

---

## 1. 背景與核心痛點 (Context & Problem Statement)
隨著專案功能擴展與多人（或多 AI 工作階段）協作，程式庫中會陸續做出許多重大架構選型、模組切分與技術抉擇。
過往缺乏統一且持久化的決策記錄機制，導致：
1. **設計背景遺失**：後續接手人員無法理解「為什麼要設計得這麼複雜」或「當時有什麼環境限制」。
2. **重複評估與記憶漂移**：AI 代理人或新成員常常重新提議已被歷史驗證為不可行的方案。
3. **缺乏 Trade-off 審核**：容易在未經方案優劣分析的情況下倉促採用第一種直覺解法，陷入微管理或 XY Problem。

---

## 2. 決策考量與負面邊界 (Decision Drivers & Constraints)
* 🛑 **負面約束紅線 (Negative Constraints)**：
  - 記錄機制必須與程式碼版本庫共同管理（In-Repo），禁止依賴專有付費軟體或外部 SaaS 知識庫。
  - 格式必須是跨平台純文字 Markdown，無任何專屬編譯工具依賴。
  - 必須強制包含「多方案評估」與「優缺點比對」，禁止只寫結論的流水帳。
* 🎯 **目標與驗收標準**：
  - 目錄結構標準化（`docs/adr/`）。
  - 與專案的 `Deliberation Gate` 思考協議無縫聯動。

---

## 3. 備選方案優缺點評估 (Considered Options)

### 方案 A: 純仰賴 Commit Message 與 PR Body 記錄
* **概念架構**: 不建立任何專屬決策文件，直接把背景與原因寫在 Git Commit 與 GitHub PR 內文。
* 👍 **優點**:
  - 零額外檔案與維護成本。
* 👎 **缺點**:
  - 極度分散，後續查閱需反向 `git log` 或搜尋 GitHub Issue/PR，難以一覽全貌。
  - 離線時或將 Repo 鏡像/遷移至其他 Git 平台時，PR 資訊往往遺失。

### 方案 B: 集中於單一長文檔（如 ARCHITECTURE.md 或 Wiki）
* **概念架構**: 在根目錄維護一份 `ARCHITECTURE.md`，每次有新決策就往下 append。
* 👍 **優點**:
  - 檔案單一集中。
* 👎 **缺點**:
  - 隨著專案演進，單檔會極度臃腫，容易引發 Git 合併衝突。
  - 無法清晰標示每個個別決策的生命週期（如 Accepted, Deprecated, Superseded）。

### 方案 C: 採用標準 MADR (Markdown Architecture Decision Records) 獨立文件庫
* **概念架構**: 於 `docs/adr/` 為每個重大決策建立獨立編號的 Markdown 檔案，搭配標準範本與索引目錄。
* 👍 **優點**:
  - 業界標準，檔案獨立、可追溯性高，無合併衝突問題。
  - 與版本庫同生共死，完全離線可用。
  - 強制包含「背景、負面邊界、2~3 個備選方案優缺點對比、最終 Trade-off」。
* 👎 **缺點**:
  - 每次重大架構改動需多建立一份文檔，有輕微的維護成本。

---

## 4. 最終決策結果與妥協代價 (Decision Outcome & Trade-offs)

### 選擇方案
**選定：方案 C (標準 MADR 獨立文件庫)**

### 決策理由
1. 完美契合 `deliberation-gate.md` 所要求的「實作前先做多方案 Trade-off 評估」原則，讓思考成果得以沉澱。
2. 純 Markdown 格式，與 Git 版本庫完全同步，兼顧長期維護性與可讀性。

### 妥協代價與負面影響 (Consequences)
* ⚠️ **已知代價**:
  - 每當進行架構重大變更時，必須同步新增或更新 `docs/adr/`。
* 🛡️ **緩解措施**:
  - 提供 `template.md`，並在 Agent Rules 中授權 AI 協助草擬與維護 ADR，將撰寫成本降至最低。
