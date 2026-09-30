#!/usr/bin/env python3
"""
lint_commits.py - 本機 Commit 政策與職責分離防搭便車稽核工具 (Commit Policy & Atomic Linter)
功能：
1. 嚴格對齊 GitHub Actions policy.yml 之 Conventional Commits 政策規範。
2. 驗證所有 commit 標題長度 <= 72 字元、白名單 scope、小寫開頭、無結尾句點。
3. 實施「職責分離與防搭便車」稽核：偵測是否有將治理文檔 (HANDOVER/MEMORY) 與功能代碼混雜提交之行為。
4. 支援指定範圍檢驗 (--range、--base) 與嚴格模式 (--strict)。
"""

import os
import re
import sys
import argparse
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ALLOWED_TYPES = [
    "feat",
    "fix",
    "refactor",
    "docs",
    "test",
    "chore",
    "style",
    "perf",
    "security",
]

ALLOWED_SCOPES = [
    "core",
    "ui",
    "web",
    "cli",
    "shell",
    "msix",
    "study",
    "plan",
    "ctfd",
    "labs",
    "challenge",
    "plugin",
    "docs",
    "ci",
    "deps",
    "sec",
    "store",
    "agent",
    "infra",
    "build",
    "release",
    "governance",
    "tracks",
    "practice",
    "tools",
    "knowledge",
    "memory",
    "deepsource",
    "links",
    "scaffold",
    "automation",
]

TYPE_PATTERN = "|".join(ALLOWED_TYPES)
SCOPE_PATTERN = "|".join(ALLOWED_SCOPES)
SUBJECT_REGEX = re.compile(
    rf"^({TYPE_PATTERN})(?:\(({SCOPE_PATTERN})\))?: [a-z0-9].*$"
)
VAGUE_REGEX = re.compile(r"^(update|misc|stuff|changes|fix bug|bug fix)$", re.IGNORECASE)

GOVERNANCE_PATTERNS = ["docs/handover.md", "memory.md", ".agent/"]
CODE_PATTERNS = [".py", ".js", ".ts", ".cs", ".sh", ".ps1", ".json", ".yml", ".yaml"]

ALLOWED_GIT_FLAGS = frozenset(
    {"--verify", "--format=%H %s", "--end-of-options", "--no-commit-id", "--name-only", "-r"}
)
SAFE_REF_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./~^-]*$")


def is_safe_ref(ref_token):
    if not ref_token or ref_token.startswith("-") or ".." in ref_token:
        return False
    return bool(SAFE_REF_REGEX.fullmatch(ref_token))


def validate_rev_range(rev_range):
    if not rev_range or rev_range.startswith("-"):
        raise ValueError(f"Invalid git rev_range specification: '{rev_range}'")
    if ".." in rev_range:
        parts = rev_range.split("..", 1)
        if is_safe_ref(parts[0]) and is_safe_ref(parts[1]):
            return f"{parts[0]}..{parts[1]}"
    elif is_safe_ref(rev_range):
        return rev_range
    raise ValueError(f"Invalid git rev_range specification: '{rev_range}'")


def sanitize_ref_arg(arg_str):
    if not arg_str or arg_str.startswith("-"):
        raise ValueError(f"Invalid reference parameter: '{arg_str}'")
    clean = arg_str.strip()
    if not is_safe_ref(clean):
        raise ValueError(f"Invalid reference parameter: '{arg_str}'")
    return clean


def run_git(cmd):
    safe_cmd = ["git"]
    for arg in cmd:
        clean_arg = str(arg).strip()
        if any(bad in clean_arg for bad in [";", "&", "|", "`", "$", "\n", "\r"]):
            raise ValueError(f"Dangerous character in git command: {clean_arg}")
        if clean_arg.startswith("-") and clean_arg not in ALLOWED_GIT_FLAGS:
            raise ValueError(f"Disallowed git option flag: {clean_arg}")
        safe_cmd.append(clean_arg)
    try:
        res = subprocess.run(
            safe_cmd,
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


def detect_base_ref():
    for candidate in ["origin/main", "main", "origin/master", "master"]:
        out = run_git(["rev-parse", "--verify", "--end-of-options", candidate])
        if out:
            return candidate
    return None


def get_commits(rev_range):
    safe_range = validate_rev_range(rev_range)
    raw = run_git(["log", "--format=%H %s", "--end-of-options", safe_range])
    if not raw:
        return []
    commits = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)
        sha = parts[0]
        subject = parts[1] if len(parts) > 1 else ""
        commits.append((sha, subject))
    return commits


def get_changed_files(sha):
    clean_sha = sha.strip()
    if clean_sha.startswith("-") or not re.fullmatch(r"[a-fA-F0-9]{7,40}", clean_sha):
        return []
    raw = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "--end-of-options", clean_sha])
    if not raw:
        return []
    return [line.strip().replace("\\", "/").lower() for line in raw.splitlines() if line.strip()]


def validate_commit(_sha, subject, changed_files, strict=False):
    errors = []
    warnings = []

    # 1. 符合正則規範
    if not SUBJECT_REGEX.match(subject):
        errors.append("標題格式錯誤：必須符合 <type>(<scope>): <subject> 且使用白名單之 type 與 scope")

    # 2. 禁止以句點結尾
    if subject.endswith("."):
        errors.append("結尾錯誤：標題結尾絕對不可帶有句號 `.`")

    # 3. 長度不大於 72 字元
    if len(subject) > 72:
        errors.append(f"長度超標：長度為 {len(subject)} 字元，超過上限 72 字元")

    # 4. 描述禁止空泛
    desc_match = re.sub(rf"^({TYPE_PATTERN})(?:\(({SCOPE_PATTERN})\))?:\s+", "", subject)
    if VAGUE_REGEX.match(desc_match.strip()):
        errors.append(f"描述過於空泛：'{desc_match}' 不符合專案描述具體性要求")

    # 5. 防搭便車職責分離偵測 (Anti-Free-Riding Check)
    has_gov = any(any(gp in f for gp in GOVERNANCE_PATTERNS) for f in changed_files)
    has_code = any(any(f.endswith(cp) for cp in CODE_PATTERNS) for f in changed_files)

    if has_gov and has_code:
        msg = "違反職責分離：偵測到治理文檔 (HANDOVER/MEMORY) 與功能代碼混雜提交（嚴禁搭便車）"
        if strict:
            errors.append(msg)
        else:
            warnings.append(msg)

    return errors, warnings


def audit_commit_batch(commits, strict=False):
    total_errors = 0
    total_warnings = 0

    for sha, subject in commits:
        changed_files = get_changed_files(sha)
        errors, warnings = validate_commit(sha, subject, changed_files, strict=strict)

        short_sha = sha[:7]
        if errors:
            print(f"❌ [{short_sha}] {subject}")
            for err in errors:
                print(f"   🔴 錯誤: {err}")
            total_errors += len(errors)
        elif warnings:
            print(f"⚠️  [{short_sha}] {subject}")
            for warn in warnings:
                print(f"   🟡 警告: {warn}")
            total_warnings += len(warnings)
        else:
            print(f"✅ [{short_sha}] {subject}")

    return total_errors, total_warnings


def main():
    parser = argparse.ArgumentParser(description="專案 Commit 規範與職責分離驗證工具")
    parser.add_argument("--base", help="基準分支或 Commit (預設自動偵測 origin/main 或 main)")
    parser.add_argument("--range", help="指定 Git 修訂範圍 (例如 main..HEAD 或 HEAD~5..HEAD)")
    parser.add_argument("--strict", action="store_true", help="啟用嚴格模式（將職責分離警告視為失敗錯誤）")
    args = parser.parse_args()

    print("=" * 75)
    print("🔍 開始執行【專案 Commit 規範與職責分離審核 (Commit Linter)】...")
    print("=" * 75)

    if args.range:
        if args.range.startswith("-"):
            print("❌ 錯誤：--range 參數不可包含選項旗標")
            sys.exit(1)
        rev_range = validate_rev_range(args.range)
    else:
        if args.base and args.base.startswith("-"):
            print("❌ 錯誤：--base 參數不可包含選項旗標")
            sys.exit(1)
        base = sanitize_ref_arg(args.base) if args.base else detect_base_ref()
        if not base:
            print("❌ 無法自動偵測基準分支，請透過 --base 指定基準分支 (例如: origin/main)")
            sys.exit(1)
        rev_range = f"{base}..HEAD"

    print(f"📌 檢驗範圍: {rev_range}")
    try:
        commits = get_commits(rev_range)
    except ValueError as val_err:
        print(f"❌ {val_err}")
        sys.exit(1)

    if not commits:
        print("ℹ️ 指定範圍內無任何提交紀錄需要檢驗。")
        sys.exit(0)

    print(f"📊 預計檢驗提交數: {len(commits)} 筆\n")
    total_errors, total_warnings = audit_commit_batch(commits, strict=args.strict)

    print("\n" + "=" * 75)
    print(f"📋 審核總結：共檢驗 {len(commits)} 筆 Commit | 錯誤: {total_errors} | 警告: {total_warnings}")
    print("=" * 75)

    if total_errors > 0:
        print("❌ 檢驗未通過！請修正上述 Commit 標題或拆分違規混雜提交後再行推送。")
        sys.exit(1)

    print("🎉 恭喜！所有 Commit 均 100% 符合專案政策與職責分離規範！")
    sys.exit(0)


if __name__ == "__main__":
    main()
