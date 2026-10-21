# F39 four MONEY quarter and cumulative header checkpoint

F39 now recognizes complete printed quarter/YTD header pairs with explicit numeric years, with or without the literal word `Năm`. It also retains conflicting explicit PRIMARY money units as an invalid-source veto instead of silently falling back to a valid NOTE. All 1,811 focused tests pass. The bounded 34-document evaluation and independent original-SQLite replay preserve the previous final outputs exactly. F39 remains unfinished; this checkpoint does not accept a workbook or seal the family.

The checkpoint descends from `96daf6e8bcf72044ee76a634b15f0c3dfa74be6b` on `codex/f39-income-tax-laptop`, with migration base `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Production reports remain 2025 through current. Standalone 2024 reports remain excluded; authenticated earlier-year comparative columns printed inside an eligible report remain valid source observations.

## Header recognition and local ownership

The family-local rule requires a typed PRIMARY INCOME or CASH_FLOW table with exactly four MONEY columns: two matching quarter columns followed by two matching cumulative columns. It accepts only the complete finite printed header grammar. Quarter codes must remain literal ASCII Roman or numeric tokens; numeric years must remain literal ASCII four-digit tokens in the calendar range 1 through 9999, ordered current after comparative and identical across the quarter/YTD pair. Relative labels still require the printed `Năm nay/Năm trước`; they supply no absolute years.

The private recognition view collapses Python 3.12 layout whitespace and the reviewed lowercase serialized newline. Original header paths, punctuation, raw tokens and source hashes remain unchanged. Unknown annotations, split digits/codes, added years and unreviewed punctuation do not disappear through normalization. Existing valid header evidence retains its previous material and receipt identity.

Each selected YTD header component receives census ownership only after a fresh whole-four-header proof matches the entire independently resolved period pair. The evidence binds the raw column and path-component ordinals, original path and text, UTF-8 SHA, period and parent receipt. The consumed-year flag is true only for a component containing its actual literal numeric year. Known YTD wording, including `từ đầu năm đến cuối quý này`, is header furniture within this proof, not a second date-range assertion. No caption, narrative, row or ancestor receives that exception. This rule grants no unit, entity, scope, sign or amount permission.

## Explicit PRIMARY unit conflicts cannot disappear

A source-visible PRIMARY tax-role row with `CONFLICTING_EXPLICIT_MONEY_UNITS` or `MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE` now remains invalid even when no usable two-column lane exists. The conflict receipt preserves the original unit/lane evidence, row, table hash and every original MONEY column. An unusable lane retains an empty selected-value list; it does not manufacture missing cells or zeroes.

The selector reports `INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT`; independent invalid-cell reasons remain separate when both occur. Both normal NOTE and original-NOTE adapter routes retain the veto. The original adapter authenticates the conditional primary-selection conflict receipt, and fresh public rebuilding rejects a self-resealed replacement. Truly absent units and unrelated existing behavior are not reclassified by this change. No shared resolver is modified.

## Verified evidence

| Gate | Result | SHA256 |
| --- | --- | --- |
| Full focused witness | 1,811 PASS, 16 suites; zero failure, error or skip; actual imports and unchanged inputs bound | `96e092eaf263b43a94554031698345040c93cc3400fe6fccb45a083a5e46a1c3` |
| Focused JUnit | 1,811 tests; zero failure, error or skip | `827a80408798eee30a07bd28e2384cbaf1c00c0fef99a4d6649424c97a46a875` |
| Bounded diagnostic | 34 documents; 18 READY review proposals, 16 UNRESOLVED, 90 final mappings; no persistence | `55acd7f5c0f70c6a4ccd1a1a71be985377fcdcc8938c0dbba4cbbe6b82d0d1f7` |
| Independent original-SQLite replay | Complete current trials reconstructed exactly; previous final statuses and whole mappings exact; no stage failures | `8d6730e47aa0c427f59537ae820bd25256c08869c1cc2a6e963908564ea3be34` |
| Original LPB source-stage witness | Both pages have intrinsic YTD, caption and local census proof; actual correspondence HOLD retained | `e29f1ccccc023b3c9059191e4446e8bd029775e6ccb13ac6c0d92f911dc613d5` |

Exact witness paths:

```text
/srv/bctc-receipts/f39-four-money-focused-v2-1792618518078-1bd72ee8b51098/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json
/srv/bctc-receipts/f39-four-money-panel-1792619426288-16a764fade9398/income-tax-bounded-diagnostic.json
/srv/bctc-receipts/f39-four-money-cold-1792619908440-37abb3e1dc6ef8/F39_SIX_MONTH_POLICY_INDEPENDENT_SOURCE_REPLAY_V2.json
/srv/bctc-receipts/f39-lpb74-four-money-source-1792620352020-f14b8cd82412b/F39_LPB74_FOUR_MONEY_ORIGINAL_SOURCE_WITNESS_V2.json
```

The comparative-flow module now has 597 cases, adding 140 without removing old tests. Cases cover both authentic raw header shapes, optional numeric-year markers, all quarters, relative-year boundaries, split layout components, Unicode whitespace, raw digit/acronym annotations, incomplete/mismatched axes, public unit vetoes and resealed evidence. The final targeted run passed all 140 new cases. An earlier full run was deliberately interrupted after 1,268 passes when a whitespace regression was confirmed; it is not a PASS receipt. Earlier failing runs and the interrupted receipt remain intact. The final 1,811-test witness follows the corrected implementation and precedes the corpus evaluations.

All 34 complete trial objects also compare exactly with the immediately prior diagnostic `fac3aba5ab3474cf82dc530d3da3efa26cf055581115eff7ac3523964b70bcb8`. The panel contains no new unit-conflict veto and does not itself exercise the LPB header-stage improvement because that document stops earlier. The separate original-source witness supplies that proof.

Warm and independent cold paths read the same 34 selected-JSON batches, 2,170 SQLite rows and 10,196,448 payload bytes: 2,169 exact original replays plus the existing single lossless redundant-TEXT normalization. Warm inventory use is 272 requests, 34 builds and 238 hits; cold use is 272 actual builds with zero hits, stored entries or dependency checks. No speed improvement is claimed for this accuracy change. The observation contract passes with zero violations; its 487 mapping objects and 974 checked cells include nested evidence and are not the final-output count or an all-raw-MONEY-cell census.

The source DB remains 573,145,088 bytes, SHA `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`. Read-only/query-only `quick_check` is ok and `foreign_key_check` is empty before and after the source witnesses. All runs use fresh Python 3.12 with bytecode writes disabled. The source/config/test axes and actual imports remain tied to the same witnessed bytes; no hot reload or arbitrary in-memory mutation is supported.

## LPB source proof and remaining ambiguity

The new source witness authenticates all 94 original selected LPB74 pages and unchanged source PDF SHA `076695d24be19332f8cde12b31ba265aba4d3e8c4fc95cc7dcacea48a0740248`, 6,219,303 bytes. Physical pages 6 and 7 retain their exact version, section and table hashes from the previous checkpoint. Their selected raw columns remain `[6,7]` and `[5,6]`; quarter columns remain separate. Both now prove intrinsic `SOURCE_YTD_QUARTER` windows for 2025/Q2 and 2024/Q2, their whole January 1 to June 30 caption, and every selected header component with no local census veto.

Actual same-source period correspondence still returns `ALGORITHM_HOLD`, with `SOURCE_PERIOD_CONTEXTUAL_CORRESPONDENCE_NOT_PROVEN` and `SOURCE_PERIOD_INTRINSIC_YTD_CONTRADICTED_BY_CASH_FLOW`. The retained CF anchors on physical pages 8 and 9 have null absolute-duration semantics in this run. The fresh reason labels do not prove a genuine issuer/date contradiction. This checkpoint neither waives that HOLD nor classifies its cause. LPB74 remains UNRESOLVED with zero final mappings.

An additional lossless, read-only retrieval preserves all 94 original page contexts at `/srv/bctc-receipts/f39-lpb74-scope-basis-context-1792619472920-66e8fa7e267668/F39_LPB74_SCOPE_BASIS_ORIGINAL_CONTEXT_AUDIT_V1.json`, SHA `d9571b7c215e82a5c81687d6511223cf865cf11f3297e35480dd81becda6d881`, 1,613,184 bytes. Held-file-descriptor and path hashes/sizes, SQLite checks and actual import bindings pass before and after; no evaluator, provider, repair or persistence is invoked by that retrieval.

The page 30 section `(dd) Thuế` explicitly includes prior-period payable-tax adjustments in current income tax. Its second narrative has raw UTF-8 SHA `db64245f1e59c48674300cd6bdc5fbfdbb2c2462173be6679358e49f47359a58`, within section SHA `ddc2a4de787338e5a9c021f264ca48e59bcd77d3035459426e05c36ea80c18e0`. This positive definition does not identify whether page 64's recognition value `8.966` and effective-rate value `9.035` measure the same component. Both sources remain intact. Schema ID 5733 remains under 5737 with a TAX_RECONCILIATION precedent; it is not narrowed to the 5723 recognized-expense branch. Equal totals, the comparative amount, the difference of 69 and the printed 20% rate do not select an amount or establish a genuine same-basis conflict.

Reading the 94 stored contexts establishes a named reporting bank, but not an affirmative separate/consolidated scope. The first two original JSON pages contain no transcribed sections, so JSON search cannot establish whole-PDF absence. Both frontmatter pages were separately rendered and visually inspected: the cover title is unqualified and the following page contains bank information. The inactive manual observation is `D:/bctc_bank/restore-receipts/F39_LPB74_FRONTMATTER_VISUAL_OBSERVATION_2026-10-22.json`, SHA `aaeefafe189ed09e7612553d01fdac538cfc2afc843ae8434be794b800ea1663`. It grants no implicit SEPARATE scope, source correction or production permission.

SSB187 retains its independently proven global comparative policy and selected literal NOTE-to-INCOME duration route. Its numeric outline ancestry remains a separate unresolved requirement; no outline permission is activated here.

## Next algorithm and family gates

Next work is source-local: resolve the retained period HOLD without ignoring contrary CF evidence; recognize the exact whole PRIMARY quoted-TNDN root label without broad NOTE aliases; authenticate a two-locator PBT/tax-to-PAT continuation bridge; resolve prior-adjustment measurement/eligibility and entity/scope evidence; and integrate an original all-status raw-cell census with authenticated disposition proofs. Inactive external prototypes are not production dependencies or acceptance evidence.

The six migration blockers are covered at focused-contract scope, not full-family acceptance. F39 still needs authoritative full271/common204 evaluation, independent source replay, complete observation/raw-cell coverage, persistence and reload, SQLite integrity, PDF/residual audit, projection verification and its release ledger. F36 and then F37 follow only after F39 is terminal; F41 remains closed. Claude owns the three PRIMARY statements in its separate worktree; this checkpoint changes only F39.

## Source pins and publication

| File | SHA256 |
| --- | --- |
| F39 evaluator | `8ba9b79b3b91514bc1542c83a6f67d3ab11c500f6919a30ed9a94f6651f1d6db` |
| Comparative-flow tests | `a90b66990953444e426f4ca1cd31a5e358bc8e6016a50b0176a0c4cae9c1789f` |
| Unchanged F39 runner | `71ec0b9ccb757b4a0ab87b6c23c072efe18f1360cb6f3e08c5f926799586c3c4` |
| Independent cold helper V2 | `acb7ed1adb6857b48d275ad31930ffb95324c75578953926dfc3d412c828850a` |
| Original LPB four-MONEY witness helper V2 | `5dd52fa29768922693534b13b4e55d9663d206e33c67e49c94057fff0cad4b77` |
| Original94 context retrieval helper | `a3643d4ab5d1cc1af8f789cf7cf62dcdb4da96f47bd1331a2bface6180d23f22` |
| Four-witness append-only publisher | `78e9fa745289b2accb151d938dd29225daba95921908781672f3f8a33e8bdbe9` |

Frozen shared evaluator remains `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`; generic runner remains `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`. No source/database write, shared/F36/F37/Claude code change, provider call, obsolete OCR, artifact cleanup or common-branch push is introduced.

All current witness jobs reached terminal state before this document or Git mutation. Coordination events were read and the active F39 claim revalidated before the checkpoint phase. The precommit HEARTBEAT is key `bctc-ai/coordination/2025-current/v1/events/20261021T220740331678Z-LAPTOP_INTEGRATOR-HEARTBEAT-fd31ad0d126c46f9b2921a6cd594e88e.json`, VersionId `_pef0k43IjRIfkhppWAisGBe_h8ffMsR`, SHA `020579fa63925513cae2df4c260354368ade13033c8ea864088610be1208f245`.

The four-witness external manifest is `D:/bctc_bank/restore-receipts/F39_FOUR_MONEY_YTD_HEADER_WITNESS_PINS_V1_2026-10-22.json`, SHA `0f276a91d9217c25d7d8e73c6d9693c1d5f46d43883eada071f8ce7a576ed649`. After the owned branch is committed and pushed, the reviewed publisher checks the clean descendant, exact source bytes and all four witness chains before uploading new keys with exact-VersionId readback. Actual publication results belong to the additive external receipt and following HEARTBEAT. The upload covers only those four JSON witnesses, not the additional context/visual receipts, helpers or a complete machine backup.
