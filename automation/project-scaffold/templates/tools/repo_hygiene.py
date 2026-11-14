"""Repository structure, directory taxonomy, and hygiene audit tool.

Verifies repository cleanliness, directory organization, and file safety:
1. Root directory and root file whitelists (prevents workspace clutter from AI agents or scratch scripts).
2. Prohibited temporary, scratch, and binary files tracked in Git.
3. Prohibited directories (e.g. archive/, scratch/, tmp/, bin/, obj/ at root).
4. Test segregation and naming conventions (tests belong in tests/, not tools/).
5. Sensitive credentials and local environment files (.env, *.pem, *.key) never tracked.
6. Documentation taxonomy structure (when docs/ exists).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Built-in sensible defaults for modern multi-archetype repositories
DEFAULT_ALLOWED_ROOT_DIRS = {
    ".agent",
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "assets",
    "automation",
    "devops",
    "docs",
    "infra",
    "media",
    "node_modules",
    "packaging",
    "packages",
    "public",
    "scripts",
    "src",
    "tests",
    "third_party",
    "tools",
}

DEFAULT_ALLOWED_ROOT_FILES = {
    ".deepsource.toml",
    ".editorconfig",
    ".env.example",
    ".env.template",
    ".gitattributes",
    ".gitignore",
    ".gitmessage.txt",
    ".npmignore",
    ".pr_agent.toml",
    ".prettierrc",
    ".prettierignore",
    ".sonarcloud.properties",
    "AGENTS.md",
    "CHANGELOG.md",
    "Directory.Build.props",
    "Directory.Build.targets",
    "LICENSE",
    "LICENSE.txt",
    "MEMORY.md",
    "Package.appxmanifest",
    "PRIVACY.md",
    "README.md",
    "README.*.md",
    "THIRD-PARTY-NOTICES.txt",
    "VERSION",
    "environment.yml",
    "eslint.config.mjs",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "requirements*.txt",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "tsconfig.json",
    "tsconfig.*.json",
    "vite.config.*",
    "webpack.config.*",
    "*.sln",
}

DEFAULT_ALLOWED_DOCS_DIRS = {
    "adr",
    "api",
    "architecture",
    "development",
    "guides",
    "history",
    "specs",
    "store",
}

DEFAULT_ALLOWED_DOCS_FILES = {
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "README.md",
    "ROADMAP.md",
    "TECHNICAL_NOTES.md",
}

DEFAULT_BANNED_ROOT_DIRS = {
    "archive",
    "bin",
    "obj",
    "scratch",
    "temp",
    "tmp",
}

DEFAULT_BANNED_FILE_PATTERNS = [
    ".tmp",
    ".temp",
    ".log",
    ".bak",
    ".swp",
    ".swo",
    "__pycache__",
    ".suo",
    ".user",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
]

DEFAULT_SENSITIVE_PATTERNS = [
    ".env",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
]


def matches_any_pattern(name: str, patterns: set[str] | list[str]) -> bool:
    """Return True if name matches any pattern directly or via fnmatch."""
    for pat in patterns:
        if pat == name or fnmatch.fnmatch(name, pat):
            return True
    return False


def load_hygiene_config(repo_root: Path) -> dict:
    """Load hygiene config from tools/project.json or project.json, falling back to defaults."""
    config = {
        "allowedRootDirs": set(DEFAULT_ALLOWED_ROOT_DIRS),
        "allowedRootFiles": set(DEFAULT_ALLOWED_ROOT_FILES),
        "allowedDocsDirs": set(DEFAULT_ALLOWED_DOCS_DIRS),
        "allowedDocsFiles": set(DEFAULT_ALLOWED_DOCS_FILES),
        "bannedRootDirs": set(DEFAULT_BANNED_ROOT_DIRS),
        "bannedFilePatterns": list(DEFAULT_BANNED_FILE_PATTERNS),
        "sensitivePatterns": list(DEFAULT_SENSITIVE_PATTERNS),
    }

    project_json_paths = [
        repo_root / "tools" / "project.json",
        repo_root / "project.json",
    ]

    for p in project_json_paths:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                hygiene_data = data.get("hygiene", {})
                if isinstance(hygiene_data, dict):
                    if "allowedRootDirs" in hygiene_data:
                        config["allowedRootDirs"].update(hygiene_data["allowedRootDirs"])
                    if "allowedRootFiles" in hygiene_data:
                        config["allowedRootFiles"].update(hygiene_data["allowedRootFiles"])
                    if "allowedDocsDirs" in hygiene_data:
                        config["allowedDocsDirs"].update(hygiene_data["allowedDocsDirs"])
                    if "allowedDocsFiles" in hygiene_data:
                        config["allowedDocsFiles"].update(hygiene_data["allowedDocsFiles"])
                    if "bannedRootDirs" in hygiene_data:
                        config["bannedRootDirs"].update(hygiene_data["bannedRootDirs"])
                    if "bannedFilePatterns" in hygiene_data:
                        config["bannedFilePatterns"].extend(hygiene_data["bannedFilePatterns"])
                    if "sensitivePatterns" in hygiene_data:
                        config["sensitivePatterns"].extend(hygiene_data["sensitivePatterns"])
                break
            except Exception:
                pass

    return config


def get_git_tracked_files(repo_root: Path) -> list[str] | None:
    """Return list of git-tracked files relative to repo root, or None if git is unavailable."""
    git_bin = shutil.which("git")
    if not git_bin:
        return None
    try:
        proc = subprocess.run(
            [git_bin, "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc.returncode != 0:
            return None
        return [
            line.strip().replace("\\", "/")
            for line in proc.stdout.splitlines()
            if line.strip()
        ]
    except Exception:
        return None


def check_banned_directories(repo_root: Path, config: dict) -> list[str]:
    """Check that deprecated or banned directories do not exist at root."""
    violations = []
    banned = config.get("bannedRootDirs", DEFAULT_BANNED_ROOT_DIRS)
    for dirname in banned:
        target = repo_root / dirname
        if target.exists():
            violations.append(f"Banned directory '{dirname}' exists at repository root.")
    return violations


def check_root_directories(
    repo_root: Path, config: dict, tracked_files: list[str] | None = None
) -> list[str]:
    """Check root directories against allowed whitelist."""
    violations = []
    allowed = config.get("allowedRootDirs", DEFAULT_ALLOWED_ROOT_DIRS)

    # 1. Check git-tracked root directories if git is available
    if tracked_files is not None:
        tracked_root_dirs = {
            f.split("/")[0] for f in tracked_files if "/" in f
        }
        for d in tracked_root_dirs:
            if not matches_any_pattern(d, allowed):
                violations.append(f"Unexpected tracked root directory found: '{d}'")

    # 2. Check physical filesystem root directories (skip unversioned ignored noise)
    ignored_fs = {".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__"}
    if repo_root.is_dir():
        for item in repo_root.iterdir():
            if item.is_dir() and item.name not in ignored_fs:
                if not matches_any_pattern(item.name, allowed):
                    msg = f"Untracked or unexpected directory on disk at root: '{item.name}'"
                    if msg not in violations:
                        violations.append(msg)

    return violations


def check_root_files(
    repo_root: Path, config: dict, tracked_files: list[str] | None = None
) -> list[str]:
    """Check root files against allowed whitelist."""
    violations = []
    allowed = config.get("allowedRootFiles", DEFAULT_ALLOWED_ROOT_FILES)

    # 1. Check git-tracked root files if git is available
    if tracked_files is not None:
        tracked_root_files = {
            f for f in tracked_files if "/" not in f
        }
        for f in tracked_root_files:
            if not matches_any_pattern(f, allowed):
                violations.append(f"Unexpected tracked root file found: '{f}'")

    # 2. Check physical filesystem root files
    if repo_root.is_dir():
        for item in repo_root.iterdir():
            if item.is_file():
                if not matches_any_pattern(item.name, allowed):
                    msg = f"Unexpected root file on disk: '{item.name}'"
                    if msg not in violations:
                        violations.append(msg)

    return violations


def check_banned_tracked_files(
    tracked_files: list[str] | None, config: dict
) -> list[str]:
    """Ensure temporary, scratch, or build files are never tracked by Git."""
    if tracked_files is None:
        return []
    violations = []
    banned_patterns = config.get("bannedFilePatterns", DEFAULT_BANNED_FILE_PATTERNS)

    for f in tracked_files:
        filename = f.split("/")[-1]
        for pat in banned_patterns:
            if f.endswith(pat) or filename.endswith(pat) or f"/{pat}/" in f:
                violations.append(
                    f"Banned temporary/scratch artifact tracked by git: '{f}' (matches '{pat}')"
                )
                break
    return violations


def check_sensitive_tracked_files(
    tracked_files: list[str] | None, config: dict
) -> list[str]:
    """Ensure secrets, credentials, or local environment files are never tracked."""
    if tracked_files is None:
        return []
    violations = []
    sensitive_patterns = config.get("sensitivePatterns", DEFAULT_SENSITIVE_PATTERNS)

    for f in tracked_files:
        filename = f.split("/")[-1]
        # Allow .env.example, .env.template, .env.sample
        if filename.startswith(".env") and (
            filename.endswith(".example")
            or filename.endswith(".template")
            or filename.endswith(".sample")
        ):
            continue

        for pat in sensitive_patterns:
            if filename == pat or fnmatch.fnmatch(filename, pat) or f.endswith(pat):
                violations.append(
                    f"Sensitive file tracked by git: '{f}' (violates credential protection rule)"
                )
                break
    return violations


def check_test_segregation(repo_root: Path) -> list[str]:
    """Ensure test files reside in tests/, not tools/, and follow test naming conventions."""
    violations = []

    # 1. tools/ must not contain test_*.py
    tools_dir = repo_root / "tools"
    if tools_dir.is_dir():
        misplaced = list(tools_dir.glob("test_*.py"))
        if misplaced:
            for p in misplaced:
                violations.append(
                    f"Misplaced test file in tools/: '{p.name}'. Tests must reside in tests/."
                )

    # 2. tests/ files should follow conventions
    tests_dir = repo_root / "tests"
    if tests_dir.is_dir():
        for p in tests_dir.glob("*.py"):
            name = p.name
            is_valid = (
                name.startswith("test_")
                or name.endswith("_test.py")
                or name.startswith("_")
                or name in {"conftest.py", "__init__.py"}
            )
            if not is_valid:
                violations.append(
                    f"Test file '{name}' in tests/ does not follow naming convention (expected 'test_*.py' or '*_test.py')."
                )

    return violations


def check_docs_structure(repo_root: Path, config: dict) -> list[str]:
    """Ensure docs/ root files and subdirectories adhere to taxonomy."""
    docs_dir = repo_root / "docs"
    if not docs_dir.is_dir():
        return []

    violations = []
    allowed_dirs = config.get("allowedDocsDirs", DEFAULT_ALLOWED_DOCS_DIRS)
    allowed_files = config.get("allowedDocsFiles", DEFAULT_ALLOWED_DOCS_FILES)

    for item in docs_dir.iterdir():
        if item.is_dir():
            if not matches_any_pattern(item.name, allowed_dirs):
                violations.append(f"Unexpected subdirectory in docs/: '{item.name}'")
        elif item.is_file():
            if not matches_any_pattern(item.name, allowed_files):
                violations.append(f"Unexpected file at docs/ root: '{item.name}'")

    return violations


def run_hygiene_audit(repo_root: Path, config: dict | None = None) -> dict:
    """Run all repository hygiene checks and return structured results."""
    resolved_root = repo_root.resolve()
    if config is None:
        config = load_hygiene_config(resolved_root)

    tracked_files = get_git_tracked_files(resolved_root)

    results = {
        "banned_dirs": check_banned_directories(resolved_root, config),
        "root_dirs": check_root_directories(resolved_root, config, tracked_files),
        "root_files": check_root_files(resolved_root, config, tracked_files),
        "banned_tracked_files": check_banned_tracked_files(tracked_files, config),
        "sensitive_files": check_sensitive_tracked_files(tracked_files, config),
        "test_segregation": check_test_segregation(resolved_root),
        "docs_structure": check_docs_structure(resolved_root, config),
    }

    all_violations = []
    for check_name, violations in results.items():
        all_violations.extend(violations)

    passed = len(all_violations) == 0
    return {
        "passed": passed,
        "violations": results,
        "total_violations": len(all_violations),
        "all_violations": all_violations,
        "git_tracked_count": len(tracked_files) if tracked_files is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repository structure, file taxonomy, and hygiene audit tool."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root directory to inspect (default: current working directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed check status even if clean.",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    report = run_hygiene_audit(repo_root)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["passed"] else 1

    if report["passed"]:
        tracked_info = (
            f" ({report['git_tracked_count']} tracked files inspected)"
            if report["git_tracked_count"] is not None
            else ""
        )
        print(f"[repo_hygiene] Repository hygiene verification passed!{tracked_info}")
        if args.verbose:
            print("  ✓ Root directory whitelist verified.")
            print("  ✓ Root file whitelist verified.")
            print("  ✓ No banned directories exist.")
            print("  ✓ No temporary/scratch artifacts tracked.")
            print("  ✓ No sensitive/credential files tracked.")
            print("  ✓ Test segregation and naming verified.")
            print("  ✓ Docs taxonomy verified.")
        return 0

    print(
        f"[repo_hygiene] ERROR: Repository hygiene audit failed with {report['total_violations']} violation(s):",
        file=sys.stderr,
    )
    for category, errs in report["violations"].items():
        if errs:
            print(f"\n[{category.upper()}]", file=sys.stderr)
            for err in errs:
                print(f"  ❌ {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
