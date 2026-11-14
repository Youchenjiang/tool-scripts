import datetime
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

import bump_version
import release_checker


class CalculateNextVersionTests(unittest.TestCase):
    def test_3part_semver(self):
        self.assertEqual("1.0.1", bump_version.calculate_next_version("1.0.0", "patch"))
        self.assertEqual("1.1.0", bump_version.calculate_next_version("1.0.4", "minor"))
        self.assertEqual("2.0.0", bump_version.calculate_next_version("1.2.3", "major"))
        self.assertEqual("1.2.3.1", bump_version.calculate_next_version("1.2.3", "revision"))

    def test_4part_semver(self):
        self.assertEqual("1.2.3.1", bump_version.calculate_next_version("1.2.3.0", "revision"))
        self.assertEqual("1.2.4.0", bump_version.calculate_next_version("1.2.3.4", "patch"))
        self.assertEqual("1.3.0.0", bump_version.calculate_next_version("1.2.3.4", "minor"))
        self.assertEqual("2.0.0.0", bump_version.calculate_next_version("1.2.3.4", "major"))

    def test_explicit_target_version(self):
        self.assertEqual("3.0.0", bump_version.calculate_next_version("1.0.0", target_ver="3.0.0"))
        self.assertEqual("3.0.0", bump_version.calculate_next_version("1.0.0", target_ver="v3.0.0"))
        with self.assertRaises(ValueError):
            bump_version.calculate_next_version("1.0.0", target_ver="invalid-ver")


class NpmBumperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_npm_bump_updates_package_and_lock(self):
        pkg = {"name": "app", "version": "1.0.0"}
        lock = {"name": "app", "version": "1.0.0", "packages": {"": {"version": "1.0.0"}}}
        (self.tmp / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        (self.tmp / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")

        modified = bump_version.bump_npm(self.tmp, "1.1.0", "package.json", ["package-lock.json"])
        self.assertIn("package.json", modified)
        self.assertIn("package-lock.json", modified)

        res_pkg = json.loads((self.tmp / "package.json").read_text(encoding="utf-8"))
        res_lock = json.loads((self.tmp / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual("1.1.0", res_pkg["version"])
        self.assertEqual("1.1.0", res_lock["version"])
        self.assertEqual("1.1.0", res_lock["packages"][""]["version"])

    def test_npm_dry_run_does_not_modify(self):
        pkg = {"name": "app", "version": "1.0.0"}
        (self.tmp / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

        bump_version.bump_npm(self.tmp, "2.0.0", "package.json", [], dry_run=True)
        res_pkg = json.loads((self.tmp / "package.json").read_text(encoding="utf-8"))
        self.assertEqual("1.0.0", res_pkg["version"])


class DotnetBumperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dotnet_bump_updates_props_and_manifest(self):
        props = "<Project><PropertyGroup><Version>1.0.0</Version><PackageVersion>1.0.0</PackageVersion></PropertyGroup></Project>"
        manifest = '<Package><Identity Name="App" Version="1.0.0.0" Publisher="CN=Test" /></Package>'
        (self.tmp / "Directory.Build.props").write_text(props, encoding="utf-8")
        (self.tmp / "Package.appxmanifest").write_text(manifest, encoding="utf-8")

        modified = bump_version.bump_dotnet(self.tmp, "1.1.0", "Directory.Build.props", ["Package.appxmanifest"])
        self.assertIn("Directory.Build.props", modified)
        self.assertIn("Package.appxmanifest", modified)

        res_props = (self.tmp / "Directory.Build.props").read_text(encoding="utf-8")
        res_mani = (self.tmp / "Package.appxmanifest").read_text(encoding="utf-8")
        self.assertIn("<Version>1.1.0</Version>", res_props)
        self.assertIn('<Identity Name="App" Version="1.1.0.0"', res_mani)


class PythonAndTagBumperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_python_bump(self):
        toml = '[project]\nname = "poc"\nversion = "0.1.0"\n'
        (self.tmp / "pyproject.toml").write_text(toml, encoding="utf-8")

        modified = bump_version.bump_python(self.tmp, "0.2.0", "pyproject.toml", [])
        self.assertIn("pyproject.toml", modified)
        res_toml = (self.tmp / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = "0.2.0"', res_toml)

    def test_github_tag_bump(self):
        (self.tmp / "VERSION").write_text("0.1.0\n", encoding="utf-8")

        modified = bump_version.bump_github_tag(self.tmp, "0.1.1", "VERSION", [])
        self.assertIn("VERSION", modified)
        res_ver = (self.tmp / "VERSION").read_text(encoding="utf-8")
        self.assertEqual("0.1.1\n", res_ver)


class ChangelogUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_insert_into_changelog(self):
        (self.tmp / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0] - 2026-01-01\n- Initial\n", encoding="utf-8")
        res = bump_version.update_changelog(self.tmp, "1.1.0")
        self.assertEqual("CHANGELOG.md", res)

        content = (self.tmp / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [1.1.0] - ", content)
        self.assertIn("TODO", content)

    def test_skip_duplicate_version(self):
        (self.tmp / "CHANGELOG.md").write_text("# Changelog\n\n## [1.1.0] - 2026-01-01\n- Initial\n", encoding="utf-8")
        res = bump_version.update_changelog(self.tmp, "1.1.0")
        self.assertIsNone(res)


class EndToEndBumpAndVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.tools = self.tmp / "tools"
        self.tools.mkdir(parents=True)
        self.pjson = self.tools / "project.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_strategy_none_skips(self):
        pjson_data = {"release": {"strategy": "none"}}
        self.pjson.write_text(json.dumps(pjson_data), encoding="utf-8")

        success, msg = bump_version.bump_project_version(project_json_path=str(self.pjson))
        self.assertTrue(success)
        self.assertIn("disabled", msg)

    def test_bump_version_then_release_checker_passes(self):
        # 1. Setup npm-version project at 1.0.0
        pjson_data = {
            "archetype": "web-spa",
            "release": {
                "strategy": "npm-version",
                "versionFile": "package.json",
                "syncFiles": ["package-lock.json"],
            },
        }
        self.pjson.write_text(json.dumps(pjson_data), encoding="utf-8")
        (self.tmp / "package.json").write_text(json.dumps({"name": "app", "version": "1.0.0"}), encoding="utf-8")
        (self.tmp / "package-lock.json").write_text(json.dumps({"name": "app", "version": "1.0.0"}), encoding="utf-8")
        (self.tmp / "CHANGELOG.md").write_text("# Changelog\n\n## [1.0.0] - 2026-01-01\n- Initial", encoding="utf-8")

        # 2. Bump minor: 1.0.0 -> 1.1.0
        success, msg = bump_version.bump_project_version(
            bump_type="minor",
            project_json_path=str(self.pjson),
        )
        self.assertTrue(success)
        self.assertIn("1.1.0", msg)

        # 3. Release checker on 1.1.0 must pass 100%!
        rc_ok, rc_msgs = release_checker.verify_release("1.1.0", str(self.pjson))
        self.assertTrue(rc_ok, f"release_checker failed: {rc_msgs}")
        self.assertTrue(any("passed" in m for m in rc_msgs))

    def test_cli_main(self):
        pjson_data = {
            "archetype": "minimal",
            "release": {"strategy": "github-tag", "versionFile": "VERSION", "syncFiles": []},
        }
        self.pjson.write_text(json.dumps(pjson_data), encoding="utf-8")
        (self.tmp / "VERSION").write_text("0.1.0\n", encoding="utf-8")

        with patch("sys.argv", ["bump_version.py", "patch", "--project-json", str(self.pjson)]):
            ret = bump_version.main()
            self.assertEqual(0, ret)

        res_ver = (self.tmp / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual("0.1.1", res_ver)


if __name__ == "__main__":
    unittest.main()
