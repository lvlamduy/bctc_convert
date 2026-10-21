# F39 owned flow date range caption checkpoint

F39 now reads a complete printed interim date-range caption without borrowing dates from another title, table or narrative. All 1,671 focused tests pass. A bounded 34-document replay retains every previous final status and whole final mapping, and an independent cache-disabled original-SQLite replay reconstructs the complete current trials exactly. These checks do not close F39 or accept an Excel output.

The checkpoint descends from `cf5686226628c01d9ff760dd00fb0bde0c077108` on `codex/f39-income-tax-laptop`, with migration base `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Production reports remain 2025 through current; standalone 2024 reports remain excluded. Printed earlier-year comparatives within eligible reports retain their source meaning.

## Printed caption rule

The new family-local parser accepts only a whole typed PRIMARY `INCOME_STATEMENT` or `CASH_FLOW` caption containing the printed start and end dates. Its finite interim grammar requires January 1 through March 31, June 30 or September 30 of the same explicitly printed year. An interim caption ending December 31 is unsupported, not an annual permission. Optional report-scope wording, continuation and the two known cash-flow methods remain raw furniture; the parser grants no unit, scope, sign, amount or comparative-year permission.

Both date tokens must already be literal ASCII dates in the raw caption. Vietnamese accent folding cannot manufacture a date by erasing marks attached to digits. Raw caption text, exact lines, UTF-8 SHA, both printed dates and the parser receipt are retained. Layout whitespace and serialized newlines are recognized without removing unknown punctuation or annotations.

Recognized malformed ranges become unsupported constraints before the existing caption slicing or header fallback. A complete header pair cannot override them. The local surface census consumes range furniture only when this same whole caption matches the independently resolved current window. It retains all other title, header, narrative and ancestor vetoes. The current-duration caption never guesses the comparative year or rewrites source lane keys.

## Verified tests and bounded source replay

| Gate | Result | SHA256 |
| --- | --- | --- |
| New targeted cases | 70 PASS, 387 deselected | JUnit `4596d122d2c6ce4bf9667bd91b64de58283c4ee6e68de7619b0be2a286368934` |
| Full focused witness | 1,671 PASS in 16 suites; 46 actual project imports; zero failure, error or skip; inputs unchanged | `42131e244b5ad557f6bef5875b656a938118d435ea9c99bce5cfe8d7545d9b2f` |
| Bounded diagnostic | 34 documents; 18 READY review proposals, 16 UNRESOLVED, 90 final mappings; no persistence | `fac3aba5ab3474cf82dc530d3da3efa26cf055581115eff7ac3523964b70bcb8` |
| Independent original-SQLite replay | Complete current trials exact; prior final statuses and whole mappings exact; no stage failures | `e6ba60c304b9da7aad371bc774633da074cf2668e46933e323c6ac2f536876a7` |
| Additional original LPB source witness | Whole-caption proof only; independent period HOLD retained without cause classification | `98a67d0c418f89e10c0b2118aa8a1b0668ea74c503e689414c86d19e31443aaa` |

Exact witness paths:

```text
/srv/bctc-receipts/f39-range-caption-focused-1792613523282-23ad4ce8852448e4a4ab59693bb6cf3c/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json
/srv/bctc-receipts/f39-range-caption-panel-1792614330659-9c142d2e68b5b8/income-tax-bounded-diagnostic.json
/srv/bctc-receipts/f39-range-caption-cold-1792614606332-f0a6a51d3947b/F39_SIX_MONTH_POLICY_INDEPENDENT_SOURCE_REPLAY_V2.json
/srv/bctc-receipts/f39-lpb74-range-source-1792614980535-5ae1d0190947d8/F39_LPB74_OWNED_RANGE_ORIGINAL_SOURCE_WITNESS_V1.json
```

The new tests are appended to the existing comparative-flow module; no old case is removed or changed. Public positives use relative `Kỳ này/Kỳ trước` columns and explicitly reject accidental absolute-header fallback. Tests cover both title owners, consistent and conflicting surfaces, multiple tables, absent comparative policy, split captions, calendar errors, interim-versus-annual conflict, Unicode digit annotations and freshly rebuilt query evidence after self-resealing attempts.

A separate external synthetic probe adds eight negative and two positive subcases in two unittest methods. It confirms that selected INCOME captions with malformed ranges remain HOLD even when their dated headers are valid, while a valid whole range preserves the literal route. This probe is not counted among the 1,671 tests. Its source is `D:/bctc_bank/restore-tools/test_f39_range_caption_header_fallback_probe_v1.py`, SHA `fdc567f52b156f99bbc8bf8540658297396893a43193bb0dacb60e89ff129344`.

The bounded panel and cold replay use the same 34 selected-JSON API calls, 2,170 SQLite rows and 10,196,448 payload bytes. They retain 2,169 exact original JSON replays and the existing single lossless redundant-TEXT-column normalization. No new repair is activated. The recomputed observation contract passes with zero violations; that audit is not a census of every raw MONEY cell.

Warm inventory use is 272 requests, 34 builds, 238 hits and 68 dependency checks. The independent replay proves actual disabled-cache builder calls with zero cache hits or stored entries. No performance improvement is claimed for this accuracy change. The comparison baseline remains the pinned diagnostic SHA `b9ae93450e32cbdd0e5a532c203be81162c7a1302ddec7bf8c6253e751b59853`; its historical candidate receipts are not required to remain identical.

All witnesses use fresh Python 3.12 with bytecode writes disabled and an initially nonexistent isolated bytecode prefix. Actual source imports, selected axes and source/config/test bytes remain bound to the witnessed snapshot. The trusted runtime does not support hot reload or arbitrary in-memory mutation. The original database remains 573,145,088 bytes with SHA `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`; read-only/query-only `quick_check` is ok and `foreign_key_check` is empty before and after the source checks.

## LPB original captions and unresolved period proof

The additional witness authenticates all 94 selected original LPB74 pages, source PDF SHA `076695d24be19332f8cde12b31ba265aba4d3e8c4fc95cc7dcacea48a0740248`, 6,219,303 bytes. Physical pages 6 and 7 retain their exact selected version and original table pins. Page 7 also matches the earlier independent original-source audit, SHA `85718495063ce60ff4e483758c38d4a7925df000d6d3d0f5c21755af30d3c2a6`.

Each page's original section title now owns its complete printed January 1 to June 30, 2025 caption. This is not a completed period correspondence. The actual raw selectors are complete at columns `[6,7]` and `[5,6]`, but intrinsic absolute duration remains null and the actual same-source correspondence remains `ALGORITHM_HOLD` with `SOURCE_PERIOD_CONTEXTUAL_CORRESPONDENCE_NOT_PROVEN` on both pages. The surface census also remains a HOLD without a resolved window. Its reason labels do not establish a genuine issuer/date conflict.

The witness deliberately calls this an **unclassified independent period HOLD**. A missing literal `Năm` in the printed quarter/YTD header grammar is a separately identified investigation lead, not a cause proved by these persisted reason labels. It is not waived by the successful caption parser. LPB74 remains UNRESOLVED with zero final mappings.

The existing SSB187 period proof also remains valid: all three global PRIMARY anchors pass, and the selected NOTE-to-INCOME pair uses the literal source-duration route, not new inheritance. Its two printed outline tokens still have no active ancestry permission. SSB187 remains UNRESOLVED with zero final mappings.

## Remaining source and family acceptance work

LPB still requires a separately verified four-MONEY quarter/YTD header rule, exact quoted-TNDN root-label semantics, a two-locator continuation bridge and reviewed eligibility for prior-tax-adjustment rows in distinct recognition and effective-rate presentations. No amount equality or equation may replace those source proofs.

A fresh whole-page PDF observation of LPB physical page 64 is saved outside the repo at `D:/bctc_bank/restore-receipts/f39-lpb74-tax-basis-visual-1792613808429-92506475fcdfe/F39_LPB74_TAX_BASIS_VISUAL_OBSERVATION.json`, SHA `2c8e2f5cb75abbb9fc0777fddb733f8c2986428992384f825e0e539495fe3ab4`. Its 200-DPI Poppler 24.02 PNG is SHA `18c8d8f8352142ac01da522c2e1f65d208462a399e2c233c1ddf2c737c682a07`, 953,413 bytes, 1,645 by 2,334 pixels. This manual observation is inactive; it chooses no exported adjustment, supplies no missing total label and does not classify a genuine source conflict.

Outside-repo prototypes for raw-cell census, four-header syntax and outline metadata are not production dependencies or acceptance evidence. A final all-status resolver must account for every relevant original row and every raw MONEY column, before lane filtering, with independently authenticated mapping/control/exclusion proofs. Unaccounted cells remain algorithm holds.

F39 still needs the remaining source-local algorithm work, authoritative full271/common204 evaluation, source replay, all-status observation/coverage checks, SQLite persistence and readback, PDF/residual audit, projection checks and its final ledger. The six original migration blockers remain covered at focused-contract scope; that is not full-family acceptance. F36 then F37 follow only after F39 is terminal; F41 remains closed.

## Code and coordination pins

| File | SHA256 |
| --- | --- |
| F39 evaluator | `3f8e8acbdc5b3936a79cec452e3980f18ac16def70ad09d04e004ffde99528be` |
| Comparative-flow module with 457 cases | `8b381b405680b5e755f71b459b4c988e3da3a57c0e7cc3d7268502b66b959442` |
| Unchanged F39 runner | `71ec0b9ccb757b4a0ab87b6c23c072efe18f1360cb6f3e08c5f926799586c3c4` |
| Reused independent cold helper V2 | `acb7ed1adb6857b48d275ad31930ffb95324c75578953926dfc3d412c828850a` |
| Additional original LPB caption witness helper | `66dfe58dd4a646c1d3adcce561d6fb3da133eb55827b02f2ce3d2baf75931cdf` |
| Four-witness append-only publisher | `fae0fc9222a6c6247f29413632291d012b12c85ac839225664ea1eb2cdeedd55` |

Frozen shared evaluator remains `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`; generic runner remains `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`. No shared, F36/F37 or Claude PRIMARY code is changed. No provider, original source/database write, obsolete OCR route, old-artifact cleanup or common-branch push is introduced.

Before the document/commit mutation, all coordination events were read and the active F39 claim revalidated. The exact-VersionId precommit HEARTBEAT is:

```text
key: bctc-ai/coordination/2025-current/v1/events/20261021T203909211192Z-LAPTOP_INTEGRATOR-HEARTBEAT-84d70482cff4472eb9716d4df2ca1fe9.json
VersionId: 4xukb9JlURg3j92qGoHpJQH.3hVkcDyK
SHA256: 6904fdb2f431a74c307badf88dd766918d4196031463e7d8150ef39a1e730065
```

The four current JSON witness pins are in the additive external manifest `D:/bctc_bank/restore-receipts/F39_OWNED_RANGE_CAPTION_WITNESS_PINS_V1_2026-10-22.json`, SHA `c2d74e07eb896e3b1214e6788fc0a87bb31adf8e108c23c8a7d44c4fbbecfebc`. After the owned-branch commit is pushed, the reviewed publisher validates the clean descendant commit and unchanged source inputs before any upload. Actual new S3 keys, VersionIds and readback results belong to the external publication receipt and following HEARTBEAT. This checkpoint does not claim a family seal or complete machine backup.
