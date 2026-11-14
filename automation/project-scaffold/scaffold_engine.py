#!/usr/bin/env python3
"""automation/project-scaffold/scaffold_engine.py

Core cross-platform scaffolding engine for Youchen projects.
Standard library only (0 external dependencies). Enforces strict ecosystem isolation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ScaffoldContext:
    target_dir: Path
    project_name: str
    archetype_key: str
    archetype_name: str
    ecosystem: str
    flow: str
    release_strategy: str
    version_file: str
    sync_files: List[str]
    features: List[str]
    scopes: List[str]
    build_cmd: Dict[str, str]
    agent_rules: List[str]
    git_files: List[str]
    tool_files: List[str]
    workflows: List[str]
    github_files: List[str]
    jitter_monthly_cron: str
    jitter_weekly_cron: str
    force: bool = False


def calculate_jitter_cron(project_name: str) -> Dict[str, str]:
    """Calculate deterministic project-specific cron schedules via SHA-256."""
    digest = int(hashlib.sha256(project_name.encode("utf-8")).hexdigest()[:8], 16)
    month_day, hour, minute, week_day = (digest % 28) + 1, (digest % 4) + 1, digest % 59, digest % 7
    return {
        "monthly": f"{minute} {hour} {month_day} * *",
        "weekly": f"{minute} {hour} * * {week_day}",
    }


def _extend_unique(target: List[str], items: List[str]) -> None:
    for item in items:
        if item not in target:
            target.append(item)


def resolve_context(
    config: Dict[str, Any],
    target_dir: Path,
    archetype_arg: Optional[str] = None,
    flow_arg: Optional[str] = None,
    release_arg: Optional[str] = None,
    features_arg: Optional[List[str]] = None,
    all_features: bool = False,
    no_features: bool = False,
    no_release: bool = False,
    project_name_arg: Optional[str] = None,
    force: bool = False,
) -> ScaffoldContext:
    defaults, archetypes = config.get("defaults", {}), config.get("archetypes", {})
    features_cfg, aliases = config.get("features", {}), config.get("legacyAliases", {})

    target_dir = target_dir.resolve()
    project_name = project_name_arg or target_dir.name

    arch_key = archetype_arg or "backend-python"
    if arch_key in aliases:
        arch_key = "backend-node" if arch_key == "backend-api" and (target_dir / "package.json").exists() else aliases[arch_key]

    if arch_key not in archetypes:
        raise ValueError(f"Unknown archetype '{arch_key}'. Available: {list(archetypes.keys())}")

    arch = archetypes[arch_key]
    ecosystem = arch.get("ecosystem", "generic")
    flow = "direct-push" if (flow_arg in ("direct-push", "trunk")) else (flow_arg or arch.get("flow", "pr"))

    avail = list(features_cfg.keys())
    if no_features:
        active_features = []
    elif all_features:
        active_features = list(avail)
    elif features_arg is not None:
        active_features = [f.strip() for f in features_arg if f.strip() in avail]
    else:
        active_features = list(arch.get("recommendedFeatures", []))

    if flow == "direct-push":
        _extend_unique(active_features, ["direct-push"])
        if "chained-prs" in active_features:
            active_features.remove("chained-prs")
    elif flow == "pr" and "direct-push" in active_features:
        active_features.remove("direct-push")

    arch_rel = arch.get("release", {})
    if no_release:
        rel_strategy, ver_file, sync_files = "none", "", []
    elif release_arg and release_arg != "default":
        rel_strategy = release_arg
        strategy_map = {
            "none": ("", []),
            "npm-version": ("package.json", ["package-lock.json"]),
            "dotnet-store": ("Directory.Build.props", ["Package.appxmanifest"]),
            "python-version": ("pyproject.toml", []),
            "github-tag": ("VERSION", []),
        }
        ver_file, sync_files = strategy_map.get(rel_strategy, ("", []))
    else:
        rel_strategy = arch_rel.get("strategy", "github-tag")
        ver_file = arch_rel.get("versionFile", "VERSION" if rel_strategy == "github-tag" else "")
        sync_files = arch_rel.get("syncFiles", [])

    rules: List[str] = list(defaults.get("coreRules", []))
    _extend_unique(rules, arch.get("agentRules", []))
    for feat in active_features:
        _extend_unique(rules, features_cfg.get(feat, {}).get("agentRules", []))

    if flow == "direct-push" or "direct-push" in active_features:
        if "git-discipline.md" in rules:
            rules.remove("git-discipline.md")
        _extend_unique(rules, ["direct-trunk.md"])
    else:
        if "direct-trunk.md" in rules:
            rules.remove("direct-trunk.md")
        _extend_unique(rules, ["git-discipline.md"])

    git_files = list(defaults.get("coreGitFiles", []))
    _extend_unique(git_files, arch.get("gitFiles", []))

    tool_files = list(defaults.get("coreTools", []))
    if arch.get("includePrTools", True) and flow == "pr":
        _extend_unique(tool_files, defaults.get("prTools", []))
    for feat in active_features:
        _extend_unique(tool_files, features_cfg.get(feat, {}).get("toolFiles", []))

    workflows = list(defaults.get("coreGithubWorkflows", []))
    _extend_unique(workflows, arch.get("githubWorkflows", []))
    for feat in active_features:
        _extend_unique(workflows, features_cfg.get(feat, {}).get("githubWorkflows", []))

    gh_files = list(defaults.get("coreGithubFiles", []))
    _extend_unique(gh_files, arch.get("githubFiles", []))
    if flow == "direct-push" and "pull_request_template.md" in gh_files:
        gh_files.remove("pull_request_template.md")

    jitter = calculate_jitter_cron(project_name)

    return ScaffoldContext(
        target_dir=target_dir,
        project_name=project_name,
        archetype_key=arch_key,
        archetype_name=arch.get("name", arch_key),
        ecosystem=ecosystem,
        flow=flow,
        release_strategy=rel_strategy,
        version_file=ver_file,
        sync_files=sync_files,
        features=active_features,
        scopes=arch.get("defaultScopes", []),
        build_cmd=arch.get("build", {}),
        agent_rules=rules,
        git_files=git_files,
        tool_files=tool_files,
        workflows=workflows,
        github_files=gh_files,
        jitter_monthly_cron=jitter["monthly"],
        jitter_weekly_cron=jitter["weekly"],
        force=force,
    )


def assemble_agent_rules(ctx: ScaffoldContext, templates_dir: Path) -> None:
    header = f"# {ctx.project_name} Agent Rules & Developer Guidelines\n\nAI Guidelines for {ctx.project_name}.\n\n"
    parts = [header]
    rules_dir = templates_dir / "agent-rules"
    for r in ctx.agent_rules:
        rf = rules_dir / r
        if rf.is_file():
            parts.append(rf.read_text(encoding="utf-8"))

    content = "\n\n".join(parts)
    (ctx.target_dir / "AGENTS.md").write_text(content, encoding="utf-8")
    agent_dir = ctx.target_dir / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "rules.md").write_text(content, encoding="utf-8")

    mem_file = ctx.target_dir / "MEMORY.md"
    if not mem_file.exists() or ctx.force:
        mem_tpl = templates_dir / "docs" / "MEMORY.starter.md"
        feat_str = ", ".join(ctx.features) if ctx.features else "Standard baseline"
        if mem_tpl.is_file():
            raw = mem_tpl.read_text(encoding="utf-8")
            mem_content = raw.format(project_name=ctx.project_name, archetype_key=ctx.archetype_key, archetype_name=ctx.archetype_name, features=feat_str)
            mem_file.write_text(mem_content, encoding="utf-8")


def deploy_git_policies(ctx: ScaffoldContext, templates_dir: Path) -> None:
    git_tpl = templates_dir / "git"
    for gf in ctx.git_files:
        if not gf.startswith("hooks/"):
            src, dst = git_tpl / gf, ctx.target_dir / gf
            if src.is_file() and not (gf == ".gitignore" and dst.exists() and not ctx.force):
                shutil.copy2(src, dst)

    hook_src_dir = git_tpl / "hooks"
    git_dir = ctx.target_dir / ".git"
    if git_dir.is_dir() and hook_src_dir.is_dir():
        hooks_dst = git_dir / "hooks"
        hooks_dst.mkdir(parents=True, exist_ok=True)
        for h in hook_src_dir.iterdir():
            if h.is_file():
                th = hooks_dst / h.name
                shutil.copy2(h, th)
                try:
                    th.chmod(th.stat().st_mode | 0o755)
                except OSError:
                    pass
        subprocess.run(["git", "config", "commit.template", ".gitmessage.txt"], cwd=ctx.target_dir, check=False, capture_output=True)
        dp = ["git", "config", "repo.directPush", "true"] if ctx.flow == "direct-push" else ["git", "config", "--unset", "repo.directPush"]
        subprocess.run(dp, cwd=ctx.target_dir, check=False, capture_output=True)

    scripts_hooks_dst = ctx.target_dir / "scripts" / "hooks"
    scripts_hooks_dst.mkdir(parents=True, exist_ok=True)
    if hook_src_dir.is_dir():
        for h in hook_src_dir.iterdir():
            if h.is_file():
                shutil.copy2(h, scripts_hooks_dst / h.name)

    if ctx.ecosystem == "node":
        mjs_src = git_tpl / "scripts" / "install-hooks.mjs"
        if mjs_src.is_file():
            shutil.copy2(mjs_src, ctx.target_dir / "scripts" / "install-hooks.mjs")
        pkg_file = ctx.target_dir / "package.json"
        if pkg_file.is_file():
            try:
                pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
                pkg.setdefault("scripts", {})
                if "prepare" not in pkg["scripts"]:
                    pkg["scripts"]["prepare"] = "node scripts/install-hooks.mjs"
                    pkg_file.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
            except (json.JSONDecodeError, OSError):
                pass
    else:
        py_src = git_tpl / "scripts" / "install-hooks.py"
        if py_src.is_file():
            shutil.copy2(py_src, ctx.target_dir / "scripts" / "install-hooks.py")


def deploy_tools_and_tests(ctx: ScaffoldContext, templates_dir: Path) -> None:
    tools_dir = ctx.target_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = ctx.target_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    tools_tpl = templates_dir / "tools"
    for tf in ctx.tool_files:
        src, dst = tools_tpl / tf, tools_dir / tf
        if not src.is_file():
            continue
        if tf == "lint_commits.py" and ctx.scopes:
            py_scopes = "# /* SCOPES_PLACEHOLDER_START */\nALLOWED_SCOPES = [\n" + "".join(f'    "{s}",\n' for s in ctx.scopes) + "]\n# /* SCOPES_PLACEHOLDER_END */"
            tool_content = src.read_text(encoding="utf-8")
            regex = r"(?s)#\s*/\*\s*SCOPES_PLACEHOLDER_START\s*\*/.*?#\s*/\*\s*SCOPES_PLACEHOLDER_END\s*\*/"
            tool_content = re.sub(regex if re.search(regex, tool_content) else r"(?s)ALLOWED_SCOPES\s*=\s*\[.*?\]", py_scopes, tool_content)
            dst.write_text(tool_content, encoding="utf-8")
            continue
        shutil.copy2(src, dst)

    if "conda-env" in ctx.features:
        for f, d in [("env_tool.py", tools_dir), ("../tests/test_env_tool.py", tests_dir)]:
            p = tools_tpl / f
            if p.is_file():
                shutil.copy2(p, d / p.name)
        env_yaml = ctx.target_dir / "environment.yml"
        if not env_yaml.exists() or ctx.force:
            tpl = "environment.api.yml" if ctx.archetype_key in ("backend-python", "backend-node") else ("environment.ai.yml" if ctx.archetype_key == "sec-research" else "environment.tool.yml")
            cp = templates_dir / "conda" / tpl
            if cp.is_file():
                raw = cp.read_text(encoding="utf-8")
                name = re.sub(r"[^a-z0-9_-]", "-", f"{ctx.archetype_key}-{ctx.project_name}".lower())
                env_yaml.write_text(re.sub(r"^name:\s*[^\r\n]+", f"name: {name}", raw, flags=re.MULTILINE), encoding="utf-8")

    if "strict-linting" in ctx.features and ctx.ecosystem == "node":
        es = templates_dir / "lint" / "eslint.config.mjs"
        if es.is_file():
            shutil.copy2(es, ctx.target_dir / "eslint.config.mjs")

    tests_tpl = templates_dir / "tests"
    if tests_tpl.is_dir():
        for t in tests_tpl.iterdir():
            if t.is_file() and t.name.startswith("test_"):
                mod = t.name[5:-3]
                if (tools_dir / f"{mod}.py").exists() or (mod == "env_tool" and "conda-env" in ctx.features):
                    shutil.copy2(t, tests_dir / t.name)

    project_contract = {
        "name": ctx.project_name,
        "archetype": ctx.archetype_key,
        "ecosystem": ctx.ecosystem,
        "flow": ctx.flow,
        "features": ctx.features,
        "scopes": ctx.scopes,
        "build": ctx.build_cmd,
        "release": {"strategy": ctx.release_strategy, "versionFile": ctx.version_file, "syncFiles": ctx.sync_files},
    }
    (tools_dir / "project.json").write_text(json.dumps(project_contract, indent=2) + "\n", encoding="utf-8")
    if ctx.release_strategy == "github-tag" and ctx.version_file == "VERSION" and not (ctx.target_dir / "VERSION").exists():
        (ctx.target_dir / "VERSION").write_text("0.1.0\n", encoding="utf-8")


def deploy_workflows(ctx: ScaffoldContext, templates_dir: Path) -> None:
    wf_dir = ctx.target_dir / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    wf_tpl = templates_dir / "github" / "workflows"
    steps_tpl = templates_dir / "github" / "steps"

    step_file = "ci.dotnet.yml" if ctx.ecosystem == "dotnet" else ("ci.python.yml" if ctx.archetype_key == "backend-python" else ("ci.sec.yml" if ctx.archetype_key == "sec-research" else ("ci.node.yml" if ctx.ecosystem == "node" else "ci.default.yml")))
    ci_snippet = (steps_tpl / step_file).read_text(encoding="utf-8") if (steps_tpl / step_file).is_file() else "      # /* CI_STEPS_PLACEHOLDER_START */\n      - run: echo 'Baseline check passed.'\n      # /* CI_STEPS_PLACEHOLDER_END */"

    for wf in ctx.workflows:
        src = wf_tpl / wf
        if not src.is_file():
            continue
        content = src.read_text(encoding="utf-8")
        if wf == "policy.yml" and ctx.scopes:
            scopes_str = "/* SCOPES_PLACEHOLDER_START */\n" + "".join(f'              "{s}",\n' for s in ctx.scopes) + "              /* SCOPES_PLACEHOLDER_END */"
            content = re.sub(r"/\*\s*SCOPES_PLACEHOLDER_START\s*\*/[\s\S]*?/\*\s*SCOPES_PLACEHOLDER_END\s*\*/", scopes_str, content)

        if "CRON_PLACEHOLDER_START" in content:
            assigned = ctx.jitter_weekly_cron if wf == "codeql.yml" else ctx.jitter_monthly_cron
            cron_block = f"# /* CRON_PLACEHOLDER_START */\n    - cron: '{assigned}'\n    # /* CRON_PLACEHOLDER_END */"
            content = re.sub(r"#\s*/\*\s*CRON_PLACEHOLDER_START\s*\*/[\s\S]*?#\s*/\*\s*CRON_PLACEHOLDER_END\s*\*/", cron_block, content)

        bot_marker = "github.event_name == 'pull_request' # /* BOT_PR_EXEMPT_PLACEHOLDER */"
        if bot_marker in content:
            rep = "github.event_name == 'pull_request' && github.event.pull_request.user.type != 'Bot'" if "bot-pr-exempt" in ctx.features else "github.event_name == 'pull_request'"
            content = content.replace(bot_marker, rep)

        if wf == "ci.yml":
            runs_on = "windows-latest" if ctx.ecosystem == "dotnet" else "ubuntu-latest"
            content = re.sub(r"/\*\s*RUNS_ON_PLACEHOLDER\s*\*/[\s\S]*?/\*\s*RUNS_ON_PLACEHOLDER_END\s*\*/", runs_on, content)
            content = re.sub(r"#\s*/\*\s*CI_STEPS_PLACEHOLDER_START\s*\*/[\s\S]*?#\s*/\*\s*CI_STEPS_PLACEHOLDER_END\s*\*/", ci_snippet.strip(), content)

        (wf_dir / wf).write_text(content, encoding="utf-8")

    gh_tpl = templates_dir / "github"
    for ghf in ctx.github_files:
        src = gh_tpl / ghf
        if src.is_file():
            shutil.copy2(src, ctx.target_dir / ".github" / ghf)

    adr_src = templates_dir / "docs" / "adr"
    if adr_src.is_dir():
        adr_dst = ctx.target_dir / "docs" / "adr"
        adr_dst.mkdir(parents=True, exist_ok=True)
        for adr in adr_src.iterdir():
            if adr.is_file():
                shutil.copy2(adr, adr_dst / adr.name)


def scaffold(
    target_dir: Path,
    archetype: Optional[str] = None,
    flow: Optional[str] = None,
    release: Optional[str] = None,
    features: Optional[List[str]] = None,
    all_features: bool = False,
    no_features: bool = False,
    no_release: bool = False,
    project_name: Optional[str] = None,
    force: bool = False,
) -> ScaffoldContext:
    script_dir = Path(__file__).resolve().parent
    presets_file = script_dir / "presets.json"
    templates_dir = script_dir / "templates"

    if not presets_file.is_file():
        raise FileNotFoundError(f"presets.json not found in {script_dir}")

    config = json.loads(presets_file.read_text(encoding="utf-8"))
    ctx = resolve_context(
        config=config,
        target_dir=target_dir,
        archetype_arg=archetype,
        flow_arg=flow,
        release_arg=release,
        features_arg=features,
        all_features=all_features,
        no_features=no_features,
        no_release=no_release,
        project_name_arg=project_name,
        force=force,
    )

    ctx.target_dir.mkdir(parents=True, exist_ok=True)
    assemble_agent_rules(ctx, templates_dir)
    deploy_git_policies(ctx, templates_dir)
    deploy_tools_and_tests(ctx, templates_dir)
    deploy_workflows(ctx, templates_dir)
    return ctx


def main() -> int:
    parser = argparse.ArgumentParser(description="Youchen Project Scaffolding Engine (Pure Python)")
    parser.add_argument("--archetype", "-a", help="Project archetype (or alias)")
    parser.add_argument("--flow", choices=["pr", "direct-push", "trunk"], help="Git workflow mode")
    parser.add_argument("--release", "-r", help="Release strategy (default, none, python-version, npm-version, dotnet-store, github-tag)")
    parser.add_argument("--no-release", action="store_true", help="Disable release and version management")
    parser.add_argument("--features", "-f", help="Comma-separated list of optional features")
    parser.add_argument("--all-features", action="store_true", help="Enable all optional features")
    parser.add_argument("--no-features", action="store_true", help="Disable all optional features")
    parser.add_argument("--target-dir", "-t", default=".", help="Target project directory")
    parser.add_argument("--project-name", "-p", help="Project name (defaults to target directory name)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing configuration files")

    args = parser.parse_args()
    feat_list = [f.strip() for f in args.features.split(",") if f.strip()] if args.features else None

    ctx = scaffold(
        target_dir=Path(args.target_dir),
        archetype=args.archetype,
        flow=args.flow,
        release=args.release,
        features=feat_list,
        all_features=args.all_features,
        no_features=args.no_features,
        no_release=args.no_release,
        project_name=args.project_name,
        force=args.force,
    )

    print(f"✨ Successfully scaffolded project '{ctx.project_name}' ({ctx.archetype_key}) at {ctx.target_dir}")
    print(f"   Ecosystem: {ctx.ecosystem}, Flow: {ctx.flow}, Release: {ctx.release_strategy}")
    print(f"   Active Features: {', '.join(ctx.features) if ctx.features else 'None'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
