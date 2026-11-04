# Spec-check CI workflow template

How to run the spec checkers in CI in any ChatNext HRMS product repo. Template: [`templates/spec-check.yml`](templates/spec-check.yml). Issue: PWHR-1318 (stage 2 of PWHR-1270). The checkers are PWHR-1317; the aggregate is PWHR-1273.

**Status: template only.** It is not installed in any repo, including this one. It sits under `docs/spec/templates/`, a path GitHub does not read for workflows. Installing it in a repo and making it a required check is stage 6 of PWHR-1270, after the pilot format gate (PWHR-1276). Do not copy it into `.github/workflows/` before then.

## 1. What a run proves and does not prove

- It proves: the case blocks have the seven fields, the index rows and test docstrings name each other, the named test file and function exist and are not skipped, and the source header is complete. The exact rules are those of the checkers ([acceptance-cases.md](acceptance-cases.md) section 8 lists what they do not judge).
- It does not run any test. A green run is not a test pass, not coverage and not a receipt. `Evidence` in a case stays `UNVERIFIED` until a real test run receipt exists ([conventions.md](conventions.md) section 10).
- It does not judge whether assertions match an Expected result. The independent reviewer does that ([reviewer-checklist.md](reviewer-checklist.md)).

## 2. Copy-in steps (stage 6 only)

1. The repo has `docs/spec/` (README, conventions, clauses) and the two checker scripts under `tools/` (PWHR-1317; its usage doc is merged with them). If either is missing, stop: the job fails by design when a listed checker file or `docs/spec/` is missing.
2. Copy `docs/spec/templates/spec-check.yml` to `.github/workflows/spec-check.yml`.
3. Edit only these lines:

   | Line | Set to |
   |---|---|
   | `push.branches` | the repo's default branch (the template says `main`) |
   | `SPEC_ROOT` | directory holding `docs/spec/` and the tests it names, relative to the repo root (default `.`) |
   | `SPEC_CHECKERS` | space-separated checker paths; default is the two checkers from PWHR-1317 |
   | `SPEC_PYTHON_VERSION` | at or below the lowest Python the repo supports (default `3.10`) |

4. Do not edit the steps or the job name. Branch protection will require the check named `Spec check`; a renamed job silently drops out of protection.
5. Open the PR with the issue key in the title. Verify the check result at the PR's current head before merge, as for any check.

## 3. Command and exit-code contract with the checkers

| Item | Rule |
|---|---|
| Invocation | `python <checker> --root <dir>` from the repo root. `--root` defaults to the repo root. |
| Dependencies | Python standard library only. No Frappe, no bench, no database, no network, no files written. |
| Exit `0` | No problem found. |
| Exit `1` | Spec problems found, one per line on stdout. |
| Other exit | The checker itself failed (for example usage error, exit `2`). Reported as a checker error, not as a spec problem. |
| Sibling modules | Located relative to the script file, so the checker works from any working directory. |
| Independence | Each checker is run even if an earlier one failed, so one run lists every problem. |

The job exits non-zero if any checker exits non-zero or any listed checker file or `docs/spec/` is missing. A checker that exits `0` after failing to read its input would pass the gate wrongly, so checkers must not do that.

Limit: an uncaught Python exception also exits `1`. The step tells it apart by a line starting `Traceback (most recent call last):` in the checker output and then reports a checker error (exit shown as `1 (traceback)`). A checker whose legitimate problem lines begin with that text would be misreported; checkers must not print such a line.

## 4. What the workflow does

- Triggers: `pull_request`, `push` to the default branch, `workflow_dispatch`.
- Permissions: `contents: read` only. No secrets, no `pull_request_target`, no cache, no artifacts. `persist-credentials: false` on checkout, so the token is not left in the clone.
- Actions are pinned to full commit SHAs with the tag in a comment (`actions/checkout` v7.0.1, `actions/setup-python` v6.3.0). Bump the SHA and comment together; do not use a moving tag.
- Output: one log group per checker, an error annotation on failure, and a job summary table (checker, exit code, result), then one block per failing checker with its output (first 20 000 bytes each).
- Timeout 10 minutes; concurrency cancels an older run on the same PR or ref.
- Runs on a fork PR with the read-only token; nothing in it needs a secret.

## 5. Limits

- Not run on GitHub: the template was linted and its shell step was exercised locally with stub checkers (PR body has the receipt). A hosted GitHub run is `UNVERIFIED` until the template is installed in a repo in stage 6.
- Python and JavaScript/TypeScript test selectors are limited to what the checkers support; see the checker usage doc.
- The workflow does not install the product, so it cannot run the tests the cases name. Running them stays with the repo's own test workflow (for example `ci.yml` in this repo).
- A passing check does not waive any quality, security, privacy or release approval.
