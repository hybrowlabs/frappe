# Acceptance cases: how to write, link and check them

Adapted from `hybrowlabs/agent-platform` `docs/spec/acceptance-cases.md`. The behaviour is in the clause file as an acceptance case with a stable ID. [test-traceability.md](test-traceability.md) is an index only. General rules (source header, citations, test kinds, evidence) are in [conventions.md](conventions.md).

## 1. Where a case lives

- File: the clause file, `docs/spec/clauses/NN-name.md`, in the section `## 11. Acceptance cases` (the last section of the clause template).
- A clause groups cases by area. One area is `### <CODE>-NN-A<k>: Title` (for example `### CORE-00-A1: Title`), with the anchor line `<a id="<code>-nn-a<k>"></a>` directly above it. The area holds an index table, then the case blocks.
- One case checks one behaviour. If the Action needs "and", split it.

## 2. Case ID

`<CODE>-<NN>-A<k>.<n><L>` (for example `CORE-00-A1.1B`).

- Anchor: lower case, `.` written as `-` (`core-00-a1-1b`).
- Never reused, never renumbered. A removed case moves to "Retired IDs" in `test-traceability.md`.

## 3. Seven-field rule

A case block has the anchor line, a heading, and exactly seven fields in this order. No other field, no `Result` or `Status` line, no loose text.

## 4. Case block

```markdown
<a id="core-00-a1-1b"></a>
#### CORE-00-A1.1B: Short title in plain words

- Precondition: the state before the action.
- Action: what is done.
- Expected result: what must be true afterwards, as the code does it now (with citation).
- Test: mapped: `tests/test_x.py::TestClass::test_name`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: what the test does not show. Write "None known." if none.
- Evidence: UNVERIFIED
```

Field rules:

- **Precondition, Action, Expected result**: plain language, one behaviour. Expected result ends with a citation to the source line that produces it (`path.py:12`), as at `Described at`. State only observable outcomes: return value, raised error, query issued, document state, message queued.
- **Test**: `<kind>: ` then the selector in backticks.
  - `<kind>` is `mapped` (test existed at `Described at`) or `characterization` (added by the spec PR). See [conventions.md section 8.1](conventions.md#81-two-kinds-of-test-link).
  - Selector for a class-based test: `path/from/repo/root.py::ClassName::test_method`. For a module-level function: `path/from/repo/root.py::test_function`. No wildcard, no absolute path, no `..`. The file and the function MUST exist.
  - A case with no real test does not exist. List the rule under "Uncovered behaviour" in the clause. An empty scaffold (see [conventions.md section 8.2](conventions.md#82-empty-scaffold-rule)) is not a test.
- **Environment**: `no-site: unittest, frappe stubbed; no database`, or `bench: <Frappe version>, <DB>, apps <list>, site <synthetic>`.
- **Known gaps**: list what the assertions do not check. If the pinned behaviour looks like a defect, name the issue key. For a statutory rule write `Does not verify statutory correctness. Statutory source: REQUIRED`.
- **Evidence**: `UNVERIFIED`, `UNVERIFIED: <reason>`, or a receipt (conventions section 10.1). A link is not a pass.

Links inside `docs/spec/` are relative. A case block holds no URL.

## 5. Index row and test docstring (two-way link)

Spec to test: the area index table.

```markdown
| Case | What the assertions check | Test |
|---|---|---|
| [CORE-00-A1.1B](00-name.md#core-00-a1-1b) | One line of what the assertions check. | [`test_name`](../../../tests/test_x.py) |
```

First link goes to the case, last link goes to the test file. Both relative. The middle cell lists what the assertions check, not what the test is called.

Test to spec: one docstring line (Python), exact path, no `*`:

```python
def test_name(self):
    """Spec: CORE-00-A1.1B (docs/spec/clauses/00-name.md#core-00-a1-1b)"""
```

A characterization test adds a second line: `Characterization: pins current behaviour, not endorsed.`

For a class-level docstring covering several tests, repeat nothing: each test needs its own `Spec:` line. A test that covers two cases carries two `Spec:` lines.

JavaScript or TypeScript tests (for repos with a React app): a line comment directly above the `it(` or `test(` call: `// Spec: <ID> (docs/spec/clauses/NN-name.md#<anchor>)`. The selector is `path/file.test.ts::exact test name`. Repo-specific selector rules for non-Python tests are added when the checker for that language exists; the current checkers accept Python selectors only, so such cases stay `UNVERIFIED` and are reported by the checker as `test-field`.

## 6. Writing steps for an as-built clause

1. Record `Described at` (conventions section 3).
2. Read the code; write each rule with its citation. Mark `[INFERENCE]` and `Statutory source: REQUIRED` where needed.
3. For each rule decide: an existing test covers it (mapped), you write a characterization test, or it is uncovered. Read the test's assertions before you write the Expected result.
4. Write the case blocks with `Evidence: UNVERIFIED`.
5. Add the `Spec:` docstring to the mapped or new test, the index row, and the row in `test-traceability.md`.
6. Run what can run. Put each real result in the PR body (command, exit code, counts, commit SHA of the exact head). Everything else stays `UNVERIFIED`.
7. File an issue for each suspected defect. Do not change behaviour in the spec PR.

## 7. Review steps

The reviewer follows [reviewer-checklist.md](reviewer-checklist.md). Short form: read the case first; open the cited source line; open the test; check that the assertions match the Expected result and that Known gaps are honest; check that Evidence matches a receipt for the reviewed head.

## 8. Limits

- The checkers (`tools/check_spec_cases.py`, `tools/check_spec_test_links.py`, see [checkers.md](checkers.md)) check the case schema, that the index row and the test docstring name each other, and that the test exists and is neither skipped nor an empty scaffold. They do not run tests, and they do not judge whether assertions match the Expected result.
- Everything else here is enforced by the reviewer.
- A case link does not waive any quality, security, privacy or release approval.
