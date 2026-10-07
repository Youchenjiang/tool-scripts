#!/usr/bin/env python3
"""slide-deck-auditor: Automated layout, semantics, and typography linter for modern presentation decks.

Detects dead space voids, elevator shaft flexbox traps, letterboxing screenshot voids,
semantic color inversions, and AI buzzword cliches across React/TSX/JSX, Vue, HTML, and CSS decks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class Issue:
    file_path: str
    line_no: int
    rule_id: str
    severity: str  # "ERROR" or "WARN"
    message: str
    snippet: str = ""
    remediation: str = ""


class Config:
    DEFAULT_CONFIG: Dict[str, Any] = {
        "rules": {
            "bottom_deadspace_void": {"enabled": True, "severity": "ERROR"},
            "typography_floor": {"enabled": True, "severity": "ERROR"},
            "elevator_shaft": {"enabled": True, "severity": "ERROR"},
            "letterboxing_void": {"enabled": True, "severity": "ERROR"},
            "semantic_color_inversion": {"enabled": True, "severity": "ERROR"},
            "ai_fluff": {"enabled": True, "severity": "ERROR"},
            "deck_integrity": {"enabled": True, "severity": "ERROR"},
            "information_density": {"enabled": True, "severity": "ERROR"},
            "vertical_overflow": {"enabled": True, "severity": "ERROR"},
            "code_wrapping_defect": {"enabled": True, "severity": "ERROR"},
            "eyebrow_character_ceiling": {"enabled": True, "severity": "ERROR"},
        },
        "eyebrow_max_chars": 16,
        "typography_thresholds": {
            "absolute_min_px": 30,
            "body_text_min_px": 30,
            "code_font_min_px": 30,
            "card_title_min_px": 36,
        },
        "deadspace_thresholds": {
            "min_content_height_px": 620,
        },
        "ai_fluff_keywords": [
            "科學驗證法則",
            "科學驗證",
            "親眼見證",
            "心智模型",
            "破案地圖",
            "震撼發現",
            "史詩級",
            "革命性突破",
            "不言而喻",
            "顯而易見",
            "眾所周知",
            "奇蹟般",
            "不可思議",
            "Game Changer",
            "Mind Blowing",
            "臨床聽診",
            "封包透視",
            "客觀證據鏈",
            "不可辯駁",
            "客觀物理",
            "截然不同",
            "解剖視野",
            "透明明信片",
            "加密鐵幕",
            "拼圖地獄",
            "不可偽造",
            "工程師心法",
            "人機分工新公式",
            "過關了嗎",
            "看清真相",
            "數位水管",
            "洋蔥切片",
            "神仙打架",
            "一目了然的真相",
            "揭開神秘面紗",
            "驚人反轉",
            "驚心動魄",
            "絕不說謊",
        ],
        "defense_keywords": [
            "防禦",
            "修復",
            "加固",
            "縱深防禦",
            "mitigation",
            "defense",
            "remediation",
            "hardening",
            "patch",
        ],
        "danger_color_patterns": [
            r"c\.accent\b",
            r"color:\s*['\"]red['\"]",
            r"border:\s*['\"][^'\"]*red",
            r"#ef4444\b",
            r"#dc2626\b",
            r"#b91c1c\b",
            r"#f87171\b",
        ],
    }

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.data = dict(self.DEFAULT_CONFIG)
        if config_dict:
            for k, v in config_dict.items():
                if isinstance(v, dict) and k in self.data and isinstance(self.data[k], dict):
                    self.data[k].update(v)
                else:
                    self.data[k] = v

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        if path and path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return cls(json.load(f))
            except Exception as e:
                print(f"[slide-deck-auditor] Warning: Failed to load config from {path}: {e}", file=sys.stderr)

        # Fallback to local rules.json in same dir as script
        default_path = Path(__file__).parent / "rules.json"
        if default_path.is_file():
            try:
                with open(default_path, "r", encoding="utf-8") as f:
                    return cls(json.load(f))
            except Exception:
                pass
        return cls()

    def is_rule_enabled(self, rule_id: str) -> bool:
        rule = self.data.get("rules", {}).get(rule_id, {})
        return rule.get("enabled", True)

    def get_severity(self, rule_id: str) -> str:
        rule = self.data.get("rules", {}).get(rule_id, {})
        return rule.get("severity", "ERROR")


class SlideDeckAuditor:
    SUPPORTED_EXTENSIONS = {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".html", ".css", ".md"}

    def __init__(self, config: Config, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.issues: List[Issue] = []

    def scan_path(self, target: Path) -> List[Issue]:
        target_files: List[Path] = []
        if target.is_file():
            if target.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                target_files.append(target)
        elif target.is_dir():
            for root, dirs, files in os.walk(target):
                # Ignore common vendor directories
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build", ".next", ".turbo"}]
                for file in files:
                    p = Path(root) / file
                    if p.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                        target_files.append(p)

        for file_path in target_files:
            self.audit_file(file_path)

        return self.issues

    def audit_file(self, file_path: Path) -> None:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            if self.verbose:
                print(f"[slide-deck-auditor] Error reading {file_path}: {e}", file=sys.stderr)
            return

        lines = content.splitlines()

        # Execute registered checks
        if self.config.is_rule_enabled("bottom_deadspace_void"):
            self._check_bottom_deadspace_void(file_path, content, lines)

        if self.config.is_rule_enabled("elevator_shaft"):
            self._check_elevator_shaft(file_path, content, lines)

        if self.config.is_rule_enabled("letterboxing_void"):
            self._check_letterboxing_void(file_path, content, lines)

        if self.config.is_rule_enabled("semantic_color_inversion"):
            self._check_semantic_color_inversion(file_path, content, lines)

        if self.config.is_rule_enabled("ai_fluff"):
            self._check_ai_fluff(file_path, content, lines)

        if self.config.is_rule_enabled("typography_floor"):
            self._check_typography_floor(file_path, content, lines)

        if self.config.is_rule_enabled("deck_integrity"):
            self._check_deck_integrity(file_path, content, lines)

        if self.config.is_rule_enabled("information_density"):
            self._check_information_density(file_path, content, lines)

        if self.config.is_rule_enabled("vertical_overflow"):
            self._check_vertical_overflow(file_path, content, lines)

        if self.config.is_rule_enabled("code_wrapping_defect"):
            self._check_code_wrapping_defect(file_path, content, lines)

        if self.config.is_rule_enabled("eyebrow_character_ceiling"):
            self._check_eyebrow_character_ceiling(file_path, content, lines)

    # -----------------------------------------------------------------------
    # Rule Checkers (Scaffold implementations)
    # -----------------------------------------------------------------------

    def _is_suppressed(self, line_no: int, rule_id: str, lines: List[str]) -> bool:
        """Checks if a rule is suppressed via comment on current line or preceding line."""
        check_indices = [line_no - 1]
        if line_no - 2 >= 0:
            check_indices.append(line_no - 2)
            
        for idx in check_indices:
            if idx < len(lines):
                line = lines[idx]
                if "slide-audit-ignore" in line:
                    if f"slide-audit-ignore: {rule_id}" in line or "slide-audit-ignore: all" in line:
                        return True
        return False

    def _find_style_blocks(self, content: str, file_path: Optional[Path] = None) -> List[Tuple[int, str]]:
        """Finds inline style objects style={{ ... }}, CSS blocks { ... }, or className='...'."""
        blocks: List[Tuple[int, str]] = []
        # Pattern for style={{ ... }}
        for match in re.finditer(r"style=\{\{([\s\S]*?)\}\}", content):
            start = match.start(1)
            line_no = content.count("\n", 0, start) + 1
            blocks.append((line_no, match.group(1)))
        
        # Pattern for CSS rule blocks in .css files
        if file_path and file_path.suffix.lower() == ".css":
            for match in re.finditer(r"\{([^{}]*?(?:display|flex-direction|justify-content|background|object-fit)[^{}]*?)\}", content):
                start = match.start(1)
                line_no = content.count("\n", 0, start) + 1
                blocks.append((line_no, match.group(1)))

        # Pattern for Tailwind / utility class strings
        for match in re.finditer(r"(?:className|class)=['\"]([^'\"]*?(?:flex|bg-|object-)[^'\"]*?)['\"]", content):
            start = match.start(1)
            line_no = content.count("\n", 0, start) + 1
            blocks.append((line_no, match.group(1)))
            
        return blocks

    def _check_bottom_deadspace_void(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags hardcoded short container heights (< 620px) or height: '100%' cards with sparse content leaving bottom dead space."""
        min_height = self.config.data.get("deadspace_thresholds", {}).get("min_content_height_px", 620)
        blocks = self._find_style_blocks(content, file_path)
        for line_no, block in blocks:
            if self._is_suppressed(line_no, "bottom_deadspace_void", lines):
                continue
            is_layout = bool(re.search(r"gridTemplateColumns|display:\s*['\"](?:grid|flex)['\"]|\bgrid\b|\bflex\b", block))
            h_match = re.search(r"\bheight:\s*['\"]?(\d{3,4})(?:px)?['\"]?", block)
            if h_match:
                h_val = int(h_match.group(1))
                if is_layout and (200 <= h_val < min_height):
                    snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                    self.issues.append(
                        Issue(
                            file_path=str(file_path),
                            line_no=line_no,
                            rule_id="bottom_deadspace_void",
                            severity=self.config.get_severity("bottom_deadspace_void"),
                            message=f"檢測到版面高度受限產生底部死空間 (height: {h_val}px < {min_height}px)：在 1080p 投影片中會導致下方留白超過 200px。",
                            snippet=snippet,
                            remediation=f"移除固定高度或將主容器改為 height: '100%' / minHeight: {min_height}px，並適當調大卡片內距與間距以填滿垂直版面。",
                        )
                    )

        # Check for Card containers with height: '100%' that lack sufficient content to fill the 1080p canvas
        card_matches = re.finditer(r"<Card\b([^>]*?style=\{\{([^}]*?height:\s*['\"]100%['\"][^}]*?)\}\}[^>]*?>)([\s\S]*?)</Card>", content)
        for match in card_matches:
            card_body = match.group(3)
            start_pos = match.start()
            line_no = content.count("\n", 0, start_pos) + 1
            if self._is_suppressed(line_no, "bottom_deadspace_void", lines):
                continue
            
            # Check if card body has code block, pre, terminal, or image to anchor vertical space
            has_visual_anchor = bool(re.search(r"<pre\b|<CodeBlock\b|font\.mono|<img\b|<svg\b|aspectRatio|gridTemplateRows", card_body))
            # Check if card body uses flex-grow to evenly expand its children vertically
            has_flex_grow = bool(re.search(r"flex:\s*1|\bflex-1\b", card_body))
            # Extract plain text characters inside card
            text_chars = len(re.sub(r"<[^>]+>|[\s\r\n]+", "", card_body))
            
            # If neither visual anchor nor flex-grow expansion is present, and text content is sparse (< 220 chars)
            if not has_visual_anchor and not has_flex_grow and text_chars < 220:
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="bottom_deadspace_void",
                        severity=self.config.get_severity("bottom_deadspace_void"),
                        message="檢測到 100% 高度卡片內部內容不足產生底部大面積空白（卡片下半部留白超過 200px）：內容稀疏且未使用 flex-grow 撐開，導致卡片下半部空洞。",
                        snippet=snippet,
                        remediation="增加實務技術證據（如 Wireshark 封包 Hex/ASCII 終端框），或使用 flex: 1 均勻伸展子區塊自然填滿垂直高度。",
                    )
                )

    def _check_elevator_shaft(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags column flex containers combined with space-between, or marginTop: auto causing mid-card voids."""
        blocks = self._find_style_blocks(content, file_path)
        for line_no, block in blocks:
            if self._is_suppressed(line_no, "elevator_shaft", lines):
                continue
            has_column = bool(re.search(r"flexDirection:\s*['\"]column['\"]|\bflex-col\b|flex-direction:\s*column", block))
            has_space_between = bool(re.search(r"justifyContent:\s*['\"]space-between['\"]|\bjustify-between\b|justify-content:\s*space-between", block))
            has_mt_auto = bool(re.search(r"marginTop:\s*['\"]auto['\"]|margin:\s*['\"]auto\b|\bmt-auto\b|margin-top:\s*auto", block))
            
            if has_column and has_space_between:
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="elevator_shaft",
                        severity=self.config.get_severity("elevator_shaft"),
                        message="檢測到電梯井排版陷阱 (Column + space-between)：同一容器內同時設定縱向排列與 space-between，內容少時將產生大面積死空間空洞。",
                        snippet=snippet,
                        remediation="改用 gap 配合緊湊的排版結構 (flex-start)，或以充足的架構圖、流程文字填滿卡片高度。",
                    )
                )
            elif has_mt_auto:
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="elevator_shaft",
                        severity=self.config.get_severity("elevator_shaft"),
                        message="檢測到電梯井偽滿高陷阱 (marginTop: 'auto' / mt-auto)：強行將元素推至底部，在內容不足時會於中間造成大面積死空間空洞。",
                        snippet=snippet,
                        remediation="移除 marginTop: 'auto' / mt-auto，以充實的架構剖析、案例演練或實體操作步驟自然填滿垂直高度。",
                    )
                )

    def _check_letterboxing_void(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags black background wrapper around images with objectFit contain causing letterboxing."""
        blocks = self._find_style_blocks(content, file_path)
        for line_no, block in blocks:
            if self._is_suppressed(line_no, "letterboxing_void", lines):
                continue
            has_black_bg = bool(re.search(r"background:\s*['\"]#(?:000|000000)['\"]|background:\s*['\"]black['\"]|\bbg-black\b|background-color:\s*black", block))
            has_contain = bool(re.search(r"objectFit:\s*['\"]contain['\"]|\bobject-contain\b|object-fit:\s*contain", block))
            
            if has_black_bg and has_contain:
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="letterboxing_void",
                        severity=self.config.get_severity("letterboxing_void"),
                        message="檢測到黑底無效截圖陷阱 (background: #000 + contain)：在寬高比不符時會產生嚴重黑邊死空間。",
                        snippet=snippet,
                        remediation="移除 #000 容器背景，為容器設定符合截圖實際比例的 aspectRatio，並以 vertical centering 置中。",
                    )
                )

    def _check_semantic_color_inversion(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags defense/mitigation sections using danger red accents."""
        defense_words = self.config.data.get("defense_keywords", [])
        danger_patterns = self.config.data.get("danger_color_patterns", [])

        # Check line by line for slide or card sections
        in_defense_block = False
        defense_block_start = 0

        for idx, line in enumerate(lines, start=1):
            if any(w in line for w in defense_words):
                in_defense_block = True
                defense_block_start = idx

            if in_defense_block:
                if self._is_suppressed(idx, "semantic_color_inversion", lines):
                    continue
                if any(re.search(pat, line) for pat in danger_patterns):
                    self.issues.append(
                        Issue(
                            file_path=str(file_path),
                            line_no=idx,
                            rule_id="semantic_color_inversion",
                            severity=self.config.get_severity("semantic_color_inversion"),
                            message="檢測到防禦/修復卡片使用攻擊紅色語意 (Semantic Color Inversion)。",
                            snippet=line.strip(),
                            remediation="防護、修復與 200 OK 成功應統一採用綠色語意 (如 c.green, #22c55e, #10b981)。",
                        )
                    )
                # Reset after 25 lines if no new trigger
                if idx - defense_block_start > 25:
                    in_defense_block = False

    def _check_ai_fluff(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags empty AI marketing fluff phrases."""
        keywords = self.config.data.get("ai_fluff_keywords", [])
        for idx, line in enumerate(lines, start=1):
            if self._is_suppressed(idx, "ai_fluff", lines):
                continue
            # Skip comments or imports
            clean_line = line.strip()
            if clean_line.startswith("//") or clean_line.startswith("/*") or clean_line.startswith("*"):
                continue
            for kw in keywords:
                if kw in clean_line:
                    self.issues.append(
                        Issue(
                            file_path=str(file_path),
                            line_no=idx,
                            rule_id="ai_fluff",
                            severity=self.config.get_severity("ai_fluff"),
                            message=f"檢測到空泛 AI 虛詞或宣傳口吻: 「{kw}」。",
                            snippet=clean_line,
                            remediation="移除空泛形容詞，改以具體技術機制、協議流程或攻防架構等工程師專業口吻闡述。",
                        )
                    )

    def _check_typography_floor(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Enforces minimum readable typography floor for 1080p decks."""
        thresholds = self.config.data.get("typography_thresholds", {})
        absolute_min = thresholds.get("absolute_min_px", 30)
        card_title_min = thresholds.get("card_title_min_px", 36)
        body_text_min = thresholds.get("body_text_min_px", 30)
        pattern = re.compile(r"fontSize:\s*(\d{1,2})\b")
        for idx, line in enumerate(lines, start=1):
            if self._is_suppressed(idx, "typography_floor", lines):
                continue
            clean_line = line.strip()
            if clean_line.startswith("//") or clean_line.startswith("/*") or clean_line.startswith("*"):
                continue

            # Allow metadata tags (header eyebrow, footer) to have typography in 18-24px
            surrounding = " ".join(lines[max(0, idx - 10):min(len(lines), idx + 10)])
            is_header_eyebrow = "{eyebrow}" in surrounding
            is_footer = "NET-Wireshark" in surrounding or ("current" in surrounding and "total" in surrounding)
            is_metadata_tag = is_header_eyebrow or is_footer

            for match in pattern.finditer(line):
                size = int(match.group(1))
                if is_metadata_tag:
                    if size < 18 or size > 24:
                        self.issues.append(
                            Issue(
                                file_path=str(file_path),
                                line_no=idx,
                                rule_id="typography_floor",
                                severity=self.config.get_severity("typography_floor"),
                                message=f"頁首/頁尾輔助標籤字級超出規範 (fontSize: {size}px，規範為 18px ~ 24px)：避免喧賓奪主或無法辨識。",
                                snippet=clean_line,
                                remediation="頁首眉題與頁尾標籤字級請維持在 18px ~ 24px。",
                            )
                        )
                else:
                    if size < absolute_min:
                        self.issues.append(
                            Issue(
                                file_path=str(file_path),
                                line_no=idx,
                                rule_id="typography_floor",
                                severity=self.config.get_severity("typography_floor"),
                                message=f"檢測到過小字級 (fontSize: {size}px < {absolute_min}px)：在 1080p 滿版簡報中後排學員完全無法辨識。",
                                snippet=clean_line,
                                remediation=f"遵循 1080p 字級地板：所有文字 fontSize ≥ {absolute_min}px（內文 ≥ {body_text_min}px，標題 ≥ {card_title_min}px）。",
                            )
                        )

    def _check_deck_integrity(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Ensures slide deck exports default array and notes array matching slide count."""
        if file_path.suffix.lower() not in {".tsx", ".jsx"}:
            return
        if not ("<Frame" in content or "satisfies Page[]" in content or "notes:" in content or "export default [" in content):
            return

        has_default_export = bool(re.search(r"export\s+default\s+\[", content))
        if not has_default_export:
            self.issues.append(
                Issue(
                    file_path=str(file_path),
                    line_no=len(lines),
                    rule_id="deck_integrity",
                    severity=self.config.get_severity("deck_integrity"),
                    message="投影片缺少 export default 陣列匯出，導致 Open Slide 無法掛載投影片。",
                    snippet="export default [ ... ]",
                    remediation="請確保檔案末尾提供 export default [ Slide1, Slide2, ... ] satisfies Page[]。",
                )
            )

        has_notes = bool(re.search(r"export\s+const\s+notes\s*:\s*string\[\]\s*=\s*\[", content) or re.search(r"export\s+const\s+notes\s*=", content))
        if not has_notes:
            self.issues.append(
                Issue(
                    file_path=str(file_path),
                    line_no=len(lines),
                    rule_id="deck_integrity",
                    severity=self.config.get_severity("deck_integrity"),
                    message="投影片缺少 export const notes: string[] 演講者備忘稿匯出，導致首頁卡片崩潰 (reading '0')。",
                    snippet="export const notes: string[] = [ ... ]",
                    remediation="請定義 export const notes: string[] 陣列，並為每一頁投影片撰寫對應的逐字稿/重點備忘。",
                )
            )

    def _check_information_density(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Enforces information density limits (Rule 6: Single Focus Rule & Anti-Bloat)."""
        thresholds = self.config.data.get("density_thresholds", {})
        max_slide_chars = thresholds.get("max_slide_chars", 750)
        max_card_chars = thresholds.get("max_multicol_card_chars", 180)
        max_boxes = thresholds.get("max_nested_boxes_per_card", 3)

        # 1. Slide-level character check
        for match in re.finditer(r"(<Frame[\s\S]*?</Frame>)", content):
            frame_chunk = match.group(1)
            start_pos = match.start(1)
            line_no = content.count("\n", 0, start_pos) + 1
            if self._is_suppressed(line_no, "information_density", lines):
                continue

            cleaned = re.sub(r"style=\{\{[\s\S]*?\}\}", "", frame_chunk)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            cleaned_text = re.sub(r"\s+", "", cleaned)
            char_count = len(cleaned_text)

            if char_count > max_slide_chars:
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="information_density",
                        severity=self.config.get_severity("information_density"),
                        message=f"檢測到單頁投影片資訊密度超載 (純文字量 {char_count} 字 > {max_slide_chars} 字)：文字量過大，學員在 3~5 秒內無法快速掃描吸收。",
                        snippet=snippet,
                        remediation="遵循單一焦點原則，移除次要教學小卡與贅詞，放大核心字級以維持呼吸感。",
                    )
                )

        # 2. Card-level micro-box and text volume check
        for c_match in re.finditer(r"(<Card[\s\S]*?</Card>)", content):
            card_chunk = c_match.group(1)
            c_start = c_match.start(1)
            c_line_no = content.count("\n", 0, c_start) + 1
            if self._is_suppressed(c_line_no, "information_density", lines):
                continue

            # Count styled nested sub-boxes (e.g. background or border within sub-divs)
            sub_boxes = len(re.findall(r"<div[^>]*?style=\{\{[^}]*?(?:background|border):", card_chunk))
            if sub_boxes > max_boxes:
                snippet = lines[c_line_no - 1].strip() if c_line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=c_line_no,
                        rule_id="information_density",
                        severity=self.config.get_severity("information_density"),
                        message=f"檢測到卡片嵌套過多碎框 (子區塊數量 {sub_boxes} > {max_boxes})：違反單一焦點原則，把投影片當成密集參考手冊。",
                        snippet=snippet,
                        remediation="刪除多餘嵌套小盒子，保留核心問題、排查點與結論（最多 2~3 個區塊）。",
                    )
                )

    def _check_vertical_overflow(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags stacked container structures that cause content to exceed 1080p canvas and collide with footer."""
        for match in re.finditer(r"(<Frame[\s\S]*?</Frame>)", content):
            frame_chunk = match.group(1)
            start_pos = match.start(1)
            line_no = content.count("\n", 0, start_pos) + 1
            if self._is_suppressed(line_no, "vertical_overflow", lines):
                continue

            # Detect top banner Card stacked directly above a grid of Cards
            has_banner_plus_grid = bool(re.search(r"<Card\b[\s\S]*?gridTemplateColumns[\s\S]*?<Card\b", frame_chunk))
            total_cards = len(re.findall(r"<Card\b", frame_chunk))
            total_sub_boxes = len(re.findall(r"<div[^>]*?style=\{\{[^}]*?(?:background|border):", frame_chunk))

            if has_banner_plus_grid and (total_cards >= 4 or total_sub_boxes >= 6):
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="vertical_overflow",
                        severity=self.config.get_severity("vertical_overflow"),
                        message=f"檢測到版面垂直內容堆疊超載 (Vertical Overflow / Footer Collision)：頂部橫幅卡片與下方多欄卡片縱向堆疊 (含 {total_cards} 張卡片與 {total_sub_boxes} 個子區塊)，超出 1080p 安全視區並遮擋底部頁尾文字。",
                        snippet=snippet,
                        remediation="移除頂部贅餘橫幅卡片，讓多欄卡片直接頂格排列；或減少卡片內嵌套盒子數量，確保底部留有 60px 以上安全呼吸感。",
                    )
                )

    def _check_code_wrapping_defect(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags wordBreak: 'break-all' applied to code blocks in multi-column cards that tears keywords across lines."""
        for match in re.finditer(r"wordBreak:\s*['\"]break-all['\"]", content):
            line_no = content.count("\n", 0, match.start()) + 1
            if self._is_suppressed(line_no, "code_wrapping_defect", lines):
                continue
            snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
            prev_snippet = lines[line_no - 2].strip() if line_no >= 2 else ""
            if "font.mono" in snippet or "font.mono" in prev_snippet or "<pre" in snippet or "<pre" in prev_snippet:
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="code_wrapping_defect",
                        severity=self.config.get_severity("code_wrapping_defect"),
                        message="檢測到代碼塊使用 break-all 強制折行 (Code Wrapping Defect)：在窄卡片中會將關鍵字 (如 http、IP 位址) 拆碎換行，嚴重影響可讀性。",
                        snippet=snippet,
                        remediation="移除 break-all，改在邏輯運算子 (如 &&、||) 處手動加入換行 (<br />)，或拓寬卡片寬度。",
                    )
                )

    def _check_eyebrow_character_ceiling(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags eyebrow tags exceeding limit, containing punctuation, timestamps, or residual phaseTags."""
        max_chars = self.config.data.get("eyebrow_max_chars", 16)

        # 1. Enforce Unified Tag (二合一): Disallow phaseTag props on Frame
        for match in re.finditer(r'\bphaseTag\s*=\s*["\'](.*?)["\']', content):
            line_no = content.count("\n", 0, match.start()) + 1
            if self._is_suppressed(line_no, "eyebrow_character_ceiling", lines):
                continue
            snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
            self.issues.append(
                Issue(
                    file_path=str(file_path),
                    line_no=line_no,
                    rule_id="eyebrow_character_ceiling",
                    severity=self.config.get_severity("eyebrow_character_ceiling"),
                    message="檢測到殘留的 phaseTag 雙重標籤：頂部標籤必須二合一（僅允許單一 eyebrow，禁止雙重並排標籤與時間戳記）。",
                    snippet=snippet,
                    remediation="移除 phaseTag 屬性，將模組分類統一收斂至單一 eyebrow 標籤中。",
                )
            )

        # 2. Check each eyebrow
        for match in re.finditer(r'eyebrow=["\'](.*?)["\']', content):
            eyebrow_text = match.group(1).strip()
            line_no = content.count("\n", 0, match.start()) + 1
            if self._is_suppressed(line_no, "eyebrow_character_ceiling", lines):
                continue

            has_sentence_punct = any(p in eyebrow_text for p in ["，", ",", "。", "！", "!", "？", "?", "：", ":"])
            too_long = len(eyebrow_text) > max_chars
            has_timestamp = bool(re.search(r"\b\d{1,2}:\d{2}\b", eyebrow_text))
            has_slang = "幹嘛" in eyebrow_text

            if too_long or has_sentence_punct or has_timestamp or has_slang:
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                reasons = []
                if too_long:
                    reasons.append(f"字數超標 ({len(eyebrow_text)} 字 > {max_chars} 字)")
                if has_sentence_punct:
                    reasons.append("包含句子標點符號")
                if has_timestamp:
                    reasons.append("包含時間戳記 (違反「不需要時間」規範)")
                if has_slang:
                    reasons.append("包含口語化字詞 (「幹嘛」)")

                reason_str = "、".join(reasons)
                self.issues.append(
                    Issue(
                        file_path=str(file_path),
                        line_no=line_no,
                        rule_id="eyebrow_character_ceiling",
                        severity=self.config.get_severity("eyebrow_character_ceiling"),
                        message=f"眉題格式違規 ({reason_str})：眉題 (Eyebrow) 為純粹章節／分類標籤 (如 'REVIEW · 課後思考')，規格必須在 16 字以內且不含時間或標點。",
                        snippet=snippet,
                        remediation="將眉題簡化為 1~2 個單詞加中文標籤 (上限 16 字，如 'SCENARIO · 連線排查')，長述句或心法請放回卡片內文。",
                    )
                )


# ---------------------------------------------------------------------------
# CLI & Formatter
# ---------------------------------------------------------------------------

def format_terminal(issues: List[Issue]) -> str:
    if not issues:
        return "\n\033[32m[PASS] 所有投影片原始碼審查通過！零死空間、零黑邊陷阱、語意色彩正確。\033[0m\n"

    output = ["\n\033[1m=== Slide Deck Audit Report ===\033[0m\n"]
    errors = 0
    warnings = 0

    for issue in issues:
        if issue.severity == "ERROR":
            errors += 1
            badge = "\033[31m[ERROR]\033[0m"
        else:
            warnings += 1
            badge = "\033[33m[WARN]\033[0m"

        output.append(f"{badge} {issue.file_path}:{issue.line_no} ({issue.rule_id})")
        output.append(f"       \033[1m問題:\033[0m {issue.message}")
        if issue.snippet:
            output.append(f"       \033[90m原始碼:\033[0m {issue.snippet}")
        if issue.remediation:
            output.append(f"       \033[36m建議:\033[0m {issue.remediation}")
        output.append("")

    summary_color = "\033[31m" if errors > 0 else "\033[33m"
    output.append(
        f"{summary_color}總計: {errors} 個錯誤 (ERROR), {warnings} 個警告 (WARN)\033[0m\n"
    )
    return "\n".join(output)


def format_json(issues: List[Issue]) -> str:
    return json.dumps([asdict(i) for i in issues], indent=2, ensure_ascii=False)


def format_github(issues: List[Issue]) -> str:
    lines = []
    for issue in issues:
        level = "error" if issue.severity == "ERROR" else "warning"
        msg = f"{issue.message} | 建議: {issue.remediation}"
        lines.append(f"::{level} file={issue.file_path},line={issue.line_no}::{msg}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="slide-deck-auditor: Linter for modern slide presentations and UI cards."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to scan (defaults to current directory).",
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to custom rules.json configuration file.",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["terminal", "json", "github"],
        default="terminal",
        help="Output format (default: terminal).",
    )
    parser.add_argument(
        "--fail-on",
        choices=["error", "warn"],
        default="error",
        help="Exit failure condition: 'error' (default) exits 1 on errors; 'warn' exits 1 on any warning.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose scanning logs.",
    )

    args = parser.parse_args()

    config = Config.load(args.config)
    auditor = SlideDeckAuditor(config, verbose=args.verbose)

    all_issues: List[Issue] = []
    for p in args.paths:
        path_obj = Path(p)
        if path_obj.exists():
            all_issues.extend(auditor.scan_path(path_obj))
        else:
            print(f"[slide-deck-auditor] Path not found: {p}", file=sys.stderr)

    if args.format == "json":
        print(format_json(all_issues))
    elif args.format == "github":
        print(format_github(all_issues))
    else:
        print(format_terminal(all_issues))

    has_errors = any(i.severity == "ERROR" for i in all_issues)
    has_warnings = any(i.severity == "WARN" for i in all_issues)

    if args.fail_on == "warn" and (has_errors or has_warnings):
        return 1
    if has_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
