#!/usr/bin/env python3
"""Check the two-way link between spec cases and Python tests.

For every case in ``<spec-dir>/clauses/*.md`` (never ``templates/``):

* spec -> test: the test file named in the Test field exists and parses, the class
  (if any) and the function exist in it (Python, including Frappe ``FrappeTestCase`` /
  ``IntegrationTestCase`` classes, found by reading the file, never by importing it);
* the test is real: not skipped (``unittest.skip*``, ``expectedFailure``,
  ``pytest.mark.skip*``, ``self.skipTest``, ``pytest.skip``, ``raise SkipTest``) and not an
  empty scaffold (no assertion, only ``assertTrue(True)``-style constants);
* test -> spec: the test's docstring has ``Spec: <ID> (<spec-dir>/clauses/<file>#<anchor>)``
  with the exact ID, path and anchor; a ``characterization`` case also has the line
  ``Characterization: pins current behaviour, not endorsed.``, a ``mapped`` one does not;
* every ``Spec:`` line found in the repo's Python files names an existing case that
  maps that very test, and sits in a function docstring;
* ``<spec-dir>/test-traceability.md`` has one row per case with the matching clause,
  kind, test and evidence class, no row for an unknown case, and no retired ID is
  reused.

It does not run tests and does not judge whether assertions match an Expected result.
Case schema and index tables are checked by ``check_spec_cases.py``.

Exit codes: 0 no findings, 1 findings, 2 usage error or spec tree missing.
"""
from __future__ import annotations

import ast
import os
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spec_check_common import (  # noqa: E402
    CASE_ID_RE,
    CHARACTERIZATION_LINE,
    Finding,
    discover_clauses,
    evidence_is_unverified,
    parse_clause,
    run_cli,
    selector_label,
)

SPEC_LINE_RE = re.compile(r"^\s*Spec: (\S+) \(([^()\s]+)\)\s*$")
SKIP_DECORATORS = {"skip", "skipIf", "skipUnless", "expectedFailure", "skipTest"}
SKIP_CALLS = {"skipTest", "skip", "importorskip"}
SCAN_PRUNE = {".git", "node_modules", "__pycache__", "venv", ".venv", "env", "site-packages", ".tox", "build", "dist"}


# ---------------------------------------------------------------------------
# Reading test files
# ---------------------------------------------------------------------------

class TestFile:
    def __init__(self, rel: str, tree: ast.Module):
        self.rel = rel
        self.tree = tree
        self.classes: dict = {}
        self.functions: dict = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self.classes[node.name] = node
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions[node.name] = node

    def find(self, cls, func):
        """Return (node, owning ClassDef or None, problem)."""
        if cls is None:
            node = self.functions.get(func)
            return (node, None, None) if node else (None, None, f"function '{func}' not found at module level in {self.rel}")
        cnode = self.classes.get(cls)
        if cnode is None:
            return None, None, f"class '{cls}' not found in {self.rel}"
        for item in cnode.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == func:
                return item, cnode, None
        return None, cnode, f"'{func}' is not defined in the body of class '{cls}' in {self.rel} (inherited tests do not count)"


def _name_of(node) -> str:
    """Dotted name of a Name/Attribute chain, '' otherwise."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_skip_decorator(dec) -> bool:
    target = dec.func if isinstance(dec, ast.Call) else dec
    name = _name_of(target)
    last = name.rsplit(".", 1)[-1]
    if last in SKIP_DECORATORS:
        return True
    return ".mark.skip" in "." + name or name.endswith("mark.skipif") or name.endswith("mark.xfail")


def skip_reasons(func, cls) -> list:
    reasons = []
    for dec in func.decorator_list:
        if _is_skip_decorator(dec):
            reasons.append(f"decorated with @{_name_of(dec.func if isinstance(dec, ast.Call) else dec)}")
    if cls is not None:
        for dec in cls.decorator_list:
            if _is_skip_decorator(dec):
                reasons.append(f"class {cls.name} is decorated with @{_name_of(dec.func if isinstance(dec, ast.Call) else dec)}")
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            name = _name_of(node.func)
            if name.rsplit(".", 1)[-1] in SKIP_CALLS and (name.startswith("self.") or name.startswith("pytest.") or name.startswith("unittest.") or name in SKIP_CALLS):
                reasons.append(f"calls {name}()")
        elif isinstance(node, ast.Raise) and node.exc is not None:
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if _name_of(target).rsplit(".", 1)[-1] in ("SkipTest", "Skipped"):
                reasons.append("raises SkipTest")
    return reasons


def _is_literal(node) -> bool:
    return isinstance(node, ast.Constant)


def _is_assertion_call(call: ast.Call) -> bool:
    """An assert*/assert_* call whose arguments are not all literals.

    ``assertTrue(True)`` and ``assertEqual(1, 1)`` cannot fail on a behaviour change.
    ``self.fail()`` counts: it is an explicit failure path.
    """
    last = _name_of(call.func).rsplit(".", 1)[-1]
    if last == "fail":
        return True
    if not (last.startswith("assert") or last.startswith("assert_")):
        return False
    if call.args and all(_is_literal(a) for a in call.args):
        return False
    return True


def has_real_assertion(func, cls, _seen=None) -> bool:
    """True when the body (or a same-class helper it calls via self) can fail."""
    seen = _seen if _seen is not None else set()
    if id(func) in seen:
        return False
    seen.add(id(func))
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            if not _is_literal(node.test):
                return True
        elif isinstance(node, ast.Call):
            if _is_assertion_call(node):
                return True
            fname = node.func
            if cls is not None and isinstance(fname, ast.Attribute) and isinstance(fname.value, ast.Name) and fname.value.id == "self":
                for item in cls.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == fname.attr and item is not func:
                        if has_real_assertion(item, cls, seen):
                            return True
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for it in node.items:
                if isinstance(it.context_expr, ast.Call) and _name_of(it.context_expr.func).rsplit(".", 1)[-1] in (
                    "assertRaises", "assertRaisesRegex", "assertWarns", "assertWarnsRegex", "assertLogs", "raises", "warns"
                ):
                    return True
    return False


def docstring_lines(node) -> list:
    doc = ast.get_docstring(node, clean=False)
    if not doc:
        return []
    return doc.split("\n")


def parse_test_file(path: Path, rel: str):
    try:
        src = path.read_text(encoding="utf-8")
        return TestFile(rel, ast.parse(src, filename=rel)), None
    except SyntaxError as exc:
        return None, f"{rel} does not parse as Python: {exc.msg} (line {exc.lineno})"
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{rel} cannot be read: {exc}"


def scan_spec_lines(layout) -> tuple[list, list]:
    """Find every 'Spec:' line in function docstrings under the repo.

    Returns (entries, findings); entry = (rel, qualname, line, id, ref).
    """
    entries, findings = [], []
    root = layout.root
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SCAN_PRUNE and not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            path = Path(dirpath) / fn
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "Spec:" not in src:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                tree = ast.parse(src, filename=rel)
            except SyntaxError as exc:
                findings.append(Finding(rel, exc.lineno or 1, "test-syntax", f"{rel} contains 'Spec:' but does not parse as Python: {exc.msg}"))
                continue

            def visit(node, prefix, in_func):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.ClassDef):
                        owner = child
                        doc = docstring_lines(child)
                        for off, text in enumerate(doc):
                            if text.strip().startswith("Spec:"):
                                findings.append(Finding(rel, child.lineno, "spec-line-misplaced",
                                                        f"'Spec:' line in the docstring of class {child.name}; each test needs its own 'Spec:' line"))
                        visit(owner, prefix + child.name + ".", in_func)
                    elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qual = prefix + child.name
                        body0 = child.body[0] if child.body else None
                        base = body0.lineno if (body0 is not None and isinstance(body0, ast.Expr) and isinstance(getattr(body0, "value", None), ast.Constant) and isinstance(body0.value.value, str)) else child.lineno
                        for off, text in enumerate(docstring_lines(child)):
                            if not text.strip().startswith("Spec:"):
                                continue
                            m = SPEC_LINE_RE.match(text)
                            if not m:
                                findings.append(Finding(rel, base + off, "spec-line-format",
                                                        "docstring line must be exactly 'Spec: <ID> (<path>#<anchor>)'"))
                                continue
                            entries.append((rel, qual, base + off, m.group(1), m.group(2)))
                        visit(child, qual + ".", True)
                    else:
                        visit(child, prefix, in_func)

            # module docstring
            for text in docstring_lines(tree):
                if text.strip().startswith("Spec:"):
                    findings.append(Finding(rel, 1, "spec-line-misplaced", "'Spec:' line in a module docstring; put it in the test's own docstring"))
            visit(tree, "", False)
    return entries, findings


# ---------------------------------------------------------------------------
# test-traceability.md
# ---------------------------------------------------------------------------

def parse_traceability(layout, findings):
    path = layout.spec_path / "test-traceability.md"
    rel = layout.rel(path)
    if not path.is_file():
        findings.append(Finding(rel, 1, "traceability-missing", "test-traceability.md is missing"))
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    rows: dict = {}
    retired: set = set()
    section = None
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if section == "cases" and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5 or cells[0].lower() == "case" or re.fullmatch(r"[\s:-]+", cells[0]):
                if len(cells) != 5 and not re.fullmatch(r"[\s:|-]+", line):
                    findings.append(Finding(rel, i, "traceability-row", "row must have 5 cells: Case | Clause | Test kind | Test | Evidence"))
                continue
            m = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", cells[0])
            if not m:
                findings.append(Finding(rel, i, "traceability-row", "first cell must be a link '[ID](clauses/file.md#anchor)'"))
                continue
            tm = re.match(r"^\[`([^`]+)`\]\(([^)]+)\)$", cells[3])
            cm = re.fullmatch(r"`([^`]+)`", cells[1])
            if m.group(1) in rows:
                findings.append(Finding(rel, i, "traceability-duplicate", f"case {m.group(1)} has two rows"))
            rows[m.group(1)] = dict(line=i, href=m.group(2), clause=cm.group(1) if cm else cells[1], kind=cells[2],
                                    label=tm.group(1) if tm else None, thref=tm.group(2) if tm else None, evidence=cells[4])
        elif section == "retired ids":
            for tok in re.findall(r"[A-Z][A-Z0-9]*-\d{2}-A\d+\.\d+[A-Z]", line):
                retired.add(tok)
    return rows, retired, rel


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def check(layout, ns):
    files, findings = discover_clauses(layout)
    clauses = [parse_clause(layout, p) for p in files]
    cases = [c for cl in clauses for c in cl.cases]
    by_id: dict = {}
    for c in cases:
        by_id.setdefault(c.id, c)

    spec_prefix = layout.spec_dir.rstrip("/") + "/clauses/"
    parsed: dict = {}  # rel -> (TestFile|None)

    def get_file(rel: str):
        if rel not in parsed:
            p = layout.root / rel
            if not p.is_file():
                parsed[rel] = (None, f"test file '{rel}' does not exist")
            else:
                parsed[rel] = parse_test_file(p, rel)
        return parsed[rel]

    covered: dict = {}  # (rel, qual) -> set(case ids that name it)
    for case in cases:
        cl = case.clause
        if case.selector is None:
            findings.append(Finding(cl.rel, case.line, "case-unlinkable",
                                    f"case {case.id} has no valid Test selector (see check_spec_cases.py)"))
            continue
        sel = case.selector
        covered.setdefault((sel.path, sel.qualname), set()).add(case.id)
        tfile, err = get_file(sel.path)
        tline = case.fields["Test"].line
        if tfile is None:
            findings.append(Finding(cl.rel, tline, "test-file", f"case {case.id}: {err}"))
            continue
        node, cnode, problem = tfile.find(sel.cls, sel.func)
        if node is None:
            findings.append(Finding(cl.rel, tline, "test-missing", f"case {case.id}: {problem}"))
            continue
        for why in skip_reasons(node, cnode):
            findings.append(Finding(cl.rel, tline, "test-skipped", f"case {case.id}: {sel.qualname} is skipped ({why}); a skipped test is not coverage"))
        if not has_real_assertion(node, cnode):
            findings.append(Finding(cl.rel, tline, "test-scaffold",
                                    f"case {case.id}: {sel.qualname} has no assertion that can fail (empty scaffold); write a characterization test or list the rule as uncovered"))
        # test -> spec docstring
        doc = docstring_lines(node)
        want_ref = f"{spec_prefix}{cl.name}#{case.anchor}"
        mine = [ln for ln in doc if SPEC_LINE_RE.match(ln) and SPEC_LINE_RE.match(ln).group(1) == case.id]
        if not mine:
            findings.append(Finding(sel.path, node.lineno, "spec-line-missing",
                                    f"{sel.qualname} must have the docstring line 'Spec: {case.id} ({want_ref})'"))
        else:
            for ln in mine:
                ref = SPEC_LINE_RE.match(ln).group(2)
                if ref != want_ref:
                    findings.append(Finding(sel.path, node.lineno, "spec-line-ref",
                                            f"'Spec: {case.id}' points to '{ref}', expected '{want_ref}'"))
            if len(mine) > 1:
                findings.append(Finding(sel.path, node.lineno, "spec-line-duplicate", f"'Spec: {case.id}' appears {len(mine)} times in {sel.qualname}"))
        has_char = any(ln.strip() == CHARACTERIZATION_LINE for ln in doc)
        if case.kind == "characterization" and not has_char:
            findings.append(Finding(sel.path, node.lineno, "characterization-line",
                                    f"{sel.qualname} is a characterization test for {case.id}; docstring needs the line '{CHARACTERIZATION_LINE}'"))

    # mapped-only tests must not claim to be characterization
    kinds: dict = {}
    for case in cases:
        if case.selector is not None:
            kinds.setdefault((case.selector.path, case.selector.qualname), set()).add(case.kind)
    for (rel, qual), ks in kinds.items():
        tfile, _ = parsed.get(rel, (None, None))
        if tfile is None or "characterization" in ks:
            continue
        cls, _, func = qual.rpartition(".")
        node, _, _ = tfile.find(cls or None, func)
        if node is not None and any(ln.strip() == CHARACTERIZATION_LINE for ln in docstring_lines(node)):
            findings.append(Finding(rel, node.lineno, "characterization-line",
                                    f"{qual} carries the Characterization line but every case that maps it is 'mapped'"))

    # every Spec: line in the repo must be backed by a case that names that test
    entries, scan_findings = scan_spec_lines(layout)
    findings.extend(scan_findings)
    for rel, qual, ln, cid, ref in entries:
        case = by_id.get(cid)
        if case is None:
            findings.append(Finding(rel, ln, "spec-line-orphan", f"'Spec: {cid}' names no case in {layout.spec_dir}/clauses"))
            continue
        sel = case.selector
        if sel is None or (sel.path, sel.qualname) != (rel, qual):
            where = f"{sel.path}::{sel.qualname}" if sel else "no valid test"
            findings.append(Finding(rel, ln, "spec-line-mismatch",
                                    f"'Spec: {cid}' is on {qual}, but case {cid} names {where}"))

    # test-traceability.md
    trace = parse_traceability(layout, findings)
    if trace is not None:
        rows, retired, trel = trace
        for cid, case in by_id.items():
            if cid in retired:
                findings.append(Finding(case.clause.rel, case.line, "retired-id-reused", f"case ID {cid} is listed under Retired IDs and must not be reused"))
            row = rows.get(cid)
            if row is None:
                findings.append(Finding(case.clause.rel, case.line, "traceability-missing-row", f"case {cid} has no row in test-traceability.md"))
                continue
            want_href = f"clauses/{case.clause.name}#{case.anchor}"
            if row["href"] != want_href:
                findings.append(Finding(trel, row["line"], "traceability-link", f"case link must be '{want_href}', found '{row['href']}'"))
            if case.clause.stable_id and row["clause"] != case.clause.stable_id:
                findings.append(Finding(trel, row["line"], "traceability-clause", f"clause cell must be `{case.clause.stable_id}`, found {row['clause']}"))
            if case.kind and row["kind"] != case.kind:
                findings.append(Finding(trel, row["line"], "traceability-kind", f"test kind must be '{case.kind}', found '{row['kind']}'"))
            if case.selector is not None:
                if row["label"] != selector_label(case.selector):
                    findings.append(Finding(trel, row["line"], "traceability-test", f"test label must be '{selector_label(case.selector)}', found '{row['label']}'"))
                if row["thref"] is not None:
                    target = posixpath.normpath(posixpath.join(layout.spec_dir, row["thref"]))
                    if target != case.selector.path:
                        findings.append(Finding(trel, row["line"], "traceability-test", f"test link resolves to '{target}' but the case names '{case.selector.path}'"))
            ev = case.fields.get("Evidence")
            if ev is not None and evidence_is_unverified(ev.text) != evidence_is_unverified(row["evidence"]):
                findings.append(Finding(trel, row["line"], "traceability-evidence", "Evidence cell and the case's Evidence field disagree (UNVERIFIED vs receipt)"))
        for cid, row in rows.items():
            if cid not in by_id:
                findings.append(Finding(trel, row["line"], "traceability-orphan-row", f"row names {cid}, which is not a case in {layout.spec_dir}/clauses"))

    return findings, f"{len(cases)} case(s), {len(parsed)} test file(s) read, {len(entries)} Spec line(s)"


def main(argv=None) -> int:
    return run_cli(
        "check_spec_test_links.py",
        "Check that every spec case and its Python test link to each other, and that the test is real.",
        "spec-links",
        check,
        argv,
    )


if __name__ == "__main__":
    sys.exit(main())
