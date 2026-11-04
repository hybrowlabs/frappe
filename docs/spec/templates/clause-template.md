<!--
Copy to docs/spec/clauses/NN-name.md. Replace every <placeholder>. Delete these comments.
Rules: docs/spec/conventions.md. Case rules: docs/spec/acceptance-cases.md.
Every statement of behaviour ends with a citation `path:line` read at "Described at".
No behaviour fixes in a spec PR. Suspected defects go in section 9.
-->
# SPEC-<CODE>-NN: <Title in plain words>

<a id="spec-<code>-nn"></a>

- Stable ID: `SPEC-<CODE>-NN`
- Described at: repo `<owner/repo>`, branch `<branch>`, commit `<40 hex>` (committer date `<YYYY-MM-DD HH:MM:SS +ZZZZ>`)
- Also read at: branch `<branch, e.g. the branch the deployed image builds from>`, commit `<40 hex>`; <same | differs: files and what differs>
- Author: <role/agent>. Reviewer: <a different role/agent>.
- Status: DRAFT

## 1. Purpose

<What this area does, in one paragraph. Citation.>

## 2. Boundaries

- In: <files, functions, DocTypes this clause covers>.
- Out: <what is covered by another clause (give its ID) or not read>.
- Extension points: <hooks, doc_events, overrides, scheduled jobs that other code uses to reach this area>.

## 3. Behaviour rules

### A1: <Area title>

- A1.1: <One testable sentence. Citation.>
- A1.2: <...>

### A2: <Area title>

- A2.1: <...>

## 4. Data and permissions

- DocTypes, fields, whitelisted methods, roles, permission checks. Citation for each.

## 5. Errors and edge behaviour

- What the code raises or returns on bad input, missing data, duplicates. Citation for each.

## 6. Configuration

- Settings, site config keys, hooks, constants. Name them; never write secret values.

## 7. Scheduled jobs, hooks and patches

- Scheduler events, `doc_events`, patches (with `patches.txt` section and line). Citation for each.

## 8. Static security and performance observations

- Security: what the code reads, writes, exposes or trusts. Facts and citations only; no severity rating.
- Performance (REQUIRED, never omitted; conventions.md section 5.1). One of:
  - Findings, one `- Performance:` bullet each: what the code does, `path:line` citation, and the issue `<key>` of the `(static performance)` issue, or "not filed: reason". Facts only; nothing here was measured unless a run receipt says so.
  - `- Performance: No performance findings. Checked: <list what you looked at, see the checklist in conventions.md section 5.1>.`

## 9. Known gaps / open questions

- G1: <Suspected defect or unclear behaviour. Fact + citation + question. Issue: <key> or "not filed: reason".>
- Statutory source: REQUIRED (supplier: <role>) <- add one per statutory rule

## 10. Uncovered behaviour

- <Rule with no real test: reason, issue key.>

## 11. Acceptance cases

<a id="<code>-nn-a1"></a>
### <CODE>-NN-A1: <Area title>

| Case | What the assertions check | Test |
|---|---|---|
| [<CODE>-NN-A1.1A](NN-name.md#<code>-nn-a1-1a) | <What the assertions check, not the test name.> | [`<function>`](../../../<path/to/test_file.py>) |

<a id="<code>-nn-a1-1a"></a>
#### <CODE>-NN-A1.1A: <Short title>

- Precondition: <state before the action>
- Action: <what is done>
- Expected result: <observable outcome, with citation `path.py:12`>
- Test: <mapped|characterization>: `<path/from/repo/root.py>::<ClassName>::<test_method>`
- Environment: <no-site: unittest, frappe stubbed; no database | bench: Frappe <ver>, <DB>, apps <list>, site <synthetic>>
- Known gaps: <what the assertions do not check, or "None known.">
- Evidence: UNVERIFIED
