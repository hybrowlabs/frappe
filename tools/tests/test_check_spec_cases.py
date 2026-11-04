"""Tests for tools/check_spec_cases.py: the good tree passes, each malformed input is named."""
import subprocess
import sys
import unittest
from pathlib import Path

import check_spec_cases
from tests.fixture import (
    CLAUSE,
    CLAUSE_PATH,
    GOOD,
    OTHER_SHA,
    SHA,
    SpecTreeCase,
)

TOOLS = Path(__file__).resolve().parents[1]


class GoodTree(SpecTreeCase):
    def test_valid_tree_has_no_findings(self):
        self.build()
        code, out, err = self.cases()
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, ["spec-cases: 1 clause(s), 2 case(s), 0 finding(s)"])

    def test_templates_are_never_scanned(self):
        # Templates hold placeholders; scanning them would be a false positive.
        self.build(**{
            "docs/spec/templates/clause-template.md": "# SPEC-<CODE>-NN: <Title>\n<placeholder>\n",
            "docs/spec/clauses/../templates/case-block-template.md": "<a id=\"<code>\"></a>\n",
        })
        self.assertEqual(self.cases()[0], 0)

    def test_fenced_and_commented_text_is_ignored(self):
        text = CLAUSE.replace(
            "## 4. Data and permissions\n",
            "## 4. Data and permissions\n\n```\n#### BAD-ID: not a case\n- Result: pass\n```\n<!-- <placeholder> -->\n",
        )
        self.build(**{CLAUSE_PATH: text})
        self.assertEqual(self.cases()[0], 0)

    def test_receipt_evidence_is_accepted(self):
        receipt = f"local; python3 -m unittest tests.test_widget; exit 0; 1 passed, 0 failed, 0 skipped; commit {OTHER_SHA}; env no-site"
        text = self.sub(CLAUSE, "- Evidence: UNVERIFIED", f"- Evidence: {receipt}")
        self.build(**{CLAUSE_PATH: text})
        self.assertEqual(self.cases()[0], 0)


class UsageErrors(SpecTreeCase):
    def test_missing_clauses_dir_is_exit_2(self):
        code, out, err = self.cases()  # nothing built
        self.assertEqual(code, 2)
        self.assertIn("clauses directory not found", err)
        self.assertEqual(out, [])

    def test_spec_dir_escaping_root_is_exit_2(self):
        self.build()
        code, _, err = self.cases("--spec-dir", "../outside")
        self.assertEqual(code, 2)
        self.assertIn("--spec-dir", err)

    def test_unknown_flag_is_exit_2(self):
        self.build()
        self.assertEqual(self.cases("--nope")[0], 2)

    def test_root_not_a_directory_is_exit_2(self):
        code, _, err = self.run_tool(check_spec_cases, "--root", str(self.root / "missing"))
        self.assertEqual(code, 2)

    def test_empty_clauses_dir_is_a_finding_not_a_pass(self):
        self.build(**{CLAUSE_PATH: None, "docs/spec/clauses/.keep": ""})
        code, out, _ = self.cases()
        self.assertEqual(code, 1)
        self.assertRule(out, "no-clauses")

    def test_custom_spec_dir(self):
        self.build()
        (self.root / "documents").mkdir()
        (self.root / "docs" / "spec").rename(self.root / "documents" / "spec")
        self.assertEqual(self.cases("--spec-dir", "documents/spec")[0], 0)


class Header(SpecTreeCase):
    def mutate(self, old, new):
        self.build(**{CLAUSE_PATH: self.sub(CLAUSE, old, new)})
        return self.cases()

    def test_short_sha_rejected(self):
        code, out, _ = self.mutate(f"commit `{SHA}`", "commit `0123abc`")
        self.assertEqual(code, 1)
        self.assertRule(out, "header-commit")

    def test_uppercase_sha_rejected(self):
        self.assertRule(self.mutate(f"commit `{SHA}`", f"commit `{SHA.upper()}`")[1], "header-commit")

    def test_branch_name_instead_of_commit_rejected(self):
        self.assertRule(self.mutate(f"commit `{SHA}`", "commit `main`")[1], "header-commit")

    def test_missing_commit_rejected(self):
        self.assertRule(self.mutate(f", commit `{SHA}`", "")[1], "header-commit")

    def test_missing_branch_rejected(self):
        self.assertRule(self.mutate("branch `main`, ", "")[1], "header-branch")

    def test_head_as_branch_rejected(self):
        self.assertRule(self.mutate("branch `main`", "branch `HEAD`")[1], "header-branch")

    def test_bad_repo_rejected(self):
        self.assertRule(self.mutate("repo `example/widgets`", "repo `widgets`")[1], "header-repo")

    def test_bad_committer_date_rejected(self):
        self.assertRule(self.mutate("2026-10-29 21:12:47 +0530", "yesterday")[1], "header-date")

    def test_missing_described_at_rejected(self):
        text = "\n".join(l for l in CLAUSE.split("\n") if not l.startswith("- Described at:"))
        self.build(**{CLAUSE_PATH: text})
        self.assertRule(self.cases()[1], "header-described-at")

    def test_missing_stable_id_rejected(self):
        text = "\n".join(l for l in CLAUSE.split("\n") if not l.startswith("- Stable ID:"))
        self.build(**{CLAUSE_PATH: text})
        self.assertRule(self.cases()[1], "header-stable-id")

    def test_stable_id_number_must_match_file(self):
        self.build(**{CLAUSE_PATH: None, "docs/spec/clauses/02-widget-rules.md": CLAUSE})
        self.assertRule(self.cases()[1], "header-stable-id", "does not match file name")

    def test_title_must_carry_stable_id(self):
        self.assertRule(self.mutate("# SPEC-CORE-01: Widget rules", "# Widget rules")[1], "title-mismatch")

    def test_clause_anchor_required(self):
        self.assertRule(self.mutate('<a id="spec-core-01"></a>\n', "")[1], "clause-anchor")

    def test_author_equal_reviewer_rejected(self):
        self.assertRule(self.mutate("Author: Writer A. Reviewer: Reviewer B.", "Author: Writer A. Reviewer: Writer A.")[1], "header-reviewer")

    def test_author_without_reviewer_rejected(self):
        self.assertRule(self.mutate("Author: Writer A. Reviewer: Reviewer B.", "Author: Writer A")[1], "header-author")

    def test_status_must_be_known(self):
        self.assertRule(self.mutate("Status: DRAFT", "Status: DONE")[1], "header-status")

    def test_also_read_at_needs_delta_statement(self):
        self.assertRule(self.mutate(f"commit `{OTHER_SHA}`; same", f"commit `{OTHER_SHA}`")[1], "header-also-delta")

    def test_also_read_at_needs_full_sha(self):
        self.assertRule(self.mutate(f"commit `{OTHER_SHA}`", "commit `abc`")[1], "header-also-commit")

    def test_template_placeholder_in_header_rejected(self):
        self.assertRule(self.mutate("Writer A.", "<role/agent>.")[1], "placeholder")

    def test_duplicate_header_line_rejected(self):
        self.assertRule(self.mutate("- Status: DRAFT", "- Status: DRAFT\n- Status: ACCEPTED")[1], "header-duplicate")


class PerformanceRule(SpecTreeCase):
    """Opt-in ``--require-performance``: section 8 must hold a non-empty Performance item."""

    SEC8 = "## 8. Static security and performance observations\n\nNone.\n"

    def with_sec8(self, body):
        text = self.sub(CLAUSE, self.SEC8, "## 8. Static security and performance observations\n\n" + body)
        self.build(**{CLAUSE_PATH: text})
        return self.cases("--require-performance")

    def test_off_by_default(self):
        self.build()  # fixture section 8 says only "None."
        self.assertEqual(self.cases()[0], 0)

    def test_section_without_performance_item_rejected(self):
        self.build()
        code, out, _ = self.cases("--require-performance")
        self.assertEqual(code, 1)
        self.assertRule(out, "performance-missing")

    def test_security_bullet_alone_is_not_performance(self):
        code, out, _ = self.with_sec8("- Security: reads one list (`widgets/count.py:3`).\n")
        self.assertEqual(code, 1)
        self.assertRule(out, "performance-missing")

    def test_findings_bullet_accepted(self):
        code, out, _ = self.with_sec8("- Performance: one query per widget in a loop (`widgets/count.py:3`). Issue: PWHR-1.\n")
        self.assertEqual((code, out), (0, ["spec-cases: 1 clause(s), 2 case(s), 0 finding(s)"]))

    def test_numbered_and_topic_labels_accepted(self):
        body = "- Performance (1): reads all rows (`widgets/count.py:3`).\n- Performance, request path: sync call (`widgets/count.py:3`).\n"
        self.assertEqual(self.with_sec8(body)[0], 0)

    def test_no_findings_with_checked_list_accepted(self):
        body = "- Performance: No performance findings. Checked: loops, unbounded reads, indexes, jobs, request path, fetches.\n"
        self.assertEqual(self.with_sec8(body)[0], 0)

    def test_no_findings_without_checked_list_rejected(self):
        code, out, _ = self.with_sec8("- Performance: No performance findings.\n")
        self.assertEqual(code, 1)
        self.assertRule(out, "performance-unchecked")

    def test_empty_performance_bullet_rejected(self):
        code, out, _ = self.with_sec8("- Performance:\n")
        self.assertEqual(code, 1)
        self.assertRule(out, "performance-empty")

    def test_heading_form_accepted_and_empty_heading_rejected(self):
        ok = self.with_sec8("### Performance\n\n- Reads every row (`widgets/count.py:3`).\n")
        self.assertEqual(ok[0], 0)
        bad = self.with_sec8("### Performance\n\n")
        self.assertEqual(bad[0], 1)
        self.assertRule(bad[1], "performance-empty")

    def test_performance_in_fenced_block_does_not_count(self):
        code, out, _ = self.with_sec8("```\n- Performance: hidden in a fence.\n```\n")
        self.assertEqual(code, 1)
        self.assertRule(out, "performance-missing")

    def test_performance_in_another_section_does_not_count(self):
        text = self.sub(CLAUSE, "## 6. Configuration\n\nNone.\n", "## 6. Configuration\n\n- Performance: sits in the wrong section (`widgets/count.py:3`).\n")
        self.build(**{CLAUSE_PATH: text})
        code, out, _ = self.cases("--require-performance")
        self.assertEqual(code, 1)
        self.assertRule(out, "performance-missing")


class Sections(SpecTreeCase):
    def test_missing_section_rejected(self):
        text = self.sub(CLAUSE, "## 6. Configuration\n\nNone.\n\n", "")
        self.build(**{CLAUSE_PATH: text})
        self.assertRule(self.cases()[1], "section-missing", "6. Configuration")

    def test_empty_section_rejected(self):
        text = self.sub(CLAUSE, "## 6. Configuration\n\nNone.\n", "## 6. Configuration\n")
        self.build(**{CLAUSE_PATH: text})
        self.assertRule(self.cases()[1], "section-empty")

    def test_wrong_section_title_rejected(self):
        text = self.sub(CLAUSE, "## 1. Purpose", "## 1. Overview")
        self.build(**{CLAUSE_PATH: text})
        self.assertRule(self.cases()[1], "section-title")

    def test_sections_out_of_order_rejected(self):
        text = self.sub(CLAUSE, "## 4. Data and permissions", "## 7. Data and permissions")
        self.build(**{CLAUSE_PATH: text})
        self.assertTrue(self.cases()[0] == 1)


class CaseSchema(SpecTreeCase):
    def mutate(self, old, new, count=1):
        self.build(**{CLAUSE_PATH: self.sub(CLAUSE, old, new, count)})
        return self.cases()

    def drop_line(self, startswith, occurrence=0):
        lines = CLAUSE.split("\n")
        hits = [i for i, l in enumerate(lines) if l.startswith(startswith)]
        del lines[hits[occurrence]]
        self.build(**{CLAUSE_PATH: "\n".join(lines)})
        return self.cases()

    def test_each_missing_field_is_named(self):
        for field in ("Precondition", "Action", "Expected result", "Test", "Environment", "Known gaps", "Evidence"):
            with self.subTest(field=field):
                code, out, _ = self.drop_line(f"- {field}:")
                self.assertEqual(code, 1)
                self.assertRule(out, "field-missing", f"'{field}'")

    def test_extra_field_rejected(self):
        code, out, _ = self.mutate("- Evidence: UNVERIFIED\n\n<a id=\"core-01-a1-1b\">", "- Evidence: UNVERIFIED\n- Result: pass\n\n<a id=\"core-01-a1-1b\">")
        self.assertRule(out, "field-unknown", "Result")

    def test_loose_text_in_case_block_rejected(self):
        code, out, _ = self.mutate("- Known gaps: None known.\n- Evidence", "- Known gaps: None known.\nSome loose sentence.\n- Evidence")
        self.assertRule(out, "loose-text")

    def test_fields_out_of_order_rejected(self):
        a = "- Precondition: an empty list.\n- Action: call `count([])`.\n"
        b = "- Action: call `count([])`.\n- Precondition: an empty list.\n"
        self.assertRule(self.mutate(a, b)[1], "field-order")

    def test_duplicate_field_rejected(self):
        self.assertRule(self.mutate("- Action: call `count([])`.\n", "- Action: call `count([])`.\n- Action: again.\n")[1], "field-duplicate")

    def test_empty_field_rejected(self):
        self.assertRule(self.mutate("- Precondition: an empty list.", "- Precondition:")[1], "field-empty")

    def test_placeholder_left_in_field_rejected(self):
        self.assertRule(self.mutate("- Precondition: an empty list.", "- Precondition: <state before the action>")[1], "placeholder")

    def test_expected_result_without_citation_rejected(self):
        code, out, _ = self.mutate("it returns 0 (`widgets/count.py:3`).", "it returns 0.")
        self.assertRule(out, "expected-citation")

    def test_expected_result_citation_without_line_rejected(self):
        self.assertRule(self.mutate("(`widgets/count.py:3`).\n- Test: mapped", "(`widgets/count.py`).\n- Test: mapped")[1], "expected-citation")

    def test_expected_result_citation_must_be_last(self):
        self.assertRule(self.mutate("it returns 0 (`widgets/count.py:3`).", "it returns 0 (`widgets/count.py:3`) always.")[1], "expected-citation")

    def test_expected_result_absolute_citation_rejected(self):
        self.assertRule(self.mutate("`widgets/count.py:3`).\n- Test: mapped", "`/home/x/widgets/count.py:3`).\n- Test: mapped")[1], "expected-citation")

    def test_expected_result_backwards_range_rejected(self):
        self.assertRule(self.mutate("`widgets/count.py:3`).\n- Test: mapped", "`widgets/count.py:9-3`).\n- Test: mapped")[1], "expected-citation")

    def test_evidence_pass_without_receipt_rejected(self):
        for bad in ("PASSED", "passed", "UNVERIFIED:", "local; ok"):
            with self.subTest(bad=bad):
                code, out, _ = self.mutate("- Evidence: UNVERIFIED\n\n<a id=\"core-01-a1-1b\">", f"- Evidence: {bad}\n\n<a id=\"core-01-a1-1b\">")
                self.assertRule(out, "evidence")

    def test_receipt_with_failures_rejected(self):
        r = f"local; cmd; exit 0; 1 passed, 2 failed, 0 skipped; commit {SHA}; env no-site"
        self.assertRule(self.mutate("- Evidence: UNVERIFIED\n\n<a id=\"core-01-a1-1b\">", f"- Evidence: {r}\n\n<a id=\"core-01-a1-1b\">")[1], "evidence", "0 failed")

    def test_receipt_with_zero_passed_rejected(self):
        r = f"local; cmd; exit 0; 0 passed, 0 failed, 0 skipped; commit {SHA}; env no-site"
        self.assertRule(self.mutate("- Evidence: UNVERIFIED\n\n<a id=\"core-01-a1-1b\">", f"- Evidence: {r}\n\n<a id=\"core-01-a1-1b\">")[1], "evidence")

    def test_receipt_short_sha_rejected(self):
        r = "local; cmd; exit 0; 1 passed, 0 failed, 0 skipped; commit abc123; env no-site"
        self.assertRule(self.mutate("- Evidence: UNVERIFIED\n\n<a id=\"core-01-a1-1b\">", f"- Evidence: {r}\n\n<a id=\"core-01-a1-1b\">")[1], "evidence")

    def test_ci_receipt_needs_run_id(self):
        r = f"ci; cmd; exit 0; 1 passed, 0 failed, 0 skipped; commit {SHA}; env no-site"
        self.assertRule(self.mutate("- Evidence: UNVERIFIED\n\n<a id=\"core-01-a1-1b\">", f"- Evidence: {r}\n\n<a id=\"core-01-a1-1b\">")[1], "evidence", "run")

    def test_environment_must_be_known_form(self):
        self.assertRule(self.mutate("- Environment: no-site: unittest, frappe stubbed; no database", "- Environment: my laptop")[1], "environment")

    def test_bench_environment_accepted(self):
        env = "bench: Frappe 15.0, MariaDB 10.6, apps cn_hrms_core, site test.example.invalid"
        self.assertEqual(self.mutate("- Environment: no-site: unittest, frappe stubbed; no database", f"- Environment: {env}")[0], 0)

    def test_malformed_test_fields_rejected(self):
        bad = [
            "- Test: tests/test_widget.py::WidgetTests::test_empty_counts_zero",  # no kind
            "- Test: covered: `tests/test_widget.py::WidgetTests::test_empty_counts_zero`",  # unknown kind
            "- Test: mapped: `tests/test_widget.py`",  # no function
            "- Test: mapped: `tests/*.py::WidgetTests::test_empty_counts_zero`",  # wildcard
            "- Test: mapped: `/abs/tests/test_widget.py::WidgetTests::test_x`",  # absolute
            "- Test: mapped: `../tests/test_widget.py::WidgetTests::test_x`",  # ..
            "- Test: mapped: `tests/test_widget.js::it works`",  # not python
            "- Test: mapped: `tests/test_widget.py::WidgetTests::helper`",  # not test_*
            "- Test: mapped: `tests/test_widget.py::A::B::test_x`",  # too deep
        ]
        for line in bad:
            with self.subTest(line=line):
                code, out, _ = self.mutate("- Test: mapped: `tests/test_widget.py::WidgetTests::test_empty_counts_zero`", line)
                self.assertEqual(code, 1)
                self.assertRule(out, "test-field")

    def test_bad_case_id_rejected(self):
        code, out, _ = self.mutate("#### CORE-01-A1.1A:", "#### CORE-1-A1.1A:")
        self.assertRule(out, "case-id")

    def test_case_of_another_clause_rejected(self):
        code, out, _ = self.mutate("#### CORE-01-A1.1A:", "#### CORE-02-A1.1A:")
        self.assertRule(out, "case-id", "does not belong")

    def test_case_listed_under_wrong_area_rejected(self):
        code, out, _ = self.mutate("#### CORE-01-A1.1A:", "#### CORE-01-A2.1A:")
        self.assertRule(out, "case-area")

    def test_missing_anchor_rejected(self):
        code, out, _ = self.mutate('<a id="core-01-a1-1a"></a>\n', "")
        self.assertRule(out, "anchor-missing", "CORE-01-A1.1A")

    def test_wrong_anchor_rejected(self):
        code, out, _ = self.mutate('<a id="core-01-a1-1a"></a>', '<a id="core-01-a1.1a"></a>')
        self.assertRule(out, "anchor-mismatch")

    def test_area_anchor_required(self):
        self.assertRule(self.mutate('<a id="core-01-a1"></a>\n', "")[1], "anchor-missing", "CORE-01-A1")

    def test_duplicate_case_id_rejected(self):
        code, out, _ = self.mutate("#### CORE-01-A1.1B:", "#### CORE-01-A1.1A:")
        self.assertRule(out, "duplicate-case-id")

    def test_duplicate_case_id_across_clauses_rejected(self):
        # a second clause that re-uses clause 01's case IDs
        clone = CLAUSE.replace("SPEC-CORE-01", "SPEC-CORE-02")
        self.build(**{"docs/spec/clauses/02-other.md": clone})
        self.assertRule(self.cases()[1], "duplicate-case-id", "already used")

    def test_no_cases_without_none_is_a_finding(self):
        start = CLAUSE.index("<a id=\"core-01-a1\"></a>")
        self.build(**{CLAUSE_PATH: CLAUSE[:start].rstrip() + "\n\nTBD\n"})
        self.assertRule(self.cases()[1], "no-cases")

    def test_stray_heading_in_cases_section_rejected(self):
        self.assertRule(self.mutate("<a id=\"core-01-a1-1b\"></a>", "##### Notes\n\n<a id=\"core-01-a1-1b\"></a>")[1], "bad-heading")


class IndexTable(SpecTreeCase):
    def mutate(self, old, new):
        self.build(**{CLAUSE_PATH: self.sub(CLAUSE, old, new)})
        return self.cases()

    def test_missing_row_rejected(self):
        row = "| [CORE-01-A1.1B](01-widget-rules.md#core-01-a1-1b) | The count of two items equals 2. | [`test_two_items`](../../../tests/test_widget.py) |\n"
        self.assertRule(self.mutate(row, "")[1], "index-row-missing", "CORE-01-A1.1B")

    def test_row_for_unknown_case_rejected(self):
        row = "| [CORE-01-A1.1B](01-widget-rules.md#core-01-a1-1b) | The count of two items equals 2. | [`test_two_items`](../../../tests/test_widget.py) |\n"
        self.assertRule(self.mutate(row, row + row.replace("1.1B", "1.1Z").replace("1-1b", "1-1z"))[1], "index-row-unknown")

    def test_duplicate_row_rejected(self):
        row = "| [CORE-01-A1.1B](01-widget-rules.md#core-01-a1-1b) | The count of two items equals 2. | [`test_two_items`](../../../tests/test_widget.py) |\n"
        self.assertRule(self.mutate(row, row + row)[1], "index-row-duplicate")

    def test_row_link_to_wrong_anchor_rejected(self):
        self.assertRule(self.mutate("(01-widget-rules.md#core-01-a1-1b)", "(01-widget-rules.md#core-01-a1-1a)")[1], "index-row-link")

    def test_row_link_to_wrong_file_rejected(self):
        self.assertRule(self.mutate("(01-widget-rules.md#core-01-a1-1b)", "(02-widget-rules.md#core-01-a1-1b)")[1], "index-row-link")

    def test_row_test_link_must_resolve_to_test_file(self):
        self.assertRule(self.mutate("[`test_two_items`](../../../tests/test_widget.py)", "[`test_two_items`](../../tests/test_widget.py)")[1], "index-row-test", "resolves to")

    def test_row_test_label_must_match_selector(self):
        self.assertRule(self.mutate("[`test_two_items`]", "[`test_other`]")[1], "index-row-test", "label")

    def test_row_with_empty_middle_cell_rejected(self):
        self.assertRule(self.mutate("| The count of two items equals 2. |", "|  |")[1], "index-row-format")

    def test_malformed_row_rejected(self):
        self.assertRule(self.mutate("| [CORE-01-A1.1B](01-widget-rules.md#core-01-a1-1b) |", "| CORE-01-A1.1B |")[1], "index-row-format")

    def test_table_header_must_match(self):
        self.assertRule(self.mutate("| Case | What the assertions check | Test |", "| Case | Notes | Test |")[1], "index-table-header")

    def test_table_missing_rejected(self):
        start = CLAUSE.index("| Case | What")
        end = CLAUSE.index('<a id="core-01-a1-1a"></a>')
        self.build(**{CLAUSE_PATH: CLAUSE[:start] + CLAUSE[end:]})
        self.assertRule(self.cases()[1], "index-table-missing")


class ReadmeAndCrossClause(SpecTreeCase):
    def test_clause_missing_from_readme_rejected(self):
        self.build(**{"docs/spec/README.md": "# As-built\n\nno index here\n"})
        self.assertRule(self.cases()[1], "readme-index", "not listed")

    def test_readme_link_to_missing_clause_rejected(self):
        readme = GOOD["docs/spec/README.md"] + "| `SPEC-CORE-09` | [Ghost](clauses/09-ghost.md) | `main` |\n"
        self.build(**{"docs/spec/README.md": readme})
        self.assertRule(self.cases()[1], "readme-index", "does not exist")

    def test_missing_readme_rejected(self):
        self.build(**{"docs/spec/README.md": None})
        self.assertRule(self.cases()[1], "readme-missing")

    def test_mixed_repo_codes_rejected(self):
        pay = (CLAUSE.replace("CORE", "PAY").replace("core", "pay").replace("01-widget-rules", "02-pay-rules")
               .replace("SPEC-PAY-01", "SPEC-PAY-02").replace("PAY-01", "PAY-02").replace("pay-01", "pay-02"))
        self.build(**{
            "docs/spec/clauses/02-pay-rules.md": pay,
            "docs/spec/README.md": GOOD["docs/spec/README.md"] + "| x | [Pay](clauses/02-pay-rules.md) | y |\n",
        })
        self.assertRule(self.cases()[1], "mixed-codes")

    def test_bad_clause_filename_rejected(self):
        self.build(**{CLAUSE_PATH: None, "docs/spec/clauses/Widget_Rules.md": CLAUSE})
        self.assertRule(self.cases()[1], "clause-filename")


class VerifyCommits(SpecTreeCase):
    def init_repo(self):
        env = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        import os
        full = {**os.environ, **env}
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True, env=full)  # noqa: E731
        run("init", "-q")
        (self.root / "f").write_text("x")
        run("add", "f")
        run("commit", "-q", "-m", "init")
        return subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

    def test_unknown_commit_rejected_only_with_flag(self):
        self.build()
        self.init_repo()
        self.assertEqual(self.cases()[0], 0)  # without the flag the header is only shape-checked
        code, out, _ = self.cases("--verify-commits")
        self.assertEqual(code, 1)
        hits = self.assertRule(out, "commit-missing")
        self.assertEqual(len(hits), 2)  # Described at + Also read at

    def test_existing_commit_accepted(self):
        real = self.init_repo()
        text = CLAUSE.replace(SHA, real).replace(OTHER_SHA, real)
        self.build(**{CLAUSE_PATH: text})
        self.assertEqual(self.cases("--verify-commits")[0], 0)

    def test_flag_outside_git_repo_is_exit_2(self):
        self.build()
        code, _, err = self.cases("--verify-commits")
        self.assertEqual(code, 2)
        self.assertIn("git repository", err)


class OutputFormat(SpecTreeCase):
    def test_github_format_is_workflow_command(self):
        self.build(**{CLAUSE_PATH: self.sub(CLAUSE, "Status: DRAFT", "Status: DONE")})
        code, out, _ = self.cases("--format", "github")
        self.assertEqual(code, 1)
        line = [l for l in out if l.startswith("::error")][0]
        self.assertTrue(line.startswith(f"::error file={CLAUSE_PATH},line="))
        self.assertIn("title=header-status::", line)

    def test_text_format_is_path_line_rule_message(self):
        self.build(**{CLAUSE_PATH: self.sub(CLAUSE, "Status: DRAFT", "Status: DONE")})
        out = self.cases()[1]
        self.assertRegex(out[0], rf"^{CLAUSE_PATH}:\d+: header-status: ")
        self.assertRegex(out[-1], r"^spec-cases: 1 clause\(s\), 2 case\(s\), 1 finding\(s\)$")

    def test_script_runs_as_a_command_and_sets_exit_code(self):
        self.build()
        ok = subprocess.run([sys.executable, str(TOOLS / "check_spec_cases.py"), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stderr), (0, ""))
        self.build(**{CLAUSE_PATH: self.sub(CLAUSE, "Status: DRAFT", "Status: DONE")})
        bad = subprocess.run([sys.executable, str(TOOLS / "check_spec_cases.py"), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)


if __name__ == "__main__":
    unittest.main()
