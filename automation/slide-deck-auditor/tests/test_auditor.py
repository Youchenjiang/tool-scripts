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

    def test_elevator_shaft_mt_auto_detected(self):
        code = """
        const CardWithMtAuto = () => (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <h2>Title</h2>
            <div style={{ marginTop: 'auto' }}>Footer pushed to bottom</div>
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

    def test_bottom_deadspace_void_detected(self):
        code = """
        const VoidSlide = () => (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, height: 500 }}>
            <div>Card 1</div>
            <div>Card 2</div>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("bottom_deadspace_void", rules)
            self.assertTrue(any(i.severity == "ERROR" and i.rule_id == "bottom_deadspace_void" for i in issues))
        finally:
            temp_path.unlink()

    def test_typography_floor_detected(self):
        code = """
        const TinyTextSlide = () => (
          <div>
            <p style={{ fontSize: 26 }}>Text below 30px floor</p>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("typography_floor", rules)
            self.assertTrue(any(i.severity == "ERROR" and i.rule_id == "typography_floor" for i in issues))
        finally:
            temp_path.unlink()

    def test_typography_floor_passes_at_30(self):
        code = """
        const GoodTextSlide = () => (
          <div>
            <p style={{ fontSize: 30 }}>Readable text meeting 30px floor</p>
          </div>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertNotIn("typography_floor", rules)
        finally:
            temp_path.unlink()


    def test_deck_integrity_missing_notes(self):
        code = """
        const Slide1 = () => <Frame title="Test"><div>Content</div></Frame>;
        export default [ Slide1 ] satisfies Page[];
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("deck_integrity", rules)
        finally:
            temp_path.unlink()

    def test_information_density_detected(self):
        code = """
        const OverloadedSlide = () => (
          <Frame title="Overloaded">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' }}>
              <Card>
                <div style={{ background: '#f00', border: '1px solid #f00' }}>Box 1</div>
                <div style={{ background: '#0f0', border: '1px solid #0f0' }}>Box 2</div>
                <div style={{ background: '#00f', border: '1px solid #00f' }}>Box 3</div>
                <div style={{ background: '#ff0', border: '1px solid #ff0' }}>Box 4</div>
              </Card>
            </div>
          </Frame>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("information_density", rules)
            self.assertTrue(any(i.severity == "ERROR" and i.rule_id == "information_density" for i in issues))
        finally:
            temp_path.unlink()

    def test_vertical_overflow_detected(self):
        code = """
        const OverflowSlide = () => (
          <Frame title="Overflow Hazard">
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <Card>Top Banner</Card>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <Card><div style={{ background: '#fff' }}>1</div><div style={{ background: '#fff' }}>2</div></Card>
                <Card><div style={{ background: '#fff' }}>1</div><div style={{ background: '#fff' }}>2</div></Card>
                <Card><div style={{ background: '#fff' }}>1</div><div style={{ background: '#fff' }}>2</div></Card>
              </div>
            </div>
          </Frame>
        );
        """
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            issues = self.auditor.scan_path(temp_path)
            rules = [i.rule_id for i in issues]
            self.assertIn("vertical_overflow", rules)
            self.assertTrue(any(i.severity == "ERROR" and i.rule_id == "vertical_overflow" for i in issues))
        finally:
            temp_path.unlink()

    def test_code_wrapping_defect_detected(self):
        code = """
        const GlitchSlide = () => (
          <div>
            <div style={{ fontFamily: font.mono, wordBreak: 'break-all' }}>
              ip.dst == 192.168.1.1 && http.request.method == "POST"
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
            self.assertIn("code_wrapping_defect", rules)
            self.assertTrue(any(i.severity == "ERROR" and i.rule_id == "code_wrapping_defect" for i in issues))
        finally:
            temp_path.unlink()

    def test_clean_deck_passes(self):
        code = """
        const CompliantCard = () => (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h1 style={{ fontSize: 36, color: c.text }}>架構剖析</h1>
            <p style={{ fontSize: 30, color: c.muted }}>深入解析底層 Worker 降權機制與隔離防線。</p>
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


