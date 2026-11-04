"""Shared parsing, reporting and CLI plumbing for the spec checkers.

Standard library only, Python >= 3.10, no frappe import. The whole ``tools/``
directory is the copy-in unit for other repos.

The rules checked here are the ones in ``docs/spec/conventions.md`` and
``docs/spec/acceptance-cases.md``. The checkers read files; they never run
tests and never judge whether assertions match an Expected result.
"""
from __future__ import annotations

import argparse
import dataclasses
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

EXIT_OK, EXIT_FINDINGS, EXIT_USAGE = 0, 1, 2

CASE_ID_RE = re.compile(r"^([A-Z][A-Z0-9]*)-(\d{2})-A(\d+)\.(\d+)([A-Z])$")
AREA_ID_RE = re.compile(r"^([A-Z][A-Z0-9]*)-(\d{2})-A(\d+)$")
STABLE_ID_RE = re.compile(r"^SPEC-([A-Z][A-Z0-9]*)-(\d{2})$")
CLAUSE_FILE_RE = re.compile(r"^(\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
ANCHOR_RE = re.compile(r'^<a id="([^"]+)"></a>$')
FIELD_LINE_RE = re.compile(r"^- ([A-Z][A-Za-z ]*?):(?: (.*))?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CITATION_RE = re.compile(r"^[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*$")
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^<>\n]*>")
CHARACTERIZATION_LINE = "Characterization: pins current behaviour, not endorsed."

FIELDS = (
    "Precondition",
    "Action",
    "Expected result",
    "Test",
    "Environment",
    "Known gaps",
    "Evidence",
)
PERFORMANCE_SECTION = 8  # "Static security and performance observations"
SECTIONS = (
    "Purpose",
    "Boundaries",
    "Behaviour rules",
    "Data and permissions",
    "Errors and edge behaviour",
    "Configuration",
    "Scheduled jobs, hooks and patches",
    "Static security and performance observations",
    "Known gaps / open questions",
    "Uncovered behaviour",
    "Acceptance cases",
)
CASES_SECTION = len(SECTIONS)  # section 11


class UsageError(Exception):
    """Bad invocation or unreadable spec tree (exit code 2)."""


@dataclasses.dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str


@dataclasses.dataclass(frozen=True)
class Layout:
    root: Path
    spec_dir: str  # posix, relative to root

    @property
    def spec_path(self) -> Path:
        return self.root / self.spec_dir

    @property
    def clauses_path(self) -> Path:
        return self.spec_path / "clauses"

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()


def make_layout(root: str, spec_dir: str) -> Layout:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise UsageError(f"--root is not a directory: {root}")
    norm = posixpath.normpath(spec_dir.replace("\\", "/"))
    if norm.startswith("/") or norm == ".." or norm.startswith("../"):
        raise UsageError(f"--spec-dir must be a relative path inside --root: {spec_dir}")
    layout = Layout(root_path, norm)
    if not layout.clauses_path.is_dir():
        raise UsageError(f"clauses directory not found: {layout.clauses_path}")
    return layout


# ---------------------------------------------------------------------------
# Selectors, evidence, citations
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Selector:
    path: str
    cls: Optional[str]
    func: str

    @property
    def qualname(self) -> str:
        return f"{self.cls}.{self.func}" if self.cls else self.func


_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TEST_FIELD_RE = re.compile(r"^(mapped|characterization): `([^`]*)`$")


def parse_test_field(text: str) -> tuple[str, Selector]:
    """Parse the ``Test`` field. Raises ValueError with a reason."""
    m = _TEST_FIELD_RE.match(text.strip())
    if not m:
        raise ValueError(
            "Test must be '<mapped|characterization>: `path.py::Class::test_name`' "
            "(or `path.py::test_function`)"
        )
    kind, raw = m.groups()
    parts = raw.split("::")
    path = parts[0]
    if len(parts) not in (2, 3):
        raise ValueError(f"selector '{raw}' must be path.py::Class::method or path.py::function")
    if re.search(r"[\s*?\[\]]", raw):
        raise ValueError(f"selector '{raw}' must not contain wildcards or whitespace")
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path) or ".." in path.split("/"):
        raise ValueError(f"test path '{path}' must be relative to the repo root with no '..'")
    if not path.endswith(".py"):
        raise ValueError(
            f"test path '{path}' is not a Python file; only Python tests are supported by this checker"
        )
    for ident in parts[1:]:
        if not _IDENT_RE.match(ident):
            raise ValueError(f"'{ident}' in selector '{raw}' is not a Python identifier")
    func = parts[-1]
    if not func.startswith("test"):
        raise ValueError(f"test function '{func}' must start with 'test'")
    return kind, Selector(path, parts[1] if len(parts) == 3 else None, func)


def selector_label(sel: Selector) -> str:
    return sel.qualname


_RECEIPT_RE = re.compile(
    r"^(?P<kind>local|ci); (?P<cmd>.+); exit (?P<exit>\d+); "
    r"(?P<p>\d+) passed, (?P<f>\d+) failed, (?P<s>\d+) skipped; "
    r"commit (?P<sha>[0-9a-f]{40}); env (?P<env>.+?)(?:; run (?P<run>\S+))?$"
)


def evidence_error(text: str) -> Optional[str]:
    """Return a reason when ``text`` is not a valid Evidence value, else None."""
    t = text.strip()
    if t == "UNVERIFIED":
        return None
    if t.startswith("UNVERIFIED:"):
        return None if t[len("UNVERIFIED:"):].strip() else "'UNVERIFIED:' needs a reason"
    m = _RECEIPT_RE.match(t)
    if not m:
        return (
            "Evidence must be UNVERIFIED, 'UNVERIFIED: <reason>', or a receipt "
            "'local|ci; <command>; exit N; P passed, F failed, S skipped; commit <40 hex>; env <...>[; run <id>]'"
        )
    if m["kind"] == "ci" and not m["run"]:
        return "a ci receipt needs '; run <CI run id>'"
    if m["kind"] == "local" and m["run"]:
        return "a local receipt must not carry '; run <id>'"
    if m["exit"] == "0" and (int(m["f"]) != 0 or int(m["p"]) < 1):
        return "exit 0 needs 0 failed and at least 1 passed"
    if m["exit"] != "0":
        return "a receipt with a non-zero exit is not evidence for a case"
    return None


def evidence_is_unverified(text: str) -> bool:
    return text.strip().startswith("UNVERIFIED")


def expected_result_error(text: str) -> Optional[str]:
    spans = re.findall(r"`([^`]+)`", text)
    if not spans or not CITATION_RE.match(spans[-1]):
        return "Expected result must end with a citation like `path/to/file.py:12` or `path.py:12-18`"
    cite = spans[-1]
    path, _, lines = cite.partition(":")
    if path.startswith("/") or ".." in path.split("/"):
        return f"citation path '{path}' must be relative to the repo root"
    for rng in lines.split(","):
        lo, _, hi = rng.partition("-")
        if int(lo) < 1 or (hi and int(hi) < int(lo)):
            return f"citation line range '{rng}' is not valid"
    tail = text[text.rindex("`" + cite + "`") + len(cite) + 2:]
    if not re.fullmatch(r"[\s).,;]*", tail):
        return "Expected result must END with the citation (only closing punctuation after it)"
    return None


def has_placeholder(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text))


def anchor_for(case_id: str) -> str:
    return case_id.lower().replace(".", "-")


# ---------------------------------------------------------------------------
# Markdown clause model
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Field:
    name: str
    text: str
    line: int


@dataclasses.dataclass
class IndexRow:
    line: int
    case_id: str
    href: str
    label: str
    test_href: str


@dataclasses.dataclass
class Case:
    id: str
    line: int
    title: str
    fields: dict  # name -> Field (first occurrence)
    kind: Optional[str] = None
    selector: Optional[Selector] = None
    clause: "Clause" = None  # type: ignore[assignment]

    @property
    def anchor(self) -> str:
        return anchor_for(self.id)


@dataclasses.dataclass
class Area:
    id: str
    line: int
    cases: list = dataclasses.field(default_factory=list)
    table_lines: list = dataclasses.field(default_factory=list)  # (lineno, text)


@dataclasses.dataclass
class Clause:
    path: Path
    rel: str
    name: str
    findings: list = dataclasses.field(default_factory=list)
    stable_id: Optional[str] = None
    code: Optional[str] = None
    nn: Optional[str] = None
    described_sha: Optional[str] = None
    described_branch: Optional[str] = None
    also_sha: Optional[str] = None
    sha_lines: list = dataclasses.field(default_factory=list)  # (line, sha)
    areas: list = dataclasses.field(default_factory=list)
    cases: list = dataclasses.field(default_factory=list)
    rows: dict = dataclasses.field(default_factory=dict)  # area id -> [IndexRow]
    cases_none: bool = False
    sec8_line: Optional[int] = None  # line of the '## 8.' heading, for the opt-in Performance rule
    sec8_body: list = dataclasses.field(default_factory=list)  # (line, text) of section 8, masked


def mask_lines(raw: list) -> list:
    """Return lines with fenced code and HTML comments replaced by None."""
    out: list = []
    fence = False
    comment = False
    for line in raw:
        s = line.strip()
        if comment:
            out.append(None)
            if "-->" in line:
                comment = False
            continue
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
            out.append(None)
            continue
        if fence:
            out.append(None)
            continue
        if "<!--" in line:
            out.append(None)
            if "-->" not in line.split("<!--", 1)[1]:
                comment = True
            continue
        out.append(line.rstrip())
    return out


# A Performance item inside section 8: a bullet "- Performance: ...", "- Performance (1): ...",
# "- Performance, read endpoint: ...", or a heading "### Performance" followed by text.
PERF_BULLET_RE = re.compile(r"^[-*]\s+\**Performance\b[^:\n]{0,60}:\**\s*(.*)$", re.IGNORECASE)
PERF_HEADING_RE = re.compile(r"^#{3,6}\s+\**Performance\b", re.IGNORECASE)
NO_FINDINGS_RE = re.compile(r"no performance findings", re.IGNORECASE)
CHECKED_RE = re.compile(r"checked\s*:", re.IGNORECASE)


def performance_findings(clause: Clause) -> list:
    """Findings for the opt-in rule: section 8 must hold a non-empty Performance item.

    Rules: ``performance-missing`` (no item), ``performance-empty`` (item with no text),
    ``performance-unchecked`` ("No performance findings" with no ``Checked:`` list).
    Shape of the item: docs/spec/conventions.md section 5.1.
    """
    if clause.sec8_line is None:
        return []  # a missing section 8 is already reported by the section rules
    out: list = []
    items = 0
    body = clause.sec8_body
    for pos, (ln, text) in enumerate(body):
        st = text.strip()
        m = PERF_BULLET_RE.match(st)
        if m:
            items += 1
            txt = m.group(1).strip()
            if not txt:
                out.append(Finding(clause.rel, ln, "performance-empty", "Performance item has no text after the colon"))
            elif NO_FINDINGS_RE.search(txt) and not CHECKED_RE.search(txt):
                out.append(Finding(clause.rel, ln, "performance-unchecked",
                                   "'No performance findings' must be followed by 'Checked:' and the list of what was checked"))
        elif PERF_HEADING_RE.match(st):
            items += 1
            rest = []
            for _, t in body[pos + 1:]:
                if t.strip().startswith("#"):
                    break
                if t.strip():
                    rest.append(t.strip())
            if not rest:
                out.append(Finding(clause.rel, ln, "performance-empty", "Performance heading has no text under it"))
            elif any(NO_FINDINGS_RE.search(t) for t in rest) and not any(CHECKED_RE.search(t) for t in rest):
                out.append(Finding(clause.rel, ln, "performance-unchecked",
                                   "'No performance findings' must be followed by 'Checked:' and the list of what was checked"))
    if items == 0:
        out.append(Finding(clause.rel, clause.sec8_line, "performance-missing",
                           "section 8 has no Performance item; add findings or 'No performance findings. Checked: ...'"))
    return out


def _backtick(text: str, key: str) -> Optional[str]:
    m = re.search(rf"\b{key} `([^`]*)`", text)
    return m.group(1) if m else None


_ROW_RE = re.compile(
    r"^\|\s*\[(?P<id>[^\]]+)\]\((?P<href>[^)]+)\)\s*\|(?P<mid>.*)\|\s*"
    r"\[`(?P<label>[^`]+)`\]\((?P<thref>[^)]+)\)\s*\|\s*$"
)
_TABLE_HEADER = ["case", "what the assertions check", "test"]


def parse_clause(layout: Layout, path: Path) -> Clause:
    rel = layout.rel(path)
    clause = Clause(path=path, rel=rel, name=path.name)

    def add(line: int, rule: str, msg: str) -> None:
        clause.findings.append(Finding(rel, line, rule, msg))

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        add(1, "unreadable", f"cannot read clause file: {exc}")
        return clause
    raw = [ln.rstrip("\r") for ln in text.split("\n")]
    lines = mask_lines(raw)

    m_file = CLAUSE_FILE_RE.match(path.name)
    if not m_file:
        add(1, "clause-filename", "clause file name must be NN-kebab-name.md (NN = two digits)")

    # --- title and header region -------------------------------------------------
    title_idx = next((i for i, s in enumerate(lines) if s is not None and s.startswith("# ")), None)
    first_sec = next((i for i, s in enumerate(lines) if s is not None and s.startswith("## ")), len(lines))
    if title_idx is None:
        add(1, "title-missing", "clause must start with '# SPEC-<CODE>-NN: <title>'")
    header_start = (title_idx + 1) if title_idx is not None else 0

    header: dict = {}
    for i in range(header_start, first_sec):
        s = lines[i]
        if s is None or not s.startswith("- "):
            continue
        key, sep, val = s[2:].partition(":")
        if not sep:
            continue
        key = key.strip()
        if key in header:
            add(i + 1, "header-duplicate", f"header line '{key}' appears twice")
            continue
        header[key] = (i + 1, val.strip())
        if has_placeholder(s):
            add(i + 1, "placeholder", f"header line '{key}' still contains a template placeholder")

    # Stable ID
    sid_entry = header.get("Stable ID")
    if not sid_entry:
        add(first_sec + 1 if first_sec < len(lines) else 1, "header-stable-id", "header line 'Stable ID' is missing")
    else:
        ln, val = sid_entry
        m = re.fullmatch(r"`([^`]+)`", val)
        sid = m.group(1) if m else ""
        sm = STABLE_ID_RE.match(sid)
        if not sm:
            add(ln, "header-stable-id", "Stable ID must be `SPEC-<CODE>-NN`")
        else:
            clause.stable_id, clause.code, clause.nn = sid, sm.group(1), sm.group(2)
            if m_file and m_file.group(1) != clause.nn:
                add(ln, "header-stable-id", f"Stable ID number {clause.nn} does not match file name {path.name}")
            if title_idx is not None:
                tm = re.match(r"^# (\S+?):", lines[title_idx] or "")
                if not tm or tm.group(1) != sid:
                    add(title_idx + 1, "title-mismatch", f"title must start with '# {sid}: '")
                if has_placeholder(lines[title_idx] or ""):
                    add(title_idx + 1, "placeholder", "title still contains a template placeholder")
            want = f'<a id="{sid.lower()}"></a>'
            if not any(lines[i] is not None and lines[i].strip() == want for i in range(header_start, first_sec)):
                add(title_idx + 1 if title_idx is not None else 1, "clause-anchor",
                    f"clause anchor {want} is missing before the first section")

    # Described at
    d_entry = header.get("Described at")
    if not d_entry:
        add(1, "header-described-at", "header line 'Described at' (repo, branch, commit) is missing")
    else:
        ln, val = d_entry
        repo = _backtick(val, "repo")
        branch = _backtick(val, "branch")
        commit = _backtick(val, "commit")
        date = _backtick(val, "committer date")
        if not repo or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            add(ln, "header-repo", "Described at needs repo `<owner/repo>`")
        if not branch:
            add(ln, "header-branch", "Described at needs branch `<branch>`")
        elif branch == "HEAD":
            add(ln, "header-branch", "branch must be a real branch name, not HEAD")
        if not commit or not SHA_RE.match(commit):
            add(ln, "header-commit", "Described at needs commit `<40 lowercase hex>` (full SHA, never a branch name or HEAD)")
        else:
            clause.described_sha = commit
            clause.sha_lines.append((ln, commit))
        clause.described_branch = branch
        if not date or not re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4}", date):
            add(ln, "header-date", "Described at needs (committer date `YYYY-MM-DD HH:MM:SS +ZZZZ`)")

    # Also read at (optional)
    a_entry = header.get("Also read at")
    if a_entry:
        ln, val = a_entry
        branch = _backtick(val, "branch")
        commit = _backtick(val, "commit")
        if not branch or branch == "HEAD":
            add(ln, "header-also-branch", "Also read at needs branch `<branch>`")
        if not commit or not SHA_RE.match(commit):
            add(ln, "header-also-commit", "Also read at needs commit `<40 lowercase hex>`")
        else:
            clause.also_sha = commit
            clause.sha_lines.append((ln, commit))
        rest = val.split("commit", 1)[-1]
        rest = rest.split("`", 2)[-1] if "`" in rest else ""
        if not re.sub(r"^[\s;,.]+", "", rest):
            add(ln, "header-also-delta", "Also read at must say whether the files are the same or what differs")

    # Author / reviewer
    r_entry = header.get("Author")
    if not r_entry:
        add(1, "header-author", "header line 'Author: <role>. Reviewer: <a different role>.' is missing")
    else:
        ln, val = r_entry
        m = re.match(r"^(.+?)\. Reviewer: (.+?)\.?$", val)
        if not m:
            add(ln, "header-author", "expected 'Author: <role>. Reviewer: <a different role>.'")
        else:
            author, reviewer = m.group(1).strip(), m.group(2).strip()
            if has_placeholder(val):
                pass  # reported above
            key = lambda s: re.sub(r"\s+", " ", s.split(",")[0]).strip().lower()  # noqa: E731
            if key(author) == key(reviewer):
                add(ln, "header-reviewer", "Author and Reviewer must be different people or agents")

    s_entry = header.get("Status")
    if not s_entry:
        add(1, "header-status", "header line 'Status: DRAFT | IN REVIEW | ACCEPTED' is missing")
    elif s_entry[1] not in ("DRAFT", "IN REVIEW", "ACCEPTED"):
        add(s_entry[0], "header-status", "Status must be DRAFT, IN REVIEW or ACCEPTED")

    # --- sections ---------------------------------------------------------------
    sec_heads: list = []  # (idx, number, title)
    for i in range(first_sec, len(lines)):
        s = lines[i]
        if s is None or not s.startswith("## "):
            continue
        m = re.match(r"^## (\d+)\. (.+?)\s*$", s)
        if not m:
            add(i + 1, "section-heading", "section heading must be '## N. Title'")
            continue
        sec_heads.append((i, int(m.group(1)), m.group(2)))
    expected = list(enumerate(SECTIONS, start=1))
    got = [(n, t) for _, n, t in sec_heads]
    if [(n, t.lower()) for n, t in got] != [(n, t.lower()) for n, t in expected]:
        have = {n for n, _ in got}
        for n, t in expected:
            if n not in have:
                add(first_sec + 1 if first_sec < len(lines) else 1, "section-missing", f"section '## {n}. {t}' is missing")
        for (i, n, t) in sec_heads:
            if 1 <= n <= len(SECTIONS) and SECTIONS[n - 1].lower() != t.lower():
                add(i + 1, "section-title", f"section {n} must be titled '{SECTIONS[n - 1]}'")
            elif n < 1 or n > len(SECTIONS):
                add(i + 1, "section-unknown", f"unexpected section number {n}")
        nums = [n for _, n, _ in sec_heads]
        if nums != sorted(nums):
            add(sec_heads[0][0] + 1, "section-order", "sections must appear in numeric order 1..11")
    for pos, (i, n, t) in enumerate(sec_heads):
        end = sec_heads[pos + 1][0] if pos + 1 < len(sec_heads) else len(lines)
        body = [s for s in lines[i + 1:end] if s is not None and s.strip() and not ANCHOR_RE.match(s.strip())]
        if not body:
            add(i + 1, "section-empty", f"section {n} is empty; write 'None.' and why")
        if n == PERFORMANCE_SECTION:
            clause.sec8_line = i + 1
            clause.sec8_body = [(j + 1, lines[j]) for j in range(i + 1, end) if lines[j] is not None]

    cases_head = next((h for h in sec_heads if h[1] == CASES_SECTION), None)
    if cases_head is None:
        return clause
    start = cases_head[0] + 1
    pos = sec_heads.index(cases_head)
    end = sec_heads[pos + 1][0] if pos + 1 < len(sec_heads) else len(lines)
    _parse_cases(clause, raw, lines, start, end, add)
    return clause


def _parse_cases(clause: Clause, raw: list, lines: list, start: int, end: int, add: Callable) -> None:
    area: Optional[Area] = None
    case: Optional[Case] = None
    block: list = []  # (lineno, text) of the current case block

    def anchor_above(idx: int, want: str, what: str) -> None:
        prev = raw[idx - 1].strip() if idx > 0 else ""
        m = ANCHOR_RE.match(prev)
        if not m:
            add(idx + 1, "anchor-missing", f'{what} needs the line <a id="{want}"></a> directly above it')
        elif m.group(1) != want:
            add(idx, "anchor-mismatch", f"anchor '{m.group(1)}' must be '{want}'")

    def finish_case() -> None:
        nonlocal case, block
        if case is None:
            return
        names: list = []
        for ln, s in block:
            fm = FIELD_LINE_RE.match(s)
            if not fm:
                add(ln, "loose-text", f"case {case.id}: only the seven fields are allowed in a case block, found: {s.strip()[:60]}")
                continue
            name, val = fm.group(1), (fm.group(2) or "").strip()
            names.append(name)
            if name not in FIELDS:
                add(ln, "field-unknown", f"case {case.id}: '{name}' is not one of the seven fields")
                continue
            if name in case.fields:
                add(ln, "field-duplicate", f"case {case.id}: field '{name}' appears twice")
                continue
            case.fields[name] = Field(name, val, ln)
            if not val:
                add(ln, "field-empty", f"case {case.id}: field '{name}' is empty")
            elif has_placeholder(val):
                add(ln, "placeholder", f"case {case.id}: field '{name}' still contains a template placeholder")
        missing = [f for f in FIELDS if f not in case.fields]
        for f in missing:
            add(case.line, "field-missing", f"case {case.id}: field '{f}' is missing")
        if not missing:
            order = [n for n in names if n in FIELDS]
            if order != list(FIELDS):
                add(case.line, "field-order", f"case {case.id}: fields must be exactly {', '.join(FIELDS)} in this order")
        _check_case_fields(clause, case, add)
        case, block = None, []

    def finish_area() -> None:
        nonlocal area
        if area is not None:
            _check_area_table(clause, area, add)
        area = None

    idx = start
    while idx < end:
        s = lines[idx]
        idx_here = idx
        idx += 1
        if s is None:
            continue
        st = s.strip()
        am = ANCHOR_RE.match(st)
        if am:
            finish_case()
            nxt = raw[idx_here + 1].strip() if idx_here + 1 < len(raw) else ""
            if not (nxt.startswith("### ") or nxt.startswith("#### ")):
                add(idx_here + 1, "anchor-orphan", f"anchor '{am.group(1)}' is not directly followed by an area or case heading")
            continue
        if s.startswith("#"):
            finish_case()
            ca = re.match(r"^#### (\S+): (.+)$", s)
            ar = re.match(r"^### (\S+): (.+)$", s)
            if ar:
                finish_area()
                aid = ar.group(1)
                am2 = AREA_ID_RE.match(aid)
                if not am2:
                    add(idx_here + 1, "area-id", f"area ID '{aid}' must look like CORE-01-A1")
                    area = Area(aid, idx_here + 1)
                else:
                    if clause.code and (am2.group(1), am2.group(2)) != (clause.code, clause.nn):
                        add(idx_here + 1, "area-id", f"area {aid} does not belong to clause {clause.stable_id}")
                    anchor_above(idx_here, aid.lower(), f"area {aid}")
                    area = Area(aid, idx_here + 1)
                clause.areas.append(area)
                if has_placeholder(s):
                    add(idx_here + 1, "placeholder", f"area heading {aid} still contains a template placeholder")
            elif ca:
                cid = ca.group(1)
                cm = CASE_ID_RE.match(cid)
                case = Case(cid, idx_here + 1, ca.group(2).strip(), {}, clause=clause)
                block = []
                if not cm:
                    add(idx_here + 1, "case-id", f"case ID '{cid}' must look like CORE-01-A1.1A")
                else:
                    if clause.code and (cm.group(1), cm.group(2)) != (clause.code, clause.nn):
                        add(idx_here + 1, "case-id", f"case {cid} does not belong to clause {clause.stable_id}")
                    anchor_above(idx_here, anchor_for(cid), f"case {cid}")
                    if area is None:
                        add(idx_here + 1, "case-outside-area", f"case {cid} appears before any '### <area>' heading")
                    elif area.id != f"{cm.group(1)}-{cm.group(2)}-A{cm.group(3)}":
                        add(idx_here + 1, "case-area", f"case {cid} is listed under area {area.id}")
                if has_placeholder(s):
                    add(idx_here + 1, "placeholder", f"case heading {cid} still contains a template placeholder")
                clause.cases.append(case)
                if area is not None:
                    area.cases.append(case)
            else:
                add(idx_here + 1, "bad-heading", "in section 11 only '### <AREA-ID>: Title' and '#### <CASE-ID>: Title' headings are allowed")
            continue
        if not st:
            continue
        if case is not None:
            block.append((idx_here + 1, s))
        elif area is not None and not area.cases and st.startswith("|"):
            area.table_lines.append((idx_here + 1, st))
        elif area is None and case is None:
            if st.strip().rstrip(".").lower() == "none":
                clause.cases_none = True
    finish_case()
    finish_area()
    if not clause.cases and not clause.cases_none:
        add(start, "no-cases", "section 11 has no case; write 'None.' and why if nothing is testable")


def _check_case_fields(clause: Clause, case: Case, add: Callable) -> None:
    f = case.fields
    if "Expected result" in f and f["Expected result"].text:
        err = expected_result_error(f["Expected result"].text)
        if err:
            add(f["Expected result"].line, "expected-citation", f"case {case.id}: {err}")
    if "Test" in f and f["Test"].text:
        try:
            case.kind, case.selector = parse_test_field(f["Test"].text)
        except ValueError as exc:
            add(f["Test"].line, "test-field", f"case {case.id}: {exc}")
    if "Environment" in f and f["Environment"].text:
        env = f["Environment"].text
        if env != "no-site: unittest, frappe stubbed; no database" and not re.fullmatch(
            r"bench: [^,]+, [^,]+, apps [^,].*, site \S.*", env
        ):
            add(f["Environment"].line, "environment",
                f"case {case.id}: Environment must be 'no-site: unittest, frappe stubbed; no database' "
                "or 'bench: <Frappe version>, <DB>, apps <list>, site <synthetic>'")
    if "Evidence" in f and f["Evidence"].text:
        err = evidence_error(f["Evidence"].text)
        if err:
            add(f["Evidence"].line, "evidence", f"case {case.id}: {err}")
        else:
            m = _RECEIPT_RE.match(f["Evidence"].text.strip())
            if m and m["kind"]:
                clause.sha_lines.append((f["Evidence"].line, m["sha"]))


def _check_area_table(clause: Clause, area: Area, add: Callable) -> None:
    rows: list = []
    tl = area.table_lines
    if not tl:
        add(area.line, "index-table-missing", f"area {area.id} needs an index table '| Case | What the assertions check | Test |'")
        clause.rows[area.id] = rows
        return
    head = [c.strip().lower() for c in tl[0][1].strip("|").split("|")]
    if head != _TABLE_HEADER:
        add(tl[0][0], "index-table-header", "index table header must be '| Case | What the assertions check | Test |'")
    if len(tl) < 2 or not re.fullmatch(r"\|[\s:|-]+\|", tl[1][1]):
        add(tl[0][0], "index-table-header", "index table needs the '|---|---|---|' separator row after the header")
        body = tl[1:]
    else:
        body = tl[2:]
    for ln, text in body:
        m = _ROW_RE.match(text)
        if not m:
            add(ln, "index-row-format", "index row must be '| [ID](file.md#anchor) | what the assertions check | [`label`](relative/test_file.py) |'")
            continue
        rows.append(IndexRow(ln, m["id"], m["href"], m["label"], m["thref"]))
        if not m["mid"].strip():
            add(ln, "index-row-format", "the middle cell must say what the assertions check")
    clause.rows[area.id] = rows
    by_id = {c.id: c for c in area.cases}
    seen: dict = {}
    for row in rows:
        case = by_id.get(row.case_id)
        if row.case_id in seen:
            add(row.line, "index-row-duplicate", f"case {row.case_id} has two index rows")
        seen[row.case_id] = row
        if case is None:
            add(row.line, "index-row-unknown", f"index row names {row.case_id}, which is not a case of area {area.id}")
            continue
        want_href = f"{clause.name}#{case.anchor}"
        if row.href != want_href:
            add(row.line, "index-row-link", f"case link must be '{want_href}', found '{row.href}'")
        if case.selector is not None:
            if row.label != selector_label(case.selector):
                add(row.line, "index-row-test", f"test label must be '{selector_label(case.selector)}' (from the Test field), found '{row.label}'")
            target = posixpath.normpath(posixpath.join(posixpath.dirname(clause.rel), row.test_href))
            if target != case.selector.path:
                add(row.line, "index-row-test", f"test link resolves to '{target}' but the Test field names '{case.selector.path}'")
    for case in area.cases:
        if case.id not in seen:
            add(case.line, "index-row-missing", f"case {case.id} has no row in the area {area.id} index table")


# ---------------------------------------------------------------------------
# Discovery, git, reporting, CLI
# ---------------------------------------------------------------------------

def discover_clauses(layout: Layout) -> tuple[list, list]:
    """Return (clause files, findings). Only ``clauses/*.md`` is scanned, never templates."""
    findings: list = []
    files = sorted(p for p in layout.clauses_path.iterdir() if p.is_file() and p.suffix == ".md")
    if not files:
        findings.append(Finding(layout.rel(layout.clauses_path), 1, "no-clauses",
                                "no clause file found; zero clauses is a finding, not a pass"))
    return files, findings


def commit_exists(root: Path, sha: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
            capture_output=True, check=False,
        )
    except OSError as exc:
        raise UsageError(f"--verify-commits needs git: {exc}")
    return r.returncode == 0


def require_git_repo(root: Path) -> None:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-dir"], capture_output=True, check=False)
    except OSError as exc:
        raise UsageError(f"--verify-commits needs git: {exc}")
    if r.returncode != 0:
        raise UsageError("--verify-commits needs --root to be inside a git repository")


def _gh_escape(value: str, prop: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def format_finding(f: Finding, fmt: str) -> str:
    if fmt == "github":
        return f"::error file={_gh_escape(f.path, True)},line={f.line},title={_gh_escape(f.rule, True)}::{_gh_escape(f.message)}"
    return f"{f.path}:{f.line}: {f.rule}: {f.message}"


def run_cli(
    prog: str,
    description: str,
    summary_prefix: str,
    check: Callable,
    argv: Optional[list] = None,
    add_args: Optional[Callable] = None,
) -> int:
    ap = argparse.ArgumentParser(prog=prog, description=description,
                                 epilog="Exit codes: 0 no findings, 1 findings, 2 usage error or spec tree missing.")
    ap.add_argument("--root", default=".", help="repo root (default: .)")
    ap.add_argument("--spec-dir", default="docs/spec", help="spec directory relative to --root (default: docs/spec)")
    ap.add_argument("--format", choices=("text", "github"), default="text", help="finding format (default: text)")
    if add_args:
        add_args(ap)
    ns = ap.parse_args(argv)  # argparse exits with 2 on a usage error
    try:
        layout = make_layout(ns.root, ns.spec_dir)
        findings, stats = check(layout, ns)
    except UsageError as exc:
        print(f"{prog}: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    findings = sorted(set(findings))
    for f in findings:
        print(format_finding(f, ns.format))
    print(f"{summary_prefix}: {stats}, {len(findings)} finding(s)")
    return EXIT_FINDINGS if findings else EXIT_OK
