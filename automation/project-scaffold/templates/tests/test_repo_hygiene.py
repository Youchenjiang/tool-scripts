import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from repo_hygiene import (
    matches_any_pattern,
    load_hygiene_config,
    check_banned_directories,
    check_root_directories,
    check_root_files,
    check_banned_tracked_files,
    check_sensitive_tracked_files,
    check_test_segregation,
    check_docs_structure,
    run_hygiene_audit,
    main,
)


class HygienePatternTests(unittest.TestCase):
    def test_matches_any_pattern(self):
        patterns = {"README.md", "README.*.md", "tsconfig.*.json", "*.sln"}
        self.assertTrue(matches_any_pattern("README.md", patterns))
        self.assertTrue(matches_any_pattern("README.zh-TW.md", patterns))
        self.assertTrue(matches_any_pattern("tsconfig.build.json", patterns))
        self.assertTrue(matches_any_pattern("MyProject.sln", patterns))
        self.assertFalse(matches_any_pattern("scratch.txt", patterns))
        self.assertFalse(matches_any_pattern("unknown.json", patterns))


class HygieneBannedDirsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_root_has_no_banned_dirs(self):
        config = {"bannedRootDirs": {"archive", "scratch", "tmp"}}
        violations = check_banned_directories(self.root, config)
        self.assertEqual([], violations)

    def test_detects_banned_root_dirs(self):
        config = {"bannedRootDirs": {"archive", "scratch", "tmp"}}
        (self.root / "archive").mkdir()
        (self.root / "tmp").mkdir()
        violations = check_banned_directories(self.root, config)
        self.assertEqual(2, len(violations))
        self.assertTrue(any("archive" in v for v in violations))
        self.assertTrue(any("tmp" in v for v in violations))


class HygieneRootItemsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_root_directories_whitelist(self):
        config = {"allowedRootDirs": {"src", "tests", "tools", "docs"}}
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "unauthorized_dir").mkdir()

        violations = check_root_directories(self.root, config, tracked_files=None)
        self.assertEqual(1, len(violations))
        self.assertIn("unauthorized_dir", violations[0])

    def test_root_files_whitelist(self):
        config = {"allowedRootFiles": {"README.md", "LICENSE", "package.json", "*.sln"}}
        (self.root / "README.md").write_text("# Test", encoding="utf-8")
        (self.root / "App.sln").write_text("", encoding="utf-8")
        (self.root / "random_scratch.txt").write_text("junk", encoding="utf-8")

        violations = check_root_files(self.root, config, tracked_files=None)
        self.assertEqual(1, len(violations))
        self.assertIn("random_scratch.txt", violations[0])


class HygieneTrackedFilesTests(unittest.TestCase):
    def test_detects_banned_tracked_files(self):
        config = {"bannedFilePatterns": [".tmp", ".log", "__pycache__", ".DS_Store"]}
        tracked = [
            "src/index.ts",
            "tests/test_main.py",
            "debug.log",
            "src/__pycache__/index.cpython-310.pyc",
            "docs/.DS_Store",
            "temp_file.tmp",
        ]
        violations = check_banned_tracked_files(tracked, config)
        self.assertEqual(4, len(violations))
        self.assertTrue(any("debug.log" in v for v in violations))
        self.assertTrue(any("__pycache__" in v for v in violations))
        self.assertTrue(any(".DS_Store" in v for v in violations))
        self.assertTrue(any("temp_file.tmp" in v for v in violations))

    def test_detects_sensitive_files(self):
        config = {"sensitivePatterns": [".env", "*.pem", "*.key", "id_rsa"]}
        tracked = [
            "src/config.ts",
            ".env.example",
            ".env.template",
            ".env",
            "certs/private.key",
            "keys/id_rsa",
        ]
        violations = check_sensitive_tracked_files(tracked, config)
        self.assertEqual(3, len(violations))
        self.assertTrue(any("'.env'" in v for v in violations))
        self.assertTrue(any("private.key" in v for v in violations))
        self.assertTrue(any("id_rsa" in v for v in violations))


class HygieneTestSegregationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_misplaced_tests_in_tools(self):
        tools = self.root / "tools"
        tools.mkdir()
        (tools / "test_wrong_place.py").write_text("", encoding="utf-8")
        (tools / "pr_tool.py").write_text("", encoding="utf-8")

        tests = self.root / "tests"
        tests.mkdir()
        (tests / "test_correct.py").write_text("", encoding="utf-8")
        (tests / "invalid_name.py").write_text("", encoding="utf-8")

        violations = check_test_segregation(self.root)
        self.assertEqual(2, len(violations))
        self.assertTrue(any("test_wrong_place.py" in v for v in violations))
        self.assertTrue(any("invalid_name.py" in v for v in violations))


class HygieneDocsTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.docs = self.root / "docs"
        self.docs.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_docs_structure_compliance(self):
        config = {
            "allowedDocsDirs": {"adr", "architecture", "specs"},
            "allowedDocsFiles": {"README.md", "ROADMAP.md"},
        }
        (self.docs / "adr").mkdir()
        (self.docs / "README.md").write_text("", encoding="utf-8")
        (self.docs / "unplanned_folder").mkdir()
        (self.docs / "stray_doc.txt").write_text("", encoding="utf-8")

        violations = check_docs_structure(self.root, config)
        self.assertEqual(2, len(violations))
        self.assertTrue(any("unplanned_folder" in v for v in violations))
        self.assertTrue(any("stray_doc.txt" in v for v in violations))


class HygieneConfigLoadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_hygiene_config_merges_custom(self):
        tools = self.root / "tools"
        tools.mkdir()
        project_json = tools / "project.json"
        project_json.write_text(
            json.dumps({
                "name": "custom-app",
                "hygiene": {
                    "allowedRootDirs": ["custom_data", "pipelines"],
                    "allowedRootFiles": ["app.config"],
                }
            }),
            encoding="utf-8",
        )

        cfg = load_hygiene_config(self.root)
        self.assertIn("custom_data", cfg["allowedRootDirs"])
        self.assertIn("pipelines", cfg["allowedRootDirs"])
        self.assertIn("app.config", cfg["allowedRootFiles"])
        # Built-in defaults still present
        self.assertIn("src", cfg["allowedRootDirs"])
        self.assertIn("README.md", cfg["allowedRootFiles"])


class HygieneCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        (self.root / "README.md").write_text("# Hello", encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_main.py").write_text("", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_clean_returns_zero(self):
        with patch.object(sys, "argv", ["hygiene_checker.py", "--root", str(self.root)]):
            rc = main()
            self.assertEqual(0, rc)

    def test_cli_violation_returns_one(self):
        (self.root / "scratch").mkdir()
        with patch.object(sys, "argv", ["hygiene_checker.py", "--root", str(self.root)]):
            rc = main()
            self.assertEqual(1, rc)


class LiveRepositoryHygieneTests(unittest.TestCase):
    def test_live_repository_is_clean_if_scaffolded(self):
        """When executed in an initialized project with project.json, verify repository hygiene."""
        repo_path = Path(REPO_ROOT).resolve()
        project_json = repo_path / "tools" / "project.json"
        if not project_json.is_file():
            # In template development directory, project.json is not yet instantiated
            raise unittest.SkipTest("Skipping live check: tools/project.json not present in template source")

        report = run_hygiene_audit(repo_path)
        self.assertTrue(
            report["passed"],
            f"Repository hygiene audit failed: {report['all_violations']}",
        )


if __name__ == "__main__":
    unittest.main()
