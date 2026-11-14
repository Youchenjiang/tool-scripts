#!/usr/bin/env python3
"""
Unit tests for tools/pr_helper.py validating PR title, body structure, branch naming, and sanitization.
"""

import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import pr_body_contract
import pr_helper

class TestSanitizeTitle(unittest.TestCase):
    """Test validation of PR titles according to Conventional Commits and policy limits."""

    def test_valid_titles(self):
        valid = [
            "feat(fluent): rebrand application to tapstrum",
            "fix(packaging): sync tapstrum identity and display name with store",
            "perf(packaging): optimize msix payload with trimming",
            "docs(docs): update privacy policy for tapstrum rebranding",
            "chore(store): add 1080p desktop screenshots for all store locales",
        ]
        for title in valid:
            self.assertEqual(pr_helper.sanitize_title(title), title)

    def test_title_too_long(self):
        too_long = "perf(packaging): optimize msix package footprint with trimming and assembly whitelist"
        self.assertGreater(len(too_long), 72)
        with self.assertRaises(ValueError):
            pr_helper.sanitize_title(too_long)

    def test_title_invalid_format(self):
        invalid = [
            "Update readme and documentation",
            "fix: Capitalized subject",
            "feat(packaging): trailing dot.",
            "",
            "   ",
        ]
        for title in invalid:
            with self.assertRaises(ValueError):
                pr_helper.sanitize_title(title)

    def test_title_dangerous_characters(self):
        dangerous = [
            'feat(core): test"quoted"',
            "feat(core): test`backtick`",
            "feat(core): test$variable",
            "feat(core): test;command",
            "feat(core): test\nnewline",
        ]
        for title in dangerous:
            with self.assertRaises(ValueError):
                pr_helper.sanitize_title(title)


class TestLintPrContent(unittest.TestCase):
    """Test verification of PR Body markdown sections."""

    def test_valid_body(self):
        valid_body = f"""## Summary
Optimize MSIX package footprint by trimming and assembly whitelisting.

## Changes
1. **PERF (build)**:
   - retarget windows sdk to 19041
2. **PERF (packaging)**:
   - optimize msix payload with trimming

## Validation
- [x] Conventional commits audit passes
- [x] All 2 commits strictly follow Conventional Commits

## Review Checklist
{pr_body_contract.PROVIDER_ITEM}
"""
        errors = pr_helper.lint_pr_content(valid_body)
        self.assertEqual(errors, [])

    def test_missing_sections(self):
        missing_summary = f"""## Changes
1. **FEAT (core)**: change

## Validation
- [x] passed

## Review Checklist
{pr_body_contract.PROVIDER_ITEM}
"""
        errors = pr_helper.lint_pr_content(missing_summary)
        self.assertTrue(any("Missing mandatory section: '## Summary'" in err for err in errors))

        missing_changes = f"""## Summary
A summary here.

## Validation
- [x] passed

## Review Checklist
{pr_body_contract.PROVIDER_ITEM}
"""
        errors = pr_helper.lint_pr_content(missing_changes)
        self.assertTrue(any("Missing mandatory section: '## Changes'" in err for err in errors))

        missing_validation = """## Summary
A summary here.

## Changes
1. **FEAT (core)**: change
"""
        errors = pr_helper.lint_pr_content(missing_validation)
        self.assertTrue(any("Missing mandatory section: '## Validation'" in err for err in errors))

        missing_checklist = """## Summary
A summary here.

## Changes
1. **FEAT (core)**: change

## Validation
- [x] passed
"""
        errors = pr_helper.lint_pr_content(missing_checklist)
        self.assertTrue(any("Missing mandatory section: '## Review Checklist'" in err for err in errors))

    def test_missing_provider_acknowledgement(self):
        body = """## Summary
A summary here.

## Changes
1. **FEAT (core)**: change

## Validation
- [x] passed

## Review Checklist
- [ ] **Behavior**: reviewed.
"""
        self.assertIn("Missing required External provider acknowledgement line.",
                      pr_helper.lint_pr_content(body))

    def test_empty_summary(self):
        empty_summary = f"""## Summary

## Changes
1. **FEAT (core)**: change

## Validation
- [x] passed

## Review Checklist
{pr_body_contract.PROVIDER_ITEM}
"""
        errors = pr_helper.lint_pr_content(empty_summary)
        self.assertTrue(any("Section '## Summary' cannot be empty" in err for err in errors))

    def test_empty_changes(self):
        empty_changes = f"""## Summary
Summary text.

## Changes

## Validation
- [x] passed

## Review Checklist
{pr_body_contract.PROVIDER_ITEM}
"""
        errors = pr_helper.lint_pr_content(empty_changes)
        self.assertTrue(any("Section '## Changes' cannot be empty" in err for err in errors))

    def test_empty_validation(self):
        empty_validation = f"""## Summary
Summary text.

## Changes
1. **FEAT (core)**: change

## Validation

## Review Checklist
{pr_body_contract.PROVIDER_ITEM}
"""
        errors = pr_helper.lint_pr_content(empty_validation)
        self.assertTrue(any("Section '## Validation' cannot be empty" in err for err in errors))


class TestLintBranchName(unittest.TestCase):
    """Test branch name validation against standard pattern."""

    def test_valid_branch_names(self):
        valid = [
            "feat/rebrand-to-tapstrum",
            "fix/store-identity-sync",
            "perf/msix-packaging-optimization",
            "docs/update-readme",
            "chore/bump-version-1.3.0.0",
        ]
        for b in valid:
            self.assertEqual(pr_helper.lint_branch_name(b), [])

    def test_invalid_branch_names(self):
        invalid = [
            "main",
            "my_feature",
            "random-branch",
            "FEAT/capital-type",
            "",
        ]
        for b in invalid:
            errors = pr_helper.lint_branch_name(b)
            self.assertGreater(len(errors), 0)


class TestBuildPrBody(unittest.TestCase):
    """Test generating standard PR body from commits."""

    def test_generated_body_structure(self):
        sample_commits = [
            ("sha1", "feat(fluent): rebrand application to tapstrum"),
            ("sha2", "fix(packaging): sync tapstrum identity with store"),
        ]
        body = pr_helper.build_pr_body(sample_commits, custom_summary="Custom summary text.")
        self.assertIn("## Summary\nCustom summary text.", body)
        self.assertIn("## Changes", body)
        self.assertIn("## Validation", body)
        self.assertTrue(body.rstrip().endswith(pr_body_contract.PROVIDER_ITEM), body)
        self.assertIn("1. **FEAT (fluent)**:", body)
        self.assertIn("2. **FIX (packaging)**:", body)
        self.assertIn("- [x] Conventional commits audit passes: `python tools/lint_commits.py`", body)

        errors = pr_helper.lint_pr_content(body)
        self.assertEqual(errors, [])

    def test_generated_body_satisfies_preflight(self):
        from pr_preflight import validate_pr_body

        body = pr_helper.build_pr_body(
            [("sha1", "feat(core): add capability")], custom_summary="Adds a capability.")
        self.assertIn("completed External provider acknowledgement required",
                      validate_pr_body(body))
        acknowledged = body.replace(pr_body_contract.PROVIDER_ITEM,
                                    pr_body_contract.PROVIDER_ITEM.replace("- [ ]", "- [x]"))
        self.assertEqual([], validate_pr_body(acknowledged))

    def test_custom_changes_provided(self):
        sample_commits = [
            ("sha1", "feat(fluent): rebrand application to tapstrum"),
        ]
        custom_changes = "1. **Architecture**:\n   - Complete rebrand to TapStrum"
        body = pr_helper.build_pr_body(sample_commits, custom_changes=custom_changes)
        self.assertIn(custom_changes, body)
        self.assertNotIn("1. **FEAT (fluent)**:", body)

    def test_changes_never_dumps_raw_commit_subjects(self):
        sample_commits = [
            (f"sha{i}", f"docs(docs): documentation item {i}")
            for i in range(10)
        ]
        body = pr_helper.build_pr_body(sample_commits)
        self.assertIn("1. **DOCS (docs)**: 10 atomic refinement(s)", body)
        self.assertNotIn("documentation item 0", body)


class TestPullRequestTemplate(unittest.TestCase):
    """The shipped template must already be in the shape preflight accepts."""

    def test_template_uses_the_contract_sections(self):
        for layout in (".github", "github"):
            path = os.path.join(REPO_ROOT, layout, "pull_request_template.md")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as handle:
                    template = handle.read()
                break
        else:
            self.skipTest("this layout ships no pull request template")
        headings = {line.strip() for line in template.splitlines() if line.startswith("## ")}
        self.assertEqual(headings, set(pr_body_contract.REQUIRED_SECTIONS))
        self.assertIn(pr_body_contract.PROVIDER_ITEM, template)


class TestSecurityGate(unittest.TestCase):
    """Test security boundaries preventing unauthorized automated merges."""

    def test_merge_subcommand_strictly_forbidden(self):
        with self.assertRaises(SystemExit) as ctx:
            pr_helper.handle_merge(None)
        self.assertEqual(ctx.exception.code, 1)

    def test_create_requires_custom_changes(self):
        class DummyArgs:
            base = "main"
            skip_checks = True
            changes_file = None
            changes = None
            title = "feat(core): test pr"
            label = "documentation"
            summary = None

        args = DummyArgs()
        with self.assertRaises(SystemExit) as ctx:
            pr_helper.handle_create(args)
        self.assertEqual(ctx.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
