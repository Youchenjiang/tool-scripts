#!/usr/bin/env python3
"""worktree_tool.py - Safe Git Worktree isolation and lifecycle manager.

Enables parallel branch development in dedicated sibling directories,
synchronizes local main without checking it out, and provides fail-closed
safety verification before removing merged feature worktrees.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PORCELAIN_STATUS = "--porcelain=v1"
BRANCH_PATTERN = re.compile(r"^(feature|feat|fix|refactor|hotfix|chore|docs|test|perf|style)/[a-z0-9][a-z0-9-]*$")


def run_git(*args, cwd=None, check=True):
    executable = shutil.which("git")
    if not executable:
        raise RuntimeError("git executable not found")
    proc = subprocess.run(
        [str(Path(executable).resolve()), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if check and proc.returncode:
        raise RuntimeError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc


def git_output(*args, cwd=None):
    return run_git(*args, cwd=cwd).stdout.strip()


def run_gh(*args):
    executable = shutil.which("gh")
    if not executable:
        raise RuntimeError("gh executable not found")
    proc = subprocess.run(
        [str(Path(executable).resolve()), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(f"GitHub inspection failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def get_worktree_list(cwd=None):
    records = []
    output = git_output("worktree", "list", "--porcelain", cwd=cwd)
    for block in output.split("\n\n"):
        entry = {}
        for line in block.splitlines():
            if " " in line:
                key, value = line.split(" ", 1)
                entry[key] = value
        if entry:
            records.append(entry)
    return records


def get_repo_state(cwd=None):
    root = Path(git_output("rev-parse", "--show-toplevel", cwd=cwd)).resolve()
    common_dir = Path(git_output("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)).resolve()
    remote_url = git_output("remote", "get-url", "origin", cwd=cwd)

    remote_main_lines = git_output("ls-remote", "--heads", "origin", "main", cwd=cwd).split()
    if len(remote_main_lines) != 2:
        # Fallback to master if main not present
        remote_main_lines = git_output("ls-remote", "--heads", "origin", "master", cwd=cwd).split()
        main_ref_name = "master"
    else:
        main_ref_name = "main"

    if len(remote_main_lines) != 2:
        raise ValueError("Cannot verify default remote branch (origin/main or origin/master)")

    remote_main_oid = remote_main_lines[0]
    remote_ref = f"refs/remotes/origin/{main_ref_name}"
    local_ref = f"refs/heads/{main_ref_name}"

    local_main = git_output("rev-parse", local_ref, cwd=cwd)

    return {
        "root": str(root),
        "repo_name": root.name,
        "common_dir": str(common_dir),
        "remote": remote_url,
        "main_branch": main_ref_name,
        "head": git_output("rev-parse", "HEAD", cwd=cwd),
        "branch": git_output("branch", "--show-current", cwd=cwd),
        "local_main": local_main,
        "remote_main": remote_main_oid,
    }


def is_ancestor(ancestor_oid, descendant_oid, cwd=None):
    proc = run_git("merge-base", "--is-ancestor", ancestor_oid, descendant_oid, cwd=cwd, check=False)
    return proc.returncode == 0


def compute_auth_token(state_dict):
    canonical = json.dumps(state_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def create_worktree(branch, cwd=None, execute=False, authorize=None):
    if not branch or not BRANCH_PATTERN.fullmatch(branch):
        raise ValueError(
            f"Invalid branch name '{branch}'. Must follow prefix/kebab-case (e.g. feat/user-auth, fix/login-crash)"
        )

    state = get_repo_state(cwd=cwd)
    root = Path(state["root"])
    branch_suffix = branch.split("/", 1)[1] if "/" in branch else branch
    target_path = root.parent / f"{state['repo_name']}-pr-{branch_suffix}"

    # Check local ref
    if run_git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", cwd=cwd, check=False).returncode == 0:
        raise ValueError(f"Local branch '{branch}' already exists; refuse to overwrite")

    # Check remote ref
    if git_output("ls-remote", "--heads", "origin", branch, cwd=cwd):
        raise ValueError(f"Remote branch '{branch}' already exists on origin")

    if target_path.exists():
        raise ValueError(f"Target worktree directory '{target_path.name}' already exists")

    action_state = {
        "action": "create",
        "branch": branch,
        "target_path": str(target_path),
        "base": state["remote_main"],
        "repo": state["repo_name"],
    }
    token = compute_auth_token(action_state)

    if not execute:
        return {
            "preview": action_state,
            "authorize": token,
            "message": f"Preview: will create dedicated worktree at '{target_path}' on branch '{branch}'",
        }

    if authorize != token:
        raise ValueError(f"Execution requires matching authorization token '{token}'")

    run_git("worktree", "add", "-b", branch, str(target_path), state["remote_main"], cwd=cwd)
    return {
        "success": True,
        "branch": branch,
        "path": str(target_path),
        "message": f"Successfully created worktree for branch '{branch}' at '{target_path}'",
    }


def verify_merge_equivalence(head_oid, merge_oid, remote_main_oid, cwd=None):
    """Verify integration mode; fail closed without exact cryptographic evidence."""
    if is_ancestor(head_oid, remote_main_oid, cwd=cwd):
        return "ancestry"

    parents = git_output("rev-list", "--parents", "-n", "1", merge_oid, cwd=cwd).split()
    if len(parents) == 2:
        base = git_output("merge-base", parents[1], head_oid, cwd=cwd)
        original_diff = git_output("diff", "--no-ext-diff", "--binary", "--no-renames", base, head_oid, cwd=cwd)
        merged_diff = git_output("diff", "--no-ext-diff", "--binary", "--no-renames", parents[1], merge_oid, cwd=cwd)
        if original_diff and original_diff == merged_diff:
            return "squash"

    # Rebase equivalence: all PR commits have cherry counterparts upstream
    base_head = git_output("merge-base", remote_main_oid, head_oid, cwd=cwd)
    cherry_output = git_output("cherry", remote_main_oid, head_oid, base_head, cwd=cwd).splitlines()
    if cherry_output and all(line.startswith("- ") for line in cherry_output):
        return "rebase"

    raise ValueError("Cannot prove all PR changes were integrated into origin/main; refusing deletion")


def cleanup_worktree(pr_number, cwd=None, execute=False, authorize=None):
    if not isinstance(pr_number, int) or pr_number < 1:
        raise ValueError("Cleanup requires a positive integer PR number")

    state = get_repo_state(cwd=cwd)
    info = run_gh("pr", "view", str(pr_number), "--json", "state,headRefName,headRefOid,mergeCommit,baseRefName")

    if info.get("state") != "MERGED":
        raise ValueError(f"PR #{pr_number} state is '{info.get('state')}', not 'MERGED'")

    target_branch = info.get("headRefName")
    head_oid = info.get("headRefOid")
    merge_commit = (info.get("mergeCommit") or {}).get("oid")

    if not target_branch or not head_oid or not merge_commit:
        raise ValueError("Incomplete PR merge metadata from GitHub")

    if not is_ancestor(merge_commit, state["remote_main"], cwd=cwd):
        raise ValueError(f"Merge commit '{merge_commit}' is not reachable from remote main")

    merge_mode = verify_merge_equivalence(head_oid, merge_commit, state["remote_main"], cwd=cwd)

    # Locate dedicated worktree
    target_ref = f"refs/heads/{target_branch}"
    worktrees = get_worktree_list(cwd=cwd)
    matches = [w for w in worktrees if w.get("branch") == target_ref]

    if len(matches) != 1:
        raise ValueError(f"Expected exactly 1 dedicated worktree for branch '{target_branch}', found {len(matches)}")

    target_path = Path(matches[0]["worktree"]).resolve()

    # Safety: check clean status
    status_out = git_output("status", PORCELAIN_STATUS, cwd=str(target_path))
    if status_out.strip():
        raise ValueError(f"Target worktree '{target_path}' has uncommitted changes; aborting cleanup")

    action_state = {
        "action": "cleanup",
        "pr": pr_number,
        "branch": target_branch,
        "target_path": str(target_path),
        "merge_commit": merge_commit,
        "merge_mode": merge_mode,
    }
    token = compute_auth_token(action_state)

    if not execute:
        return {
            "preview": action_state,
            "authorize": token,
            "message": f"Preview: will delete worktree at '{target_path}' and branch '{target_branch}' (merge verified via {merge_mode})",
        }

    if authorize != token:
        raise ValueError(f"Execution requires matching authorization token '{token}'")

    run_git("worktree", "remove", str(target_path), cwd=cwd)
    run_git("branch", "-D", target_branch, cwd=cwd)
    run_git("worktree", "prune", cwd=cwd)

    return {
        "success": True,
        "pr": pr_number,
        "branch": target_branch,
        "deleted_path": str(target_path),
        "message": f"Successfully cleaned up merged worktree for PR #{pr_number} ({target_branch})",
    }


def list_worktrees(cwd=None):
    worktrees = get_worktree_list(cwd=cwd)
    formatted = []
    for w in worktrees:
        path = w.get("worktree", "")
        branch = w.get("branch", "").replace("refs/heads/", "")
        head = w.get("HEAD", "")[:7]
        is_bare = "bare" in w
        formatted.append({"path": path, "branch": branch, "head": head, "bare": is_bare})
    return formatted


def main():
    parser = argparse.ArgumentParser(description="Git Worktree isolation and parallel development manager.")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = sub.add_parser("list", help="List active worktrees and branches")
    list_p.add_argument("--json", action="store_true", help="Output as JSON")

    # start / create
    start_p = sub.add_parser("start", help="Create a dedicated worktree for a new feature branch")
    start_p.add_argument("branch", help="New branch name (e.g. feat/user-auth)")
    start_p.add_argument("--execute", action="store_true", help="Execute worktree creation (default: preview)")
    start_p.add_argument("--authorize", help="Authorization token from preview")

    # cleanup
    clean_p = sub.add_parser("cleanup", help="Safely verify and remove a merged PR worktree")
    clean_p.add_argument("pr", type=int, help="Merged PR number")
    clean_p.add_argument("--execute", action="store_true", help="Execute worktree deletion (default: preview)")
    clean_p.add_argument("--authorize", help="Authorization token from preview")

    args = parser.parse_args()

    try:
        if args.command == "list":
            items = list_worktrees()
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                print(f"[worktree_tool] Active worktrees ({len(items)}):")
                for w in items:
                    print(f"  - [{w['branch'] or 'HEAD'}] {w['path']} ({w['head']})")
            return 0

        elif args.command == "start":
            res = create_worktree(args.branch, execute=args.execute, authorize=args.authorize)
            print(json.dumps(res, indent=2))
            return 0

        elif args.command == "cleanup":
            res = cleanup_worktree(args.pr, execute=args.execute, authorize=args.authorize)
            print(json.dumps(res, indent=2))
            return 0

    except Exception as e:
        print(f"[worktree_tool] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
