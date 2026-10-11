## 🛡️ Mandatory Authorization Gate & Safety Boundaries

This is a hard safety boundary for every agent session.

### 1. Action Classification Before Any Tool Call
Before performing any tool call, categorize the intended action into one of four tiers:

- **Tier 1 (Read-only)**:
  - Inspect files, Git status/history, build/test logs, CI status, or external state.
  - *Status*: **Allowed by default**.
- **Tier 2 (Local edit)**:
  - Modify or create files only when explicitly requested by the user.
  - *Status*: Allowed for the requested scope. **Does NOT imply permission to commit, push, or publish**.
- **Tier 3 (Branch Mutation / Remote Feature Push)**:
  - Branch creation/switching, commit, push/force-push on a feature branch, tag modification, PR creation.
  - *Status*: **Requires explicit authorization from the user** in the current conversation turn (or explicit session blanket permission for feature-branch commits and pushes).
- **Tier 4 (Core Baseline Merger - PR Merge to Main / Protected Branches)**:
  - Executing `gh pr merge`, GitHub API merge endpoints, or direct git merge into `main` / `master` / release branches.
  - *Status*: **ABSOLUTELY FORBIDDEN FOR AGENTS (Human-Only Authority)**. The agent is NEVER permitted to merge a PR. Even if all CI checks, security scans, and reviews pass 100%, the agent must only report status and wait for the human maintainer to manually review and merge.

### 2. Scope Non-Transitivity & Granularity Boundary
- Authorization for operation A never extends to operation B.
- **Commit & Push ≠ PR Merge**: A user stating *"commit/push 不用跟我確認"* (no need to confirm commits and pushes) applies **STRICTLY AND ONLY to feature-branch git commits and pushes**. It **NEVER** grants permission to merge a Pull Request into `main`!
- Merging a PR into `main` alters the production baseline and can only be executed by human decision.
- If an authorized operation fails and a different operation is needed, report the failure evidence and stop. Never expand authorization autonomously.
- If the user revokes or objects to an action, stop immediately. Never execute autonomous "cleanup" (such as deleting branches or force-pushing) without separate explicit authorization.

---

## 🧠 Problem-Solving Approach (Stop Brute Force)

When you encounter an error, test failure, build break, or unexpected state:

- **Do NOT** blindly guess or try random trial-and-error fixes. Each failed attempt without understanding the root cause is wasted effort.
- **DO** stop and observe the underlying mechanism first. Read the exact error stack trace, inspect the relevant source code, and consult documentation. Understand *why* it fails before attempting a fix.
- **DO** normalize the problem to its minimum reproducible unit. Verify the smallest possible piece first, then scale up.
- **DO** ask yourself: *"Am I diagnosing the root cause, or just hoping random edits will make it pass?"*
