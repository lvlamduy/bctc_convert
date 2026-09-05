# Read-only audit: exact duplicate `mapping.source_refs`

Audit ID: `sharedsourcerefsv1:audit:165a35d73503f7ebeaee9182799539d0b5e5c1f148c7c5ad5a5fec8b4736f5a7`

Verdict: `CONFIRMED_SYSTEMIC_PROVENANCE_REDUNDANCY_WITH_AUTHORITY_DEPENDENT_AFFECTED_SET_REQUIRES_STAGED_RESEAL`

## Kết luận điều hành

Không tồn tại một phát biểu đúng kiểu “exactly 13 family trên toàn hệ” nếu không gắn authority. Hai snapshot/query surfaces đều có 13 family affected nhưng khác nhau một family ở mỗi phía:

- frozen common204 compatibility inventory: 13 family, gồm legacy F26 `OTHER_PAYABLES_LIABILITIES`, không gồm F16;
- bounded current full271 artifact surface đã scan: 13 observed affected families, gồm F16 `INVESTMENT_SECURITIES`, không gồm legacy F26; F27 bị omit có khai báo vì query shape khác và các family chưa có terminal artifact không nằm trong surface này;
- intersection: 12 family; union xuyên hai snapshots: 14 logical `family_id`.

Baseline common204 phục hồi có đúng **13 family trong riêng snapshot đó** mang lỗi lặp nguyên xi một hoặc nhiều object trong `mapping.source_refs`:

`OTHER_LONG_TERM_INVESTMENTS`, `OTHER_ASSETS`, `GOVERNMENT_SBV_LIABILITIES`, `ENTRUSTED_INVESTMENT_RISK_CAPITAL`, `ISSUED_VALUABLE_PAPERS`, `OTHER_PAYABLES_LIABILITIES`, `INTEREST_INCOME`, `INTEREST_EXPENSE`, `SERVICE_ACTIVITY`, `FX_GOLD_ACTIVITY`, `TRADING_SECURITIES_ACTIVITY`, `INVESTMENT_SECURITIES_ACTIVITY`, `CAPITAL_CONTRIBUTION_DIVIDEND_INCOME`.

Trên 50 artifact common204 có output và 32.404 mappings, 13 family này có:

- 5.426 mappings tổng cộng;
- 5.372 mappings chứa ít nhất một exact duplicate, tức 99,0%;
- 12.205 source-ref occurrences trước chuẩn hóa;
- 6.141 source refs sau stable exact dedup;
- 6.064 occurrences dư thừa;
- 5.060 mappings hiện bị đóng dấu `row_id="corroborated:<ROLE>"` dù sau dedup chỉ còn đúng một source row.

Bounded current full271 scan quan sát **12.779 duplicate mappings / 13.918 redundant refs trong 13 family**, sau khi scan 24.011 mappings trên declared artifact surface. Đây không phải bằng chứng chỉ có 13 affected families trên toàn bộ 54 operational evaluators. Không có bằng chứng numeric double count trong evaluator được audit: mỗi period lane vẫn chọn đúng một cell rồi append đúng một value cell. Lỗi nằm ở provenance vector. Tuy vậy đây là integrity blocker vì nó làm sai multiplicity/`row_id`, làm đổi content-addressed `item_mapping_id`, và có thể gây đếm lặp nếu downstream dùng `source_refs` như tập toán hạng.

## Reconcile authority: common204 vs current full271

| Scope | Affected set | Mappings có duplicate | Redundant refs | Ý nghĩa |
|---|---|---:|---:|---|
| Frozen restored common204 compatibility directory | F17, F22–F26 legacy, F28–F33, F35 | 5.372 | 6.064 | Exhaustive trên 50 artifacts/32.404 mappings có trong directory; không phải current operational catalogue |
| Bounded current full271 artifact surface | F16, F17, F22–F25, F28–F33, F35 | 12.779 | 13.918 | Current query shapes in scanned artifacts; independent audit scan 24.011 mappings, with declared F27 omission |
| Intersection | F17, F22–F25, F28–F33, F35 | — | — | 12 family cùng xuất hiện ở cả hai authority |
| Common-only | legacy F26 `OTHER_PAYABLES_LIABILITIES` | 733 | 1.233 | Family đã retired khỏi current operational axis |
| Full-only | F16 `INVESTMENT_SECURITIES` | 12 | 12 | Vắng trong restored common directory do artifact freshness/query shape, không phải proof of safety |

F16 giải thích chênh lệch theo artifact freshness:

- restored file `/dev/shm/bctc-ai-27-bank-family-live-v1/family-16-investment-securities.json`, SHA `7a74610be9520397eadfcc69c51d08c3e0e146aa599f4b6321b3dab6ffa482cf`, chỉ có 573 mappings, `56 Ready / 148 Unresolved`, zero duplicate;
- later terminal common204 artifact `/dev/shm/f16-acceptance-current204-v9-final.uKoaWc/family16.json`, SHA `b6a7de27b38539398296cbe92694c11d3b04bfab73516ac3781c848f9e439b68`, có 2.539 mappings, `204 Ready`, và đúng 12 duplicate mappings trong 6 documents như full271;
- current full271 F16 artifact `/dev/shm/f16-acceptance-full271-v8-final.VXxHpQ/family16.json`, SHA `fc169f778ed5fdfc87638e14de2bc469b9dc8b03c2709eb87fb29f7a3283881e`, có 3.299 mappings, 12 duplicate mappings/12 redundant refs trong 6 documents.

F26 giải thích chênh lệch theo catalogue/query shape:

- legacy ordinal F26 `OTHER_PAYABLES_LIABILITIES` chỉ thuộc compatibility snapshot được scan;
- current operational ordinal F26 là `LOAN_INTEREST_ACCRUAL_CLASSIFICATION`, không phải cùng family. Current common204 artifact có 402 mappings/zero duplicate; current full271 có 561 mappings/zero duplicate.

Catalogue có 55 conceptual/display rows nhưng current executable axis có 54 operational evaluators; `NET_INTEREST_INCOME` là derived display concept không có source evaluator riêng. Mọi broad replay gate phải nói rõ denominator là `54 operational`, không dùng 55 như số evaluator.

## Phạm vi và authority

- Read-only hoàn toàn: không sửa repo, Git, S3, database hay provider.
- Code checkpoint: `7b2e33d900d6d10fe6e339cd31847b8a86707060`.
- Migration branch tip: `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.
- SHA-256 F17 engine: `af4cbdbf3eb63eb799b2a1a475db66726b8e9d1f3a133b0d897ebdd47d567fc5`.
- SHA-256 shared multitable evaluator: `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
- Exhaustive authority cho kết luận “đúng 13” là frozen common204 ở `/dev/shm/bctc-ai-27-bank-family-live-v1`: 50 family artifacts hiện diện, 32.404 mappings.
- Independent current full271 surface report: `/dev/shm/cross-family-audit-s3-readback.md`, SHA-256 `2a71885bc3a7eae4b526bfa39de49fa6f4a15d17dd8ba3ae3f8c791c9d8fe784`; 24.011 mappings scanned. F27 was omitted there because its artifact has a different query shape, and that omission must remain explicit.
- Current full271 affected-artifact table dưới đây có 13 current operational family. Legacy `OTHER_PAYABLES_LIABILITIES` không có mặt vì đã retired/replaced trên current axis.
- Ordinal `F17/F22/...` là nhãn artifact lịch sử. `family_id` trong JSON là định danh có thẩm quyền khi numbering drift.

## Thống kê chính xác theo family trên common204

Các cột: `M` = mappings; `R` = source-ref occurrences; `D` = mappings có duplicate; `X` = redundant occurrences; `U` = refs sau stable exact dedup; `I` = mappings đổi từ fake corroborated row ID sang singleton physical row ID nếu sửa trước seal; `Docs` = documents bị ảnh hưởng trong family.

| Ordinal | `family_id` | M | R | D | X | U | I | Docs | Artifact SHA-256 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 17 | `OTHER_LONG_TERM_INVESTMENTS` | 324 | 701 | 324 | 350 | 351 | 297 | 105 | `fde2abe6f7b80491de78e493c1ae7cda0933352c49e1394691e8bf7a561273c7` |
| 22 | `OTHER_ASSETS` | 873 | 1.816 | 873 | 908 | 908 | 838 | 105 | `66fbcec3e01d3357e225e8361a1f788b008953e578b3659f59382fceff3f5199` |
| 23 | `GOVERNMENT_SBV_LIABILITIES` | 377 | 802 | 377 | 401 | 401 | 357 | 87 | `49f20a9267ff27daf77b45d820e0621de14a46d6bcae846c7d67f3985da344d4` |
| 24 | `ENTRUSTED_INVESTMENT_RISK_CAPITAL` | 30 | 60 | 30 | 30 | 30 | 30 | 13 | `b535245253e0edfee0ee465f497c166127577469b871be98239918eec6f2376f` |
| 25 | `ISSUED_VALUABLE_PAPERS` | 402 | 866 | 348 | 385 | 481 | 310 | 74 | `dfef19c0dfcdb834db4e584cfe59ead7b2cfe625e622076e14476aa0b4ef9231` |
| 26 | `OTHER_PAYABLES_LIABILITIES` | 733 | 2.446 | 733 | 1.233 | 1.213 | 593 | 143 | `af5306912660a93ab2aa7512d18055ac41dbd4e2a6100182399b9baeefcf8e7b` |
| 28 | `INTEREST_INCOME` | 906 | 1.812 | 906 | 906 | 906 | 906 | 156 | `d9a3c82499adcbe21ce8df09933768c6c93620c0d42bfad0741c5b6242211671` |
| 29 | `INTEREST_EXPENSE` | 766 | 1.532 | 766 | 766 | 766 | 766 | 157 | `d49cab3a713ac6287e9e09998368bdbf80ee6de78d4bfe61369a2580b1027263` |
| 30 | `SERVICE_ACTIVITY` | 261 | 572 | 261 | 286 | 286 | 244 | 31 | `769edcb78eee37d659541b76f8fbb68a9dd7c657f9676c72a0493e1d00bcccdf` |
| 31 | `FX_GOLD_ACTIVITY` | 147 | 334 | 147 | 167 | 167 | 127 | 21 | `91dcb11996c85a00a4d463c7fb357d7ed0634bc2641e3de22327a2b8c284cb09` |
| 32 | `TRADING_SECURITIES_ACTIVITY` | 184 | 368 | 184 | 184 | 184 | 184 | 57 | `6e5ee63b9c187aa9754b7d816f4235d21e2635bb5942cafbaa110425989bbd02` |
| 33 | `INVESTMENT_SECURITIES_ACTIVITY` | 266 | 532 | 266 | 266 | 266 | 266 | 79 | `ff55af3c81454e609e896dd04e387f97d0baaf1ffbddbcde7f1fd94df066057a` |
| 35 | `CAPITAL_CONTRIBUTION_DIVIDEND_INCOME` | 157 | 364 | 157 | 182 | 182 | 142 | 42 | `2568ff701f1b3635e976971616bfea6191815d0da0da67a72ddde6edb8bb5a0f` |
| **Tổng** | **13 family** | **5.426** | **12.205** | **5.372** | **6.064** | **6.141** | **5.060** | — | — |

Multiplicity trước → sau exact dedup trên 5.372 mappings: `2→1: 5.060`, `3→2: 13`, `4→2: 183`, `6→3: 42`, `8→4: 15`, `10→5: 23`, `12→6: 2`, `14→7: 12`, `16→8: 6`, `18→9: 8`, `20→10: 7`, `56→18: 1`.

## State coverage chính xác trên common204

Lỗi không chỉ nằm ở direct leaf rows. State distribution trên toàn bộ 5.372 duplicate mappings là:

| State | Count |
|---|---:|
| `SOURCE_OBSERVED_ROLE_ROW` | 4.072 |
| `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER` | 785 |
| `SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE` | 111 |
| `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM` | 69 |
| `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE` | 51 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE` | 51 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE` | 49 |
| `SOURCE_VISIBLE_FAMILY_TOTAL_PROVEN_BY_EXACT_EQUATION` | 44 |
| `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_SOLE_DIRECT_CHILD_AFTER_SOURCE_TOTAL_CLOSURE` | 37 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SECTION_CONTEXT_ROLE` | 30 |
| `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT` | 21 |
| `CORROBORATED_SOURCE_VISIBLE_FAMILY_ROOT_PRESENTATIONS` | 15 |
| `SOURCE_VISIBLE_FAMILY_ROOT_DEFERRED_TO_DOCUMENT_COMPONENT_CLOSURE` | 13 |
| `STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER` | 7 |
| `SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE` | 6 |
| `SOURCE_VISIBLE_FAMILY_ROOT_PROVEN_BY_DIRECT_CHILD_FRONTIER` | 4 |
| `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_AFTER_DERIVED_STRUCTURAL_PARENT_CLOSURE` | 3 |
| `DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM` | 2 |
| `SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE` | 1 |
| `SOURCE_VISIBLE_FAMILY_ROOT_PROVEN_BY_ORDERED_CHILD_FRONTIER` | 1 |

Per-family exact state breakdown:

- `OTHER_LONG_TERM_INVESTMENTS`: `SOURCE_OBSERVED_ROLE_ROW=279`; `SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE=1`; `SOURCE_VISIBLE_FAMILY_TOTAL_PROVEN_BY_EXACT_EQUATION=44`.
- `OTHER_ASSETS`: `SOURCE_OBSERVED_ROLE_ROW=758`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=34`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE=45`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SECTION_CONTEXT_ROLE=22`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE=10`; `SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE=3`; `SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE=1`.
- `GOVERNMENT_SBV_LIABILITIES`: `SOURCE_OBSERVED_ROLE_ROW=228`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=45`; `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM=38`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE=27`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_SOLE_DIRECT_CHILD_AFTER_SOURCE_TOTAL_CLOSURE=26`; `SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE=10`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT=2`; `SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE=1`.
- `ENTRUSTED_INVESTMENT_RISK_CAPITAL`: `SOURCE_OBSERVED_ROLE_ROW=17`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=10`; `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM=3`.
- `ISSUED_VALUABLE_PAPERS`: `SOURCE_OBSERVED_ROLE_ROW=238`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=69`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_SOLE_DIRECT_CHILD_AFTER_SOURCE_TOTAL_CLOSURE=11`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE=10`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT=8`; `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM=5`; `DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM=2`; `SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE=2`; `STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER=2`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE=1`.
- `OTHER_PAYABLES_LIABILITIES`: `SOURCE_OBSERVED_ROLE_ROW=450`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=124`; `SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE=98`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE=21`; `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM=14`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SECTION_CONTEXT_ROLE=8`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE=6`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE=5`; `SOURCE_VISIBLE_FAMILY_ROOT_PROVEN_BY_DIRECT_CHILD_FRONTIER=4`; `SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE=2`; `SOURCE_VISIBLE_FAMILY_ROOT_PROVEN_BY_ORDERED_CHILD_FRONTIER=1`.
- `INTEREST_INCOME`: `SOURCE_OBSERVED_ROLE_ROW=750`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=156`.
- `INTEREST_EXPENSE`: `SOURCE_OBSERVED_ROLE_ROW=609`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=157`.
- `SERVICE_ACTIVITY`: `SOURCE_OBSERVED_ROLE_ROW=220`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=24`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT=8`; `CORROBORATED_SOURCE_VISIBLE_FAMILY_ROOT_PRESENTATIONS=7`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE=2`.
- `FX_GOLD_ACTIVITY`: `SOURCE_OBSERVED_ROLE_ROW=114`; `SOURCE_VISIBLE_FAMILY_ROOT_DEFERRED_TO_DOCUMENT_COMPONENT_CLOSURE=13`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE=10`; `CORROBORATED_SOURCE_VISIBLE_FAMILY_ROOT_PRESENTATIONS=8`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT=2`.
- `TRADING_SECURITIES_ACTIVITY`: `SOURCE_OBSERVED_ROLE_ROW=127`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=57`.
- `INVESTMENT_SECURITIES_ACTIVITY`: `SOURCE_OBSERVED_ROLE_ROW=187`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=79`.
- `CAPITAL_CONTRIBUTION_DIVIDEND_INCOME`: `SOURCE_OBSERVED_ROLE_ROW=95`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER=30`; `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM=9`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE=8`; `SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE=6`; `STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER=5`; `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_AFTER_DERIVED_STRUCTURAL_PARENT_CLOSURE=3`; `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT=1`.

Machine-readable `SCAN.json` chứa thêm exact role counts, per-family multiplicity, numeric-axis SHA và mọi đường dẫn artifact; Markdown này không lược bỏ state nào.

## Observed affected set trên bounded current full271 surface

Observed current full271 affected set trong bounded scan gồm 13 family. Tổng riêng 13 affected artifacts là 17.102 mappings, 32.546 refs, 12.779 duplicate mappings, 13.918 redundant occurrences, 18.628 refs sau dedup và 11.926 singleton row-ID corrections dự kiến. Independent broader scan đã xét 24.011 mappings để xác định observed set; bảng dưới không tự nhận là replacement release manifest hay complete 54-evaluator result.

| Family | M | R | D | X | U | I | Docs |
|---|---:|---:|---:|---:|---:|---:|---:|
| `INVESTMENT_SECURITIES` (F16) | 3.299 | 3.549 | 12 | 12 | 3.537 | 12 | 6 |
| `OTHER_LONG_TERM_INVESTMENTS` | 584 | 1.326 | 579 | 657 | 669 | 499 | 190 |
| `OTHER_ASSETS` | 1.547 | 3.358 | 1.547 | 1.678 | 1.680 | 1.416 | 271 |
| `GOVERNMENT_SBV_LIABILITIES` | 1.158 | 2.794 | 1.158 | 1.397 | 1.397 | 1.082 | 269 |
| `ENTRUSTED_INVESTMENT_RISK_CAPITAL` | 322 | 540 | 210 | 214 | 326 | 206 | 88 |
| `ISSUED_VALUABLE_PAPERS` | 1.438 | 2.840 | 954 | 1.108 | 1.732 | 784 | 182 |
| `INTEREST_INCOME` | 1.775 | 3.668 | 1.775 | 1.834 | 1.834 | 1.762 | 271 |
| `INTEREST_EXPENSE` | 1.402 | 2.547 | 1.131 | 1.138 | 1.409 | 1.124 | 271 |
| `SERVICE_ACTIVITY` | 2.150 | 4.808 | 2.150 | 2.404 | 2.404 | 1.941 | 202 |
| `FX_GOLD_ACTIVITY` | 1.446 | 2.870 | 1.316 | 1.370 | 1.500 | 1.262 | 271 |
| `TRADING_SECURITIES_ACTIVITY` | 571 | 1.127 | 556 | 556 | 571 | 556 | 227 |
| `INVESTMENT_SECURITIES_ACTIVITY` | 771 | 1.653 | 752 | 817 | 836 | 707 | 271 |
| `CAPITAL_CONTRIBUTION_DIVIDEND_INCOME` | 639 | 1.466 | 639 | 733 | 733 | 575 | 217 |
| **Tổng** | **17.102** | **32.546** | **12.779** | **13.918** | **18.628** | **11.926** | — |

Exact affected-state distribution trên 12.779 full271 duplicate mappings:

| State | Count |
|---|---:|
| `SOURCE_OBSERVED_ROLE_ROW` | 10.049 |
| `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER` | 1.008 |
| `SOURCE_VISIBLE_EXACT_FAMILY_ROOT_ONLY_ROW` | 218 |
| `DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM` | 155 |
| `SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT` | 153 |
| `PARTIAL_SOURCE_OBSERVATION` | 142 |
| `SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE` | 137 |
| `STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER` | 117 |
| `CORROBORATED_SOURCE_VISIBLE_FAMILY_ROOT_PRESENTATIONS` | 95 |
| `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT` | 95 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE` | 82 |
| `SOURCE_VISIBLE_FAMILY_TOTAL_PROVEN_BY_EXACT_EQUATION` | 82 |
| `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_DIRECT_CHILD_FRONTIER_AFTER_SOURCE_TOTAL_CLOSURE` | 76 |
| `SOURCE_VISIBLE_EXACT_RESULT_ROW_WITHOUT_COMPONENT_EVIDENCE` | 68 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE` | 62 |
| `DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_PROJECTED_FROM_SOLE_DIRECT_CHILD_AFTER_SOURCE_TOTAL_CLOSURE` | 55 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SECTION_CONTEXT_ROLE` | 45 |
| `DECLARED_ROLE_DERIVED_FROM_EXACT_VISIBLE_COMPONENT_SUM` | 41 |
| `SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SOLE_TABLE_SECTION_NARRATIVE_CONTEXT_ROLE` | 19 |
| `SOURCE_OBSERVED_ROLE_ROW_ON_EXACT_ROLE_METRIC_AXIS` | 16 |
| `ADAPTER_DERIVED_EXACT_SUM_OF_COMPONENT_ROLES` | 12 |
| `ADAPTER_DERIVED_ROOT_EXACT_VISIBLE_TERMINAL_AND_OWNER_TOTAL` | 11 |
| `SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE` | 11 |
| `SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE` | 8 |
| `SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_WITH_INCOMPLETE_BLANK_LANE_CONTROL` | 7 |
| `CORROBORATED_IDENTICAL_SOURCE_ROWS` | 6 |
| `DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL` | 6 |
| `SOURCE_OBSERVED_COMPOUND_ROLE_METRIC_PROJECTION` | 2 |
| `CORROBORATED_MULTI_SOURCE_PRESENTATIONS` | 1 |

## Root cause trong code dùng chung

1. F17 `_global_records`, dòng 2744–2764, nhân mỗi local row thành một observation cho từng lane nhưng mang theo toàn bộ row-level `source_refs` ở mỗi observation.
2. Dòng 2773–2804 chọn đúng một cell cho `CURRENT_PERIOD` và một cell cho `COMPARATIVE_PERIOD`. Sau mỗi lane, vòng lặp dòng 2802–2804 nối lại `item["source_refs"]`. Một bảng bình thường có hai cột kỳ vì vậy sinh hai object provenance byte-identical cho cùng một physical source row.
3. Dòng 2842–2846 trả vector đã lặp. F17 seal ở dòng 3062–3089 dùng `len(source_refs)` để chọn physical `row_id` hay `corroborated:<ROLE>`, rồi hash cả vector vào `item_mapping_id`.
4. Shared multitable evaluator import trực tiếp `_global_records` ở dòng 42–53 và gọi nó trong `_multitable_global_records` ở dòng 13077–13099. Comment dòng 13105–13115 đã thừa nhận lane reconciler lặp một record-level provenance ref theo từng lane và chỉ dedup một root đặc biệt.
5. Multitable compile mặc định `source_reference_identity_policy=PRESERVE_SOURCE_PRESENTATIONS` ở dòng 520–527. Opt-in `EXACT_UNIQUE_SOURCE_IDENTITIES` có stable hash dedup ở dòng 13410–13417; 12 legacy multitable configs trong nhóm 13 không bật policy này. Seal ở dòng 13458–13491 có cùng hậu quả `row_id`/content ID như F17.
6. `source_observation_mapping_contract_v1.py` hiện kiểm non-empty/bound refs và cell observation, nhưng không kiểm pairwise uniqueness. Vì gate này được runners/store gọi xuyên family, đây là vị trí thích hợp cho invariant fail-closed cuối cùng.

F16 là một producer-origin riêng, không đi qua `_global_records` trên. `gemini_json_investment_securities_family_v1.py` (SHA-256 `809e6c11d50e3970f4fff26588a84a62e031fe238a9d6cf2282ac01ff0ca7783`) có:

- `_corroborate_identical`, dòng 2715–2777: khi nhiều records có cùng coefficient axis, dòng 2775 nối mọi `record["source_refs"]`; hai semantic presentations có thể trỏ đúng cùng physical ref nên exact object bị lặp;
- dòng 3827–3834: derived single-group parent kế thừa vector đã lặp;
- seal dòng 4191–4214: `len(source_refs)>1` tạo `aggregate:<ROLE>` và hash vector vào mapping ID.

12 F16 duplicates là `2→1` trong 6 documents: `HTM_TOTAL/CORROBORATED_IDENTICAL_SOURCE_ROWS=6` và `HTM_DEBT/DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL=6`. Vì vậy sửa riêng `_global_records` không đủ; F16 cũng chứng minh tại sao cần invariant family-agnostic ở contract.

## Bằng chứng PDF trực quan

PDF nguồn: `/workspace/bctc-ai/vietstock_bctc/ABB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf`, SHA-256 `58bd3fe4b64b1b569631d335c31b6616771c54fa059b016eceaba68029060810`.

- F17, physical page 19: bảng “Góp vốn, đầu tư dài hạn” có một physical row “Các khoản đầu tư vào công ty liên doanh” và hai cột `Cuối kỳ`/`Đầu kỳ`. Mapping `JOINT_VENTURE` có values `[0,0]`, nhưng cùng exact row ref xuất hiện hai lần (`2→1`). Render: `ABB-doc003-p019.png`, SHA-256 `d5778f78bc3d8e1827abd31bbf74609e88a0e821a833f975a9211bd60470a550`.
- Non-F17 F28, physical page 23: bảng thu nhập lãi có một row “Thu nhập lãi tiền gửi” với hai giá trị `475.263`/`202.330`. Mapping `DEPOSIT_INTEREST` có values `[475263,202330]`, nhưng cùng exact row ref xuất hiện hai lần (`2→1`). Render: `ABB-doc003-p023.png`, SHA-256 `9e1df3c69ef36fb4334c1b363988bda9aeffb6e1ab85bd8ecb09d9318d897cbb`.

Hai witness xác nhận hai period cells là hai observations số trên **một** physical source row; chúng không phải hai independent provenance operands.

## Provenance redundancy, không phải numeric double count đã chứng minh

Stable exact dedup được đề xuất chỉ biến đổi `source_refs`. Nó không chạm `report_norm_id`, `role`, `unit`, `state`, `values`, equation/frontier hay source cell selection. Trong inspected code, `cells.append(...)` chạy một lần sau khi chọn một candidate cho mỗi lane; phép lặp chỉ xảy ra khi nối provenance vector.

Do đó:

- đã chứng minh: exact provenance redundancy, false corroboration multiplicity và content-identity churn;
- chưa chứng minh: evaluator cộng một numeric operand hai lần hoặc làm đổi current/comparative values;
- vẫn phải fail closed: downstream có quyền coi `source_refs` là distinct witnesses/operands, nên giữ duplicate sẽ tạo semantic risk.

Distinct refs phải được bảo toàn. Hai refs có cùng `row_id` nhưng khác page/table/locator/hierarchy/label/cell/money-column frontier không phải exact duplicate và không được gộp.

## Invariant dùng chung đề xuất

> Every emitted `mapping.source_refs` list is non-empty and pairwise unique under exact typed canonical JSON identity; distinct source rows, pages, tables, hierarchy paths, labels, or money-column frontiers remain distinct.

Áp dụng theo nguyên tắc “normalize at the proven semantic origin, validate everywhere”:

- Một pure helper thực hiện first-occurrence stable dedup bằng `canonical_json_bytes_v1(ref)`; không dedup theo `row_id`, nhãn hay digest-only key.
- Lane lineage: gọi helper khi `_global_records` đóng một reconciled same-role record, trước F17/multitable mapping seal. Đây là nơi semantic context chứng minh exact ref bị lặp do hai period lanes.
- F16 lineage: gọi cùng helper trong `_corroborate_identical` sau khi equal-axis corroboration đã được chứng minh, trước khi derived parent kế thừa provenance.
- Bổ sung `SOURCE_REFS_EXACT_IDENTITY_IS_NOT_UNIQUE` vào `source_observation_mapping_contract_v1`; mọi duplicate còn sót phải fail closed trước persistence/publication.
- Giữ các opt-in policies hiện hữu tương thích, nhưng exact byte-identical duplicate không còn được diễn giải là hai presentations. `PRESERVE_SOURCE_PRESENTATIONS` chỉ bảo toàn các presentation thực sự khác nhau.

Không đặt một silent generic dedup ngay cuối mapping seal cho mọi state. Cách đó có thể che giấu việc cùng một physical row bị dùng hai lần như hai arithmetic operands. Contract cuối phải reject; auto-normalization chỉ xảy ra ở producer origin đã chứng minh provenance reuse.

### Khuyến nghị implementation ưu tiên số 1

Tạo một canonical-bytes stable-unique helper dùng chung, áp dụng ở đúng **hai bounded semantic origins**: `_global_records` cho lane lineage và F16 `_corroborate_identical` cho identical-presentation lineage; sau đó đặt global uniqueness assertion ở source-observation contract. Không sửa riêng từng F17/F22–F35 adapter; không dedup theo row ID; không reseal lẫn vào family feature work đang chạy.

Vì `_global_records` của F17 được multitable import trực tiếp và multitable evaluator đang hash-frozen, thay đổi này là architectural/shared change dù patch nhỏ. F16 là second bounded producer edit. Phải thực hiện trên branch riêng, review riêng và replay toàn bộ released family surface theo migration gate trước khi merge vào các family branches.

### Negative-state/fail-closed policy

- Auto-normalize chỉ tại hai origin đã chứng minh ở trên; unknown producer/state → reject, không tự chữa.
- Nếu exact duplicate còn tồn tại trong `AGGREGATED_*`, `DERIVED_*`, equation/component frontier, hoặc state chứa `SUM`, contract phải fail closed trừ khi producer-origin receipt chứng minh duplicate do provenance reuse và component source identities vẫn complete/disjoint.
- Cùng `row_id` nhưng khác canonical locator/page/table/hierarchy/cell/money-column frontier phải giữ riêng.
- Hai refs khác object nhưng cùng label/value không bao giờ được gộp.
- Duplicate removal không được làm đổi role/unit/state/value/equation/numeric-axis; bất kỳ delta nào ngoài provenance multiplicity, corrected synthetic row ID và dependent content IDs đều fail.
- Empty refs, null/malformed refs, blank-as-zero, overlapping parent+child frontier, conflicting periods/units và arithmetic backsolve vẫn giữ typed negative disposition; uniqueness repair không được nâng chúng thành Ready.

## Identity churn và migration an toàn

Ngay trên frozen common204 compatibility snapshot, ít nhất 5.372 `item_mapping_id` phải được reseal vì material hash chứa `source_refs`; trong đó 5.060 `row_id` cũng phải trở về exact physical row ID. Trên current operational full271 affected set, tương ứng là 12.779 mapping IDs và 11.926 synthetic `corroborated:`/`aggregate:` row IDs. Candidate/sweep/audit/store IDs có material phụ thuộc mapping phải được giả định là cascade-changed cho tới khi delta receipt chứng minh ngược lại.

Không overwrite hoặc relabel historical artifacts/databases. Phát hành additive version mới và một translation receipt old→new. Semantic join key tối thiểu cho receipt:

`(source_sha256, report_norm_id, role, unit, state, values, ordered_unique_source_refs)`.

Receipt phải ghi old/new item mapping ID, old/new row ID, old/new ref multiplicity, canonical unique-ref identity, reason `EXACT_DUPLICATE_SOURCE_REF_REMOVED`, producer commit/config/code hashes và before/after numeric-axis hash. Không dùng list position hay ordinal family làm authority.

## Kế hoạch staged migration và test

### Stage 0 — isolate/freeze

- Không trộn shared repair vào F36/F37/F39 hay family feature branches đang chạy.
- Chốt architectural decision và authoritative family/release denominator.
- Dùng immutable DB/cache để replay; không gọi Gemini/provider cho lỗi deterministic này.

### Stage 1 — red tests, helper, global gate

- Red unit test tái hiện một physical row/two period lanes → refs `2→1` nhưng values giữ hai cells.
- F16 red tests tái hiện `CORROBORATED_IDENTICAL_SOURCE_ROWS` và derived `HTM_DEBT` cùng trỏ một physical total; normalize ở `_corroborate_identical`, không tại generic arithmetic seal.
- Test one-lane/partial-lane, near-duplicate refs, same `row_id` nhưng locator/cell khác, distinct aggregate child rows, order preservation, non-empty constraint và repeated duplicate multiplicity.
- Dùng canonical bytes thay digest-only identity, loại bỏ collision ambiguity.
- Thêm contract test để duplicate surviving normalization fail với typed reason.
- Target suites tối thiểu:
  - `tests/unit/test_gemini_json_other_long_term_investments_family_v1.py`;
  - `tests/unit/test_gemini_json_multitable_hierarchical_family_v1.py`;
  - `tests/unit/test_source_observation_mapping_contract_v1.py`;
  - focused adapter/storage tests cho 13 families và persistence gate.

### Stage 2 — common204 shadow delta replay

- Replay deterministic từ immutable DB/cache cho đúng 13 family của frozen common204 compatibility set trước; ghi rõ đây gồm legacy F26 và chưa đại diện current F16 artifact.
- Chạy later terminal common204 F16 như một delta cohort riêng và yêu cầu đúng `12 mappings / 12 redundant refs / 6 documents` trước sửa, zero sau sửa.
- Assert document disposition, Ready/NotObserved/Unresolved counts, mapping count, `report_norm_id`, role, unit, state, values, equation/frontier receipts và ordered **unique** ref set không đổi.
- Chỉ cho phép thay đổi: exact duplicate multiplicity, corrected physical `row_id`, content-addressed IDs và receipts phụ thuộc các IDs đó.
- Assert đúng baseline impact: `5.426 M / 12.205 R / 5.372 D / 6.064 X / 6.141 U / 5.060 I`.
- Chạy hai cụm review độc lập: balance/liability `F17,F22–F26`; income/activity `F28–F35`. Spot-check PDF gồm ABB p19 và p23.

### Stage 3 — unaffected-family/no-regression gate

- Scan tất cả common204 family artifacts, không chỉ nhóm 13.
- Family không affected phải byte-equal hoặc semantic-equal theo declared identity policy; mọi emitted mapping phải có zero exact duplicate refs.
- Không dùng “tests pass” thay cho artifact-level delta accounting.

### Stage 4 — full271 và broad released-family replay

- Chỉ mở full271 khi common204 xanh.
- Replay đủ 13 current operational affected families từ cache/DB, rồi scan toàn bộ authoritative executable registry; gate hiện hành phải là `54/54 operational evaluators zero duplicate mappings`. Conceptual/display count 55 không được dùng làm evaluator denominator.
- F27 query-shape omission phải được đóng bằng adapter-aware scan hoặc một typed explicit exclusion receipt; không được lặng lẽ coi là PASS.
- Do shared imported code thay đổi, chạy broad regression bắt buộc cho tất cả released operational families, kể cả các families không thấy lỗi trong common204 scan.
- Assert numeric-axis SHA/semantic payload ổn định; mọi sai khác ngoài allowlist phải fail closed.

### Stage 5 — additive publish

- Independent reviewer kiểm artifact delta, PDF witnesses và translation receipt.
- Commit/push code+tests+receipts trước; publish immutable DB/artifact version mới sau khi toàn bộ gates xanh.
- Không xóa/overwrite historical DB/S3 objects. S3 manifest ghi exact object/version IDs, hashes, counts và parent release.
- Provider remains unused; DB/cache handles deterministic replay, và full replay chỉ chạy một lần tại checkpoint sau các bounded deltas.

## Reproduction files

- Machine-readable scan: `/dev/shm/shared-provenance-audit-views/SCAN.json`.
- Read-only scanner: `/dev/shm/shared-provenance-audit-views/scan_exact_duplicate_source_refs.py`.
- PDF renders: `/dev/shm/shared-provenance-audit-views/ABB-doc003-p019.png`, `/dev/shm/shared-provenance-audit-views/ABB-doc003-p023.png`.

`SCAN.json` là exact machine-readable count authority cho báo cáo này; Markdown là interpretation và migration recommendation, không phải release receipt.
