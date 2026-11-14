# Archetypes: what `init-project.ps1` actually generates

`presets.json` is the only source of truth. This document records what each archetype
does today, where the README disagrees with it, and which remaining backport item
belongs to which type.

## 1. The six archetypes

| Archetype | Aliases (code) | Scopes | Workflows | `githubFiles` | Rules | Recommended features |
|---|---|---|---|---|---|---|
| `web-spa` | `web` | 13 | 3: policy, trufflehog, codeql | template, dependabot, SECURITY | 4 (adds `web-guidelines.md`) | `strict-linting`, `chained-prs` |
| `backend-api` | — | 11 | 4: policy, trufflehog, codeql, sbom | template, dependabot, SECURITY | 3 | `strict-linting`, `conda-env` |
| `desktop-app` | `desktop` | 10 | 4: policy, trufflehog, codeql, sbom | template, dependabot, SECURITY | 5 (adds `dotnet-hygiene.md`, `store-release.md`) | `chained-prs` |
| `sec-research` | `research` | 10 | 6: policy, trufflehog, codeql, nuclei, pr-agent, sbom | template, SECURITY (**no dependabot**) | 3 | `conda-env` |
| `minimal` | `minimal` (self) | 6 | 1: policy | template, SECURITY (**no dependabot**) | 3 | `conda-env` |
| `script-tool` | `script`, `scripts`, `tool`, `tools` | 14 | 3: policy, trufflehog, codeql | dependabot, SECURITY (**no PR template**) | 3 (`direct-trunk.md` replaces `git-discipline.md`) | `direct-push` |

`gitFiles` are nearly identical everywhere: `.gitignore`, `.gitmessage.txt`,
`.editorconfig`, `hooks/commit-msg`. Only `script-tool` drops `hooks/pre-push`, and only
`sec-research` adds `.pr_agent.toml`.

Tool payload: the five PR-based archetypes ship the same 14 files
(`lint_commits`, `branch_policy`, `process_guard`, `gh_guard`, `sonar_audit`, `pr_audit`,
`pr_reports`, `pr_verification`, `pr_body_contract`, `pr_preflight`, `pr_publication`,
`pr_creation`, `pr_tool`, `pr_helper`). `script-tool` ships `lint_commits.py` only.

## 2. What actually differs

Only four things vary by archetype:

1. **Commit scopes** injected into `policy.yml` (`defaultScopes`).
2. **Which workflows** are deployed, i.e. the security surface.
3. **Which agent rules** are concatenated into `AGENTS.md`.
4. **Whether a PR flow exists at all** — `script-tool` pushes straight to trunk.

Everything else (commit format, PR body contract, branch policy, PR tooling, release
tooling that does not exist yet) is identical. That matters for the backport: most
remaining items are **not** per-archetype features, they are per-axis features.

## 3. Four axes hidden inside one field

An archetype today encodes four independent decisions. Treating them separately avoids
writing six copies of every gate:

| Axis | Values in use | Where it lives now |
|---|---|---|
| Build system | npm (web-spa, strict-linting), dotnet (desktop-app), python (conda-env), none (script-tool) | implied by rules and features, never declared |
| Release surface | none, static site, container, MSIX + Store | only `desktop-app` has rules for it (`store-release.md`) |
| PR flow | PR-based (5) / direct trunk (1) | `script-tool` + `direct-push` feature |
| Security surface | policy only / +codeql+trufflehog / +sbom / +nuclei+pr-agent+enterprise | `githubWorkflows` lists |

Any per-type deepening should add a **config field per axis** (for example
`build: {lint, test}`, `release: {versionFile, changelog, paths}`) rather than branch on
the archetype name inside the tools.

## 4. Known drift between the README and `presets.json`

Verified by comparing the README table with `presets.json` on 2026-11-13.

**Scopes.** README lists scopes that are not injected, so a contributor following the
README gets a rejected commit, while real scopes are undocumented:

| Archetype | README-only (rejected in practice) | Code-only (undocumented) |
|---|---|---|
| `backend-api` | `models`, `routes`, `spec`, `rules`, `quality`, `sec` | `service`, `middleware`, `config` |
| `desktop-app` | `app`, `winui`, `test`, `spec`, `rules`, `quality`, `release` | `shell`, `native`, `msix`, `store` |
| `sec-research` | `agent`, `audit`, `rules`, `exp`, `test`, `spec`, `quality`, `sec` | `vuln`, `exploit`, `report`, `scanner`, `data` |
| `minimal` | `cli`, `deps`, `setup` | `tool`, `chore` |
| `web-spa`, `script-tool` | — | — |

**Aliases.** README advertises aliases that `legacyAliases` does not resolve:
`frontend` (`web-spa`), `winui`/`wpf` (`desktop-app`), `security`/`lab` (`sec-research`),
`cli` (`minimal`). Worse, README maps `tool` and `script` to `minimal` while
`legacyAliases` maps them to `script-tool` — the same invocation produces two different
projects depending on which document you trust.

**Other inconsistencies:**

- `minimal` recommends `conda-env`, so a "minimal utility" receives `environment.yml`,
  `env_tool.py` and `conda-hygiene.md` by default.
- `backend-api` also recommends `conda-env` although its description covers
  Node/Express and Go services.
- `sec-research` and `minimal` ship no `dependabot.yml`, unlike the other four.

## 5. Which backport item belongs to which type

`S` numbers refer to `BACKPORT.md`.

| Item | web-spa | backend-api | desktop-app | sec-research | minimal | script-tool |
|---|---|---|---|---|---|---|
| S5 version/release gate | package.json version | pyproject/package version | `Directory.Build.props` + manifests + store listings | — | — | — |
| S6 roadmap alignment | yes | yes | yes | yes | optional | optional |
| S7 `bump_version` | package.json + lock | pyproject + lock | BOM-preserving props | — | — | — |
| S8 release pipeline | static publish | container publish | MSIX + Store | — | — | — |
| S9 publish reconciliation | — | — | Store | — | — | — |
| S10 product CI | npm lint/test/build | language-specific | dotnet build/test | pytest/none | none/pytest | none/pytest |
| S11 pre-push governance | yes | yes | yes | yes | yes | different: no pre-push exists |
| S12 PR body generator | shipped | shipped | shipped | shipped | shipped | n/a |
| S13 test scoping | e2e | integration | MSIX/e2e | — | — | — |
| S14 tenant leakage | yes | yes | yes | yes | yes | n/a (no `pr_verification`) |
| S15 docs/agent structure | yes | yes | yes | yes | yes | yes |

## 6. Recommended order

1. **Fix the drift in §4** — README table and aliases are wrong today, and a wrong
   taxonomy makes every later per-type decision unreliable. Cheapest possible fix:
   generate the README table from `presets.json` (or at least assert equality in a test).
2. **S14** — tenant leakage inside `pr_verification`, which all five PR-based types ship.
3. **S10 + S11** — both need a declared build/test command per type, which is the first
   genuine per-type field. Everything else can stay shared.
4. **S5–S9** — release lifecycle, starting with `desktop-app` only (it is the only type
   with a release surface today), then `web-spa`/`backend-api` once their publish paths
   exist.
