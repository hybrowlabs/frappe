<!--
Copy this section into the repo's AGENTS.md (create the file if it does not exist).
Replace <CODE> with the repo's spec code (docs/spec/conventions.md section 2). Delete this comment.
-->
## Specification and tests

- The as-built specification is in `docs/spec/` (`docs/spec/README.md` has the clause index). It says what the code does now, with `path:line` citations and the branch and commit it was read at. Read the clause for the area before you change it.
- Rules for clauses and cases: `docs/spec/conventions.md` and `docs/spec/acceptance-cases.md`. IDs: clause `SPEC-<CODE>-NN`, case `<CODE>-NN-A<k>.<n><L>`.
- **Spec first.** To change behaviour that has a clause: edit the clause and its cases first (new cases are `Evidence: UNVERIFIED`), then write the failing test and record the real failure, then change the code. Put clause, cases, index row, test, docstring and code in one PR.
- A case has seven fields: precondition, action, expected result, `Test` (kind `mapped` or `characterization`, exact `path::Class::method`), environment, known gaps, evidence. The test carries `Spec: <ID> (docs/spec/clauses/NN-name.md#<anchor>)` in its docstring.
- Never write "passed" without a receipt: command, exit code, counts and the commit SHA of the exact head. A case that was not run on that head is `UNVERIFIED`.
- An empty scaffold test (`class TestX(FrappeTestCase): pass`, no assertion, skipped) is not coverage. Do not link it to a case.
- A suspected defect found while specifying is a Known gap and a separate issue. Do not fix behaviour in a spec PR.
- Do not assert statutory rules (tax, PF/ESIC, leave, attendance law) from memory or from code. Write `Statutory source: REQUIRED`.
- Keep product-core specs and tests customer-neutral. Customer-specific behaviour is specified only in that customer's repo.
- Synthetic data only: no credentials, customer data, real people or HR/payroll records in specs, tests or fixtures.
- Do not skip a test, weaken an assertion or bypass a hook to get a case to pass.

## Pull requests

- The PR title carries the issue key. Use `.github/pull_request_template.md`; fill every section.
- The author is not the reviewer. Review uses `docs/spec/reviewer-checklist.md`.
- Docs-only spec PRs report **Red** (gaps and suspected defects found, with issue keys) and **Blue** (tests mapped or added, with receipts), and a `Could not run:` line. No UI recording applies.
- Verify the checks at the current head before merge. A push needs a new review.
