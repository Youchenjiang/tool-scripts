#!/usr/bin/env python3
"""
Integration tests for the template pre-push hook's bootstrap rule.

Each test pushes to a local bare repository, so no network access is needed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
HOOK = TEMPLATES / "git" / "hooks" / "pre-push"
LINT = TEMPLATES / "tools" / "lint_commits.py"


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for key in ("ALLOW_DIRECT_PUSH", "PR_BODY_FILE", "CLICKRA_PR_BODY_FILE"):
        env.pop(key, None)
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.local",
         "-c", "init.defaultBranch=main", *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", check=check,
    )


@unittest.skipUnless(shutil.which("git"), "git is required")
class TestPrePushBootstrap(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="test_pre_push_"))
        self.remote = self.tmp / "remote.git"
        git(self.tmp, "init", "--bare", str(self.remote))
        self.work = self.tmp / "work"
        self.work.mkdir()
        git(self.work, "init")
        hooks = self.work / ".git" / "hooks"
        shutil.copy2(HOOK, hooks / "pre-push")
        (self.work / "tools").mkdir()
        shutil.copy2(LINT, self.work / "tools" / "lint_commits.py")
        git(self.work, "remote", "add", "origin", str(self.remote))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit(self, message: str, name: str = "README.md") -> None:
        path = self.work / name
        path.write_text(path.read_text(encoding="utf-8") + "x\n" if path.exists() else "x\n", encoding="utf-8")
        git(self.work, "add", "-A")
        git(self.work, "commit", "-m", message)

    def push(self, refspec: str = "main:main") -> subprocess.CompletedProcess:
        return git(self.work, "push", "origin", refspec, check=False)

    def seed_remote_branch(self, branch: str) -> None:
        """Create a branch on the remote without running the hook under test."""
        git(self.work, "push", "--no-verify", "origin", f"main:{branch}")

    def test_first_push_to_empty_remote_is_allowed(self) -> None:
        self.commit("chore(setup): scaffold project from the minimal template")
        res = self.push()
        self.assertEqual(0, res.returncode, res.stderr)
        self.assertIn("Bootstrap push", res.stdout + res.stderr)

    def test_bootstrap_push_lints_every_commit(self) -> None:
        self.commit("Update stuff")
        self.commit("chore(setup): scaffold project from the minimal template")
        res = self.push()
        output = res.stdout + res.stderr
        self.assertIn("Bootstrap push", output, "the push must get past the main/master rule")
        self.assertIn("Linting commits", output)
        self.assertNotEqual(0, res.returncode, "a bad first commit must still fail lint")

    def test_main_push_blocked_when_remote_has_other_branches(self) -> None:
        self.commit("chore(setup): scaffold project from the minimal template")
        self.seed_remote_branch("feat/existing-work")
        res = self.push()
        self.assertNotEqual(0, res.returncode)
        self.assertIn("prohibited", res.stderr)

    def test_main_push_blocked_when_remote_main_exists(self) -> None:
        self.commit("chore(setup): scaffold project from the minimal template")
        self.seed_remote_branch("main")
        self.commit("docs: add usage notes")
        res = self.push()
        self.assertNotEqual(0, res.returncode)
        self.assertIn("prohibited", res.stderr)


if __name__ == "__main__":
    unittest.main()
