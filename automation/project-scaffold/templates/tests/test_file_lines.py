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

from file_lines import (
    count_file_lines,
    load_metrics_config,
    scan_directory,
    check_line_limits,
    main,
)


class FileLinesCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_count_file_lines(self):
        f1 = self.root / "empty.py"
        f1.write_bytes(b"")
        self.assertEqual(0, count_file_lines(f1))

        f2 = self.root / "with_newline.py"
        f2.write_bytes(b"line 1\nline 2\nline 3\n")
        self.assertEqual(3, count_file_lines(f2))

        f3 = self.root / "no_trailing_newline.py"
        f3.write_bytes(b"line 1\nline 2")
        self.assertEqual(2, count_file_lines(f3))

    def test_scan_directory_filters(self):
        src = self.root / "src"
        src.mkdir()
        (src / "app.py").write_text("print(1)\nprint(2)\n", encoding="utf-8")
        (src / "types.ts").write_text("export type A = number;\n", encoding="utf-8")
        (src / "notes.txt").write_text("plain text", encoding="utf-8")

        node_mods = src / "node_modules"
        node_mods.mkdir()
        (node_mods / "skip.js").write_text("skip me", encoding="utf-8")

        counts = scan_directory(self.root, target_dir=src)
        self.assertIn("src/app.py", counts)
        self.assertIn("src/types.ts", counts)
        self.assertNotIn("src/notes.txt", counts)
        self.assertNotIn("src/node_modules/skip.js", counts)
        self.assertEqual(2, counts["src/app.py"])
        self.assertEqual(1, counts["src/types.ts"])

    def test_check_line_limits(self):
        counts = {
            "file_small.py": 100,
            "file_large.py": 600,
            "file_huge.py": 950,
        }
        violations = check_line_limits(counts, max_lines=500)
        self.assertEqual(2, len(violations))
        self.assertEqual("file_huge.py", violations[0][0])
        self.assertEqual(950, violations[0][1])
        self.assertEqual("file_large.py", violations[1][0])
        self.assertEqual(600, violations[1][1])


class FileLinesConfigAndCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.src = self.root / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_metrics_config(self):
        tools = self.root / "tools"
        tools.mkdir()
        (tools / "project.json").write_text(
            json.dumps({
                "metrics": {
                    "maxFileLines": 250,
                    "sourceDirs": ["src", "lib"],
                }
            }),
            encoding="utf-8",
        )
        cfg = load_metrics_config(self.root)
        self.assertEqual(250, cfg["maxFileLines"])
        self.assertEqual(["src", "lib"], cfg["sourceDirs"])

    def test_cli_output_file(self):
        (self.src / "main.py").write_text("line 1\nline 2\n", encoding="utf-8")
        out_file = self.root / "file_lines.json"

        with patch.object(sys, "argv", ["file_lines.py", "--root", str(self.root), "--output", str(out_file)]):
            rc = main()
            self.assertEqual(0, rc)
            self.assertTrue(out_file.is_file())
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIn("src/main.py", data)
            self.assertEqual(2, data["src/main.py"])

    def test_cli_check_fails_on_violation(self):
        (self.src / "long_file.py").write_text("\n" * 15, encoding="utf-8")
        with patch.object(sys, "argv", ["file_lines.py", "--root", str(self.root), "--max-lines", "10", "--check"]):
            rc = main()
            self.assertEqual(1, rc)

    def test_cli_check_passes_when_clean(self):
        (self.src / "short_file.py").write_text("\n" * 5, encoding="utf-8")
        with patch.object(sys, "argv", ["file_lines.py", "--root", str(self.root), "--max-lines", "10", "--check"]):
            rc = main()
            self.assertEqual(0, rc)

    def test_cli_json_mode(self):
        (self.src / "test.py").write_text("print('hi')\n", encoding="utf-8")
        with patch.object(sys, "argv", ["file_lines.py", "--root", str(self.root), "--json"]):
            rc = main()
            self.assertEqual(0, rc)


if __name__ == "__main__":
    unittest.main()
