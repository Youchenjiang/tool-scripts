#!/usr/bin/env python3
"""
Tests for the scaffold commit message, the next-step hints and --publish.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from scaffold_engine import initial_commit_message, next_steps, publish, scaffold  # noqa: E402

HEADER = re.compile(r"^chore\(setup\): [a-z].{0,60}[^.]$")


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)


class TestInitialCommitMessage(unittest.TestCase):
    def test_every_archetype_allows_the_setup_scope(self) -> None:
        presets = json.loads((SCRIPT_DIR / "presets.json").read_text(encoding="utf-8"))
        for key, arch in presets["archetypes"].items():
            with self.subTest(archetype=key):
                self.assertIn("setup", arch["defaultScopes"])

    def test_message_follows_conventional_commits_for_every_archetype(self) -> None:
        presets = json.loads((SCRIPT_DIR / "presets.json").read_text(encoding="utf-8"))
        tmp = Path(tempfile.mkdtemp(prefix="test_publish_msg_"))
        try:
            for key in presets["archetypes"]:
                with self.subTest(archetype=key):
                    ctx = scaffold(target_dir=tmp / key, archetype=key, no_features=True)
                    lines = initial_commit_message(ctx).splitlines()
                    self.assertRegex(lines[0], HEADER)
                    self.assertLessEqual(len(lines[0]), 72)
                    self.assertEqual("", lines[1])
                    self.assertTrue(all(re.match(r"^\d+\. ", line) for line in lines[2:]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestNextSteps(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="test_next_steps_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pr_flow_recommends_a_ruleset(self) -> None:
        ctx = scaffold(target_dir=self.tmp, archetype="minimal", flow="pr", no_features=True)
        self.assertTrue(any("Rulesets" in step for step in next_steps(ctx)))
        self.assertEqual(1, len(next_steps(ctx, published=True)))

    def test_direct_push_flow_skips_the_ruleset(self) -> None:
        ctx = scaffold(target_dir=self.tmp, archetype="minimal", flow="direct-push", no_features=True)
        self.assertFalse(any("Rulesets" in step for step in next_steps(ctx)))


@unittest.skipUnless(shutil.which("git"), "git is required")
class TestPublish(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="test_publish_"))
        self.target = self.tmp / "demo-kit"
        self.target.mkdir()
        self.remote = self.tmp / "remote.git"
        git(self.tmp, "init", "--bare", str(self.remote))
        git(self.target, "init")
        git(self.target, "config", "user.name", "Test")
        git(self.target, "config", "user.email", "test@example.local")
        self.env = {k: os.environ.pop(k) for k in ("ALLOW_DIRECT_PUSH", "PR_BODY_FILE") if k in os.environ}

    def tearDown(self) -> None:
        os.environ.update(self.env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_publish_commits_and_bootstraps_an_empty_remote(self) -> None:
        """End to end: the scaffold commit passes commit-msg, and the first push passes pre-push."""
        ctx = scaffold(target_dir=self.target, archetype="minimal", flow="pr", no_features=True)
        git(self.target, "remote", "add", "origin", str(self.remote))
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if args[0] == "gh":
                raise AssertionError("gh must not run when origin already exists")
            return subprocess.run(args, **kwargs)

        publish(ctx, "private", run=run)
        subject = git(self.remote, "log", "-1", "--format=%s", "main").stdout.strip()
        self.assertEqual("chore(setup): scaffold project from the minimal template", subject)
        self.assertIn(["git", "push", "-u", "origin", "refs/heads/main:refs/heads/main"], calls)

    def test_publish_creates_the_repository_when_origin_is_missing(self) -> None:
        ctx = scaffold(target_dir=self.target, archetype="minimal", no_features=True)
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if args[:2] == ["git", "remote"] or args[:2] == ["git", "rev-parse"]:
                return subprocess.CompletedProcess(args, 1, "", "")
            return subprocess.CompletedProcess(args, 0, "", "")

        publish(ctx, "public", run=run)
        self.assertIn(["gh", "repo", "create", "demo-kit", "--public", "--source", ".", "--remote", "origin"], calls)

    def test_publish_refuses_a_repository_with_commits_and_bad_input(self) -> None:
        ctx = scaffold(target_dir=self.target, archetype="minimal", no_features=True)
        ok = lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "", "")  # noqa: E731
        with self.assertRaises(RuntimeError):
            publish(ctx, "private", run=ok)
        with self.assertRaises(ValueError):
            publish(ctx, "internal", run=ok)
        ctx.project_name = "--evil"
        with self.assertRaises(ValueError):
            publish(ctx, "private", run=ok)


if __name__ == "__main__":
    unittest.main()
