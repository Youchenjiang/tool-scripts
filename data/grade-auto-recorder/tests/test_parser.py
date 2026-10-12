#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - GradeParser 解析測試"""

import unittest
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


if __name__ == "__main__":
    unittest.main()
