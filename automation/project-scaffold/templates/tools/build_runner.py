#!/usr/bin/env python3
"""Execute build, test, and lint commands defined in tools/project.json."""

import json
import os
import subprocess
import sys
from pathlib import Path


def find_project_json(start_dir=None):
    cur = Path(start_dir or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        p = d / "tools" / "project.json"
        if p.is_file():
            return p
        p_root = d / "project.json"
        if p_root.is_file():
            return p_root
    return None


def should_skip_command(cmd, project_root):
    """Check if command should be skipped because relevant files don't exist."""
    cmd_lower = cmd.lower()
    root = Path(project_root)

    # Node.js commands: skip if package.json does not exist
    if any(cmd_lower.startswith(prefix) for prefix in ("npm ", "npx ", "yarn ", "pnpm ")):
        if not (root / "package.json").is_file():
            return True, "package.json not found"

    # .NET commands: skip if no .sln or .*proj file exists
    if cmd_lower.startswith("dotnet "):
        has_dotnet = any(root.glob("*.sln")) or any(root.glob("*.*proj")) or any(root.glob("**/*.csproj"))
        if not has_dotnet:
            return True, "no .NET solution or project files found"

    # Python test commands: skip if tests directory does not exist
    if "unittest" in cmd_lower or "pytest" in cmd_lower:
        if not (root / "tests").is_dir() and not (root / "test").is_dir():
            return True, "tests directory not found"

    # Python flake8 lint: skip if no python files exist outside tools/
    if "flake8" in cmd_lower:
        py_files = [f for f in root.glob("*.py") if f.name != "setup.py"]
        if not py_files and not (root / "src").is_dir():
            return True, "no python source files found"

    return False, ""


def run_stage(stage_name, cmd, project_root):
    if not cmd or not cmd.strip():
        return True

    cmd = cmd.strip()
    skip, reason = should_skip_command(cmd, project_root)
    if skip:
        print(f"[build_runner] {stage_name}: skipped ({reason})")
        return True

    print(f"[build_runner] {stage_name}: executing '{cmd}'...")
    res = subprocess.run(cmd, shell=True, cwd=str(project_root))
    if res.returncode != 0:
        print(f"[build_runner] ERROR: {stage_name} failed with exit code {res.returncode}", file=sys.stderr)
        return False
    return True


def run_all(project_json_path=None):
    pjson_path = project_json_path or find_project_json()
    if not pjson_path or not Path(pjson_path).is_file():
        print("[build_runner] No project.json found; skipping build checks.")
        return 0

    try:
        data = json.loads(pjson_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[build_runner] ERROR parsing {pjson_path}: {e}", file=sys.stderr)
        return 1

    project_root = pjson_path.parent.parent if pjson_path.parent.name == "tools" else pjson_path.parent
    build_cfg = data.get("build", {})
    if not build_cfg:
        print("[build_runner] No build configuration in project.json; baseline check passed.")
        return 0

    stages = [
        ("lint", build_cfg.get("lint", "")),
        ("test", build_cfg.get("test", "")),
        ("build", build_cfg.get("build", "")),
    ]

    for stage_name, cmd in stages:
        if not run_stage(stage_name, cmd, project_root):
            return 1

    print("[build_runner] All configured build and test checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run_all())
