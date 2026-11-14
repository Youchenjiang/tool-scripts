#!/usr/bin/env python3
"""Release lifecycle verification gate across project archetypes.

Validates git release tags, version files, synchronized package manifests,
and CHANGELOG.md entries against the contract defined in tools/project.json.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SEMVER_REGEX = re.compile(r"^v?(\d+\.\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$")


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


def normalize_version(tag_or_ver):
    if not tag_or_ver:
        return None
    s = tag_or_ver.strip()
    if s.startswith("refs/tags/"):
        s = s[len("refs/tags/"):]
    m = SEMVER_REGEX.match(s)
    if m:
        return m.group(1)
    return None


def verify_npm_version(project_root, version, version_file, sync_files, strict=False):
    errors = []
    vfile = project_root / (version_file or "package.json")
    if not vfile.is_file():
        if strict:
            errors.append(f"Release version file not found: {vfile.name}")
        return errors

    try:
        data = json.loads(vfile.read_text(encoding="utf-8"))
        actual = data.get("version")
        if actual != version:
            errors.append(f"{vfile.name} version mismatch: expected '{version}', found '{actual}'")
    except Exception as e:
        errors.append(f"Error parsing {vfile.name}: {e}")

    for sf in sync_files:
        sf_path = project_root / sf
        if sf_path.is_file():
            try:
                sf_data = json.loads(sf_path.read_text(encoding="utf-8"))
                actual_sf = sf_data.get("version")
                if actual_sf != version:
                    errors.append(f"{sf} version mismatch: expected '{version}', found '{actual_sf}'")
            except Exception as e:
                errors.append(f"Error parsing {sf}: {e}")
    return errors


def verify_dotnet_version(project_root, version, version_file, sync_files, strict=False):
    errors = []
    vfile = project_root / (version_file or "Directory.Build.props")
    if not vfile.is_file():
        if strict:
            errors.append(f"Release version file not found: {vfile.name}")
        return errors

    content = vfile.read_text(encoding="utf-8")
    m = re.search(r"<(?:Version|PackageVersion)>([^<]+)</(?:Version|PackageVersion)>", content)
    if not m:
        errors.append(f"Could not find <Version> or <PackageVersion> in {vfile.name}")
    elif m.group(1).strip() != version:
        errors.append(f"{vfile.name} version mismatch: expected '{version}', found '{m.group(1).strip()}'")

    for sf in sync_files:
        sf_path = project_root / sf
        if sf_path.is_file():
            sf_content = sf_path.read_text(encoding="utf-8")
            m_id = re.search(r'Identity\s+[^>]*Version="([^"]+)"', sf_content, re.IGNORECASE)
            if m_id:
                # AppxManifest uses 4-part version: e.g. 1.2.0.0
                actual_ver = m_id.group(1)
                prefix_ver = ".".join(actual_ver.split(".")[:3])
                if prefix_ver != version and actual_ver != version:
                    errors.append(f"{sf} manifest version mismatch: expected '{version}', found '{actual_ver}'")
    return errors


def verify_python_version(project_root, version, version_file, sync_files, strict=False):
    errors = []
    vfile = project_root / (version_file or "pyproject.toml")
    if not vfile.is_file():
        if strict:
            errors.append(f"Release version file not found: {vfile.name}")
        return errors

    content = vfile.read_text(encoding="utf-8")
    m = re.search(r'(?:^|\n)\s*version\s*=\s*["\']([^"\']+)["\']', content)
    if not m:
        errors.append(f"Could not find 'version = \"...\"' in {vfile.name}")
    elif m.group(1).strip() != version:
        errors.append(f"{vfile.name} version mismatch: expected '{version}', found '{m.group(1).strip()}'")
    return errors


def verify_github_tag(project_root, version, version_file, sync_files, strict=False):
    errors = []
    if version_file:
        vfile = project_root / version_file
        if not vfile.is_file():
            if strict:
                errors.append(f"Release version file not found: {vfile.name}")
            return errors
        content = vfile.read_text(encoding="utf-8").strip()
        norm = normalize_version(content) or content
        if norm != version:
            errors.append(f"{version_file} version mismatch: expected '{version}', found '{content}'")
    return errors


def verify_changelog(project_root, version, raw_tag=None):
    cl_path = project_root / "CHANGELOG.md"
    if not cl_path.is_file():
        return []

    content = cl_path.read_text(encoding="utf-8")
    patterns = [
        re.escape(f"[{version}]"),
        re.escape(f"## {version}"),
        re.escape(f"## [{version}]"),
        re.escape(f"## v{version}"),
        re.escape(f"## [v{version}]"),
    ]
    if raw_tag:
        patterns.append(re.escape(f"[{raw_tag}]"))
        patterns.append(re.escape(f"## {raw_tag}"))

    regex = re.compile("|".join(patterns), re.IGNORECASE)
    if not regex.search(content):
        return [f"CHANGELOG.md does not contain an entry for release version '{version}'"]
    return []


def verify_release(target_tag_or_ver, project_json_path=None, strict=False):
    norm_ver = normalize_version(target_tag_or_ver)
    if not norm_ver:
        return False, [f"Invalid release tag/version format '{target_tag_or_ver}'. Must follow Semantic Versioning (e.g. v1.2.3)"]

    if project_json_path:
        pjson_path = Path(project_json_path).resolve()
    else:
        pjson_path = find_project_json()

    if not pjson_path or not pjson_path.is_file():
        return True, ["[release_checker] No project.json found; skipping release verification."]

    try:
        data = json.loads(pjson_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"Error reading project.json: {e}"]

    project_root = pjson_path.parent.parent if pjson_path.parent.name == "tools" else pjson_path.parent
    rel_cfg = data.get("release", {})
    strategy = (rel_cfg.get("strategy") or "").strip()
    version_file = (rel_cfg.get("versionFile") or "").strip()
    sync_files = rel_cfg.get("syncFiles") or []

    if strategy in ("", "none"):
        return True, [f"[release_checker] Strategy is '{strategy}'; release check skipped."]

    strategy_map = {
        "npm-version": verify_npm_version,
        "dotnet-store": verify_dotnet_version,
        "python-version": verify_python_version,
        "github-tag": verify_github_tag,
    }

    verifier = strategy_map.get(strategy)
    if not verifier:
        return False, [f"Unknown release strategy: '{strategy}'"]

    all_errors = verifier(project_root, norm_ver, version_file, sync_files, strict=strict)
    all_errors.extend(verify_changelog(project_root, norm_ver, raw_tag=target_tag_or_ver))

    if all_errors:
        return False, all_errors

    return True, [f"Release verification passed for version '{norm_ver}' (strategy: {strategy})."]


def main():
    parser = argparse.ArgumentParser(description="Verify release version consistency across project assets.")
    parser.add_argument("--tag", "-t", help="Git release tag (e.g., v1.0.0 or refs/tags/v1.0.0)")
    parser.add_argument("--version", "-v", help="Target release version (e.g., 1.0.0)")
    parser.add_argument("--project-json", help="Path to project.json")
    parser.add_argument("--strict", action="store_true", help="Fail if version files are missing")
    args = parser.parse_args()

    raw_target = args.tag or args.version
    if not raw_target:
        print("Usage: release_checker.py --tag <tag> OR --version <version>", file=sys.stderr)
        return 1

    # Strip refs/tags/ prefix if present from git hook
    if raw_target.startswith("refs/tags/"):
        raw_target = raw_target[len("refs/tags/"):]

    success, messages = verify_release(raw_target, args.project_json, strict=args.strict)
    for msg in messages:
        if success:
            print(f"[release_checker] {msg}")
        else:
            print(f"[release_checker] ERROR: {msg}", file=sys.stderr)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
