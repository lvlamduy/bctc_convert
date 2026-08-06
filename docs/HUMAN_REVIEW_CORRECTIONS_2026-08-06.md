# Human-reviewed mapping corrections — 2026-08-06

## Authority and boundary

`HR-2026-08-06-CTG-ACB-MBB` is authoritative only for the exact PDF hashes and one-based pages listed below. It is a calibration registry, not production routing logic. No bank name, page number, coordinate, or reviewed amount from this registry may become a procedural mapping rule.

| Document | SHA-256 | Bytes | Pages | Frozen role |
|---|---|---:|---:|---|
| CTG consolidated Q2/2026 | `f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318` | 6,703,623 | 61 | `CALIBRATION` |
| ACB consolidated Q2/2026 | `db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86` | 8,000,750 | 33 | `CALIBRATION` |
| MBB consolidated Q1/2026 | `eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83` | 3,977,471 | 61 | `CALIBRATION` |

The machine-readable decisions are in `reference/human_review/reviewed-mapping-corrections-2026-08-06.yaml` (SHA-256 `32c86c0bf7642d3bd7596225331fc6f10906970476e1a9ba982b2f478d0f8e74`). The governing safety contract is `config/reference/human-review-v1.yaml`. Run:

```bash
.venv/bin/bctc-ai review-audit
```

The audit checks policy identity, target-template hash, source registry, immutable dataset role, every raw/numeric pair, every period map, hierarchy/order references, page bounds, visible-row uniqueness, and local PDF hash/size/page count.

## Schema audit and ReportNormId ordering

The current CDKT target template contains 77 items and ends numerically at ID `5699`. IDs `5700–5717` are absent from all four current templates. Therefore:

- `5701–5711` are retained only as reviewed external/off-balance reference IDs.
- They are not schema additions and are not written to CDKT.
- The audit requires them to be disjoint from every current template ID, addressing the duplicate-ID safety requirement.
- Context-only IDs `5715–5717` are preserved as external visible-order references where the reviewed PDF uses finer detail than the current target template.

ReportNormId is an identity key, not an ordering key. Ordering comes only from the row order in the applicable template workbook (`SchemaItem.display_order`). A newly added item can have the largest numeric ID while appearing in the middle of the report. For example, the correct template sequence is:

```text
4337 (display_order 64)
4373 (display_order 65)
4338 (display_order 66)
```

It must never be changed to numeric order. `validate_mapping_sequence()` rejects non-increasing `display_order`, duplicate schema assignments, cross-statement mappings, and unknown IDs.

## Period-axis rules

Period assignment is table-level metadata. It is never inferred from which amount is larger, from MongoDB, or independently for every row.

For CTG main CDKT page 4 and the separately scoped off-balance table on page 5, the reviewed orientation is the same but is stored as two table maps:

```text
LEFT  -> CURRENT     -> 2026-06-30
RIGHT -> COMPARATIVE -> 2025-12-31 (audited)
```

For ACB page 3:

```text
LEFT  -> CURRENT     -> 2026-06-30
RIGHT -> COMPARATIVE -> 2025-12-31
```

For MBB pages 3–4:

```text
LEFT  -> CURRENT     -> 2026-03-31
RIGHT -> COMPARATIVE -> 2025-12-31
```

`period_propagation_v1` requires a complete visible local header set or no local period evidence at all. A headerless continuation inherits only through an accepted adjacent continuation edge with the same statement instance, statement type, scope, value-column count/order, and compatible normalized geometry. Inheritance stops at a new statement, a new non-continuation table, or an explicit period-structure change. Partial repeated headers fail closed rather than being mixed with inherited metadata.

## Raw observation and value status

Confidence status and value-presence status are separate dimensions. The required value statuses are:

| Status | Meaning | Numeric output |
|---|---|---|
| `OBSERVED_VALUE` | Visible row and visible non-zero amount | Parsed amount |
| `OBSERVED_ZERO` | Visible row with numeric zero, dash, or verified empty numeric cell | `0` |
| `NOT_OBSERVED` | Schema row is absent from the PDF | None; never zero |
| `OUT_OF_SCOPE_FOR_TARGET_TEMPLATE` | Visible row belongs outside the requested template | Retained as evidence; not exported to target |
| `AMBIGUOUS_MAPPING` | Visible evidence cannot yet establish one schema ID | Not auto-exported |
| `REFERENCE_NOT_YET_BUILT` | Machine reference is unavailable | Visible extraction is retained; absence of reference is not an error |

Raw and normalized representations remain together:

```text
raw_value="-"             -> normalized_numeric_value=0
raw_value="(3.801.708)"   -> normalized_numeric_value=-3801708
```

A visibly empty numeric cell becomes zero only after the row, numeric-cell geometry, and table structure are verified. An absent schema row has no raw cell observation.

## Structural mapping priority

The production candidate rank is lexicographic and fail-closed:

1. Exact statement/table/scope context.
2. Parent-child relationship.
3. Previous/next rows and direction in template workbook order.
4. Indentation and numbering.
5. Exact/normalized label.
6. Same-bank history as a review-only tie-breaker.
7. Cross-bank history as a review-only tie-breaker.

Names retrieve candidates; they do not override a verified parent. Historical evidence can order a review list but cannot automatically resolve a tie and cannot override any verified structural mismatch. Numeric amounts are not mapping features.

## Reviewed CTG decisions

### CDKT page 4

| ID | PDF row | 2026-06-30 | 2025-12-31 | Decision |
|---:|---|---:|---:|---|
| 4340 | Cố phiếu quỹ | 0 (`-`) | 0 (`-`) | Map to 4340 |
| 4374 | Cố phiếu ưu đãi | 0 (`-`) | 0 (`-`) | Map to 4374 |
| 4339 | Vốn khác | 2,170,078 | 1,574,563 | Map to 4339 |
| 4365 | Quỹ của TCTD | 31,651,682 | 31,654,355 | Map to 4365 |
| 4342 | Chênh lệch tỷ giá hối đoái | 346,575 | 362,748 | Map to 4342 |
| 4343 | Lợi nhuận sau thuế chưa phân phối | 78,144,110 | 58,212,794 | Valid wording variant of 4343 |
| 5699 | Lợi ích của cổ đông không kiểm soát | 1,257,755 | 1,206,433 | Map once to 5699; do not duplicate into 4306 |
| 4305 | OCR-corrupted total liabilities/equity label | 2,962,003,670 | 2,767,699,300 | Map to 4305 despite label OCR errors |
| 4373 | Vốn đầu tư XDCB, mua sắm TSCĐ | 0 (`-`) | 0 (`-`) | Map once to 4373 |
| 4337 | No visible row | — | — | `NOT_OBSERVED`; do not copy 4373's dashes |

### Off-balance page 5

All rows below are visible but `OUT_OF_SCOPE_FOR_TARGET_TEMPLATE`; they are not mapping failures and never populate target CDKT.

| External reference ID | Row | 2026-06-30 | 2025-12-31 |
|---:|---|---:|---:|
| 5701 | Bảo lãnh vay vốn | 36,255,058 | 28,630,320 |
| 5702 | Cam kết giao dịch hối đoái | 953,123,645 | 860,422,276 |
| 5703 | Cam kết mua ngoại tệ | 7,973,593 | 5,341,651 |
| 5704 | Cam kết bán ngoại tệ | 7,970,563 | 5,341,779 |
| 5705 | Cam kết giao dịch hoán đổi | 937,179,489 | 849,738,846 |
| 5706 | Cam kết trong nghiệp vụ L/C | 104,889,002 | 91,019,626 |
| 5707 | Bảo lãnh khác | 155,889,602 | 147,475,860 |
| 5708 | Các cam kết khác | 89,547,959 | 83,119,399 |
| 5709 | Lãi cho vay và phí phải thu chưa thu được | 10,115,233 | 10,640,841 |
| 5710 | Nợ khó đòi đã xử lý | 203,790,510 | 185,652,293 |
| 5711 | Tài sản và chứng từ khác | 115,147,331 | 95,027,390 |

ID 5711 must not map to `4366 — Chi tiết Tài sản “Có” khác`; section/parent context is different.

## Reviewed ACB decisions

| ID | PDF row and structural reason | 2026-06-30 | 2025-12-31 |
|---:|---|---:|---:|
| 4345 | Generic `Dự phòng rủi ro`, but child of 4312 after 4326 and before 4313 | 0 (`-`) | 0 (`-`) |
| 4367 | Generic original-cost label under tangible fixed assets 4328 | 7,212,349 | 6,806,108 |
| 4368 | Generic depreciation label under tangible fixed assets 4328 | -3,801,708 | -3,605,621 |

The same generic original-cost/depreciation labels map to `4369/4370` under finance-lease assets and `4371/4372` under intangible assets.

## Reviewed MBB decisions

| ID | PDF row | Current 2026-03-31 | Comparative 2025-12-31 | Superseded OCR |
|---:|---|---:|---:|---:|
| 4317 | Góp vốn, đầu tư dài hạn | 467,906 | 468,396 | 468,896 |
| 4354 | Đầu tư vào công ty liên kết | 0 (`-`) | 0 (`-`) | — |
| 4357 | Các khoản lãi, phí phải thu | 16,082,037 | 13,549,018 | 13,549,010 |
| 4335 | Tài sản thuế TNDN hoãn lại | 37,793 | 34,339 | 34,333 |
| 4366 | Tài sản Có khác | 6,622,398 | 7,894,091 | 7,894,090 |
| 4336 | Thuế TNDN hoãn lại phải trả | 0 (`-`) | 0 (`-`) | — |

The visible PDF remains authoritative. Same-bank history may support a one-digit reread decision but cannot overwrite the PDF.

## Implemented regression gates

- Raw dash, verified blank, parentheses, absence, scope, and missing-reference semantics.
- CTG left-current/right-comparative propagation to a headerless continuation.
- Stop conditions and partial-header failure.
- Generic TSCĐ label resolved by parent despite deliberately stronger wrong historical scores.
- Generic risk provision resolved by parent and neighbors.
- XDCB row maps once to 4373, not 4337.
- Off-balance section yields scope exclusion with no CDKT candidates.
- History-only discrimination remains `AMBIGUOUS_MAPPING`.
- Non-monotonic ID sequence passes when template `display_order` is correct; numeric-ID sorting fails.
- Duplicate assignment of a single schema ID to two visible rows fails.
- All 30 reviewed decisions and 58 visible values validate against source/schema/policy identities.

## What this registry must not do

- It must not route CTG/ACB/MBB pages in production.
- It must not become a label dictionary that bypasses structure.
- It must not inject reviewed numbers into a new extraction.
- It must not promote calibration accuracy to holdout or production accuracy.
- It must not mutate historical experiment artifacts.
- It must not add IDs `5701–5711` to the target template.
