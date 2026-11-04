# As-built specifications

This folder holds the **delta specification** of the fork `hybrowlabs/frappe`: what the fork changes against upstream `frappe/frappe`, with the acceptance cases that pin the behaviour of each code change to tests. It does not describe upstream. Future changes are written spec first (see [conventions.md](conventions.md#9-spec-first-changes)).

The conventions, templates and checkers are copied unchanged from `hybrowlabs/CN-HRMS-Core` `main` at `963aa7c367b14d4357c8b3e3e7086e050d0b6d25` (parent issue PWHR-1270; this issue PWHR-1387). The folder `tools/tests/` is the checkers' own unit-test suite, copied with them.

## Layout

| Path | What it is |
|---|---|
| [`README.md`](README.md) | This file and the clause index. |
| [`conventions.md`](conventions.md) | The rules: IDs, source header, citations, test kinds, evidence, statutory and customer rules. |
| [`acceptance-cases.md`](acceptance-cases.md) | How to write, link and check an acceptance case (seven fields). |
| [`test-traceability.md`](test-traceability.md) | Index only: case to test rows, uncovered rules, retired IDs. |
| [`reviewer-checklist.md`](reviewer-checklist.md) | Checklist for the independent reviewer. |
| [`ci-spec-check.md`](ci-spec-check.md) | Copy-in GitHub Actions workflow template; not installed in this repo (stage 6 of PWHR-1270). |
| [`checkers.md`](checkers.md) | How to run the two checker scripts in `tools/` and what each rule means. |
| [`clauses/NN-name.md`](clauses/) | One clause per area. |
| [`reference/`](reference/) | Empty: this fork has no generated reference tables. |
| [`adr/`](adr/) | Decisions about the spec system itself, copied from CN-HRMS-Core. |
| [`templates/`](templates/) | Clause, case block, `AGENTS.md` snippet, PR template, spec-check workflow. Not installed in this repo. |

## IDs in this repo

- Repo code: `FRK` (fork inventory, `hybrowlabs/frappe`). Clause ID: `SPEC-FRK-NN`. Case ID: `FRK-NN-A<k>.<n><L>`.
- ADR-0001 open decision D3 proposed the code `FORK` for the fork-delta repos. This issue uses `FRK` for `hybrowlabs/frappe`, `FRH` for `hybrowlabs/frappe-hardened` and `HDK` for `hybrowlabs/helpdesk`, so that three specs in three repositories have three different codes and the closeout index (PWHR-1388) can tell them apart. Open decision for the architect: keep these three codes or rename.

## Clause index

| ID | Title | Described at |
|---|---|---|
| `SPEC-FRK-01` | [Fork delta inventory against upstream `frappe/frappe` (three branches, base and head per branch)](clauses/01-fork-delta-inventory.md) | `operate-v16-release-20260913` `caac3a8a19eb34db47e0487303623b2b8e25ed5e` |
| `SPEC-FRK-02` | [Asset-bundle resolution in `frappe.require` (refresh of the boot asset map)](clauses/02-asset-bundle-resolution.md) | `operate-v16-release-20260913` `caac3a8a19eb34db47e0487303623b2b8e25ed5e` |

A clause that is not in this table does not exist yet.

## What the fork holds (computed 2026-11-04, `git` over `origin` and `upstream`)

| Branch of `hybrowlabs/frappe` | Head | Upstream base | Own commits | Behaviour |
|---|---|---|---|---|
| `develop` (default) | `c4cabbb11ae052115787866f362454276324e8c3` (2023-10-27) | itself: an ancestor of `upstream/develop`, 25850 behind | 0 | none |
| `operate-v16-release-20260913` | `caac3a8a19eb34db47e0487303623b2b8e25ed5e` (2026-09-13) | `upstream/version-16` tag `v16.33.1` `988e54f3c4c291e2077a83809663f123731abe76`, now 2414 behind | 1 | [`SPEC-FRK-02`](clauses/02-asset-bundle-resolution.md) |
| `fix-zoom-on-ios-safari-devices` | `d99a3cc3e0bc4cdb78ae64772e5d952834fd7f1b` (2023-08-08) | `59e1db7bb58e155744f9a2e7912fd233f9fac981` | 1 | one line of `frappe/templates/base.html`, unmerged ([`SPEC-FRK-01`](clauses/01-fork-delta-inventory.md) A1.3 and G1) |

The PW deployment branch map names `hybrowlabs/frappe-hardened`, not this repository, as the Frappe source of the PW UAT and production images (see `SPEC-FRK-01` section 2). Whether any image builds `hybrowlabs/frappe` is not recorded in this repo.

## Tests

- `tests/test_frk_assets.py` holds 13 no-site characterization tests (standard library plus Node 18 or later, no Frappe import, no database). Run from the repo root: `python3 -m unittest tests.test_frk_assets`. `tests/js/assets_harness.js` runs the real, unchanged `frappe/public/js/frappe/assets.js` in a `vm` context with recording stand-ins for `frappe`, `window` and `document`.
- The repo's own tests (`frappe/tests/`, `frappe/**/test_*.py`) need a bench site and are not mapped: this spec covers only the fork's delta.
- Hosted CI has not run on this branch: UNVERIFIED. No bench run was made: every case is `UNVERIFIED` until the receipt of the exact PR head is in the PR body.

## Status of tooling

`tools/check_spec_cases.py` and `tools/check_spec_test_links.py` check form and links only; usage and limits are in [checkers.md](checkers.md). Whether assertions match an Expected result and whether a citation is true stay with the reviewer using [reviewer-checklist.md](reviewer-checklist.md). No CI gate runs them yet.
