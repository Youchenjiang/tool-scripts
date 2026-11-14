"""Conservative read-only final PR gate across GitHub and SonarQube."""

import os
import re

PASS = {"SUCCESS", "PASS", "PASSED"}
SKIP = {"SKIPPED", "SKIPPING", "NEUTRAL"}
PENDING = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED", "EXPECTED"}
REQUIRED = {
    "PR and commit policy",
    "PR governance script tests",
    "DeepSource: Python",
    "SonarCloud",
    "SonarCloud Code Analysis",
}


def resolve_required_checks(repo=""):
    env_req = os.environ.get("PR_REQUIRED_CHECKS")
    if env_req:
        return {item.strip() for item in env_req.split(",") if item.strip()}
    return set(REQUIRED)


def _classify_checks(checks, required):
    """Group provider statuses and require all mandatory checks."""
    groups = {"failed": [], "pending": [], "skipped": [], "passed": []}
    for item in checks:
        name = item.get("name") or item.get("context") or "unnamed"
        status = str(item.get("conclusion") or item.get("state") or item.get("status") or "PENDING").upper()
        if status in PASS:
            groups["passed"].append(name)
        elif status in SKIP:
            groups["skipped"].append(name)
        elif status in PENDING:
            groups["pending"].append(name)
        else:
            groups["failed"].append(name)
    present = set().union(*map(set, groups.values()))
    groups["pending"].extend(f"Missing required check: {name}" for name in sorted(required - present))
    return groups


def _pr_problems(pr, remote_sha):
    problems = []
    if pr.get("state") == "OPEN" and pr["headRefOid"] != remote_sha:
        problems.append("PR HEAD differs from remote SHA")
    for key, expected, message in (
            ("baseRefName", "main", "PR target is not main"),
            ("state", "OPEN", "PR is not open")):
        if pr.get(key) != expected:
            problems.append(message)
    for key, expected, message in (
            ("isDraft", True, "PR is still a draft"),
            ("mergeable", "CONFLICTING", "PR has merge conflicts"),
            ("reviewDecision", "CHANGES_REQUESTED", "PR has changes requested")):
        if pr.get(key) == expected:
            problems.append(message)
    return problems


def _required_checks(files, repo="", author=""):
    if files is not None and not isinstance(files, list):
        raise RuntimeError("invalid changed-file inventory")
    required = set(resolve_required_checks(repo))
    if author.lower() in {"dependabot", "dependabot[bot]"}:
        required.discard("PR and Commit Policy Validation")
        required.discard("PR and commit policy")
    if (files and not ("tapstrum" in repo.lower() or "tapster" in repo.lower()) and
            any(file.get("path", "").startswith("src/") or
                file.get("path") == ".github/workflows/dependency-security-scan.yml"
                for file in files)):
        required.add("NuGet Dependency Vulnerability Scan")
    return required


def _is_finding_addressed(author, pr_body):
    if not pr_body or not author:
        return False
    clean_author = author.lower().replace("[bot]", "")
    pattern = re.compile(
        rf"(?:addressed|resolved|fixed).*?@{clean_author}|@{clean_author}.*?(?:addressed|resolved|fixed)",
        re.IGNORECASE,
    )
    return bool(pattern.search(pr_body.lower().replace("[bot]", "")))


def extract_top_review_findings(reviews, pr_body=""):
    """Detect top-level reviews reporting issues, changes requested, or blocker findings."""
    findings = []
    pattern = re.compile(
        r"(?:blocking issues|finding details|### finding|\bissues found\b|\baction required\b)",
        re.IGNORECASE,
    )
    clean_pattern = re.compile(
        r"\b(?:no\s+(?:blocking\s+)?issues\s+found|0\s+issues\s+found|no\s+findings)\b",
        re.IGNORECASE,
    )
    for item in reviews:
        body = item.get("body") or ""
        state = item.get("state")
        author = item.get("author") or (item.get("user") or {}).get("login") or "unknown"
        relation = item.get("head_relation") or item.get("relation") or "unscoped"
        stripped_body = clean_pattern.sub("", body)
        if state == "CHANGES_REQUESTED" or bool(pattern.search(stripped_body)):
            addressed = (state != "CHANGES_REQUESTED" and
                         relation != "current" and
                         _is_finding_addressed(author, pr_body))
            findings.append({
                "author": author,
                "state": state,
                "relation": relation,
                "url": item.get("url") or item.get("html_url") or "",
                "body": body,
                "addressed": addressed,
            })
    return findings

def _finding_problems(report, groups, required, pr_body=""):
    count = report["counts"]["unresolved"]
    sonar_count = report["sonar"]["total"]
    problems = []
    for value, label in ((count, "unresolved review threads"),
                         (sonar_count, "SonarQube issues")):
        if value:
            problems.append(f"{value} {label}")
    unaddressed = [item for item in extract_top_review_findings(report.get("reviews", []), pr_body)
                   if not item["addressed"]]
    if unaddressed:
        problems.append(
            f"{len(unaddressed)} unaddressed top-level review finding(s): "
            + ", ".join("@" + item["author"] for item in unaddressed))
    for names, label in ((groups["failed"], "failed checks"),
                         (sorted(required.intersection(groups["skipped"])), "required checks skipped"),
                         (groups["pending"], "pending checks")):
        if names:
            problems.append(f"{label}: {', '.join(names)}")
    return problems


def _check_details(checks, required):
    """Expose live check statuses and URLs without a separate native gh query."""
    details = []
    for item in checks:
        name = item.get("name") or item.get("context") or "unnamed"
        status = str(item.get("conclusion") or item.get("state") or item.get("status") or "PENDING").upper()
        details.append({"name": name, "status": status,
                        "required": name in required,
                        "url": item.get("detailsUrl") or item.get("targetUrl") or None})
    present = {item["name"] for item in details}
    details.extend({"name": name, "status": "MISSING", "required": True, "url": None}
                   for name in sorted(required - present))
    return details


def _max_new_duplication():
    """Optional ceiling; unset keeps the historical report-only behavior."""
    raw = os.environ.get("PR_MAX_NEW_DUPLICATION")
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError("PR_MAX_NEW_DUPLICATION must be numeric") from exc


def _sonar_quality_problems(quality):
    problems = []
    if quality is None:
        return problems
    gate = quality.get("quality_gate") or {}
    if gate.get("status") != "OK":
        problems.append("SonarQube quality gate not passed")
    ceiling = _max_new_duplication()
    raw = (quality.get("metrics") or {}).get("new_duplicated_lines_density")
    if ceiling is not None and raw is not None:
        try:
            if float(raw) > ceiling:
                problems.append(
                    f"SonarQube new code duplication is {raw}% (must be <= {ceiling}%)")
        except (TypeError, ValueError):
            problems.append("SonarQube new code duplication is unreadable")
    return problems


def summarize(pr, report, *, remote_sha):
    """An absent or incomplete check is not a pass. Skip is reported separately."""
    head = pr.get("headRefOid")
    checks = pr.get("statusCheckRollup")
    if not isinstance(head, str) or len(head) != 40 or not isinstance(checks, list):
        raise RuntimeError("missing verified PR HEAD or CI rollup")
    repo_hint = pr.get("url") or ""
    author_val = pr.get("author")
    author = author_val.get("login", "") if isinstance(author_val, dict) else str(author_val or "")
    required = _required_checks(pr.get("files"), repo=repo_hint, author=author)
    groups = _classify_checks(checks, required)
    count = report["counts"]["unresolved"]
    sonar_count = report["sonar"]["total"]
    pr_body = pr.get("body") or ""
    problems = (_pr_problems(pr, remote_sha) +
                _finding_problems(report, groups, required, pr_body))
    quality = report.get("sonar_quality")
    problems.extend(_sonar_quality_problems(quality))
    top_findings = extract_top_review_findings(report.get("reviews", []), pr_body)
    unresolved_details = [
        {"id": t["id"], "path": t["path"], "line": t["line"], "outdated": t["outdated"]}
        for t in report.get("threads", []) if not t.get("resolved")
    ]
    return {"ready": not problems, "state": pr.get("state"),
            "historical_checks_passed": (pr.get("state") == "MERGED" and
                                         not _finding_problems(report, groups, required, pr_body)),
            "problems": problems, "passed": groups["passed"],
            "top_level_findings": top_findings,
            "skipped": groups["skipped"], "head": head, "sonar_issues": sonar_count,
            "unresolved_threads": count, "unresolved_thread_details": unresolved_details,
            "checks": _check_details(checks, required),
            "sonar_quality": quality}
