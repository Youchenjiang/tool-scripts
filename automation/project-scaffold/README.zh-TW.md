# 🚀 Project Scaffolding System (工程規範一鍵腳手架)

本工具為新專案或既有專案提供**一鍵自動化裝配**：
- **Agent Rules**（授權三階網關、寬進嚴出思考協議 Deliberation Gate、除錯防暴力、MEMORY 協議、Conventional Commits、平台防禦）
- **Git 規範與 Hook**（`.gitignore`、`.gitmessage.txt`、`.editorconfig`、`commit-msg` 驗證鉤子）
- **GitHub Actions CI/CD**（PR Gate、CycloneDX SBOM、Dependency-Track、DefectDojo、Greenbone/OpenVAS、Faraday、Wazuh、PR-Agent、Nuclei）
- **協作模板**（`pull_request_template.md`、`dependabot.yml`、`SECURITY.md`）
- **架構決策與演進**（[演進與變更日誌 CHANGELOG.md](CHANGELOG.md)、ADR 決策記錄框架 `docs/adr/`）

---

## 快速使用

### 1. 跨平台命令列執行

腳手架核心引擎採用 **100% 純 Python 標準庫** 實作（`scaffold_engine.py`），具備跨平台支援：

#### 🐧 Linux / macOS
```bash
# 使用 Bash 包裝器
./init-project.sh --archetype backend-python --project-name "MyApi" --target-dir "./MyApi"

# 或直接使用 Python 引擎
python scaffold_engine.py --archetype backend-python --project-name "MyApi" --target-dir "./MyApi"
```

#### 🪟 Windows PowerShell
```powershell
# 互動式選單
.\init-project.ps1

# 命令列直接開案
.\init-project.ps1 -Archetype backend-python -ProjectName "MyApi" -TargetDir "C:\path\to\MyApi"
```

### 2. 常用開案範例
```powershell
# Python 後端 (FastAPI / Django) - 保證 0% Node.js / npm 污染
.\init-project.ps1 -Archetype backend-python -Features conda-env -TargetDir "C:\path\to\PyApi" -ProjectName "PyApi"

# Node.js 後端 (Express / Nest / TypeScript)
.\init-project.ps1 -Archetype backend-node -Features strict-linting -TargetDir "C:\path\to\NodeApi" -ProjectName "NodeApi"

# 網頁 / 前端全端 (React / Ionic / Vite) + 啟用代碼規範與鏈式 PR 指引
.\init-project.ps1 -Archetype web-spa -Features strict-linting,chained-prs -TargetDir "C:\path\to\WebPortal" -ProjectName "WebPortal"

# 桌面端 (Windows / C# / .NET / WinUI) + 啟用 MSIX 打包與架構拓撲守護
.\init-project.ps1 -Archetype desktop-app -Features msix-packaging,architecture-guard,git-worktree -TargetDir "C:\path\to\NewApp" -ProjectName "NewApp"

# AI 研究 / 資安實驗室
.\init-project.ps1 -Archetype sec-research -TargetDir "C:\path\to\Research" -ProjectName "Research"

# 極簡小工具 / 單檔腳本 (無額外擴充模組、設定免版本管理)
.\init-project.ps1 -Archetype minimal -NoRelease -NoFeatures -TargetDir "C:\path\to\Tool" -ProjectName "Tool"
```
*(向後相容：亦可繼續使用 `-Preset` 參數傳入舊有名稱如 `backend-api`、`web`、`desktop`、`research`。`backend-api` 將自動探測目標目錄之檔案並轉導為 `backend-python` 或 `backend-node`。)*

### 3. 直接對 Agent 下指令
在新專案開啟對話時，直接告訴 Agent：
> *「請使用 `Script-List/automation/project-scaffold` 的 `web-spa` archetype（啟用 `strict-linting` 與 `chained-prs`）初始化這個專案」*

Agent 會自動讀取配置並就地生成完整的規範體系與客製化 Scopes。

---

## 🏗️ 雙層架構設計 (Archetypes & Features)

腳手架採用 **「基礎專案雛型 (Archetype) ➔ 可選擴充模組 (Modular Features)」** 的兩層架構：

### 1. 基礎雛型 (Archetypes)

| Archetype | 相容別名 | 主要生態 | 適用場景 | 自動注入 CI Scopes | 專屬預載規範 / Hook 安裝器 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`backend-python`** | `backend-api`, `backend-py` | Python 3.10+ | FastAPI, Django, Flask, 現代化微服務 | `core, api, auth, db, service, middleware, config, test, deps, docs, ci, setup, agent, chore` | Python Ruff/Pytest、`scripts/install-hooks.py` (**0% Node.js 污染**) |
| **`backend-node`** | `backend-js`, `node-api` | Node.js / TS | Express, NestJS, Fastify 服務端全端 | `core, api, auth, db, service, middleware, config, test, deps, docs, ci, setup, agent, chore` | ESLint、npm prepare hook、`scripts/install-hooks.mjs` |
| **`web-spa`** | `web`, `frontend` | TypeScript | React, Ionic, Vue, Vite, SPA 前端專案 | `core, app, ui, style, render, sim, test, docs, ci, deps, spec, rules, setup, quality, agent, chore` | Web Guidelines、`eslint.config.mjs`、`scripts/install-hooks.mjs` |
| **`desktop-app`** | `desktop`, `winui`, `wpf` | C# / .NET | Windows, .NET, WinUI, WPF 桌面應用 | `core, shell, ui, native, msix, store, test, deps, docs, ci, setup, agent, chore` | .NET Hygiene, Store Release, `scripts/install-hooks.py` |
| **`sec-research`** | `research`, `security`, `lab` | Python | AI 論文, 漏洞分析, PoC 實驗庫 | `core, poc, vuln, exploit, report, scanner, data, test, deps, docs, ci, setup, agent, chore` | PR-Agent, Security Audit rules, `scripts/install-hooks.py` |
| **`script-tool`** | `script`, `scripts`, `tools` | 語言中立 | 腳本庫 / 個人工具集 / Monorepo (如 tool-scripts) | `core, automation, data, media, text, security, ai, cli, test, deps, docs, ci, setup, catalog, agent, chore` | 免開 PR、主幹原子推送規範 (`direct-trunk.md`)、`scripts/install-hooks.py` |
| **`minimal`** | `tool`, `cli` | 語言中立 | 極簡小工具, 快速原型 | `core, tool, test, deps, docs, ci, setup, agent, chore` | 僅核心 Commit 規範與 policy.yml, `scripts/install-hooks.py` |

### 2. 可選擴充模組 (Modular Features / Add-ons)

| Feature | 模組名稱 | 功用與配置內容 |
| :--- | :--- | :--- |
| **`git-worktree`** | Git Worktree 並行工作流 | 支援獨立 Worktree 目錄並行開發（`../<repo>-pr-<branch>`），避免依賴快取污染。清理時具備 `ancestry`、`squash` patch、`rebase` cherry 3 重密碼學等價證明合併驗證門禁，嚴防未合併代碼遺失。 |
| **`architecture-guard`** | 逐層架構與代碼指標 | 部署 `layered-architecture.md` 規則、`tools/file_lines.py`（單檔 500 行上限門禁）與 `tools/architecture_graph.py`（Python/TS/C# AST 相依拓撲、循環依賴檢測、孤兒死碼掃描與 Mermaid 輸出）。 |
| **`msix-packaging`** | Windows MSIX 桌面打包簽章套件 | 部署 `tools/create_dev_cert.ps1`（自簽 Code Signing 憑證生成與本機 Trusted People 一鍵信任）與 `tools/verify_msix_signature.ps1`（MSIX Authenticode 簽章與發行者 Publisher CN 一致性校驗門禁）。 |
| **`strict-linting`** | 嚴格代碼規範 | 部署 `eslint.config.mjs`，內建 TypeScript 嚴格規則、SonarCloud S3358 巢狀三元運算式防禦 (`no-nested-ternary`)、變數命名長度規範 (`id-length`)、物件非空斷言防禦 (`no-non-null-assertion`)。 |
| **`bot-pr-exempt`** | 自動化 PR 免 body 契約 | `dependabot[bot]`、`github-actions[bot]` 等 Bot 開的 PR 跳過 PR body 章節與 External provider 勾選檢查；人手開的 PR 仍完整檢查。未啟用時所有 PR 一律受檢查。 |
| **`direct-push`** | 免 PR 主幹原子推送 | 適用於無需開 PR 的腳本庫、筆記庫或工具庫。自動切換 Agent Rules 為主幹推送規範 (`direct-trunk.md`)，並設定 `git config repo.directPush true` 允許直推 `main`，Policy CI 同步支援 push 事件。 |
| **`chained-prs`** | 鏈式 PR 工作流 | 部署 `chained-prs.md` 規則，規範滾動 Rebase（Rolling Rebase）技巧、分支推動決策樹（普通 append vs force-with-lease）、GitHub 倉儲設定（關閉 squash merge、Rulesets 配置）。 |
| **`sec-enterprise`** | 企業級資安平台對接 | 部署完整 Post-Deploy 與排程安全驗證工作流（Dependency-Track, DefectDojo, Faraday, Wazuh, Nuclei, post-merge-security）。適合企業正式環境使用。 |
| **`conda-env`** | Conda/Mamba 環境管理 | 自動生成現代化 `environment.yml`（支援 Python 3.14、PyTorch CUDA、FastAPI、工具模板），注入 `tools/env_tool.py`（提供硬體/GPU/Mamba 診斷、一鍵建立與髒 YAML 清洗）與 `tests/test_env_tool.py`。 |

### 3. 發佈與版本生命週期策略 (Release & CD Lifecycle)

開案時可透過 `-Release <strategy>` 或互動選單選擇版本管理策略（或使用 `-NoRelease` 完全關閉版本管理）：

| 策略名稱 | 版本控制主檔 | 同步檔案 (`syncFiles`) | 適用情境 |
| :--- | :--- | :--- | :--- |
| **`npm-version`** | `package.json` | `package-lock.json` | Node / TypeScript / 前端 Web 專案 |
| **`dotnet-store`** | `Directory.Build.props` | `Package.appxmanifest` | .NET / C# 桌面端或 Windows Store 應用（保持 4 碼對齊） |
| **`python-version`** | `pyproject.toml` | 無 | Python 函式庫、CLI 套件、FastAPI 服務 |
| **`github-tag`** | `VERSION` | 無 | 單元腳本庫、Go/Rust 輕量工具、容器化服務 |
| **`none`** | 無 (不建立版號檔案) | 無 | 內部快速原型、免版本管理工具庫 (`-NoRelease`) |

配套治理工具：
- **`tools/bump_version.py`**：依據 `tools/project.json` 自動進行 `major`/`minor`/`patch`/`revision` 升版，同步關聯檔案並自動在 `CHANGELOG.md` 注入新版本日誌骨架。
- **`tools/release_checker.py`**：Tag 推播前的嚴格門禁，驗證 Tag 版本與各檔案版本號及 CHANGELOG 是否 100% 吻合。

### 4. 生態隔離 Git Hook 生命週期 (Ecosystem-Clean Hooks)
- **Node.js 專案 (`backend-node`, `web-spa`)**：
  - 當目標專案包含 `package.json` 時，腳手架自動於 `scripts` 注入 `"prepare": "node scripts/install-hooks.mjs"`。
  - 同步部署 `scripts/install-hooks.mjs` 與版本庫納管的 `scripts/hooks/*`。
  - 執行 `npm install` 時自動部署 `.git/hooks/commit-msg` 與 `pre-push`。
- **Python / .NET / 通用專案 (`backend-python`, `desktop-app`, `sec-research`, `minimal`, `script-tool`)**：
  - 部署純 Python 標準庫實作之 `scripts/install-hooks.py`。
  - 執行 `python scripts/install-hooks.py` 即可完成 Hook 部署與 `.gitmessage.txt` 提交範本綁定，**100% 零 Node.js / npm 依賴**。

---

## 🛠️ 內建工程規範與 PR 工具說明

初始化專案會在 `tools/` 目錄裝配兩套經 SonarCloud 零漏洞驗證之跨平台自動化工具：

### 1. `tools/lint_commits.py` (Commit 規範與職責分離稽核器)
* **檢驗項目**：Conventional Commits 標題格式、長度 $\le 72$ 字元、白名單 Scope、禁止句點結尾、杜絕空洞描述。
* **防搭便車 (Anti-Free-Riding)**：自動使用 `git diff-tree` 掃描整條修訂範圍，若偵測到在同一筆 Commit 中將治理文檔 (`MEMORY.md`, `docs/HANDOVER.md`, `.agent/`) 與功能代碼混雜提交，立即發出告警或錯誤阻擋。
* **執行方式**：
  ```bash
  python tools/lint_commits.py --base origin/main
  # 嚴格模式（將警告視為錯誤）
  python tools/lint_commits.py --base origin/main --strict
  ```

### 2. `tools/pr_helper.py` (PR 自動生成、結構驗證與安全提交助手)
* **自動萃取 Body**：解析自基準分支以來的所有 Commit，按 Conventional Commits 分類產出合規 Markdown。
* **格式驗證**：推送前本機檢驗 PR 標題、分支命名、與 PR Body 必要章節（`## Summary`, `## Changes`, `## Validation`, `## Review Checklist`）與 External provider 聲明。
* **Provider 決策**：`create` 產生的 body 帶未勾選的 `External provider` 項（刻意設計，工具不得替人宣告供應商決定）；開 PR 前請確認該項，否則 policy 會擋。
* **規避 Shell 字串截斷**：以 `--body-file` 搭配 `--label` 呼叫 `gh pr create`，徹底消除 Windows/PowerShell 引號脫落與 GitHub Actions 時序競態問題。
* **執行方式**：
  ```bash
  # 1. 自動產生 PR 內容
  python tools/pr_helper.py generate --base origin/main
  # 2. 本機驗證 PR 格式
  python tools/pr_helper.py lint --body-file PR_BODY.md --title "feat(core): implement new feature"
  # 3. 本機預檢並一鍵安全提交 PR
  python tools/pr_helper.py create --title "feat(core): implement new feature" --label "documentation"
  ```

---

## 🛡️ 安全 CI 架構：PR Gate → Post-Deploy → Runtime & Jitter Schedule

安全流程依生命週期分成三層。完整設計、平台設定與導入順序請見 [Security CI Architecture](SECURITY-CI.zh-TW.md)。

| 階段 | 自動執行內容 | 定位 |
| :--- | :--- | :--- |
| **PR Gate** | Policy、TruffleHog、CodeQL、SBOM；research preset 另有 PR-Agent | 合併前找出程式碼、Secret、規範與供應鏈問題 |
| **Post-Deploy Security** | Dependency-Track、Staging readiness、ZAP、OpenVAS、DefectDojo、Faraday | CD 部署成功後觸發 (`workflow_run`)，驗證正式 SBOM 與部署環境（Zero-Waste 守衛） |
| **Runtime & Scheduled Audit** | Nuclei、CodeQL 定期巡檢（哈希錯峰 Jitter 排程）；Wazuh 24/7 Agent 監控 | 部署後端點與輕量 CVE 巡檢持續在線，避免多專案併發撞牆與額度耗盡 |

PR 階段的 Enforcement 不是全部相同：

| Workflow | Enforcement |
| :--- | :--- |
| `policy.yml` | **Hard Gate** |
| `trufflehog.yml` | **Security Gate** |
| `codeql.yml` | **Soft Security Signal**（目前分析步驟 `continue-on-error`） |
| `sbom.yml` | **Artifact-only on PR**；Dependency-Track 只在非 PR 上傳 |
| `pr_agent.yml` | **Optional Soft Review** |

### Workflow 詳細參考

### 1. `policy.yml` (PR & Commit 政策看門狗)
* **檢驗標準**：PR 標題與所有 Commit 首行必須符合 Conventional Commits 格式，長度小於 72 字元，禁止結尾句號，禁止模糊詞彙。
* **分級回報**：
  * ❌ **Blocker (硬性阻擋)**：格式錯誤、超長、帶句號 -> 阻擋 PR 合併。
  * ⚠️ **Warning (軟性提醒)**：缺少 Label、未關聯 Milestone -> 輸出警告提醒補件，不阻擋合併。
  * 📋 **Step Summary**：自動在 Actions Summary 頁面產生 Markdown 表格，清晰條列狀態與修正指引。

### 2. `trufflehog.yml` (機敏金鑰與 Token 洩漏防禦)
* **防禦機制**：啟用 `--only-verified` 深入掃描 800+ 種 API Keys 與私鑰，僅在經端點實名驗證為真實金鑰時才報警，杜絕假陽性干擾。
* **容錯處理**：分開處理 `pull_request` 與 `push` 事件，徹底解決新分支首次推送時引發的自我比對崩潰問題。

### 3. `codeql.yml` (SAST 靜態代碼安全分析)
* **觸發時機**：推送到 main/master、PR 到 main/master、以及**每週哈希錯峰排程 (Weekly Hash Jitter)**。
* **分析範圍**：支援 `javascript-typescript` 與 `python`，深度分析 SQL Injection、Command Injection、XSS 等語意資料流漏洞。
* **容錯處理**：加上語言容錯（`continue-on-error: true`），若專案僅包含其中一種語言，不會造成整個工作流失敗。

### 4. `zap-scan.yml` (OWASP ZAP DAST 動態網站漏洞掃描)
* **觸發時機**：**手動按需觸發 (`workflow_dispatch`)**。
* **為什麼不自動跑？**：動態黑箱掃描必須有正在運行的 Web 伺服器端點（如 Staging/Dev 伺服器），因此設計為按需輸入 URL 執行，避免在 PR 自動跑時因伺服器未啟動而無謂報錯。
* **輸出結果**：掃描完成後，若發現安全風險會自動在 Repository 建立 GitHub Issue 安全警示報告。

### 5. `sbom.yml` (CycloneDX SBOM + Dependency-Track)
* **SBOM 產生**：Push、PR 或手動執行時使用 Syft 產生 `sbom.cdx.json`，並保存 30 天 Actions Artifact。
* **Dependency-Track**：非 PR 執行時，若已設定 `DTRACK_URL` 與 `DTRACK_API_KEY`，自動上傳至 `/api/v1/bom`。
* **專案對應**：可設定 `DTRACK_PROJECT_UUID` 指向既有專案；未設定時，以 Repository 名稱與分支版本呼叫 Dependency-Track auto-create。

### 6. `defectdojo-upload.yml` (DefectDojo 報告聚合)
* **定位**：這是一個 reusable workflow，不負責掃描；它下載其他 scanner job 產生的 Artifact，再呼叫 DefectDojo `/api/v2/reimport-scan/`。
* **必要輸入**：`artifact_name`、Artifact 內的 `report_path`、以及 DefectDojo 支援的 `scan_type`（例如 `ZAP Scan`、`SARIF`）。
* **手動重送**：支援 `workflow_dispatch` 指定既有 Actions `source_run_id`，方便測試或補送失敗報告。
* **安全預設**：未設定 `DEFECTDOJO_URL` / `DEFECTDOJO_API_TOKEN` 時只顯示 Notice 並跳過；PR 不會上傳外部平台。

### 7. `faraday-upload.yml` (Faraday 滲透測試協作)
* **定位**：Reusable connector，將 ZAP、OpenVAS 等 scanner 產生的 Artifact 匯入 Faraday workspace。
* **API**：使用 `Authorization: Token` 呼叫 `/_api/v3/ws/<workspace>/upload_report`。
* **安全預設**：未設定 Faraday URL、workspace 或 API Token 時自動跳過，不影響 CI。

### 8. `wazuh-health.yml` (Wazuh Runtime 健康檢查)
* **定位**：Wazuh 維持 24/7 Runtime / Endpoint 監控；CI 僅在部署後確認指定 Agent 仍為 `active`。
* **流程**：向 Wazuh Server API 取得 JWT，再查詢 `GET /agents`。
* **自簽憑證**：僅在必要時設定 `WAZUH_TLS_INSECURE=true`。

### 9. `post-merge-security.yml` (CD 部署後動態安全驗證)
* **觸發時機**：CD 部署完成事件 (`workflow_run` on completion of Deploy/CD)，或手動按需觸發 (`workflow_dispatch`)。
* **Zero-Waste 額度守衛**：若未配置 `STAGING_URL`，秒級判定並優雅跳過，不白白佔用 Runner 額度。
* **Staging Gate**：最多等待 5 分鐘確認部署端點可連線，再開始動態掃描。
* **Web DAST**：對 Staging 執行 ZAP Baseline，報告同時可送 DefectDojo 與 Faraday。
* **Infrastructure Scan**：若 Greenbone 設定完整，透過 GMP over SSH 啟動既有 OpenVAS task、等待完成並保存 XML，之後同時送 DefectDojo 與 Faraday。輪詢上限限縮至 25 分鐘，避免卡死 Runner。
* **Runtime Check**：最後呼叫 Wazuh health workflow，確認部署環境 Agent 仍在線。

### 10. `pr_agent.yml` (AI 自動代碼審查)
* **配置需求**：需在 Repo Secrets 設置 `OPENAI_KEY` 或 `SILICONFLOW_API_KEY`。
* **韌性防護**：若未配置 Secret 會輸出 GitHub Notice 並優雅跳過；設有 `continue-on-error: true`，第三方 AI API 服務超時或停機時**絕不阻擋**正常代碼合併。

### 11. `nuclei-scan.yml` (輕量 CVE 與安全性設定巡檢)
* **觸發時機**：**每月哈希錯峰排程 (Hash-based Jitter Schedule)** 或手動執行 (`workflow_dispatch`)。
* **錯峰排程 (Jitter) 機制**：`init-project.ps1` 依據專案名稱哈希自動注入獨立的每月執行日（1..28）、時（1..4 UTC）、分（0..58），徹底杜絕多專案在同日同時段併發衝擊 Runner 額度與目標伺服器 (Self-DDoS)。
* **極速掃描與額度保護**：鎖定 `critical,high` 與 `cve,misconfig` 標籤，單次掃描約 40 秒，消耗額度極低。
* **警示整合**：掃描結果自動輸出為 SARIF 格式並上傳至 GitHub Code Scanning Alerts。

### 外部安全平台設定

| 類型 | 名稱 | 用途 |
| :--- | :--- | :--- |
| Repository Variable | `DTRACK_URL` | Dependency-Track base URL |
| Repository Secret | `DTRACK_API_KEY` | Dependency-Track API key；既有專案需 BOM upload 權限，auto-create 另需 project creation upload 權限 |
| Repository Variable | `DTRACK_PROJECT_UUID` | 可選；直接指定既有 Dependency-Track project |
| Repository Variable | `DTRACK_PROJECT_NAME` | 可選；auto-create 時覆寫 Repository 名稱 |
| Repository Variable | `DTRACK_PROJECT_VERSION` | 可選；auto-create 時覆寫分支版本 |
| Repository Variable | `DEFECTDOJO_URL` | DefectDojo base URL |
| Repository Secret | `DEFECTDOJO_API_TOKEN` | DefectDojo API v2 Token |
| Repository Variable | `STAGING_URL` | Merge 後 ZAP / deployment readiness 的 Staging URL |
| Repository Variable | `OPENVAS_HOST` | Greenbone / GVM 主機名稱或 IP |
| Repository Variable | `OPENVAS_TASK_ID` | 已建立好的 Greenbone scan task UUID |
| Repository Variable | `OPENVAS_SSH_PORT` | 可選；Greenbone SSH port，預設 22 |
| Repository Variable | `OPENVAS_SSH_USERNAME` | 可選；Greenbone SSH 使用者，預設 `gmp` |
| Repository Secret | `OPENVAS_GMP_USERNAME` | Greenbone Management Protocol 使用者 |
| Repository Secret | `OPENVAS_GMP_PASSWORD` | Greenbone Management Protocol 密碼 |
| Repository Secret | `OPENVAS_SSH_PASSWORD` | Greenbone SSH transport 密碼 |
| Repository Variable | `FARADAY_URL` | Faraday server base URL |
| Repository Variable | `FARADAY_WORKSPACE` | Faraday workspace 名稱 |
| Repository Secret | `FARADAY_API_TOKEN` | Faraday API Token |
| Repository Variable | `WAZUH_URL` | Wazuh server API URL，例如 `https://wazuh.example:55000` |
| Repository Variable | `WAZUH_AGENT_NAME` | Merge 後要確認狀態的 Wazuh agent 名稱 |
| Repository Variable | `WAZUH_TLS_INSECURE` | 可選；自簽 TLS 環境才設為 `true` |
| Repository Secret | `WAZUH_API_USER` | Wazuh server API 使用者 |
| Repository Secret | `WAZUH_API_PASSWORD` | Wazuh server API 密碼 |

Merge 後的預設安全資料流為：

```text
Merge to main/master
  -> Staging readiness
  -> ZAP -----------+-> DefectDojo
                    +-> Faraday
  -> OpenVAS -------+-> DefectDojo
                    +-> Faraday
  -> Wazuh agent health check

SBOM -> Dependency-Track
```

DefectDojo connector 由 scanner workflow 以 job 方式呼叫，例如：

```yaml
jobs:
  upload-defectdojo:
    needs: scan
    uses: ./.github/workflows/defectdojo-upload.yml
    with:
      artifact_name: zap-report
      report_path: report_json.json
      scan_type: ZAP Scan
    secrets: inherit
```

---

## 🛠️ PR 全生命週期與工程治理工具鏈 (Engineering & Governance Toolchain)

腳手架提供開箱即用、通過 SonarCloud 與單元測試（225 項測試）驗證的跨平台治理工具庫（位於目標專案的 `tools/`）：

### 1. PR 流程與分支治理
- **`pr_tool.py`（一站式 PR 操作中樞）**：
  - `python tools/pr_tool.py prepare`：飛行前檢查（分支命名合規性、工作區乾淨度、Commit 格式）。
  - `python tools/pr_tool.py push`：受控推播，嚴格執行 `pre-push` 本地完整門禁。
  - `python tools/pr_tool.py create`：依據模板安全建立 PR，防止 Windows 引號與字串截斷。
  - `python tools/pr_tool.py verify`：一鍵聚合查詢 CI 狀態、SonarCloud 品質指標與未解決 Review 討論串。
  - `python tools/pr_tool.py diagnose`：自動提取失敗 CI 或靜態分析的關鍵日誌。
  - `python tools/pr_tool.py threads <PR>`：透過 GitHub GraphQL 查詢所有未解決之審核討論串。
  - `python tools/pr_tool.py resolve <PR> --thread-id <ID> | --all`：經授權透過 GraphQL 一鍵解決 Review 討論串。
- **`branch_policy.py`（分支命名守衛）**：
  - 強制分支前綴規範（`feat/`, `fix/`, `refactor/` 等）、後綴 2～3 個單字、總長度嚴格 $\le 25$ 字元。
- **`pr_helper.py`（PR 內容智慧萃取）**：
  - `python tools/pr_helper.py generate`：自動解析分支相對於 `origin/main` 的 Commits，萃取標準 Markdown PR 內容。
- **`worktree_tool.py`（Git Worktree 隔離並行開發）**：
  - `python tools/worktree_tool.py list`：列出活躍工作樹。
  - `python tools/worktree_tool.py start <branch>`：建立父目錄獨立工作樹（`../<repo>-pr-<branch>`），避免跨分支快取污染。
  - `python tools/worktree_tool.py cleanup <PR>`：清理已合併工作樹，內建 `ancestry`、`squash` patch、`rebase` cherry 3 重密碼學等價證明合併驗證，確保未合併代碼絕不被刪除。

### 2. 版本管理與發佈門禁
- **`bump_version.py`（多雛型通用自動升版）**：
  - `python tools/bump_version.py [patch|minor|major|revision]`：依 `tools/project.json` 同步版號檔案並自動注入 `CHANGELOG.md` 區塊。支援 `--dry-run` 與 `--to <version>`。
- **`release_checker.py`（Tag 發佈門禁守衛）**：
  - `python tools/release_checker.py --version <version>`：驗證 Tag 版本與各版號檔案、CHANGELOG 是否完全一致。

### 3. 代碼品質與存儲庫衛生門禁
- **`repo_hygiene.py`（存儲庫衛生與目錄學測試）**：
  - `python tools/repo_hygiene.py [--check]`：驗證根目錄白名單、禁止暫存檔案 (`*.tmp`, `*.log`, `__pycache__`) 與敏感憑證 (`.env`, `*.pem`) 進入 Git，確保測試檔案與文檔目錄學合規。
- **`file_lines.py`（代碼行數統計與單檔上限門禁）**：
  - `python tools/file_lines.py [--check --max-lines 500]`：跨語言統計源代碼行數，阻斷超長「神仙檔 (God File)」，支援輸出 `file_lines.json`。
- **`architecture_graph.py`（真實相依拓撲分析器）**：
  - `python tools/architecture_graph.py [--format mermaid|html|json] [--check]`：透過 AST 解析真實相依關係，自動偵測循環依賴環路與孤兒死碼，輸出 Mermaid 架構圖。
- **`lint_commits.py`（Commit 規範與防搭便車稽核）**：
  - `python tools/lint_commits.py --base origin/main [--strict]`：驗證 Conventional Commits 格式與職責分離。
- **`build_runner.py`（跨語言統一建置調度器）**：
  - `python tools/build_runner.py [lint|test|build|all]`：依據 `tools/project.json` 統一調度 npm、dotnet、python 等建置命令。

### 4. Windows 桌面應用與 MSIX 封裝套件 (`msix-packaging`)
- **`create_dev_cert.ps1`**：建立本機 Code Signing 自簽憑證，支援 `-Install` 一鍵信任至 `CurrentUser\TrustedPeople`。
- **`verify_msix_signature.ps1`**：驗證 `.msix` Authenticode 簽章與 Publisher CN 一致性。

---

## 如何擴充與自訂
1. **新增/修改 Rule**：在 `templates/agent-rules/` 新增或調整 `.md` 模組。
2. **新增/調整 Lint 設定**：在 `templates/lint/` 調整 `eslint.config.mjs`。
3. **新增 Workflow**：在 `templates/github/workflows/` 新增 `.yml` 檔案。
4. **調整 Archetype 與 Feature 結構**：編輯 `presets.json`，在 `archetypes` 或 `features` 中定義包含的 rules、workflows、與專屬 `allowedScopes`。

