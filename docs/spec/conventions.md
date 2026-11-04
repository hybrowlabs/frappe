# Spec conventions

Applies to every ChatNext HRMS product repo. Adapted from `hybrowlabs/agent-platform` `docs/spec/` (`README.md`, `acceptance-cases.md`). The difference: agent-platform wrote its spec before its code. Our code already runs, so a spec here **describes current behaviour** and each claim is tied to a source line.

Words: MUST, SHOULD and MAY are used as in RFC 2119.

## 1. Layout

```text
docs/spec/
  README.md              layout and clause index
  conventions.md         this file
  acceptance-cases.md    case block rules
  test-traceability.md   index only
  reviewer-checklist.md
  checkers.md            how to run tools/check_spec_*.py
  clauses/NN-name.md     one clause per area, NN = two digits, name = kebab-case
  adr/NNNN-title.md      decisions about the spec system
  templates/             copy-ready templates (not clauses)
```

- One writer per clause file at a time. A second PR that needs the same clause rebases onto the first and keeps its content.
- A clause file never holds a rule for another repo.
- Tools that scan `docs/spec/clauses/` MUST NOT scan `templates/`; templates hold placeholders.

## 2. IDs

| Thing | Format | Example |
|---|---|---|
| Clause | `SPEC-<CODE>-NN` | `SPEC-CORE-01` |
| Area in a clause | `A<k>` | `A2` |
| Case | `<CODE>-NN-A<k>.<n><L>` | `CORE-01-A2.1B` |
| Area anchor | the area ID in lower case | `core-01-a2` |
| Case anchor | the case ID in lower case, `.` written as `-` | `core-01-a2-1b` |
| Clause anchor | the clause ID in lower case | `spec-core-01` |

- `NN` matches the clause file number. `A<k>` is the k-th behaviour area of that clause. `<n>` is a topic group inside the area, `<L>` is one case in the group (`A`, `B`, `C`...).
- An ID is never reused and never renumbered. A removed case is listed under "Retired IDs" in `test-traceability.md`.
- Clause `00` is reserved for the worked example. It is not copied to other repos.
- Codes (proposal, see [ADR-0001](adr/0001-spec-system-conventions.md)):

| Code | Repository |
|---|---|
| `CORE` | CN-HRMS-Core |
| `PAY` | ERPNext-India-Payroll |
| `LSM` | cn-leave-shift-managment |
| `NEXT` | chatnext |
| `PMS` | cn-pms |
| `REC` | cn-recruitment |
| `EXP` | chatnext-expense-trips |
| `WC` | chatnext-work-connect |
| `TODO` | cn_todo_manager |
| `CAND` | Candidate-Portal |
| `ALUM` | alumni-portal |
| `STU` | Cn-Studio |
| `PWC` | PW-Customizations (customer PW only) |
| `PWH` | pw_helpdesk (customer PW only) |

Repos with no code yet (hrms-test-automation mapping, fork inventory) are an open decision in ADR-0001.

## 3. Source header (mandatory)

Every clause file starts with this block, before any behaviour text:

```markdown
- Stable ID: `SPEC-<CODE>-NN`
- Described at: repo `<owner/repo>`, branch `<branch>`, commit `<40 hex>` (committer date `<YYYY-MM-DD HH:MM:SS +ZZZZ>`)
- Also read at: branch `<branch>`, commit `<40 hex>`; <same | differs: list files and what differs>   (omit if not applicable)
- Author: <role/agent>. Reviewer: <a different role/agent>.
- Status: DRAFT | IN REVIEW | ACCEPTED
```

- `Described at` is the commit all `path:line` citations refer to. Use the full 40-hex SHA, never a branch name alone and never `HEAD`.
- Where the deployed image builds a private app from a branch other than the default branch (for example a customer deployment that pins its apps to a release branch), read the cited files at that branch tip too and fill `Also read at`. If a cited file or line differs, say so in the header and in Known gaps. Differences are facts; do not pick the "right" branch. Branch names are allowed in the header of a core clause; customer behaviour is not (section 7).
- The spec PR's own commit is not `Described at`. Do not rewrite `Described at` unless you re-read every cited line at the new commit.

## 4. Citations

- Every statement of behaviour, data, permission, error, config or schedule ends with a citation: `` `path/from/repo/root.py:12` `` or `` `path.py:12-18` `` (inclusive). No absolute paths. No URLs inside a clause.
- A citation says "the code at `Described at` does this". It does not say "the code is right".
- If you could not find the code, say `Not found in code` and put it in Known gaps. Do not guess from names.
- Observed-by-running statements are separate: say what you ran, where, and the result. Otherwise the statement is read-only analysis.
- Statements you infer (framework behaviour you did not read, data you did not see) are written `[INFERENCE]` and listed in Known gaps.

## 5. What a clause contains

Use [`templates/clause-template.md`](templates/clause-template.md). Sections, in order:

1. Purpose
2. Boundaries (in, out, neighbouring clauses, extension points)
3. Behaviour rules, grouped in areas `A1`, `A2`... Each rule is one testable sentence with its citation.
4. Data and permissions
5. Errors and edge behaviour
6. Configuration
7. Scheduled jobs, hooks and patches
8. Static security and performance observations
9. Known gaps / open questions (suspected defects go here, each with an issue key once filed)
10. Uncovered behaviour (rules with no test, with reason and issue key)
11. Acceptance cases (index table, then the case blocks)

Write in plain words, present tense. Say "you" only when you instruct the reader. Omit a section only by writing `None.` and why.

Rules for what you may and may not write:

- **Current behaviour only.** Not intended behaviour, not a design critique. A suspected defect is a fact about the code plus a question, in section 9, and a separate issue. **No behaviour fixes in a spec PR.**
- **Security and performance** are static findings: what the code reads, builds or queries. Do not run load or security scans against UAT or production. Do not rate severity unless a security reviewer does.
- **Core stays customer-neutral** (section 7).

### 5.1 Performance (required in section 8)

Section 8 MUST hold a Performance item. A clause with no Performance item, or an empty one, is not complete and is a blocking finding in review ([reviewer-checklist.md](reviewer-checklist.md) section 2). Section 8 keeps its number and title so existing clauses and checkers stay valid; the Performance item is the required part of it.

Write one of:

- **Findings.** One bullet per finding, in the form: `- Performance: <what the code does> (<path:line>). Issue: <key>`. The issue is a separate `(static performance)` issue with the same citation, or `not filed: <reason>`. Several bullets are fine; a `- Performance, <topic>:` or `- Performance (n):` label is accepted.
- **No findings.** `- Performance: No performance findings. Checked: <list>.` The list names what you looked at, from the checklist below. A bare "None." is not accepted.

Checklist: look for each of these in the code the clause covers, and cite `path:line` for what you find.

1. Database calls in loops (N+1), and commits or `set_value`/`save` per row.
2. Unbounded reads (`limit_page_length=0`, no `limit`) and a full result built in memory before paging or slicing.
3. Unindexed filters and sorts (leading-wildcard `LIKE`, filters on text or JSON columns, `ORDER BY` on unindexed columns).
4. Scheduler jobs and `doc_events` that scan all records, or that run on every save of every DocType.
5. Slow work in the request path (external calls, PDF or mail generation, large loops that belong in a background job).
6. Frontend fetch patterns: one request per row, no paging, refetch on every render, large payloads, assets loaded on every page.

Rules: facts and citations only, no severity, no load test against UAT or production. State what was not read. Findings are not fixed in the spec PR (section 5 above).

Optional check: `python3 tools/check_spec_cases.py --require-performance` fails a clause whose section 8 has no Performance item (`performance-missing`), an empty one (`performance-empty`), or "No performance findings" without `Checked:` (`performance-unchecked`). It is off by default; see [checkers.md](checkers.md).

## 6. Statutory rules

Payroll, tax, PF/ESIC, leave and attendance law are never asserted from memory, and never from the code alone.

- Write what the code does with a citation (for example "the code applies the constant at `path.py:40`").
- Immediately after it write: `Statutory source: REQUIRED (supplier: <role>)`.
- A statutory claim is accepted only when the line is replaced with `Statutory source: <Act or notification, section, issuing authority, retrieval date, supplied by>` and the source is a primary or authoritative one. A secondary blog or an AI answer does not count.
- A test for such a rule pins the code's value. Its case says in Known gaps: `Does not verify statutory correctness.`
- `Statutory source: REQUIRED` is an open item; the reviewer counts the open ones in the PR.

## 7. Customer isolation

- Core and product repo clauses are customer-neutral: no customer name, tenant, hostname, user, rate or policy value of one customer.
- Customer behaviour lives only in that customer's repos: PW behaviour is specced only in `PW-Customizations` and `pw_helpdesk` (codes `PWC`, `PWH`). Those clauses say what they override in core by citing the core clause ID.
- Homefirst Finance and any other customer: separate repos and separate specs; never mixed with PW.
- Deployment branch names may appear in a header (section 3). Behaviour read only on that branch is recorded as a branch delta, not as core behaviour.

## 8. Tests and cases

### 8.1 Two kinds of test link

| Kind | Definition | Rules |
|---|---|---|
| **Mapped** | A test that already existed at `Described at`. | You may add only the `Spec:` docstring line. You MUST read its assertions and write in the case what they check. What they do not check goes in `Known gaps`. |
| **Characterization** | A test added by the spec PR that pins what the code does now. | It runs the real code path and asserts an observable outcome (return value, raised error, query issued, document state). Its docstring says `Characterization: pins current behaviour, not endorsed.` It MUST fail if the pinned behaviour changes. If the pinned behaviour is a suspected defect, the case's Known gaps names the issue. |

The case's `Test` field states the kind (see [acceptance-cases.md](acceptance-cases.md#4-case-block)).

### 8.2 Empty-scaffold rule

An **empty scaffold** is a test that cannot fail on a behaviour change: a class with only `pass`, a test method with no assertion, only `assertTrue(True)`, a skipped test, a test that only imports. Example: `class TestEmployeeRole(FrappeTestCase): pass`.

- An empty scaffold MUST NOT be mapped to a case and does not count as coverage.
- A rule that has no real test is listed under "Uncovered behaviour" in its clause with the reason and issue key. There is no case without a real test.
- Counting scaffolds is a finding. Fix by writing a characterization test, not by editing the scaffold to pass.

At `c01016b5b530097366904f082fed97c55d25d9c2` (`main`), 57 of the 58 files named `test_*.py` under `cn_hrms_core/` define no test method; this was counted by parsing the files, not by running them. The only one with methods is `cn_hrms_core/cn_hrms_core/notifications/test_placeholders.py`.

### 8.3 Two test environments

| Environment | Used for | How to run | `Environment` text |
|---|---|---|---|
| **no-site** | Pure Python logic, patches, API functions with `frappe` stubbed | `python3 -m unittest <module>` from the repo root | `no-site: unittest, frappe stubbed; no database` |
| **bench** | Anything that needs a real DocType, query or hook | `bench --site <site> run-tests --app <app> ...` on a test site | `bench: <Frappe version>, <DB>, apps <list>, site <synthetic>` |

- A bench test is written and linked now, and stays `UNVERIFIED` until a bench run exists (bench feasibility is tracked in PWHR-1272). Do not wait for the bench to write the spec.
- A bench test that mocks nothing needs synthetic records created inside the test. Do not call `frappe.db.commit()` in a test; if a test must commit, it deletes what it made.
- Which test paths the repo's CI discovers is stated per repo. For CN-HRMS-Core, CI runs `bench --site test_site run-tests --app cn_hrms_core` (`.github/workflows/ci.yml:104`), and CI is triggered by pushes to `develop` and by pull requests (`.github/workflows/ci.yml:5-8`). Whether that command discovers the root-level `tests/` directory has not been verified (open decision D7 in ADR-0001).
- Synthetic data only: IDs like `EMP-TEST-0001`, e-mail `*@example.invalid`, no real names, numbers, salaries or documents. No credentials in a test, fixture or spec.

## 9. Spec-first changes

For a later change to behaviour that already has a clause:

1. Edit the clause first: add or change the rule and its cases (new area `A<k+1>` for new behaviour; an existing ID keeps its meaning). Add a line `Updated for <issue key> at <commit>` under the header. New cases are `UNVERIFIED`.
2. Write the failing test. Record the real failure (command, output, revision). Do not invent a test-first history.
3. Change the code until the test passes.
4. In one PR: clause, case, index row, test, docstring, code. The PR body lists each affected case ID with actual results.
5. A changed head needs a new check run and a new review.

## 10. Evidence

### 10.1 Case evidence field

`Evidence:` is `UNVERIFIED`, `UNVERIFIED: <reason>`, or a receipt:

- `local; <command>; exit N; P passed, F failed, S skipped; commit <40 hex>; env <no-site|bench:...>`
- `ci; <command>; exit N; P passed, F failed, S skipped; commit <40 hex>; env <...>; run <CI run id>`

Exit 0 needs 0 failed and at least 1 passed, and the case's own test must not be among the skipped. A receipt is bound to a commit; a receipt for another head is not evidence for this one.

New cases are written `UNVERIFIED`. A receipt written into a file goes stale when the branch is rebased, so the exact-head results go in the PR body. A receipt is copied into the case only at closeout, with its commit. Never write "passed" without a receipt. Which receipt kind counts as acceptance is an open decision (D5 in ADR-0001).

### 10.2 Docs-only PR evidence: Red and Blue

Pomerado browser recordings do not apply to a docs-only spec PR. In its place the PR body has two blocks:

- **Red** = what you found wrong or missing while reading or characterizing: suspected defects, undocumented behaviour, uncovered rules, scaffold counts, branch deltas. Each item has a citation and an issue key (or "not filed: reason"). Red is not a failure of the PR.
- **Blue** = the tests you mapped or added, each with its run receipt (command, exit code, counts, commit SHA of the exact head), plus any check that ran on the spec files themselves.

Then one line `Could not run:` listing every test or check that was not run and why (for example "no bench available"). If a UI exists and the PR changes it, normal UI evidence applies instead; a spec PR changes no UI.

## 11. Review

The author is never the reviewer. The reviewer reads the case first, then the code at the cited lines, and uses [reviewer-checklist.md](reviewer-checklist.md). The head that is reviewed is the head that is merged; a new push needs a new review. Verify the CI checks at the current head before merge.

Each repo's spec set ends with an independent review issue.

## 12. Limits of these conventions

- These rules do not prove the code is right. They record what it does and which test would notice a change.
- A link is not coverage, and a case is not a pass. Only a receipt for the exact head is evidence of a run.
- Checkers (`tools/check_spec_cases.py`, `tools/check_spec_test_links.py`, [checkers.md](checkers.md)) check case schema and the two-way links. They do not check that assertions match the Expected result; the reviewer does that.
