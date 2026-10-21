# F39 printed recognition and tax effect checkpoint

This is a non-terminal Family 39 checkpoint, on `codex/f39-income-tax-laptop`, descending from `b2ad88ff013eb024650c4e7cbebfe3c799143e64` and migration base `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.

Production scope remains source reports from 2025 through current. Printed earlier-year comparatives inside those reports remain evidence; 2024 source PDFs do not enter production or a provider queue. No provider calls, re-extraction, original-source writes, F36/F37 edits or shared frozen-file edits were performed.

## Printed recognition population

The family-local adapter now authenticates the actual blank GROUP for tax expense recognized in the separate/consolidated income statement, its two contiguous CURRENT and deferred-income children, and the immediately closing standalone printed root. It does not synthesize a GROUP from ancestry or from equality of amounts.

The receipt is tri-state: `NOT_APPLICABLE`, `PASS` local source frontier, or `ALGORITHM_HOLD` for recognized but malformed evidence. Missing actual GROUPs, nonblank carriers, extra descendants, unknown/trailing rows, duplicate roles, foreign ancestry, incomplete money/unit axes and explicit scope conflicts remain holds. Scope words in original GROUP paths and column headers cannot disappear when structural ancestry is removed.

Deferred income shares the expense-zero representation only when both selected source cells independently contain observed zero, including the declared accounting-dash convention. Raw text and states remain intact. Blanks, partial lanes and nonzero deferred income do not obtain that representation. CURRENT plus the two observed zeros must equal the printed root in both lanes; no source value is solved from that equation.

Raw labels are checked before punctuation normalization. The literal root marker `(*)` is supported only with its unique, exact, owned single-table estimation narrative. That narrative is not amount, unit, scope or period authority. Unknown annotations and non-Vietnamese combining markers remain holds.

Fresh ancestry proofs retain original scope paths for signed-display verification. The final source-control seal checks every recognition population even if generic evaluation consumed or suppressed its mappings. Existing source-period, document/entity, unit and independent nonroot sign-orientation gates remain mandatory.

## Independent tax effect control

A separate finite source control authenticates the printed PBT, monetary statutory-tax amount, blank adjustment GROUP, complete ordered signed adjustments, calculation subtotal and following recognition frontier. Printed RATE plus all observed signed effects must close the printed calculation, and calculation must separately match printed CURRENT in both lanes. PBT times 20 percent is not an operand or an inferred source value.

This control prevents generic tax-effect observations from being exported as income-basis `NON_TAXABLE_AGGREGATE` or `NON_DEDUCTIBLE_EXPENSE` targets. Only one fully matching original source identity can be projected to source-only evidence: locator, ordinal, kind, label, path, money columns, unit, raw text, coefficients and source states all match. Mixed refs, value drift and equation/derived dependencies are rejected. The projection locally recognizes the frozen evaluator's exact `SOURCE_OBSERVED_ROLE_ROW` state; the general signed/root observation predicate is unchanged.

Original generic mappings and full raw-source forward controls remain in an additive closure receipt with `schema_exported: false`. Only final top-level trial mappings enter exported mappings or `family_mapping` storage rows. Recursive observation-audit counts are not export counts.

## Verification

The first complete witness was retained as a failure, not acceptance: 1,079 tests, 16 failures, unchanged inputs. Eight failures exposed earlier rejection of historical missing-GROUP fixtures; eight exposed the projection's initial overly narrow direct-observation state check. Missing-GROUP fixtures remain negative; honest actual-GROUP and PRIMARY-counterpart fixtures preserve positive repair and receipt-order replay tests. Root-retention and scope-negative assertions remain covered.

Failed witness:

- `/srv/bctc-receipts/f39-recognition-focused-1792586784390-fc9f904a847e88/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`
- SHA256 `b10df4d0171b7284575d4971b9e657be0262ff2cef7b2d413d14c402f86114cc`.

Final evidence:

| Gate | Result | Receipt SHA256 |
| --- | --- | --- |
| Focused implementation witness | PASS, 1,099 tests, 14 suites, no failures/errors/skips; 44 actual project imports; inputs unchanged | `0d09cb72650622af8ce0d525e62e1c2f08fa5b77ce8657a3802e2bce6518cee3` |
| Bounded 34-document diagnostic | 15 READY, 19 UNRESOLVED, 68 final mappings; no persistence or corpus acceptance claim | `ca45adc6cff8ef0403053275e189fe2383b6178d35137cb29f4e2ceb4b3cc68e` |
| Independent cold original-source replay | PASS cold source replay and semantic export invariants, not family acceptance | `d5a56c2a1a982df0c494273ab3e86043a83d838a04d22eb5371ce4aaa0b748c2` |

Exact paths:

```text
/srv/bctc-receipts/f39-recognition-focused-1792587600658-ccb12244e11648/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json
/srv/bctc-receipts/f39-recognition-panel-1792587991939-6084a39abee498/income-tax-bounded-diagnostic.json
/srv/bctc-receipts/f39-recognition-cold-1792588283962-456bc7e36cfc18/F39_SCHEMA_SEMANTIC_INDEPENDENT_SOURCE_REPLAY.json
```

The diagnostic read 2,170 original selected SQLite payloads: 2,169 exact replays and the already registered, lossless redundant-text-column EIB witness. It made 34 selected-JSON API calls, read 10,196,448 payload bytes, and had zero base-cache hits. Measured selected-JSON load was 2.513 seconds, generic base evaluation 34.855 seconds and family evaluation 133.765 seconds; these are stage measurements, not a claimed overall speedup.

Source observation audit: PASS, zero violations, 445 recursively audited mappings/890 cells, two derived cells, six source blanks and six partial mappings. These nested audit counts must not be confused with the 68 final mappings.

Source database was independently opened read-only with query-only enabled: `quick_check = ok`, `foreign_key_check = []`. Its SHA before and after was `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`, size 573,145,088 bytes. The bounded run did not create a persisted results database; full-result persistence remains a terminal gate.

## Bounded outcome

All final mapping objects for the preceding 12 READY sources remain exactly unchanged: full271 ordinals `1, 27, 30, 39, 44, 193, 231, 249, 260, 261, 262, 264`. Comparison input was the preceding diagnostic SHA `cfe806fddb63724346bc6f976b3cff6d3042e87f2eafda15746cb23821e5baf8`.

New READY sources are `181, 185, 186`. Each exports only PBT RNID 5728, CURRENT RNID 5723 and the original signed PRIMARY root RNID 5727. Values below are coefficients in explicitly printed MILLION_VND; root signs are not rewritten.

| Full271 ordinal | Scope | PBT current and comparative | CURRENT current and comparative | PRIMARY root current and comparative |
| --- | --- | --- | --- | --- |
| 181 | SEPARATE | 6742185 / 5909471 | 1345829 / 1181961 | -1345829 / -1181961 |
| 185 | CONSOLIDATED | 6739389 / 4508225 | 1334139 / 913134 | -1334139 / -913134 |
| 186 | CONSOLIDATED | 6868389 / 6039399 | 1358850 / 1223373 | -1358850 / -1223373 |

The two tax-effect income-basis RNIDs are absent from each source's final mappings and retained only as suppressed controls. Source 187 remains unresolved: its independent PRIMARY display/population proof cannot erase numeric `7`/`8` ancestors supported only by hierarchy proposals. Its accepted NOTE frontier and exact root-footnote context do not resolve that separate gap. Source 180 has no actual recognition GROUP; the new route does not invent one.

## Code and frozen authorities

Family evaluator SHA256: `a0fff05b7094c6a64cda35a08676a5a247479545f448c30fa9c95dadf8aaf653`.

New tests include 90 recognition-frontier cases and 91 RATE-effect/projection/public-boundary cases. The complete focused receipt binds all changed tests and the source/configuration axes, not just these two modules.

Frozen evaluator remains `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`; frozen generic runner remains `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`. The original thirteen-repair specification and render registry are unchanged.

Coordination was read and an immutable precommit HEARTBEAT exact-version verified:

```text
key: bctc-ai/coordination/2025-current/v1/events/20261021T131817015675Z-LAPTOP_INTEGRATOR-HEARTBEAT-80bd631f9c55436c9a4a8a11f1be0c31.json
VersionId: l5tULoXugoECHQHzuipWWkxMdR.SQWOR
SHA256: da0c0c324a9e1eba553af6e94506938dc4b93de1593d6493673bde142e9700ef
```

The three final witnesses are published append-only after this descendant commit is pushed. Their exact S3 keys/VersionIds are recorded in the external publication receipt and following HEARTBEAT; no migration object or historical receipt is overwritten.

## Parallel PRIMARY handoff and next work

The user assigned Claude the three PRIMARY statements and Codex the notes. The two new handoff files, committed with this checkpoint, are `CLAUDE_PRIMARY_STATEMENTS_GOAL_2026-10-21.md` and `CLAUDE_PRIMARY_STATEMENTS_INSTRUCTIONS_2026-10-21.md`. Claude starts from this pushed commit in a separate worktree/branch, owns PRIMARY-only new code and receipts, and does not modify TM or the frozen platform. A three-statement PRIMARY_ONLY workbook can be accepted independently; it is not full BCTC completion.

Codex continues the NOTE work in order F39, F36, F37. F41 remains closed until all three are terminal. Next bounded F39 work includes independently printed comparative-flow policies, the remaining PRIMARY ancestry/source-caption ambiguities and their exact source reviews. Known KLB66 caption transcription evidence is not an applied repair or readiness receipt.

F39 is not terminal. Full271/common204 independent runs, full source accounting, persistence/reload, PDF/residual acceptance and the final ledger/seal remain required. The old workbook writer and recursive observation audit are not a released Gemini-to-Excel bridge. No READY_FOR_INTEGRATION event is claimed for F39 by this checkpoint.
