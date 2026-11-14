#!/usr/bin/env python3
"""scripts/install-hooks.py

Installs version-controlled git hooks from scripts/hooks/ into .git/hooks/.
Also configures git commit template if .gitmessage.txt exists.
Cross-platform pure standard library implementation (0 external dependencies).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_git_dir(repo_root: Path) -> Path | None:
    """Locate the actual git directory (handles both normal repos and worktrees)."""
    git_entry = repo_root / ".git"
    if not git_entry.exists():
        return None

    if git_entry.is_dir():
        return git_entry

    # Worktree or submodule: .git is a file containing "gitdir: <path>"
    try:
        content = git_entry.read_text(encoding="utf-8").strip()
        if content.startswith("gitdir:"):
            target_str = content.split("gitdir:", 1)[1].strip()
            target_path = Path(target_str)
            if not target_path.is_absolute():
                target_path = (repo_root / target_path).resolve()
            return target_path if target_path.is_dir() else None
    except OSError:
        pass

    return None


def install_hooks() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    git_dir = resolve_git_dir(repo_root)

    if git_dir is None:
        print("[hooks] Not inside a git repository or worktree. Skipping hook installation.")
        return 0

    target_hooks_dir = git_dir / "hooks"
    target_hooks_dir.mkdir(parents=True, exist_ok=True)

    source_hooks_dir = repo_root / "scripts" / "hooks"
    # Also support hooks/ at repo root or scripts/hooks/
    if not source_hooks_dir.exists():
        source_hooks_dir = repo_root / "hooks"

    hook_names = ["commit-msg", "pre-commit", "pre-push"]
    installed = 0

    if source_hooks_dir.exists() and source_hooks_dir.is_dir():
        for name in hook_names:
            source = source_hooks_dir / name
            if source.exists() and source.is_file():
                target = target_hooks_dir / name
                shutil.copy2(source, target)
                try:
                    # Grant execute permissions on POSIX systems
                    target.chmod(target.stat().st_mode | 0o755)
                except OSError:
                    pass
                print(f"[hooks] Installed hook: {target.relative_to(repo_root) if target.is_relative_to(repo_root) else target}")
                installed += 1

    # Optional: configure git commit template if .gitmessage.txt is present
    gitmessage = repo_root / ".gitmessage.txt"
    if gitmessage.exists():
        try:
            subprocess.run(
                ["git", "config", "commit.template", ".gitmessage.txt"],
                cwd=repo_root,
                check=False,
                capture_output=True,
            )
            print("[hooks] Configured commit.template -> .gitmessage.txt")
        except OSError:
            pass

    print(f"[hooks] Setup complete ({installed} hook(s) installed).")
    return 0


if __name__ == "__main__":
    sys.exit(install_hooks())
