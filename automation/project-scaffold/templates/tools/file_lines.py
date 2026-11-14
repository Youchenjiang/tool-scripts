"""Source code line count and max-lines quality gate tool.

Scans source code files across languages (.py, .ts, .js, .cs, .go, .rs, .dart, etc.),
calculates line metrics, and enforces single-file length boundaries to prevent
unmaintainable God Files/Classes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".cs",
    ".go",
    ".rs",
    ".dart",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".kt",
    ".swift",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".agent",
    ".vscode",
    ".idea",
    "node_modules",
    "bin",
    "obj",
    "__pycache__",
    "dist",
    "build",
    "out",
    "target",
    ".pytest_cache",
    ".ruff_cache",
    "tests",
    "tools",
    "scripts",
    "docs",
    "assets",
}

DEFAULT_MAX_FILE_LINES = 500


def count_file_lines(file_path: Path) -> int:
    """Count the total number of lines in a file safely."""
    try:
        with open(file_path, "rb") as fh:
            content = fh.read()
            if not content:
                return 0
            count = content.count(b"\n")
            if not content.endswith(b"\n"):
                count += 1
            return count
    except Exception:
        return 0


def load_metrics_config(repo_root: Path) -> dict:
    """Load line metrics config from tools/project.json or project.json."""
    config = {
        "maxFileLines": DEFAULT_MAX_FILE_LINES,
        "sourceDirs": [],
        "extensions": set(DEFAULT_SOURCE_EXTENSIONS),
        "excludeDirs": set(DEFAULT_EXCLUDE_DIRS),
    }

    for p in [repo_root / "tools" / "project.json", repo_root / "project.json"]:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                metrics = data.get("metrics", {})
                if isinstance(metrics, dict):
                    if "maxFileLines" in metrics and isinstance(metrics["maxFileLines"], int):
                        config["maxFileLines"] = metrics["maxFileLines"]
                    if "sourceDirs" in metrics and isinstance(metrics["sourceDirs"], list):
                        config["sourceDirs"] = metrics["sourceDirs"]
                    if "extensions" in metrics and isinstance(metrics["extensions"], list):
                        config["extensions"].update(metrics["extensions"])
                    if "excludeDirs" in metrics and isinstance(metrics["excludeDirs"], list):
                        config["excludeDirs"].update(metrics["excludeDirs"])
                break
            except Exception:
                pass

    return config


def scan_directory(
    repo_root: Path,
    target_dir: Path | None = None,
    extensions: set[str] | None = None,
    exclude_dirs: set[str] | None = None,
) -> dict[str, int]:
    """Scan source files under target_dir and return a dict of {rel_path: line_count}."""
    resolved_root = repo_root.resolve()
    base_dir = (target_dir or resolved_root).resolve()
    exts = extensions or DEFAULT_SOURCE_EXTENSIONS
    excludes = exclude_dirs or DEFAULT_EXCLUDE_DIRS

    results: dict[str, int] = {}

    if not base_dir.is_dir():
        return results

    for dirpath, dirnames, filenames in os.walk(base_dir):
        # Exclude directories in-place
        dirnames[:] = [d for d in dirnames if d not in excludes and not d.startswith(".")]

        current_path = Path(dirpath)
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in exts:
                file_path = current_path / fname
                try:
                    rel_path = file_path.relative_to(resolved_root).as_posix()
                except ValueError:
                    rel_path = file_path.as_posix()
                results[rel_path] = count_file_lines(file_path)

    return dict(sorted(results.items(), key=lambda item: item[1], reverse=True))


def check_line_limits(
    counts: dict[str, int], max_lines: int
) -> list[tuple[str, int]]:
    """Return files that exceed max_lines threshold sorted descending."""
    violations = [
        (filepath, lines)
        for filepath, lines in counts.items()
        if lines > max_lines
    ]
    violations.sort(key=lambda x: x[1], reverse=True)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Source code line count and max-lines quality gate tool."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root directory (default: current working directory).",
    )
    parser.add_argument(
        "--dir",
        help="Specific subfolder to scan (e.g. src). If omitted, automatically checks src/ or root.",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        help="Maximum allowed lines per file before failure (default: from project.json or 500).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Enforce max-lines limit as a quality gate (exit code 1 on violation).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of largest files to display in summary table (default: 20).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw results in JSON format.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Save results dictionary directly to a JSON file (e.g. file_lines.json).",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    config = load_metrics_config(repo_root)

    target_dir = None
    if args.dir:
        target_dir = repo_root / args.dir
    elif config["sourceDirs"]:
        target_dir = repo_root / config["sourceDirs"][0]
    elif (repo_root / "src").is_dir():
        target_dir = repo_root / "src"
    else:
        target_dir = repo_root

    max_lines = args.max_lines if args.max_lines is not None else config["maxFileLines"]

    counts = scan_directory(
        repo_root=repo_root,
        target_dir=target_dir,
        extensions=config["extensions"],
        exclude_dirs=config["excludeDirs"],
    )

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = repo_root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(counts, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[file_lines] Line counts written to: {out_path}")

    if args.json:
        payload = {
            "total_files": len(counts),
            "total_lines": sum(counts.values()),
            "max_lines_limit": max_lines,
            "violations": check_line_limits(counts, max_lines),
            "files": counts,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        if args.check and payload["violations"]:
            return 1
        return 0

    total_lines = sum(counts.values())
    print(f"\n[file_lines] Scanned {len(counts)} source file(s) ({total_lines:,} total lines)")
    print(f"             Scan root: {target_dir.resolve()}")
    print(f"             Max lines limit: {max_lines}\n")

    if counts:
        print(f"{'Lines':>8}  {'File Path'}")
        print(f"{'-' * 8}  {'-' * 60}")
        displayed = 0
        for path, lines in counts.items():
            if displayed >= args.top:
                break
            marker = " ⚠️ [OVER LIMIT]" if lines > max_lines else ""
            print(f"{lines:>8}  {path}{marker}")
            displayed += 1
        if len(counts) > args.top:
            print(f"        ... ({len(counts) - args.top} more files not shown, use --top to increase)")

    violations = check_line_limits(counts, max_lines)
    if violations:
        print(f"\n❌ [GATE FAIL] {len(violations)} file(s) exceeded the {max_lines}-line threshold:")
        for path, lines in violations:
            print(f"   - {path}: {lines} lines (exceeds limit by {lines - max_lines})")
        if args.check:
            return 1
    else:
        print(f"\n✅ [GATE PASS] All {len(counts)} source file(s) are within the {max_lines}-line limit.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
