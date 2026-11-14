import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from release_checker import (
    normalize_version,
    verify_npm_version,
    verify_dotnet_version,
    verify_python_version,
    verify_github_tag,
    verify_changelog,
    verify_release,
    main,
)


class NormalizeVersionTests(unittest.TestCase):
    def test_valid_semver(self):
        self.assertEqual("1.2.3", normalize_version("1.2.3"))
        self.assertEqual("1.2.3", normalize_version("v1.2.3"))
        self.assertEqual("0.1.0-alpha.1", normalize_version("v0.1.0-alpha.1"))
        self.assertEqual("2.0.0+build123", normalize_version("2.0.0+build123"))
        self.assertEqual("1.2.3.0", normalize_version("v1.2.3.0"))

    def test_invalid_versions(self):
        self.assertIsNone(normalize_version(""))
        self.assertIsNone(normalize_version(None))
        self.assertIsNone(normalize_version("invalid"))
        self.assertIsNone(normalize_version("v1.2"))
        self.assertIsNone(normalize_version("version_1"))


class NpmReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_npm_matching_version(self):
        (self.tmp / "package.json").write_text(json.dumps({"name": "app", "version": "1.0.0"}), encoding="utf-8")
        (self.tmp / "package-lock.json").write_text(json.dumps({"name": "app", "version": "1.0.0"}), encoding="utf-8")

        errors = verify_npm_version(self.tmp, "1.0.0", "package.json", ["package-lock.json"])
        self.assertEqual([], errors)

    def test_npm_version_mismatch(self):
        (self.tmp / "package.json").write_text(json.dumps({"name": "app", "version": "0.9.0"}), encoding="utf-8")

        errors = verify_npm_version(self.tmp, "1.0.0", "package.json", [])
        self.assertTrue(any("mismatch" in e for e in errors))

    def test_npm_missing_package_json_strict(self):
        errors = verify_npm_version(self.tmp, "1.0.0", "package.json", [], strict=True)
        self.assertTrue(any("not found" in e for e in errors))

    def test_npm_missing_package_json_relaxed(self):
        errors = verify_npm_version(self.tmp, "1.0.0", "package.json", [], strict=False)
        self.assertEqual([], errors)

    def test_npm_sync_file_mismatch(self):
        (self.tmp / "package.json").write_text(json.dumps({"name": "app", "version": "1.0.0"}), encoding="utf-8")
        (self.tmp / "package-lock.json").write_text(json.dumps({"name": "app", "version": "0.9.0"}), encoding="utf-8")

        errors = verify_npm_version(self.tmp, "1.0.0", "package.json", ["package-lock.json"])
        self.assertTrue(any("package-lock.json version mismatch" in e for e in errors))


class DotnetReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dotnet_matching_version(self):
        props = "<Project><PropertyGroup><Version>2.1.0</Version></PropertyGroup></Project>"
        (self.tmp / "Directory.Build.props").write_text(props, encoding="utf-8")

        manifest = '<Package><Identity Name="Test" Version="2.1.0.0" /></Package>'
        (self.tmp / "Package.appxmanifest").write_text(manifest, encoding="utf-8")

        errors = verify_dotnet_version(self.tmp, "2.1.0", "Directory.Build.props", ["Package.appxmanifest"])
        self.assertEqual([], errors)

    def test_dotnet_version_mismatch(self):
        props = "<Project><PropertyGroup><Version>1.0.0</Version></PropertyGroup></Project>"
        (self.tmp / "Directory.Build.props").write_text(props, encoding="utf-8")

        errors = verify_dotnet_version(self.tmp, "2.0.0", "Directory.Build.props", [])
        self.assertTrue(any("mismatch" in e for e in errors))

    def test_dotnet_manifest_mismatch(self):
        props = "<Project><PropertyGroup><Version>2.0.0</Version></PropertyGroup></Project>"
        (self.tmp / "Directory.Build.props").write_text(props, encoding="utf-8")

        manifest = '<Package><Identity Name="Test" Version="1.5.0.0" /></Package>'
        (self.tmp / "Package.appxmanifest").write_text(manifest, encoding="utf-8")

        errors = verify_dotnet_version(self.tmp, "2.0.0", "Directory.Build.props", ["Package.appxmanifest"])
        self.assertTrue(any("manifest version mismatch" in e for e in errors))


class PythonReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_python_matching_version(self):
        toml = '[project]\nname = "poc"\nversion = "0.5.2"\n'
        (self.tmp / "pyproject.toml").write_text(toml, encoding="utf-8")

        errors = verify_python_version(self.tmp, "0.5.2", "pyproject.toml", [])
        self.assertEqual([], errors)

    def test_python_version_mismatch(self):
        toml = '[project]\nname = "poc"\nversion = "0.5.0"\n'
        (self.tmp / "pyproject.toml").write_text(toml, encoding="utf-8")

        errors = verify_python_version(self.tmp, "0.5.2", "pyproject.toml", [])
        self.assertTrue(any("mismatch" in e for e in errors))


class GithubTagReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_version_file_matching(self):
        (self.tmp / "VERSION").write_text("v1.3.0\n", encoding="utf-8")
        errors = verify_github_tag(self.tmp, "1.3.0", "VERSION", [])
        self.assertEqual([], errors)

    def test_version_file_mismatch(self):
        (self.tmp / "VERSION").write_text("v1.2.0\n", encoding="utf-8")
        errors = verify_github_tag(self.tmp, "1.3.0", "VERSION", [])
        self.assertTrue(any("mismatch" in e for e in errors))


class ChangelogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_changelog_found(self):
        cl = "# Changelog\n\n## [1.2.0] - 2026-11-14\n- Initial release\n"
        (self.tmp / "CHANGELOG.md").write_text(cl, encoding="utf-8")
        self.assertEqual([], verify_changelog(self.tmp, "1.2.0"))

    def test_changelog_not_found(self):
        cl = "# Changelog\n\n## [1.1.0] - 2026-11-01\n- Initial release\n"
        (self.tmp / "CHANGELOG.md").write_text(cl, encoding="utf-8")
        errors = verify_changelog(self.tmp, "1.2.0")
        self.assertTrue(any("CHANGELOG.md does not contain" in e for e in errors))

    def test_missing_changelog_file_is_optional(self):
        self.assertEqual([], verify_changelog(self.tmp, "1.2.0"))


class VerifyReleaseEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tools_dir = self.tmp / "tools"
        self.tools_dir.mkdir(parents=True)
        self.pjson_path = self.tools_dir / "project.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_invalid_tag_format(self):
        success, messages = verify_release("not-a-semver", str(self.pjson_path))
        self.assertFalse(success)
        self.assertTrue(any("Semantic Versioning" in m for m in messages))

    def test_strategy_none_skips(self):
        pjson = {"archetype": "test", "release": {"strategy": "none"}}
        self.pjson_path.write_text(json.dumps(pjson), encoding="utf-8")

        success, messages = verify_release("v1.0.0", str(self.pjson_path))
        self.assertTrue(success)
        self.assertTrue(any("skipped" in m for m in messages))

    def test_full_flow_success(self):
        pjson = {
            "archetype": "web-spa",
            "release": {
                "strategy": "npm-version",
                "versionFile": "package.json",
                "syncFiles": ["package-lock.json"],
            },
        }
        self.pjson_path.write_text(json.dumps(pjson), encoding="utf-8")
        (self.tmp / "package.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
        (self.tmp / "package-lock.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
        (self.tmp / "CHANGELOG.md").write_text("## [1.0.0]\n- Launch", encoding="utf-8")

        success, messages = verify_release("refs/tags/v1.0.0", str(self.pjson_path))
        self.assertTrue(success)
        self.assertTrue(any("passed" in m for m in messages))

    def test_full_flow_version_mismatch_failure(self):
        pjson = {
            "archetype": "web-spa",
            "release": {
                "strategy": "npm-version",
                "versionFile": "package.json",
                "syncFiles": [],
            },
        }
        self.pjson_path.write_text(json.dumps(pjson), encoding="utf-8")
        (self.tmp / "package.json").write_text(json.dumps({"version": "0.9.0"}), encoding="utf-8")

        success, messages = verify_release("v1.0.0", str(self.pjson_path))
        self.assertFalse(success)
        self.assertTrue(any("version mismatch" in m for m in messages))

    def test_cli_main_success(self):
        pjson = {
            "archetype": "script-tool",
            "release": {"strategy": "github-tag", "versionFile": "VERSION", "syncFiles": []},
        }
        self.pjson_path.write_text(json.dumps(pjson), encoding="utf-8")
        (self.tmp / "VERSION").write_text("1.0.0\n", encoding="utf-8")

        with patch("sys.argv", ["release_checker.py", "--tag", "refs/tags/v1.0.0", "--project-json", str(self.pjson_path)]):
            ret = main()
            self.assertEqual(0, ret)

    def test_cli_main_failure(self):
        pjson = {
            "archetype": "script-tool",
            "release": {"strategy": "github-tag", "versionFile": "VERSION", "syncFiles": []},
        }
        self.pjson_path.write_text(json.dumps(pjson), encoding="utf-8")
        (self.tmp / "VERSION").write_text("0.9.0\n", encoding="utf-8")

        with patch("sys.argv", ["release_checker.py", "--tag", "v1.0.0", "--project-json", str(self.pjson_path)]):
            ret = main()
            self.assertEqual(1, ret)


if __name__ == "__main__":
    unittest.main()
