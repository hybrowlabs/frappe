## What this changes

<!-- One or two sentences. PR title must carry the issue key (for example PWHR-1271). -->

## Linked issue and clauses

- Issue: <!-- PWHR-____ -->
- Clauses: <!-- SPEC-<CODE>-NN, or "none" -->
- Described at: <!-- repo, branch, 40-hex commit read for the spec -->
- Also read at: <!-- deployed-branch commit, or "not applicable" -->

## Behaviour change

- [ ] No behaviour change: only `docs/spec/` and tests (docstrings or new characterization tests) changed.
- [ ] Behaviour changes, and the clause and cases were edited first in this PR.

## Cases in this PR

<!-- One row per case. Say what the assertions check, not what the test is called. Kind is mapped or characterization. -->

| Case ID | Kind | What the assertions check | Test file and function |
|---|---|---|---|
| | | | |

## What this PR does not do

<!-- Explicit limits: behaviour, environments or checks out of scope. -->

## Red: gaps found while reading or characterizing

<!-- Suspected defects, undocumented behaviour, uncovered rules, empty-scaffold counts, branch differences. Each with a citation and an issue key, or "not filed: reason". Red is not a failure of the PR. -->

## Blue: tests and run receipts

<!-- Results are facts from a run on the exact head. -->

| Case ID | Command | Exit | Counts (passed/failed/skipped) | Commit SHA (exact head) | Environment |
|---|---|---|---|---|---|
| | | | | | |

UNVERIFIED cases (linked but not run on the exact head, or not run at all):

- <!-- case ID and reason, or "none" -->

Could not run: <!-- every test or check not run and why, for example "no bench available" -->

## Open statutory items

<!-- Count of `Statutory source: REQUIRED` lines, and the supplier role for each. "none" if none. -->

## Checklist

- [ ] Every statement in the clause has a `path:line` citation at `Described at`.
- [ ] Section 8 of every new or changed clause has a Performance item: findings with `path:line` and a `(static performance)` issue key, or "No performance findings. Checked: ..." (`docs/spec/conventions.md` section 5.1).
- [ ] No empty scaffold is linked as a test.
- [ ] Core clauses name no customer; customer behaviour is only in that customer's repo.
- [ ] Synthetic data only; no credentials or real HR/payroll data.
- [ ] The reviewer is not the author (`docs/spec/reviewer-checklist.md`).

A link is not coverage and not a pass. A case that was not run stays UNVERIFIED.
