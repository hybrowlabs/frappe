#!/usr/bin/env python3
"""Check the as-built spec clauses: source header, sections, case schema, index rows.

Checks, per clause file in ``<spec-dir>/clauses/*.md`` (never ``templates/``):

* source header: Stable ID, Described at (repo, branch, full 40-hex commit, committer
  date), optional Also read at, Author/Reviewer different, Status;
* the eleven sections in order, none empty; with ``--require-performance`` (opt-in) section 8
  also holds a Performance item: findings, or "No performance findings. Checked: ...";
* every case: ID shape and clause/area match, anchor line above the heading, exactly the
  seven fields in order, Expected result ends with a ``path:line`` citation, Test field
  well-formed, Environment form, Evidence form (``UNVERIFIED`` or a well-formed receipt),
  no template placeholder left;
* every area has an index table with one row per case, linking to the case anchor and
  to the test file named in the case's Test field;
* IDs are unique across the spec; all clauses use one repo code; ``README.md`` lists
  each clause file.

It does not run tests and does not judge whether assertions match an Expected result.
Test existence and the spec/test two-way link are checked by ``check_spec_test_links.py``.

Exit codes: 0 no findings, 1 findings, 2 usage error or spec tree missing.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spec_check_common import (  # noqa: E402
    Finding,
    UsageError,
    commit_exists,
    discover_clauses,
    parse_clause,
    performance_findings,
    require_git_repo,
    run_cli,
)


def check(layout, ns):
    files, findings = discover_clauses(layout)
    clauses = [parse_clause(layout, p) for p in files]
    for c in clauses:
        findings.extend(c.findings)
        if ns.require_performance:
            findings.extend(performance_findings(c))

    # --- cross-clause rules -----------------------------------------------------
    stable: dict = {}
    case_ids: dict = {}
    codes: dict = {}
    for c in clauses:
        if c.stable_id:
            if c.stable_id in stable:
                findings.append(Finding(c.rel, 1, "duplicate-clause-id",
                                        f"{c.stable_id} is already used by {stable[c.stable_id]}"))
            stable.setdefault(c.stable_id, c.rel)
            codes.setdefault(c.code, c.rel)
        for case in c.cases:
            if case.id in case_ids:
                findings.append(Finding(c.rel, case.line, "duplicate-case-id",
                                        f"case ID {case.id} is already used at {case_ids[case.id]}"))
            case_ids.setdefault(case.id, f"{c.rel}:{case.line}")
    if len(codes) > 1:
        listing = ", ".join(f"{k} ({v})" for k, v in sorted(codes.items()))
        findings.append(Finding(layout.rel(layout.clauses_path), 1, "mixed-codes",
                                f"clause files use more than one repo code: {listing}; a clause never holds a rule for another repo"))

    # --- README clause index -----------------------------------------------------
    readme = layout.spec_path / "README.md"
    if not readme.is_file():
        findings.append(Finding(layout.rel(readme), 1, "readme-missing", "README.md with the clause index is missing"))
    else:
        text = readme.read_text(encoding="utf-8", errors="replace")
        linked = {}
        for i, line in enumerate(text.split("\n"), start=1):
            for m in re.finditer(r"\]\(clauses/([^)#\s]+)(?:#[^)]*)?\)", line):
                linked.setdefault(m.group(1), i)
        names = {p.name for p in files}
        for name in sorted(names - set(linked)):
            findings.append(Finding(layout.rel(readme), 1, "readme-index",
                                    f"clauses/{name} is not listed in the README clause index"))
        for name, ln in sorted(linked.items()):
            if name not in names and name.endswith(".md"):
                findings.append(Finding(layout.rel(readme), ln, "readme-index",
                                        f"README links to clauses/{name}, which does not exist"))

    # --- optional commit existence -----------------------------------------------
    if ns.verify_commits:
        require_git_repo(layout.root)
        checked: dict = {}
        for c in clauses:
            for ln, sha in c.sha_lines:
                if sha not in checked:
                    checked[sha] = commit_exists(layout.root, sha)
                if not checked[sha]:
                    findings.append(Finding(c.rel, ln, "commit-missing",
                                            f"commit {sha} is not in this repository (shallow clone? use fetch-depth: 0)"))

    ncases = sum(len(c.cases) for c in clauses)
    return findings, f"{len(clauses)} clause(s), {ncases} case(s)"


def _add_args(ap):
    ap.add_argument("--verify-commits", action="store_true",
                    help="require each header/receipt commit SHA to exist in the git history of --root")
    ap.add_argument("--require-performance", action="store_true",
                    help="require a non-empty Performance item in section 8 of every clause "
                         "(opt-in; docs/spec/conventions.md section 5.1)")


def main(argv=None) -> int:
    return run_cli(
        "check_spec_cases.py",
        "Check spec clause headers, sections, case schema and area index tables.",
        "spec-cases",
        check,
        argv,
        _add_args,
    )


if __name__ == "__main__":
    sys.exit(main())
