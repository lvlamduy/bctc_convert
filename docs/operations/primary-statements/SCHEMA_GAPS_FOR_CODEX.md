# PRIMARY statements — schema gaps and shared-contract notes for Codex review

Schema revision: `UNIVERSAL_BANK_BCTC_SCHEMA@6076` (CDKT 99, KQKD 25, LCTT 110).
Nothing below was force-mapped. Every row is kept with disposition `SOURCE_ONLY`
(or `UNRESOLVED`) and its reason in the result store, the workbook
`SOURCE_ROWS` sheet and the ledger. Counts are distinct documents / rows in
full271 at the ledger commit.

## 1. Off-balance-sheet items are registered as consolidated-only (largest gap)

The registry scopes the off-balance block of CDKT (ReportNormId 6038–6056:
guarantees, FX commitments, L/C commitments, swaps, written-off bad debts,
uncollected interest, other assets and documents, other commitments) to the
consolidated statement only. Separate (riêng lẻ / công ty mẹ) statements print
the same block. The pipeline does not map a separate-scope row to a
consolidated-only identity; it records
`POSSIBLE_SCHEMA_GAP_SCOPE:<rnid>_IS_CONSOLIDATED_ONLY`.

Examples (docs/rows): 6047 "Bảo lãnh khác" 145/151, 6041 "Cam kết giao dịch
hối đoái" 138/144, 6053 "Tài sản và chứng từ khác" 138/144, 6052 "Nợ khó đòi
đã xử lý" 137/143, 6051 "Lãi cho vay và phí phải thu chưa thu được" 132/138,
6040 "Bảo lãnh vay vốn" 131/137, 6042/6043 FX buy/sell 118/124 each, 6056
swaps 117/123, 6048 other commitments 102/102, 6046 L/C 99/99.

Proposal: extend the scope of 6038–6056 to SEPARATE (same meaning), or add
separate-scope identities. Re-running the pipeline then maps these rows
without code changes (the catalog reads scope from the registry).

## 2. Concepts printed in PRIMARY statements without a PRIMARY identity

| Statement | Printed concept | Reason code | Docs / rows |
| --- | --- | --- | --- |
| CDKT | Vốn góp liên doanh (JV investment, distinct from associates) | `POSSIBLE_SCHEMA_GAP_JOINT_VENTURE_INVESTMENT_DISTINCT_FROM_A…` | 103 / 114 |
| CDKT | Cam kết cho vay không hủy ngang | `POSSIBLE_SCHEMA_GAP_IRREVOCABLE_LOAN_COMMITMENT` | 102 / 113 |
| CDKT | Giao dịch bán và mua lại TPCP với Kho bạc Nhà nước | `POSSIBLE_SCHEMA_GAP_GOVERNMENT_BOND_REPO_WITH_STATE_TREASURY` | 82 / 82 |
| CDKT | Cam kết giao dịch tương lai / hoán đổi chéo / kỳ hạn GTCG | `POSSIBLE_SCHEMA_GAP_OFF_BALANCE_DERIVATIVE_COMMITMENT` | 72 / 83 + 16 × 5 |
| CDKT | Hạn mức tín dụng chưa sử dụng | `NARROWER_OR_DIFFERENT_OFF_BALANCE_CONCEPT_NO_SCHEMA_IDENTITY` | 16 / 16 |
| CDKT | Lợi nhuận năm nay / lũy kế năm trước (detail of 4343) | `DETAIL_OF_4343_WITHOUT_SCHEMA_IDENTITY` | 44+32+12 |
| CDKT | FX spot/swap legs (detail of 6041) | `DETAIL_OF_6041_WITHOUT_SCHEMA_IDENTITY` | 27+26+26+12+12+10+10 |
| KQKD | Lãi suy giảm trên cổ phiếu (diluted EPS) | `POSSIBLE_SCHEMA_GAP_DILUTED_EARNINGS_PER_SHARE` | 10 / 10 |
| KQKD | Operating-expense details (staff, depreciation, assets, other) | `DETAIL_OF_4391_WITHOUT_PRIMARY_SCHEMA_IDENTITY_TM_ONLY` | 14+10+8+6+2+2 |
| LCTT | Direct method "(Chi phí) khác (đã trả)" | `POSSIBLE_SCHEMA_GAP_DIRECT_OTHER_OPERATING_EXPENSE_PAID` | 35+8 |
| LCTT | Direct method "Thu nhập/(chi phí) khác" net | `POSSIBLE_SCHEMA_GAP_DIRECT_NET_OTHER_INCOME_EXPENSE_DISTINCT` | 17+9+6 |
| LCTT | Góp vốn của cổ đông không kiểm soát | `POSSIBLE_SCHEMA_GAP_FINANCING_CONTRIBUTION_FROM_NON_CONTROLL…` | 6 / 6 |

The operating-expense details exist as TM identities; the PRIMARY pipeline
does not borrow TM ReportNormIds (instruction: do not fill PRIMARY from TM).

## 3. Shared primitives used read-only

- `storage/gemini_income_tax_source_page_loader_v1.load_income_tax_source_page_json_versions_v1`
  is used read-only to authenticate selected page JSON. Its name is F39's; no
  change was made. A neutral alias in shared storage would be cleaner.
- Schema registry and templates are read through `schema/registry.py`; pins are
  verified in preflight (`UNIVERSAL_BANK_BCTC_SCHEMA@6076`, counts 99/25/110/1721).
- No shared schema, template, loader, store, exporter, manifest, TM family or
  frozen file was modified (allowed-path diff in the ledger).

## 4. Coordination envelope

PRIMARY events reuse `bctc-ai-coordination-event-v1` with `family_id: null`
and `scope.claim_scope: PRIMARY_STATEMENTS` (worker `CLAUDE_PRIMARY`). If
Codex prefers a dedicated namespace field, that is an envelope change to agree
on; no family ID was invented.
