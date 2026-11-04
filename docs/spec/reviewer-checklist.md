# Reviewer checklist for as-built spec PRs

For the independent reviewer. The reviewer is not the author of the clause or the tests. Record the reviewed head SHA in your review; a later push needs a new review. Tick only what you checked yourself.

## 1. Header and scope

- [ ] `Described at` has repo, branch, and a 40-hex commit that exists (`git cat-file -t <sha>`).
- [ ] Where the deployed image uses another branch (for PW: `pw-uat` for private apps), `Also read at` is filled and the differences are listed.
- [ ] Author and reviewer in the header are different people or agents.
- [ ] The PR title carries the issue key. The PR changes docs and tests only. No behaviour change in source files (diff outside `docs/` and test files is empty, or each hunk is explained).
- [ ] Core clauses contain no customer name, tenant, host, rate or policy value. PW behaviour appears only in `PW-Customizations` or `pw_helpdesk` specs.

## 2. Claims

- [ ] Sample at least 10 statements per clause (all of them for a clause under 10). For each, open the cited `path:line` at `Described at` and confirm the line supports the sentence.
- [ ] Nothing is described as intended or desirable behaviour. Suspected defects are in Known gaps with an issue key, and no fix is in the PR.
- [ ] `[INFERENCE]` marks exist where the author did not read the code. No framework behaviour is asserted from memory without a marker.
- [ ] Statutory rules: each has `Statutory source: REQUIRED` or a primary source with act, section, authority and date. List the open ones in your review.
- [ ] No credential, token, real person, real salary, customer document or real URL to an internal system appears in specs, tests or fixtures. IDs and e-mails in tests are synthetic.
- [ ] **Performance (blocking).** Section 8 has a non-empty Performance item: findings each with `path:line` and a `(static performance)` issue key (or `not filed: reason`), or "No performance findings" with a `Checked:` list that covers the [conventions.md section 5.1](conventions.md#51-performance-required-in-section-8) checklist. A missing or empty Performance item blocks the PR. Spot-check at least two findings (or two checked items) against the code; where the clause covers code the author did not read, it says so.

## 3. Cases

For each case, read the case first, then the test.

- [ ] Exactly seven fields in order, ID and anchor match, ID not reused.
- [ ] `Test` file and function exist; the kind (`mapped` or `characterization`) is true. A "mapped" test existed at `Described at`.
- [ ] The test is not an empty scaffold: it has an assertion that fails if the behaviour changes.
- [ ] The assertions match the Expected result. Open the test and compare line by line; a name match is not enough.
- [ ] Known gaps lists what the test does not check, including the `mock hides the database` gap for no-site tests.
- [ ] `Evidence` is `UNVERIFIED`, or a receipt whose commit is the reviewed head and whose counts include this test. A receipt for another head is treated as `UNVERIFIED`.
- [ ] Two-way link: the index row link points to the test file; the test has the matching `Spec:` docstring line; the traceability row exists.
- [ ] Every rule in the clause has a case, or appears under Uncovered behaviour with a reason and issue key.

## 4. Tests that were added

- [ ] The characterization test fails when you break the pinned behaviour (mutate one line locally, or state why you could not).
- [ ] The test does not call real services, commit to a shared database or depend on test order.
- [ ] Run it yourself where a runtime exists. Record command, exit code, counts and your own head SHA. Say what you could not run.

## 5. PR body

- [ ] Red block: gaps found, each with a citation and issue key or reason.
- [ ] Blue block: tests mapped or added, with receipts for the exact head.
- [ ] `Could not run:` line present and honest.
- [ ] Open `Statutory source: REQUIRED` count stated.
- [ ] Checks at the current head are green, or each failure is explained, before merge.

## 6. Verdict

State one of: approve / changes requested / blocked, the reviewed SHA, and which sections you did not complete.
