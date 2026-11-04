# SPEC-FRK-02: Asset-bundle resolution in `frappe.require` (refresh of the boot asset map)

<a id="spec-frk-02"></a>

- Stable ID: `SPEC-FRK-02`
- Described at: repo `hybrowlabs/frappe`, branch `operate-v16-release-20260913`, commit `caac3a8a19eb34db47e0487303623b2b8e25ed5e` (committer date `2026-09-13 12:11:15 +0530`)
- Also read at: branch `develop`, commit `c4cabbb11ae052115787866f362454276324e8c3`; differs: it is a 2023-10-27 snapshot of upstream, so every cited file differs from the Described-at commit. `frappe/public/js/frappe/assets.js:8-20` is the upstream `frappe.require` with no refresh step and `bundled_asset` has no leading-slash handling (`frappe/public/js/frappe/assets.js:191-196`); `get_boot_assets_json` is at `frappe/sessions.py:180-181` and `get_assets_json` at `frappe/utils/__init__.py:963`; the other callers sit at `frappe/public/js/frappe/desk.js:85`, `frappe/public/js/frappe/dom.js:376` and `frappe/public/js/frappe/microtemplate.js:172`.
- Author: Developer Agent (Yashwanth). Reviewer: Code Reviewer (Yashwanth).
- Status: DRAFT

## 1. Purpose

The fork's one code change on this branch makes `frappe.require` resolve a logical bundle name (for example `desk.bundle.js`) against a fresh copy of the server's asset map when the page's boot copy has no entry for it, then loads the hashed file (`frappe/public/js/frappe/assets.js:8-61`). The change is one commit, `caac3a8a19` "fix(assets): resolve logical bundles from refreshed v16 boot map", on top of upstream `version-16` tag `v16.33.1` (`988e54f3c4c291e2077a83809663f123731abe76`). Why, as the code comment states it: a stale shared `assets_json` cache can make a valid v16 bundle look like a root-relative file (`frappe/public/js/frappe/assets.js:31-32`). Nothing outside the code was read for the reason.

## 2. Boundaries

- In: `frappe.require` (`frappe/public/js/frappe/assets.js:8-61`), `AssetManager.bundled_asset` (`frappe/public/js/frappe/assets.js:186-196`), and the server method it calls, `frappe.sessions.get_boot_assets_json` (`frappe/sessions.py:192-194`).
- Out: `AssetManager.execute` and the loaders, which this commit does not touch (`frappe/public/js/frappe/assets.js:150-177`); how `assets/assets.json` is produced by the bundler (`frappe/build.py:58-62`); the delta inventory of all three fork branches is `SPEC-FRK-01`.
- Callers: 15 lines in 12 files under `frappe/public/js` contain `frappe.require(`, counted by `grep -rn` at the Described-at commit; one is `frappe/public/js/frappe/desk.js:131`. Two other places call `bundled_asset` (`frappe/public/js/frappe/microtemplate.js:187`, `frappe/public/js/frappe/dom.js:400`).
- Extension points: `frappe.boot.assets_json`, set at page boot from `get_assets_json()` (`frappe/sessions.py:166`), and replaced in full by the build-event handler after a rebuild (`frappe/public/js/frappe/build_events/build_events.bundle.js:28-31`).

## 3. Behaviour rules

### A1: `frappe.require`

- A1.1: When every `.bundle.` name requested is already a key of `frappe.boot.assets_json` (or is not a bundle name), no server call is made and the hashed paths are loaded (`frappe/public/js/frappe/assets.js:14-29`, `frappe/public/js/frappe/assets.js:51-60`). [FRK-02-A1.1A]
- A1.2: When at least one requested name contains `.bundle.`, does not start with `/assets`, and has no key in the map, `frappe.require` calls `frappe.sessions.get_boot_assets_json` once, merges the reply over the existing map (the reply wins on a shared key) and only then resolves and loads every requested item (`frappe/public/js/frappe/assets.js:16-25`, `frappe/public/js/frappe/assets.js:33-41`, `frappe/public/js/frappe/assets.js:51-60`). [FRK-02-A1.2A] [FRK-02-A1.2B]
- A1.3: Concurrent `frappe.require` calls share one in-flight refresh through `frappe._assets_json_refresh`; the field is cleared when the call settles, so a later `frappe.require` of a still-unmapped name calls the server again (`frappe/public/js/frappe/assets.js:33`, `frappe/public/js/frappe/assets.js:44-46`). [FRK-02-A1.3A] [FRK-02-A1.3B]
- A1.4: A failed refresh is swallowed (`.catch(() => {})`), the map stays as it was, and the bundle name is loaded as given, resolved against the site origin; a reply that is not an object is ignored in the same way (`frappe/public/js/frappe/assets.js:36-43`). [FRK-02-A1.4A] [FRK-02-A1.4B]
- A1.5: Only a name that contains `.bundle.` and does not start with `/assets` can trigger a refresh; one leading `/` is removed before the map lookup (`frappe/public/js/frappe/assets.js:17-24`). [FRK-02-A1.5A] [FRK-02-A1.5B]
- A1.6: When `frappe.call` is not a function, no refresh is attempted and the names are loaded as given (`frappe/public/js/frappe/assets.js:27-29`). [FRK-02-A1.6A]

### A2: `bundled_asset`

- A2.1: For a name that contains `.bundle.` and does not start with `/assets`, `bundled_asset` looks up the name with one leading `/` removed and returns the mapped path, or the name unchanged when there is no entry; other names are returned unchanged (`frappe/public/js/frappe/assets.js:186-196`). [FRK-02-A2.1A]
- A2.2: A `.css` name asked for with `is_rtl` is looked up with an `rtl_` prefix (and returned with it when unmapped); a missing `frappe.boot` or `assets_json` does not throw (`frappe/public/js/frappe/assets.js:188-192`). [FRK-02-A2.2A]

### A3: Server method

- A3.1: `get_boot_assets_json` is a `@frappe.whitelist()` function with no arguments that returns `get_assets_json()` (`frappe/sessions.py:192-194`). [FRK-02-A3.1A] `get_assets_json` returns the merged `assets/assets.json` and `assets/assets-rtl.json`, from a shared client cache outside developer mode and re-read from disk in developer mode (`frappe/utils/__init__.py:951-969`).

## 4. Data and permissions

- The method is whitelisted without `allow_guest`, so the framework default applies (a logged-in session) [INFERENCE: the default was not read here] (`frappe/sessions.py:192`).
- The reply is the asset map: logical bundle name to built file path. No user data is in it (`frappe/utils/__init__.py:953-959`).
- The merged map lives only in `frappe.boot.assets_json` in the page; nothing is persisted (`frappe/public/js/frappe/assets.js:37-40`).

## 5. Errors and edge behaviour

- A rejected call is ignored; the page then requests the unhashed logical name, which the server may not serve (`frappe/public/js/frappe/assets.js:43`, `frappe/public/js/frappe/assets.js:191-193`). What the server answers for it was not read.
- `frappe.require` now always returns a promise that waits for the refresh step first, even when no refresh is needed (`frappe/public/js/frappe/assets.js:51`). The `callback` still runs after the load (`frappe/public/js/frappe/assets.js:55-58`).

## 6. Configuration

- `developer_mode` only changes where `get_assets_json` reads from (`frappe/utils/__init__.py:961-969`). The browser side has no setting.

## 7. Scheduled jobs, hooks and patches

- None. No hook, scheduler event or patch is touched by the delta.

## 8. Static security and performance observations

- Security: the refresh sends no argument and trusts the reply's keys and values as script and stylesheet locations; a path in the reply is loaded as is (`frappe/public/js/frappe/assets.js:37-40`, `frappe/public/js/frappe/assets.js:67-75`). The server side only reads two files from `assets/` (`frappe/utils/__init__.py:953-959`). Not assessed beyond this; no severity rating.
- Performance: one extra POST to `frappe.sessions.get_boot_assets_json` for each `frappe.require` that names an unmapped bundle, and the result is not remembered when the reply still lacks the name, so every later `frappe.require` of that name repeats the call (`frappe/public/js/frappe/assets.js:33`, `frappe/public/js/frappe/assets.js:44-46`; case FRK-02-A1.3B). Every `frappe.require` also waits one promise tick before it starts loading (`frappe/public/js/frappe/assets.js:51`). Issue: not filed: no measurement, and it is a design question for the fork owner.

## 9. Known gaps / open questions

- G1: The build-event handler replaces `frappe.boot.assets_json` with the whole reply, while `frappe.require` merges it, so the two paths treat an entry missing from a later reply differently (`frappe/public/js/frappe/build_events/build_events.bundle.js:28-31`, `frappe/public/js/frappe/assets.js:37-40`). Question: is the difference intended? Issue: not filed: observation only, no wrong result shown.
- G2: A bundle name that the map will never contain (a typo, or a file outside `assets.json`) costs one server call on every `frappe.require` of it (case FRK-02-A1.3B). Issue: not filed: see Performance.
- G3: Upstream `version-16` (`3d1284c5fdb52207a516a49bbf2fd186cb43b3ab`) and `develop` (`bb1630488e0be316f24c73dd7e07a51661e07265`) have no `requested_items` or `_assets_json_refresh` in `assets.js`, counted by `grep -c` of `git show`; the delta is not upstream as of 2026-11-04. Not a defect; a fact for anyone who merges upstream into this branch: the conflict is in `assets.js` only.
- G4: The tests use a stand-in for `document` and `frappe.call`; whether a real browser orders script loads the same way was not run (cases list it).
- Statutory source: not applicable; no tax, leave or attendance rule is stated here.

## 10. Uncovered behaviour

- Real script and stylesheet loading, `frappe.dom.freeze` and the order in which a browser executes the scripts: needs a browser. Not filed: no browser runner for this repo in this PR.
- What the server answers for an unhashed `/desk.bundle.js` request after a failed refresh (A1.4): needs a bench and a built `assets/`. Not filed: no bench (PWHR-1272).
- That `get_boot_assets_json` is reachable by a logged-in user only and returns the real `assets.json`: needs a bench. Not filed: no bench (PWHR-1272). Case FRK-02-A3.1A pins the function's shape, not its runtime result.
- The build-event path (G1): it runs inside a Vue bundle with imports and has no stand-in here. Not filed: static observation only.

## 11. Acceptance cases

<a id="frk-02-a1"></a>
### FRK-02-A1: `frappe.require`

| Case | What the assertions check | Test |
|---|---|---|
| [FRK-02-A1.1A](02-asset-bundle-resolution.md#frk-02-a1-1a) | No refresh call, and one script load whose URL is the site origin plus the mapped hashed path. | [`RequireTests.test_a_bundle_already_in_the_boot_map_loads_its_hashed_file_without_any_server_call`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.2A](02-asset-bundle-resolution.md#frk-02-a1-2a) | One call to the named method, the map holds both entries afterwards, and both hashed files load in request order. | [`RequireTests.test_an_unresolved_bundle_makes_one_refresh_call_merges_the_reply_and_then_loads_the_hashed_file`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.2B](02-asset-bundle-resolution.md#frk-02-a1-2b) | The reply's value replaces the page's value for a shared key, and the replaced path is the one loaded. | [`RequireTests.test_the_refresh_reply_overwrites_an_entry_the_page_already_had_for_the_same_logical_name`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.3A](02-asset-bundle-resolution.md#frk-02-a1-3a) | Two overlapping requires make exactly one server call and both hashed files load. | [`RequireTests.test_two_overlapping_requires_share_one_refresh_call`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.3B](02-asset-bundle-resolution.md#frk-02-a1-3b) | Two sequential requires of an unmapped name make two server calls and load the logical name both times. | [`RequireTests.test_a_later_require_after_the_refresh_settled_calls_the_server_again_while_the_bundle_stays_unresolved`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.4A](02-asset-bundle-resolution.md#frk-02-a1-4a) | A rejected call leaves the map empty, one call was made and the logical name is loaded from the site origin. | [`RequireTests.test_a_failed_refresh_is_swallowed_and_the_bundle_loads_from_its_root_relative_logical_path`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.4B](02-asset-bundle-resolution.md#frk-02-a1-4b) | A string reply leaves the map unchanged and the unmapped name loads as given. | [`RequireTests.test_a_reply_that_is_not_an_object_leaves_the_boot_map_unchanged`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.5A](02-asset-bundle-resolution.md#frk-02-a1-5a) | An `/assets/...bundle...` path, a plain file and a plain stylesheet make no server call although the map is empty. | [`RequireTests.test_only_a_non_assets_dot_bundle_name_missing_from_the_map_triggers_a_refresh`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.5B](02-asset-bundle-resolution.md#frk-02-a1-5b) | A leading `/` on a mapped name makes no server call and loads the mapped path. | [`RequireTests.test_a_leading_slash_on_the_requested_name_is_ignored_when_the_map_is_checked`](../../../tests/test_frk_assets.py) |
| [FRK-02-A1.6A](02-asset-bundle-resolution.md#frk-02-a1-6a) | With no `frappe.call`, no call is recorded and the logical name loads. | [`RequireTests.test_without_frappe_call_no_refresh_is_attempted_and_the_logical_path_is_loaded`](../../../tests/test_frk_assets.py) |

<a id="frk-02-a1-1a"></a>
#### FRK-02-A1.1A: A bundle already in the boot map loads its hashed file without a server call

- Precondition: `frappe.boot.assets_json` maps `desk.bundle.js` to a hashed path; `frappe.call` is a recording stub.
- Action: Run the real `frappe.require("desk.bundle.js")` and wait for it.
- Expected result: No call is recorded; one script element is appended with the site origin plus the hashed path. `frappe/public/js/frappe/assets.js:14-29`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_a_bundle_already_in_the_boot_map_loads_its_hashed_file_without_any_server_call`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: `document` and `frappe.call` are stand-ins; no script is fetched or executed.
- Evidence: UNVERIFIED

<a id="frk-02-a1-2a"></a>
#### FRK-02-A1.2A: An unresolved bundle triggers one refresh, a merge and then the load

- Precondition: The map holds `desk.bundle.js` only; the stubbed server reply holds `form.bundle.js`.
- Action: Run `frappe.require(["desk.bundle.js", "form.bundle.js"])`.
- Expected result: One call to `frappe.sessions.get_boot_assets_json`; the map then holds both entries; both hashed files load in request order. `frappe/public/js/frappe/assets.js:33-41`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_an_unresolved_bundle_makes_one_refresh_call_merges_the_reply_and_then_loads_the_hashed_file`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: The reply is a stub; the real method and its cache are not run.
- Evidence: UNVERIFIED

<a id="frk-02-a1-2b"></a>
#### FRK-02-A1.2B: The refresh reply wins over the page's own entry

- Precondition: The map holds `desk.bundle.js` with an old hash; the reply holds a new hash for it and one more name.
- Action: Run `frappe.require(["x.bundle.js", "desk.bundle.js"])`.
- Expected result: The map holds the new hash for `desk.bundle.js` and the new name; the new hash is loaded. `frappe/public/js/frappe/assets.js:37-40`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_the_refresh_reply_overwrites_an_entry_the_page_already_had_for_the_same_logical_name`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: Whether an old hash can really be newer than the server's is not shown.
- Evidence: UNVERIFIED

<a id="frk-02-a1-3a"></a>
#### FRK-02-A1.3A: Overlapping requires share one refresh

- Precondition: The map is empty; the reply holds two bundles.
- Action: Start `frappe.require("desk.bundle.js")` and `frappe.require("form.bundle.js")` together and wait for both.
- Expected result: Exactly one server call; both hashed files load. `frappe/public/js/frappe/assets.js:33`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_two_overlapping_requires_share_one_refresh_call`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: Timing is the promise queue of Node, not a browser's network.
- Evidence: UNVERIFIED

<a id="frk-02-a1-3b"></a>
#### FRK-02-A1.3B: A later require repeats the call while the name stays unmapped

- Precondition: The map is empty; the reply is an empty object.
- Action: Run `frappe.require("missing.bundle.js")` twice in sequence.
- Expected result: Two server calls; the logical name is loaded from the site origin. `frappe/public/js/frappe/assets.js:44-46`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_a_later_require_after_the_refresh_settled_calls_the_server_again_while_the_bundle_stays_unresolved`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: The asserted load list shows one entry because the second load of the same path is skipped by `_executed`; that skip belongs to code this delta does not change (`frappe/public/js/frappe/assets.js:138-141`).
- Evidence: UNVERIFIED

<a id="frk-02-a1-4a"></a>
#### FRK-02-A1.4A: A failed refresh is swallowed

- Precondition: `frappe.call` returns a rejected promise; the map is empty.
- Action: Run `frappe.require("desk.bundle.js")`.
- Expected result: The promise resolves; one call was made; the logical name loads from the site origin; the map is still empty. `frappe/public/js/frappe/assets.js:43`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_a_failed_refresh_is_swallowed_and_the_bundle_loads_from_its_root_relative_logical_path`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: No error is shown to the user in the code; the test does not check for logging because the code does not log.
- Evidence: UNVERIFIED

<a id="frk-02-a1-4b"></a>
#### FRK-02-A1.4B: A reply that is not an object is ignored

- Precondition: The map holds `desk.bundle.js`; the reply `message` is a string.
- Action: Run `frappe.require("form.bundle.js")`.
- Expected result: The map is unchanged; `form.bundle.js` loads as given. `frappe/public/js/frappe/assets.js:36-41`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_a_reply_that_is_not_an_object_leaves_the_boot_map_unchanged`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: An array reply (an object in JavaScript) is not exercised.
- Evidence: UNVERIFIED

<a id="frk-02-a1-5a"></a>
#### FRK-02-A1.5A: Only non-`/assets` bundle names trigger a refresh

- Precondition: The map is empty.
- Action: Run `frappe.require` with `/assets/frappe/dist/js/x.bundle.AAA.js`, `lib/plain.js` and `/assets/css/plain.css`.
- Expected result: No server call; three files are loaded. `frappe/public/js/frappe/assets.js:16-25`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_only_a_non_assets_dot_bundle_name_missing_from_the_map_triggers_a_refresh`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: The positive side (a `.bundle.` name with no `/assets` prefix triggers) is shown by FRK-02-A1.2A.
- Evidence: UNVERIFIED

<a id="frk-02-a1-5b"></a>
#### FRK-02-A1.5B: One leading slash is ignored for the map check

- Precondition: The map holds `desk.bundle.js`.
- Action: Run `frappe.require("/desk.bundle.js")`.
- Expected result: No server call; the mapped hashed path loads. `frappe/public/js/frappe/assets.js:18`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_a_leading_slash_on_the_requested_name_is_ignored_when_the_map_is_checked`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: A name with two leading slashes is not exercised.
- Evidence: UNVERIFIED

<a id="frk-02-a1-6a"></a>
#### FRK-02-A1.6A: Without `frappe.call` no refresh is attempted

- Precondition: `frappe.call` is not defined; the map is empty.
- Action: Run `frappe.require("desk.bundle.js")`.
- Expected result: No call; the logical name loads from the site origin. `frappe/public/js/frappe/assets.js:27-29`
- Test: characterization: `tests/test_frk_assets.py::RequireTests::test_without_frappe_call_no_refresh_is_attempted_and_the_logical_path_is_loaded`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: None known.
- Evidence: UNVERIFIED

<a id="frk-02-a2"></a>
### FRK-02-A2: `bundled_asset`

| Case | What the assertions check | Test |
|---|---|---|
| [FRK-02-A2.1A](02-asset-bundle-resolution.md#frk-02-a2-1a) | A mapped name with and without a leading slash gives the mapped path; an unmapped bundle, a non-bundle and an `/assets` path come back unchanged. | [`BundledAssetTests.test_bundled_asset_looks_up_the_name_without_its_leading_slash_and_returns_unmapped_names_unchanged`](../../../tests/test_frk_assets.py) |
| [FRK-02-A2.2A](02-asset-bundle-resolution.md#frk-02-a2-2a) | The `rtl_`-prefixed key is used for a stylesheet bundle, an unmapped one returns with the prefix, and a missing boot object returns the name. | [`BundledAssetTests.test_bundled_asset_prefixes_a_stylesheet_bundle_with_rtl_when_asked_and_survives_a_missing_boot_object`](../../../tests/test_frk_assets.py) |

<a id="frk-02-a2-1a"></a>
#### FRK-02-A2.1A: `bundled_asset` looks the name up without its leading slash

- Precondition: The map holds `desk.bundle.js`.
- Action: Call `bundled_asset` with `desk.bundle.js`, `/desk.bundle.js`, `/other.bundle.js`, `lib/plain.js` and `/assets/frappe/dist/js/desk.bundle.js`.
- Expected result: The first two return the mapped path; the other three come back unchanged. `frappe/public/js/frappe/assets.js:186-196`
- Test: characterization: `tests/test_frk_assets.py::BundledAssetTests::test_bundled_asset_looks_up_the_name_without_its_leading_slash_and_returns_unmapped_names_unchanged`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: `frappe.boot` is a plain object here, not the real boot payload.
- Evidence: UNVERIFIED

<a id="frk-02-a2-2a"></a>
#### FRK-02-A2.2A: A stylesheet bundle asked for as right-to-left uses the `rtl_` key

- Precondition: The map holds `rtl_desk.bundle.css`; a second harness has no `frappe.boot`.
- Action: Call `bundled_asset("desk.bundle.css", true)`, `bundled_asset("other.bundle.css", true)`, and on the second harness `bundled_asset("desk.bundle.js")`.
- Expected result: The mapped RTL path; `rtl_other.bundle.css`; `desk.bundle.js` with no exception. `frappe/public/js/frappe/assets.js:188-192`
- Test: characterization: `tests/test_frk_assets.py::BundledAssetTests::test_bundled_asset_prefixes_a_stylesheet_bundle_with_rtl_when_asked_and_survives_a_missing_boot_object`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: The `rtl_` prefix on an unmapped name is arguably an unusable URL; the test pins it, it does not endorse it.
- Evidence: UNVERIFIED

<a id="frk-02-a3"></a>
### FRK-02-A3: Server method

| Case | What the assertions check | Test |
|---|---|---|
| [FRK-02-A3.1A](02-asset-bundle-resolution.md#frk-02-a3-1a) | One top-level function of that name, decorated `frappe.whitelist()`, no arguments, body `return get_assets_json()`. | [`ServerMethodTests.test_get_boot_assets_json_is_a_plain_whitelisted_function_that_returns_the_assets_map`](../../../tests/test_frk_assets.py) |

<a id="frk-02-a3-1a"></a>
#### FRK-02-A3.1A: `get_boot_assets_json` is a whitelisted wrapper around `get_assets_json`

- Precondition: The source file `frappe/sessions.py` is parsed, not imported.
- Action: Find the top-level function `get_boot_assets_json` in the syntax tree.
- Expected result: One such function, decorated `frappe.whitelist()`, no parameters, one statement `return get_assets_json()`. `frappe/sessions.py:192-194`
- Test: characterization: `tests/test_frk_assets.py::ServerMethodTests::test_get_boot_assets_json_is_a_plain_whitelisted_function_that_returns_the_assets_map`
- Environment: no-site: unittest, frappe stubbed; no database
- Known gaps: A syntax-tree test: it shows the shape, not that the method returns the real map or who may call it (Uncovered behaviour).
- Evidence: UNVERIFIED
