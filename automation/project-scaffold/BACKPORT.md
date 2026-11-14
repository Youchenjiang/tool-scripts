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
| S1 | Read-only git surface for release/version gates | `scripts/process_guard.py` | `templates/tools/process_guard.py` | landed |
| S2 | Unaddressed top-level review findings are not detected | `scripts/pr_verification.py` | `templates/tools/pr_verification.py` | landed |
| S3 | New-code duplication ceiling cannot be enforced | `scripts/pr_verification.py` | `templates/tools/pr_verification.py` | landed |
| S4 | PR body contract: headings, provider acknowledgement, reviewer prompts | `scripts/pr_preflight.py` | `templates/tools/pr_body_contract.py`, template, `policy.yml` | landed |
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

### S4 landed: one PR body contract

Four implementations used to disagree about the PR body shape — the template,
`policy.yml`, `pr_preflight.py` and `pr_helper.py` — so a body written from the template
failed the local gate, while a body that passed the gate failed CI. They now all read
`templates/tools/pr_body_contract.py`:

- `pr_preflight` (and through it `pr_creation` and `pr_tool`) validates the four headings,
  the placeholder words and the provider acknowledgement.
- `policy.yml` runs `pr_preflight.py --check-body` using the **base branch** tools, so CI
  applies exactly the local rule and cannot be loosened by the PR under review. The
  workflow keeps only Markdown hygiene checks of its own.
- The template and `pr_helper generate` emit the same shape. The provider item stays
  unchecked on purpose: only a human can assert that decision.
- Reviewer prompts remain optional
  (`test_review_prompts_are_optional_but_provider_acknowledgement_is_not`); only the
  provider acknowledgement is enforced.
- The `bot-pr-exempt` feature decides at scaffold time whether automated accounts skip
  these steps. Human PRs are checked either way.

Deferred, with the trigger that should revive them:

- **Legacy heading aliases** (`## Key Changes` → `## Changes`) — only if a scaffolded
  project outside this repository still has open PRs in the old shape. Aliases alone
  cannot rescue those bodies anyway: they carry no provider line.
- **`pr_helper create --external-provider`** — only once someone actually drives that
  subcommand. Clickra and this repository use `pr_tool.py`, and a rejected body is
  visible and editable on GitHub, so the failure is recoverable rather than silent.

### Landed in this batch

- **S1** — `process_guard` now permits `tag -l`, `ls-remote --tags` and a
  `-z --no-renames` name-only diff, including `origin/main...<full commit id>`
  for a pushed object. Anything else still fails closed.
- **S2** — `pr_verification.summarize` now rejects review submissions that report
  blocking findings when they are not addressed. A finding counts as addressed only
  when the review is not on the current head and the PR body references the reviewer.
  Parsed findings are returned as `top_level_findings`.
- **S3** — new-code duplication is reported as before, and enforced only when
  `PR_MAX_NEW_DUPLICATION` is set (for example `0` for a zero-duplication policy).
  An unreadable metric fails closed once a ceiling is configured.
- **S4** — one PR body contract in `pr_body_contract.py`, consumed by the preflight, the
  PR creation path, the helper and `policy.yml`; the template and `generate` produce a
  body that passes both gates, and the provider acknowledgement is required from a human.

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
6. `refactor(automation)`: S4a — read the PR body shape from one module.
7. `fix(automation)`: S4b — draft PR bodies in the shape the preflight accepts.
8. `refactor(automation)`: S4c — collapse the contract to one provider pattern.
9. `feat(automation)`: S4d — enforce the contract in `policy.yml`.
10. `feat(automation)`: S4e — let projects opt into the bot PR exemption.

S5–S15 continue in later batches, in the order listed.

## 6. Verification

Template tests assume a scaffolded layout (`tools/` and `tests/` siblings), so they are
run against a throwaway copy:

```bash
T=automation/project-scaffold/.verify-tmp
rm -rf "$T" && mkdir -p "$T"
for d in tools tests git github; do cp -r automation/project-scaffold/templates/$d "$T/$d"; done
(cd "$T" && python -m unittest discover -s tests -v)
rm -rf "$T"
```
