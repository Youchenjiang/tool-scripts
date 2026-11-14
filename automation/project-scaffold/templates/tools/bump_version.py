#!/usr/bin/env python3
"""bump_version.py - Automated release version bumping across project archetypes.

Reads the release configuration contract from tools/project.json, calculates
the new semantic version (major, minor, patch, revision, or custom --to), updates
the corresponding version files and synchronization manifests, and inserts a
changelog skeleton into CHANGELOG.md.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

SEMVER_REGEX = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$")


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


def parse_semver(ver_str):
    if not ver_str:
        return None
    m = SEMVER_REGEX.match(ver_str.strip())
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3))
    rev = int(m.group(4)) if m.group(4) is not None else None
    return major, minor, patch, rev


def calculate_next_version(current_ver_str, bump_type="patch", target_ver=None):
    if target_ver:
        parsed = parse_semver(target_ver)
        if not parsed:
            raise ValueError(f"Target version '{target_ver}' is not a valid Semantic Version.")
        # Strip optional leading 'v'
        return target_ver.strip().lstrip("v")

    parsed = parse_semver(current_ver_str)
    if not parsed:
        # Default starting version if unparseable
        return "0.1.1" if bump_type == "patch" else "0.2.0"

    major, minor, patch, rev = parsed

    if rev is not None:
        # 4-part version (e.g. 1.2.3.0)
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
            rev = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
            rev = 0
        elif bump_type == "patch":
            patch += 1
            rev = 0
        elif bump_type == "revision":
            rev += 1
        else:
            raise ValueError(f"Unknown bump type: {bump_type}")
        return f"{major}.{minor}.{patch}.{rev}"
    else:
        # 3-part version (e.g. 1.2.3)
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        elif bump_type == "revision":
            # Upgrade 3-part to 4-part with revision 1
            return f"{major}.{minor}.{patch}.1"
        else:
            raise ValueError(f"Unknown bump type: {bump_type}")
        return f"{major}.{minor}.{patch}"


def get_current_version(project_root, strategy, version_file):
    if strategy == "npm-version":
        vf = project_root / (version_file or "package.json")
        if vf.is_file():
            try:
                data = json.loads(vf.read_text(encoding="utf-8"))
                return data.get("version")
            except Exception:
                pass
    elif strategy == "dotnet-store":
        vf = project_root / (version_file or "Directory.Build.props")
        if vf.is_file():
            content = vf.read_text(encoding="utf-8")
            m = re.search(r"<(?:Version|PackageVersion)>([^<]+)</(?:Version|PackageVersion)>", content)
            if m:
                return m.group(1).strip()
    elif strategy == "python-version":
        vf = project_root / (version_file or "pyproject.toml")
        if vf.is_file():
            content = vf.read_text(encoding="utf-8")
            m = re.search(r'(?:^|\n)\s*version\s*=\s*["\']([^"\']+)["\']', content)
            if m:
                return m.group(1).strip()
    elif strategy == "github-tag":
        vf = project_root / (version_file or "VERSION")
        if vf.is_file():
            return vf.read_text(encoding="utf-8").strip().lstrip("v")

    return "0.1.0"


def bump_npm(project_root, new_version, version_file, sync_files, dry_run=False):
    modified = []
    vf = project_root / (version_file or "package.json")
    if vf.is_file():
        try:
            data = json.loads(vf.read_text(encoding="utf-8"))
            data["version"] = new_version
            if not dry_run:
                vf.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            modified.append(vf.name)
        except Exception as e:
            raise RuntimeError(f"Failed to update {vf.name}: {e}")

    for sf_name in sync_files:
        sf = project_root / sf_name
        if sf.is_file() and sf_name.endswith(".json"):
            try:
                sf_data = json.loads(sf.read_text(encoding="utf-8"))
                sf_data["version"] = new_version
                if "packages" in sf_data and "" in sf_data["packages"]:
                    sf_data["packages"][""]["version"] = new_version
                if not dry_run:
                    sf.write_text(json.dumps(sf_data, indent=2) + "\n", encoding="utf-8")
                modified.append(sf_name)
            except Exception as e:
                raise RuntimeError(f"Failed to update {sf_name}: {e}")
    return modified


def bump_dotnet(project_root, new_version, version_file, sync_files, dry_run=False):
    modified = []
    # Ensure 4-part version for MSIX / Store app manifest compatibility
    parsed = parse_semver(new_version)
    if parsed and parsed[3] is not None:
        ver_4part = new_version
    elif parsed:
        ver_4part = f"{parsed[0]}.{parsed[1]}.{parsed[2]}.0"
    else:
        ver_4part = new_version

    vf = project_root / (version_file or "Directory.Build.props")
    if vf.is_file():
        content = vf.read_text(encoding="utf-8")
        new_content = re.sub(
            r"<(Version|PackageVersion)>([^<]+)</\1>",
            f"<\\1>{new_version}</\\1>",
            content,
        )
        if not dry_run:
            vf.write_text(new_content, encoding="utf-8")
        modified.append(vf.name)

    for sf_name in sync_files:
        sf = project_root / sf_name
        if sf.is_file():
            sf_content = sf.read_text(encoding="utf-8")
            new_sf = re.sub(
                r'(Identity\s+[^>]*Version=")([^"]+)(")',
                f"\\g<1>{ver_4part}\\g<3>",
                sf_content,
                flags=re.IGNORECASE,
            )
            if not dry_run:
                sf.write_text(new_sf, encoding="utf-8")
            modified.append(sf_name)
    return modified


def bump_python(project_root, new_version, version_file, sync_files, dry_run=False):
    modified = []
    vf = project_root / (version_file or "pyproject.toml")
    if vf.is_file():
        content = vf.read_text(encoding="utf-8")
        new_content = re.sub(
            r'(?m)^(\s*version\s*=\s*["\'])([^"\']+)(["\'])',
            f"\\g<1>{new_version}\\g<3>",
            content,
        )
        if not dry_run:
            vf.write_text(new_content, encoding="utf-8")
        modified.append(vf.name)
    return modified


def bump_github_tag(project_root, new_version, version_file, sync_files, dry_run=False):
    modified = []
    vf = project_root / (version_file or "VERSION")
    if not dry_run:
        vf.write_text(f"{new_version}\n", encoding="utf-8")
    modified.append(vf.name)
    return modified


def update_changelog(project_root, new_version, dry_run=False):
    cl_path = project_root / "CHANGELOG.md"
    if not cl_path.is_file():
        return None

    content = cl_path.read_text(encoding="utf-8")
    # Don't add duplicate entry if already exists
    if f"[{new_version}]" in content or f"## {new_version}" in content or f"[v{new_version}]" in content:
        return None

    today = datetime.date.today().isoformat()
    entry = f"\n## [{new_version}] - {today}\n\n- **TODO**: Add changelog entry here\n"

    m = re.search(r"(?im)^#\s+changelog\r?\n", content)
    if m:
        idx = m.end()
        new_content = content[:idx] + entry + content[idx:]
    else:
        new_content = f"# Changelog\n{entry}\n" + content

    if not dry_run:
        cl_path.write_text(new_content, encoding="utf-8")
    return "CHANGELOG.md"


def bump_project_version(bump_type="patch", target_ver=None, project_json_path=None, dry_run=False, no_changelog=False):
    pjson_path = Path(project_json_path).resolve() if project_json_path else find_project_json()
    if not pjson_path or not pjson_path.is_file():
        return False, "tools/project.json not found; cannot determine release strategy."

    try:
        data = json.loads(pjson_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"Failed to parse project.json: {e}"

    project_root = pjson_path.parent.parent if pjson_path.parent.name == "tools" else pjson_path.parent
    rel_cfg = data.get("release", {})
    strategy = (rel_cfg.get("strategy") or "").strip()
    version_file = (rel_cfg.get("versionFile") or "").strip()
    sync_files = rel_cfg.get("syncFiles") or []

    if strategy in ("", "none"):
        return True, f"[bump_version] Strategy is '{strategy}'; version bumping is disabled for this project."

    current_ver = get_current_version(project_root, strategy, version_file)
    try:
        next_ver = calculate_next_version(current_ver, bump_type=bump_type, target_ver=target_ver)
    except Exception as e:
        return False, str(e)

    strategy_map = {
        "npm-version": bump_npm,
        "dotnet-store": bump_dotnet,
        "python-version": bump_python,
        "github-tag": bump_github_tag,
    }

    bumper = strategy_map.get(strategy)
    if not bumper:
        return False, f"Unsupported release strategy: '{strategy}'"

    try:
        modified_files = bumper(project_root, next_ver, version_file, sync_files, dry_run=dry_run)
    except Exception as e:
        return False, str(e)

    if not no_changelog:
        cl_updated = update_changelog(project_root, next_ver, dry_run=dry_run)
        if cl_updated:
            modified_files.append(cl_updated)

    status_tag = "[DRY-RUN] Would bump" if dry_run else "Successfully bumped"
    summary = (
        f"{status_tag} version from '{current_ver}' to '{next_ver}' (strategy: {strategy}).\n"
        f"Modified files ({len(modified_files)}): {', '.join(modified_files) if modified_files else 'None'}"
    )
    return True, summary


def main():
    parser = argparse.ArgumentParser(description="Automated project release version bumping tool.")
    parser.add_argument(
        "type",
        nargs="?",
        default="patch",
        choices=["patch", "minor", "major", "revision"],
        help="Version component to bump (default: patch)",
    )
    parser.add_argument("--to", help="Explicit target version (e.g. 2.0.0 or 1.2.3.4)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Preview version changes without writing to disk")
    parser.add_argument("--no-changelog", action="store_true", help="Skip updating CHANGELOG.md")
    parser.add_argument("--project-json", help="Explicit path to tools/project.json")
    args = parser.parse_args()

    success, message = bump_project_version(
        bump_type=args.type,
        target_ver=args.to,
        project_json_path=args.project_json,
        dry_run=args.dry_run,
        no_changelog=args.no_changelog,
    )
    if success:
        print(f"[bump_version] {message}")
        return 0
    else:
        print(f"[bump_version] ERROR: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
