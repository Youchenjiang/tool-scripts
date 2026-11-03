#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit Tests for Conda/Mamba Environment Manager (env_tool)."""

from pathlib import Path
import sys
import tempfile
import unittest

for _dir in ("tools", "scripts"):
    _p = str(Path(__file__).resolve().parents[1] / _dir)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from env_tool import (
    build_parser,
    detect_gpu_info,
    find_conda_executable,
    find_mamba_executable,
    sanitize_environment_yaml,
    update_daemon_scripts,
)


class TestEnvTool(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sanitize_dirty_yaml(self):
        dirty_input = """name: dirty-env
channels:
  - conda-forge
  - https://repo.anaconda.com/pkgs/main
  - defaults
dependencies:
  - bzip2=1.0.8=h2bbff1b_6
  - ca-certificates=2026.2.25=haa95532_0
  - libxml2=2.15.2=h7594589_0
  - m2w64-gcc-libs=5.3.0=7
  - openssl=3.6.1=h2466b09_1
  - python=3.12.13=h2bbff1b_0
  - pytorch=2.5.1=cuda124_py312
  - vc14_runtime=14.44.35208=h4731da8_26
  - pip=26.0.1=py312haa95532_0
  - pip:
      - transformers==4.57.6
      - accelerate==1.12.0
prefix: C:\\MyAPP\\Anaconda3\\envs\\dirty-env
"""
        cleaned = sanitize_environment_yaml(
            dirty_input,
            target_name="clean-ai-project",
            target_python="3.14",
        )

        self.assertIn("name: clean-ai-project", cleaned)
        self.assertNotIn("prefix:", cleaned)
        self.assertNotIn("ca-certificates", cleaned)
        self.assertNotIn("vc14_runtime", cleaned)
        self.assertNotIn("m2w64", cleaned)
        self.assertNotIn("libxml2", cleaned)
        self.assertNotIn("https://repo.anaconda.com", cleaned)

        # Check preserved essential packages
        self.assertIn("python=3.14", cleaned)
        self.assertIn("pytorch", cleaned)
        self.assertIn("transformers==4.57.6", cleaned)
        self.assertIn("accelerate==1.12.0", cleaned)

    def test_installer_detection(self):
        # find_mamba_executable and find_conda_executable should return None or a valid string
        mamba = find_mamba_executable()
        if mamba:
            self.assertIsInstance(mamba, str)

        conda = find_conda_executable()
        if conda:
            self.assertIsInstance(conda, str)

    def test_gpu_info_structure(self):
        gpu = detect_gpu_info()
        self.assertIn("available", gpu)
        self.assertIn("name", gpu)
        self.assertIn("driver_version", gpu)
        self.assertIn("cuda_version", gpu)

    def test_update_daemon_scripts(self):
        ps1_path = self.root / "run_daemon.ps1"
        ps1_path.write_text(
            '$condaPython = "C:\\OldPath\\python.exe"\n& $condaPython daemon.py',
            encoding="utf-8",
        )

        bat_path = self.root / "run_daemon.bat"
        bat_path.write_text(
            'set CONDA_ENV=C:\\OldPath\\env\n"%CONDA_ENV%\\python.exe" daemon.py',
            encoding="utf-8",
        )

        target_python = self.root / ".conda" / "python.exe"
        target_python.parent.mkdir(parents=True, exist_ok=True)
        target_python.touch()

        patched = update_daemon_scripts(self.root, target_python)
        self.assertIn("run_daemon.ps1", patched)
        self.assertIn("run_daemon.bat", patched)

        new_ps1 = ps1_path.read_text(encoding="utf-8")
        self.assertNotIn("C:\\OldPath\\python.exe", new_ps1)
        self.assertIn(str(target_python.resolve()), new_ps1)

        new_bat = bat_path.read_text(encoding="utf-8")
        self.assertNotIn("C:\\OldPath\\env", new_bat)
        self.assertIn(str(target_python.parent.resolve()), new_bat)

    def test_cli_parser(self):
        parser = build_parser()
        args_doc = parser.parse_args(["doctor"])
        self.assertEqual(args_doc.command, "doctor")

        args_setup = parser.parse_args(["setup", "-p", "--dry-run"])
        self.assertEqual(args_setup.command, "setup")
        self.assertTrue(args_setup.prefix)
        self.assertTrue(args_setup.dry_run)

        args_san = parser.parse_args(["sanitize", "old.yml", "-o", "new.yml", "-n", "test-env"])
        self.assertEqual(args_san.command, "sanitize")
        self.assertEqual(args_san.name, "test-env")


if __name__ == "__main__":
    unittest.main()
