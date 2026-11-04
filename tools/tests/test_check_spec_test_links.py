"""Tests for tools/check_spec_test_links.py: each broken spec/test link is named."""
import subprocess
import sys
import unittest
from pathlib import Path

from tests.fixture import CLAUSE, CLAUSE_PATH, GOOD, TEST, TEST_PATH, TRACE, SpecTreeCase

TOOLS = Path(__file__).resolve().parents[1]
TRACE_PATH = "docs/spec/test-traceability.md"
DOC_A = f'"""Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)"""'
DOC_B_CHAR = (
    f'"""Spec: CORE-01-A1.1B ({CLAUSE_PATH}#core-01-a1-1b)\n'
    "    Characterization: pins current behaviour, not endorsed.\n    \"\"\""
)


class LinkCase(SpecTreeCase):
    def with_test(self, old, new):
        self.build(**{TEST_PATH: self.sub(TEST, old, new)})
        return self.links()

    def with_trace(self, old, new):
        self.build(**{TRACE_PATH: self.sub(TRACE, old, new)})
        return self.links()


class GoodTree(LinkCase):
    def test_valid_tree_has_no_findings(self):
        self.build()
        code, out, err = self.links()
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, ["spec-links: 2 case(s), 1 test file(s) read, 2 Spec line(s), 0 finding(s)"])

    def test_one_test_may_cover_two_cases_with_two_spec_lines(self):
        # a second case mapped to the same test, with its own Spec line
        clause = CLAUSE.replace("test_two_items`", "test_two_items`", 1)
        extra_case = (
            '\n<a id="core-01-a1-1c"></a>\n#### CORE-01-A1.1C: Two items again\n\n'
            "- Precondition: a list of two items.\n- Action: call `count(items)`.\n"
            "- Expected result: it returns 2 (`widgets/count.py:3`).\n"
            "- Test: characterization: `tests/test_widget.py::test_two_items`\n"
            "- Environment: no-site: unittest, frappe stubbed; no database\n"
            "- Known gaps: None known.\n- Evidence: UNVERIFIED\n"
        )
        row = "| [CORE-01-A1.1C](01-widget-rules.md#core-01-a1-1c) | Same. | [`test_two_items`](../../../tests/test_widget.py) |\n"
        clause = self.sub(clause, "\n<a id=\"core-01-a1-1a\"></a>", row + "\n<a id=\"core-01-a1-1a\"></a>")
        clause = clause.rstrip("\n") + "\n" + extra_case
        trace = TRACE.replace("\n## Uncovered", "| [CORE-01-A1.1C](clauses/01-widget-rules.md#core-01-a1-1c) | `SPEC-CORE-01` | characterization | [`test_two_items`](../../tests/test_widget.py) | UNVERIFIED |\n\n## Uncovered")
        test = TEST.replace(
            "    Characterization: pins current behaviour, not endorsed.\n",
            f"    Spec: CORE-01-A1.1C ({CLAUSE_PATH}#core-01-a1-1c)\n    Characterization: pins current behaviour, not endorsed.\n",
        )
        self.build(**{CLAUSE_PATH: clause, TRACE_PATH: trace, TEST_PATH: test})
        self.assertEqual(self.links()[0], 0, self.links()[1])

    def test_frappe_style_test_class_is_found(self):
        test = (
            "from frappe.tests.utils import FrappeTestCase\n\n\n"
            "class WidgetTests(FrappeTestCase):\n"
            "    def test_empty_counts_zero(self):\n"
            f"        {DOC_A}\n"
            "        self.assertEqual(len([]), 0)\n\n\n"
            "def test_two_items():\n"
            f"    {DOC_B_CHAR}\n"
            "    assert len([1, 2]) == 2\n"
        )
        self.build(**{TEST_PATH: test})
        self.assertEqual(self.links()[0], 0, self.links()[1])

    def test_assertion_in_same_class_helper_counts(self):
        test = TEST.replace(
            "        self.assertEqual(count([]), 0)\n",
            "        self.check_zero()\n\n    def check_zero(self):\n        self.assertEqual(count([]), 0)\n",
        )
        self.build(**{TEST_PATH: test})
        self.assertEqual(self.links()[0], 0, self.links()[1])

    def test_assert_raises_context_counts(self):
        test = TEST.replace(
            "        self.assertEqual(count([]), 0)\n",
            "        with self.assertRaises(TypeError):\n            count(None)\n",
        )
        self.build(**{TEST_PATH: test})
        self.assertEqual(self.links()[0], 0, self.links()[1])

    def test_templates_directory_is_not_scanned(self):
        self.build(**{"docs/spec/templates/case-block-template.md": "#### CORE-99-A1.1A: <x>\n- Test: mapped: `nope.py::T::test_x`\n"})
        self.assertEqual(self.links()[0], 0)


class SpecToTest(LinkCase):
    def test_missing_test_file_rejected(self):
        self.build(**{TEST_PATH: None})
        code, out, _ = self.links()
        self.assertEqual(code, 1)
        hits = self.assertRule(out, "test-file", "does not exist")
        self.assertEqual(len(hits), 2)

    def test_missing_function_rejected(self):
        code, out, _ = self.with_test("def test_empty_counts_zero(self):", "def test_renamed(self):")
        self.assertEqual(code, 1)
        self.assertRule(out, "test-missing", "test_empty_counts_zero")

    def test_missing_class_rejected(self):
        self.assertRule(self.with_test("class WidgetTests(", "class OtherTests(")[1], "test-missing", "class 'WidgetTests' not found")

    def test_function_defined_in_wrong_class_rejected(self):
        test = TEST + "\n\nclass Other(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(1 == 1)\n"
        clause = self.sub(CLAUSE, "WidgetTests::test_empty_counts_zero", "Other::test_empty_counts_zero")
        self.build(**{TEST_PATH: test, CLAUSE_PATH: clause})
        self.assertRule(self.links()[1], "test-missing", "'test_empty_counts_zero' is not defined")

    def test_inherited_test_does_not_count(self):
        test = TEST + "\n\nclass Child(WidgetTests):\n    pass\n"
        clause = self.sub(CLAUSE, "WidgetTests::test_empty_counts_zero", "Child::test_empty_counts_zero")
        self.build(**{TEST_PATH: test, CLAUSE_PATH: clause})
        self.assertRule(self.links()[1], "test-missing", "inherited")

    def test_module_function_selector_does_not_match_method(self):
        clause = self.sub(CLAUSE, "tests/test_widget.py::WidgetTests::test_empty_counts_zero", "tests/test_widget.py::test_empty_counts_zero")
        self.build(**{CLAUSE_PATH: clause})
        self.assertRule(self.links()[1], "test-missing", "module level")

    def test_unparseable_test_file_rejected(self):
        self.build(**{TEST_PATH: "def test_x(:\n"})
        self.assertRule(self.links()[1], "test-file", "does not parse")

    def test_case_with_malformed_selector_is_unlinkable(self):
        clause = self.sub(CLAUSE, "`tests/test_widget.py::test_two_items`", "`tests/*.py::test_two_items`")
        self.build(**{CLAUSE_PATH: clause})
        self.assertRule(self.links()[1], "case-unlinkable", "CORE-01-A1.1B")


class RealTestNotScaffold(LinkCase):
    def test_skip_decorators_rejected(self):
        for deco in ("@unittest.skip('later')", "@unittest.skipIf(True, 'x')", "@unittest.expectedFailure", "@pytest.mark.skip", "@pytest.mark.xfail"):
            with self.subTest(deco=deco):
                code, out, _ = self.with_test("    def test_empty_counts_zero", f"    {deco}\n    def test_empty_counts_zero")
                self.assertEqual(code, 1)
                self.assertRule(out, "test-skipped", "CORE-01-A1.1A")

    def test_skip_inside_body_rejected(self):
        for call in ("self.skipTest('no db')", "pytest.skip('no db')", "raise unittest.SkipTest('x')"):
            with self.subTest(call=call):
                code, out, _ = self.with_test("        self.assertEqual(count([]), 0)", f"        {call}\n        self.assertEqual(count([]), 0)")
                self.assertRule(out, "test-skipped")

    def test_skipped_class_rejected(self):
        self.assertRule(self.with_test("class WidgetTests(", "@unittest.skip('x')\nclass WidgetTests(")[1], "test-skipped", "class WidgetTests")

    def test_module_function_skip_rejected(self):
        self.assertRule(self.with_test("def test_two_items", "@pytest.mark.skip\ndef test_two_items")[1], "test-skipped", "CORE-01-A1.1B")

    def test_pass_only_test_is_scaffold(self):
        code, out, _ = self.with_test("        self.assertEqual(count([]), 0)", "        pass")
        self.assertEqual(code, 1)
        self.assertRule(out, "test-scaffold", "CORE-01-A1.1A")

    def test_assert_true_constant_is_scaffold(self):
        for body in ("self.assertTrue(True)", "self.assertEqual(1, 1)", "self.assertIsNone(None)", "assert True", "assert 1"):
            with self.subTest(body=body):
                self.assertRule(self.with_test("        self.assertEqual(count([]), 0)", f"        {body}")[1], "test-scaffold")

    def test_import_only_test_is_scaffold(self):
        self.assertRule(self.with_test("        self.assertEqual(count([]), 0)", "        import json")[1], "test-scaffold")

    def test_empty_frappe_test_class_pattern_is_not_coverage(self):
        # the shape 57 of 58 test_*.py files in CN-HRMS-Core have: a class with only 'pass'
        test = TEST + '\n\nclass TestEmployeeRole(unittest.TestCase):\n    pass\n'
        clause = self.sub(CLAUSE, "WidgetTests::test_empty_counts_zero", "TestEmployeeRole::test_empty_counts_zero")
        self.build(**{TEST_PATH: test, CLAUSE_PATH: clause})
        self.assertRule(self.links()[1], "test-missing")

    def test_assertion_on_unrelated_literal_calls_only_is_scaffold(self):
        self.assertRule(self.with_test("        self.assertEqual(count([]), 0)", "        self.assertEqual(0, 0)\n        self.assertTrue(True)")[1], "test-scaffold")


class TestToSpec(LinkCase):
    def test_missing_spec_line_rejected(self):
        code, out, _ = self.with_test(f'        {DOC_A}\n', "")
        self.assertEqual(code, 1)
        self.assertRule(out, "spec-line-missing", "CORE-01-A1.1A")

    def test_spec_line_with_wrong_anchor_rejected(self):
        self.assertRule(self.with_test("#core-01-a1-1a)", "#core-01-a1-1z)")[1], "spec-line-ref", "core-01-a1-1z")

    def test_spec_line_with_wrong_path_rejected(self):
        self.assertRule(self.with_test("docs/spec/clauses/01-widget-rules.md#core-01-a1-1a", "docs/spec/01-widget-rules.md#core-01-a1-1a")[1], "spec-line-ref")

    def test_spec_line_with_wildcard_path_rejected(self):
        self.assertRule(self.with_test("docs/spec/clauses/01-widget-rules.md#core-01-a1-1a", "docs/spec/clauses/*.md#core-01-a1-1a")[1], "spec-line-ref")

    def test_spec_line_in_comment_instead_of_docstring_rejected(self):
        code, out, _ = self.with_test(f'        {DOC_A}\n', f"        # Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)\n")
        self.assertRule(out, "spec-line-missing")

    def test_spec_line_in_class_docstring_rejected(self):
        test = self.sub(TEST, "class WidgetTests(unittest.TestCase):\n", f'class WidgetTests(unittest.TestCase):\n    """Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)"""\n\n')
        self.build(**{TEST_PATH: test})
        self.assertRule(self.links()[1], "spec-line-misplaced")

    def test_malformed_spec_line_rejected(self):
        self.assertRule(self.with_test("(docs/spec/clauses/01-widget-rules.md#core-01-a1-1a)", "docs/spec/clauses/01-widget-rules.md#core-01-a1-1a")[1], "spec-line-format")

    def test_characterization_test_needs_its_line(self):
        code, out, _ = self.with_test("    Characterization: pins current behaviour, not endorsed.\n", "")
        self.assertEqual(code, 1)
        self.assertRule(out, "characterization-line", "CORE-01-A1.1B")

    def test_mapped_test_must_not_carry_characterization_line(self):
        test = self.sub(TEST, f'        """Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)"""', f'        """Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)\n        Characterization: pins current behaviour, not endorsed.\n        """')
        self.build(**{TEST_PATH: test})
        self.assertRule(self.links()[1], "characterization-line", "'mapped'")

    def test_orphan_spec_line_for_unknown_case_rejected(self):
        other = 'def test_unrelated():\n    """Spec: CORE-01-A9.9Z (docs/spec/clauses/01-widget-rules.md#core-01-a9-9z)"""\n    assert 1 + 1 == 2\n'
        self.build(**{"tests/test_other.py": other})
        self.assertRule(self.links()[1], "spec-line-orphan", "CORE-01-A9.9Z")

    def test_spec_line_on_a_test_the_case_does_not_name_rejected(self):
        other = f'def test_unrelated():\n    """Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)"""\n    assert 1 + 1 == 2\n'
        self.build(**{"tests/test_other.py": other})
        self.assertRule(self.links()[1], "spec-line-mismatch", "test_unrelated")

    def test_duplicate_spec_line_rejected(self):
        self.assertRule(self.with_test(f'        {DOC_A}\n', f'        """Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)\n        Spec: CORE-01-A1.1A ({CLAUSE_PATH}#core-01-a1-1a)\n        """\n')[1], "spec-line-duplicate")

    def test_spec_lines_in_non_test_dirs_are_scanned_but_vendored_dirs_are_not(self):
        stale = f'def test_old():\n    """Spec: CORE-01-A8.8A ({CLAUSE_PATH}#core-01-a8-8a)"""\n    assert 1\n'
        self.build(**{"node_modules/pkg/test_old.py": stale, "app/test_old.py": stale})
        out = self.links()[1]
        hits = self.assertRule(out, "spec-line-orphan")
        self.assertEqual(len(hits), 1)
        self.assertIn("app/test_old.py", hits[0])


class Traceability(LinkCase):
    def test_missing_file_rejected(self):
        self.build(**{TRACE_PATH: None})
        self.assertRule(self.links()[1], "traceability-missing")

    def test_missing_row_rejected(self):
        row = "| [CORE-01-A1.1B](clauses/01-widget-rules.md#core-01-a1-1b) | `SPEC-CORE-01` | characterization | [`test_two_items`](../../tests/test_widget.py) | UNVERIFIED |\n"
        self.assertRule(self.with_trace(row, "")[1], "traceability-missing-row", "CORE-01-A1.1B")

    def test_row_for_unknown_case_rejected(self):
        row = "| [CORE-01-A1.1B](clauses/01-widget-rules.md#core-01-a1-1b) | `SPEC-CORE-01` | characterization | [`test_two_items`](../../tests/test_widget.py) | UNVERIFIED |\n"
        self.assertRule(self.with_trace(row, row + row.replace("1.1B", "1.1Q").replace("1-1b", "1-1q"))[1], "traceability-orphan-row")

    def test_duplicate_row_rejected(self):
        row = "| [CORE-01-A1.1B](clauses/01-widget-rules.md#core-01-a1-1b) | `SPEC-CORE-01` | characterization | [`test_two_items`](../../tests/test_widget.py) | UNVERIFIED |\n"
        self.assertRule(self.with_trace(row, row + row)[1], "traceability-duplicate")

    def test_wrong_kind_rejected(self):
        self.assertRule(self.with_trace("| characterization |", "| mapped |")[1], "traceability-kind")

    def test_wrong_clause_rejected(self):
        self.assertRule(self.with_trace("`SPEC-CORE-01` | mapped", "`SPEC-CORE-02` | mapped")[1], "traceability-clause")

    def test_wrong_test_label_rejected(self):
        self.assertRule(self.with_trace("[`test_two_items`]", "[`test_other`]")[1], "traceability-test", "label")

    def test_test_link_to_other_file_rejected(self):
        self.assertRule(self.with_trace("[`test_two_items`](../../tests/test_widget.py)", "[`test_two_items`](../../tests/test_other.py)")[1], "traceability-test", "resolves to")

    def test_link_to_wrong_anchor_rejected(self):
        self.assertRule(self.with_trace("(clauses/01-widget-rules.md#core-01-a1-1b)", "(clauses/01-widget-rules.md#core-01-a1-1a)")[1], "traceability-link")

    def test_evidence_disagreement_rejected(self):
        self.assertRule(self.with_trace("characterization | [`test_two_items`](../../tests/test_widget.py) | UNVERIFIED", "characterization | [`test_two_items`](../../tests/test_widget.py) | passed")[1], "traceability-evidence")

    def test_short_row_rejected(self):
        self.assertRule(self.with_trace("| mapped | [`WidgetTests", "| [`WidgetTests")[1], "traceability-row")

    def test_retired_id_reuse_rejected(self):
        code, out, _ = self.with_trace("## Retired IDs\n\nNone.\n", "## Retired IDs\n\n- CORE-01-A1.1B (removed)\n")
        self.assertEqual(code, 1)
        self.assertRule(out, "retired-id-reused", "CORE-01-A1.1B")


class Cli(LinkCase):
    def test_usage_error_exit_2(self):
        self.assertEqual(self.links()[0], 2)  # nothing built: no clauses dir

    def test_empty_clauses_dir_is_a_finding(self):
        self.build(**{CLAUSE_PATH: None, "docs/spec/clauses/.keep": ""})
        code, out, _ = self.links()
        self.assertEqual(code, 1)
        self.assertRule(out, "no-clauses")

    def test_github_format(self):
        code, out, _ = self.with_test(f'        {DOC_A}\n', "")
        code, out, _ = self.links("--format", "github")
        self.assertEqual(code, 1)
        line = [l for l in out if l.startswith("::error")][0]
        self.assertIn(f"file={TEST_PATH},line=", line)
        self.assertIn("title=spec-line-missing::", line)

    def test_script_runs_as_a_command_and_sets_exit_code(self):
        self.build()
        cmd = [sys.executable, str(TOOLS / "check_spec_test_links.py"), "--root", str(self.root)]
        self.assertEqual(subprocess.run(cmd, capture_output=True, text=True).returncode, 0)
        (self.root / TEST_PATH).unlink()
        bad = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("test-file", bad.stdout)


if __name__ == "__main__":
    unittest.main()
