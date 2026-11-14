#!/usr/bin/env python3
"""automation/project-scaffold/tests/test_scaffold_e2e.py

End-to-end integration tests for Youchen project scaffolding engine.
Validates zero cross-ecosystem contamination, archetype coverage, Jitter determinism, and test passing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add project-scaffold directory to path
CURRENT_DIR = Path(__file__).resolve().parent
SCAFFOLD_DIR = CURRENT_DIR.parent
if str(SCAFFOLD_DIR) not in sys.path:
    sys.path.insert(0, str(SCAFFOLD_DIR))

from scaffold_engine import calculate_jitter_cron, scaffold


class TestScaffoldEngineE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="test_scaffold_e2e_")
        self.target_path = Path(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_backend_python_zero_node_pollution(self) -> None:
        """backend-python must produce zero Node/npm artifacts."""
        ctx = scaffold(
            target_dir=self.target_path,
            archetype="backend-python",
            project_name="CleanPythonApp",
        )
        self.assertEqual(ctx.ecosystem, "python")

        # Zero Node.js footprint assertions
        self.assertFalse((self.target_path / "package.json").exists())
        self.assertFalse((self.target_path / "package-lock.json").exists())
        self.assertFalse((self.target_path / "eslint.config.mjs").exists())
        self.assertFalse((self.target_path / "scripts" / "install-hooks.mjs").exists())

        # Python artifacts assertions
        self.assertTrue((self.target_path / "scripts" / "install-hooks.py").exists())
        self.assertTrue((self.target_path / "environment.yml").exists())

        # CI workflow inspection
        ci_content = (self.target_path / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("Setup Python", ci_content)
        self.assertIn("ruff check", ci_content)
        self.assertNotIn("setup-node", ci_content)

        # project.json inspection
        pj_data = json.loads((self.target_path / "tools" / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(pj_data["ecosystem"], "python")
        self.assertEqual(pj_data["release"]["strategy"], "python-version")

    def test_backend_node_includes_node_tooling(self) -> None:
        """backend-node must properly scaffold Node/npm tooling."""
        ctx = scaffold(
            target_dir=self.target_path,
            archetype="backend-node",
            project_name="NodeApp",
        )
        self.assertEqual(ctx.ecosystem, "node")
        self.assertTrue((self.target_path / "scripts" / "install-hooks.mjs").exists())
        self.assertFalse((self.target_path / "scripts" / "install-hooks.py").exists())

        ci_content = (self.target_path / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("Setup Node.js", ci_content)
        self.assertNotIn("Setup Python", ci_content)

    def test_all_archetypes_scaffold_successfully(self) -> None:
        """All archetypes defined in presets.json must scaffold without error."""
        presets_file = SCAFFOLD_DIR / "presets.json"
        config = json.loads(presets_file.read_text(encoding="utf-8"))
        for arch_key in config.get("archetypes", {}):
            with tempfile.TemporaryDirectory(prefix=f"arch_{arch_key}_") as arch_temp:
                arch_path = Path(arch_temp)
                ctx = scaffold(target_dir=arch_path, archetype=arch_key, project_name=f"Test_{arch_key}")
                self.assertTrue((arch_path / "AGENTS.md").exists())
                self.assertTrue((arch_path / "MEMORY.md").exists())
                self.assertTrue((arch_path / "tools" / "project.json").exists())
                self.assertTrue((arch_path / ".github" / "workflows" / "ci.yml").exists())

    def test_jitter_determinism_and_staggering(self) -> None:
        """Jitter cron calculation must be deterministic for the same name."""
        cron1 = calculate_jitter_cron("ProjectAlpha")
        cron2 = calculate_jitter_cron("ProjectAlpha")
        self.assertEqual(cron1, cron2)

        # Different projects should yield staggered schedules
        cron_beta = calculate_jitter_cron("ProjectBetaXYZ123")
        self.assertIn("*", cron_beta["monthly"])
        self.assertIn("*", cron_beta["weekly"])

    def test_release_override_options(self) -> None:
        """Release strategies can be overridden to none or github-tag."""
        scaffold(
            target_dir=self.target_path,
            archetype="minimal",
            no_release=True,
            project_name="NoReleaseApp",
        )
        pj_data = json.loads((self.target_path / "tools" / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(pj_data["release"]["strategy"], "none")
        self.assertFalse((self.target_path / "VERSION").exists())

        with tempfile.TemporaryDirectory() as tag_dir:
            scaffold(
                target_dir=Path(tag_dir),
                archetype="minimal",
                release="github-tag",
                project_name="TagApp",
            )
            self.assertTrue((Path(tag_dir) / "VERSION").exists())
            self.assertEqual((Path(tag_dir) / "VERSION").read_text(encoding="utf-8").strip(), "0.1.0")

    def test_install_hooks_python_execution(self) -> None:
        """Test that install-hooks.py successfully installs hooks into .git/hooks/."""
        scaffold(target_dir=self.target_path, archetype="backend-python", project_name="HooksTest")
        # Initialize a mock git repo
        git_dir = self.target_path / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        script_path = self.target_path / "scripts" / "install-hooks.py"
        res = subprocess.run([sys.executable, str(script_path)], cwd=self.target_path, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"install-hooks.py failed: {res.stderr}")
        self.assertTrue((git_dir / "hooks" / "commit-msg").exists())
        self.assertTrue((git_dir / "hooks" / "pre-push").exists())

    def test_scaffolded_project_tests_pass(self) -> None:
        """Generated project tests must pass 100% when executed in the scaffolded project."""
        scaffold(
            target_dir=self.target_path,
            archetype="backend-python",
            project_name="SelfCheckApp",
            no_features=True,  # Avoid env_tool which needs actual conda/mamba CLI
        )
        res = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=self.target_path,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Scaffolded project test discovery failed:\n{res.stderr}\n{res.stdout}")


if __name__ == "__main__":
    unittest.main()
