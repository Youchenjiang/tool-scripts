#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - CLI 命令列參數與非互動批次操作測試"""

import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
import io

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from grade_recorder.cli import parse_resolve_arg, main
from grade_recorder.models import Roster


class TestGradeCLI(unittest.TestCase):
    def setUp(self):
        base_dir = Path(__file__).resolve().parent.parent
        self.example_roster_path = base_dir / "data.example" / "roster.example.csv"
        self.roster = Roster(self.example_roster_path)

    def test_parse_resolve_arg(self):
        """測試 --resolve 參數解析字串"""
        # 01 在範例名冊中有 115423001 王小明 (碩) 與 115483001 張小美 (博)
        # 04 只有 115423004 林志強 (碩)
        # 02 碩班是 115423002 陳大華
        resolve_str = "1碩=A, 1博=A+, 04=A++, 陳大華=A"
        resolved, warnings = parse_resolve_arg(resolve_str, self.roster)

        self.assertEqual(resolved.get("115423001"), "A")
        self.assertEqual(resolved.get("115483001"), "A+")
        self.assertEqual(resolved.get("115423004"), "A++")
        self.assertEqual(resolved.get("115423002"), "A")  # 陳大華
        self.assertEqual(len(warnings), 0)

    def test_cli_audit_mode_json(self):
        """測試 --audit --json 模式輸出結構"""
        input_data = "A+\tA\n04\t01\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as tf:
            tf.write(input_data)
            tf_path = tf.name

        try:
            test_args = [
                "run.py",
                "-i", tf_path,
                "--roster", str(self.example_roster_path),
                "--audit",
                "--json"
            ]
            with patch.object(sys, "argv", test_args):
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    with self.assertRaises(SystemExit) as cm:
                        main()
                    self.assertEqual(cm.exception.code, 0)
                    output = mock_stdout.getvalue()
                    data = json.loads(output)
                    self.assertEqual(data["total_submissions"], 2)
                    self.assertIn("A+", data["grade_counts"])
                    self.assertIn("A", data["grade_counts"])
        finally:
            Path(tf_path).unlink(missing_ok=True)

    def test_cli_non_interactive_batch_export(self):
        """測試 --input, --resolve 與 -y 一鍵批次匯出 CSV 與 Excel"""
        input_data = "A+\tA\n04\t01\n"
        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            input_file = temp_dir / "raw.txt"
            input_file.write_text(input_data, encoding="utf-8")

            # 在臨時目錄中執行測試，避免污染正式 data/
            test_args = [
                "run.py",
                "-i", str(input_file),
                "--roster", str(self.example_roster_path),
                "--resolve", "1碩=A, 1博=A+",
                "-o", "unit_test_grade",
                "-y",
                "--json"
            ]

            with patch.object(sys, "argv", test_args):
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    main()
                    out = mock_stdout.getvalue()
                    res = json.loads(out)
                    self.assertEqual(res["status"], "success")
                    self.assertTrue(Path(res["csv_path"]).exists())
                    self.assertTrue(Path(res["xlsx_path"]).exists())
                    # 清理產出之檔案
                    Path(res["csv_path"]).unlink(missing_ok=True)
                    Path(res["xlsx_path"]).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
