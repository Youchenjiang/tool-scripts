# 🚀 Project Scaffolding System (工程規範一鍵腳手架)

本工具為新專案或既有專案提供**一鍵自動化裝配**：
- **Agent Rules**（授權三階網關、除錯防暴力、MEMORY 協議、Conventional Commits、平台防禦）
- **Git 規範與 Hook**（`.gitignore`、`.gitmessage.txt`、`.editorconfig`、`commit-msg` 驗證鉤子）
- **GitHub Actions CI/CD**（`policy.yml` 看門狗、TruffleHog、CodeQL、OWASP ZAP、CycloneDX SBOM、Dependency-Track、DefectDojo、PR-Agent）
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

### 3. 直接對 Agent 下指令
在新專案開啟對話時，直接告訴 Agent：
> *「請使用 `Script-List/automation/project-scaffold` 的 `web` preset 初始化這個專案」*

Agent 會自動讀取配置並就地生成完整的規範體系。

---

## Presets 設定一覽

| Preset | 適用技術棧 | 包含 Agent 規則 | 包含 GitHub Workflows |
| :--- | :--- | :--- | :--- |
| **`desktop`** | Windows / C# / .NET / WinUI | Core + Memory + Git + .NET Hygiene + Store Release | `policy.yml`, `trufflehog.yml`, `codeql.yml`, `sbom.yml`, `defectdojo-upload.yml` |
| **`web`** | React / Ionic / Vite / Node | Core + Memory + Git + Web Guidelines | `policy.yml`, `trufflehog.yml`, **`codeql.yml`**, **`zap-scan.yml`**, `sbom.yml`, `defectdojo-upload.yml` |
| **`research`** | AI 論文 / 資安挖掘 / 實驗 | Core + Memory + Git | `policy.yml`, `trufflehog.yml`, **`codeql.yml`**, `pr_agent.yml`, `sbom.yml`, `defectdojo-upload.yml` |
| **`minimal`** | 快速小工具 / 單檔腳本 | Core + Memory + Git | `policy.yml` |

---

## 🛡️ 安全測試與 CI Workflows 說明

各專案生成的 GitHub Actions 均具備高容錯與分級防禦設計：

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

### 7. `pr_agent.yml` (AI 自動代碼審查)
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
2. **新增 Workflow**：在 `templates/github/workflows/` 新增 `.yml` 檔案。
3. **調整 Preset**：編輯 `presets.json`，將對應的檔案名稱加入對應的 array 即可。
