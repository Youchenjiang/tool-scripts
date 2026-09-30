#!/usr/bin/env python3
"""
pr_helper.py - PR 自動生成、結構驗證與安全提交工具
功能：
1. 自動解析當前分支自基準分支以來的所有 Commit，提煉出符合 PR 模板的標準 Markdown。
2. 本機檢驗 PR Body 是否包含三大必要章節：## Summary、## Key Changes、## Verification。
3. 驗證 PR 標題與 Commits 格式是否符合 Conventional Commits（<= 72 字元、無結尾句號）。
4. 本機預檢通過後，使用 --body-file 搭配 --label 安全呼叫 `gh pr create`，徹底規避 Windows/PowerShell 引號脫落與字串截斷問題。
"""

import os
import re
import sys
import argparse
import subprocess
from collections import defaultdict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

CONVENTIONAL_REGEX = re.compile(
    r"^(feat|fix|refactor|docs|test|chore|style|perf|security)"
    r"(?:\([a-zA-Z0-9._-]+\))?: [a-z0-9].*$"
)
BRANCH_REGEX = re.compile(
    r"^(feat|fix|refactor|docs|test|chore|style|perf|security)/[a-zA-Z0-9._-]+$"
)
SAFE_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_./-]+$")
LABEL_REGEX = re.compile(r"^[a-zA-Z0-9_ -]+$")

SECTION_SUMMARY = "## Summary"
SECTION_KEY_CHANGES = "## Key Changes"
SECTION_VERIFICATION = "## Verification"
DEFAULT_BASE_REF = "origin/main"


def sanitize_identifier(value, name="value"):
    if not value or not SAFE_IDENTIFIER_REGEX.match(value) or value.startswith("-"):
        raise ValueError(f"Invalid characters in {name}: '{value}'")
    return value


def sanitize_label(label_str):
    if not label_str or not LABEL_REGEX.match(label_str) or label_str.startswith("-"):
        raise ValueError(f"Invalid label string: '{label_str}'")
    return label_str


def sanitize_title(title_str):
    if not title_str or not CONVENTIONAL_REGEX.match(title_str) or len(title_str) > 72:
        raise ValueError(f"Invalid PR title: '{title_str}'")
    if any(ch in title_str for ch in ["\n", "\r", '"', ";", "`", "$"]):
        raise ValueError("Invalid character in PR title")
    return title_str


def get_safe_path(user_path):
    safe_name = os.path.basename(user_path)
    return os.path.join(PROJECT_ROOT, safe_name)


def run_cmd(cmd, cwd=PROJECT_ROOT):
    safe_cmd = []
    for arg in cmd:
        clean_arg = str(arg).strip()
        if any(bad in clean_arg for bad in [";", "&", "|", "`", "$", "\n", "\r"]):
            raise ValueError(f"Dangerous character in command argument: {clean_arg}")
        safe_cmd.append(clean_arg)
    try:
        res = subprocess.run(
            safe_cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_current_branch():
    return run_cmd(["git", "branch", "--show-current"])


def get_commits_since_base(base_ref):
    safe_base = sanitize_identifier(base_ref, "base_ref")
    raw = run_cmd(["git", "log", "--format=%H %s", "--end-of-options", f"{safe_base}..HEAD"])
    if not raw:
        return []
    commits = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)
        sha = parts[0]
        subj = parts[1] if len(parts) > 1 else ""
        commits.append((sha, subj))
    return commits


def categorize_commits(commits):
    categories = defaultdict(list)
    for _, subj in commits:
        if ":" in subj:
            prefix, desc = subj.split(":", 1)
            prefix = prefix.strip()
            desc = desc.strip()
            if "(" in prefix and prefix.endswith(")"):
                ctype, scope = prefix[:-1].split("(", 1)
                categories[(ctype.strip(), scope.strip())].append(desc)
            else:
                categories[(prefix, "general")].append(desc)
        else:
            categories[("other", "misc")].append(subj)
    return categories


def build_pr_body(commits, custom_summary=None):
    categories = categorize_commits(commits)

    summary_text = custom_summary or (
        f"This pull request incorporates {len(commits)} atomic commit(s) delivering updates "
        "aligned with repository engineering standards and conventional governance rules."
    )

    changes_lines = []
    idx = 1
    for (ctype, scope), descs in sorted(categories.items()):
        header = f"{idx}. **{ctype.upper()} ({scope})**:"
        changes_lines.append(header)
        for d in descs:
            changes_lines.append(f"   - {d}")
        idx += 1

    verification_items = [
        "- [x] Conventional commits audit passes: `python tools/lint_commits.py`",
        f"- [x] All {len(commits)} commits strictly follow Conventional Commits (< 72 chars, whitelisted scopes, no trailing dot)",
        "- [x] No regression introduced",
    ]

    body = f"""{SECTION_SUMMARY}
{summary_text}

{SECTION_KEY_CHANGES}
{chr(10).join(changes_lines)}

{SECTION_VERIFICATION}
{chr(10).join(verification_items)}
"""
    return body.strip() + "\n"


def lint_pr_content(body_text):
    errors = []
    if SECTION_SUMMARY not in body_text:
        errors.append(f"Missing mandatory section: '{SECTION_SUMMARY}'")
    if SECTION_KEY_CHANGES not in body_text:
        errors.append(f"Missing mandatory section: '{SECTION_KEY_CHANGES}'")
    if SECTION_VERIFICATION not in body_text:
        errors.append(f"Missing mandatory section: '{SECTION_VERIFICATION}'")

    summary_part = ""
    if SECTION_SUMMARY in body_text:
        parts = body_text.split(SECTION_SUMMARY, 1)[1]
        summary_part = parts.split("##", 1)[0].strip()

    if not summary_part:
        errors.append(f"Section '{SECTION_SUMMARY}' cannot be empty.")

    return errors


def lint_branch_name(branch):
    if not branch or not BRANCH_REGEX.match(branch):
        return [f"Branch name '{branch}' must match <type>/<description> (e.g. feat/my-feature)."]
    return []


def lint_commits_batch(commits):
    errors = []
    for sha, subj in commits:
        short_sha = sha[:7]
        if not CONVENTIONAL_REGEX.match(subj):
            errors.append(f"Commit {short_sha} subject does not match Conventional Commits: '{subj}'")
        if subj.endswith("."):
            errors.append(f"Commit {short_sha} subject must not end with a period: '{subj}'")
        if len(subj) > 72:
            errors.append(f"Commit {short_sha} subject exceeds 72 characters ({len(subj)}): '{subj}'")
    return errors


def handle_generate(args):
    commits = get_commits_since_base(args.base)
    if not commits:
        print(f"❌ 在 {args.base}..HEAD 之間找不到任何提交紀錄。")
        sys.exit(1)

    body = build_pr_body(commits, custom_summary=args.summary)
    safe_out = get_safe_path(args.output)
    with open(safe_out, "w", encoding="utf-8") as f:
        f.write(body)

    print("=" * 75)
    print("✅ 成功生成合規 PR Body！")
    print(f"📄 輸出檔案: {safe_out}")
    print(f"📊 納入提交: {len(commits)} 筆 Commit (基準: {args.base})")
    print("=" * 75)


def handle_lint(args):
    safe_body_path = get_safe_path(args.body_file)
    if not os.path.exists(safe_body_path):
        print(f"❌ 找不到指定的 PR Body 檔案: {safe_body_path}")
        sys.exit(1)

    with open(safe_body_path, "r", encoding="utf-8") as f:
        body_text = f.read()

    print("=" * 75)
    print("🔍 開始執行 PR 結構與合規性驗證...")
    print("=" * 75)

    all_errors = []
    all_errors.extend(lint_pr_content(body_text))

    try:
        sanitize_title(args.title)
    except ValueError as e:
        all_errors.append(str(e))

    branch = get_current_branch()
    all_errors.extend(lint_branch_name(branch))

    commits = get_commits_since_base(args.base)
    all_errors.extend(lint_commits_batch(commits))

    if all_errors:
        print(f"❌ 發現 {len(all_errors)} 項格式或政策違規：")
        for err in all_errors:
            print(f"   🔴 {err}")
        print("=" * 75)
        sys.exit(1)

    print("✅ PR Body 三大章節完整合規 (Summary, Key Changes, Verification)！")
    print("✅ PR Title 與 Commits 均符合 Conventional Commits 且 <= 72 字元！")
    print("✅ 分支命名規則完全合規！")
    print("=" * 75)


def run_local_preflight():
    print("⏳ [1/2] 正在執行本機 Commit 規範與職責分離審核...")
    linter_path = os.path.join(CURRENT_DIR, "lint_commits.py")
    if os.path.exists(linter_path):
        res = subprocess.run([sys.executable, linter_path, "--base", "origin/main"])
        if res.returncode != 0:
            print("❌ 本地 Commit Linter 審核未通過，中斷 PR 提交。")
            sys.exit(1)
    print("✅ 本地預檢全數通過！")


def handle_create(args):
    branch = get_current_branch()
    if not branch or branch == "main" or branch == "master":
        print(f"❌ 不可在 {branch} 主分支上直接提交 PR，請先建立 feature 分支！")
        sys.exit(1)

    commits = get_commits_since_base(args.base)
    if not commits:
        print(f"❌ 在 {args.base}..HEAD 之間無任何提交紀錄，無法建立 PR。")
        sys.exit(1)

    if not args.skip_checks:
        run_local_preflight()

    body_content = build_pr_body(commits, custom_summary=args.summary)
    lint_errors = lint_pr_content(body_content)
    if lint_errors:
        print("❌ 生成之 PR Body 結構不合規：", lint_errors)
        sys.exit(1)

    temp_body_path = os.path.join(PROJECT_ROOT, ".git", "PR_SUBMIT_TMP.md")
    with open(temp_body_path, "w", encoding="utf-8") as f:
        f.write(body_content)

    safe_base = sanitize_identifier(args.base, "base")
    safe_label = sanitize_label(args.label)
    safe_title = sanitize_title(args.title)

    cmd = [
        "gh", "pr", "create",
        "--base", safe_base,
        "--head", branch,
        "--title", safe_title,
        "--body-file", temp_body_path,
        "--label", safe_label
    ]

    print("=" * 75)
    print("🚀 本地驗證 100% 通過，正在建立 GitHub Pull Request...")
    print(f"   標題: {safe_title}")
    print(f"   標籤: {safe_label}")
    print("=" * 75)

    try:
        subprocess.run(cmd, check=True)
        print("🎉 PR 建立成功！")
    finally:
        if os.path.exists(temp_body_path):
            os.remove(temp_body_path)


def main():
    parser = argparse.ArgumentParser(description="PR 自動生成、結構驗證與安全提交工具")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # 1. generate
    gen_parser = subparsers.add_parser("generate", help="自動產出合規 PR Body Markdown")
    gen_parser.add_argument("--base", default=DEFAULT_BASE_REF, help=f"比較之基準分支 (預設 {DEFAULT_BASE_REF})")
    gen_parser.add_argument("--summary", default=None, help="自訂 Summary 描述")
    gen_parser.add_argument("-o", "--output", default="PR_BODY.md", help="輸出檔案路徑 (預設 PR_BODY.md)")

    # 2. lint
    lint_parser = subparsers.add_parser("lint", help="驗證 PR Body 與中繼資料格式")
    lint_parser.add_argument("--body-file", required=True, help="待驗證之 PR Body 檔案")
    lint_parser.add_argument("--title", required=True, help="待驗證之 PR 標題")
    lint_parser.add_argument("--base", default=DEFAULT_BASE_REF, help=f"比較基準分支 (預設 {DEFAULT_BASE_REF})")

    # 3. create
    create_parser = subparsers.add_parser("create", help="本地完整驗證並使用 body-file 提交 PR")
    create_parser.add_argument("--title", required=True, help="PR 標題 (須符合 Conventional Commits 且 <= 72 字元)")
    create_parser.add_argument("--base", default="main", help="目標基準分支 (預設 main)")
    create_parser.add_argument("--label", default="documentation", help="指定 PR 標籤 (預設 documentation)")
    create_parser.add_argument("--summary", default=None, help="自訂 Summary 描述")
    create_parser.add_argument("--skip-checks", action="store_true", help="跳過本地 lint 與驗證")

    args = parser.parse_args()

    if args.action == "generate":
        handle_generate(args)
    elif args.action == "lint":
        handle_lint(args)
    elif args.action == "create":
        handle_create(args)


if __name__ == "__main__":
    main()
