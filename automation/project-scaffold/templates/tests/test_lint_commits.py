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
        valid = [
            ("sha1", "feat(fluent): rebrand application to tapstrum", ["tapster.fluent/mainpage.xaml.cs"]),
            ("sha2", "perf(packaging): optimize msix payload with trimming", ["scripts/build_msix.ps1"]),
            ("sha3", "docs(docs): update architecture documentation", ["docs/architecture.md"]),
            ("sha4", "chore(deps): bump nuget package versions", ["tapster.fluent.csproj"]),
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
        subj = "perf(packaging): optimize msix package footprint with trimming and assembly whitelist"
        self.assertGreater(len(subj), 72)
        errors, _ = lint_commits.validate_commit(sha, subj, ["scripts/build_msix.ps1"], strict=True)
        self.assertTrue(any("超過上限 72 字元" in err for err in errors))

    def test_vague_description(self):
        vague_examples = [
            "fix(core): fix bug",
            "chore(packaging): update",
            "refactor(ui): misc",
            "refactor(ui): changes",
            "feat(launcher): stuff",
        ]
        for subj in vague_examples:
            errors, _ = lint_commits.validate_commit("sha1", subj, ["file.cs"], strict=True)
            self.assertTrue(any("描述過於空泛" in err for err in errors), f"Expected vague error for '{subj}'")

    def test_separation_of_concerns_free_riding(self):
        # Mixing governance doc (memory.md) with code file (app.cs)
        files = ["memory.md", "src/tapster/app.cs"]
        subj = "feat(core): implement feature and update memory"
        errors, warnings = lint_commits.validate_commit("sha1", subj, files, strict=True)
        self.assertTrue(any("違反職責分離" in err for err in errors))

    def test_governance_isolated_in_docs(self):
        # Isolated governance commit should pass
        files = ["memory.md"]
        subj = "docs(docs): record tapstrum rebranding and partner center identity"
        errors, warnings = lint_commits.validate_commit("sha1", subj, files, strict=True)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
