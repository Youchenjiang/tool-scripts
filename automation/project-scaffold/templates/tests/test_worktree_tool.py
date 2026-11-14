import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import worktree_tool


class BranchPatternTests(unittest.TestCase):
    def test_valid_branches(self):
        valid = [
            "feat/user-auth",
            "feature/awesome-thing",
            "fix/null-pointer",
            "refactor/split-module",
            "docs/update-readme",
            "test/runner-gate",
            "chore/deps-bump",
        ]
        for b in valid:
            self.assertTrue(bool(worktree_tool.BRANCH_PATTERN.fullmatch(b)), f"Expected '{b}' to be valid")

    def test_invalid_branches(self):
        invalid = [
            "main",
            "feat/",
            "feature/UpperCase",
            "unknown/feature",
            "feat/with_underscore",
            "feat/trailing-period.",
        ]
        for b in invalid:
            self.assertFalse(bool(worktree_tool.BRANCH_PATTERN.fullmatch(b)), f"Expected '{b}' to be invalid")


class CreateWorktreeTests(unittest.TestCase):
    @patch("worktree_tool.get_repo_state")
    @patch("worktree_tool.run_git")
    @patch("worktree_tool.git_output")
    def test_create_worktree_preview_mode(self, mock_output, mock_run, mock_state):
        mock_state.return_value = {
            "root": "/repos/my-app",
            "repo_name": "my-app",
            "remote_main": "a" * 40,
        }
        mock_run.return_value = MagicMock(returncode=1)  # show-ref fails (branch does not exist)
        mock_output.return_value = ""  # ls-remote empty

        with patch("pathlib.Path.exists", return_value=False):
            res = worktree_tool.create_worktree("feat/new-ui", execute=False)

        self.assertIn("preview", res)
        self.assertIn("authorize", res)
        self.assertEqual("feat/new-ui", res["preview"]["branch"])
        mock_run.assert_called()  # Checked show-ref, did not call worktree add

    @patch("worktree_tool.get_repo_state")
    @patch("worktree_tool.run_git")
    @patch("worktree_tool.git_output")
    def test_create_worktree_execute_requires_matching_token(self, mock_output, mock_run, mock_state):
        mock_state.return_value = {
            "root": "/repos/my-app",
            "repo_name": "my-app",
            "remote_main": "a" * 40,
        }
        mock_run.return_value = MagicMock(returncode=1)
        mock_output.return_value = ""

        with patch("pathlib.Path.exists", return_value=False):
            with self.assertRaisesRegex(ValueError, "matching authorization token"):
                worktree_tool.create_worktree("feat/new-ui", execute=True, authorize="wrong-token")

    def test_create_worktree_rejects_invalid_branch(self):
        with self.assertRaisesRegex(ValueError, "Invalid branch name"):
            worktree_tool.create_worktree("bad_branch_name")


class CleanupWorktreeTests(unittest.TestCase):
    @patch("worktree_tool.run_gh")
    @patch("worktree_tool.get_repo_state")
    def test_cleanup_rejects_unmerged_pr(self, mock_state, mock_gh):
        mock_state.return_value = {"root": "/repos/my-app", "remote_main": "a" * 40}
        mock_gh.return_value = {"state": "OPEN"}

        with self.assertRaisesRegex(ValueError, "state is 'OPEN'"):
            worktree_tool.cleanup_worktree(42)

    @patch("worktree_tool.run_gh")
    @patch("worktree_tool.get_repo_state")
    @patch("worktree_tool.is_ancestor")
    def test_cleanup_rejects_unreachable_merge(self, mock_ancestor, mock_state, mock_gh):
        mock_state.return_value = {"root": "/repos/my-app", "remote_main": "a" * 40}
        mock_gh.return_value = {
            "state": "MERGED",
            "headRefName": "feat/done",
            "headRefOid": "b" * 40,
            "mergeCommit": {"oid": "c" * 40},
        }
        mock_ancestor.return_value = False

        with self.assertRaisesRegex(ValueError, "not reachable from remote main"):
            worktree_tool.cleanup_worktree(42)

    @patch("worktree_tool.run_gh")
    @patch("worktree_tool.get_repo_state")
    @patch("worktree_tool.is_ancestor")
    @patch("worktree_tool.verify_merge_equivalence")
    @patch("worktree_tool.get_worktree_list")
    @patch("worktree_tool.git_output")
    def test_cleanup_preview_mode(self, mock_out, mock_wts, mock_mode, mock_anc, mock_state, mock_gh):
        mock_state.return_value = {"root": "/repos/my-app", "remote_main": "a" * 40}
        mock_gh.return_value = {
            "state": "MERGED",
            "headRefName": "feat/done",
            "headRefOid": "b" * 40,
            "mergeCommit": {"oid": "c" * 40},
        }
        mock_anc.return_value = True
        mock_mode.return_value = "squash"
        mock_wts.return_value = [{"branch": "refs/heads/feat/done", "worktree": "/repos/my-app-pr-done"}]
        mock_out.return_value = ""  # clean status

        res = worktree_tool.cleanup_worktree(42, execute=False)
        self.assertIn("preview", res)
        self.assertIn("authorize", res)
        self.assertEqual("squash", res["preview"]["merge_mode"])
        self.assertEqual("feat/done", res["preview"]["branch"])


class ListWorktreesTests(unittest.TestCase):
    @patch("worktree_tool.git_output")
    def test_list_worktrees(self, mock_out):
        porcelain = (
            "worktree /repos/my-app\nHEAD abcdef123456\nbranch refs/heads/main\n\n"
            "worktree /repos/my-app-pr-test\nHEAD 123456abcdef\nbranch refs/heads/feat/test\n"
        )
        mock_out.return_value = porcelain
        items = worktree_tool.list_worktrees()
        self.assertEqual(2, len(items))
        self.assertEqual("main", items[0]["branch"])
        self.assertEqual("feat/test", items[1]["branch"])


if __name__ == "__main__":
    unittest.main()
