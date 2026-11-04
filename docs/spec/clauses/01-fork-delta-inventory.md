# SPEC-FRK-01: `hybrowlabs/frappe` fork: delta inventory against upstream `frappe/frappe`

<a id="spec-frk-01"></a>

- Stable ID: `SPEC-FRK-01`
- Described at: repo `hybrowlabs/frappe`, branch `operate-v16-release-20260913`, commit `caac3a8a19eb34db47e0487303623b2b8e25ed5e` (committer date `2026-09-13 12:11:15 +0530`)
- Also read at: branch `fix-zoom-on-ios-safari-devices`, commit `d99a3cc3e0bc4cdb78ae64772e5d952834fd7f1b`; differs: it is a different line of history (one commit on `59e1db7bb58e155744f9a2e7912fd233f9fac981`, 2023-08-08) and holds only a one-line change to `frappe/templates/base.html:6`, which the Described-at commit does not have. Branch `develop`, commit `c4cabbb11ae052115787866f362454276324e8c3` (2023-10-27 16:47:26 +0530) is read for the facts in A1.2 only.
- Author: Developer Agent (Yashwanth). Reviewer: Code Reviewer (Yashwanth).
- Status: DRAFT

## 1. Purpose

This clause lists what the fork `hybrowlabs/frappe` holds that upstream `frappe/frappe` does not, per branch, with the upstream base commit and the fork head. It is a delta spec: it does not describe upstream behaviour. The result, computed by `git` over the fork's three remote branches and the upstream remote (fetched 2026-11-04): the fork carries two commits of its own in total, one on `operate-v16-release-20260913` (specified in `SPEC-FRK-02`) and one on `fix-zoom-on-ios-safari-devices` (A1.3 here). Its default branch `develop` has no commit of its own.

## 2. Boundaries

- In: the three branches of `hybrowlabs/frappe` (`develop`, `fix-zoom-on-ios-safari-devices`, `operate-v16-release-20260913`) and their upstream bases.
- Out: behaviour of the one code delta (`SPEC-FRK-02`); upstream behaviour; the hardened fork `hybrowlabs/frappe-hardened`, which is a separate repository with its own inventory.
- Deployment: the PW branch map recorded in the Multica workspace (verified there on 2026-10-29, not re-read for this clause) lists `hybrowlabs/frappe-hardened` as the Frappe source of the UAT and production images, on branch `fix/hyba-310-frappe-15-121` for UAT and `hardened/version-15` for production, and does not list `hybrowlabs/frappe`. UAT also fails its build unless that branch's checkout equals `7f1c7a9a9f82f67a247b349f2e3cc4ba86aa856f`; that pin belongs to the hardened-fork spec. Which image, if any, builds `hybrowlabs/frappe` is not recorded here: A question for the deployment owner.
- Extension points: none; the fork changes no hook, DocType or patch.

## 3. Behaviour rules

### A1: Branch inventory

- A1.1: `operate-v16-release-20260913` is exactly one commit, `caac3a8a19eb34db47e0487303623b2b8e25ed5e` ("fix(assets): resolve logical bundles from refreshed v16 boot map", Chinmay Kulkarni, 2026-09-13), on top of upstream `version-16` tag `v16.33.1` (`988e54f3c4c291e2077a83809663f123731abe76`, 2026-09-08 17:06:40 +0000); `git rev-list --count upstream/version-16..operate-v16-release-20260913` is 1, and the diff against the tag touches one file, `frappe/public/js/frappe/assets.js` (48 insertions, 6 deletions). Upstream `version-16` has since moved 2414 commits (`3d1284c5fdb52207a516a49bbf2fd186cb43b3ab` on 2026-11-04). Behaviour of the change: `SPEC-FRK-02` (`frappe/public/js/frappe/assets.js:8-61`, `frappe/public/js/frappe/assets.js:186-196`).
- A1.2: `develop` (`c4cabbb11ae052115787866f362454276324e8c3`, "chore: bump `werkzeug` to `3.0.1` (#22945)") is an ancestor of `upstream/develop`: `git rev-list --count upstream/develop..origin/develop` is 0 and the upstream `develop` is 25850 commits ahead (`bb1630488e0be316f24c73dd7e07a51661e07265`). The fork's default branch therefore holds no change of its own and is a 2023-10-27 snapshot of upstream.
- A1.3: `fix-zoom-on-ios-safari-devices` is one commit, `d99a3cc3e0bc4cdb78ae64772e5d952834fd7f1b` ("fix: zoom on input ios safari", Chinmay Kulkarni, 2023-08-08), on upstream commit `59e1db7bb58e155744f9a2e7912fd233f9fac981`. It rewrites line 6 of `frappe/templates/base.html` to `<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" maximum-scale=1">`, so `maximum-scale=1` sits after the closing quote of the `content` attribute and is not part of the viewport value (read at the commit named in the header). The branch is the head of the pull-request ref `refs/pull/1/head` of the fork (`git ls-remote origin`); no other branch contains it, and neither `develop` nor `operate-v16-release-20260913` has it (`git branch -r --contains`). At the Described-at commit the line is the upstream text, without the attribute (`frappe/templates/base.html:6`).
- A1.4: The fork's remote has three branches and one pull-request ref (`git ls-remote origin`), so there is no hardening, patch or customer branch in this repository.

### A2: Delta size

- A2.1: Measured against `upstream/version-16`, the fork's `operate-v16-release-20260913` is 1 commit ahead and 2414 behind (`git rev-list --count` both ways); measured against `upstream/develop`, the same branch is 3495 ahead and 16660 behind because it is a `version-16` line, not a `develop` line. Use the first figure for the delta and ignore the second.

## 4. Data and permissions

- None. The delta adds no DocType, permission, role or whitelisted method of its own; the only server method that the code delta calls already exists upstream at the same tag and is described in `SPEC-FRK-02` (`frappe/sessions.py:192-194`).

## 5. Errors and edge behaviour

- None. The inventory states no runtime behaviour.

## 6. Configuration

- None.

## 7. Scheduled jobs, hooks and patches

- None. The delta touches no `hooks.py`, scheduler event or patch (`git diff --stat` over the single commit lists one JavaScript file).

## 8. Static security and performance observations

- Security: no security hardening is carried by this repository. The hardening line is `hybrowlabs/frappe-hardened`; nothing in this repository's three branches changes authentication, session or output escaping. Observed by the diffstat only; no scan was run, no severity is rated.
- Performance: No performance findings. Checked: (1) database calls in loops, (2) unbounded reads, (3) unindexed filters, (4) scheduler jobs and `doc_events`: none apply, the inventory covers no Python code and the one code delta changes only a browser file; (5) slow work in the request path: not applicable to an inventory; (6) frontend fetch patterns: the one delta adds a conditional extra request, specified and cited in `SPEC-FRK-02` section 8 (`frappe/public/js/frappe/assets.js:33`). The `base.html` change of A1.3 adds no request.

## 9. Known gaps / open questions

- G1: The one change of `fix-zoom-on-ios-safari-devices` puts `maximum-scale=1` outside the `content` attribute, so it is a stray attribute and, read statically, does not set a viewport limit (A1.3). Question: was the intent to stop iOS Safari zooming on input focus? The branch is not merged anywhere in the fork and is not on the PW branch map, so nothing deployed carries it. Issue: not filed: unmerged branch, no deployed effect; the owner decides whether to delete it. [INFERENCE: how browsers read the stray attribute was not run.]
- G2: `develop`, the fork's default branch, is a 2023-10-27 snapshot with no change of its own and 25850 commits behind upstream `develop` (A1.2). Question: is `develop` used by any build? Not found in the PW branch map. Issue: not filed: needs the deployment owner.
- G3: `operate-v16-release-20260913` is 2414 commits behind upstream `version-16` (A1.1). Merging upstream will conflict only in `frappe/public/js/frappe/assets.js`, because that is the only file the fork changes; verified by the diffstat against the base tag, not by a trial merge.
- Statutory source: not applicable; no tax, leave or attendance rule is stated here.

## 10. Uncovered behaviour

- Every rule here is a repository-history fact (commit counts, ancestry, diffstat). A test that would pin it needs the full upstream history, which a shallow CI checkout does not have and which changes every day. Not filed: the facts are recorded with their commands and dates in this clause and are re-computed by the reviewer with `git`.
- The `base.html` viewport line (A1.3) has no test: the branch is unmerged and is not the checked-out tree for any test here. Not filed: see G1.

## 11. Acceptance cases

None.

No case is written: every rule of this clause is a statement about git history, not about runtime behaviour, and no test that can fail on a behaviour change is available for it (section 10). The behaviour of the one code delta is specified, with cases, in `SPEC-FRK-02`.
