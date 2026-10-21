## 🚀 Trunk-Based Direct Push & Git Discipline

### 1. Trunk-Based Direct Push Model (免開 PR 主幹模式)
- **No Pull Requests Required**: This repository operates on a direct-to-main trunk development model. Standard features, fixes, refactorings, and documentation updates do NOT require creating separate feature branches or opening Pull Requests.
- **Direct Commit & Push**: Work directly on `main` (or master). Once changes are verified and committed locally with atomic discipline, push directly to remote via:
  ```bash
  git push origin main
  ```
- **Pull Remote First**: Always ensure local `main` is synchronized with `origin/main` before starting new edits:
  ```bash
  git pull --ff-only origin main
  ```

### 2. Atomic Commits & The Revert Test (嚴格原子化提交)
Direct-push mode demands the highest standard of commit discipline, because commits enter `main` immediately:
- **One purpose per commit**: Never mix functional logic updates with formatting, comment cleanups, documentation, or rule adjustments in a single commit.
- **The Revert Test**: If change A can be reverted without breaking change B, they represent separate purposes and MUST be committed in separate commits.
- **Strict Staging**: NEVER run bulk staging (`git add .` or `git add -A`). Always stage explicitly by target file or path.

### 3. Conventional Commit Formatting
All commit messages must strictly follow the Conventional Commits format:
```
<type>(<scope>): <subject>
or
<type>: <subject>

1. <Numbered English detail line 1>
2. <Numbered English detail line 2>
```

- **Allowed Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`, `security`
- **Rules**:
  - Header length: Maximum 72 characters.
  - No trailing period (`.`) at the end of the subject.
  - Avoid vague descriptions (`update`, `misc`, `fix bug`, `changes`).
  - Body must be a numbered list in English explaining technical rationale.

### 4. Separation of Concerns & Anti-Free-Riding Rule
- **Four Functional Tiers**:
  - **Tier 1 (Purpose & Specifications)**: `SPECIFICATION.md`, ADRs, architecture diagrams, schemas.
  - **Tier 2 (Feature & Implementation)**: Source code, scripts, modules, test suites.
  - **Tier 3 (Context & Navigation)**: `README.md`, `README.zh-TW.md`, documentation catalogs, changelogs.
  - **Tier 4 (Governance & Session Memory)**: `MEMORY.md`, `.agent/*` rules.
- **Strict Anti-Free-Riding**: NEVER bundle Tier 4 governance/memory updates into Tier 2 feature/implementation commits. If a feature commit is reverted, project governance and session memory must remain intact.

### 5. Push Safety & Prohibitions
- **Verify Before Push**: Always run local tests and lint checks before pushing to `origin/main`.
- **PROHIBITED COMMANDS**:
  - NEVER execute `git push --force` or `git push -f` on `main`.
  - NEVER execute `git push --delete origin main`.
  - Fast-forward only: if push is rejected due to remote divergence, pull and rebase or fast-forward cleanly.
