# F39 original-unit regression harness correction — UNRUN

Development checkpoint only. F39/F36/F37 remain nonterminal; F41 is locked.
Scope remains2025-current; standalone2024 and provider calls remain excluded.
Parent: `262f6cfb476b0e86bf89e563318dbeb50575190b`.
Branch: `codex/f39-unit-replay-tests-v1`.

The actual complete26 diagnostic at
`/home/bctc/codex-runs/f39-original-unit-diagnostic-20261028-v1`
finished15PASS/11FAIL, pytest exit1, with valid source-before/after proof.
The failed run remains unchanged. It is not full-F39 acceptance.

This test-only correction uses the real indexed-query/trial replay API,
`validate_gemini_json_income_tax_replay_v1`. The previous helper named a
nonexistent candidate-only API. Tamper cases now change a resealed candidate
inside actual trials and require the exact family-typed trial-replay error.

The observation audit traverses every nested retained source-control mapping.
Whole-candidate counts therefore differ from financial-export counts. Tests
now audit the complete candidate, the financial vector and retained controls
separately, require all audits to pass, bind the financial count to the export
vector and require the two disjoint audit counts to add to the whole count.

BAB original raw input must remain READY, with identical financial mappings
before/after the unit guard and unchanged source records. EIB has the actual
pre-existing `SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS`
financial hold. The public wrapper returns non-READY candidates before the
unit guard. The pre-guard evaluator body at262f is byte-identical to the public
evaluator at `161c08c515e7823a57638a46924782f3e6dc4441` after its sole function
rename (LF/trimmed-tail normalized SHA-256:
`99fc807c9f7349cd615a66ec767975f810d4730e3b2263fe0dcd67296d12ea53`).
The EIB test requires that exact old reason, zero financial mappings,
byte-identical public/pre-guard candidate and guard no-op; it does not edit raw
units, signs or values to create READY. A fresh execution of these assertions
is still required.

Only this dedicated test module and this note changed. Production, shared
frozen files, the older311-case module, query-axis tests, all four original
raw page fixtures and their provenance remain unchanged. The collection
function/parameter axis remains26 normal nodes; no skip/xfail was added.

Source-only authoring: no Python, import, AST, WSL process, tests, database,
PDF, provider, commit or push executed by the author. Root must review/capture
then run a fresh complete26 gate, actual full311/query13 regression and the
remaining current F39 gates before any acceptance or seal.
