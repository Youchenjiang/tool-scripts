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

### 2. 命令列快速執行
```powershell
# 桌面端 (Windows / .NET / Python)
.\init-project.ps1 -Preset desktop -TargetDir "C:\path\to\NewApp" -ProjectName "NewApp"

# 網頁 / 前端全端 (React / Ionic / Vite)
.\init-project.ps1 -Preset web -TargetDir "C:\path\to\WebPortal" -ProjectName "WebPortal"

# AI 研究 / 資安分析
.\init-project.ps1 -Preset research -TargetDir "C:\path\to\Research" -ProjectName "Research"

# 極簡小腳本 / 輕量工具
.\init-project.ps1 -Preset minimal -TargetDir "C:\path\to\Tool" -ProjectName "Tool"
```

---

## Presets 設定一覽

| Preset | 適用技術棧 | 包含 Agent 規則 | 內建工程與治理工具 | 包含 GitHub Workflows |
| :--- | :--- | :--- | :--- | :--- |
| **`desktop`** | Windows / C# / .NET / WinUI | Core + Memory + Git (含職責分離防搭便車) + .NET Hygiene + Store Release | `lint_commits.py`, `pr_helper.py` | `policy.yml`, `trufflehog.yml`, `codeql.yml`, `sbom.yml`, `defectdojo-upload.yml`, `faraday-upload.yml`, `wazuh-health.yml`, `post-merge-security.yml` |
| **`web`** | React / Ionic / Vite / Node | Core + Memory + Git (含職責分離防搭便車) + Web Guidelines | `lint_commits.py`, `pr_helper.py` | `policy.yml`, `trufflehog.yml`, **`codeql.yml`**, **`zap-scan.yml`**, `sbom.yml`, `defectdojo-upload.yml`, `faraday-upload.yml`, `wazuh-health.yml`, `post-merge-security.yml` |
| **`research`** | AI 論文 / 資安挖掘 / 實驗 | Core + Memory + Git (含職責分離防搭便車) | `lint_commits.py`, `pr_helper.py` | `policy.yml`, `trufflehog.yml`, **`codeql.yml`**, `pr_agent.yml`, `sbom.yml`, `defectdojo-upload.yml`, `faraday-upload.yml`, `wazuh-health.yml`, `post-merge-security.yml` |
| **`minimal`** | 快速小工具 / 單檔腳本 | Core + Memory + Git (含職責分離防搭便車) | `lint_commits.py`, `pr_helper.py` | `policy.yml` |

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
* **格式驗證**：推送前本機檢驗 PR 標題、分支命名、與 PR Body 三大章節（`## Summary`, `## Key Changes`, `## Verification`）。
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

## 🛡️ 安全 CI 架構：PR Gate → Post-Merge → Runtime

安全流程依生命週期分成三層。完整設計、平台設定與導入順序請見 [Security CI Architecture](SECURITY-CI.zh-TW.md)。

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
* **檢驗標準**：PR 標題與所有 Commit 首行必須符合 Conventional Commits 格式，長度小於 72 字元，禁止結尾句號，禁止模糊詞彙。
* **分級回報**：
  * ❌ **Blocker (硬性阻擋)**：格式錯誤、超長、帶句號 -> 阻擋 PR 合併。
  * ⚠️ **Warning (軟性提醒)**：缺少 Label、未關聯 Milestone -> 輸出警告提醒補件，不阻擋合併。
  * 📋 **Step Summary**：自動在 Actions Summary 頁面產生 Markdown 表格，清晰條列狀態與修正指引。

### 2. `trufflehog.yml` (機敏金鑰與 Token 洩漏防禦)
* **防禦機制**：啟用 `--only-verified` 深入掃描 800+ 種 API Keys 與私鑰，僅在經端點實名驗證為真實金鑰時才報警，杜絕假陽性干擾。
* **容錯處理**：分開處理 `pull_request` 與 `push` 事件，徹底解決新分支首次推送時引發的自我比對崩潰問題。

### 3. `codeql.yml` (SAST 靜態代碼安全分析)
* **觸發時機**：推送到 main/master、PR 到 main/master、以及**每週一上午定期巡檢**。
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
