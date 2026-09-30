## 🔄 串接 PR 工作流程與儲存庫規範 (Chained / Stacked PRs)

當功能規模較大或需要拆解為多個相依 PR 依序合入時，必須遵循 **Rolling Rebase** 策略，避免使用過長、難以審查的大分支。

```
main ──▶ merge PR #1 ──▶ merge PR #2 ──▶ merge PR #N
              ↑                ↑                ↑
     feature/foo     feature/bar      feature/baz
```

---

### 1. 每一輪的標準操作步驟

1. **拉取最新主幹**：前一個 PR 合併至 `main` 後，立即更新本地：
   ```bash
   git fetch origin
   ```
2. **滾動 Rebase**：將下一個功能分支 rebase 至最新的 `origin/main`：
   ```bash
   git rebase origin/main feature/<next-name>
   ```
3. **本地全體驗證**：
   ```bash
   npm run typecheck && npm run test:policy && npm test
   ```
4. **推播判斷準則（避免不必要的 Force Push）**：
   - **純追加 Commit**（如在已開啟但尚未合併的 PR 補上一筆修正）：這是 Fast-forward，**一律使用一般 push**：
     ```bash
     git push origin feature/<next-name>
     ```
   - **剛 Rebase 過、Commit SHA 已改寫**（`main` 前進導致歷史改變）：遠端舊提交已被重寫，此時才使用 lease：
     ```bash
     git push --force-with-lease origin feature/<next-name>
     ```
   - **不確定時**：先嘗試一般 push，唯有被拒絕（non-fast-forward）且確認是 rebase 造成時，才改用 lease：
     ```bash
     git push origin feature/<next-name> || git push --force-with-lease origin feature/<next-name>
     ```
   - **嚴格禁忌**：**永遠不要使用無保護的 `--force`**，以免覆蓋他人工作。
5. **PR 標靶設定**：在 GitHub 上 PR 的 **Base branch 一律設為 `main`**（切勿設為前一個功能分支）。

---

### 2. GitHub 儲存庫必要設定 (Repository Settings)

Rolling rebase 依賴於「每個 PR 的 Commit 保持原樣進入 `main`」，因此儲存庫必須配置以下項目：

1. **嚴禁 Squash Merge**：
   - Squash 會把整個 PR 壓縮成單一 Commit，導致 `main` 不包含分支原本的 Commit SHA，下一輪分支 rebase 時無法識別已合併提交，產生大量虛假衝突。
   - **設定位置**：Repo → Settings → General → Pull Requests → 取消勾選 **Allow squash merging**，僅保留 **Merge commit** 或 **Rebase and merge**。
2. **Main 分支保護 (Rulesets)**：
   - 建立 Ruleset：強制所有變更經由 PR、禁止直接 Push、禁止 Force Push、禁止刪除 `main`。
3. **Required Status Checks 的 Job Name 陷阱**：
   - Required check 必須填寫 GitHub Actions 顯示的 **Job Name**（例如 `Typecheck, build, and unit tests`），而非內部的 Job ID。
   - 該 Check 關聯的 Workflow 必須已經存在於 `main` 分支中，否則所有 PR 會陷入永久 `BLOCKED`。
4. **合併後自動清理**：
   - 啟用 **Automatically delete head branches**，保持遠端分支整潔。
