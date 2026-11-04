<!--
One case. Exactly these seven fields, in this order. No other field or loose text.
Copy under "## 11. Acceptance cases" of a clause. Rules: docs/spec/acceptance-cases.md.
-->
<a id="<code>-nn-a<k>-<n><l>"></a>
#### <CODE>-NN-A<k>.<n><L>: <Short title in plain words>

- Precondition: <the state before the action>
- Action: <what is done; one behaviour>
- Expected result: <what must be true afterwards, as the code does it now; citation `path.py:12`>
- Test: <mapped|characterization>: `<path/from/repo/root.py>::<ClassName>::<test_method>`
- Environment: <no-site: unittest, frappe stubbed; no database | bench: Frappe <ver>, <DB>, apps <list>, site <synthetic>>
- Known gaps: <what the assertions do not check, or "None known.">
- Evidence: UNVERIFIED

<!--
Test docstring (Python), one line per case the test covers, exact path:
    """Spec: <CODE>-NN-A<k>.<n><L> (docs/spec/clauses/NN-name.md#<code>-nn-a<k>-<n><l>)"""
A characterization test adds:
    Characterization: pins current behaviour, not endorsed.
Index row (area table in the clause) and a row in docs/spec/test-traceability.md.
Evidence receipt forms (only after a real run, bound to a commit):
    local; <command>; exit N; P passed, F failed, S skipped; commit <40 hex>; env <...>
    ci; <command>; exit N; P passed, F failed, S skipped; commit <40 hex>; env <...>; run <id>
-->
