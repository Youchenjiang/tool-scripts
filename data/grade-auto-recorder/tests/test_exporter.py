#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""單元測試 - GradeExporter 匯出測試"""

import unittest
import tempfile
import shutil
from pathlib import Path
from grade_recorder.models import Roster
from grade_recorder.exporter import GradeExporter


class TestGradeExporter(unittest.TestCase):
    def setUp(self):
        base_dir = Path(__file__).resolve().parent.parent
        example_csv = base_dir / "data.example" / "roster.example.csv"
        self.roster = Roster(example_csv)
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_full_pipeline(self):
        grades = {"115423001": "A+", "115423002": "A"}
        csv_p, xlsx_p = GradeExporter.export_full(
            roster=self.roster,
            grades_map=grades,
            output_dir=self.temp_dir,
            custom_name="test_grade"
        )
        self.assertTrue(csv_p.exists())
        self.assertTrue(xlsx_p.exists())
        self.assertGreater(xlsx_p.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
