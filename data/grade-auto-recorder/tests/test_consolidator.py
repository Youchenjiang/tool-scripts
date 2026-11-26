#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - SemesterConsolidator 全學期歷次成績彙整測試"""

import sys
import unittest
import tempfile
from pathlib import Path

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from grade_recorder.models import Roster
from grade_recorder.consolidator import SemesterConsolidator


class TestSemesterConsolidator(unittest.TestCase):
    def setUp(self):
        base_dir = Path(__file__).resolve().parent.parent
        self.roster_path = base_dir / "data.example" / "roster.example.csv"
        self.roster = Roster(self.roster_path)

    def test_find_grade_csv_files(self):
        """測試自動掃描並排序 grade_YYYYMMDD.csv 檔案"""
        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            (temp_dir / "grade_20261006.csv").write_text("帳號,姓名,成績\n", encoding="utf-8")
            (temp_dir / "grade_20260915.csv").write_text("帳號,姓名,成績\n", encoding="utf-8")
            (temp_dir / "other_file.csv").write_text("帳號,姓名,成績\n", encoding="utf-8")

            files = SemesterConsolidator.find_grade_csv_files(temp_dir)
            self.assertEqual(len(files), 2)
            self.assertEqual(files[0][0], "2026-09-15")
            self.assertEqual(files[1][0], "2026-10-06")

    def test_consolidate_aggregation_and_stats(self):
        """測試歷次成績彙整、缺繳計算、繳交率及平均等第積分運算"""
        # 範例名冊包含 5 位學生：
        # 115423001 王小明
        # 115423002 陳大華
        # 115423004 林志強
        # 115483001 張小美
        # 115483002 李雅婷
        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)

            # Session 1: 2026-09-15
            csv1 = temp_dir / "grade_20260915.csv"
            csv1.write_text(
                "帳號,姓名,成績,備註\n"
                "115423001,王小明,A+,\n"
                "115423002,陳大華,A,\n"
                "115423004,林志強,A++,\n"
                "115483001,張小美,A+,\n"
                "115483002,李雅婷,,\n",  # 李雅婷缺繳
                encoding="utf-8-sig"
            )

            # Session 2: 2026-09-29
            csv2 = temp_dir / "grade_20260929.csv"
            csv2.write_text(
                "帳號,姓名,成績,備註\n"
                "115423001,王小明,A,\n"
                "115423002,陳大華,A,\n"
                "115423004,林志強,A+,\n"
                "115483001,張小美,,\n"  # 張小美缺繳
                "115483002,李雅婷,A+,\n",
                encoding="utf-8-sig"
            )

            out_csv, out_xlsx, summary = SemesterConsolidator.consolidate(
                data_dir=temp_dir,
                roster=self.roster,
                output_dir=temp_dir,
                custom_prefix="test_summary"
            )

            self.assertTrue(out_csv.exists())
            self.assertTrue(out_xlsx.exists())

            self.assertEqual(summary["total_students"], 5)
            self.assertEqual(summary["total_sessions"], 2)
            self.assertEqual(summary["perfect_submission_count"], 3)  # 王小明、陳大華、林志強全勤

            # 讀取 CSV 檢驗內容
            import csv
            with open(out_csv, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.assertEqual(len(rows), 5)
            by_sid = {r["帳號"]: r for r in rows}

            # 王小明: A+ (4.0) + A (3.7) -> 實繳 2, 缺繳 0, 繳交率 100.0%, GPA 3.85
            s1 = by_sid["115423001"]
            self.assertEqual(s1["2026-09-15"], "A+")
            self.assertEqual(s1["2026-09-29"], "A")
            self.assertEqual(s1["實繳次數"], "2")
            self.assertEqual(s1["缺繳次數"], "0")
            self.assertEqual(s1["繳交率"], "100.0%")
            self.assertEqual(s1["平均等第積分"], "3.85")

            # 李雅婷: 缺繳 1 次, A+ 1 次 -> 實繳 1, 缺繳 1, 繳交率 50.0%
            s5 = by_sid["115483002"]
            self.assertEqual(s5["2026-09-15"], "")
            self.assertEqual(s5["2026-09-29"], "A+")
            self.assertEqual(s5["實繳次數"], "1")
            self.assertEqual(s5["缺繳次數"], "1")
            self.assertEqual(s5["繳交率"], "50.0%")


if __name__ == "__main__":
    unittest.main()
