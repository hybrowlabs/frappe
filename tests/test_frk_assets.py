"""No-site characterization tests for the fork's asset-bundle resolution (``frappe/public/js/frappe/assets.js``) and the
server method it calls (``frappe/sessions.py``).

Two kinds of test live here:

* behaviour tests run the real, unchanged ``assets.js`` under Node in ``tests/js/assets_harness.js``, a ``vm`` context
  whose ``frappe``, ``window`` and ``document`` are recording stand-ins. No browser, no Frappe server, no network.
  Node (18 or later) must be on ``PATH``; a missing Node makes these tests fail, never skip;
* one static test parses ``frappe/sessions.py`` with ``ast`` and does not import it.

Run from the repo root: ``python3 -m unittest tests.test_frk_assets`` (standard library only).
Synthetic values only (``example.invalid``).
"""
import ast
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "js" / "assets_harness.js"
SESSIONS_PY = ROOT / "frappe" / "sessions.py"

SPEC = "docs/spec/clauses/02-asset-bundle-resolution.md"
CHARACTERIZATION = "Characterization: pins current behaviour, not endorsed."

DESK_MAP = {"desk.bundle.js": "/assets/frappe/dist/js/desk.bundle.AAA.js"}
FORM_MAP = {"form.bundle.js": "/assets/frappe/dist/js/form.bundle.BBB.js"}
SITE = "https://site.example.invalid"


def run_js(body):
    """Run ``body`` as the body of ``async (h) => {...}`` inside the harness and return the JSON it returns."""
    proc = subprocess.run(
        ["node", str(HARNESS)], input=body, capture_output=True, text=True, cwd=str(ROOT), timeout=120
    )
    if proc.returncode != 0:
        raise AssertionError(f"harness failed ({proc.returncode}): {proc.stderr[-1500:]}")
    return json.loads(proc.stdout)


def js_literal(value):
    return json.dumps(value)


class RequireTests(unittest.TestCase):
    def test_a_bundle_already_in_the_boot_map_loads_its_hashed_file_without_any_server_call(self):
        """Spec: FRK-02-A1.1A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-1a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{assetsJson: {js_literal(DESK_MAP)}}});
            await e.frappe.require("desk.bundle.js");
            return {{calls: e.calls, loaded: e.loaded}};
            """
        )
        self.assertEqual(out["calls"], [])
        self.assertEqual(out["loaded"], [{"tag": "script", "url": SITE + DESK_MAP["desk.bundle.js"]}])

    def test_an_unresolved_bundle_makes_one_refresh_call_merges_the_reply_and_then_loads_the_hashed_file(self):
        """Spec: FRK-02-A1.2A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-2a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{assetsJson: {js_literal(DESK_MAP)}, callResponse: {js_literal(FORM_MAP)}}});
            await e.frappe.require(["desk.bundle.js", "form.bundle.js"]);
            return {{calls: e.calls, loaded: e.loaded, boot: e.frappe.boot.assets_json}};
            """
        )
        self.assertEqual(out["calls"], ["frappe.sessions.get_boot_assets_json"])
        self.assertEqual(out["boot"], {**DESK_MAP, **FORM_MAP})
        self.assertEqual(
            [item["url"] for item in out["loaded"]],
            [SITE + DESK_MAP["desk.bundle.js"], SITE + FORM_MAP["form.bundle.js"]],
        )

    def test_the_refresh_reply_overwrites_an_entry_the_page_already_had_for_the_same_logical_name(self):
        """Spec: FRK-02-A1.2B (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-2b)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{
              assetsJson: {{"desk.bundle.js": "/assets/frappe/dist/js/desk.bundle.OLD.js"}},
              callResponse: {{"desk.bundle.js": "/assets/frappe/dist/js/desk.bundle.NEW.js", "x.bundle.js": "/assets/x.js"}},
            }});
            await e.frappe.require(["x.bundle.js", "desk.bundle.js"]);
            return {{boot: e.frappe.boot.assets_json, loaded: e.loaded}};
            """
        )
        self.assertEqual(out["boot"]["desk.bundle.js"], "/assets/frappe/dist/js/desk.bundle.NEW.js")
        self.assertEqual(out["boot"]["x.bundle.js"], "/assets/x.js")
        self.assertEqual(out["loaded"][1]["url"], SITE + "/assets/frappe/dist/js/desk.bundle.NEW.js")

    def test_two_overlapping_requires_share_one_refresh_call(self):
        """Spec: FRK-02-A1.3A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-3a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{assetsJson: {{}}, callResponse: {js_literal({**DESK_MAP, **FORM_MAP})}}});
            await Promise.all([e.frappe.require("desk.bundle.js"), e.frappe.require("form.bundle.js")]);
            return {{calls: e.calls, loaded: e.loaded.map((x) => x.url)}};
            """
        )
        self.assertEqual(out["calls"], ["frappe.sessions.get_boot_assets_json"])
        self.assertEqual(
            sorted(out["loaded"]),
            sorted([SITE + DESK_MAP["desk.bundle.js"], SITE + FORM_MAP["form.bundle.js"]]),
        )

    def test_a_later_require_after_the_refresh_settled_calls_the_server_again_while_the_bundle_stays_unresolved(self):
        """Spec: FRK-02-A1.3B (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-3b)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            """
            const e = h.build({assetsJson: {}, callResponse: {}});
            await e.frappe.require("missing.bundle.js");
            await e.frappe.require("missing.bundle.js");
            return {calls: e.calls, loaded: e.loaded.map((x) => x.url)};
            """
        )
        self.assertEqual(out["calls"], ["frappe.sessions.get_boot_assets_json"] * 2)
        self.assertEqual(out["loaded"], [SITE + "/missing.bundle.js"])

    def test_a_failed_refresh_is_swallowed_and_the_bundle_loads_from_its_root_relative_logical_path(self):
        """Spec: FRK-02-A1.4A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-4a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            """
            const e = h.build({assetsJson: {}, callImpl: () => Promise.reject(new Error("offline"))});
            await e.frappe.require("desk.bundle.js");
            return {calls: e.calls, loaded: e.loaded.map((x) => x.url), boot: e.frappe.boot.assets_json};
            """
        )
        self.assertEqual(out["calls"], ["frappe.sessions.get_boot_assets_json"])
        self.assertEqual(out["loaded"], [SITE + "/desk.bundle.js"])
        self.assertEqual(out["boot"], {})

    def test_a_reply_that_is_not_an_object_leaves_the_boot_map_unchanged(self):
        """Spec: FRK-02-A1.4B (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-4b)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{assetsJson: {js_literal(DESK_MAP)}, callResponse: "not-an-object"}});
            await e.frappe.require("form.bundle.js");
            return {{boot: e.frappe.boot.assets_json, loaded: e.loaded.map((x) => x.url)}};
            """
        )
        self.assertEqual(out["boot"], DESK_MAP)
        self.assertEqual(out["loaded"], [SITE + "/form.bundle.js"])

    def test_only_a_non_assets_dot_bundle_name_missing_from_the_map_triggers_a_refresh(self):
        """Spec: FRK-02-A1.5A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-5a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            """
            const e = h.build({assetsJson: {}, callResponse: {}});
            await e.frappe.require(["/assets/frappe/dist/js/x.bundle.AAA.js", "lib/plain.js", "/assets/css/plain.css"]);
            return {calls: e.calls, loaded: e.loaded.map((x) => x.url)};
            """
        )
        self.assertEqual(out["calls"], [])
        self.assertEqual(len(out["loaded"]), 3)

    def test_a_leading_slash_on_the_requested_name_is_ignored_when_the_map_is_checked(self):
        """Spec: FRK-02-A1.5B (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-5b)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{assetsJson: {js_literal(DESK_MAP)}}});
            await e.frappe.require("/desk.bundle.js");
            return {{calls: e.calls, loaded: e.loaded.map((x) => x.url)}};
            """
        )
        self.assertEqual(out["calls"], [])
        self.assertEqual(out["loaded"], [SITE + DESK_MAP["desk.bundle.js"]])

    def test_without_frappe_call_no_refresh_is_attempted_and_the_logical_path_is_loaded(self):
        """Spec: FRK-02-A1.6A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a1-6a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            """
            const e = h.build({assetsJson: {}, noCall: true});
            await e.frappe.require("desk.bundle.js");
            return {calls: e.calls, loaded: e.loaded.map((x) => x.url)};
            """
        )
        self.assertEqual(out["calls"], [])
        self.assertEqual(out["loaded"], [SITE + "/desk.bundle.js"])


class BundledAssetTests(unittest.TestCase):
    def test_bundled_asset_looks_up_the_name_without_its_leading_slash_and_returns_unmapped_names_unchanged(self):
        """Spec: FRK-02-A2.1A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a2-1a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            f"""
            const e = h.build({{assetsJson: {js_literal(DESK_MAP)}}});
            const a = e.frappe.assets;
            return {{
              plain: a.bundled_asset("desk.bundle.js"),
              slash: a.bundled_asset("/desk.bundle.js"),
              unmapped: a.bundled_asset("/other.bundle.js"),
              not_a_bundle: a.bundled_asset("lib/plain.js"),
              absolute: a.bundled_asset("/assets/frappe/dist/js/desk.bundle.js"),
            }};
            """
        )
        self.assertEqual(out["plain"], DESK_MAP["desk.bundle.js"])
        self.assertEqual(out["slash"], DESK_MAP["desk.bundle.js"])
        self.assertEqual(out["unmapped"], "/other.bundle.js")
        self.assertEqual(out["not_a_bundle"], "lib/plain.js")
        self.assertEqual(out["absolute"], "/assets/frappe/dist/js/desk.bundle.js")

    def test_bundled_asset_prefixes_a_stylesheet_bundle_with_rtl_when_asked_and_survives_a_missing_boot_object(self):
        """Spec: FRK-02-A2.2A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a2-2a)

        Characterization: pins current behaviour, not endorsed.
        """
        out = run_js(
            """
            const e = h.build({assetsJson: {"rtl_desk.bundle.css": "/assets/frappe/dist/css-rtl/desk.RTL.css"}});
            const a = e.frappe.assets;
            const rtl = a.bundled_asset("desk.bundle.css", true);
            const rtl_unmapped = a.bundled_asset("other.bundle.css", true);
            const no_boot = h.build({noBoot: true}).frappe.assets.bundled_asset("desk.bundle.js");
            return {rtl, rtl_unmapped, no_boot};
            """
        )
        self.assertEqual(out["rtl"], "/assets/frappe/dist/css-rtl/desk.RTL.css")
        self.assertEqual(out["rtl_unmapped"], "rtl_other.bundle.css")
        self.assertEqual(out["no_boot"], "desk.bundle.js")


class ServerMethodTests(unittest.TestCase):
    def test_get_boot_assets_json_is_a_plain_whitelisted_function_that_returns_the_assets_map(self):
        """Spec: FRK-02-A3.1A (docs/spec/clauses/02-asset-bundle-resolution.md#frk-02-a3-1a)

        Characterization: pins current behaviour, not endorsed.
        """
        tree = ast.parse(SESSIONS_PY.read_text(encoding="utf-8"))
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_boot_assets_json"]
        self.assertEqual(len(funcs), 1)
        fn = funcs[0]
        self.assertEqual([ast.unparse(d) for d in fn.decorator_list], ["frappe.whitelist()"])
        self.assertEqual(len(fn.body), 1)
        self.assertEqual(ast.unparse(fn.body[0]), "return get_assets_json()")
        self.assertEqual(fn.args.args, [])


if __name__ == "__main__":
    unittest.main()
