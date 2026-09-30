## 📐 Git Discipline & Conventional Commits

### 1. Atomic Commits & Revert Test
- **One purpose per commit**: Never mix functional logic updates with formatting, comment cleanups, or asset moves in a single commit.
- **The Revert Test**: If change A can be reverted without breaking change B, they represent separate purposes and must be committed in separate batches.
- Even within the same file, split logically independent hunks (e.g. using `git add -p`).

### 2. Conventional Commit Formatting
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

### 3. Safety Rules
- **NEVER** run `git push` or `git push --force` automatically. Only commit locally unless explicit push authorization is granted.

### 4. Separation of Concerns & Anti-Free-Riding Rule
- **Orthogonal Categorization, NOT Fixed Quotas**: Commits must be separated by their technical nature, but PRs are never forced into a fixed number of commits (small PRs can have 1-2 commits, larger PRs can have multiple atomic commits).
- **Four Functional Tiers**:
  - **Tier 1 (Purpose & Specifications)**: `SPECIFICATION.md`, ADRs, architecture diagrams, schemas.
  - **Tier 2 (Feature & Implementation)**: Source code, business logic, CLI scripts, test suites.
  - **Tier 3 (Context & Navigation)**: `README.md`, `index.md`, documentation catalogs, changelogs.
  - **Tier 4 (Governance & Session Memory)**: `MEMORY.md`, `docs/HANDOVER.md`, `.agent/*` rules.
- **Strict Anti-Free-Riding**: NEVER bundle Tier 4 governance/memory updates into Tier 2 feature/implementation commits. If a feature commit is reverted, project governance and session memory must remain intact.

### 5. Pull Request Submission Protocol
- **Bypass Shell String Escaping**: Never pass raw markdown text directly via CLI string arguments (e.g. `gh pr create --body "..."`). Always write the PR body to a temporary or standard file and pass `--body-file <path>` to eliminate Windows/PowerShell escape stripping and markdown truncation.
- **Atomic Label Assignment**: Always pass `--label` during the initial `gh pr create` invocation to avoid race conditions with GitHub Actions policy workflows triggering on the `opened` event.
- **Use Dedicated PR Helper**: Prefer using `python tools/pr_helper.py create` or equivalent local tools to validate PR structure and submit safely.
