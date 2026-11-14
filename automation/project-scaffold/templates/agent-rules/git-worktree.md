# Git Worktree Parallel Development Guidelines

To prevent dependency churn, build artifact conflicts, and environment cache pollution when working across multiple pull requests:

### 1. Dedicated Sibling Worktree Isolation
- Always create feature branches in dedicated sibling worktree directories rather than checking them out in the main working tree:
  ```bash
  python tools/worktree_tool.py start feat/your-feature
  ```
- This automatically creates and switches to `../<repo>-pr-<feature>` branched cleanly from the latest `origin/main`.
- The root repository directory remains permanently pinned to `main` for clean integration inspections.

### 2. Cryptographic Merge Verification Before Cleanup
- Once a PR is merged into `main`, clean up the dedicated worktree using:
  ```bash
  # Step 1: Preview cleanup and receive authorization token
  python tools/worktree_tool.py cleanup <PR_NUMBER>

  # Step 2: Execute cleanup with explicit user authorization
  python tools/worktree_tool.py cleanup <PR_NUMBER> --execute --authorize <TOKEN>
  ```
- The cleanup tool enforces fail-closed integration proof before deletion:
  - **Ancestry check**: PR merge commit reachable from remote main.
  - **Equivalence check**: Verifies squash patch or rebase cherry equivalence.
  - **Dirty state check**: Refuses to remove worktrees containing uncommitted modifications.
