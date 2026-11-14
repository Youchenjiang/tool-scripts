#!/usr/bin/env python3
"""
Unit tests for tools/lint_commits.py validating commit message syntax, length, vagueness, and separation of concerns.
"""

import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import lint_commits


class TestValidateCommit(unittest.TestCase):
    """Test validation of commit subjects and separation of concerns."""

    def test_valid_commits(self):
        sample_scope = lint_commits.ALLOWED_SCOPES[0] if lint_commits.ALLOWED_SCOPES else "core"
        valid = [
            ("sha1", f"feat({sample_scope}): implement new feature", ["src/main.py"]),
            ("sha2", "perf(core): optimize payload with trimming", ["scripts/build.ps1"]),
            ("sha3", "docs(docs): update architecture documentation", ["docs/architecture.md"]),
            ("sha4", "chore(deps): bump package versions", ["package.json"]),
        ]
        for sha, subj, files in valid:
            errors, warnings = lint_commits.validate_commit(sha, subj, files, strict=True)
            self.assertEqual(errors, [], f"Unexpected errors for '{subj}': {errors}")
            self.assertEqual(warnings, [], f"Unexpected warnings for '{subj}': {warnings}")

    def test_trailing_period(self):
        sha = "sha1"
        subj = "feat(core): implement direct input simulation."
        errors, _ = lint_commits.validate_commit(sha, subj, ["src/program.cs"], strict=True)
        self.assertTrue(any("句號" in err for err in errors))

    def test_subject_too_long(self):
        sha = "sha1"
        subj = "perf(core): optimize package footprint with trimming and assembly whitelist"
        self.assertGreater(len(subj), 72)
        errors, _ = lint_commits.validate_commit(sha, subj, ["scripts/build.ps1"], strict=True)
        self.assertTrue(any("超過上限 72 字元" in err for err in errors))

    def test_vague_description(self):
        sample_scope = lint_commits.ALLOWED_SCOPES[0] if lint_commits.ALLOWED_SCOPES else "core"
        vague_examples = [
            f"fix({sample_scope}): fix bug",
            f"chore({sample_scope}): update",
            f"refactor({sample_scope}): misc",
            f"refactor({sample_scope}): changes",
            f"feat({sample_scope}): stuff",
        ]
        for subj in vague_examples:
            errors, _ = lint_commits.validate_commit("sha1", subj, ["file.cs"], strict=True)
            self.assertTrue(any("描述過於空泛" in err for err in errors), f"Expected vague error for '{subj}'")

    def test_separation_of_concerns_free_riding(self):
        # Mixing governance doc (memory.md) with code file (app.py)
        files = ["memory.md", "src/core/app.py"]
        subj = "feat(core): implement feature and update memory"
        errors, warnings = lint_commits.validate_commit("sha1", subj, files, strict=True)
        self.assertTrue(any("違反職責分離" in err for err in errors))

    def test_governance_isolated_in_docs(self):
        # Isolated governance commit should pass
        files = ["memory.md"]
        subj = "docs(docs): record architecture decision and memory updates"
        errors, warnings = lint_commits.validate_commit("sha1", subj, files, strict=True)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
