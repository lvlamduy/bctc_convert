# Family 14 — PURCHASED_DEBT_ACTIVITY

## Scope and result

This audit covers the immutable 2025–2026 corpus of 271 PDFs and 14,945 selected page-JSON versions. No provider request or source mutation was used.

| Stage | READY | NOT_OBSERVED | UNRESOLVED | Mappings |
|---|---:|---:|---:|---:|
| Baseline | 34 | 175 | 62 | 126 |
| Accepted implementation | 71 | 175 | 25 | 266 |

The transition is exactly 37 `UNRESOLVED → READY`. All 34 baseline READY documents retain the same normalized RNID/coefficient mappings, all 175 NOT_OBSERVED documents retain their disposition, and the 25 remaining UNRESOLVED documents have direct PDF evidence that the required purchased-principal/interest detail population is not printed.

Accepted full-corpus artifacts:

- Sweep: `/dev/shm/f14-full271-final6.MMYOe2/family14.json`, SHA-256 `c5c90a98a88338c2f605e2f93b9fc620e097a9b8f21619d9abf26cbd22436913`, 3,302,977 bytes.
- Audit: `/dev/shm/f14-full271-final6.MMYOe2/family14.audit.json`, SHA-256 `029cdb2576377a5ebcc0535a64c42e58d4248c62f0e0a6df53a67fb46f8b133f`, 2,333,778 bytes.
- A second full replay is byte-identical to the accepted sweep.
- Historical comparator disposition is `NOT_APPLICABLE_DISJOINT_CORPUS`, with zero overlap against the independently authenticated historical oracle sources.

## Schema outputs and algorithm changes

The family root RNID 800 remains structural context only. Visible source rows map to RNID 801 (VND purchase), RNID 802 (foreign-currency purchase), RNID 803 (provision), RNID 5738 (purchased principal), and RNID 5739 (purchased interest).

The 37 recovered PDFs use reusable, source-bound rules rather than bank/file/page routing:

- exact owner and row aliases for `Mua nợ`, purchased-principal variants, and purchased-interest variants;
- exact VND and million-VND unit domains, preserving the declared scale in receipts;
- a uniquely labelled single component/result and a unique trailing visible total;
- at most one adjacent continuation page, with same-source adjacency, direction, owner/reset, period, unit, and component-frontier checks;
- unitless tables only when every consumed cell is an observed dash/zero and no conflicting unit is present;
- source blank preservation: `null` is never converted to numeric zero and no equation backfills an unobserved lane;
- exact PDF-visible cell corrections and exact adjacent duplicate-row removal through an immutable, page/image/table/row/column-bound repair artifact;
- a table caption that merely mentions an already active owner no longer creates a false new owner fence; an explicit owner heading or reset still does.

The registered repair artifact is `data/registered/gemini_json_dual_component_source_repairs_v1.json`, SHA-256 `879091395013512327cb87d5cf254f577d9d8705cc2a151452631703ce9195d8`. It contains 18 page receipts and 84 exact cell repairs: 8 current-corpus receipts/43 cells plus 10 compatibility receipts/41 cells. Every replacement is a literal value visible on the rendered PDF; none is computed from another value or an equation. One current receipt also drops one byte-identical adjacent JSON row after the PDF confirms a single visible row.

## Complete visual disposition of the former 62 residuals

All 62 baseline residual PDFs, covering 66 relevant pages and the necessary adjacent pages, were visually inspected against source-SHA-verified PDFs.

- 37 contain complete, schema-mappable Family-14 evidence and are now READY: BVB 3, NAB 1, OCB 4, PGB 1, TCB 1, TPB 16, and VAB 11.
- 25 remain UNRESOLVED because the PDF prints the balance/quality/provision population but omits the purchased-principal/interest detail population: EIB ordinals `37,38,41,42,43,46,47,48,49,50,51,52`; MSB `76,77,78,79,80,81,88,89`; PGB `140,141,144,145,146`.
- None of the remaining 25 is blocked by an alias, layout, header, continuation, unit parser, or missing schema RNID.

## Source-observation gate

`validate_source_observation_mapping_contract_v1` passes the accepted full sweep:

- mapping occurrences: 532 (candidate and trial copies of 266 mappings);
- cells: 1,064;
- partial mappings/source-blank cells: 40/40;
- derived cells: 0;
- violations: 0.

Thus visible sister lanes remain mapped while genuine blank lanes stay typed `BLANK_SOURCE_CELL`; no all-unobserved mapping or fabricated zero is emitted.

## Protected regression

The protected compatibility replay completes with 64 READY / 76 NOT_OBSERVED / 0 UNRESOLVED and 254 mappings:

- Sweep: `/dev/shm/f14-old140-strict-final5.TZ9C4W/family14.json`, SHA-256 `272ff4cdaca33d8e8a0e8b2d2dd5478f33a6ad0bc45ccb4fe9464447331ddc2e`.
- Audit: `/dev/shm/f14-old140-strict-final5.TZ9C4W/family14.audit.json`, SHA-256 `8ac92f263cc1c177cb7302516bcc6bd803cbdd79faef25f054268e55c697f0e4`.
- Historical comparator: 16/16 exact; page, region, comparator, and selected-frontier axes are unchanged.

An independent visual audit reproduced all ten source PDF hashes and all ten project-native 300-DPI render hashes, and confirmed that 41/41 selected-JSON `BLANK/null` cells are visibly printed dashes. Evidence: `/dev/shm/f14-old140-null-vs-visible-dash-audit-v1.json`, SHA-256 `53056ca63a3250883aec83945f1a3781a1157636fe4f3e8b1c4e9c7dbed3770d`.

Two protected audit seals were deliberately resealed with audited semantics:

- equation axis: numeric left/right sides and ordering are unchanged for all 256 equations; only the typed status changes from legacy `EXACT` to `EXACT_OBSERVED_SOURCE_LANE`;
- mapping axis: exactly 25 emitted cells now carry authenticated PDF-dash receipts instead of the incorrect base `BLANK` state. The other 16 repaired dash cells are visible totals/controls and are not schema mappings.

## Verification

- 33 focused evaluator, indexed replay, source-repair, comparator-policy, and runner tests pass.
- Ruff passes on all Family-14-owned Python paths.
- `git diff --check` passes on all Family-14-owned paths.
- Final engine SHA-256: `407000fd67004cb9650ad5c76581d7c16c3a11e5f95bf47338404f9a81149ed0`.
- Final topology/evaluation/schema SHA-256: `7e4cbe85cf2ea8f55b1b96d7b681da878cc69a3369ebe719ca97797d46c774f8` / `699aebf42b9a91fa8b4fec1c0504eb88ec7833657b372a4da9ece5a631b14f5d` / `eefad521260bda7eefdbab877afdb4962e57c9995d032331d20ec3839e965901`.
- Final runner SHA-256: `e04ae6949fdc8714cb10980e6e5696f9618719e9200c841610ff9a7dde481af1`.
