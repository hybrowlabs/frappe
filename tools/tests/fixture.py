"""Builds a small, valid, synthetic spec tree in a temp dir for the checker tests.

Every test starts from ``GOOD`` (zero findings), changes one thing, and asserts the
checker reports the specific rule. Only synthetic names appear here.
"""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import check_spec_cases
import check_spec_test_links

SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_SHA = "fedcba9876543210fedcba9876543210fedcba98"
CLAUSE_NAME = "01-widget-rules.md"
CLAUSE_PATH = f"docs/spec/clauses/{CLAUSE_NAME}"
TEST_PATH = "tests/test_widget.py"
SPEC_REF = f"{CLAUSE_PATH}#"

README = """# As-built specifications

| ID | Title | Described at |
|---|---|---|
| `SPEC-CORE-01` | [Widget rules](clauses/01-widget-rules.md) | `main` |
"""

CLAUSE = f"""# SPEC-CORE-01: Widget rules

<a id="spec-core-01"></a>

- Stable ID: `SPEC-CORE-01`
- Described at: repo `example/widgets`, branch `main`, commit `{SHA}` (committer date `2026-10-29 21:12:47 +0530`)
- Also read at: branch `release`, commit `{OTHER_SHA}`; same
- Author: Writer A. Reviewer: Reviewer B.
- Status: DRAFT

## 1. Purpose

Widgets are counted (`widgets/count.py:3`).

## 2. Boundaries

- In: `count()`.

## 3. Behaviour rules

### A1: Counting

- A1.1: An empty list counts as zero (`widgets/count.py:3`).

## 4. Data and permissions

None. Pure function.

## 5. Errors and edge behaviour

None.

## 6. Configuration

None.

## 7. Scheduled jobs, hooks and patches

None.

## 8. Static security and performance observations

None.

## 9. Known gaps / open questions

None known.

## 10. Uncovered behaviour

None.

## 11. Acceptance cases

<a id="core-01-a1"></a>
### CORE-01-A1: Counting

| Case | What the assertions check | Test |
|---|---|---|
| [CORE-01-A1.1A](01-widget-rules.md#core-01-a1-1a) | The count of an empty list equals 0. | [`WidgetTests.test_empty_counts_zero`](../../../tests/test_widget.py) |
| [CORE-01-A1.1B](01-widget-rules.md#core-01-a1-1b) | The count of two items equals 2. | [`test_two_items`](../../../tests/test_widget.py) |

<a id="core-01-a1-1a"></a>
#### CORE-01-A1.1A: Empty list counts zero

- Precondition: an empty list.
- Action: call `count([])`.
- Expected result: it returns 0 (`widgets/count.py:3`).
- Test: mapped: `tests/test_widget.py::WidgetTests::test_empty_counts_zero`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: None known.
- Evidence: UNVERIFIED

<a id="core-01-a1-1b"></a>
#### CORE-01-A1.1B: Two items count two

- Precondition: a list of two items.
- Action: call `count(items)`.
- Expected result: it returns 2 (`widgets/count.py:3`).
- Test: characterization: `tests/test_widget.py::test_two_items`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: Pins current behaviour only.
- Evidence: UNVERIFIED
"""

TRACE = f"""# Test traceability index

## Cases

| Case | Clause | Test kind | Test | Evidence |
|---|---|---|---|---|
| [CORE-01-A1.1A](clauses/01-widget-rules.md#core-01-a1-1a) | `SPEC-CORE-01` | mapped | [`WidgetTests.test_empty_counts_zero`](../../tests/test_widget.py) | UNVERIFIED |
| [CORE-01-A1.1B](clauses/01-widget-rules.md#core-01-a1-1b) | `SPEC-CORE-01` | characterization | [`test_two_items`](../../tests/test_widget.py) | UNVERIFIED |

## Uncovered behaviour

None.

## Retired IDs

None.
"""

TEST = f'''import unittest


def count(items):
    return len(items)


class WidgetTests(unittest.TestCase):
    def test_empty_counts_zero(self):
        """Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)"""
        self.assertEqual(count([]), 0)


def test_two_items():
    """Spec: CORE-01-A1.1B ({CLAUSE_PATH}#core-01-a1-1b)
    Characterization: pins current behaviour, not endorsed.
    """
    assert count([1, 2]) == 2
'''

GOOD = {
    "docs/spec/README.md": README,
    CLAUSE_PATH: CLAUSE,
    "docs/spec/test-traceability.md": TRACE,
    TEST_PATH: TEST,
}


class SpecTreeCase(unittest.TestCase):
    """Base class: writes ``GOOD`` plus overrides to a temp root and runs a checker."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def build(self, **changes):
        """changes: path -> new content, or None to delete. Keys use '/' separators."""
        files = dict(GOOD)
        for key, value in changes.items():
            if value is None:
                files.pop(key, None)
            else:
                files[key] = value
        for rel, content in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def sub(self, text, old, new, count=1):
        """Replace ``old`` with ``new`` in ``text``; fail loudly if ``old`` is absent."""
        self.assertIn(old, text, f"fixture drift: {old!r} not found")
        return text.replace(old, new, count)

    def run_tool(self, module, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = module.main(["--root", str(self.root), *extra])
            except SystemExit as exc:  # argparse usage error
                code = exc.code
        return code, out.getvalue().splitlines(), err.getvalue()

    def cases(self, *extra):
        return self.run_tool(check_spec_cases, *extra)

    def links(self, *extra):
        return self.run_tool(check_spec_test_links, *extra)

    def rules(self, lines):
        """Rule names of the finding lines (``path:line: rule: msg``)."""
        found = []
        for ln in lines:
            if ln.startswith(("spec-cases:", "spec-links:")):
                continue
            found.append(ln.split(": ", 2)[1])
        return found

    def assertRule(self, lines, rule, contains=None):
        hits = [ln for ln in lines if f": {rule}: " in ln]
        self.assertTrue(hits, f"rule {rule!r} not reported; output:\n" + "\n".join(lines))
        if contains is not None:
            self.assertTrue(any(contains in ln for ln in hits), f"{contains!r} not in {hits}")
        return hits
