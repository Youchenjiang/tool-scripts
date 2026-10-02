#!/usr/bin/env python3
"""Unit tests for slide-deck-auditor."""

import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slide_deck_auditor import Config, SlideDeckAuditor


class TestSlideDeckAuditor(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.auditor = SlideDeckAuditor(self.config)

    def test_elevator_shaft_detected(self):
        code = """
        const Card = () => (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <h1>Title</h1>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("elevator_shaft", rules)
        finally:
            temp_path.unlink()

    def test_letterboxing_void_detected(self):
        code = """
        const ImageBox = () => (
          <div style={{ background: '#000', objectFit: 'contain' }}>
            <img src="shot.png" />
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("letterboxing_void", rules)
        finally:
            temp_path.unlink()

    def test_semantic_color_inversion_detected(self):
        code = """
        const DefenseCard = () => (
          <div>
            <h2>縱深防禦與修復措施</h2>
            <div style={{ border: '2px solid red', color: c.accent }}>
              <p>落實更新與路徑限制</p>
            </div>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("semantic_color_inversion", rules)
        finally:
            temp_path.unlink()

    def test_ai_fluff_detected(self):
        code = """
        const Intro = () => (
          <div>
            <h1>這是一套科學驗證法則與震撼發現</h1>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("ai_fluff", rules)
        finally:
            temp_path.unlink()

    def test_inline_suppression(self):
        code = """
        const SpecialCard = () => (
          // slide-audit-ignore: elevator_shaft
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <h1>Intentional Layout</h1>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertNotIn("elevator_shaft", rules)
        finally:
            temp_path.unlink()

    def test_clean_deck_passes(self):
        code = """
        const CompliantCard = () => (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h1 style={{ fontSize: 36, color: c.text }}>架構剖析</h1>
            <p style={{ fontSize: 26, color: c.muted }}>深入解析底層 Worker 降權機制與隔離防線。</p>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            self.assertEqual(len(issues), 0)
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
