# Backport Inventory: Clickra → Project Scaffold

This document tracks which governance mechanisms hardened in the Clickra repository
still have to be absorbed by this scaffold, and in what order.

**Direction of transfer**: Clickra (hardened downstream) → `project-scaffold` (generic
upstream template). The scaffold's `templates/tools/` files started life as Clickra's
`scripts/` files; Clickra has since added a full release lifecycle that the scaffold
never received.

**Snapshot**: 2026-11-13, compared against Clickra `main` at `202bddd0`.

## 1. Evidence

Line counts after `diff --strip-trailing-cr` (CRLF differences excluded):

| File | scaffold | Clickra | Note |
|---|---|---|---|
| `branch_policy.py` | 57 | 57 | in sync |
| `gh_guard.py` | 212 | 212 | in sync |
| `pr_audit.py` | 77 | 77 | in sync |
| `pr_reports.py` | 55 | 55 | in sync |
| `pr_publication.py` | 65 | 65 | in sync |
| `sonar_audit.py` | 106 | 108 | minor drift |
| `process_guard.py` | 73 | 83 | read-only surface behind |
| `pr_creation.py` | 158 | 205 | behind |
| `pr_verification.py` | 145 | 193 | behind |
| `pr_preflight.py` | 252 | 568 | furthest behind |
| `pr_tool.py` | 538 | 606 | diverged both ways |

The scaffold also has **no product CI at all**: its eleven workflow templates cover
policy and security scanning, but no template builds or tests the scaffolded project,
and `templates/git/hooks/pre-push` never runs the scaffold's own governance tests.

## 2. Inventory

Status values: `planned` · `landed` · `blocked` · `rejected`.

| ID | Gap | Clickra source | Target here | Status |
|---|---|---|---|---|
| S1 | Read-only git surface for release/version gates | `scripts/process_guard.py` | `templates/tools/process_guard.py` | planned |
| S2 | Unaddressed top-level review findings are not detected | `scripts/pr_verification.py` | `templates/tools/pr_verification.py` | planned |
| S3 | New-code duplication ceiling cannot be enforced | `scripts/pr_verification.py` | `templates/tools/pr_verification.py` | planned |
| S4 | Review-checklist prompts and metadata-as-checkbox ban | `scripts/pr_preflight.py` | `templates/tools/pr_preflight.py` | blocked |
| S5 | Version gate: release-impact paths, tag already released, manifest/changelog/listing sync | `scripts/pr_preflight.py` | `templates/tools/pr_preflight.py` + presets | planned |
| S6 | Roadmap/spec alignment gate (milestone must exist in `docs/ROADMAP.md`) | `scripts/pr_preflight.py` | `templates/tools/pr_preflight.py` + docs template | planned |
| S7 | Version-surface bump tool (BOM preserving) | `scripts/bump_version.ps1` | `templates/tools/bump_version.py` | planned |
| S8 | Version-driven auto tag + release pipeline | `.github/workflows/ci.yml`, `release.yml` | `templates/github/workflows/` | planned |
| S9 | Post-publish reconciliation ("workflow green ≠ published") | `store-release-enrichment.yml`, `check_store_release_published.py` | feature `release-verify` | planned |
| S10 | Product CI with a stable aggregate required-check name | `.github/workflows/ci.yml` | `templates/github/workflows/ci.yml` | planned |
| S11 | Pre-push runs only preflight; governance tests and builds are skipped | `scripts/hooks/pre-push` | `templates/git/hooks/pre-push` + presets | planned |
| S12 | PR body generator (preflight requires a body file, nothing drafts one) | `.agent/skills/`, `pr_helper.py generate` | `templates/tools/` | planned |
| S13 | Conditional expensive-test scoping via exit-code contract | `scripts/pdf_fixture_scope.py` | `templates/tools/test_scope.py` | planned |
| S14 | Tenant leakage: required checks hardcode Clickra/TapStrum names | — (scaffold-only defect) | `presets.json` → generated config | planned |
| S15 | Docs/agent structure: thin `AGENTS.md`, skills, authority headers, SHA-pinned actions | `.agent/`, `AGENTS.md`, workflows | `templates/agent-rules`, `templates/github` | planned |

### S4 is blocked on a contract conflict

Three files disagree about the PR body shape:

- `templates/github/pull_request_template.md`: `## Summary` / `## Key Changes` / `## How to Verify (Verification)` / `## Pre-Submission Checklist`
- `templates/github/workflows/policy.yml`: requires `## Summary` / `## Key Changes` / `## Verification`
- `templates/tools/pr_preflight.py`: requires `## Summary` / `## Changes` / `## Validation` / `## Review Checklist`

Adding Clickra's mandatory checklist prompts before unifying these three would fail
every scaffolded project. Unifying the contract is its own change and must land first.

## 3. Reverse protection (scaffold is ahead — do not overwrite)

| ID | Scaffold behavior | Clickra behavior |
|---|---|---|
| R1 | `pr_preflight` reads `lint_commits.ALLOWED_SCOPES` (single source) | four hand-synced copies |
| R2 | Sonar project key resolved from `.sonarcloud.properties` | derived from repository name |
| R3 | PR lookup uses `--state all`, so closed duplicate PRs are refused | `--state open` only |
| R4 | Agent rule Tier 4: agents may never merge a PR | merge allowed with authorization |
| R5 | `PR_REQUIRED_CHECKS` override for required checks | hardcoded set |

Any backport must preserve R1–R5.

## 4. Explicit non-goals

- `N1` Copying Clickra-specific paths (`src/Clickra.Core`, `docs/store/StoreListing_*`,
  PDF translation fixtures) into templates. Every gate must be parameterized.
- `N2` Shipping the Partner Center / Store ingestion scripts. They encode one vendor's
  API and one publisher identity; only the reconciliation *pattern* (S9) generalizes.
- `N3` Adopting Clickra's `REQUIRED` check names as scaffold defaults (see S14).

## 5. Commit plan

Each commit has one purpose and can be reverted independently.

1. `docs(automation)`: this inventory.
2. `fix(automation)`: S1 — extend the read-only git surface.
3. `feat(automation)`: S2 — reject unaddressed top-level review findings.
4. `feat(automation)`: S3 — opt-in new-code duplication ceiling.
5. `docs(automation)`: update the ledger with landed items.

S4–S15 continue in later batches, in the order listed once S4's contract
conflict is resolved.

## 6. Verification

Template tests assume a scaffolded layout (`tools/` and `tests/` siblings), so they are
run against a throwaway copy:

```bash
T=automation/project-scaffold/.verify-tmp
rm -rf "$T" && mkdir -p "$T"
cp -r automation/project-scaffold/templates/tools "$T/tools"
cp -r automation/project-scaffold/templates/tests "$T/tests"
cp -r automation/project-scaffold/templates/git   "$T/git"
(cd "$T" && python -m unittest discover -s tests -p 'test_pr_verification.py' -v)
(cd "$T" && python -m unittest discover -s tests -p 'test_process_guard.py' -v)
rm -rf "$T"
```
