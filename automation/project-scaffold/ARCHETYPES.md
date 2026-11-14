# 範本（Archetype）現況與修正計劃

`init-project.ps1` 開專案時要選一個範本。這份文件說明六個範本目前是什麼、有什麼問題，
以及接下來按什麼順序修。

## 一、現況：六個範本實際產出什麼

| 範本 | 給誰用 | commit 分類字 | GitHub 檢查 | AI 規則檔 | 特別之處 |
|---|---|---|---|---|---|
| `web-spa` | 網站、前端 | 13 個 | 3 支 | 4 份 | 多一份前端規範、預設 ESLint |
| `backend-api` | 伺服器、API | 11 個 | 4 支 | 3 份 | 多一個套件清單檢查 |
| `desktop-app` | Windows、.NET | 10 個 | 4 支 | 5 份 | 多 .NET 與上架 Store 規範 |
| `sec-research` | 資安研究、PoC | 10 個 | 6 支 | 3 份 | 多弱點掃描與 AI 審查 |
| `minimal` | 小工具 | 6 個 | 1 支 | 3 份 | 幾乎只有 commit 規範 |
| `script-tool` | 零散腳本的大雜燴 | 14 個 | 3 支 | 3 份 | 不開 PR、直接推 main |

工具程式：前五種裝同一組 14 個（commit 檢查、分支規範、PR 流程）；`script-tool` 只裝 1 個。

## 二、問題（按嚴重度）

### 問題 1：本地檢查與 CI 用的是兩份互相衝突的分類字清單

- CI 用範本自己的清單（寫進 `policy.yml`）。
- 本地 `tools/lint_commits.py` 用的是**另一份固定清單**，而且裡面還有 `tapster`、`fluent`、
  `launcher`、`tray`、`ctfd`、`labs` 這些舊專案的名字。
- 產生一個 `web-spa` 專案實測：
  - `feat(app): ...`（web-spa 自己文件寫的分類字）→ CI 通過、**本地拒絕**。
  - `feat(tapster): ...`（別人的專案名）→ CI 拒絕、**本地通過**。
- push 前的檢查會匯入本地那份清單，所以「照專案設定做」和「照本地檢查做」不可能同時成立。

### 問題 2：六個範本不是分類，是六個範例

- 不互斥：一個網站同時有前端和後端 → 只能選一個，另一個的設定就沒了。
- 邊界模糊：`minimal` 和 `script-tool` 都是「小工具」，差別只是要不要走 PR。
- 有缺口：要發佈到 npm 的套件、資料分析、純文件庫，六個都不太合身。
- 沒有判斷規則：選錯不會報錯，只會拿到一整套不對的設定（例如選 `tool` 會變成直推 main）。

### 問題 3：「只差在 commit 分類字」這句話不成立

實際差異還包含：檢查支數（1～6）、規則檔（3～5）、有沒有 push 前檢查（`script-tool` 沒有）、
有沒有 PR 模板、有沒有自動更新依賴、工具 14 個 vs 1 個，以及程式碼裡直接判斷 `script-tool`
就改成直推行為。

反過來說，**真正該不同的地方六種都一樣**：沒有任何一個範本會建置或測試你的程式。

### 問題 4：文件與程式不一致

- 說明書列的分類字（`models`、`routes`、`winui`、`agent`、`audit`、`release`、`cli`、`deps`…）
  多半不在實際清單裡；照著用會被 CI 擋。
- 說明書說 `tool` / `script` 是 `minimal` 的別名，程式卻指向 `script-tool`。
- 說明書廣告的 `frontend`、`winui`、`wpf`、`security`、`lab`、`cli` 別名根本不存在，用了會直接報錯。

## 三、修正方向

### 設計決定

1. **範本定位改成「起手包」**，不假裝是互斥分類。保留六個，但說明「選最接近的，差異可再用開關調整」。
2. **真正的差異軸只有三條**，全部變成範本上的設定欄位：
   - `build`：這個型別用什麼指令做 lint / test / build（沒有就留空，不前進也不報錯）。
   - `release`：這個型別怎麼發佈、版本號寫在哪個檔、要同步哪些檔（沒有就整段跳過）。
   - `flow`：走 PR 還是直接推 main（目前 `script-tool` 的行為寫死在程式碼裡，改成讀欄位）。
3. **commit 分類字是「領域」的副產品**，由範本提供預設值，且**只有一份**：產生專案時同時寫進
   `policy.yml` 與 `lint_commits.py`，本地與 CI 不可能再分岔。
4. **不新增第七、第八個範本**。需要組合時用開關（例如 `web-spa` + 後端 API 的檢查），
   而不是再長一個分類。

### 分階段計劃

每階段一個 commit，可獨立 revert；每階段都有可執行的驗證。

**第 0 階段：止血（先讓規則一致，不動架構）**

1. `lint_commits.py` 的分類字改成 placeholder，由 `init-project.ps1` 依範本注入，與 `policy.yml`
   用同一份來源。
2. 從注入清單與 `lint_commits.py` 預設值中移除舊專案名稱（`tapster`、`fluent`、`launcher`、
   `tray`、`macro`、`ctfd`、`labs`、`challenge`、`plugin`、`deepsource`、`links`、`memory`、
   `knowledge`、`tracks`、`practice`）。
3. `pr_verification.py` 的 required check 名稱改成由設定提供，移除 `Build Clickra.Core`、
   `DeepSource: Python` 這類寫死的名字。
4. 修文件：說明書的範本表改由 `presets.json` 產生（或加測試斷言兩者一致）。

驗證：產生六個專案，對每個範本自己的分類字跑本地檢查與 CI 正則，兩邊結果必須相同；
`feat(app)` 在 `web-spa` 通過、`feat(tapster)` 全部拒絕。

**第 1 階段：把三條軸變成資料**

- 在 `presets.json` 每個範本加上 `build` / `release` / `flow` 欄位（先只有值，還沒有消費者）。
- 產生專案時輸出 `tools/project.json`，讓後面的工具與 CI 讀同一份。

驗證：六個專案的 `project.json` 內容與 `presets.json` 一致；沒有新增任何行為。

**第 2 階段：產品 CI**

- 新增 `ci.yml` 範本，指令由 `build` 欄位填入；required check 名稱固定一個。
- 沒有程式碼的專案（剛 scaffold 完）要能通過，不能因為沒有測試就紅燈。

驗證：六個專案產生後 `ci.yml` 可解析；指令與 `build` 相符；空的專案不會失敗。

**第 3 階段：push 前檢查補齊**

- `pre-push` 依序跑：commit 規範 → 專案測試 → 建置（依 `build` 欄位）。
- 為 `script-tool` 補一個等價的 push 前檢查（它現在完全沒有，直推 main 反而更危險）。

驗證：故意讓測試失敗時 push 被擋；`script-tool` 也有同樣保護。

**第 4 階段：發佈生命週期（先只做桌面）**

- 版本檢查（tag 已存在、版本檔與 changelog 同步）讀 `release` 欄位；沒設定的範本整段跳過。
- 先實作 `desktop-app`，`web-spa` / `backend-api` 等各自的發佈路徑確定後再做。

驗證：桌面專案改了發佈相關檔案但沒升版本時被擋；其他五個範本不受影響。

## 四、已定稿的決定：工作流程自主選擇 (Flow Selection)

原本的爭議是：`tool` / `script` 要偏向「直推 main」還是「走 PR」。
**已定稿方案**：將工作流程抽成**獨立的一級選項**，不再與範本死綁：

- CLI 新增參數 `-Flow <pr|direct-push|trunk>`。
- 互動模式在 Stage 1 選完範本後，直接進入 **Stage 2: Git Workflow Mode** 供使用者自選：
  - `[1] pr`：Pull Request 審查流程（分行開發、開 PR、PR 模板與審查門禁工具）。
  - `[2] direct-push`：Direct Trunk Push（免開 PR、原子提交直接推 main、自動設定 `repo.directPush true`）。
- 範本在 `presets.json` 中保留其推薦預設（例如 `script-tool` 預設 `direct-push`，其他預設 `pr`），但使用者擁有最終選擇權。

## 五、進度追蹤

- [x] **第 0 階段：止血（已完成）**
  - [x] `lint_commits.py` 分類字改為 placeholder，由 `init-project.ps1` 依範本動態注入，與 `policy.yml` 完全同源。
  - [x] 徹底清理 `lint_commits.py` 與各範本殘留的舊專案名稱（`tapster`, `fluent`, `ctfd` 等）。
  - [x] `pr_verification.py` 移除寫死的 `Build Clickra.*` 等專屬 checks，改為通用門禁並支援 `PR_REQUIRED_CHECKS` 環境變數。
  - [x] 實作 `-Flow` 參數與互動式工作流程選擇（開 PR vs 免開 PR 直推）。
  - [x] 通過 142 項單元測試全數驗證。
- [x] **第 1 階段：把三條軸變成資料（已完成）**
  - [x] 在 `presets.json` 每個範本定義結構化 `build` / `release` / `flow` 資料欄位。
  - [x] 專案生成時統一輸出 `tools/project.json`（UTF-8 without BOM），作為本地工具與 CI 共同遵循之架構契約。
  - [x] 針對全部 6 種 Archetype 自動執行測試，斷言 `tools/project.json` 內容與 `presets.json` 100% 精準吻合。
- [x] **第 2 階段：產品 CI（已完成）**
  - [x] 新增 `ci.yml` 範本，統一固定 required check 名稱為 `Continuous Integration`。
  - [x] `init-project.ps1` 依範本之 `build` 欄位動態注入對應之建置/測試步驟（`npm` / `dotnet` / `python` / baseline）。
  - [x] 設計防禦機制，剛初始化或無程式碼之專案保證綠燈通過，不因無測試而紅燈。
  - [x] 針對 6 大 Archetype 全數通過 YAML 解析與指令映射驗證。
- [ ] **第 3 階段：push 前檢查補齊**
- [ ] **第 4 階段：發佈生命週期**

## 六、不在這次範圍

- 不新增範本，也不為單一範本寫專屬工具分支。
- 不改 Clickra 本身。
- 不改已經產生出去的專案；它們要重跑 `init-project.ps1 -Force` 才會拿到新設定。
