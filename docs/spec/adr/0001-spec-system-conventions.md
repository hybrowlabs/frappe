# ADR-0001: As-built spec conventions for ChatNext HRMS repos

## Status

Proposed. Not accepted until the pilot format sign-off (PWHR-1276) and answers to the open decisions below.

## Date

2026-10-30

## Context

PWHR-1270 moves ChatNext HRMS to spec-driven development. Each product repo gets an as-built spec with acceptance cases that link to real tests. The reference model is `hybrowlabs/agent-platform` `docs/spec/`, which wrote its spec before its code. Our code already runs, so specs here record current behaviour with `path:line` citations and the branch and commit they were read at. PW's image builds eight private apps from `pw-uat`, not default branches (source: PWHR-1270), so the branch matters. The copy-ready conventions state this generically; the PW fact is recorded only here.

Measured at CN-HRMS-Core `main` `c01016b5b530097366904f082fed97c55d25d9c2`: 57 of 58 `test_*.py` files under `cn_hrms_core/` define no test method (parsed, not run). The repo's CI runs `bench --site test_site run-tests --app cn_hrms_core` (`.github/workflows/ci.yml:104`). Root-level `tests/` holds three no-site `unittest` files.

## Decision

Adopt the conventions in `docs/spec/conventions.md` and `docs/spec/acceptance-cases.md`, with the choices below.

1. Per-repo spec in `docs/spec/`, with clauses `SPEC-<CODE>-NN` and cases `<CODE>-NN-A<k>.<n><L>`.
2. The source header (`Described at`, `Also read at`) is mandatory.
3. A case's test is `mapped` (existed before) or `characterization` (added by the spec PR). Empty scaffolds are never mapped.
4. New case evidence is `UNVERIFIED`; receipts are bound to a commit; exact-head results go in the PR body.
5. Statutory rules are `Statutory source: REQUIRED` until an authoritative source is given.
6. Core specs are customer-neutral; PW behaviour is specced only in PW-Customizations and pw_helpdesk.
7. Clause `00` in CN-HRMS-Core is a worked example, not copied to other repos.

## Alternatives considered

- **Copy agent-platform verbatim** (`FAS-SPEC-NN`, verbatim original text plus plain-words section): rejected. That layout fits a spec that exists as a source document. We have no source document, only code.
- **One central spec repo**: see open decision D2.
- **Cases in `test-traceability.md` only**: rejected; agent-platform moved to cases in the clause file with the index as a derivative, which avoids two sources of truth.

## Open decisions (sent to chinmay)

| # | Decision | Proposal in these docs | Alternative |
|---|---|---|---|
| D1 | Spec ID codes | `CORE PAY LSM NEXT PMS REC EXP WC TODO CAND ALUM STU PWC PWH` | Longer or different codes; changing later means renumbering every ID |
| D2 | Where specs live | Per repo, in `docs/spec/`, plus a cross-repo index at closeout (PWHR-1388) | A central index or spec repo; cost: specs drift from the code they describe |
| D3 | Repos without a code home (hrms-test-automation mapping PWHR-1386, fork delta inventory PWHR-1387) | Assign codes `E2E` and `FORK` when those issues start | Put them under the closeout repo |
| D4 | Case ID shape | Keep `<CODE>-NN-A<k>.<n><L>` as proposed in the issue; `NN-A<k>` ties each area to its clause | Drop `A<k>` for shorter IDs |
| D5 | Which receipt counts as acceptance (agent-platform: only Argo CI) | `local` and `ci` receipts both allowed; reviewer decides at closeout | CI-only, once the bench in PWHR-1272 and the CI template in PWHR-1273 exist |
| D6 | Install `AGENTS.md` and the PR template in CN-HRMS-Core now or after pilot sign-off | After sign-off: they would change contribution rules for every PR. Not installed by this PR | Install now as part of the pilot PR |
| D7 | Does `bench run-tests --app cn_hrms_core` discover root-level `tests/`? | Not verified; no-site tests there are run directly with `python3 -m unittest` | Move spec tests under `cn_hrms_core/` |
| D8 | CI trigger branch: `ci.yml` pushes only on `develop`, which this repo has no remote branch for (`git ls-remote origin develop` returned nothing) | Report only; pull-request trigger still applies | Fix in a separate issue |
| D9 | Statutory source supplier per repo (payroll, leave, attendance) | Named in each clause as a role | A single compliance owner |

## Consequences

- Every clause costs a source header and a citation per statement; readers can re-check any line.
- Checkers exist for case schema and spec/test links (`tools/`, PWHR-1317, see `checkers.md`); everything they do not check is enforced by the reviewer with `reviewer-checklist.md`.
- Changing an ID code after clauses exist means renumbering across clauses, tests and index rows.
