# Test traceability index

This file is an **index only**. It is not the behaviour specification. The behaviour of each tested rule is an acceptance case in its clause file; the rules for cases are in [acceptance-cases.md](acceptance-cases.md). Results are in PR evidence, not here.

Each row links both ways: spec to test by a relative link, and test to spec by the `Spec: <ID> (path#anchor)` docstring line. A link is not coverage and not a pass.

## Cases

| Case | Clause | Test kind | Test | Evidence |
|---|---|---|---|---|
| [FRK-02-A1.1A](clauses/02-asset-bundle-resolution.md#frk-02-a1-1a) | `SPEC-FRK-02` | characterization | [`RequireTests.test_a_bundle_already_in_the_boot_map_loads_its_hashed_file_without_any_server_call`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.2A](clauses/02-asset-bundle-resolution.md#frk-02-a1-2a) | `SPEC-FRK-02` | characterization | [`RequireTests.test_an_unresolved_bundle_makes_one_refresh_call_merges_the_reply_and_then_loads_the_hashed_file`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.2B](clauses/02-asset-bundle-resolution.md#frk-02-a1-2b) | `SPEC-FRK-02` | characterization | [`RequireTests.test_the_refresh_reply_overwrites_an_entry_the_page_already_had_for_the_same_logical_name`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.3A](clauses/02-asset-bundle-resolution.md#frk-02-a1-3a) | `SPEC-FRK-02` | characterization | [`RequireTests.test_two_overlapping_requires_share_one_refresh_call`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.3B](clauses/02-asset-bundle-resolution.md#frk-02-a1-3b) | `SPEC-FRK-02` | characterization | [`RequireTests.test_a_later_require_after_the_refresh_settled_calls_the_server_again_while_the_bundle_stays_unresolved`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.4A](clauses/02-asset-bundle-resolution.md#frk-02-a1-4a) | `SPEC-FRK-02` | characterization | [`RequireTests.test_a_failed_refresh_is_swallowed_and_the_bundle_loads_from_its_root_relative_logical_path`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.4B](clauses/02-asset-bundle-resolution.md#frk-02-a1-4b) | `SPEC-FRK-02` | characterization | [`RequireTests.test_a_reply_that_is_not_an_object_leaves_the_boot_map_unchanged`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.5A](clauses/02-asset-bundle-resolution.md#frk-02-a1-5a) | `SPEC-FRK-02` | characterization | [`RequireTests.test_only_a_non_assets_dot_bundle_name_missing_from_the_map_triggers_a_refresh`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.5B](clauses/02-asset-bundle-resolution.md#frk-02-a1-5b) | `SPEC-FRK-02` | characterization | [`RequireTests.test_a_leading_slash_on_the_requested_name_is_ignored_when_the_map_is_checked`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A1.6A](clauses/02-asset-bundle-resolution.md#frk-02-a1-6a) | `SPEC-FRK-02` | characterization | [`RequireTests.test_without_frappe_call_no_refresh_is_attempted_and_the_logical_path_is_loaded`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A2.1A](clauses/02-asset-bundle-resolution.md#frk-02-a2-1a) | `SPEC-FRK-02` | characterization | [`BundledAssetTests.test_bundled_asset_looks_up_the_name_without_its_leading_slash_and_returns_unmapped_names_unchanged`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A2.2A](clauses/02-asset-bundle-resolution.md#frk-02-a2-2a) | `SPEC-FRK-02` | characterization | [`BundledAssetTests.test_bundled_asset_prefixes_a_stylesheet_bundle_with_rtl_when_asked_and_survives_a_missing_boot_object`](../../tests/test_frk_assets.py) | UNVERIFIED |
| [FRK-02-A3.1A](clauses/02-asset-bundle-resolution.md#frk-02-a3-1a) | `SPEC-FRK-02` | characterization | [`ServerMethodTests.test_get_boot_assets_json_is_a_plain_whitelisted_function_that_returns_the_assets_map`](../../tests/test_frk_assets.py) | UNVERIFIED |

## Uncovered behaviour

### SPEC-FRK-01

- SPEC-FRK-01: every rule (branch heads, ancestry, commit counts, diffstat) — reason: statements about git history, not runtime behaviour; a test needs the full upstream history, which a shallow checkout lacks — not filed: recomputed by the reviewer with `git`; no case is written (clause section 11 is `None.`).
- SPEC-FRK-01: `frappe/templates/base.html` viewport line on `fix-zoom-on-ios-safari-devices` — reason: unmerged branch, not the tree any test here runs against — not filed: clause G1.

### SPEC-FRK-02

- SPEC-FRK-02: real script and stylesheet loading, `frappe.dom.freeze`, and browser execution order — reason: needs a browser; `document` is a stand-in in `tests/js/assets_harness.js` — not filed: no browser runner in this PR.
- SPEC-FRK-02: what the server answers for an unhashed bundle request after a failed refresh, and that `get_boot_assets_json` returns the real `assets.json` to a logged-in user only — reason: needs a bench with a built `assets/` — not filed: no bench (PWHR-1272).
- SPEC-FRK-02: the build-event handler's replacement of `frappe.boot.assets_json` (`frappe/public/js/frappe/build_events/build_events.bundle.js:28-31`) — reason: runs inside a Vue bundle with imports, no stand-in here — not filed: clause G1.

## Retired IDs

None.
