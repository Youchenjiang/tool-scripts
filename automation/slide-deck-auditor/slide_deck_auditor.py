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
            "elevator_shaft": {"enabled": True, "severity": "ERROR"},
            "letterboxing_void": {"enabled": True, "severity": "ERROR"},
            "semantic_color_inversion": {"enabled": True, "severity": "ERROR"},
            "ai_fluff": {"enabled": True, "severity": "WARN"},
            "typography_floor": {"enabled": True, "severity": "WARN"},
        },
        "ai_fluff_keywords": [
            "科學驗證法則",
            "親眼見證",
            "驚人心智模型",
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
        "typography_thresholds": {
            "card_title_min_px": 32,
            "body_text_min_px": 22,
            "code_font_min_px": 20,
        },
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

    # -----------------------------------------------------------------------
    # Rule Checkers (Scaffold implementations)
    # -----------------------------------------------------------------------

    def _find_style_blocks(self, content: str) -> List[Tuple[int, str]]:
        """Finds inline style objects style={{ ... }} or CSS declaration blocks { ... }."""
        blocks: List[Tuple[int, str]] = []
        # Pattern for style={{ ... }}
        for match in re.finditer(r"style=\{\{([\s\S]*?)\}\}", content):
            start = match.start(1)
            line_no = content.count("\n", 0, start) + 1
            blocks.append((line_no, match.group(1)))
        
        # Pattern for CSS rule blocks .class { ... }
        for match in re.finditer(r"\{([^{}]*?(?:display|flexDirection|justifyContent|background|objectFit)[^{}]*?)\}", content):
            start = match.start(1)
            line_no = content.count("\n", 0, start) + 1
            blocks.append((line_no, match.group(1)))
            
        return blocks

    def _check_elevator_shaft(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags column flex containers combined with space-between in the same style block."""
        blocks = self._find_style_blocks(content)
        for line_no, block in blocks:
            has_column = bool(re.search(r"flexDirection:\s*['\"]column['\"]|flex-col|flex-direction:\s*column", block))
            has_space_between = bool(re.search(r"justifyContent:\s*['\"]space-between['\"]|justify-between|justify-content:\s*space-between", block))
            
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

    def _check_letterboxing_void(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Flags black background wrapper around images with objectFit contain causing letterboxing."""
        blocks = self._find_style_blocks(content)
        for line_no, block in blocks:
            has_black_bg = bool(re.search(r"background:\s*['\"]#(?:000|000000)['\"]|background:\s*['\"]black['\"]|bg-black|background-color:\s*black", block))
            has_contain = bool(re.search(r"objectFit:\s*['\"]contain['\"]|object-contain|object-fit:\s*contain", block))
            
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
        """Warns if font sizes drop below readable floor for 1080p decks."""
        # Simple regex checking fontSize under minimums (e.g. fontSize: 16)
        pattern = re.compile(r"fontSize:\s*(\d{1,2})\b")
        for idx, line in enumerate(lines, start=1):
            for match in pattern.finditer(line):
                size = int(match.group(1))
                if size < 18:
                    self.issues.append(
                        Issue(
                            file_path=str(file_path),
                            line_no=idx,
                            rule_id="typography_floor",
                            severity=self.config.get_severity("typography_floor"),
                            message=f"檢測到過小字級 (fontSize: {size}px)：在 1080p 滿版簡報中後排學員無法辨識。",
                            snippet=line.strip(),
                            remediation="遵循字級地板：卡片標題 ≥ 32~40px，內文 ≥ 24~28px，補充微字 ≥ 20px。",
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
