# 🚀 Project Scaffolding System (工程規範一鍵腳手架)

本工具為新專案或既有專案提供**一鍵自動化裝配**：
- **Agent Rules**（授權三階網關、除錯防暴力、MEMORY 協議、Conventional Commits、平台防禦）
- **Git 規範與 Hook**（`.gitignore`、`.gitmessage.txt`、`.editorconfig`、`commit-msg` 驗證鉤子）
- **GitHub Actions CI/CD**（PR Gate、CycloneDX SBOM、Dependency-Track、DefectDojo、Greenbone/OpenVAS、Faraday、Wazuh、PR-Agent）
- **協作模板**（`pull_request_template.md`、`dependabot.yml`、`SECURITY.md`）

---

## 快速使用

### 1. 互動式選單
直接在目標專案目錄（或從本目錄指向目標專案）執行：
```powershell
.\init-project.ps1
```
互動式選單會引導您選擇 **Archetype（專案雛型）** 以及是否啟用 **可選擴充模組（Features）**。

### 2. 命令列快速執行
```powershell
# 網頁 / 前端全端 (React / Ionic / Vite) + 啟用代碼規範與鏈式 PR 指引
.\init-project.ps1 -Archetype web-spa -Features strict-linting,chained-prs -TargetDir "C:\path\to\WebPortal" -ProjectName "WebPortal"

# 後端 API 服務 (Node / Express / FastAPI) + 啟用全部模組
.\init-project.ps1 -Archetype backend-api -AllFeatures -TargetDir "C:\path\to\ApiServer" -ProjectName "ApiServer"

# 桌面端 (Windows / C# / .NET / WinUI)
.\init-project.ps1 -Archetype desktop-app -TargetDir "C:\path\to\NewApp" -ProjectName "NewApp"

# AI 研究 / 資安實驗室
.\init-project.ps1 -Archetype sec-research -TargetDir "C:\path\to\Research" -ProjectName "Research"

# 極簡小工具 / 單檔腳本 (無額外擴充模組)
.\init-project.ps1 -Archetype minimal -NoFeatures -TargetDir "C:\path\to\Tool" -ProjectName "Tool"
```
*(向後相容：亦可繼續使用 `-Preset` 參數傳入舊有名稱如 `web`、`desktop`、`research`。)*

### 3. 直接對 Agent 下指令
在新專案開啟對話時，直接告訴 Agent：
> *「請使用 `Script-List/automation/project-scaffold` 的 `web-spa` archetype（啟用 `strict-linting` 與 `chained-prs`）初始化這個專案」*

Agent 會自動讀取配置並就地生成完整的規範體系與客製化 Scopes。

---

## 🏗️ 雙層架構設計 (Archetypes & Features)

腳手架採用 **「基礎專案雛型 (Archetype) ➔ 可選擴充模組 (Modular Features)」** 的兩層架構：

### 1. 基礎雛型 (Archetypes)

| Archetype | 相容別名 | 適用場景 | 自動注入 CI Scopes | 專屬預載規範 / 設定 |
| :--- | :--- | :--- | :--- | :--- |
| **`web-spa`** | `web`, `frontend` | React, Ionic, Vue, Vite, SPA 前端專案 | `app, ui, style, render, sim, test, docs, ci, deps, spec, rules, setup, quality` | Web Guidelines、`eslint.config.mjs`、npm prepare hook |
| **`backend-api`** | `api`, `server`, `service` | Node/Express, Nest, FastAPI, Go 服務 | `api, auth, db, models, routes, test, docs, ci, deps, spec, rules, setup, quality, sec` | Backend Guidelines |
| **`desktop-app`** | `desktop`, `winui`, `wpf` | Windows, C#, .NET, WinUI, Electron | `app, ui, winui, core, test, docs, ci, deps, spec, rules, setup, quality, release` | .NET Hygiene, Store Release |
| **`sec-research`** | `research`, `security`, `lab` | AI 論文, 漏洞分析, PoC 實驗 | `agent, audit, rules, poc, exp, test, docs, ci, deps, spec, setup, quality, sec` | PR-Agent, Security Audit rules |
| **`minimal`** | `tool`, `script`, `cli` | 輕量腳本, 小型命令列工具 | `core, cli, test, docs, ci, deps, setup` | 僅核心 Commit 規範與 policy.yml |

### 2. 可選擴充模組 (Modular Features / Add-ons)

| Feature | 模組名稱 | 功用與配置內容 |
| :--- | :--- | :--- |
| **`strict-linting`** | 嚴格代碼規範 | 部署 `eslint.config.mjs`，內建 TypeScript 嚴格規則、SonarCloud S3358 巢狀三元運算式防禦 (`no-nested-ternary`)、變數命名長度規範 (`id-length`)、物件非空斷言防禦 (`no-non-null-assertion`)。 |
| **`chained-prs`** | 鏈式 PR 工作流 | 部署 `chained-prs.md` 規則，規範滾動 Rebase（Rolling Rebase）技巧、分支推動決策樹（普通 append vs force-with-lease）、GitHub 倉儲設定（關閉 squash merge、Rulesets 配置）。 |
| **`sec-enterprise`** | 企業級資安平台對接 | 部署完整 Post-Merge 安全驗證工作流（Dependency-Track, DefectDojo, Faraday, Wazuh, post-merge-security）。適合企業正式環境使用。 |

### 3. 自動化 Git Hook 生命週期 (npm prepare)
- 當目標專案包含 `package.json` 時，腳手架會自動於 `scripts` 中注入 `"prepare": "node scripts/install-hooks.mjs"`。
- 同步產出 `scripts/install-hooks.mjs` 與版本庫納管的 `scripts/hooks/commit-msg`。
- 任何團隊成員或 AI 代理人執行 `npm install` 時，本機 `.git/hooks/commit-msg` 便會自動部署就緒，免除手動安裝步驟。

---

## 🛡️ 安全 CI 架構：PR Gate → Post-Merge → Runtime

安全流程依生命週期分成三層。完整設計、平台設定與導入順序請見 [Security CI Architecture](SECURITY-CI.md)。

| 階段 | 自動執行內容 | 定位 |
| :--- | :--- | :--- |
| **PR Gate** | Policy、TruffleHog、CodeQL、SBOM；research preset 另有 PR-Agent | 合併前找出程式碼、Secret、規範與供應鏈問題 |
| **Post-Merge Security** | Dependency-Track、Staging readiness、ZAP、OpenVAS、DefectDojo、Faraday | main/master 更新後驗證正式 SBOM 與部署環境 |
| **Runtime Monitoring** | Wazuh 24/7；CI 驗證 Agent health | 確認部署後端點監控持續在線 |

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
* **觸發時機**：每次開 PR 或更新 PR。
* **檢驗標準**：PR 標題與所有 Commit 首行必須符合 Conventional Commits 格式，長度小於 72 字元，禁止結尾句號，禁止模糊詞彙。
* **分級回報**：
  * ❌ **Blocker (硬性阻擋)**：格式錯誤、超長、帶句點 -> 阻擋 PR 合併。
  * ⚠️ **Warning (軟性提醒)**：缺少 Label、未關聯 Milestone -> 輸出警告提醒補件，不阻擋合併。
  * 📋 **Step Summary**：自動在 Actions Summary 頁面產生 Markdown 表格，清晰條列每個 Commit 狀態與修正指引。

### 2. `trufflehog.yml` (機敏金鑰與 Token 洩漏防禦)
* **觸發時機**：每次 Push 與 Pull Request。
* **防禦機制**：啟用 `--only-verified` 深入掃描 800+ 種 API Keys 與私鑰，僅在經端點實名驗證為真實金鑰時才報警，杜絕假陽性干擾。
* **容錯處理**：分開處理 `pull_request`（比對 base_ref）與 `push` 事件，徹底解決新分支首次推送時引發的自我比對崩潰問題。

### 3. `codeql.yml` (SAST 靜態代碼安全分析)
* **觸發時機**：每次推送到主要分支 (main/master)、PR 到主要分支、以及**每週一上午定期巡檢**。
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

### 9. `post-merge-security.yml` (Merge 後安全驗證)
* **觸發時機**：程式 Push / Merge 進 `main` 或 `master`，也可手動執行。
* **Staging Gate**：若有 `STAGING_URL`，最多等待 5 分鐘確認部署端點可連線，再開始動態掃描。
* **Web DAST**：對 Staging 執行 ZAP Baseline，報告同時可送 DefectDojo 與 Faraday。
* **Infrastructure Scan**：若 Greenbone 設定完整，透過 GMP over SSH 啟動既有 OpenVAS task、等待完成並保存 XML，之後同時送 DefectDojo 與 Faraday。
* **Runtime Check**：最後呼叫 Wazuh health workflow，確認部署環境 Agent 仍在線。

### 10. `pr_agent.yml` (AI 自動代碼審查)
* **觸發時機**：PR 建立或留言互動。
* **配置需求**：需在 Repo Secrets 設置 `OPENAI_KEY` 或 `SILICONFLOW_API_KEY`。
* **韌性防護**：若未配置 Secret 會輸出 GitHub Notice 並優雅跳過；設有 `continue-on-error: true`，第三方 AI API 服務超時或停機時**絕不阻擋**正常代碼合併。

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

## 如何擴充與自訂
1. **新增/修改 Rule**：在 `templates/agent-rules/` 新增或調整 `.md` 模組。
2. **新增/調整 Lint 設定**：在 `templates/lint/` 調整 `eslint.config.mjs`。
3. **新增 Workflow**：在 `templates/github/workflows/` 新增 `.yml` 檔案。
4. **調整 Archetype 與 Feature 結構**：編輯 `presets.json`，在 `archetypes` 或 `features` 中定義包含的 rules、workflows、與專屬 `allowedScopes`。
