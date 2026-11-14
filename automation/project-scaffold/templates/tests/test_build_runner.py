#!/usr/bin/env python3
"""Unit tests for tools/build_runner.py."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import build_runner


class TestBuildRunner(unittest.TestCase):
    def test_missing_project_json_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(0, build_runner.run_all(Path(tmpdir) / "does_not_exist.json"))

    def test_empty_build_config_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "project.json"
            p.write_text(json.dumps({"name": "test", "build": {}}), encoding="utf-8")
            self.assertEqual(0, build_runner.run_all(p))

    def test_absent_source_files_skip_gracefully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "tools" / "project.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps({
                    "name": "test",
                    "build": {
                        "lint": "npm run lint",
                        "test": "npm test",
                        "build": "dotnet build",
                    }
                }),
                encoding="utf-8"
            )
            # Since no package.json and no .sln exists in tmpdir, all should skip cleanly
            self.assertEqual(0, build_runner.run_all(p))

    def test_failing_command_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "tools" / "project.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps({
                    "name": "test",
                    "build": {
                        "test": f'"{sys.executable}" -c "exit(1)"'
                    }
                }),
                encoding="utf-8"
            )
            self.assertEqual(1, build_runner.run_all(p))

    def test_successful_command_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "tools" / "project.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps({
                    "name": "test",
                    "build": {
                        "test": f'"{sys.executable}" -c "exit(0)"'
                    }
                }),
                encoding="utf-8"
            )
            self.assertEqual(0, build_runner.run_all(p))


if __name__ == "__main__":
    unittest.main()
