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

### 5. Branch Scope & Naming Discipline
- **Single Scope Rule**: Every branch must address exactly ONE focused capability or problem.
- **No Compound or Sequence Suffixes**: Never concatenate unrelated topic words, and never use sequence suffixes such as `-pr2` or `phase-1`.
- **Strict Word & Length Limits**:
  - The branch suffix must consist of **2 to 3 words** separated by hyphens (e.g. `feat/user-auth` or `fix/jwt-expiry`).
  - The branch suffix length must **NOT exceed 25 characters** (enforced by `branch_policy.py`).

### 6. Pull Request Toolchain & Submission Protocol
- **Primary PR Toolchain (`pr_tool.py`)**: Use `python tools/pr_tool.py` (or `scripts/pr_tool.py`) as the standard PR operations entry point:
  - `prepare`: Fast preflight verifying branch naming, clean worktree, and commit messages.
  - `push`: Separately authorized branch publication running the pre-push gate.
  - `create`: Separately authorized PR creation with validation against the PR template.
  - `verify`: Combined acceptance checking CI status, SonarCloud quality gate, and open review threads.
  - `diagnose`: Automatic failure log and check run diagnostic extraction.
  - `resolve`: Safe GraphQL-based review thread resolution upon explicit user authorization.
- **PR Content Generator (`pr_helper.py`)**: Use `python tools/pr_helper.py generate` to auto-extract and structure PR body drafts from commit history.
- **Bypass Shell String Escaping**: Never pass raw markdown text directly via CLI string arguments. Always write the PR body to a file and pass `--body-file <path>` to eliminate Windows/PowerShell escape stripping and markdown truncation.
- **Atomic Label Assignment**: Always pass `--label` during initial PR creation to avoid race conditions with GitHub Actions policy workflows triggering on the `opened` event.

### 7. PR Lifecycle Red Line & Intent Interpretation (Non-negotiable)
- **Strict Intent Interpretation**: User instructions such as "修" (fix), "改" (change), or "處理" (handle) mean strictly editing local code and fixing the reported issues. Never interpret them as authorization to close, abandon, recreate, or start a new branch/PR.
- **Never autonomously close or abandon PRs**: An active PR must NEVER be closed (`gh pr close`), abandoned, or replaced with a new branch unless the user explicitly and verbatim commands it (e.g. "關閉 PR", "close PR", "放棄此 PR"). All review findings and CI failures must be resolved by adding atomic follow-up commits to the existing branch.
- **Zero-tolerance for unauthorized PR mutation commands**: Never invoke `gh pr close`, `gh pr edit`, `gh pr merge`, `git push --delete`, or `git push --force` autonomously. Direct PR mutations require explicit, separate, per-operation authorization.

### 8. PR Review Safety & Closure Protocol (Non-negotiable)
- Never create, reply to, edit, repost, or delete GitHub PR review comments or conversation comments. Autonomous comment replies are prohibited. Do not use comments to announce a fix.
- **Mandatory Review Thread Closure Protocol**:
  - Whenever `pr_tool.py verify` reports unresolved review threads, the agent **MUST NEVER report the check as "passed" or "clean"**.
  - Review threads never resolve automatically; after pushing verified fixes and verifying CI is green, the agent **MUST immediately and proactively** list every open thread (whether active or outdated), cite the commit that fixed it, and explicitly request user authorization to resolve that thread ID via `pr_tool.py resolve`.
  - Never wait for the user to notice or remind about open threads.

### 9. Pull Request Merge Authority (Absolute Human-Only Gate)
- **STRICT AGENT BAN ON MERGES**: The AI agent must **NEVER** run `gh pr merge`, call merge APIs, or merge commits into `main` / `master` / protected branches.
- **Agent Lifecycle End**: Once a PR is opened, review feedback is resolved, and CI checks pass, the agent's work on the PR is **COMPLETE**. The agent must report the status to the user and await the user's manual merge.
- **No Blanket Exemption**: Blanket permissions for branch commits and pushes (`git commit`, `git push`) strictly exclude PR merges. Merging to `main` is an irreversible product baseline decision that exclusively belongs to the repository owner.
