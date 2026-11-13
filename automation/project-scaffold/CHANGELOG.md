# 📜 Project Scaffold 演進與變更歷史 (Changelog & Architecture Evolution)

本文件完整記錄 `automation/project-scaffold` 從建立至今的架構演進脈絡。專案腳手架遵循「漸進式增強（Progressive Enhancement）」與「防禦性工程（Defensive Engineering）」原則，經歷了從最初的一鍵模板生成，逐步進化為支援雙層架構、企業安全管線、CI 錯峰保護、現代化環境治理，乃至認知層級的「寬進嚴出思考協議（Deliberation Gate）」。

---

## 🗺️ 演進歷程總覽 (Milestone Overview)

```
[v1.0 基礎奠基] 
  ├── 一鍵裝配 (Git Hook / 多語言 .gitignore / Commit 政策 / CI Workflows)
  └── PR-Agent AI 代碼審查與 CodeQL SAST 整合
         │
         ▼
[v2.0 企業級資安平台管線] 
  ├── PR Gate ➔ Post-Deploy ➔ Runtime 三層生命週期防護
  └── 整合 CycloneDX SBOM, Dependency-Track, DefectDojo, Faraday, Wazuh, OpenVAS
         │
         ▼
[v3.0 雙層架構與工程治理工具集] 
  ├── Archetypes (專案雛型) ➔ Features (可選模組) 雙層解耦
  ├── 動態 Scope 注入與 Commit Linter (防搭便車 Anti-Free-Riding)
  └── 模組化 PR 治理套件 (13 項自動化審核、診斷、發布與發散防護)
         │
         ▼
[v4.0 效能防禦、配額守門與錯峰排程] 
  ├── CD 解耦 (workflow_run) 與 Staging URL 零額度浪費守衛 (Zero-Waste)
  ├── 導入輕量 Nuclei CVE 巡檢 (~40s 極速掃描)
  └── Hash-based Jitter Scheduling (以專案名稱哈希實現分鐘/時段完全錯峰，防止 Self-DDoS)
         │
         ▼
[v5.0 現代化環境治理與單元庫支援] 
  ├── 支援 script-tool 雛型與 direct-push (免 PR 主幹原子推送模式)
  └── 支援 conda-env 模組 (Python 3.14 + Mamba/GPU 最佳化、env_tool 髒配置清洗與硬體健檢)
         │
         ▼
[v6.0 寬進嚴出與認知層思考網關 (當前版本)] 
  └── 注入 deliberation-gate.md (What/Why 優先、負面約束紅線、多方案 Trade-off、破除 XY Problem、主動反駁權)
```

---

## 🔖 詳細變更日誌 (Detailed Version Changelog)

### [v6.0.0] - 2026-11-14：寬進嚴出思考協議 (Deliberation Gate)
> **核心痛點**：AI 容易陷入「微管理陷阱」，使用者過早指定「怎麼做（How）」而扼殺架構空間；AI 預設過度順從，不敢反駁過度設計或陷入 XY Problem。

* **新增 `deliberation-gate.md` 規範範本** (`templates/agent-rules/deliberation-gate.md`)：
  1. **What & Why over How**：將需求轉化為清晰目標與可測試驗收標準，抽離過度死板的實作步驟。
  2. **負面邊界（Negative Constraints）**：改以「禁止額外付費、不可破壞現有 Schema、資源預算上限」等紅線進行限制，在邊界內賦予 AI 充足架構自由度。
  3. **強制前置架構發散（Deliberation Gate）**：非瑣碎變更必須先提出 2~3 種取向的方案（極簡 MVP、穩健擴充、實用取向），並分析複雜度、維護成本與 Trade-off，經人類決策後才動手寫代碼。
  4. **破除 XY Problem**：主動識別使用者提出的代碼 Workaround 背後的根本限制，優先解決真痛點。
  5. **主動反駁權（Challenge Assumptions）**：正式授權 AI 主動質疑過度設計、邏輯矛盾與脆弱架構。
* **全專案 Archetype 預設裝配**：
  - 更新 `presets.json`，將 `deliberation-gate.md` 普及至全部 6 種專案雛型（`web-spa`, `backend-api`, `desktop-app`, `sec-research`, `minimal`, `script-tool`）。

---

### [v5.0.0] - 2026-11-01 ~ 2026-11-13：現代化環境管理與免 PR 主幹模式
> **核心痛點**：跨平台開發常因 Conda/Pip 髒配置與 CUDA 驅動不符導致環境崩潰；個人腳本庫與 Monorepo 每次提交都被強迫開 PR，流程過度冗贅。

* **新增 `conda-env` 擴充模組**：
  - 支援 Python 3.14 最新標準，按 Archetype 自動分發 `environment.ai.yml`、`environment.api.yml` 與 `environment.tool.yml`。
  - 注入 `tools/env_tool.py` 輔助工具：具備硬體/GPU/Mamba 診斷、一鍵跨平台建立環境、自動清洗 PyTorch/CUDA 與 pip prefix 髒設定。
  - 隨附完整測試套件 `tests/test_env_tool.py`。
* **新增 `script-tool` Archetype 與 `direct-push` 模組**：
  - 專為腳本庫、自動化工具與 Monorepo 設計。
  - 注入 `direct-trunk.md` Agent 規則，替換 PR 流程為「嚴格原子化提交（The Revert Test）+ 主幹直接推送（Direct Trunk Push）」。
  - 腳手架自動配置 `git config repo.directPush true`，且 GitHub Actions `policy.yml` 同步放行 push 事件。

---

### [v4.0.0] - 2026-10-05：CI 效能解耦、配額守門與錯峰排程 (Jitter Scheduling)
> **核心痛點**：Merge 後安全掃描卡在 CD 前置；OpenVAS 輪詢超時燒乾 GitHub Actions 配額；多個專案同時在每週一或每月 1 號集體執行定時掃描，引發 Concurrency 塞車與目標主機 Self-DDoS。

* **CD 解耦與 Zero-Waste 守衛** (`f3fcc94`)：
  - `post-merge-security.yml` 改用 `workflow_run` 監聽 CD/Deploy 成功完成事件，彻底與程式碼 push 解耦。
  - 加入秒級 URL 守衛：未設定 `STAGING_URL` 時秒級略過，0 耗費 Runner 額度。
  - OpenVAS 輪詢時間縮緊至 25 分鐘，避免卡死 Runner。
* **導入輕量 Nuclei 定期安全巡檢** (`a984495`)：
  - 新增 `nuclei-scan.yml`，針對 CVE 與危險設定進行高精準弱點掃描（耗時約 40 秒）。
  - 自動輸出 SARIF 格式無縫對接 GitHub Code Scanning 警示。
* **Hash-Based Jitter 錯峰排程機制** (`166e5d2`)：
  - 於 `init-project.ps1` 實作依專案名稱字串哈希 (`GetHashCode()`) 演算法。
  - 自動為不同專案生成隨機但確定性的排程（每月第 1~28 天、UTC 1~4 點、0~58 分；每週 1~7 天不同時段），杜絕多專案併發衝撞。

---

### [v3.0.0] - 2026-09-15 ~ 2026-10-04：雙層架構 (Archetypes & Features) 與 PR 治理套件
> **核心痛點**：過去 Preset 過於僵硬，無法自由組合；AI 提交代碼時常將文檔、記憶與功能代碼混在一起（搭便車 Free-Riding）；PR 格式混亂。

* **雙層架構全面重構** (`b12836e`, `46a70fa`)：
  - 抽象出基礎專案雛型：`web-spa`, `backend-api`, `desktop-app`, `sec-research`, `minimal`。
  - 抽象出可選擴充模組：`strict-linting`, `chained-prs`, `sec-enterprise`。
  - `init-project.ps1` 支援互動式選單、參數指定與動態白名單 Scope 注入 (`8efc0e3`)。
* **工程規範與防搭便車稽核器 (`lint_commits.py`)** (`b48f633`, `0dbf263`)：
  - 檢驗 Conventional Commits、字元上限 $\le 72$、禁句點、禁模糊字詞。
  - 採用 `git diff-tree` 實作 **Anti-Free-Riding**：嚴格禁止在單一 Commit 內混雜治理文件（`MEMORY.md`, `.agent/*`）與核心代碼。
* **全方位 PR 治理與輔助工具集 (`tools/pr_*.py`)** (`c06f6ba`, `865bab4`, `621d5c8`)：
  - 建立包含預檢、發布、審查、驗證、防發散等完整生命週期工具，Cognitive Complexity 經重構控制在 15 以下。
* **鏈式 PR 指引 (`chained-prs.md`) 與 嚴格代碼規範 (`strict-linting`)**：
  - 規範滾動 Rebase 技巧與 force-with-lease 邊界。
  - 注入 ESLint 嚴格規則（禁非空斷言、禁巢狀三元、命名長度防禦）。

---

### [v2.0.0] - 2026-09-02 ~ 2026-09-10：企業級全生命週期安全整合
> **核心痛點**：安全工具零散，無法在現代 DevOps 流程中建立統一資產清單與漏洞追蹤平台。

* **三層安全生命週期定義** (`SECURITY-CI.md`)：
  - **PR Gate**：`policy.yml`, `trufflehog.yml`, `codeql.yml`, `sbom.yml`。
  - **Post-Merge Security**：`post-merge-security.yml`, `zap-scan.yml`。
  - **Runtime Monitoring**：`wazuh-health.yml` 24/7 Agent 巡檢。
* **企業級安全平台對接 Workflows**：
  - `sbom.yml`：Syft 生成 CycloneDX SBOM，自動推送 Dependency-Track。
  - `defectdojo-upload.yml`：聚合 ZAP / SARIF 掃描報告。
  - `faraday-upload.yml`：滲透測試協作平台報告串接。
  - `wazuh-health.yml`：JWT 驗證 Wazuh Manager 端點代理健康度。

---

### [v1.0.0] - 2026-09-01：專案腳手架誕生
> **核心痛點**：新專案啟動時需重複配置 Git Hooks、Agent 規範、CI 政策與權限邊界。

* **初始化引擎**：
  - 推出 PowerShell 自動化部署腳本 `init-project.ps1`。
  - 支援 Windows / Linux CRLF 相容處理。
* **Agent 三階網關與記憶協議**：
  - 建立 `core.md`（只讀、本地編輯、分支變更、PR 合併四階授權隔離）。
  - 建立 `memory-protocol.md` 與持久化 `MEMORY.md` 規範。
  - 建立防暴力除錯協議（Stop Guessing & Brute Force）。
* **Git 與 CI 基底**：
  - 部署標準多語言 `.gitignore`、`.gitmessage.txt` 與 `.editorconfig`。
  - 部署 `.git/hooks/commit-msg` 與 GitHub Actions `policy.yml`。
  - 整合 `pr_agent.yml` 提供 AI 自動代碼 Review。
