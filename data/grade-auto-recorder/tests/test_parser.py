#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - GradeParser 解析測試"""

import sys
import unittest
from pathlib import Path

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from grade_recorder.parser import GradeParser


class TestGradeParser(unittest.TestCase):
    def test_multi_column_table_parsing(self):
        text = "A+\tA\tA-\n32\t52\t24\n60\t65\t\n"
        data = GradeParser.parse_multi_column_table(text)
        self.assertIsNotNone(data)
        self.assertEqual(data["A+"], ["32", "60"])
        self.assertEqual(data["A"], ["52", "65"])
        self.assertEqual(data["A-"], ["24"])

    def test_key_value_parsing(self):
        text = "59 A-\n1博 A+\n115423001 90\n"
        items = GradeParser.parse_key_value_lines(text)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0], ("59", "A-"))
        self.assertEqual(items[1], ("1博", "A+"))
        self.assertEqual(items[2], ("115423001", "90"))

    def test_extract_submissions_dispatcher(self):
        table_text = "A+\tA\n01\t02\n"
        items, fmt = GradeParser.extract_submissions(table_text)
        self.assertEqual(fmt, "multi_column")
        self.assertEqual(len(items), 2)

        kv_text = "01 A+\n02 A\n"
        items, fmt = GradeParser.extract_submissions(kv_text)
        self.assertEqual(fmt, "key_value")
        self.assertEqual(len(items), 2)

    def test_headerless_multi_column_parsing(self):
        """測試無表頭（首行為純數字）多欄表格透過 custom_headers 成功解析"""
        text = "24\t28\t35\n59\t33\t14\n"
        # 未指定 custom_headers 時應為 None（不誤判為表頭）
        self.assertIsNone(GradeParser.parse_multi_column_table(text))

        # 指定 custom_headers 後首行視為資料並正確對齊各欄
        data = GradeParser.parse_multi_column_table(text, custom_headers=["A", "A+", "A++"])
        self.assertIsNotNone(data)
        self.assertEqual(data["A"], ["24", "59"])
        self.assertEqual(data["A+"], ["28", "33"])
        self.assertEqual(data["A++"], ["35", "14"])

        # 透過 extract_submissions 統一介面測試
        items, fmt = GradeParser.extract_submissions(text, custom_headers=["A", "A+", "A++"])
        self.assertEqual(fmt, "multi_column_custom_headers")
        self.assertEqual(len(items), 6)
        self.assertIn(("24", "A"), items)
        self.assertIn(("28", "A+"), items)
        self.assertIn(("35", "A++"), items)


if __name__ == "__main__":
    unittest.main()
