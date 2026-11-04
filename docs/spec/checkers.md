# Spec checkers

Two scripts in `tools/` check the files in this folder. They read files only: they never run a test, never import the code under test, and never judge whether a test's assertions match an Expected result (the reviewer does that, see [reviewer-checklist.md](reviewer-checklist.md)). Standard library only, Python 3.10 or later, no `frappe`, no network.

| Script | Checks |
|---|---|
| `tools/check_spec_cases.py` | Clause source header, the eleven sections, the seven-field case schema, area index tables, ID and anchor rules, README clause index. |
| `tools/check_spec_test_links.py` | Spec to test: the test file, class and function exist, are not skipped and are not empty scaffolds. Test to spec: the docstring `Spec:` line. `test-traceability.md` rows. |

Both run from the repo root. A passing run does not prove a case passed; Evidence still needs a receipt (conventions section 10).

## Run

```bash
python3 tools/check_spec_cases.py
python3 tools/check_spec_test_links.py
python3 tools/check_spec_cases.py --verify-commits   # also: each header/receipt SHA exists in git history
python3 tools/check_spec_cases.py --require-performance   # also: section 8 holds a non-empty Performance item
```

| Option | Meaning |
|---|---|
| `--root DIR` | Repo root. Default `.`. |
| `--spec-dir DIR` | Spec folder relative to `--root`. Default `docs/spec`. Must stay inside `--root`. |
| `--format text\|github` | `text` (default) prints `path:line: rule: message`. `github` prints `::error file=...,line=...,title=<rule>::<message>`, which GitHub Actions turns into annotations. |
| `--verify-commits` | (`check_spec_cases.py` only.) Runs `git cat-file` on every 40-hex SHA in a clause header and in a receipt. Needs full history: use `fetch-depth: 0` in `actions/checkout`, otherwise leave it off. |
| `--require-performance` | (`check_spec_cases.py` only; off by default.) Every clause must hold a Performance item in section 8 ([conventions.md section 5.1](conventions.md#51-performance-required-in-section-8)). Off by default so a repo whose merged clauses predate the rule keeps a green check; turn it on once its clauses carry the item. |

### Output and exit codes

- One line per finding on stdout, sorted, then one summary line starting `spec-cases:` or `spec-links:`.
- Exit `0`: no findings. Exit `1`: at least one finding. Exit `2`: usage error, `--root` or `--spec-dir` invalid, `clauses/` missing, or `--verify-commits` outside a git repository (message on stderr).
- Zero clause files is a finding (`no-clauses`, exit 1), not a pass.
- Only `<spec-dir>/clauses/*.md` is scanned. `templates/` is never read, because templates hold `<placeholders>`.
- Run both scripts. Neither implies the other.

## What each check means

Rule names appear in the finding line. Each rule maps to a section in [conventions.md](conventions.md) or [acceptance-cases.md](acceptance-cases.md).

### `check_spec_cases.py`

| Rule | Fires when |
|---|---|
| `clause-filename`, `title-mismatch`, `clause-anchor` | File not `NN-kebab-name.md`; title not `# SPEC-<CODE>-NN: ...`; the `<a id="spec-<code>-nn"></a>` line is missing. |
| `header-stable-id`, `header-described-at`, `header-repo`, `header-branch`, `header-commit`, `header-date` | Header line missing or wrong. The commit must be 40 lowercase hex, never a branch name or `HEAD`; the branch must be named; the committer date must be `YYYY-MM-DD HH:MM:SS +ZZZZ`. |
| `header-also-branch`, `header-also-commit`, `header-also-delta` | `Also read at` is present but lacks a branch, a full SHA, or the `same` / `differs: ...` statement. The line itself is optional. |
| `header-author`, `header-reviewer`, `header-status`, `header-duplicate` | Author/Reviewer line malformed or both the same; status not `DRAFT`, `IN REVIEW` or `ACCEPTED`; a header key given twice. |
| `section-missing`, `section-title`, `section-order`, `section-empty`, `section-unknown`, `section-heading` | The eleven sections of conventions section 5 are not all present, in order, with the exact titles, and non-empty (write `None.` and why). |
| `area-id`, `case-id`, `case-area`, `case-outside-area`, `duplicate-case-id`, `duplicate-clause-id`, `mixed-codes` | ID shape `CORE-01-A1.1A`; code and number match the clause; case sits under its own area; IDs unique across all clauses; one repo code per spec folder. |
| `anchor-missing`, `anchor-mismatch`, `anchor-orphan` | The anchor line above an area or case heading is missing, differs from the lower-cased ID (`.` written `-`), or precedes no heading. |
| `field-missing`, `field-unknown`, `field-order`, `field-duplicate`, `field-empty`, `loose-text` | A case block is not exactly the seven fields in order, or carries other text. |
| `expected-citation` | Expected result does not end with a `` `path.py:12` `` or `` `path.py:12-18` `` citation (relative path, valid range). |
| `test-field`, `environment`, `evidence` | `Test` is not `<mapped\|characterization>: ` plus a Python selector with no wildcard, absolute path or `..`; `Environment` is not one of the two forms; `Evidence` is not `UNVERIFIED`, `UNVERIFIED: <reason>` or a well-formed receipt (exit 0 needs 0 failed and at least 1 passed; a `ci` receipt needs `; run <id>`). |
| `placeholder` | A `<...>` template placeholder is left in a header line, heading or field. |
| `index-table-missing`, `index-table-header`, `index-row-format`, `index-row-missing`, `index-row-unknown`, `index-row-duplicate`, `index-row-link`, `index-row-test` | Each area has the `Case / What the assertions check / Test` table with exactly one row per case; the case link is `<clause-file>#<anchor>`; the test link resolves, from the clause file, to the file named in the `Test` field; the label is `Class.method` or `function`. |
| `no-cases` | Section 11 has no case and no `None.`. |
| `readme-missing`, `readme-index` | `README.md` is missing, a clause file is not linked from it, or it links to a clause file that does not exist. |
| `commit-missing` | (`--verify-commits`.) A SHA is not in the git history. |
| `performance-missing`, `performance-empty`, `performance-unchecked` | (`--require-performance`.) Section 8 has no `- Performance` bullet or `### Performance` heading; the item has no text; or it says "No performance findings" without a `Checked:` list. |

### `check_spec_test_links.py`

| Rule | Fires when |
|---|---|
| `case-unlinkable` | The case has no valid `Test` field to follow (fix it first with `check_spec_cases.py`). |
| `test-file`, `test-missing` | The test file does not exist or does not parse; the class is not in the file; the function is not defined in that class body (an inherited test does not count) or, for a module-level selector, not at module level. The file is read with `ast`, never imported, so Frappe test classes (`FrappeTestCase`, `IntegrationTestCase`) are found like any other class. |
| `test-skipped` | The test, or its class, is skipped: `unittest.skip*`, `expectedFailure`, `pytest.mark.skip*` / `xfail`, `self.skipTest`, `pytest.skip`, `raise SkipTest`. |
| `test-scaffold` | The test has no assertion that can fail: `pass`, import-only, or only literal assertions such as `assertTrue(True)`, `assertEqual(1, 1)`, `assert True`. An assertion in a `self.helper()` of the same class counts. |
| `spec-line-missing`, `spec-line-ref`, `spec-line-duplicate` | The test's own docstring lacks `Spec: <ID> (<spec-dir>/clauses/<file>#<anchor>)`, or the path/anchor differs, or the line appears twice. |
| `spec-line-format`, `spec-line-misplaced` | A `Spec:` line is not exactly `Spec: <ID> (<path>#<anchor>)`, or is in a class or module docstring (each test needs its own). |
| `characterization-line` | A `characterization` case's test lacks `Characterization: pins current behaviour, not endorsed.`, or a test whose cases are all `mapped` carries it. |
| `spec-line-orphan`, `spec-line-mismatch` | Any `Spec:` docstring line in a `.py` file under `--root` names no case, or names a case whose `Test` field points at a different test. Directories named `.git`, `node_modules`, `venv`, `site-packages`, `build`, `dist` and dot-directories are skipped. |
| `test-syntax` | A Python file containing `Spec:` does not parse. |
| `traceability-missing`, `traceability-missing-row`, `traceability-orphan-row`, `traceability-duplicate`, `traceability-row` | `test-traceability.md` is missing, lacks a row for a case, has a row for no case or two rows for one, or a row is not five cells. |
| `traceability-link`, `traceability-clause`, `traceability-kind`, `traceability-test`, `traceability-evidence` | A row's case link, clause ID, kind, test label or test link disagrees with the clause; the row says `UNVERIFIED` where the case has a receipt (or the reverse). |
| `retired-id-reused` | A case ID is listed under `## Retired IDs`. |
| `no-clauses` | As above. |

## Limits

- Only Python tests are checked. A `Test` field naming a JavaScript or TypeScript test is reported as `test-field`; conventions section 5 of [acceptance-cases.md](acceptance-cases.md) keeps such cases `UNVERIFIED` until a JS selector rule exists.
- Skip and assertion detection is static. A test that skips through a helper in another module, or asserts only through a function that is not an `assert*` method, can be misjudged. The reviewer checklist still applies.
- The checkers do not check that `Expected result` is true, that a citation line exists in the code, that Known gaps is honest, or that statutory items carry a source.
- A receipt is checked for form only. Whether it is a real run for the reviewed head is the reviewer's check.

## Copy into another product repo

1. Copy the `tools/` folder (three scripts plus `tools/tests/`) and this file. Change nothing in the scripts for one repo.
2. Keep the spec folder layout of [conventions.md](conventions.md) section 1, or pass `--spec-dir`.
3. Run `python3 tools/check_spec_cases.py && python3 tools/check_spec_test_links.py` at the repo root. Fix every finding before the first clause PR.
4. To run them in CI, use the copy-in workflow in [ci-spec-check.md](ci-spec-check.md) (`templates/spec-check.yml`). It calls each script as `python <script> --root <dir>` and treats exit 0 as clean, 1 as spec problems and anything else as a checker failure, which is the contract above. It is not installed in any repo; installing it is Stage 6 of PWHR-1270.

## Generator for DocType field tables

`tools/gen_doctype_field_tables.py` is not a checker. It writes `docs/spec/reference/core-03-doctype-fields.md` (every DocType's fields, naming, permissions, controller and test-file state, with JSON line numbers) from `cn_hrms_core/cn_hrms_core/doctype/*/*.json` and parses controllers with `ast`; it never imports `frappe`.

```bash
python3 tools/gen_doctype_field_tables.py --branch main --described-at <40-hex>   # rewrite
python3 tools/gen_doctype_field_tables.py --check                                  # exit 1 if the file on disk is stale
```

`Described at` is read back from the existing file when the two options are omitted. Exit 0 ok, 1 stale (`--check`), 2 usage error. `tests/test_master_doctype_schema.py` runs `--check`, so any edit to a DocType file, controller, client script or test file in `doctype/` fails that test until the reference is regenerated and its `Described at` is raised.

## Tests of the checkers

```bash
python3 -m unittest discover -s tools/tests -t tools
```

No site, no network. Every malformed-input test starts from a valid synthetic spec tree, changes one thing, and asserts the specific rule. Mutating a check in the scripts makes these tests fail.
