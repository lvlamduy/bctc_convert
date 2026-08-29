# Unresolved mapping and adjudication review ledger

Updated: 2026-08-25 (UTC)

This is the cumulative human-readable file requested for every source item or
family region that could not initially be mapped.  Entries remain here after
resolution so the project owner can audit the original issue, the adjudication,
and the exact result that closed it.  `NO_COMPLETE_REGION` alone never means a
family is absent; report-level absence is recorded only when the project owner
explicitly confirms it for the bound PDF.

This is the single cross-family review file.  Every new unresolved entry records,
when applicable: family, bank, report and reporting period, exact PDF/page/region
locator, raw VietOCR Transformer text, accentless normalized text, independent
pixel transcription when they disagree, visible values and axes, nearest schema
candidate, accounting/structure checks that passed or failed, the unresolved
reason, and the next evidence needed.  Bank/report/page fields are evidence
locators only and are never parser or mapping conditions.

Completion rule: every family checkpoint must update both this ledger and
`COMPLETED_TM_FAMILIES.md` in the same change. A nonzero unresolved count must
have one auditable filing row per unresolved trial here; a zero count must be
stated explicitly. A family is not complete for handoff if either file is
missing that update.

Ledger total: **545 entries = 205 OPEN + 340 closed/history**. The 340 is the
existing **210 row/graph resolutions + 88 confirmed bound-report family
absences + 42 superseded Family 3 review rows**. The canonical OPEN queue now
contains **205 rows outside Family 3**: **134 annual-2025 + 71
historical/current**. This replaces the stale 247/298 summary after E-0178 closed
all 42 current Family 3 trials, and also replaces the older 143/101 summary which omitted
E-0158/E-0159/E-0161 and historical/current OPEN rows. Bank/report/page fields
are evidence locators only, never matching rules.

<a id="canonical-open-source-rows"></a>

## Canonical OPEN — một dòng cho mỗi source-row/filing

Đây là queue OPEN duy nhất có hiệu lực để con người review: **205 dòng**, gồm
**134 dòng annual-2025 + 71 dòng historical/current** ngoài Family 3; đủ 38 dòng
E-0158/E-0159/E-0161 từng bị index bỏ sót. 42 dòng Family 3 cũ đã chuyển thành
closed history bởi E-0178 và nằm ngoài marker canonical này. PM-001 không thuộc
queue vì period gap cũ đã stale/superseded khi corpus có VPB Q2/2026.

DIRECT_PIXEL_REVIEW_2026-08-24 chỉ dùng cho sáu physical page vừa mở trực tiếp. PERSISTED_CODEX_PIXEL_REVIEW/PERSISTED_PIXEL_CROP_REVIEW là tái sử dụng artifact pixel/crop đã niêm phong, không giả là vừa mở lại PDF. Mọi dòng OPEN đều có bằng chứng trực tiếp hoặc persisted.

<!-- STALE_SCHEMA_PIN_LIVE_REPLAY_BEGIN -->

### Lưu ý bắt buộc replay schema sống

Audit ngày 2026-08-24 phát hiện **84 cặp hash/kích thước không còn khớp** trên
bảy file schema sống được 12 formal artifact cũ tham chiếu. PDF nguồn và bằng
chứng pixel/crop của các artifact này vẫn giữ nguyên danh tính; riêng kết luận
“schema gap” lịch sử **không phải exact replay của schema hiện hành**. Vì vậy,
mọi dòng schema-gap thuộc bảng dưới đây mang trạng thái
`KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY`: phải chạy lại đối
chiếu với schema sống trước khi đóng, không được dùng pin lịch sử để khẳng định
leaf vẫn thiếu.

| Formal artifact có pin schema cũ | Số dòng OPEN schema-gap phải replay sống |
| --- | ---: |
| `docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json` | 12 |
| `docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json` | 0 |
| `docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json` | 8 |
| `docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json` | 4 |
| `docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json` | 1 |
| `docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json` | 0 |
| `docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json` | 13 |
| `docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json` | 0 |
| `docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json` | 29 |
| `docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json` | 0 |
| `docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json` | 2 |
| `docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json` | 7 |
| **Tổng** | **76** |

Bảy reference cần replay sống:
`config/schemas/hierarchy_reference.yaml`, `config/schemas/sources.yaml`,
`data/registered/hierarchy_registry.json`,
`data/registered/schema_coverage_registry.json`,
`data/registered/schema_registry.json`, `reference/schemas/schema_graph.jsonl`,
và `template/Bank_TM_ReportNormId.v2.xlsx`. Các disposition không phải schema-gap
trong 12 artifact trên không bị đổi bởi lưu ý này.

<!-- STALE_SCHEMA_PIN_LIVE_REPLAY_END -->

<!-- HISTORICAL_FAMILY3_OPEN_SOURCE_ROWS_BEGIN -->

| Composite ID | Trial / source-row | Family | Ngân hàng / kỳ / scope / assurance | PDF path + SHA-256 | Physical / printed page | PDF_VIEWED | Trạng thái | Nguyên nhân tiếng Việt dễ hiểu | Machine reason / formal ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F3-IDL-575-001 | trial 1; source IDL-575-001 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p7, p46; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Bảng tóm tắt p7 in đúng tổng `149.990.681 / 117.882.259` và dẫn `Thuyết minh 6`; p46 phân rã đúng cùng population. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:TERM_DEPOSIT_GROUP`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-002 | trial 3; source IDL-575-002 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / H1 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/ACB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:94cbe09e3533cc2354055253811f33df40a6c56461cfe131b12e75cea7a36366 | physical p7, p45; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Bảng tóm tắt p7 in `125.447.269 / 117.882.259` và dẫn `Thuyết minh 6`; p45 là bảng chi tiết của đúng population đó. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-003 | trial 5; source IDL-575-003 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q1 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf<br>sha256:5a22f62d8b2853423f71fab7d09e42f96cf8dc3eacd9032836febb5550198db7 | physical p15; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `129.347.480 / 117.882.259`; lane so sánh có khoản vay `150.979` và dự phòng `(50.000)`, còn các ô ngoại tệ/dự phòng hiện kỳ là dấu gạch bị crop bỏ. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-004 | trial 6; source IDL-575-004 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q1 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/ACB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf<br>sha256:d8258cc1695acfcf8ebe6edfff5fdaa67dddb30dc8f47571d8a5d59b7e0dbbd3 | physical p15; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `115.347.683 / 108.003.288`; khoản vay ngoại tệ là `- / -` và dự phòng cho vay là `- / (50.000)`, nhưng các dash không thành role-lane đầy đủ. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-005 | trial 11; source IDL-575-005 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q4 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf<br>sha256:ad6cab1acd7556f8ee0372764f732f2efe8746b36b5517761f68762b095b07b7 | physical p16; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `149.990.681 / 117.882.259`; khoản vay là `- / 150.979`, dự phòng so sánh `(50.000)` và một số dash cùng hàng bị detector bỏ. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-006 | trial 12; source IDL-575-006 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q4 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/ACB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf<br>sha256:28937fe83d897bd6466b2bb9e5831dbeda0f68cf81982c6ac1b15c6dec899f71 | physical p16; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `139.216.637 / 108.003.288`; các dòng ngoại tệ/dự phòng có dash và lane so sánh `(50.000)`, nên OCR text-only làm mất cấu trúc hai kỳ. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-007 | trial 17; source IDL-575-007 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | MBB / Q1 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf<br>sha256:09421ed8d0d7a6dd3eece828b64be46d053aff70b4870bb27afc405b0e27cd33 | physical p29; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal tiền gửi in `53.258.553`, trong khi ba child engine đã giữ chỉ cộng `7.228.307 + 5.711.171 + 37.081.841 = 50.021.319`; bảng còn một child tiền tệ cùng group. | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSIT_GROUP`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-008 | trial 18; source IDL-575-008 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | MBB / Q1 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/MBB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf<br>sha256:c4aea54c740ce5c2b825b69752ef4779cd5cb05ab261f1b4399ddc633738903e | physical p26; trang in: p18 | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | KEEP_UNRESOLVED_SOURCE_CONFLICT | Trên lane `31/12/2024`, sáu dòng in `5.499.868 + 5.157.164 + 55.404.500 + 3.361.724 + 2.881.932 + 0 = 72.305.188`, nhưng tổng in `72.305.186`; lệch 2 triệu đồng. | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-009 | trial 25; source IDL-575-009 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p42; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Bảng số tiền có dòng `Cấp tín dụng bằng ngoại tệ`, nhưng bảng lãi suất ngay cùng trang dùng đơn vị `%/năm` và giá trị `Không áp dụng`; engine đang trộn hai bảng. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-010 | trial 26; source IDL-575-010 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VPB / Năm 2025 / BCTC công ty mẹ/riêng lẻ / kiểm toán | vietstock_bctc/VPB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf<br>sha256:af79940cbde9bd50850fe0dfc4cf8ba78a8d0f4b5340e6f0cc0368a12cfbc788 | physical p36; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Dòng tiền `Cấp tín dụng bằng ngoại tệ` nằm trên bảng balance, còn `%/năm`/`Không áp dụng` thuộc bảng lãi suất phía dưới; hai surface bị nhập chung. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-011 | trial 27; source IDL-575-011 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VPB / H1 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/VPB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:c9f27ab6b1d69611209dee51e5bd9dc91dd74f491abf4f25a01821964266eecf | physical p44; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Trên p44, `Cấp tín dụng bằng ngoại tệ` của bảng số tiền đứng gần bảng lãi suất có header `%/năm` và ô `Không áp dụng`; lỗi là nhầm loại bảng. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-012 | trial 28; source IDL-575-012 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VPB / H1 2025 / BCTC công ty mẹ/riêng lẻ / soát xét | vietstock_bctc/VPB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:a1e74b14a1d601e7bec8e18795bca623ce66b184f12dc6031a45e20558e3cf27 | physical p36; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Bảng balance và bảng rate cùng chứa nhãn tín dụng/TCTD, nhưng chỉ bảng rate in `%/năm` và `Không áp dụng`; engine chưa chặn cross-table binding. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-013 | trial 37; source IDL-575-013 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p34; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `27.921.384 / 7.374.353`; nhóm `Trong đó: Chiết khấu, tái chiết khấu` lặp, khoản vay VND có `- / 1.157.667`, và dash làm thiếu lane. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-014 | trial 38; source IDL-575-014 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Năm 2025 / BCTC công ty mẹ/riêng lẻ / kiểm toán | vietstock_bctc/HDB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf<br>sha256:082e0fe75550085df0b73351afd3f3561ba1b716bbbf0157bcf1e11f34b78ae8 | physical p33; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `31.521.384 / 12.474.353`; subgroup `Chiết khấu, tái chiết khấu` xuất hiện lặp và khoản vay VND có dash cạnh `1.157.667`. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-015 | trial 39; source IDL-575-015 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / H1 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/HDB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:fe89f3c5a0886370cbbc506364d784963d3fda8c44ad03f31e10313e9f02e11f | physical p31; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Các nhánh có subtotal cục bộ; dòng cuối `7.746.366 / 7.374.353` là footer/subtotal của nhánh gần nhất, không phải một family total tự do. | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-016 | trial 40; source IDL-575-016 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / H1 2025 / BCTC công ty mẹ/riêng lẻ / soát xét | vietstock_bctc/HDB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:474bb77c099bdc0865a5aeaf16be18351b612325f717a9a39bc83f07aaf12cd9 | physical p30; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | footer cuối `10.446.366 / 12.474.353` đứng sau các subtotal tiền gửi/cho vay cục bộ; engine đang thử nó như tổng của population rộng hơn. | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-017 | trial 41; source IDL-575-017 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Q1 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf<br>sha256:5d163e501bea8f8b962c246ae9a811c756574a2d0efc83895609f5a415e5a28b | physical p3; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `8.833.734 / 7.374.353`; dòng `Dự phòng rủi ro` là sibling/contra ở cấp family với `- / -`, không phải child duy nhất phải cộng ra subtotal cho vay. | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-018 | trial 42; source IDL-575-018 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Q1 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/HDB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf<br>sha256:e4423025c872b514804c50d7d6882290cff6abe5e418a2b577dfd4fd565ac10a | physical p3; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `13.583.734 / 12.474.353`, còn `Dự phòng rủi ro - / -` là sibling root; hierarchy hiện tại kéo nó xuống sai nhánh. | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-019 | trial 43; source IDL-575-019 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Q2 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf<br>sha256:58b2c92247a2c49312861b182ffdfab8cb813ccde8cc9231289a07a03a6c9f9c | physical p3; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `7.746.366 / 7.374.353`; provision `- / -` là sibling root ngang cấp với nhánh tiền gửi/cho vay, không phải component của subtotal. | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-020 | trial 44; source IDL-575-020 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Q2 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/HDB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf<br>sha256:ef08f65eb1dc9f07dafdeec05372d9d8d267593549cff4b9acd7577fb415ac4f | physical p3; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `10.446.366 / 12.474.353`; provision sibling root kế tiếp có hai dash nhưng bị đưa vào tập component sai population. | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-021 | trial 45; source IDL-575-021 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Q3 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf<br>sha256:88d7f95685de6c070fba76966b5a7f861aaec0eb9e5874aac0529b39b8d8355a | physical p3; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `13.618.632 / 7.374.353`; provision là sibling root và detector chỉ giữ một trong hai dash nhìn thấy. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-022 | trial 46; source IDL-575-022 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | HDB / Q3 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/HDB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf<br>sha256:d9187258556cee67b17748e17c5721ca6721ac362b1364bb0ae406b45f8b749a | physical p3; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Subtotal cho vay in `17.218.632 / 12.474.353`; sibling root provision có hai dash nhìn thấy nhưng một lane bị bỏ và hierarchy đang ở sai cấp. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-023 | trial 62; source IDL-575-023 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | CTG / Năm 2025 / BCTC công ty mẹ/riêng lẻ / kiểm toán | vietstock_bctc/CTG/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf<br>sha256:87f852400bf25421aa80000436387f25c5382bfd0d72a4d67122493361b486e6 | physical p39–40; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p39 chứa nhánh tiền gửi, p40 tiếp sang nhánh cho vay và **lặp lại ngay** header kỳ/đơn vị; tại p40 `5.922.473 + 8.883.891 = 14.806.364`, lane so sánh `2.500.000 + 1.111.649 = 3.611.649`. | `CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN`<br>`COLUMN_CONTEXT:CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-024 | trial 64; source IDL-575-024 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | CTG / H1 2025 / BCTC công ty mẹ/riêng lẻ / soát xét | vietstock_bctc/CTG/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:79714aee142d29b8673880e128cca1d9911ee93dadcd8b552bbbee6e9c8f08ac | physical p11, p21; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p11 là bảng số tiền thật; p21 chỉ là prose chính sách có cụm `tiền gửi/cho vay TCTD khác`, không có topology bảng tiền. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_2:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-025 | trial 65; source IDL-575-025 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | CTG / Q1 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất quý 1 năm 2025.pdf<br>sha256:244171fc77a8ab7e8685b90a74ea8a52f00f3ad622864b591affcea21f953065 | physical p4; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tiền gửi in `401.757.806 / 370.530.038`, cho vay `4.821.450 / 7.952.847`; provision `- / -` là sibling/contra cấp family chứ không phải component duy nhất của loan. | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-026 | trial 75; source IDL-575-026 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | BID / H1 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/BID/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:1e12da259d3cd63629cf01d546135363a289f20bff85fcd6a1db2f0af3371b71 | physical p9; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Nhãn provision bị xuống dòng nhưng số `(102.971) / (80.854)` vẫn thuộc family; tổng nhìn thấy khép `381.762.553 + 10.938.582 - 102.971 = 392.598.164` và `268.366.137 + 11.686.232 - 80.854 = 279.971.515`. | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM`<br>`HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-027 | trial 86; source IDL-575-027 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Năm 2025 / BCTC công ty mẹ/riêng lẻ / kiểm toán | vietstock_bctc/VIB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf<br>sha256:61e5cc0bbc8da93fa8aaa540afd8125c1517f45c801b0e450fc6efd1f6a53d20 | physical p9, p37; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p9 là summary có lane tham chiếu `Thuyết minh`; p37 mở đúng cùng population thành các dòng không kỳ hạn/có kỳ hạn và VND/ngoại tệ. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-028 | trial 87; source IDL-575-028 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / H1 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:aee7fe9d825852e656c0912513e9720bec872f009ce93013256380c949a1e424 | physical p9, p37; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p9 chỉ tóm tắt owner/tổng và số `Thuyết minh`; p37 là detail cùng kỳ với các hàng currency, không phải population thứ hai. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-029 | trial 88; source IDL-575-029 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / H1 2025 / BCTC công ty mẹ/riêng lẻ / soát xét | vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf<br>sha256:1e56fffdff551caf6dec5b13c57e4817f54e84c5d0c51f818978d17f28173105 | physical p10, p38; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Summary p10 có cột `Thuyết minh`, còn p38 phân rã cùng tổng thành VND/ngoại tệ; engine đang coi cả hai là candidate ngang nhau. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-030 | trial 89; source IDL-575-030 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q1 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét quý 1 năm 2025.pdf<br>sha256:5b2b6a8d135a6dac734a8cc08cf8125be99776002f61287dcf1f2786d147e52d | physical p9, p37; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Owner/tổng tại p9 dẫn bằng lane `Thuyết minh`; p37 lặp owner rồi có các child currency của cùng population. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:COLUMN_CONTEXT:DECLARED_UNIT_KIND_AXIS_LENGTH_DIFFERS_FROM_BODY_COLUMNS`<br>`CANDIDATE_1:COLUMN_CONTEXT:PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN`<br>`CANDIDATE_1:COLUMN_CONTEXT:UNIT_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-031 | trial 90; source IDL-575-031 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q1 2025 / BCTC công ty mẹ/riêng lẻ / soát xét | vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét quý 1 năm 2025.pdf<br>sha256:f58da65f95cc1979f35feb0ea93fa11c3d034ccdaf24bbbeb95a4141bc857568 | physical p10, p37; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p10 là balance-sheet summary có note reference, p37 là note detail với `Tiền gửi không kỳ hạn`, `Tiền gửi có kỳ hạn`, `Cho vay`; đây là hai mức trình bày của một tổng. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-032 | trial 92; source IDL-575-032 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q2 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/VIB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf<br>sha256:21d618c30b343908190c56066b2db54c7de1a886cf7556023b3b2f6d50012ed9 | physical p5, p32; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Summary p5 có owner/tổng cùng cột `Thuyết minh`; detail p32 mới chứa các hàng VND/ngoại tệ của đúng tổng đó. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-033 | trial 93; source IDL-575-033 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q3 2025 / BCTC hợp nhất / soát xét | vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét 9 tháng đầu năm 2025.pdf<br>sha256:7ff7c257c012eba17ed732065a1df4bc6024f9bec50270fe1c7abc96a861e3cd | physical p8, p36; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p8 trình bày summary kèm lane `Thuyết minh`, p36 trình bày currency detail của cùng family/kỳ; không có hai population độc lập. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-034 | trial 94; source IDL-575-034 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q3 2025 / BCTC công ty mẹ/riêng lẻ / soát xét | vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét 9 tháng đầu năm 2025.pdf<br>sha256:b4abb04963bf0a4ce560ea65853e3aad6c9a26818f66ceb3d3f105af60774884 | physical p9, p37; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Summary p9 dẫn note bằng `Thuyết minh`; p37 mở các dòng không kỳ hạn/có kỳ hạn và cho vay của cùng tổng nguồn. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-035 | trial 95; source IDL-575-035 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q4 2025 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf<br>sha256:e6276e8e43f3aa22c70ebb082fd212845dcde23e217b1c72f8116690c03bf008 | physical p5, p33; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p5 chỉ có family summary/note reference; p33 có đầy đủ child VND/ngoại tệ của cùng population, nên hai candidate không được cộng dồn. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-036 | trial 96; source IDL-575-036 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q4 2025 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/VIB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf<br>sha256:5f8510194f53e98172092b8d4cb0ca1b237791d772035e58c2b61eecb42fac8f | physical p5, p32; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Summary p5 và detail p32 có cùng owner/kỳ; p32 chứa các dòng currency trong khi p5 có lane `Thuyết minh`. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-037 | trial 99; source IDL-575-037 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/20260422 - ACB - BCTC Hop nhat Quy 1 nam 2026.pdf<br>sha256:a85402445a34e80dd4248471c2d23d4cf4b349ab2455b91db457f3e6effbdd4a | physical p16; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `131.619.452 / 149.990.681`; khoản vay VND `2.000.000 / -`, còn các dòng ngoại tệ/provision có dash hoặc ô không sinh text nên thiếu lane. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-038 | trial 100; source IDL-575-038 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q1 2026 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/ACB/2026/20260422 - ACB - BCTC Rieng le Quy 1 nam 2026.pdf<br>sha256:0b1c3d36212d77072fb53640073b2c6b888609d4e1f0369f92e10d53d8067c6c | physical p16; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `119.456.384 / 139.216.637`; khoản vay VND `3.399.504 / 1.294.915`, ngoại tệ `- / -`, còn provision không có đủ text box. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-039 | trial 101; source IDL-575-039 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86 | physical p16; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `123.441.277 / 149.990.681`; khoản vay VND `6.392.840 / -`, các ô ngoại tệ và provision là dash nhưng detector bỏ một phần lane. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-040 | trial 102; source IDL-575-040 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | ACB / Q2 2026 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf<br>sha256:4bb54ef4451ecee9aa4e55b68e076dea2a4a2b9783d0d6165f7161bcc40438f7 | physical p16; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Tổng in `113.314.155 / 139.216.637`; khoản vay VND `8.229.242 / 1.294.915`, còn ngoại tệ/provision dùng dash không được bind đủ. | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`<br>`VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-041 | trial 139; source IDL-575-041 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p5, p32; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | p5 là summary có lane `Thuyết minh`; p32 là detail cùng population với các hàng VND/ngoại tệ và subtotal cho vay. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>formal: #family-3-rnid-575-unresolved |
| F3-IDL-575-042 | trial 140; source IDL-575-042 | Tiền gửi tại/cho vay TCTD khác — tài sản (575) | VIB / Q2 2026 / BCTC công ty mẹ/riêng lẻ / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf<br>sha256:98bd6458eb223b168acf4795703f6ae628dcec166ef0ef07d402fb86636a86ef | physical p5, p32; printed: không ghi nhận | PERSISTED_DIRECT_PIXEL_REVIEW — 58 renders/42 filings; ref #open-family3-rnid575 | RESOLVABLE_PENDING_GENERIC_FIX | Summary p5 và detail p32 là cùng population; ngay sau detail p32 bắt đầu family kế tiếp, nên candidate hiện bị kéo quá ranh giới. | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`<br>`CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>formal: #family-3-rnid-575-unresolved |
<!-- HISTORICAL_FAMILY3_OPEN_SOURCE_ROWS_END -->

<!-- CANONICAL_OPEN_SOURCE_ROWS_BEGIN -->

| Composite ID | Trial / source-row | Family | Ngân hàng / kỳ / scope / assurance | PDF path + SHA-256 | Physical / printed page | PDF_VIEWED | Trạng thái | Nguyên nhân tiếng Việt dễ hiểu | Machine reason / formal ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

| E0073-OA-001 | doc 3; source OA-001 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu bán tài sản tài chính” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Source is broader than schema 976 Phải thu từ bán chứng khoán; no forced narrowing.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-002 | doc 3; source OA-002 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:No equivalent receivable child in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-003 | doc 3; source OA-003 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p52; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Số dư đầu kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Other-asset provision roll-forward has no equivalent branch in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-004 | doc 3; source OA-004 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p52; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Trích lập dự phòng rủi ro trong kỳ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Other-asset provision roll-forward has no equivalent branch in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-005 | doc 3; source OA-005 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p52; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Số dư cuối kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Other-asset provision roll-forward has no equivalent branch in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-006 | doc 3; source OA-006 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p52; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng tài sản Có rủi ro tín dụng” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Closing provision decomposition is not the asset-quality population 1018.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-007 | doc 3; source OA-007 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p52; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng cụ thể” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:No equivalent other-asset provision child in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-008 | doc 3; source OA-008 | Tài sản Có khác | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p52; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng rủi ro phải thu khó đòi” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:No equivalent other-asset provision child in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-009 | doc 8; source OA-009 | Tài sản Có khác | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p39; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu từ Ngân sách Nhà nước” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Not equivalent to schema 979 Phải thu từ NHNN Việt Nam.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-010 | doc 8; source OA-010 | Tài sản Có khác | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p39; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu từ hoạt động tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:No equivalent receivable child in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-011 | doc 8; source OA-011 | Tài sản Có khác | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p39; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu hoa hồng bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:Not proven equivalent to receivable from an insurance subsidiary.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0073-OA-012 | doc 8; source OA-012 | Tài sản Có khác | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p39; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0073-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Tài sản thuế TNDN hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0073:No equivalent child in family 966-1023.<br>formal: docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json |
| E0076-IVP-005 | doc 3; source IVP-005 | Phát hành giấy tờ có giá | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p56; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0076-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Trục/hàng “Phát hành giấy tờ có giá theo kỳ hạn gốc / Dưới 12 tháng” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0076:WHOLE_FAMILY_TENOR_AXIS_IS_NOT_ONE_INSTRUMENT_SPECIFIC_SCHEMA_LEAF<br>formal: docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0076-IVP-006 | doc 3; source IVP-006 | Phát hành giấy tờ có giá | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p56; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0076-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Trục/hàng “Từ trên 12 tháng đến 5 năm” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0076:WHOLE_FAMILY_TENOR_AXIS_IS_NOT_ONE_INSTRUMENT_SPECIFIC_SCHEMA_LEAF<br>formal: docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0076-IVP-007 | doc 3; source IVP-007 | Phát hành giấy tờ có giá | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p56; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0076-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Trục/hàng “Từ trên 5 năm trở lên” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0076:WHOLE_FAMILY_TENOR_AXIS_IS_NOT_ONE_INSTRUMENT_SPECIFIC_SCHEMA_LEAF<br>formal: docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-001 | doc 3; source CAF-001 | Vốn và các quỹ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p60; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-002 | doc 3; source CAF-002 | Vốn và các quỹ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p60; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_EQUITY_BALANCE_LEAF; VISIBLE_DASHES_ARE_NOT_NEEDED_FOR_TOTAL_CLOSURE<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-003 | doc 4; source CAF-003 | Vốn và các quỹ | HDB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:dae87ce9d04a135515dc0211591b21f44d3421eaeccd8258122bfeef3fe5877f | physical p33; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_EQUITY_BALANCE_LEAF; EMPTY_SOURCE_COLUMN_NOT_PROMOTED_TO_ZERO<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-004 | doc 4; source CAF-004 | Vốn và các quỹ | HDB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:dae87ce9d04a135515dc0211591b21f44d3421eaeccd8258122bfeef3fe5877f | physical p33; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư xây dựng cơ bản” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-005 | doc 5; source CAF-005 | Vốn và các quỹ | VCB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223 | physical p36; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_RESERVE_SUBTOTAL_AND_EQUITY_TOTAL<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-006 | doc 6; source CAF-006 | Vốn và các quỹ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p43; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_EQUITY_BALANCE_LEAF; EMPTY_SOURCE_ROW_NOT_PROMOTED_TO_ZERO<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-007 | doc 6; source CAF-007 | Vốn và các quỹ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p43; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Chênh lệch đánh giá lại tài sản” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_SCHEMA_BALANCE_COLUMN; EMPTY_SOURCE_ROW_NOT_PROMOTED_TO_ZERO<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-008 | doc 6; source CAF-008 | Vốn và các quỹ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p43; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0078-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0078:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-009 | doc 7; source CAF-009 | Vốn và các quỹ | BID / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:73d9ead38e4e60b2241ae7d41a6e5382f8f2e5cc59f2e7a70ca0bedb95792003 | physical p27–28; printed p24–25 | DIRECT_PIXEL_REVIEW_2026-08-24 — [receipt E-0177](E-0177-canonical-open-direct-pixel-review-receipt-v1.json), entries p27/p28 — render-sha c027fb01e25f35bd453f343920ce5d395a7059079237ca29fd07c8c336612c2e/d43878ddf4e846c5198240fcc5e0360559f99adc13638dd1697d40d1537f9258 | RESOLVABLE_PENDING_GENERIC_FIX | Đã mở trực tiếp BID p27–28: p27/trang in 24 là bảng thay đổi vốn xoay, hàng/cột và số nhìn rõ; p28 đã sang chi tiết vốn/cổ phiếu. Nguồn không mơ hồ; chờ primitive bảng xoay generic. | E-0078:ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0078-CAF-010 | doc 8; source CAF-010 | Vốn và các quỹ | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p44–45; printed p42–43 | DIRECT_PIXEL_REVIEW_2026-08-24 — [receipt E-0177](E-0177-canonical-open-direct-pixel-review-receipt-v1.json), entries p44/p45 — render-sha c15f60c04ac13348c4566feccff0ba8955009a5a2ff23e5d9ad7b1a4240ec9e0/d61bf7597038ee6731fbdcd45f71d7ea382ab2f2712a884a78274008269c836e | RESOLVABLE_PENDING_GENERIC_FIX | Đã mở trực tiếp VIB p44–45: p44/trang in 42 là bảng thay đổi vốn xoay, hàng/cột và số nhìn rõ; p45 đã sang thuyết minh khác. Nguồn không mơ hồ; chờ primitive bảng xoay generic. | E-0078:ROTATED_SOURCE_NUMERIC_CHALLENGER_NOT_RELIABLE; UNIQUE_STRUCTURE_VERIFIED_BUT_NUMERIC_MAPPING_DEFERRED<br>formal: docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0088-OE-001 | doc 3; source OE-001 | Chi phí quản lý chung | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p65; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0088-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Khoản chi “Chi thuê tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0088:No distinct live TM schema leaf represents operating asset-rental expense under Chi về tài sản.<br>formal: docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0088-OE-002 | doc 3; source OE-002 | Chi phí quản lý chung | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p65; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0088-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Khoản chi “Chi phí công nghệ thông tin” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0088:No distinct live TM schema leaf represents operating information-technology expense.<br>formal: docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0088-OE-003 | doc 3; source OE-003 | Chi phí quản lý chung | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p65; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0088-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Khoản chi “Chi về thuế GTGT đầu vào không được khấu trừ” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0088:No distinct live TM schema leaf represents non-deductible input VAT operating expense.<br>formal: docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0088-OE-004 | doc 6; source OE-004 | Chi phí quản lý chung | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p47; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0088-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Khoản chi “Chi khác về TSCĐ” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0088:No distinct live TM schema leaf represents other fixed-asset operating expense under Chi về tài sản.<br>formal: docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0091-TAX-001 | doc 8; source TAX-001 | Chi phí thuế TNDN | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p48; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0091-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Điều chỉnh khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0091:The source label is broader than the prior-period adjustment leaf; its current-period cell is blank and is not interpreted as zero.<br>formal: docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json |
| E0097-BPA-001 | doc 3; source BPA-001 | Tài sản/GTCG thế chấp, cầm cố, chiết khấu | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p67; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0097-bank-pledged-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_CONFLICT | Parent “Giấy tờ có giá đưa đi thế chấp, cầm cố” bằng hai con nhưng tổng in cộng cả parent và con; nguồn mâu thuẫn, không double-count. | E-0097:SOURCE_COMBINED_PARENT_EQUALS_ITS_TRADING_AND_INVESTMENT_PLEDGED_CHILDREN_BUT_IS_ADDED_AGAIN_IN_PRINTED_TOTAL<br>formal: docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json |
| E0097-BPA-002 | doc 8; source BPA-002 | Tài sản/GTCG thế chấp, cầm cố, chiết khấu | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0097-bank-pledged-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | “Giấy tờ có giá đưa đi thế chấp, cầm cố” không tách loại chứng khoán; không ép phân bổ. | E-0097:GENERIC_VALUABLE_PAPERS_NOT_SPLIT_BETWEEN_TRADING_AND_INVESTMENT_SCHEMA_LEAVES<br>formal: docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json |
| E0097-BPA-003 | doc 8; source BPA-003 | Tài sản/GTCG thế chấp, cầm cố, chiết khấu | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0097-bank-pledged-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | “Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu” không tách loại chứng khoán; không ép phân bổ. | E-0097:GENERIC_VALUABLE_PAPERS_NOT_SPLIT_BETWEEN_TRADING_AND_INVESTMENT_SCHEMA_LEAVES<br>formal: docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json |
| E0098-CL-001 | doc 1; source CL-001 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86 | physical p26; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Thư tín dụng trả ngay” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:NO_DEDICATED_SCHEMA_LEAF_FOR_SIGHT_LC<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-002 | doc 1; source CL-002 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86 | physical p26; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Thư tín dụng trả chậm” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:NO_DEDICATED_SCHEMA_LEAF_FOR_DEFERRED_LC<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-003 | doc 1; source CL-003 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86 | physical p26; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | E-0098:LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-004 | doc 1; source CL-004 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86 | physical p26; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-005 | doc 1; source CL-005 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86 | physical p26; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | E-0098:GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-007 | doc 3; source CL-007 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | E-0098:LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-008 | doc 3; source CL-008 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Cam kết bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-009 | doc 3; source CL-009 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | E-0098:GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-010 | doc 3; source CL-010 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Cam kết hoán đổi lãi suất tiền tệ chéo - nhận” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:NO_SCHEMA_LEAF_FOR_CROSS_CURRENCY_INTEREST_SWAP_RECEIVE_LEG<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-011 | doc 3; source CL-011 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Cam kết hoán đổi lãi suất tiền tệ chéo - trả” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:NO_SCHEMA_LEAF_FOR_CROSS_CURRENCY_INTEREST_SWAP_PAY_LEG<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-012 | doc 3; source CL-012 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Cam kết hoán đổi lãi suất một đồng tiền” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:NO_SCHEMA_LEAF_FOR_SINGLE_CURRENCY_INTEREST_SWAP<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-013 | doc 3; source CL-013 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Cam kết khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:GRANULAR_OTHER_COMMITMENT_REPEATS_ITS_GROUP_PARENT_LABEL<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0098-CL-014 | doc 3; source CL-014 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p68; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0098-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Trong đó: hạn mức tín dụng chưa sử dụng có thể / hủy ngang” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0098:IN_THAT_UNUSED_CANCELLABLE_LIMIT_IS_NON_ADDITIVE_AND_HAS_NO_DEDICATED_SCHEMA_LEAF<br>formal: docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0099-FI-001 | doc 3; source FI-001 | Công cụ tài chính — giá trị hợp lý | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p86; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0099-financial-instruments-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE | PDF ghi giá trị hợp lý “(*) Giá trị hợp lý của các tài sản tài chính này không thể xác định được / giá trị hợp lý của các công cụ tài chính” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | E-0099:SOURCE_EXPLICITLY_MARKS_FAIR_VALUE_UNAVAILABLE;_ASTERISK_IS_NOT_ZERO<br>formal: docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json |
| E0099-FI-002 | doc 5; source FI-002 | Công cụ tài chính — giá trị hợp lý | VCB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223 | physical p45; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0099-financial-instruments-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE | PDF ghi giá trị hợp lý “(*) Do không đủ thông tin để sử dụng các kỹ thuật định giá / đáng tin cậy và do đó, không được thuyết minh” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | E-0099:SOURCE_EXPLICITLY_MARKS_FAIR_VALUE_UNAVAILABLE;_ASTERISK_IS_NOT_ZERO<br>formal: docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json |
| E0099-FI-003 | doc 6; source FI-003 | Công cụ tài chính — giá trị hợp lý | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0099-financial-instruments-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE | PDF ghi giá trị hợp lý “(*) Ngân hàng chưa đánh giá giá trị hợp lý / chưa có hướng dẫn cụ thể về việc xác định giá trị hợp lý” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | E-0099:SOURCE_EXPLICITLY_MARKS_FAIR_VALUE_UNAVAILABLE;_ASTERISK_IS_NOT_ZERO<br>formal: docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json |
| E0101-CRISK-002 | doc 3; source CRISK-002 | Rủi ro tiền tệ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p80; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0101:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0101-CRISK-007 | doc 4; source CRISK-007 | Rủi ro tiền tệ | HDB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:dae87ce9d04a135515dc0211591b21f44d3421eaeccd8258122bfeef3fe5877f | physical p39; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0101:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0101-CRISK-009 | doc 6; source CRISK-009 | Rủi ro tiền tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p60; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0101:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0103-LRISK-002 | doc 3; source LRISK-002 | Rủi ro thanh khoản | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p82; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SOURCE_CONFLICT | Ba ô tại “1–3 tháng” đã pixel-review nhưng phép trừ lệch 6.000 triệu đồng so với số in; giữ source, không backsolve. | E-0103:SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL<br>formal: docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json |
| E0103-LRISK-003 | doc 3; source LRISK-003 | Rủi ro thanh khoản | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p82; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SOURCE_CONFLICT | Ba ô tại “1–5 năm” đã pixel-review nhưng phép trừ lệch 275.500 triệu đồng so với số in; giữ source, không backsolve. | E-0103:SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL<br>formal: docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json |
| E0103-LRISK-004 | doc 3; source LRISK-004 | Rủi ro thanh khoản | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p82; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SOURCE_CONFLICT | Ba ô tại “3–12 tháng” đã pixel-review nhưng phép trừ lệch 6.001 triệu đồng so với số in; giữ source, không backsolve. | E-0103:SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL<br>formal: docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json |
| E0103-LRISK-005 | doc 3; source LRISK-005 | Rủi ro thanh khoản | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p82; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SOURCE_CONFLICT | Ba ô tại “Tổng tài sản / Tổng nợ phải trả / Mức chếnh thanh khoản ròng” đã pixel-review nhưng phép trừ lệch 275.499 triệu đồng so với số in; giữ source, không backsolve. | E-0103:SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL<br>formal: docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-001 | doc 3; source FXRATE-001 | Tỷ giá ngoại tệ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p90; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-002 | doc 3; source FXRATE-002 | Tỷ giá ngoại tệ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p90; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-003 | doc 3; source FXRATE-003 | Tỷ giá ngoại tệ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p90; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-004 | doc 3; source FXRATE-004 | Tỷ giá ngoại tệ | VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf<br>sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde | physical p90; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-005 | doc 6; source FXRATE-005 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-006 | doc 6; source FXRATE-006 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-007 | doc 6; source FXRATE-007 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-008 | doc 6; source FXRATE-008 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-009 | doc 6; source FXRATE-009 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-010 | doc 6; source FXRATE-010 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “KRW” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-011 | doc 6; source FXRATE-011 | Tỷ giá ngoại tệ | CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318 | physical p61; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “LAK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-012 | doc 8; source FXRATE-012 | Tỷ giá ngoại tệ | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p71; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-013 | doc 8; source FXRATE-013 | Tỷ giá ngoại tệ | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p71; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-014 | doc 8; source FXRATE-014 | Tỷ giá ngoại tệ | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p71; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0104-FXRATE-015 | doc 8; source FXRATE-015 | Tỷ giá ngoại tệ | VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf<br>sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c | physical p71; printed: không ghi trong artifact | PERSISTED_PIXEL_CROP_REVIEW — docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json (crop_ref + pixel_transcription) | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0104:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-001 | doc 1; source A2025-OA-001 | Tài sản Có khác | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p58; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản tạm ứng và phải thu nội bộ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:One printed row combines advances and internal receivables; it cannot be split between ReportNormIds 975 and 970.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-002 | doc 1; source A2025-OA-002 | Tài sản Có khác | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p58; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu Ngân sách Nhà nước” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The source does not state that this is tax overpayment/deductible tax, so ReportNormId 974 is not inferred.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-003 | doc 1; source A2025-OA-003 | Tài sản Có khác | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p59; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Tài sản thuế thu nhập doanh nghiệp hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets schema family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-004 | doc 1; source A2025-OA-004 | Tài sản Có khác | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p59; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | RESOLVABLE_PENDING_GENERIC_FIX | Pixel artifact xác nhận ô “Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | E-0127:The comparative cell is a visible dash; the current verifier does not promote an unbound blank geometry cell to numeric evidence.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-005 | doc 1; source A2025-OA-005 | Tài sản Có khác | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p60; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-006 | doc 2; source A2025-OA-006 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu liên quan đến tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets family; the current cell is a visible dash.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-007 | doc 2; source A2025-OA-007 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | RESOLVABLE_PENDING_GENERIC_FIX | Pixel artifact xác nhận ô “Các khoản phải thu miễn truy đòi theo bộ chứng từ” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | E-0127:The comparative cell is a visible dash and is not promoted without bound dash geometry.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-008 | doc 2; source A2025-OA-008 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản tạm ứng và đặt cọc hợp đồng” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:One source row combines ReportNormIds 975 and 973; no allocation is printed.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-009 | doc 2; source A2025-OA-009 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng phí và dự phòng bồi thường nghiệp vụ nhượng tái bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-010 | doc 2; source A2025-OA-010 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Lãi phải thu hoạt động tín dụng và phí phải thu” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The printed row combines credit interest and fees, so it is not narrowed to ReportNormId 983.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-011 | doc 2; source A2025-OA-011 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p63; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | RESOLVABLE_PENDING_GENERIC_FIX | Pixel artifact xác nhận ô “Lợi thế thương mại” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | E-0127:The current cell is a visible dash and the row is not promoted without bound dash geometry.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-012 | doc 2; source A2025-OA-012 | Tài sản Có khác | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p63; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-013 | doc 3; source A2025-OA-013 | Tài sản Có khác | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p55; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu bán tài sản tài chính” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The source meaning is broader than ReportNormId 976, which is specifically sale of securities.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-014 | doc 3; source A2025-OA-014 | Tài sản Có khác | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p55; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-015 | doc 3; source A2025-OA-015 | Tài sản Có khác | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p55; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | RESOLVABLE_PENDING_GENERIC_FIX | Pixel artifact xác nhận ô “Nợ đủ tiêu chuẩn” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | E-0127:The comparative cell is a visible dash and is not promoted without bound dash geometry.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-016 | doc 3; source A2025-OA-016 | Tài sản Có khác | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p56; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | RESOLVABLE_PENDING_GENERIC_FIX | Pixel artifact xác nhận ô “Tài sản có khác” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | E-0127:The comparative cell is a visible dash and is not promoted without bound dash geometry.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-017 | doc 3; source A2025-OA-017 | Tài sản Có khác | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p56; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | RESOLVABLE_PENDING_GENERIC_FIX | Pixel artifact xác nhận ô “Lợi thế thương mại” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | E-0127:The current cell is a visible dash and is not promoted without bound dash geometry.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-018 | doc 3; source A2025-OA-018 | Tài sản Có khác | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p57; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-019 | doc 4; source A2025-OA-019 | Tài sản Có khác | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p42; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản tạm ứng và phải thu nội bộ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:One printed row combines advances and internal receivables; it cannot be split between ReportNormIds 975 and 970.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-020 | doc 4; source A2025-OA-020 | Tài sản Có khác | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p43; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu từ thanh lý TSCĐ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The current cell is a visible dash; no exact schema child exists and the row is not forced into other receivables.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-021 | doc 4; source A2025-OA-021 | Tài sản Có khác | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng rủi ro các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-022 | doc 5; source A2025-OA-022 | Tài sản Có khác | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p50; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu từ ngân sách Nhà nước về hỗ trợ lãi suất” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The source is a government-budget receivable, not a receivable from the State Bank under ReportNormId 979.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-023 | doc 5; source A2025-OA-023 | Tài sản Có khác | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Tài sản thuế thu nhập hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets schema family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-024 | doc 5; source A2025-OA-024 | Tài sản Có khác | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-025 | doc 6; source A2025-OA-025 | Tài sản Có khác | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p50; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản tạm ứng và phải thu nội bộ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:One printed row combines advances and internal receivables; it cannot be split between ReportNormIds 975 and 970.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-026 | doc 6; source A2025-OA-026 | Tài sản Có khác | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p50; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-027 | doc 7; source A2025-OA-027 | Tài sản Có khác | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản phải thu khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:This source group contains internal and external receivables and is not the narrow ReportNormId 981 leaf.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-028 | doc 7; source A2025-OA-028 | Tài sản Có khác | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Tài sản thuế thu nhập doanh nghiệp hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets schema family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-029 | doc 7; source A2025-OA-029 | Tài sản Có khác | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The 966–1023 schema family has no exact provision-balance and movement branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-030 | doc 7; source A2025-OA-030 | Tài sản Có khác | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu trong nghiệp vụ tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-031 | doc 8; source A2025-OA-031 | Tài sản Có khác | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu từ Ngân sách Nhà nước” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The source does not state that this is tax overpayment/deductible tax or a State Bank receivable.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-032 | doc 8; source A2025-OA-032 | Tài sản Có khác | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu từ hoạt động tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-033 | doc 8; source A2025-OA-033 | Tài sản Có khác | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Phải thu hoa hồng bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The source does not identify the counterparty as an insurance subsidiary required by ReportNormId 978.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-034 | doc 8; source A2025-OA-034 | Tài sản Có khác | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Tài sản thuế TNDN hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:No exact child exists in the current TM other-assets schema family.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0127-A2025-OA-035 | doc 8; source A2025-OA-035 | Tài sản Có khác | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | E-0127:The current cell is a visible dash and the 966–1023 family has no exact provision branch.<br>formal: docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json |
| E0129-A2025-CD-001 | doc 7; source A2025-CD-001 | Tiền gửi khách hàng | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Dòng “Công ty cổ phần” gộp nhiều loại khách hàng pháp lý; không có dữ liệu phân bổ theo leaf. | E-0129:The broad printed JSC row does not distinguish State-over-50% from other JSC leaves 1081/1082.<br>formal: docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json |
| E0129-A2025-CD-002 | doc 7; source A2025-CD-002 | Tiền gửi khách hàng | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Dòng “Doanh nghiệp tư nhân, cá nhân” gộp nhiều loại khách hàng pháp lý; không có dữ liệu phân bổ theo leaf. | E-0129:One printed value combines private enterprises and individuals, so it cannot be allocated between 1083 and 1089.<br>formal: docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json |
| E0131-A2025-IVP-001 | doc 3; source A2025-IVP-001 | Phát hành giấy tờ có giá | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Trục/hàng “Dưới 12 tháng” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0131:WHOLE_FAMILY_TENOR_AXIS_IS_NOT_INSTRUMENT_SPECIFIC<br>formal: docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0131-A2025-IVP-002 | doc 3; source A2025-IVP-002 | Phát hành giấy tờ có giá | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Trục/hàng “Từ 12 tháng đến dưới 5 năm” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0131:WHOLE_FAMILY_TENOR_AXIS_IS_NOT_INSTRUMENT_SPECIFIC<br>formal: docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0131-A2025-IVP-003 | doc 3; source A2025-IVP-003 | Phát hành giấy tờ có giá | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p62; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Trục/hàng “Từ 5 năm trở lên” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0131:WHOLE_FAMILY_TENOR_AXIS_IS_NOT_INSTRUMENT_SPECIFIC<br>formal: docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0131-A2025-IVP-004 | doc 4; source A2025-IVP-004 | Phát hành giấy tờ có giá | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p46; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Trục/hàng “Chi phí phát hành” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0131:ISSUANCE_COST_CONTRA_ROW_HAS_NO_DEDICATED_SCHEMA_LEAF<br>formal: docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0131-A2025-IVP-005 | doc 5; source A2025-IVP-005 | Phát hành giấy tờ có giá | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p54; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Trục/hàng “Trung, dài hạn bằng ngoại tệ” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | E-0131:ONE_SOURCE_ROW_COMBINES_MEDIUM_AND_LONG_TENORS_WITHOUT_ALLOCATION<br>formal: docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-001 | doc 3; source A2025-CAF-001 | Vốn và các quỹ | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p66; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-002 | doc 4; source A2025-CAF-002 | Vốn và các quỹ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p48; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_EQUITY_BALANCE_LEAF; CLOSING_BLANK_NOT_PROMOTED_TO_ZERO<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-003 | doc 4; source A2025-CAF-003 | Vốn và các quỹ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p48; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Vốn đầu tư xây dựng cơ bản” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-004 | doc 5; source A2025-CAF-004 | Vốn và các quỹ | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p56; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_RESERVE_SUBTOTAL_AND_EQUITY_TOTAL<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-005 | doc 6; source A2025-CAF-005 | Vốn và các quỹ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p55; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-006 | doc 7; source A2025-CAF-006 | Vốn và các quỹ | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p53; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0133-A2025-CAF-007 | doc 8; source A2025-CAF-007 | Vốn và các quỹ | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p49; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | E-0133:NO_EXACT_SCHEMA_BALANCE_COLUMN; VALUES_REMAIN_IN_VERIFIED_EQUITY_TOTAL<br>formal: docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json |
| E0137-SA-CTG-001 | doc 6; source SA-CTG-001 | Thu nhập/chi phí dịch vụ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p58; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Dòng “Thu từ dịch vụ tư vấn, ủy thác và đại lý” gộp tư vấn với ủy thác/đại lý; không có căn cứ tách dù tổng khép. | E-0137:NO_EXACT_SCHEMA_LEAF_FOR_COMBINED_CONSULTING_TRUST_AND_AGENCY_ROW<br>formal: docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json |
| E0137-SA-CTG-002 | doc 6; source SA-CTG-002 | Thu nhập/chi phí dịch vụ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p58; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Dòng “Chi về dịch vụ tư vấn, ủy thác và đại lý” gộp tư vấn với ủy thác/đại lý; không có căn cứ tách dù tổng khép. | E-0137:NO_EXACT_SCHEMA_LEAF_FOR_COMBINED_CONSULTING_TRUST_AND_AGENCY_ROW<br>formal: docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json |
| E0142-CCDI-CTG-001 | doc 6; source CCDI-CTG-001 | Thu nhập góp vốn/cổ tức | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p59; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_SCOPE | Dòng “Từ chứng khoán vốn” gộp nhiều loại chứng khoán vốn; không có căn cứ phân bổ. | E-0142:The source prints one combined 'Từ chứng khoán vốn' amount; the live schema has separate trading- and investment-equity leaves, so the printed amount is retained source-only and is not split or narrowed.<br>formal: docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-001 | doc 1; source OE-A2025-001 | Chi phí quản lý chung | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p70; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi khác” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:The source-specific residual asset-cost row has no distinct live TM schema leaf and is retained without narrowing it to another expense concept.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-002 | doc 1; source OE-A2025-002 | Chi phí quản lý chung | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p70; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Hoàn nhập chi phí dự phòng” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:The printed aggregate provision line is retained source-only because its two separately disclosed components are mapped independently and the aggregate must not be double counted.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-003 | doc 2; source OE-A2025-003 | Chi phí quản lý chung | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p74; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi khác về tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:The source-specific residual asset-cost row has no distinct live TM schema leaf and is retained without silently merging it into depreciation.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-004 | doc 3; source OE-A2025-004 | Chi phí quản lý chung | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p72; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi thuê tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Operating asset-rental expense is a distinct visible source child but the live TM family has no corresponding leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-005 | doc 3; source OE-A2025-005 | Chi phí quản lý chung | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p72; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi phí công nghệ thông tin” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Operating information-technology expense is distinct in the source but has no corresponding live TM leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-006 | doc 3; source OE-A2025-006 | Chi phí quản lý chung | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p72; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi về thuế GTGT đầu vào không được khấu trừ” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Non-deductible input VAT is a distinct wrapped source row but has no corresponding live TM leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-007 | doc 4; source OE-A2025-007 | Chi phí quản lý chung | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi thuê tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Operating asset-rental expense is retained source-only because the live TM family has no distinct leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-008 | doc 4; source OE-A2025-008 | Chi phí quản lý chung | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi về bảo dưỡng và sửa chữa tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Asset maintenance and repair expense is retained source-only because the live TM family has no distinct leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-009 | doc 4; source OE-A2025-009 | Chi phí quản lý chung | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi khác về tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:The source-specific residual asset-cost row has no distinct live TM schema leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-010 | doc 4; source OE-A2025-010 | Chi phí quản lý chung | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi phí quảng cáo, tiếp thị, khuyến mại” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Advertising, marketing and promotion expense has no distinct live TM leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-011 | doc 4; source OE-A2025-011 | Chi phí quản lý chung | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi phí hội nghị, lễ tân, khánh tiết” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Conference, reception and hospitality expense has no distinct live TM leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-012 | doc 4; source OE-A2025-012 | Chi phí quản lý chung | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p51; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi phí điện, nước, vệ sinh cơ quan” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:Utilities and office-cleaning expense has no distinct live TM leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-013 | doc 6; source OE-A2025-013 | Chi phí quản lý chung | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p60; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi khác” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:The source-specific residual asset-cost row has no distinct live TM schema leaf.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0143-OE-A2025-014 | doc 6; source OE-A2025-014 | Chi phí quản lý chung | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p60; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Khoản chi “Chi phí dự phòng” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | E-0143:The source prints only a generic provision-expense row, so it is retained without narrowing it to either long-term-investment or other-asset provision schema leaves.<br>formal: docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-ACB-001 | doc 1; source A2025-ITAX-ACB-001 | Chi phí thuế TNDN | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p71; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Các khoản điều chỉnh làm tăng/(giảm) thu nhập chịu thuế khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:The broad increase/decrease row has no independently named leaf outside the already source-bound non-taxable-income row.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-ACB-002 | doc 1; source A2025-ITAX-ACB-002 | Chi phí thuế TNDN | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p71; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Chi phí thuế thu nhập doanh nghiệp hoãn lại phát sinh từ hoàn / nhập tài sản thuế thu nhập hoãn lại (Thuyết minh 14.2)” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:The live schema contains the deferred-tax net but no source-specific reversal component leaf.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-ACB-003 | doc 1; source A2025-ITAX-ACB-003 | Chi phí thuế TNDN | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p71; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Thu nhập thuế thu nhập doanh nghiệp hoãn lại phát sinh từ các / khoản chênh lệch tạm thời được khấu trừ (Thuyết minh 14.2)” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:The live schema contains the deferred-tax net but no source-specific deductible-difference component leaf.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-MBB-001 | doc 2; source A2025-ITAX-MBB-001 | Chi phí thuế TNDN | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p76; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Thuế TNDN do thoái vốn tại công ty con” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:The source-specific divestment tax has no exact current-tax component leaf; the comparative source cell is visibly blank and is not zero-filled.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-VPB-001 | doc 3; source A2025-ITAX-VPB-001 | Chi phí thuế TNDN | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p64; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Các điều chỉnh khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:This row belongs to the subsequent tax-payable rollforward, has no exact expense leaf, and its comparative cell is visibly blank.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-CTG-001 | doc 6; source A2025-ITAX-CTG-001 | Chi phí thuế TNDN | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p60; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Điều chính khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:This row belongs to the subsequent tax-payable rollforward and has no exact tax-expense leaf.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0146-A2025-ITAX-VIB-001 | doc 8; source A2025-ITAX-VIB-001 | Chi phí thuế TNDN | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p53; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Điều chỉnh khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | E-0146:The broad source label does not establish the prior-period nature required by ReportNormId 5733; it remains visible and participates in the verified total equation.<br>formal: docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json |
| E0153-CL-001 | doc 1; source CL-001 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết trong nghiệp vụ L/C trả ngay” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:NO_DEDICATED_SCHEMA_LEAF_FOR_SIGHT_LC<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-002 | doc 1; source CL-002 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết trong nghiệp vụ L/C trả chậm” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:NO_DEDICATED_SCHEMA_LEAF_FOR_DEFERRED_LC<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-003 | doc 1; source CL-003 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | E-0153:LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-004 | doc 1; source CL-004 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-005 | doc 1; source CL-005 | Nghĩa vụ nợ tiềm ẩn và cam kết | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | E-0153:GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-007 | doc 3; source CL-007 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | E-0153:LC_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-008 | doc 3; source CL-008 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:GRANULAR_OTHER_GUARANTEE_REPEATS_ITS_GROUP_PARENT_LABEL<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-009 | doc 3; source CL-009 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | E-0153:GUARANTEE_MARGIN_DEDUCTION_IS_A_CONTROL_NOT_A_SCHEMA_VALUE<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-010 | doc 3; source CL-010 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết hoán đổi lãi suất tiền tệ chéo - nhận” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:NO_DEDICATED_SCHEMA_LEAF_FOR_CROSS_CURRENCY_SWAP_RECEIVE<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-011 | doc 3; source CL-011 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết hoán đổi lãi suất tiền tệ chéo - trả” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:NO_DEDICATED_SCHEMA_LEAF_FOR_CROSS_CURRENCY_SWAP_PAY<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-012 | doc 3; source CL-012 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết hoán đổi lãi suất một đồng tiền” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:NO_DEDICATED_SCHEMA_LEAF_FOR_SINGLE_CURRENCY_INTEREST_SWAP<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-013 | doc 3; source CL-013 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Cam kết khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:SOURCE_CHILD_REPEATS_OTHER_COMMITMENT_PARENT_LABEL<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0153-CL-014 | doc 3; source CL-014 | Nghĩa vụ nợ tiềm ẩn và cam kết | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p75; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | E-0153:NON_ADDITIVE_WITHIN_SUBSET_HAS_NO_SCHEMA_LEAF<br>formal: docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json |
| E0154-FI-001 | doc 3; source FI-001 | Công cụ tài chính — giá trị hợp lý | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p94; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE | PDF ghi giá trị hợp lý “(*) Ngân hàng chưa xác định giá trị của khoản mục này / chưa có hướng dẫn về xác định giá trị hợp lý” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | E-0154:SOURCE_EXPLICITLY_MARKS_FAIR_VALUE_UNAVAILABLE;_ASTERISK_IS_NOT_ZERO<br>formal: docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json |
| E0154-FI-002 | doc 5; source FI-002 | Công cụ tài chính — giá trị hợp lý | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p74; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE | PDF ghi giá trị hợp lý “(*) Do không đủ thông tin để sử dụng các kỹ thuật định giá / giá trị hợp lý không được ước tính một cách đáng tin cậy / không được thuyết minh” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | E-0154:SOURCE_EXPLICITLY_MARKS_FAIR_VALUE_UNAVAILABLE;_ASTERISK_IS_NOT_ZERO<br>formal: docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-001 | doc 1; source A2025-CRISK-001 | Rủi ro tiền tệ | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p84; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục AUD có năm ô nguồn đã pixel-review (Tổng tài sản, Tổng nợ phải trả, trạng thái nội bảng, ngoại bảng và tổng nội/ngoại bảng), nhưng schema lõi chưa có trục AUD tương đương; giữ source-only, không gộp vào ngoại tệ khác. | E-0155:NO_EQUIVALENT_CORE_SCHEMA_ROW<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-002 | doc 1; source A2025-CRISK-002 | Rủi ro tiền tệ | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p84; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục CAD có năm ô nguồn đã pixel-review (Tổng tài sản, Tổng nợ phải trả, trạng thái nội bảng, ngoại bảng và tổng nội/ngoại bảng), nhưng schema lõi chưa có trục CAD tương đương; giữ source-only, không gộp vào ngoại tệ khác. | E-0155:NO_EQUIVALENT_CORE_SCHEMA_ROW<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-003 | doc 1; source A2025-CRISK-003 | Rủi ro tiền tệ | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p84; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0155:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-004 | doc 1; source A2025-CRISK-004 | Rủi ro tiền tệ | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p84; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục JPY có năm ô nguồn đã pixel-review (Tổng tài sản, Tổng nợ phải trả, trạng thái nội bảng, ngoại bảng và tổng nội/ngoại bảng), nhưng schema lõi chưa có trục JPY tương đương; giữ source-only, không gộp vào ngoại tệ khác. | E-0155:NO_EQUIVALENT_CORE_SCHEMA_ROW<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-005 | doc 3; source A2025-CRISK-005 | Rủi ro tiền tệ | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p88; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0155:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-006 | doc 4; source A2025-CRISK-006 | Rủi ro tiền tệ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p63; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0155:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0155-A2025-CRISK-007 | doc 6; source A2025-CRISK-007 | Rủi ro tiền tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p71; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | E-0155:NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH<br>formal: docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json |
| E0156-AIRRISK-001 | doc 3; source AIRRISK-001 | Rủi ro lãi suất | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SOURCE_CONFLICT | Tổng kết hợp tại “Tổng tài sản / Tổng nợ phải trà / Mức chênh nhạy cảm với lãi suất nội, ngoại bảng / Mức chênh nhạy cảm với lãi suất ngoại bảng / Mức chếnh nhạy cảm với lãi suất nội bảng” lệch 2 triệu so với nội bảng cộng ngoại bảng; giữ số nguồn. | E-0156:SOURCE_PRESENTATION_OR_NUMERIC_CHALLENGER_RESIDUAL<br>formal: docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-001 | doc 3; source AFXRATE-001 | Tỷ giá ngoại tệ | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p98; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-002 | doc 3; source AFXRATE-002 | Tỷ giá ngoại tệ | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p98; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-003 | doc 3; source AFXRATE-003 | Tỷ giá ngoại tệ | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p98; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-004 | doc 3; source AFXRATE-004 | Tỷ giá ngoại tệ | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p98; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-005 | doc 4; source AFXRATE-005 | Tỷ giá ngoại tệ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p69; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-006 | doc 4; source AFXRATE-006 | Tỷ giá ngoại tệ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p69; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-007 | doc 4; source AFXRATE-007 | Tỷ giá ngoại tệ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p69; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “KRW” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-008 | doc 4; source AFXRATE-008 | Tỷ giá ngoại tệ | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p69; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-009 | doc 6; source AFXRATE-009 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-010 | doc 6; source AFXRATE-010 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-011 | doc 6; source AFXRATE-011 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-012 | doc 6; source AFXRATE-012 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-013 | doc 6; source AFXRATE-013 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-014 | doc 6; source AFXRATE-014 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “KRW” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-015 | doc 6; source AFXRATE-015 | Tỷ giá ngoại tệ | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p85; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “LAK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-016 | doc 8; source AFXRATE-016 | Tỷ giá ngoại tệ | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p77; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-017 | doc 8; source AFXRATE-017 | Tỷ giá ngoại tệ | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p77; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-018 | doc 8; source AFXRATE-018 | Tỷ giá ngoại tệ | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p77; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0158-AFXRATE-019 | doc 8; source AFXRATE-019 | Tỷ giá ngoại tệ | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p77; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | E-0158:NO_LIVE_TM_SCHEMA_LEAF_FOR_VISIBLE_CURRENCY_OR_GOLD<br>formal: docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json |
| E0159-AIFUND-001 | doc 3; source AIFUND-001 | Tiền gửi/vay TCTD khác — nguồn vốn | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p59; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0159-annual-2025-interbank-funding-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Vốn vay từ IFC” là detail/parent trung gian chưa có leaf và không cộng thêm vào subtotal vay; tránh double-count. | E-0159:NO_EXACT_LIVE_TM_SCHEMA_LEAF_OR_NONADDITIVE_DETAIL<br>formal: docs/experiments/E-0159-annual-2025-interbank-funding-8bank-codex-verified-mapping-v1.json |
| E0159-AIFUND-002 | doc 4; source AIFUND-002 | Tiền gửi/vay TCTD khác — nguồn vốn | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p44; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0159-annual-2025-interbank-funding-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SCHEMA_GAP | “Phải trả nghiệp vụ UPAS L/C” là detail/parent trung gian chưa có leaf và không cộng thêm vào subtotal vay; tránh double-count. | E-0159:NO_EXACT_LIVE_TM_SCHEMA_LEAF_OR_NONADDITIVE_DETAIL<br>formal: docs/experiments/E-0159-annual-2025-interbank-funding-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-001 | doc 1; source ASEG-001 | Báo cáo bộ phận hợp nhất | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p95; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | “Cho thuê tài chính” là một trục kinh doanh nhìn thấy trong bảng ACB, nhưng schema 5807–5842 không có trục tương đương; giữ source-only, không ép vào trục khác. | E-0161:SOURCE_BUSINESS_AXIS_NOT_PRESENT_IN_5807_5842<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-002 | doc 1; source ASEG-002 | Báo cáo bộ phận hợp nhất | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p95; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | ACB trình bày riêng “Chứng khoán” và “Quản lý quỹ”, trong khi schema chỉ có trục kết hợp; chưa có rule cộng có kiểm soát hai trục nguồn nên chưa map. | E-0161:TWO_SOURCE_AXES_REQUIRE_CONTROLLED_AGGREGATION_TO_COMBINED_SCHEMA_AXIS<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-003 | doc 1; source ASEG-003 | Báo cáo bộ phận hợp nhất | ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b | physical p95; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Nhãn “Kết quả kinh doanh bộ phận” không xác lập rõ đây là “Lợi nhuận trước thuế”; không thu hẹp nghĩa để map. | E-0161:SOURCE_LABEL_DOES_NOT_EXPLICITLY_ESTABLISH_PROFIT_BEFORE_TAX<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-004 | doc 2; source ASEG-004 | Báo cáo bộ phận hợp nhất | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p87; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Trục địa lý “Nước ngoài” của MBB không đồng nhất với schema “Khu vực khác”; giữ source-only, không relabel. | E-0161:SOURCE_GEOGRAPHIC_AXIS_IS_NOT_IDENTICAL_TO_KHU_VUC_KHAC<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-005 | doc 2; source ASEG-005 | Báo cáo bộ phận hợp nhất | MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:9853cc4909dc73ddea9907465b09d7ecdb96cf6c1627f56943f3a20d14b49f80 | physical p83; printed p79 | DIRECT_PIXEL_REVIEW_2026-08-24 — [receipt E-0177](E-0177-canonical-open-direct-pixel-review-receipt-v1.json), entry p83 — render-sha 9b699dca3c6c84a4263f0b93acf291d77097f0c0c5df9b414649c7e828baaa48 | RESOLVABLE_PENDING_GENERIC_FIX | Đã mở trực tiếp MBB p83/trang in 79: bảng bộ phận, cột loại trừ và dòng Thu nhập/Chi phí nội bộ đọc rõ; chờ binding generic cho hàng đối trừ. | E-0161:INTERNAL_ELIMINATION_REVENUE_EXPENSE_RECONCILIATION_NOT_INCLUDED_IN_BOUNDED_REVIEW<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-006 | doc 3; source ASEG-006 | Báo cáo bộ phận hợp nhất | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p96; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | “Hoạt động công ty tài chính” của VPB không có trục tương đương trong schema 5807–5842; giữ source-only. | E-0161:SOURCE_BUSINESS_AXIS_NOT_PRESENT_IN_5807_5842<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-007 | doc 3; source ASEG-007 | Báo cáo bộ phận hợp nhất | VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0 | physical p96; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | “Hoạt động chứng khoán” hẹp hơn trục schema kết hợp “Chứng khoán/Quản lý quỹ”; không mở rộng population để map. | E-0161:SOURCE_AXIS_NARROWER_THAN_CHUNG_KHOAN_QUAN_LY_QUY<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-008 | doc 4; source ASEG-008 | Báo cáo bộ phận hợp nhất | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p61; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Trục “Nước ngoài” của HDB không đồng nhất với “Khu vực khác”; giữ source-only. | E-0161:SOURCE_GEOGRAPHIC_AXIS_IS_NOT_IDENTICAL_TO_KHU_VUC_KHAC<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-009 | doc 4; source ASEG-009 | Báo cáo bộ phận hợp nhất | HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3 | physical p61; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Nhãn “Kết quả kinh doanh bộ phận” không xác lập rõ đây là “Lợi nhuận trước thuế”; không thu hẹp nghĩa để map. | E-0161:SOURCE_LABEL_DOES_NOT_EXPLICITLY_ESTABLISH_PROFIT_BEFORE_TAX<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-010 | doc 5; source ASEG-010 | Báo cáo bộ phận hợp nhất | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p71; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | “Miền Trung và Tây Nguyên” rộng hơn schema “Miền Trung”; không thu hẹp population để map. | E-0161:SOURCE_AXIS_BROADER_THAN_MIEN_TRUNG<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-011 | doc 5; source ASEG-011 | Báo cáo bộ phận hợp nhất | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p71; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | VCB có trục “Nước ngoài” nhưng schema địa lý hiện hành không có trục tương đương; giữ source-only. | E-0161:SOURCE_GEOGRAPHIC_AXIS_NOT_PRESENT_IN_SCHEMA<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-012 | doc 5; source ASEG-012 | Báo cáo bộ phận hợp nhất | VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:295f397de287f84c26dafbfa06f668604aa696a013e236253149d8547d032d1f | physical p72; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Các trục “Dịch vụ tài chính phi ngân hàng / Chứng khoán / Khác” của VCB không đồng nhất với các trục kinh doanh schema; không ép gần nghĩa. | E-0161:SOURCE_BUSINESS_AXES_NOT_IDENTICAL_TO_LIVE_SCHEMA_AXES<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-013 | doc 6; source ASEG-013 | Báo cáo bộ phận hợp nhất | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p82; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Các trục “Dịch vụ tài chính phi ngân hàng / Khác” của CTG không đồng nhất với các trục kinh doanh schema; không ép gần nghĩa. | E-0161:SOURCE_BUSINESS_AXES_NOT_IDENTICAL_TO_LIVE_SCHEMA_AXES<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-014 | doc 6; source ASEG-014 | Báo cáo bộ phận hợp nhất | CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137 | physical p82; printed p80 | DIRECT_PIXEL_REVIEW_2026-08-24 — [receipt E-0177](E-0177-canonical-open-direct-pixel-review-receipt-v1.json), entry p82 — observed-render-sha f3fb0c18b88ff2137ed0f03351bbf019adbb29c6c66eca96c16ca1880cec9e79 (system PyMuPDF/MuPDF 1.26.3; 1.438.284 bytes); canonical-replay-sha 01c83ad86684b837c60c1a94dbcd47eea0fe7d870a1352688518e8a541b3438d (.venv PyMuPDF 1.28.0/MuPDF 1.29.0; 1.438.261 bytes) | RESOLVABLE_PENDING_GENERIC_FIX | Đã mở trực tiếp CTG p82/trang in 80: toàn bộ bảng bộ phận xoay, hàng kết quả và số đọc rõ; chờ promote/bind đủ hàng bằng primitive generic. | E-0161:SUPPORTED_AXIS_NUMBERS_NOT_PROMOTED_WITHOUT_FULL_PIXEL_ROW_RECONCILIATION<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-015 | doc 7; source ASEG-015 | Báo cáo bộ phận hợp nhất | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p37; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Các trục “Cho thuê tài chính / Chứng khoán / Khác” của BID không đồng nhất với các trục kinh doanh schema; không ép gần nghĩa. | E-0161:SOURCE_BUSINESS_AXES_NOT_IDENTICAL_TO_LIVE_SCHEMA_AXES<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-016 | doc 7; source ASEG-016 | Báo cáo bộ phận hợp nhất | BID / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:415d713b18f281f97ea5416da01ddec32d20d9ad49342f3e31fc001743b8a222 | physical p38; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | BID chỉ trình bày “Trong nước / Nước ngoài”, không tương đương trục schema “Miền Bắc / Miền Trung / Miền Nam”; không phân bổ suy diễn. | E-0161:SOURCE_GEOGRAPHIC_AXES_NOT_EQUIVALENT_TO_NORTH_CENTRAL_SOUTH_SCHEMA<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |
| E0161-ASEG-017 | doc 8; source ASEG-017 | Báo cáo bộ phận hợp nhất | VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf<br>sha256:d6b96ddaaadb19a4ea1c083ceaa1a15500b742383321c2bcb7c22706509837b7 | physical p61; printed: không ghi trong artifact | PERSISTED_CODEX_PIXEL_REVIEW — docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-pixel-review-v1.json | KEEP_UNRESOLVED_SEMANTIC_GAP | Ô “Tài sản cố định — Miền Trung” của VIB nhìn thấy là blank thật, không phải dấu gạch và không phải 0; giữ unresolved value, không tự điền 0. | E-0161:VISIBLE_CELL_IS_BLANK_NOT_DASH_AND_NOT_ZERO<br>formal: docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json |<!-- CANONICAL_OPEN_SOURCE_ROWS_END -->

## Danh mục OPEN cần xử lý

Bảng này nằm trước toàn bộ phần `CLOSED` và dẫn tới mọi heading `OPEN` hiện có
trong ledger. Tổng hiện hành là **205 source-row OPEN ngoài Family 3**; bảng
canonical phía trên là authority đếm. Family 3 có 0 OPEN sau E-0178; 42 hàng
review cũ được giữ ở closed history và không còn nằm trong index này.

<!-- OPEN_FAMILY_INDEX_BEGIN -->

| Family | Số OPEN | Tình trạng/nguyên nhân dễ hiểu | Link chi tiết |
| --- | ---: | --- | --- |
| Tài sản/GTCG đem thế chấp, cầm cố, chiết khấu | 3 | Một hierarchy nguồn mâu thuẫn và hai dòng không tách loại chứng khoán. | [Canonical rows](#canonical-open-source-rows) |
| Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra | 26 | 13 annual + 13 historical/current; thiếu leaf L/C, ký quỹ, swap và dòng `Trong đó`. | [Chi tiết annual](#open-contingent-liabilities-annual-2025) |
| Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý | 5 | 2 annual + 3 historical/current; PDF ghi `(*)`/không công bố giá trị số. | [Chi tiết annual](#open-financial-instruments-fair-value-annual-2025) |
| Rủi ro tiền tệ | 10 | 7 annual + 3 historical/current; schema thiếu trục AUD/CAD/JPY/vàng. | [Chi tiết annual](#open-currency-risk-annual-2025) |
| Rủi ro lãi suất | 1 | Tổng kết hợp VPB lệch 2 so với nội bảng cộng ngoại bảng; giữ nguyên 5 ô nguồn. | [Chi tiết](#open-interest-rate-risk-annual-2025) |
| Rủi ro thanh khoản | 4 | Bốn trục VPB có residual nguồn vật chất; không backsolve. | [Canonical rows](#canonical-open-source-rows) |
| Tỷ giá ngoại tệ | 34 | 19 annual + 15 historical/current là mã tiền/vàng chưa có leaf. | [Canonical rows](#canonical-open-source-rows) |
| Chi phí thuế thu nhập doanh nghiệp | 8 | 7 annual + 1 historical/current; component chưa có leaf chính xác. | [Chi tiết annual](#open-income-tax-expense-annual-2025) |
| Chi phí quản lý chung | 18 | 14 annual + 4 historical/current; leaf nguồn chưa có schema tương đương. | [Chi tiết annual](#open-operating-expense-annual-2025) |
| Thu nhập từ góp vốn, mua cổ phần và cổ tức | 1 | CTG gộp thu nhập từ chứng khoán vốn kinh doanh và đầu tư, không có căn cứ phân bổ. | [Chi tiết](#open-dividend-income-annual-2025) |
| Thu nhập, chi phí và lãi thuần dịch vụ | 2 | CTG gộp tư vấn với đại lý/ủy thác trong cùng số nguồn, không có căn cứ chia leaf. | [Chi tiết](#open-service-income-expense-annual-2025) |
| Vốn và các quỹ | 17 | 7 annual + 10 historical/current; BID/VIB vừa direct-view và chờ primitive bảng xoay generic. | [Annual](#open-equity-funds-annual-2025); [legacy](#open-equity-funds-legacy-current) |
| Phát hành giấy tờ có giá | 8 | 5 dòng annual là trục gộp/contra; 3 tenor VPB của queue kỳ trước áp dụng toàn family nên chưa thể phân bổ theo công cụ. | [Annual](#open-issued-valuable-papers-annual-2025); [legacy](#open-issued-valuable-papers-legacy-current) |
| Tiền gửi của khách hàng | 2 | BID gộp các population pháp lý trong một số in, không có dữ liệu để tách. | [Chi tiết](#open-customer-deposits-annual-2025) |
| Tài sản Có khác | 47 | 35 annual + 12 historical/current; schema/semantic gap và sáu dash-only chờ generic fix. | [Chi tiết annual](#open-other-assets-annual-2025) |
| Tiền gửi/vay TCTD khác — nguồn vốn | 2 | Hai detail/parent trung gian source-only, không cộng lại subtotal vay. | [Canonical rows](#canonical-open-source-rows) |
| Báo cáo bộ phận hợp nhất | 17 | 15 semantic/schema gap; MBB/CTG vừa direct-view và chờ primitive generic. | [Canonical rows](#canonical-open-source-rows) |

<!-- OPEN_FAMILY_INDEX_END -->

<a id="open-family3-rnid575"></a>

## CLOSED HISTORY — Family 3: Tiền gửi tại/cho vay TCTD khác — tài sản (575)

E-0178 đã đóng Family 3 trên đủ 140 filing: **126 `VERIFIED_BY_CODEX`, 14
`NOT_OBSERVED_PROPOSAL_ONLY`, 0 `UNRESOLVED`, 763 mapping**. Formal evidence
SHA-256 là `12be4964a7ce6ad29200b51c3bbbb8a99595aa328fe426f710b4c3cf886e42a3`;
formal mapping SHA-256 là
`7b61a38464430808dbb3801ecc49e1a02dc3080a79c83d604ded021b6e32d3d4`.
Hai artifact canonical single-LF, mode `0444`, nlink 1, đã build và exact-verify
tại clean Git `827d5a736e4816c1f1fea014f9a746c444212355`; seal là
`e0178:seal:71efeb5b5337250e489941b8b8e6dc7304e2b876f8abc4c55a46caf619fec3a6`.

Toàn bộ 42/42 filing lịch sử vẫn được giữ nguyên dưới đây với
`PDF_VIEWED = 42`, tương ứng 58 ảnh physical page qua ba lượt
`17 + 12 + 29 = 58`. Các nhãn `OPEN` trong bảng là **trạng thái lịch sử đã bị
E-0178 supersede**, không còn thuộc canonical queue. Trial 18 vẫn giữ nguyên hai
số nguồn `72.305.188` và `72.305.186`; V4 không backsolve/sửa digit mà chỉ dùng
receipt hierarchy exhaustive, source-bound và disposition rounding đã khai báo.
Phụ lục [technical/pre-review provenance](#family-3-rnid-575-unresolved) tiếp tục
bảo toàn source identity, region và machine reason của artifact cũ.

<!-- INTERBANK_575_PDF_REVIEW_BEGIN -->

| ID | Trial | Ngân hàng | Kỳ báo cáo | Loại báo cáo/phạm vi | Trang PDF (và trang in nếu có) | Đã xem PDF | Kết luận dễ hiểu | Việc cần sửa |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| IDL-575-001 | 1 | ACB | Năm 2025 | BCTC hợp nhất | PDF p7, p46; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Bảng tóm tắt p7 in đúng tổng `149.990.681 / 117.882.259` và dẫn `Thuyết minh 6`; p46 phân rã đúng cùng population. | Chọn shared authority giữa summary và note detail bằng cột `Thuyết minh`, owner, kỳ và coverage; không cộng hai vùng. |
| IDL-575-002 | 3 | ACB | H1 2025 | BCTC hợp nhất | PDF p7, p45; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Bảng tóm tắt p7 in `125.447.269 / 117.882.259` và dẫn `Thuyết minh 6`; p45 là bảng chi tiết của đúng population đó. | Chọn shared authority giữa summary và detail, giữ summary làm đối chiếu tổng và detail làm nguồn leaf. |
| IDL-575-003 | 5 | ACB | Q1 2025 | BCTC hợp nhất | PDF p15; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `129.347.480 / 117.882.259`; lane so sánh có khoản vay `150.979` và dự phòng `(50.000)`, còn các ô ngoại tệ/dự phòng hiện kỳ là dấu gạch bị crop bỏ. | Bổ sung dash-cell recovery và bind đủ hai lane theo geometry trước khi chạy closure. |
| IDL-575-004 | 6 | ACB | Q1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p15; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `115.347.683 / 108.003.288`; khoản vay ngoại tệ là `- / -` và dự phòng cho vay là `- / (50.000)`, nhưng các dash không thành role-lane đầy đủ. | Bổ sung dash-cell recovery theo cùng hàng/cột và complete-lane receipt dùng chung cho mọi bank. |
| IDL-575-005 | 11 | ACB | Q4 2025 | BCTC hợp nhất | PDF p16; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `149.990.681 / 117.882.259`; khoản vay là `- / 150.979`, dự phòng so sánh `(50.000)` và một số dash cùng hàng bị detector bỏ. | Khôi phục dash bằng bbox/crop cùng hàng rồi bind hai kỳ; không suy ô trống thành 0. |
| IDL-575-006 | 12 | ACB | Q4 2025 | BCTC công ty mẹ/riêng lẻ | PDF p16; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `139.216.637 / 108.003.288`; các dòng ngoại tệ/dự phòng có dash và lane so sánh `(50.000)`, nên OCR text-only làm mất cấu trúc hai kỳ. | Dùng geometry + dash crop để hoàn tất lane rồi mới kiểm tổng; không thêm rule theo ACB. |
| IDL-575-007 | 17 | MBB | Q1 2025 | BCTC hợp nhất | PDF p29; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal tiền gửi in `53.258.553`, trong khi ba child engine đã giữ chỉ cộng `7.228.307 + 5.711.171 + 37.081.841 = 50.021.319`; bảng còn một child tiền tệ cùng group. | Bắt buộc exhaustive visible-row coverage của bốn child tiền gửi trước khi đối chiếu subtotal. |
| IDL-575-008 | 18 | MBB | Q1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p26; trang in: p18 | PDF_VIEWED | OPEN — UNRESOLVED_AFTER_PDF_REVIEW — Trên lane `31/12/2024`, sáu dòng in `5.499.868 + 5.157.164 + 55.404.500 + 3.361.724 + 2.881.932 + 0 = 72.305.188`, nhưng tổng in `72.305.186`; lệch 2 triệu đồng. | Giữ nguyên source và unresolved; không backsolve/sửa 2 triệu. Chỉ đóng khi có đính chính hoặc evidence nguồn độc lập. |
| IDL-575-009 | 25 | VPB | Năm 2025 | BCTC hợp nhất | PDF p42; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Bảng số tiền có dòng `Cấp tín dụng bằng ngoại tệ`, nhưng bảng lãi suất ngay cùng trang dùng đơn vị `%/năm` và giá trị `Không áp dụng`; engine đang trộn hai bảng. | Thêm table-role fence theo đơn vị tiền so với `%/năm`, coi `Không áp dụng` là text của bảng lãi suất. |
| IDL-575-010 | 26 | VPB | Năm 2025 | BCTC công ty mẹ/riêng lẻ | PDF p36; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Dòng tiền `Cấp tín dụng bằng ngoại tệ` nằm trên bảng balance, còn `%/năm`/`Không áp dụng` thuộc bảng lãi suất phía dưới; hai surface bị nhập chung. | Tách region bằng unit/header/reset và chỉ bind numeric lane tiền trong bảng balance. |
| IDL-575-011 | 27 | VPB | H1 2025 | BCTC hợp nhất | PDF p44; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Trên p44, `Cấp tín dụng bằng ngoại tệ` của bảng số tiền đứng gần bảng lãi suất có header `%/năm` và ô `Không áp dụng`; lỗi là nhầm loại bảng. | Dùng classifier tiền tệ-vs-lãi suất và hard boundary trước `%/năm`; không diễn giải `Không áp dụng` thành ô tiền. |
| IDL-575-012 | 28 | VPB | H1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p36; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Bảng balance và bảng rate cùng chứa nhãn tín dụng/TCTD, nhưng chỉ bảng rate in `%/năm` và `Không áp dụng`; engine chưa chặn cross-table binding. | Thêm shared unit incompatibility gate và reset vùng tại header bảng lãi suất. |
| IDL-575-013 | 37 | HDB | Năm 2025 | BCTC hợp nhất | PDF p34; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `27.921.384 / 7.374.353`; nhóm `Trong đó: Chiết khấu, tái chiết khấu` lặp, khoản vay VND có `- / 1.157.667`, và dash làm thiếu lane. | Nhận repeated subgroup là detail không cộng dồn, đồng thời recover dash theo geometry cho cả hai kỳ. |
| IDL-575-014 | 38 | HDB | Năm 2025 | BCTC công ty mẹ/riêng lẻ | PDF p33; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `31.521.384 / 12.474.353`; subgroup `Chiết khấu, tái chiết khấu` xuất hiện lặp và khoản vay VND có dash cạnh `1.157.667`. | Deduplicate repeated subgroup theo topology và bind dash cùng hàng trước closure. |
| IDL-575-015 | 39 | HDB | H1 2025 | BCTC hợp nhất | PDF p31; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Các nhánh có subtotal cục bộ; dòng cuối `7.746.366 / 7.374.353` là footer/subtotal của nhánh gần nhất, không phải một family total tự do. | Phân loại local subtotal/footer theo indentation và owner span; chỉ đóng tổng đúng population. |
| IDL-575-016 | 40 | HDB | H1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p30; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — footer cuối `10.446.366 / 12.474.353` đứng sau các subtotal tiền gửi/cho vay cục bộ; engine đang thử nó như tổng của population rộng hơn. | Thêm trailing-footer boundary và receipt chứng minh owner của subtotal, không gán theo vị trí cuối vùng. |
| IDL-575-017 | 41 | HDB | Q1 2025 | BCTC hợp nhất | PDF p3; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `8.833.734 / 7.374.353`; dòng `Dự phòng rủi ro` là sibling/contra ở cấp family với `- / -`, không phải child duy nhất phải cộng ra subtotal cho vay. | Gán provision đúng sibling level và bind hai dash; closure chỉ dùng component cùng source group. |
| IDL-575-018 | 42 | HDB | Q1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p3; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `13.583.734 / 12.474.353`, còn `Dự phòng rủi ro - / -` là sibling root; hierarchy hiện tại kéo nó xuống sai nhánh. | Sửa shared hierarchy-level inference cho provision và dash-cell binding. |
| IDL-575-019 | 43 | HDB | Q2 2025 | BCTC hợp nhất | PDF p3; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `7.746.366 / 7.374.353`; provision `- / -` là sibling root ngang cấp với nhánh tiền gửi/cho vay, không phải component của subtotal. | Dùng indentation/owner span để giữ provision ở sibling level và xác thực dash trước closure. |
| IDL-575-020 | 44 | HDB | Q2 2025 | BCTC công ty mẹ/riêng lẻ | PDF p3; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `10.446.366 / 12.474.353`; provision sibling root kế tiếp có hai dash nhưng bị đưa vào tập component sai population. | Tách source-group của loan khỏi family-level provision bằng shared topology rule. |
| IDL-575-021 | 45 | HDB | Q3 2025 | BCTC hợp nhất | PDF p3; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `13.618.632 / 7.374.353`; provision là sibling root và detector chỉ giữ một trong hai dash nhìn thấy. | Recover dash còn thiếu rồi gán provision ở cấp family, không ép nó đóng subtotal cho vay. |
| IDL-575-022 | 46 | HDB | Q3 2025 | BCTC công ty mẹ/riêng lẻ | PDF p3; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Subtotal cho vay in `17.218.632 / 12.474.353`; sibling root provision có hai dash nhìn thấy nhưng một lane bị bỏ và hierarchy đang ở sai cấp. | Kết hợp dash recovery với sibling-level provision inference dùng chung. |
| IDL-575-023 | 62 | CTG | Năm 2025 | BCTC công ty mẹ/riêng lẻ | PDF p39–40; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p39 chứa nhánh tiền gửi, p40 tiếp sang nhánh cho vay và **lặp lại ngay** header kỳ/đơn vị; tại p40 `5.922.473 + 8.883.891 = 14.806.364`, lane so sánh `2.500.000 + 1.111.649 = 3.611.649`. | Ưu tiên header local lặp trên p40; continuation không cần suy thừa kế kỳ/đơn vị từ p39. |
| IDL-575-024 | 64 | CTG | H1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p11, p21; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p11 là bảng số tiền thật; p21 chỉ là prose chính sách có cụm `tiền gửi/cho vay TCTD khác`, không có topology bảng tiền. | Đưa policy prose thành hard-negative và chọn p11 bằng owner + monetary lanes + table geometry. |
| IDL-575-025 | 65 | CTG | Q1 2025 | BCTC hợp nhất | PDF p4; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tiền gửi in `401.757.806 / 370.530.038`, cho vay `4.821.450 / 7.952.847`; provision `- / -` là sibling/contra cấp family chứ không phải component duy nhất của loan. | Sửa hierarchy level cho provision và chỉ chạy component-sum trong đúng sibling group. |
| IDL-575-026 | 75 | BID | H1 2025 | BCTC hợp nhất | PDF p9; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Nhãn provision bị xuống dòng nhưng số `(102.971) / (80.854)` vẫn thuộc family; tổng nhìn thấy khép `381.762.553 + 10.938.582 - 102.971 = 392.598.164` và `268.366.137 + 11.686.232 - 80.854 = 279.971.515`. | Nối wrapped provision label theo geometry, gán contra sibling rồi nhận owner-visible family total bằng phương trình có dấu. |
| IDL-575-027 | 86 | VIB | Năm 2025 | BCTC công ty mẹ/riêng lẻ | PDF p9, p37; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p9 là summary có lane tham chiếu `Thuyết minh`; p37 mở đúng cùng population thành các dòng không kỳ hạn/có kỳ hạn và VND/ngoại tệ. | Nhận hai view là alias: dùng note detail cho leaf, summary cho tổng đối chiếu; loại lane `Thuyết minh` khỏi numeric values. |
| IDL-575-028 | 87 | VIB | H1 2025 | BCTC hợp nhất | PDF p9, p37; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p9 chỉ tóm tắt owner/tổng và số `Thuyết minh`; p37 là detail cùng kỳ với các hàng currency, không phải population thứ hai. | Sửa dual-view arbitration bằng note reference, kỳ và leaf coverage; không cộng summary với detail. |
| IDL-575-029 | 88 | VIB | H1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p10, p38; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Summary p10 có cột `Thuyết minh`, còn p38 phân rã cùng tổng thành VND/ngoại tệ; engine đang coi cả hai là candidate ngang nhau. | Bind reference lane riêng, chọn detail làm leaf authority và dùng summary làm control total. |
| IDL-575-030 | 89 | VIB | Q1 2025 | BCTC hợp nhất | PDF p9, p37; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Owner/tổng tại p9 dẫn bằng lane `Thuyết minh`; p37 lặp owner rồi có các child currency của cùng population. | Liên kết summary-to-note bằng reference/owner/period và deduplicate population trước mapping. |
| IDL-575-031 | 90 | VIB | Q1 2025 | BCTC công ty mẹ/riêng lẻ | PDF p10, p37; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p10 là balance-sheet summary có note reference, p37 là note detail với `Tiền gửi không kỳ hạn`, `Tiền gửi có kỳ hạn`, `Cho vay`; đây là hai mức trình bày của một tổng. | Thêm shared summary/detail role và cấm chọn cột `Thuyết minh` như monetary lane. |
| IDL-575-032 | 92 | VIB | Q2 2025 | BCTC công ty mẹ/riêng lẻ | PDF p5, p32; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Summary p5 có owner/tổng cùng cột `Thuyết minh`; detail p32 mới chứa các hàng VND/ngoại tệ của đúng tổng đó. | Ghép hai vùng theo note reference + exact period; detail cấp leaf, summary chỉ corroborate total. |
| IDL-575-033 | 93 | VIB | Q3 2025 | BCTC hợp nhất | PDF p8, p36; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p8 trình bày summary kèm lane `Thuyết minh`, p36 trình bày currency detail của cùng family/kỳ; không có hai population độc lập. | Áp dụng shared dual-view deduplication và complete-lane check trên detail. |
| IDL-575-034 | 94 | VIB | Q3 2025 | BCTC công ty mẹ/riêng lẻ | PDF p9, p37; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Summary p9 dẫn note bằng `Thuyết minh`; p37 mở các dòng không kỳ hạn/có kỳ hạn và cho vay của cùng tổng nguồn. | Tách reference lane, liên kết note detail và giữ một population receipt duy nhất. |
| IDL-575-035 | 95 | VIB | Q4 2025 | BCTC hợp nhất | PDF p5, p33; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p5 chỉ có family summary/note reference; p33 có đầy đủ child VND/ngoại tệ của cùng population, nên hai candidate không được cộng dồn. | Chọn detail bằng leaf coverage, giữ summary total làm equation control và loại note-reference lane. |
| IDL-575-036 | 96 | VIB | Q4 2025 | BCTC công ty mẹ/riêng lẻ | PDF p5, p32; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Summary p5 và detail p32 có cùng owner/kỳ; p32 chứa các dòng currency trong khi p5 có lane `Thuyết minh`. | Thêm generic same-population summary/detail merge thay vì fail vì hai complete regions. |
| IDL-575-037 | 99 | ACB | Q1 2026 | BCTC hợp nhất | PDF p16; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `131.619.452 / 149.990.681`; khoản vay VND `2.000.000 / -`, còn các dòng ngoại tệ/provision có dash hoặc ô không sinh text nên thiếu lane. | Recover dash/cell bằng geometry và hoàn tất hai period lanes trước mapping. |
| IDL-575-038 | 100 | ACB | Q1 2026 | BCTC công ty mẹ/riêng lẻ | PDF p16; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `119.456.384 / 139.216.637`; khoản vay VND `3.399.504 / 1.294.915`, ngoại tệ `- / -`, còn provision không có đủ text box. | Dùng dash crop + row geometry để bind mọi role trên cả hai kỳ; blank thật vẫn giữ blank. |
| IDL-575-039 | 101 | ACB | Q2 2026 | BCTC hợp nhất | PDF p16; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `123.441.277 / 149.990.681`; khoản vay VND `6.392.840 / -`, các ô ngoại tệ và provision là dash nhưng detector bỏ một phần lane. | Bổ sung shared dash recovery và exact two-lane coverage receipt. |
| IDL-575-040 | 102 | ACB | Q2 2026 | BCTC công ty mẹ/riêng lẻ | PDF p16; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Tổng in `113.314.155 / 139.216.637`; khoản vay VND `8.229.242 / 1.294.915`, còn ngoại tệ/provision dùng dash không được bind đủ. | Khôi phục dash theo bbox cùng hàng/cột và chạy accounting chỉ sau khi đủ lane. |
| IDL-575-041 | 139 | VIB | Q2 2026 | BCTC hợp nhất | PDF p5, p32; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — p5 là summary có lane `Thuyết minh`; p32 là detail cùng population với các hàng VND/ngoại tệ và subtotal cho vay. | Merge hai view theo owner/reference/kỳ, detail cấp leaf và summary cấp total control. |
| IDL-575-042 | 140 | VIB | Q2 2026 | BCTC công ty mẹ/riêng lẻ | PDF p5, p32; trang in: — | PDF_VIEWED | OPEN — RESOLVABLE_PENDING_GENERIC_FIX — Summary p5 và detail p32 là cùng population; ngay sau detail p32 bắt đầu family kế tiếp, nên candidate hiện bị kéo quá ranh giới. | Dùng note-reference để merge hai view và thêm hard reset tại owner của family kế tiếp. |

<!-- INTERBANK_575_PDF_REVIEW_END -->


## CLOSED — family-first 140-filing `Phân tích dư nợ cho vay theo khu vực địa lý`

Lượt sweep hiện hành đã có disposition cho đủ 140/140 filing: 38
`EXACT_CUSTOMER_LOAN_GEOGRAPHY`, 78 `BROAD_POPULATION_BOUNDED_ABSENCE` và
24 bounded `NOT_OBSERVED`; **0 filing `UNRESOLVED`**. 38 filing dương tính
phát sinh 76 mapping `Trong nước`/`Nước ngoài`, 130 ô tiền và 65
phương trình tổng in nguồn đóng chính xác. 42 dấu gạch chỉ thành 0
sau pixel replay.

78 filing có bảng địa lý nhưng population là tổng dư nợ hoặc một
population trộn/rộng hơn được giữ nguyên là bounded absence; không
thu hẹp hay backsolve thành `Cho vay khách hàng`. Parent 716/759 không được
map. Không có Family11-specific OPEN ID và không làm tăng current open
queue.

Machine-readable seal:
`docs/experiments/E-0175-family-first-loan-geography-140-filing-schema-sweep-seal-v1.json`.
E-0117 annual-2025 là tập con lịch sử được tái sử dụng, không bị
chạy lại hoặc trộn kỳ.

## CLOSED — family-first 140-filing `Phân tích cho vay theo loại hình tiền tệ`

Lượt sweep hiện hành dùng authenticated SQLite document evidence store và chỉ
hydrate full axis cho mười filing dương tính, không OCR lại 130 filing absence:
đủ 140/140 filing đã có disposition, gồm 10 `VERIFIED_BY_CODEX` và 130
`VERIFIED_BOUNDED_ABSENCE`; không còn filing, ô hoặc source row `UNRESOLVED`.
Theo bank: ACB 6 present/12 absent/12 mapping, HDB 4/12/8; MBB, VPB, VCB, CTG
và VIB mỗi bank 0/18/0; BID 0/16/0. Tổng cộng có 20 mapping 757/758, 40 ô tiền
và 36 phương trình nguồn đã đóng.

| Bank | Năm/kỳ | Phạm vi | Assurance | Trang |
| --- | --- | --- | --- | ---: |
| ACB | 2025 annual | Hợp nhất / công ty mẹ | Kiểm toán | 51 / 44 |
| ACB | 2025 H1 | Hợp nhất / công ty mẹ | Soát xét | 50 / 46 |
| ACB | 2026 H1 | Hợp nhất / công ty mẹ | Soát xét | 49 / 44 |
| HDB | 2025 annual | Hợp nhất / công ty mẹ | Kiểm toán | 37 / 36 |
| HDB | 2025 H1 | Hợp nhất / công ty mẹ | Soát xét | 35 / 34 |

Tám detector hole tại bốn filing HDB được bind lại từ exact full-page pixel:
sáu glyph DASH trực tiếp và hai ô chỉ được nhận sau bounded same-row peer
evidence; cả tám mới được chuẩn hóa thành 0. Bốn filing này còn có 12 dòng/24
ô dân số thư tín dụng trả chậm được xác minh source-only để khép tổng, không
được map vào 757/758. Hai bất đồng bề mặt PP-OCRv6/VietOCR và một bất đồng số
được pixel cùng accounting corroborate/veto; Gemma không được dùng. Parent 716
và 756 không phát sinh mapping, còn 130 absence trial không hydrate numeric/page
evidence.

Không có Family10-specific OPEN ID; queue canonical hiện hành vẫn được đếm độc
lập ở đầu file (**205 OPEN / 545 entries**).
E-0116 annual-2025 cùng E-0064 lượt tám PDF hiện hành được giữ làm tập con lịch
sử. Seal:
`docs/experiments/E-0173-family-first-loan-currency-140-filing-schema-sweep-seal-v1.json`.
E-0174 chưa chạy và không có receipt: S3 registration đang security hold cho
đến khi chủ dự án xác nhận đã xoay/thu hồi hai Gemini API key bị lộ trước đó.

## CLOSED — family-first 140-filing `Phân tích dư nợ theo thời gian/thời hạn gốc`

Lượt sweep hiện hành dùng SQLite document evidence store và page shortlist,
không OCR lại: đủ 140/140 filing `VERIFIED_BY_CODEX`, không có filing vắng
family, không còn ô/source row `UNRESOLVED`, và có 438 mapping. Theo bank: ACB
18 filing/54 mapping, MBB 18/63, VPB 18/63, HDB 16/48, VCB 18/54, CTG 18/54,
BID 16/48 và VIB 18/54.

420 mapping lõi là ba bucket ngắn/trung/dài hạn; 18 mapping còn lại là margin.
876 ô tiền, 108 ô phần trăm child, 36 ô tổng phần trăm và 352 phương trình
nguồn đã đóng. Sáu population HDB bổ sung được xác minh source-only để khép
tổng và nằm ngoài schema bucket, nên không tạo dòng OPEN. Tám dấu gạch HDB
thành 0 chỉ sau pixel binding. Hai request hosted Gemma 4 trên một full page
MBB chỉ làm challenger cho một conflict cell đã có control/accounting độc lập;
Gemma không là numeric authority duy nhất.

E-0115 là tập con annual-2025 lịch sử và được sweep này supersede. Seal:
`docs/experiments/E-0171-family-first-loan-maturity-140-filing-schema-sweep-seal-v1.json`.
Formal result và ba hosted assets đã full-restore PASS trong checkpoint S3
`20260823T131218475925Z-195457c13a5d`, đăng ký bởi receipt E-0172. Public exact
replay cần restored checkpoint đó, không thể chỉ dùng bare Git checkout.

## CLOSED — family-first 140-filing `Phân tích chất lượng cho vay`

Lượt sweep hiện hành dùng document evidence store, không OCR lại: đủ 140/140
filing `VERIFIED_BY_CODEX`, không có filing vắng family, không còn ô/source row
`UNRESOLVED`, và có 727 mapping. Theo bank: ACB 18 filing/99 mapping, MBB
18/99, VPB 18/99, HDB 16/80, VCB 18/90, CTG 18/90, BID 16/80 và VIB 18/90.

700 mapping lõi là năm nhóm chất lượng; 27 mapping còn lại là khoản margin và
ứng trước tiền bán chứng khoán đã được chuẩn hóa theo đúng bốn presentation
mode nguồn. 122 bảng ngang, 18 bảng xếp dọc/nhiều cột tài sản, 136 trục hai
lane tiền và bốn trục tiền–%–tiền–% đều đóng số. Hai crop số và bốn crop
footnote khó được hosted Gemma 4 đối chứng trên exact crop; Gemma không quyết
định số một mình, ô trống không thành 0 và không có dòng OPEN mới.

Các scope E-0067B/E-0114 trước đây là tập con lịch sử và được sweep này
supersede. Machine-readable seal:
`docs/experiments/E-0169-family-first-loan-quality-140-filing-schema-sweep-seal-v1.json`.

## CLOSED — family-first 140-filing `Phân tích cho vay theo ngành nghề kinh doanh`

Lượt sweep hiện hành dùng document evidence store, không OCR lại: 98 filing
`VERIFIED_BY_CODEX`, 42 filing `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`, không
còn filing/source row `UNRESOLVED`, và có 1.520 child mapping. Theo bank:
ACB 6 verified/12 absent, MBB 18/0, VPB 18/0, HDB 16/0, VCB 4/14, CTG 2/16,
BID 16/0 và VIB 18/0.

Các filing vắng family được liệt kê đầy đủ dưới đây. Mỗi mục gồm cả hợp nhất và
công ty mẹ/riêng lẻ; `Q*` là không kiểm toán, `H1` là soát xét. Đường dẫn chính
xác của từng PDF nằm trong formal result; thư mục gốc được ghi ở cột cuối.

| Bank | Năm | Kỳ và phạm vi vắng family | Assurance | Thư mục nguồn |
| --- | ---: | --- | --- | --- |
| ACB | 2025 | Q1 hợp nhất; Q1 công ty mẹ; Q2 hợp nhất; Q2 công ty mẹ; Q3 hợp nhất; Q3 công ty mẹ; Q4 hợp nhất; Q4 công ty mẹ | Không kiểm toán | `vietstock_bctc/ACB/2025/` |
| ACB | 2026 | Q1 hợp nhất; Q1 riêng lẻ; Q2 hợp nhất; Q2 công ty mẹ | Không kiểm toán | `vietstock_bctc/ACB/2026/` |
| VCB | 2025 | H1 hợp nhất; H1 công ty mẹ; Q1 hợp nhất; Q1 công ty mẹ; Q2 hợp nhất; Q2 công ty mẹ; Q3 hợp nhất; Q3 công ty mẹ | H1 soát xét; Q1–Q3 không kiểm toán | `vietstock_bctc/VCB/2025/` |
| VCB | 2026 | H1 hợp nhất; H1 công ty mẹ; Q1 hợp nhất; Q1 công ty mẹ; Q2 hợp nhất; Q2 công ty mẹ | H1 soát xét; Q1–Q2 không kiểm toán | `vietstock_bctc/VCB/2026/` |
| CTG | 2025 | H1 hợp nhất; H1 công ty mẹ; Q1 hợp nhất; Q1 công ty mẹ; Q2 hợp nhất; Q2 công ty mẹ; Q3 hợp nhất; Q3 riêng lẻ; Q4 hợp nhất; Q4 công ty mẹ | H1 soát xét; Q1–Q4 không kiểm toán | `vietstock_bctc/CTG/2025/` |
| CTG | 2026 | H1 hợp nhất; H1 công ty mẹ; Q1 hợp nhất; Q1 công ty mẹ; Q2 hợp nhất; Q2 công ty mẹ | H1 soát xét; Q1–Q2 không kiểm toán | `vietstock_bctc/CTG/2026/` |

Graph chung quét toàn document, không dùng bank/page/note làm điều kiện. Nó chỉ
nhận một region khi shortest unique combination của owner/child, trục kỳ, đơn
vị, hình học lane và total accounting cùng khớp; branch title, hàng quấn dòng,
child subset/thứ tự và hai/bốn lane có thể thay đổi. Vì vậy 42 dòng trên là
absence của đúng filing, không phải false negative do một alias hoặc page cố
định.

Một xung đột số duy nhất đã đóng: HDB annual-2025 riêng lẻ p36, hàng `Khác`,
PP-OCRv6 `31.027.066`; pixel + VietOCR Transformer + hosted Gemma 4 cùng đọc
`31.027.068`, và chỉ số này đóng cả hai phương trình tổng. Một residual làm
tròn VPB được corroborate bằng cột phần trăm nhìn thấy; không sửa số nguồn.
Không còn dòng OPEN cho family này.

Machine-readable seal:
`docs/experiments/E-0166-family-first-loan-industry-140-filing-schema-sweep-seal-v1.json`.

## CLOSED — family-first 140-filing `Phân tích theo loại hình cho vay`

Lượt sweep hiện hành dùng document evidence store, không OCR lại: đủ 140/140
filing `VERIFIED_BY_CODEX`, không có filing vắng family, không còn ô hoặc source
row `UNRESOLVED`, và có 732 child mapping. Theo bank: ACB 18/18, MBB 18/18,
VPB 18/18, HDB 16/16, VCB 18/18, CTG 18/18, BID 16/16, VIB 18/18.

Graph chung quét toàn document và chỉ nhận một vùng khi owner, tập con các hàng
loại hình, trục kỳ/đơn vị, hình học lane và tổng kế toán cùng khớp. Nó cho phép
branch title ẩn/hiện, label quấn dòng, thứ tự con thay đổi, bốn lane tiền–%,
margin và các source row bổ sung; bank/page không tham gia rule. Các source
component `Cho vay khác`, `Cấp tín dụng khác`, thấu chi/thẻ tín dụng và thư tín
dụng trả chậm được giữ riêng rồi cộng đúng một lần vào 726.

Các thiếu hụt detector đã đóng, không còn OPEN: 140 ô có glyph `-` được crop
pixel xác thực rồi mới chuẩn hóa thành 0. VPB H1/2025 riêng lẻ p38 và Q4/2025
riêng lẻ p34 mỗi trang bị detector bỏ một chữ số `2` ở hàng `Cho vay đối với
các tổ chức, cá nhân nước ngoài`, cột so sánh. PP-OCRv6 reference-blind đọc hai
exact crop là `2` với score lần lượt 0,9999853373 và 0,9999754429; crop p38 còn
được Gemma 4 full-page đọc đối chứng. Khi thêm `2`, child sum khớp đúng tổng
in `620.775.177`; accounting chỉ là veto, không tự tạo chữ số.

Machine-readable seal:
`docs/experiments/E-0164-family-first-loan-type-140-filing-schema-sweep-seal-v1.json`.

## CLOSED — family-first 140-filing `Công cụ tài chính phái sinh`

Lượt sweep hiện hành dùng document evidence store, không OCR lại: 126 filing
`VERIFIED_BY_CODEX`, 14 filing `NOT_OBSERVED_IN_BOUND_REPORT`, 0 filing/ô
`UNRESOLVED`, 1.684 mapping và ba numeric challenger rescue. Theo bank: ACB
18/18, MBB 18/18, VPB 18/18, HDB 16/16, CTG 18/18, BID 16/16 và VIB 18/18
đã xác minh; VCB có 4 filing đã xác minh và 14 filing bounded không quan sát
thấy family.

14 bounded absence của VCB gồm: H1/Q1/Q2/Q3 năm 2025 hợp nhất và riêng lẻ;
H1/Q1/Q2 năm 2026 hợp nhất và riêng lẻ. Các dòng chính sách, giá trị hợp lý,
tổng tài sản/nợ và bảng kiểm soát rủi ro gần giống đã được giữ làm đối chứng âm,
không bị relabel thành bảng giao dịch phái sinh.

Ba bất đồng OCR đã đóng, không còn OPEN: HDB annual-2025 riêng lẻ p34 dùng
`36.046` (PP-OCRv6 + Gemma đồng thuận); VIB H1/2025 riêng lẻ p38 dùng
`(19.039)` (PP-OCRv6 + Gemma); VPB Q1/2026 riêng lẻ p34 dùng `(250.520)`
(VietOCR + Gemma, đồng thời bác token PP có scale thập phân sai). Mỗi kết quả
đều phải khép phương trình kế toán; Gemma không được dùng một mình.

Machine-readable seal:
`docs/experiments/E-0163-family-first-derivative-140-filing-schema-sweep-seal-v1.json`.

## CLOSED — family-first 140-filing `Chứng khoán kinh doanh`

<!-- TRADING_SECURITIES_OPEN_FILINGS_BEGIN -->
Lượt sweep hiện hành quét đủ 140 filing từ document evidence store, không chạy
lại OCR: 114 filing `VERIFIED_BY_CODEX`, 26 filing bounded
`NOT_OBSERVED_PROPOSAL_ONLY`, 0 `UNRESOLVED`, và 457 mapping. Theo bank, số
filing đã xác minh là ACB 18, MBB 18, VPB 12, HDB 16, VCB 18, CTG 16, BID 16;
VIB không có family trong cả 18 filing. Sáu filing riêng lẻ VPB và hai filing
riêng lẻ CTG cũng không quan sát thấy family trong đúng PDF đã bind.

Các TS-001…TS-134 trước đây đã đóng bằng các rule chung: wrapped label theo hình
học; dash nhìn thấy nhưng detector bỏ; parent/group tùy chọn chỉ in một phần
lane với pixel blank độc lập; header kỳ/đơn vị lặp hoặc dịch khi sang trang;
và các view issuer/listed-unlisted được xem là biến thể thay thế. Một subtotal
hoặc net không nhãn chỉ chọn biến thể khi đúng một tập component khép số.

VPB annual-2025 p43, `Chứng khoán nợ do các TCTD khác trong nước phát hành`,
ô so sánh có raw PP-OCRv6 `3.202.820 0UNG` vì con dấu màu chồng lên crop
`aee965db363a0752febdba0d31a36782df8b7872bf015ac6433cb00acc892b38`.
VietOCR giữ đúng tiền tố `3.202.820`; PP-OCRv6 trên năm mức loại nhiễu màu đều
đọc `3.202.820`; Gemma 4 API full-page đọc cùng giá trị; và phương trình leaf +
dự phòng khớp chính xác net so sánh `13.110.971`. Không có digit nào được sửa
chỉ để ép phương trình đóng.

Machine-readable artifacts:
`output/calibration/family-first-accounting-evidence-sweeps-v1/trading-securities.json`
và
`output/calibration/family-first-accounting-schema-mappings-v1/trading-securities.json`.
<!-- TRADING_SECURITIES_OPEN_FILINGS_END -->

## CLOSED — family-first 140-filing `Tiền gửi tại NHNN`

The baseline formal replay scanned all 140 available filings. A bounded refresh
then authenticated and root-checked only the affected MBB document packet,
proved it was the only mixed-separator candidate inside this family's topology
regions, and produced 70 `VERIFIED_BY_CODEX`, 70
`NOT_OBSERVED_PROPOSAL_ONLY`, zero `UNRESOLVED` and 245 mappings.

| ID | Bank/report | Trang | Khoản mục nguồn và giá trị nhìn thấy | Kết quả đóng |
| --- | --- | ---: | --- | --- |
| FF-CBD-001 | MBB H1/2026 công ty mẹ | 39 | `Tiền gửi tại NHNNVN bằng VND (i)`: `19.849.504` / `55.307.732`; raw PP-OCRv6 comparative token `55,307.732`; sample `sample-000498485`; crop SHA `232a952a6707802818f1971ccbd785252fc61ee28375d4a1a44f27df419daa42` | `CLOSED`: giữ nguyên raw token, bảo toàn dãy chữ số thành candidate scale 0; VietOCR cùng crop đọc `55.307.732`, lane tiền có các peer scale 0 và `55.307.732 + 10.429.524 + 667.675 = 66.404.931` đóng chính xác. Gemma lặp lại dấu sai của PP-OCR nên không tham gia authority. |

Machine-readable authorities:
`output/calibration/family-first-topology-sweeps-v1/central-bank-deposits.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/central-bank-deposits-evidence.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/central-bank-deposits-mapping.json`
và receipt cùng thư mục.

## CLOSED — family-first 140-filing `Tiền, kim loại quý và đá quý`

The baseline formal replay scanned all 140 available filings. A bounded refresh
authenticated and root-checked only the two affected VIB document packets,
proved they were the complete mixed-separator scope inside this family's
topology regions, and produced 72 `VERIFIED_BY_CODEX`, 68
`NOT_OBSERVED_PROPOSAL_ONLY`, zero `UNRESOLVED` and 292 mappings.

| ID | Bank/report | Trang | Khoản mục nguồn và giá trị nhìn thấy | Kết quả đóng |
| --- | --- | ---: | --- | --- |
| FF-CASH-001 | VIB Q2/2025 hợp nhất | 32 | `Tiền mặt bằng VND`: `1.460.873` / `1.195.200`; raw PP-OCRv6 current token `1.460,873`; crop SHA `ef1eca9f1bb9cfb0c2494ad7bd1ad5c7b8e05054457cb3b9276ab9833fac49aa` | `CLOSED`: VietOCR cùng crop và hai request Gemma độc lập đọc `1.460.873`; lane tiền scale 0 và `1.460.873 + 382.482 + 94 = 1.843.449` đóng chính xác. |
| FF-CASH-002 | VIB Q2/2025 công ty mẹ | 31 | `Tiền mặt bằng VND`: `1.460.854` / `1.195.181`; raw PP-OCRv6 current token `1,460.854`; crop SHA `99ff5a40cacb70c9b4ca1c257a946ed8484400e8d51823c03013de1da462ca40` | `CLOSED`: VietOCR cùng crop và hai request Gemma độc lập đọc `1.460.854`; lane tiền scale 0 và `1.460.854 + 382.482 + 94 = 1.843.430` đóng chính xác. |

Machine-readable authorities:
`output/calibration/family-first-topology-sweeps-v1/cash-precious-metals.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/cash-precious-metals-evidence.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/cash-precious-metals-mapping.json`
và receipt cùng thư mục.

## CLOSED — annual-2025 `Chi phí dự phòng rủi ro tín dụng`

E-0144 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025. Graph chung
tìm đúng một note chi tiết tại ACB p70, MBB p75, VPB p73, VCB p61 và VIB p52;
pixel, trục số nguồn, schema hiện hành và 12 phương trình xác minh 25 mapping/50
ô số. Một dấu `-` hiện kỳ của VPB được crop-bind trước khi chuẩn hóa 0; không có
disagreement số VietOCR và không còn dòng OPEN. Các component `Dự phòng cho vay
giao dịch ký quỹ và ứng trước` + `Dự phòng cho tài sản Có khác có rủi ro` của
VPB, cũng như hai component dự phòng trái phiếu doanh nghiệp chưa niêm yết của
VCB, được xác minh riêng rồi cộng đúng một lần vào 1228 `Dự phòng khác`.

| ID | Bank | Locator/đối chứng | Disposition và căn cứ bounded absence |
| --- | --- | --- | --- |
| CRPE-A2025-001 | HDB | Toàn filing; aggregate tại KQKD/báo cáo bộ phận và diễn giải chính sách | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết 1221 với trục kỳ, đơn vị, các hàng thành phần và tổng; aggregate không được relabel thành bảng chi tiết. |
| CRPE-A2025-002 | CTG | p60 chi phí hoạt động + aggregate KQKD | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: `Chi phí dự phòng` là nhãn chung trong family chi phí hoạt động, không phải note chi tiết rủi ro tín dụng 1221. |
| CRPE-A2025-003 | BID | p57 chi phí hoạt động + aggregate KQKD | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: dòng `(Hoàn nhập) dự phòng` tại p57 loại trừ dự phòng rủi ro tín dụng/chứng khoán; không có note chi tiết 1221 ở nơi khác trong filing. |

Các kết luận trên chỉ là vắng mặt trong đúng filing annual-2025 đã bind, không
phải khẳng định bank/source rộng hơn. Machine-readable result:
`docs/experiments/E-0144-annual-2025-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập, chi phí và lãi thuần từ hoạt động khác`

E-0145 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p69, MBB p74, VPB p71, HDB p51, VCB p60, CTG p59,
BID p56 và VIB p51. Pixel, trục số nguồn, schema hiện hành và 48 phương trình
xác minh 72 mapping/144 ô số; không có disagreement số VietOCR, family absence
hoặc dòng OPEN.

Graph chung nhận tổng có/không có nhãn, số đứng trước nhãn theo provider order,
child tùy chọn và các cách gọi `hoán đổi lãi suất`, `giao dịch phái sinh`, `nợ
xấu/cho vay đã xử lý`, `nghiệp vụ bán nợ`. Các dòng phạt hợp đồng, kinh doanh
khác, tài trợ khác hoặc `Khác` được đưa vào catch-all tương ứng chỉ bằng phép
cộng có kiểm soát trên từng số nguồn đã xác minh; parent thu, parent chi và net
đều phải đóng. Không tạo unresolved candidate mới và không dùng bank/page làm
điều kiện matching.

Machine-readable result:
`docs/experiments/E-0145-annual-2025-other-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập nhân viên của ngân hàng`

E-0149 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p73, VPB p73, BID p58 và VIB p54. Pixel, trục số nguồn,
schema hiện hành và 16 phương trình xác minh 18 mapping/36 ô số. MBB, HDB, VCB
và CTG là bounded detailed-note absences trong đúng filing đã bind.

Không còn dòng OPEN. BID được nhận bằng biến thể từ vựng tổng quát cho `cán bộ,
nhân viên bình quân`; VIB giữ topology số đứng trước nhãn. Hai số bình quân năm
ACB được kiểm tra ngược với quỹ lương/tổng thu nhập chia số nhân viên, rồi mới
quy đổi 12 tháng sang 1267/1268; OCR không được dùng làm numeric truth.

Machine-readable result:
`docs/experiments/E-0149-annual-2025-employee-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Tình hình thực hiện nghĩa vụ với ngân sách nhà nước`

E-0150 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p73, MBB p68, VPB p64, HDB p47, VCB p65, CTG p62,
BID p52 và VIB p52. Pixel, trục số nguồn, schema hiện hành và 35 phương trình
xác minh 35 mapping/140 ô logic; không có family absence hoặc dòng OPEN.

Các biến thể nhiều block, cột phải trả/ứng trước, nhánh phải thu/phải trả và
nhãn quấn dòng đều được xử lý bằng graph chung. CTG chỉ net các ô phải thu/phải
trả sau khi từng thành phần được xác thực. Dấu `-` HDB được bind pixel rồi mới
chuẩn hóa 0; numeric challenger bác lỗi VietOCR `80.055` và giữ số nguồn
`60.055`. Không có khoản mục nào cần đưa vào ledger OPEN.

Machine-readable result:
`docs/experiments/E-0150-annual-2025-state-budget-obligations-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ`

E-0151 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025. Graph chung
tìm đúng một vùng customer-scoped tại ACB p74, VPB p74, HDB p54 và VIB p54;
pixel, trục số nguồn, schema hiện hành và 10 phương trình xác minh 25 mapping/50
ô số. ACB giữ dòng `GTCG do doanh nghiệp phát hành` như chi tiết không cộng lặp;
VIB cộng bốn dòng nguồn đã xác thực đúng một lần vào 1288 `Khác`.

HDB dùng trục tương đối `Số cuối năm`/`Số đầu năm`. Crop nguồn bác proposal
VietOCR `368.639.341` và xác nhận `388.639.341`; chỉ số nguồn này mới làm tổng
so sánh `706.190.899` đóng chính xác. Không còn dòng OPEN.

| ID | Bank | Locator/đối chứng | Disposition và căn cứ bounded absence |
| --- | --- | --- | --- |
| CC-A2025-001 | MBB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết customer-collateral 1280–1288 với owner, hai trục và các hàng thành phần; policy/credit-risk mentions không được relabel. |
| CC-A2025-002 | VCB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có vùng customer-scoped thỏa graph đầy đủ; tài sản của chính ngân hàng và diễn giải bảo đảm là đối chứng âm. |
| CC-A2025-003 | CTG | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết 1280–1288 với period/unit/numeric topology trong filing annual đã bind. |
| CC-A2025-004 | BID | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết 1280–1288; các mention chính sách/hạn mức không mang bảng thành phần khách hàng. |

Các kết luận trên chỉ là vắng mặt trong đúng filing annual-2025 đã bind, không
phải khẳng định bank/source rộng hơn. Machine-readable result:
`docs/experiments/E-0151-annual-2025-customer-collateral-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Tài sản/GTCG ngân hàng đưa đi thế chấp, cầm cố và chiết khấu`

E-0152 quét đủ 695 trang và tìm đúng một vùng bank-owned tại ACB p74, MBB p78,
VPB p74, CTG p63 và VIB p54. Graph chung cho phép owner + một child khi hai kỳ,
đơn vị và ô số cùng đóng topology; vì vậy bảng MBB một hàng không còn bị loại
bởi ngưỡng hai child cũ. Nhãn quấn dòng CTG, các child trực tiếp ACB và các hàng
GTCG/repo tổng quát đều đi qua cùng matcher, không dùng bank/page để route.

Pixel, trục số nguồn, schema hiện hành và 10 phương trình xác minh 13 mapping/26
ô số. Hai dash ACB và một dash CTG chỉ thành 0 sau khi crop render được xác thực.
Các hàng nguồn tổng quát tại MBB/VPB/CTG/VIB được cộng đúng một lần vào 1293
`Tài sản khác`; không thu hẹp ngầm sang 1290/1291. Không còn dòng annual OPEN.

| ID | Bank | Locator/đối chứng | Disposition và căn cứ bounded absence |
| --- | --- | --- | --- |
| BPA-A2025-001 | HDB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có owner bank-owned cùng ít nhất một child, hai kỳ và đơn vị; customer collateral/policy không được relabel. |
| BPA-A2025-002 | VCB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có bảng 1289–1293 chi tiết thỏa graph trong filing đã bind. |
| BPA-A2025-003 | BID | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có vùng bank-owned pledged/discounted-assets đủ topology; các mention vay/bảo đảm không phải bảng family. |

Ba kết luận này chỉ là bounded absence trong đúng filing annual-2025. Các dòng
BPA-001–BPA-003 của lượt hiện hành E-0097 vẫn OPEN theo đúng source/hierarchy
cũ và không bị kết quả annual relabel. Machine-readable result:
`docs/experiments/E-0152-annual-2025-bank-pledged-assets-8bank-codex-verified-mapping-v1.json`.

<a id="open-contingent-liabilities-annual-2025"></a>

## OPEN/CLOSED — annual-2025 `Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra`

E-0153 quét đủ 695 trang và tìm đúng một vùng value-bearing tại ACB p75,
MBB p79, VPB p75, HDB p55, CTG p63, BID p59 và VIB p55. VCB p66 chỉ có
diễn giải family; p67 đã sang note giao dịch bên liên quan, nên đây là một
bounded detailed-table absence trong đúng filing annual đã bind. Pixel, trục số
nguồn, schema hiện hành và 46 phương trình xác minh 58 mapping/114 ô số.

HDB dùng hai parent trung gian và tiền ký quỹ âm; BID dùng group bảo lãnh cùng
group cam kết thanh toán; VIB map cột thuần sau khi gross và ký quỹ đóng đúng.
Tất cả 15 ReportNormId hiện có của family đều đã được dùng nơi nguồn hỗ trợ.
Các source row sau vẫn OPEN vì source có độ chi tiết/trục khấu trừ mà schema
không có. Chúng tái diễn đúng các gap CL-001–CL-005/CL-007–CL-014 của lượt hiện
hành, nên ledger giữ cùng ID thay vì tạo 13 schema-gap ID trùng nghĩa.

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| CL-001 | ACB | 75 | Cam kết trong nghiệp vụ L/C trả ngay | `3.393.925` / `1.999.681` | Parent 1295 chưa có leaf L/C trả ngay. |
| CL-002 | ACB | 75 | Cam kết trong nghiệp vụ L/C trả chậm | `3.531.929` / `1.519.333` | Parent 1295 chưa có leaf L/C trả chậm. |
| CL-003 | ACB | 75 | Trừ: Tiền ký quỹ — L/C | `(259.375)` / `(207.241)` | Đây là trục khấu trừ để ra L/C thuần, không phải schema value hiện có. |
| CL-004 | ACB | 75 | Bảo lãnh khác — dòng con | `11.804.589` / `7.752.095` | Dòng con lặp tên group parent; map thêm vào 1300 sẽ double-count. |
| CL-005 | ACB | 75 | Trừ: Tiền ký quỹ — bảo lãnh | `(1.459.157)` / `(1.068.032)` | Đây là trục khấu trừ để ra bảo lãnh thuần, chưa có leaf schema. |
| CL-007 | VPB | 75 | Trừ: Tiền ký quỹ — L/C | `(387.745)` / `(57.332)` | Trục khấu trừ đóng parent L/C nhưng chưa có leaf schema. |
| CL-008 | VPB | 75 | Cam kết bảo lãnh khác | `25.861.416` / `9.932.865` | Child lặp nghĩa group `Bảo lãnh khác`; không map hai lần vào 1300. |
| CL-009 | VPB | 75 | Trừ: Tiền ký quỹ — bảo lãnh | `(1.959.457)` / `(671.675)` | Trục khấu trừ đóng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-010 | VPB | 75 | Hoán đổi lãi suất tiền tệ chéo — nhận | `46.229.090` / `35.324.065` | Chưa có leaf nhận của swap lãi suất tiền tệ chéo. |
| CL-011 | VPB | 75 | Hoán đổi lãi suất tiền tệ chéo — trả | `46.716.751` / `36.760.922` | Chưa có leaf trả của swap lãi suất tiền tệ chéo. |
| CL-012 | VPB | 75 | Hoán đổi lãi suất một đồng tiền | `24.343.737` / `39.136.588` | Chưa có leaf swap lãi suất một đồng tiền. |
| CL-013 | VPB | 75 | Cam kết khác — dòng con | `296.447.263` / `229.654.799` | Child lặp tên parent 1304; map thêm sẽ double-count. |
| CL-014 | VPB | 75 | Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang | `294.728.542` / `229.511.446` | Dòng `Trong đó` non-additive chưa có leaf schema. |

Machine-readable result:
`docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json`.

<a id="open-financial-instruments-fair-value-annual-2025"></a>

## OPEN/CLOSED — annual-2025 `Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý`

E-0154 quét đủ 695 trang và tìm đúng hai bảng đồng thời có nhánh giá trị ghi
sổ và giá trị hợp lý tại VPB p94 và VCB p73–74. Pixel toàn trang, trục số
nguồn, schema hiện hành và 9 phương trình xác minh 41 mapping/35 ô số. Hai
trang bảng landscape được xử lý trực tiếp trong hệ tọa độ upright canonical;
không xoay về portrait và không chiếu bbox ngược vào logic dựng bảng.

ACB chỉ có diễn giải rằng chưa xác định giá trị hợp lý. MBB/BID chỉ có bảng
phái sinh; HDB/VIB chỉ có nội dung rủi ro tín dụng; CTG có bảng rủi ro tiền tệ.
Đó là sáu bounded detailed-table absences trong đúng filing annual-2025, không
phải khẳng định source-wide rằng bank không có công cụ tài chính.

Hai gap nguồn tái diễn đúng FI-001/FI-002 của lượt hiện hành nên không tạo ID
schema-gap trùng nghĩa:

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Giá trị | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| FI-001 | VPB | 94 | Giá trị hợp lý của phần lớn tài sản và nợ tài chính | `(*)` | Nguồn ghi chưa xác định được giá trị hợp lý; ký hiệu không phải 0 và giá trị ghi sổ không được dùng thay thế. |
| FI-002 | VCB | 74 | Giá trị hợp lý của phần lớn tài sản và nợ phải trả tài chính | `(*)` | Nguồn ghi không thể ước tính đáng tin cậy và không thuyết minh giá trị số; giữ OPEN. |

Machine-readable result:
`docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json`.

<a id="open-currency-risk-annual-2025"></a>

## OPEN/CLOSED — annual-2025 `Rủi ro tiền tệ`

E-0155 quét toàn bộ 695 trang và tìm đúng một bảng hiện kỳ tại ACB p84,
MBB p97, VPB p88, HDB p63, VCB p80, CTG p71, BID p65 và VIB p71. Bốn bảng
so sánh tại ACB p85, MBB p98, CTG p72 và VIB p72 được nhận diện nhưng không
được dùng thay cho kỳ báo cáo. Pixel, trục số nguồn, schema hiện hành và 74
phương trình xác minh 155 mapping/155 ô số; tám dấu `-` được xác thực trước
khi chuẩn hóa thành 0. Không có residual trình bày ở các mapping đã nhận.

Gemma 4 local GPU cứu hộ đúng hai nhãn BID mà VietOCR Transformer sai
chính tả: `Trạng thái tiền tệ nội bảng` và `Trạng thái tiền tệ ngoại bảng`.
Một full-page control làm sai chữ số nên Gemma chỉ có text-diagnostic
authority trên hai crop đó, tuyệt đối không có numeric authority.

Bảy nhóm sau vẫn OPEN/source-only. Đây là khoảng trống schema, không phải lỗi
OCR hay hình học; các giá trị của chúng vẫn được giữ đầy đủ để đóng các tổng
nguồn và không bị gộp ngầm sang một trục tiền tệ khác.

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| A2025-CRISK-001 | ACB | 84 | AUD | Không có trục AUD tương đương dưới family 1352–1482. |
| A2025-CRISK-002 | ACB | 84 | CAD | Không có trục CAD tương đương dưới family 1352–1482. |
| A2025-CRISK-003 | ACB | 84 | Vàng | Schema chưa có nhánh trục vàng. |
| A2025-CRISK-004 | ACB | 84 | JPY | Không có trục JPY tương đương dưới family 1352–1482. |
| A2025-CRISK-005 | VPB | 88 | Vàng | Schema chưa có nhánh trục vàng. |
| A2025-CRISK-006 | HDB | 63 | Vàng | Schema chưa có nhánh trục vàng. |
| A2025-CRISK-007 | CTG | 71 | Vàng | Schema chưa có nhánh trục vàng. |

Machine-readable result:
`docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json`.

<a id="open-interest-rate-risk-annual-2025"></a>

## OPEN — annual-2025 `Rủi ro lãi suất`

E-0156 quét toàn bộ 695 trang và tìm đúng một vùng hiện kỳ tại ACB p87,
MBB p95, VPB p85, HDB p65, VCB p78, CTG p75, BID p67 và VIB p68. Bốn bảng
so sánh ACB p88, MBB p96, CTG p76 và VIB p69 được giữ làm control. Header
CTG gộp text `Quá hạn`/`Không chịu lãi`, nhưng x-centre của các hàng số xác
thực hai cột độc lập. Exact replay xác minh 280 mapping/280 ô, 87 phương
trình và 10 DASH→0 có pixel component.

Chỉ còn một nhóm OPEN. Đây là residual nguồn, không phải lỗi OCR/header:

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Giá trị và lý do chưa map |
| --- | --- | ---: | --- | --- |
| AIRRISK-001 | VPB | 85 | Tổng cộng — tổng tài sản, tổng nợ, trạng thái nội bảng/ngoại bảng/kết hợp | `1.277.980.310 - 1.079.873.967 = 198.106.343`; ngoại bảng `2`; nội + ngoại = `198.106.345`, nhưng kết hợp in `198.106.343`. Giữ nguyên cả 5 ô, residual 2 và không tự sửa/làm tròn. |

Machine-readable result:
`docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-verified-mapping-v1.json`.

## COMPLETE — annual-2025 `Mua mới và thanh lý các công ty con`

E-0148 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và không tìm
thấy vùng nào có đủ ba dòng bắt buộc 1256–1258. Tất cả 25 hit gần là policy,
narrative mua/bán/hợp nhất công ty con hoặc caption dòng tiền; không hit nào có
đủ tổng giá trị, tiền thanh toán và tiền thực có trong đơn vị được mua/thanh lý.
Kết quả là 8 bounded-report absences, 0 mapping và 0 dòng OPEN.

Machine-readable result:
`docs/experiments/E-0148-annual-2025-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json`.

## COMPLETE — annual-2025 `Tiền và các khoản tương đương tiền`

E-0147 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p73, MBB p78, VPB p73, HDB p54, VCB p64, CTG p62,
BID p58 và VIB p50. Pixel, trục số nguồn, schema hiện hành và 18 phương trình
xác minh 43 mapping/86 ô số. Ba dấu `-` nhìn thấy được bind trước khi chuẩn hóa
zero. Không có family absence, disagreement số hay dòng OPEN mới.

Machine-readable result:
`docs/experiments/E-0147-annual-2025-cash-equivalents-8bank-codex-verified-mapping-v1.json`.

<a id="open-income-tax-expense-annual-2025"></a>

## OPEN — annual-2025 `Chi phí thuế thu nhập doanh nghiệp`

E-0146 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng thuế chi tiết tại ACB p71, MBB p76, VPB p64, HDB p52, VCB p62,
CTG p60, BID p57 và VIB p53. Pixel, trục số nguồn, schema hiện hành và 32
phương trình xác minh 61 mapping/120 ô số. Không có family absence. Hai proposal
số VietOCR sai được giữ nguyên và bị numeric challenger bác bỏ: CTG
`(370.109]` → `(370.109)` và VIB `2.40i` → `2.401`; không sửa tay số nguồn.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| A2025-ITAX-ACB-001 | ACB | 71 | Các khoản điều chỉnh làm tăng/(giảm) thu nhập chịu thuế khác | `31.324` / `(145.520)` | Nhãn rộng; không ép vào một leaf điều chỉnh thuế cụ thể. |
| A2025-ITAX-ACB-002 | ACB | 71 | Hoàn nhập tài sản thuế TNDN hoãn lại | `14.913` / `33.594` | Schema có net thuế hoãn lại nhưng chưa có leaf component nguồn này; dòng vẫn tham gia phương trình net. |
| A2025-ITAX-ACB-003 | ACB | 71 | Chênh lệch tạm thời được khấu trừ | `(14.858)` / `(17.190)` | Schema có net thuế hoãn lại nhưng chưa có leaf component nguồn này; dòng vẫn tham gia phương trình net. |
| A2025-ITAX-MBB-001 | MBB | 76 | Thuế TNDN do thoái vốn tại công ty con | `(341.855)` / `BLANK` | Chưa có leaf thuế hiện hành do thoái vốn; ô so sánh để trống và không đổi thành 0. |
| A2025-ITAX-VPB-001 | VPB | 64 | Các điều chỉnh khác | `45.695` / `BLANK` | Dòng thuộc phần cuốn chiếu thuế phải nộp sau chi phí thuế, chưa có leaf chi phí tương đương; ô so sánh giữ trống. |
| A2025-ITAX-CTG-001 | CTG | 60 | Điều chỉnh khác | `1.396` / `(61.403)` | Dòng thuộc phần cuốn chiếu thuế phải nộp, không ép vào family chi phí thuế. |
| A2025-ITAX-VIB-001 | VIB | 53 | Điều chỉnh khác | `163` / `169` | Nhãn rộng hơn leaf 5733 về điều chỉnh thuế các năm trước; giữ source-only nhưng dùng trong phương trình tổng đã xác minh. |

Machine-readable result:
`docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json`.

<a id="open-operating-expense-annual-2025"></a>

## OPEN — annual-2025 `Chi phí quản lý chung (Chi phí hoạt động)`

E-0143 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p70, MBB p74, VPB p72, HDB p51, VCB p61, CTG p60,
BID p57 và VIB p52. Pixel, trục số nguồn, schema hiện hành và 42 phương trình
xác minh 103 mapping/206 ô số. Bốn disagreement số của VietOCR được giữ nguyên
trong evidence và bị source/pixel/accounting bác bỏ: HDB `11.960.755` →
`11.980.755`, CTG `7.127.165` → `1.127.165`, CTG `75.588` → `15.588`, VIB
`804 696` → `804.696`. Dấu `-` hiện kỳ VCB được bind trước khi chuẩn hóa 0.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| OE-A2025-001 | ACB | 70 | Chi khác (dưới `Chi về tài sản`) | `1.222.510` / `1.212.164` | Schema không có leaf chi phí tài sản khác; không thu hẹp vào chi phí quản lý khác. |
| OE-A2025-002 | ACB | 70 | Hoàn nhập chi phí dự phòng (tổng) | `(3.362)` / `(16.637)` | Aggregate của hai component 1218/1220 đã map; giữ source-only để kiểm tra và tránh double count. |
| OE-A2025-003 | MBB | 74 | Chi khác về tài sản | `1.870.772` / `1.532.145` | Schema không có leaf chi phí tài sản khác. |
| OE-A2025-004 | VPB | 72 | Chi thuê tài sản | `1.009.205` / `924.119` | Schema không có leaf chi phí thuê tài sản dưới 1212. |
| OE-A2025-005 | VPB | 72 | Chi phí công nghệ thông tin | `1.275.072` / `928.944` | Schema không có leaf chi phí CNTT. |
| OE-A2025-006 | VPB | 72 | Chi về thuế GTGT đầu vào không được khấu trừ | `150.526` / `134.629` | Schema không có leaf VAT đầu vào không khấu trừ. |
| OE-A2025-007 | HDB | 51 | Chi thuê tài sản | `520.137` / `510.494` | Schema không có leaf chi phí thuê tài sản. |
| OE-A2025-008 | HDB | 51 | Chi về bảo dưỡng và sửa chữa tài sản | `372.394` / `300.759` | Schema không có leaf bảo dưỡng/sửa chữa tài sản. |
| OE-A2025-009 | HDB | 51 | Chi khác về tài sản | `134.640` / `155.665` | Schema không có leaf chi phí tài sản khác. |
| OE-A2025-010 | HDB | 51 | Chi phí quảng cáo, tiếp thị, khuyến mại | `812.322` / `857.690` | Schema không có leaf quảng cáo/tiếp thị/khuyến mại. |
| OE-A2025-011 | HDB | 51 | Chi phí hội nghị, lễ tân, khánh tiết | `232.505` / `458.607` | Schema không có leaf hội nghị/lễ tân/khánh tiết. |
| OE-A2025-012 | HDB | 51 | Chi phí điện, nước, vệ sinh cơ quan | `160.138` / `141.194` | Schema không có leaf tiện ích/vệ sinh cơ quan. |
| OE-A2025-013 | CTG | 60 | Chi khác (dưới `Chi về tài sản`) | `2.016.938` / `1.845.093` | Schema không có leaf chi phí tài sản khác. |
| OE-A2025-014 | CTG | 60 | Chi phí dự phòng | `161.178` / `427.692` | Nhãn nguồn chung không đủ căn cứ thu hẹp vào 1218 hoặc 1220. |

Machine-readable result:
`docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json`.

<a id="open-dividend-income-annual-2025"></a>

## OPEN/CLOSED — annual-2025 `Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức`

E-0142 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng
một note chi tiết tại ACB p69, MBB p74, VPB p71, HDB p51, VCB p60, CTG p59 và
BID p56. Pixel, trục số nguồn, schema hiện hành và 20 phương trình xác minh 28
mapping/56 ô số; bốn dấu `-` được crop-bind trước khi chuẩn hóa 0 và không có
disagreement số VietOCR. VIB chỉ in aggregate ở báo cáo kết quả hoạt động p11;
toàn filing không có note chi tiết nên tạo một bounded absence.

Graph chung bổ sung ba biến thể ngữ nghĩa, không có bank/page rule: `Thu từ cổ
tức, lợi tức`; lãi bán hoặc thu nhập thanh lý khoản góp vốn/mua cổ phần; và
`Từ chứng khoán vốn`. BID chứng minh nhãn con có thể xuống dòng với hai giá trị
xen giữa hai fragment. Matcher hiện hành E-0087 vẫn giữ nguyên scan ID và replay
byte-exact.

### CCDI-CTG-001 — CTG — dòng chứng khoán vốn gộp

- Report: BCTC hợp nhất kiểm toán năm 2025.
- Physical page / family: 59 / thu nhập từ góp vốn, mua cổ phần và cổ tức.
- Source label / accentless: `Từ chứng khoán vốn` / `tu chung khoan von`.
- Visible values: `15.823 | 13.284` (`2025 | 2024`, triệu đồng).
- Nearest schema: ReportNormId 1200 `Từ chứng khoán Vốn kinh doanh` và 1201
  `Từ chứng khoán Vốn đầu tư`.
- Review status: `OPEN_NEEDS_SCHEMA_DECISION`.
- Reason: một số in gộp hai phạm vi mà schema hiện tách riêng; không có nguồn
  phân rã để chia số hoặc chọn một leaf. Dòng được xác minh source-only và cùng
  1202 đóng `15.823 + 55.529 = 71.352` / `13.284 + 7.255 = 20.539`.

Machine-readable result:
`docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư`

E-0141 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và không tìm
thấy dòng số tổng hợp ReportNormId 5990 trong bất kỳ filing nào: 0 complete
numeric row, 1 near control, 8 bounded absences và 0 dòng OPEN.

BID p56 in một tiêu đề mục chung `Lãi thuần từ mua bán chứng khoán kinh doanh và
chứng khoán đầu tư`, rồi trình bày hai bảng độc lập 30.1 trading và 30.2
investment. Pixel và hình học xác nhận tiêu đề không có hai giá trị cùng hàng;
hai bảng con không bị cộng để tạo một dòng schema không được in. Matcher dùng
cụm mở đầu lãi/(lỗ) thuần cùng đủ hai family anchors và cho phép từ nối `mua
bán`/`và`, nhưng vẫn yêu cầu số cùng hàng để trở thành complete region. ACB,
MBB, VPB, HDB, VCB, CTG và VIB không có cả near lẫn complete match. Kết luận chỉ
có authority trong tám báo cáo annual-2025 đã bind.

Machine-readable result:
`docs/experiments/E-0141-annual-2025-combined-securities-net-8bank-bound-report-absence-v1.json`.

## CLOSED — annual-2025 `Lãi/lỗ thuần từ mua bán chứng khoán đầu tư`

E-0140 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p68, MBB p73, VPB p70, HDB p50, VCB p59, CTG p59,
BID p56 và VIB p51. Exact replay xác minh 32 mapping/64 ô logic từ 70 thành
phần nguồn cùng 16 phương trình; không có dòng OPEN, family absence hoặc
disagreement số VietOCR.

Một graph chung nhận net có/không có nhãn, owner con dưới umbrella trading +
investment và nhánh dự phòng tùy chọn. VPB/VIB in nhiều hàng dự phòng AFS/HTM;
mỗi thành phần được pixel/source-challenge trước khi cộng đúng một lần vào 1196.
VCB không in dự phòng nên đóng `thu + chi = net`. Năm dấu `-` tại ACB/VPB/VIB
được khóa bằng crop trước khi chuẩn hóa 0. Không có bank/page rule mới.

Machine-readable result:
`docs/experiments/E-0140-annual-2025-investment-securities-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh`

E-0139 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p68, MBB p73, VPB p70, HDB p50, VCB p59, CTG p58 và
BID p56. Exact replay xác minh 27 mapping/54 ô số cùng 14 phương trình; không
có dòng OPEN hoặc disagreement số VietOCR.

Graph dùng chung cho phép net có/không có nhãn, nhãn dự phòng xuống dòng, owner
trading nằm dưới umbrella trading + investment và hàng dự phòng là tùy chọn.
HDB không in dự phòng nên `thu + chi = net`; sáu vùng còn lại đóng `thu + chi +
dự phòng = net`. VIB không có graph trading trong toàn filing; note mua bán
chứng khoán đầu tư là đối chứng family khác và tạo đúng một confirmed
bound-report absence, không tạo mapping giả.

Machine-readable result:
`docs/experiments/E-0139-annual-2025-trading-securities-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối`

E-0138 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p68, MBB p73, VPB p69, HDB p50, VCB p59, CTG p58,
BID p55 và VIB p51. Exact replay xác minh 69 mapping/138 ô logic từ 152 thành
phần nguồn cùng 48 phương trình; không có dòng OPEN hoặc family absence.

Graph dùng chung nhận tổng thu/chi đứng trước, đứng sau hoặc được suy ra từ
children; nhánh vàng tùy chọn; ngoại tệ giao ngay và vàng có thể tách hoặc gộp.
VCB cộng đúng một lần các thành phần bán/đánh giá lại vàng và giao dịch/đánh giá
lại phái sinh. ACB suy ra hai parent không in giá trị từ các child rồi đối chiếu
net. MBB được nhận qua owner, siblings, trục kỳ, đơn vị và accounting closure dù
nhãn gộp không có `giao ngay`. Năm dấu `-` nhìn thấy ở VCB/BID được xác thực từ
crop trước khi chuẩn hóa thành 0; các ô không phải DASH không có disagreement số
VietOCR.

Machine-readable result:
`docs/experiments/E-0138-annual-2025-fx-gold-activity-8bank-codex-verified-mapping-v1.json`.

<a id="open-service-income-expense-annual-2025"></a>

## OPEN — annual-2025 `Thu nhập, chi phí và lãi thuần từ hoạt động dịch vụ`

E-0137 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p67, MBB p72, VPB p69, HDB p50, VCB p58, CTG p58,
BID p55 và VIB p50. Exact replay xác minh 101 mapping/202 ô giá trị cùng 48
phương trình. Hai hàng gộp của CTG vẫn tham gia chính xác vào tổng thu/tổng chi
nhưng không được tách hoặc thu hẹp vào một leaf schema đơn lẻ.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| SA-CTG-001 | CTG | 58 | Thu từ dịch vụ tư vấn, ủy thác và đại lý | `965.390` / `961.413` | Một số nguồn gộp tư vấn với ủy thác/đại lý; schema hiện chỉ có các leaf tách rời 5986 và 1163, không có căn cứ phân bổ. |
| SA-CTG-002 | CTG | 58 | Chi về dịch vụ tư vấn, ủy thác và đại lý | `(309.758)` / `(195.158)` | Một số nguồn gộp tư vấn với ủy thác/đại lý; schema hiện chỉ có các leaf tách rời 5987 và 1172, không có căn cứ phân bổ. |

Hai disagreement số của VietOCR được giữ làm evidence, không tạo thêm OPEN:
HDB đọc thiếu ngoặc mở `73.409)` nhưng pixel/source là `(73.409)`; VIB đọc
`993 178` nhưng pixel/source là `993.178`. Numeric challenger và sáu phương
trình mỗi bank giữ đúng giá trị nguồn.

Machine-readable result:
`docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập từ lãi thuần`

E-0136 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một graph báo cáo kết quả hoạt động hợp nhất tại ACB p10, MBB p13, VPB p12,
HDB p10, VCB p11, CTG p11, BID p12 và VIB p11. Exact replay xác minh 8
mapping/16 ô giá trị cùng 48 đối chiếu statement–TM–công thức; không có dòng
OPEN hoặc family absence.

Hai cách gọi `Thu nhập lãi thuần` và `Thu nhập từ lãi thuần` cùng bind vào
ReportNormId 5985. VIB có provider order đặt hai giá trị trước nhãn nhưng
geometry vẫn bind đúng hàng. Mỗi giá trị statement được đối chiếu lại với
family 1143/1151 đã xác minh và phương trình live-schema `5985 = 1143 + 1151`;
VietOCR không được dùng làm numeric truth.

Machine-readable result:
`docs/experiments/E-0136-annual-2025-net-interest-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Chi phí lãi và các khoản tương tự chi phí lãi`

E-0135 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p67, MBB p72, VPB p68, HDB p49, VCB p58, CTG p57, BID p55 và
VIB p50. Exact replay xác minh 40 mapping/80 ô giá trị cùng 16 phương trình;
không có dòng OPEN hoặc family absence.

CTG dùng hai nhãn nguồn rút gọn `Lãi tiền gửi` và `Lãi tiền vay`; matcher chỉ
nhận chúng trong graph chi phí lãi đầy đủ, không nhận bằng chuỗi độc lập. HDB
VietOCR đọc `26,150.925`, còn pixel/trục số nguồn đọc `26.150.925`; cả hai
chuẩn hóa về 26.150.925 nên không phát sinh numeric disagreement. ReportNormId
1155 `Trả lãi tiền thuê tài chính` được ghi nhận không quan sát thấy trong tám
vùng đã bind, không phải tuyên bố vắng mặt toàn PDF.

Machine-readable result:
`docs/experiments/E-0135-annual-2025-interest-expense-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập lãi và các khoản thu nhập tương tự`

E-0134 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p67, MBB p72, VPB p68, HDB p49, VCB p57, CTG p57, BID p54 và
VIB p50. Exact replay xác minh 55 mapping/110 ô giá trị cùng 28 phương trình;
không có dòng OPEN hoặc family absence.

Hai khoảng trống schema thực sự khác bản chất đã được đóng bằng append-only
ReportNormId 6075 `Thu nhập lãi cho vay khách hàng và các TCTD khác` cho dòng
gộp của MBB và 6076 `Thu phí nghiệp vụ thư tín dụng (L/C)` cho HDB. Các ID cũ,
giá trị và trạng thái mapping trước đó không đổi. Không có lỗi numeric cần
Gemma/rescue trong family annual này.

Machine-readable result:
`docs/experiments/E-0134-annual-2025-interest-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Các khoản phải trả và công nợ khác`

E-0132 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng một vùng
family tại ACB p64, MBB p67, VPB p63, HDB p47, VCB p54, CTG p54, BID p52 và
VIB p48. Exact replay xác minh 53 mapping/184 thành phần giá trị cùng 32 phương
trình; ba ô DASH của MBB/CTG được bind pixel trước khi chuẩn hóa 0. Không còn
dòng OPEN: mọi nhãn nguồn không có leaf chuyên biệt được map vào 1127 `Khác`,
giữ nguyên thành phần nguồn và đánh dấu non-additive với parent để không cộng
lặp. HDB fresh VietOCR đọc `14.169.816`; pixel, PP-OCRv6 và phương trình nguồn
xác nhận đúng là `4.169.816`.

E-0132A áp dụng cùng quyết định của chủ dự án cho lượt hiện hành E-0077 và đóng
OPL-001–OPL-018 vào 1127 `Khác`, không đổi số nguồn hay tái phân bổ parent.

Machine-readable results:
`docs/experiments/E-0132-annual-2025-other-payables-liabilities-8bank-codex-verified-mapping-v1.json`
và
`docs/experiments/E-0132A-other-payables-project-owner-other-closure-v1.json`.

<a id="open-equity-funds-annual-2025"></a>

## OPEN — annual-2025 `Vốn và các quỹ`

E-0133 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p65–66, MBB p69–70, VPB p66–67, HDB p48–49, VCB p56–57,
CTG p55–56, BID p53–54 và VIB p49–50; 23 vùng gần giống được giữ làm đối
chứng âm. Xoay toàn trang rồi detect lại CTG/BID/VIB trong tọa độ landscape
chuẩn giúp cả tám bảng xác minh 74 mapping/132 ô giá trị cùng 18 phương trình.
BID dùng word boxes để tách hai số chung một line. HDB fresh VietOCR đọc
`835.956`; pixel, PP-OCRv6 và phương trình nguồn xác nhận đúng là `535.956`.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị mở/đóng kỳ | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| A2025-CAF-001 | VPB | 66 | Quỹ đầu tư phát triển | `68.758` / `68.758` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| A2025-CAF-002 | HDB | 48 | Cổ phiếu quỹ | `(413.448)` / ô trống | Schema chưa có leaf số dư vốn tương đương; ô đóng kỳ trống không được đổi thành 0. |
| A2025-CAF-003 | HDB | 48 | Vốn đầu tư xây dựng cơ bản | `89` / `89` | Schema chưa có leaf số dư vốn tương đương. |
| A2025-CAF-004 | VCB | 56 | Quỹ đầu tư phát triển | `1.357.643` / `9.058.060` | Schema chưa có leaf riêng; hai số vẫn nằm trong subtotal quỹ và tổng vốn đã xác minh. |
| A2025-CAF-005 | CTG | 55 | Quỹ đầu tư phát triển | `512.455` / `548.467` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| A2025-CAF-006 | BID | 53 | Quỹ đầu tư phát triển | `290.036` / `6.903.598` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| A2025-CAF-007 | VIB | 49 | Quỹ đầu tư phát triển | `10.556` / `10.556` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |

Machine-readable result:
`docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json`.

<a id="open-issued-valuable-papers-annual-2025"></a>

## OPEN — annual-2025 `Phát hành giấy tờ có giá`

E-0131 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p63, MBB p66, VPB p62, HDB p46, VCB p54, CTG p53–54, BID p52
và VIB p47. Exact replay xác minh 70 mapping/188 thành phần giá trị cùng 34
phương trình. Mười một ô DASH của CTG/VIB được bind pixel rồi mới chuẩn hóa 0.
Năm dòng dưới đây vẫn nằm trong parent/tổng nguồn nhưng không được phân bổ hoặc
ép sang một leaf sai nghĩa.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| A2025-IVP-001 | VPB | 62 | Toàn family — Dưới 12 tháng | `25.699.521` / `53.256.694` | Trục kỳ hạn áp dụng cho tổng chứng chỉ tiền gửi và trái phiếu; không có phân bổ theo công cụ. |
| A2025-IVP-002 | VPB | 62 | Toàn family — Từ 12 tháng đến dưới 5 năm | `72.134.379` / `12.723.428` | Cùng trục toàn-family; không tự chia vào các leaf CD/kỳ phiếu/trái phiếu. |
| A2025-IVP-003 | VPB | 62 | Toàn family — Từ 5 năm trở lên | `9.286.753` / `995.582` | Cùng trục toàn-family; không tự chia vào các leaf theo công cụ. |
| A2025-IVP-004 | HDB | 46 | Chi phí phát hành | `(74.995)` / `(35.706)` | Dòng contra đã tham gia chính xác vào tổng giá trị thuần nhưng schema chưa có leaf chi phí phát hành riêng. |
| A2025-IVP-005 | VCB | 54 | Trung, dài hạn bằng ngoại tệ | `14` / `14` | Một số nguồn gộp hai bucket trung và dài hạn; không có căn cứ phân bổ sang 1115/1116. |

Tổng đầu năm HDB trên pixel là `81.349.744`; fresh VietOCR đọc nhầm
`31.349.744`, còn PP-OCRv6 và phương trình tổng đều xác nhận chữ số đầu là 8.

Machine-readable result:
`docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json`.

<a id="open-customer-deposits-annual-2025"></a>

## OPEN — annual-2025 `Tiền gửi của khách hàng`

E-0129 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng một vùng
family tại mỗi bank và xác minh 159 mapping cùng 43 phương trình. Hai dòng gộp
của BID p51 dưới đây vẫn tham gia tổng nguồn nhưng không được tách số in sang
các leaf pháp lý riêng.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| A2025-CD-001 | BID | 51 | Công ty cổ phần (`204.344.052`) | Dòng nguồn không phân biệt công ty cổ phần vốn Nhà nước trên 50% (1081) và công ty cổ phần khác (1082). |
| A2025-CD-002 | BID | 51 | Doanh nghiệp tư nhân, cá nhân (`1.109.262.426`) | Một số in gộp doanh nghiệp tư nhân (1083) và cá nhân (1089), không có căn cứ phân bổ. |

Machine-readable result:
`docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Vốn nhận tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro`

E-0130 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p63, MBB p66, VPB p62, HDB p45, VCB p53, CTG p53, BID p51 và
VIB p47. Exact replay xác minh 20 mapping/40 ô giá trị cùng 8 phương trình;
không phát sinh dòng OPEN. Matcher được nới theo cấu trúc chung, không theo bank:
owner có thể không kèm số note nếu đã có child + hai kỳ + hai đơn vị + ô số, và
dòng child có thể bắt đầu bằng `Vốn tài trợ` thay vì chỉ `Vốn nhận`.

BID `bằng vàng và ngoại tệ` được giữ nguyên một số nguồn rồi map một lần vào
1099 `Khác`, không thu hẹp giả thành ngoại tệ. Dấu `-` hiện kỳ của VCB được
bind bằng crop render xác thực trước khi chuẩn hóa thành 0.

Machine-readable result:
`docs/experiments/E-0130-annual-2025-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Các khoản nợ Chính phủ và Ngân hàng Nhà nước`

E-0128 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng một vùng
family tại mỗi bank. Sau adjudication của chủ dự án, exact replay xác minh 47
mapping/101 ô giá trị cùng 46 phương trình và không còn dòng OPEN. Sáu dấu `-`
được bind trực tiếp vào crop ảnh rồi chuẩn hóa 0; số so sánh `1` của HDB cũng
được bind bằng crop số vì detector không sinh một line/bbox riêng cho glyph nhỏ.

| ID | Bank | Trang | Khoản mục nguồn | Cách đóng |
| --- | --- | ---: | --- | --- |
| A2025-GN-001 | ACB | 60 | Giao dịch bán và mua lại trái phiếu Chính phủ với KBNN | Map 1033 `Vay khác`; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-002 | HDB | 44 | Vay NHNN | Map 6070; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-003 | HDB | 44 | Vay chiết khấu các giấy tờ có giá | Map 1026; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-004 | HDB | 44 | Tiền gửi của Kho bạc Nhà nước | Map 1035; số so sánh `1` được xác thực từ crop render dù line detector bỏ sót. |
| A2025-GN-005 | VCB | 52 | Vay cầm cố GTCG | Map 1027; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-006 | CTG | 51 | Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước | Cộng có kiểm soát vào 1033; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-007 | BID | 50 | Nhận vốn từ NHNN để tạm ứng cho Ban Xử lý nợ cho vay đặc biệt Ngân hàng TMCP Nam Đô | Cộng có kiểm soát vào 1033 `Vay khác`. |
| A2025-GN-008 | BID | 50 | Vay thực hiện dự án hiện đại hóa ngân hàng và Hệ thống Thanh toán của Ngân hàng bằng ngoại tệ | Cộng có kiểm soát vào 1033; ô hiện kỳ DASH pixel-bound = 0. |

Machine-readable result:
`docs/experiments/E-0128-annual-2025-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json`.

<a id="open-other-assets-annual-2025"></a>

## OPEN — annual-2025 `Tài sản Có khác`

E-0127 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại mỗi bank. 134 mapping và 66 phương trình đã đóng; 35 dòng dưới đây
giữ nguyên nguồn và `UNRESOLVED` vì chưa có schema chính xác, dòng gộp không có
phân bổ, hoặc ô DASH chưa có numeric bbox độc lập.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| A2025-OA-001 | ACB | 58 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| A2025-OA-002 | ACB | 58 | Phải thu Ngân sách Nhà nước | Không nói đây là thuế nộp thừa/được khấu trừ để map 974. |
| A2025-OA-003 | ACB | 59 | Tài sản thuế thu nhập doanh nghiệp hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-004 | ACB | 59 | Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-005 | ACB | 60 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-006 | MBB | 62 | Phải thu liên quan đến tài trợ thương mại | Chưa có leaf tương đương; ô hiện kỳ là DASH. |
| A2025-OA-007 | MBB | 62 | Các khoản phải thu miễn truy đòi theo bộ chứng từ | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-008 | MBB | 62 | Các khoản tạm ứng và đặt cọc hợp đồng | Một dòng gộp 975/973, không có phân bổ nguồn. |
| A2025-OA-009 | MBB | 62 | Dự phòng phí và dự phòng bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có leaf tương đương. |
| A2025-OA-010 | MBB | 62 | Lãi phải thu hoạt động tín dụng và phí phải thu | Dòng gộp lãi tín dụng và phí, không thu hẹp vào 983. |
| A2025-OA-011 | MBB | 63 | Lợi thế thương mại | Ô hiện kỳ là DASH chưa có numeric bbox độc lập. |
| A2025-OA-012 | MBB | 63 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-013 | VPB | 55 | Phải thu bán tài sản tài chính | Rộng hơn 976 `Phải thu từ bán chứng khoán`. |
| A2025-OA-014 | VPB | 55 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có leaf tương đương. |
| A2025-OA-015 | VPB | 55 | Nợ đủ tiêu chuẩn | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-016 | VPB | 56 | Tài sản có khác | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-017 | VPB | 56 | Lợi thế thương mại | Ô hiện kỳ là DASH chưa có numeric bbox độc lập. |
| A2025-OA-018 | VPB | 57 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-019 | HDB | 42 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| A2025-OA-020 | HDB | 43 | Phải thu từ thanh lý TSCĐ | Ô hiện kỳ là DASH và chưa có leaf chính xác. |
| A2025-OA-021 | HDB | 44 | Dự phòng rủi ro các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-022 | VCB | 50 | Phải thu từ ngân sách Nhà nước về hỗ trợ lãi suất | Là phải thu ngân sách, không phải phải thu NHNN 979. |
| A2025-OA-023 | VCB | 51 | Tài sản thuế thu nhập hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-024 | VCB | 51 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-025 | CTG | 50 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| A2025-OA-026 | CTG | 50 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-027 | BID | 49 | Các khoản phải thu khác | Parent gộp phải thu nội bộ và bên ngoài, không phải leaf hẹp 981. |
| A2025-OA-028 | BID | 49 | Tài sản thuế thu nhập doanh nghiệp hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-029 | BID | 49 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-030 | BID | 49 | Phải thu trong nghiệp vụ tài trợ thương mại | Chưa có leaf tương đương. |
| A2025-OA-031 | VIB | 44 | Phải thu từ Ngân sách Nhà nước | Không đủ nghĩa để map vào 974 hoặc 979. |
| A2025-OA-032 | VIB | 44 | Phải thu từ hoạt động tài trợ thương mại | Chưa có leaf tương đương. |
| A2025-OA-033 | VIB | 44 | Phải thu hoa hồng bảo hiểm | Không xác định đối tác là công ty bảo hiểm con như 978 yêu cầu. |
| A2025-OA-034 | VIB | 44 | Tài sản thuế TNDN hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-035 | VIB | 44 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Ô hiện kỳ là DASH và chưa có nhánh dự phòng chính xác. |

Machine-readable result:
`docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json`.

## CLOSED HISTORY — annual-2025 `Chứng khoán đầu tư`

E-0121 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và xác minh family tại
ACB p52–53, MBB p54–56, VPB p50–52, HDB p39–40, VCB p42–43, CTG p45–46,
BID p44–45 và VIB p40–41. Kết quả đã đóng 112 mapping, 224 ô giá trị và 72
phương trình. Hai hàng nguồn gộp dưới đây đã được chủ dự án adjudicate và
`VERIFIED_BY_CODEX` mà không tách giả giá trị in.

### E-0121-AIS-001 — MBB — government/government-guaranteed combined row

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 54.
- Source label: `Trái phiếu Chính phủ và trái phiếu Chính phủ bảo lãnh`.
- Nearest schema leaves: 807 và 5740.
- Structure/accounting: nằm đúng trong nhánh AFS duy nhất; giá trị nguồn tham gia
  đầy đủ các phương trình tổng đã đóng.
- Resolution: giữ nguyên số in gộp và map một lần vào 807 theo quyết định của
  chủ dự án; không đồng thời ghi 5740 nên không phát sinh double count.
- Status: `CLOSED — VERIFIED_BY_CODEX_AS_ONE_PRINTED_ROW_TO_807`.

### E-0121-AIS-002 — HDB — central-bank bill/government-security combined row

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 39.
- Source label: `Tín phiếu NHNN + Chứng khoán Chính phủ`.
- Nearest schema leaf: 831 `Chứng khoán nợ do Chính phủ phát hành`.
- Structure/accounting: nằm đúng trong nhánh HTM duy nhất; số nguồn và tổng family
  đã được pixel/PaddleOCR6/phương trình xác minh.
- Resolution: cộng có kiểm soát đúng hai hàng nguồn theo từng kỳ rồi map một lần
  vào 831: `0 + 3.225.821 = 3.225.821` và
  `13.250.000 + 3.386.590 = 16.636.590`.
- Status: `CLOSED — VERIFIED_CONTROLLED_TWO_ROW_AGGREGATION_TO_831`.

E-0122 `Các khoản đầu tư dài hạn khác` quét lại toàn bộ tám BCTC hợp nhất kiểm
toán annual-2025 và tìm đúng một vùng tại ACB p54, MBB p57, VPB p52, HDB p41,
VCB p44–45, CTG p47, BID p45 và VIB p41. 28 mapping, 56 ô giá trị và 11
phương trình đã được pixel/PaddleOCR6/schema/accounting replay xác minh; không
phát sinh dòng `OPEN` mới. Dấu `-` của CTG được map thành dự phòng 0 sau khi
bind ảnh; dấu `-` so sánh CAEX tại VPB chỉ dùng để đóng subtotal 5960 và không
được biến thành một khoản mục schema riêng. Vì không có issue mới, tổng ledger
và open queue ở đầu file không thay đổi.

E-0123 `Tăng, giảm tài sản cố định hữu hình` quét lại toàn bộ tám BCTC hợp nhất
kiểm toán annual-2025 và tìm đúng một vùng tại ACB p55, MBB p58, VPB p53, HDB
p41, VCB p48, CTG p48, BID p47 và VIB p42. 105 mapping và 32 phương trình
roll-forward/carrying-value đã được pixel, PP-OCRv6, schema và accounting replay
xác minh; không phát sinh dòng `OPEN` mới. CTG/BID/VIB dùng cùng một biến thể
hình học xoay, không có routing theo bank/page. VietOCR proposal VIB `164.02`
được giữ nguyên làm semantic evidence không đủ thẩm quyền số; numeric challenger
đọc `164.021` và phương trình nguồn xác nhận giá trị đó. Vì không có issue mới,
tổng ledger và open queue ở đầu file không thay đổi.

E-0125 `Tăng, giảm tài sản cố định vô hình` quét lại toàn bộ tám BCTC hợp nhất
kiểm toán annual-2025 và tìm đúng một vùng tại ACB p56, MBB p60, VPB p54, HDB
p42, VCB p49, CTG p49, BID p48 và VIB p43. 107 mapping và 32 phương trình
roll-forward/carrying-value đã được pixel, trục số PP-OCRv6 nguồn, schema và
accounting replay xác minh; không phát sinh dòng `OPEN` mới. Ba disclosure có
số nằm cùng câu được xử lý bằng một rule inline chung. VietOCR CTG đọc sai
`(65.998)`; pixel, PP-OCRv6 và phương trình đều khóa `(85.998)`. Kết quả
Q2/2026 và VPB Q1/2026 cũ vẫn byte-exact; tổng ledger và open queue không đổi.

E-0126 `Tăng, giảm bất động sản đầu tư` quét lại toàn bộ tám BCTC hợp nhất
kiểm toán annual-2025 và tìm đúng hai vùng duy nhất tại ACB p57 và MBB p61.
18 mapping cùng 27 phương trình được pixel, trục số PP-OCRv6 nguồn, family-local
schema và accounting replay xác minh; không phát sinh dòng `OPEN`. ACB có hai
bảng anh em `cho thuê`/`nắm giữ chờ tăng giá`: năm tổng family được cộng đúng
một lần từ các component đã xác minh, còn DASH được bind bằng hình học hàng–cột
trước khi chuẩn hóa 0. VPB/HDB/VCB/CTG/BID/VIB là bounded absence giữa family
TSCĐ vô hình và Tài sản Có khác trong đúng filing annual-2025. E-0072 hiện hành
vẫn byte-exact; tổng ledger và open queue không đổi.

E-0107 `Tiền, kim loại quý và đá quý` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p45,
MBB p46, VPB p41, HDB p33, VCB p35, CTG p39, BID p39 và VIB p35. 35 mapping
và tám phương trình tổng đã `VERIFIED_BY_CODEX`. VietOCR đọc số HDB
`1.194.005`, nhưng pixel cùng trục số nguồn xác nhận `1.194.085` và phương
trình đóng đúng; dấu gạch CTG bị provider bỏ sót được bind từ đúng ô ảnh rồi
chuẩn hóa 0. Hai bất đồng là đối chứng OCR đã đóng, không phải khoảng trống
mapping.

E-0108 `Tiền gửi tại NHNN` trên tám BCTC hợp nhất kiểm toán năm 2025 không
bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại cả tám bank và map 28
dòng với mười phương trình đóng chính xác. Tiền gửi tại ngân hàng trung ương
Lào/Campuchia được gom có kiểm soát vào 574 tại MBB/VCB/BID. Graph đã sửa lỗi
subtree tổng quát tại BID: các nhánh VND/ngoại tệ của từng jurisdiction phải
kết thúc trước khi tìm tổng family `123.629.833`. VietOCR HDB `B.416.558` được
pixel và trục số nguồn xác nhận là `8.416.558`; đây là lỗi OCR đã đóng.

E-0109 `Tiền, vàng gửi tại và cho vay/vay các TCTD khác` trên tám BCTC hợp
nhất kiểm toán năm 2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một
vùng tại ACB p46, MBB p48, VPB p42, HDB p34, VCB p36, CTG p40, BID p39 và VIB
p36; 86 mapping và 33 phương trình đóng chính xác. Các ô `DASH` của ACB được
bind từ pixel rồi chuẩn hóa 0. VietOCR HDB `27.921.364` được ảnh gốc, trục số
nguồn và phép cộng bác bỏ thành `27.921.384`. Dự phòng tổng tại MBB/VCB/BID
được map vào 5718. Đây đều là đối chứng đã đóng, không phải dòng OPEN.

E-0110 `Chứng khoán kinh doanh` trên tám BCTC hợp nhất kiểm toán năm 2025
không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p47, MBB
p49, VPB p43, HDB p34, VCB p37, CTG p41 và BID p40; VIB được xác nhận không
có family trading trong đúng báo cáo đã bind và family chứng khoán đầu tư của
VIB không bị relabel. 58 mapping và 21 phương trình đóng chính xác. Dấu `-`
hiện kỳ của HDB được bind từ pixel rồi chuẩn hóa 0. Bốn view tình trạng niêm
yết tại ACB/MBB/HDB/CTG được giữ làm đối chứng không cộng trùng. Đây là family
đã đóng, không tạo candidate hoặc dòng OPEN mới.

E-0111 `Công cụ tài chính phái sinh và tài sản/công nợ tài chính khác` trên
tám BCTC hợp nhất kiểm toán năm 2025 không bổ sung dòng OPEN: whole-PDF graph
tìm đúng một vùng tại ACB p49, MBB p66, VPB p44, HDB p35, CTG p42, BID p41 và
VIB p37; VCB được xác nhận không có family chi tiết trong báo cáo đã bind. 100
mapping và 62 phương trình đóng chính xác. Header nhiều tầng của MBB được phục
hồi thành bốn lane bằng quan hệ hình học, không bằng rule theo bank. 24 dấu `-`
được bind từ giao điểm hàng–cột rồi chuẩn hóa 0. VietOCR đọc dòng kiểm tra MBB
`173.426`; pixel, trục số nguồn và phép trừ xác nhận `173.425`. Đây là lỗi OCR
đã đóng, không phải dòng OPEN.

E-0112 `Phân tích theo loại hình cho vay` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p50,
MBB p51, VPB p45, HDB p35, VCB p39, CTG p43, BID p41 và VIB p37; 44 hàng nguồn
được `VERIFIED_BY_CODEX`, tám tổng family đóng chính xác và ba dấu `-` được giữ
typed trước khi chuẩn hóa 0. Các biến thể được thêm ở mức family, không theo
bank: `Số cuối năm/Số đầu năm`, bảng tiền/% bốn lane, khoản phải thu cho thuê
tài chính, thư tín dụng trả chậm và các cách gọi margin/đối tượng nước ngoài.
VietOCR HDB đọc tổng so sánh `442.464.841`; pixel và phép cộng các hàng xác nhận
`442.484.841`. Đây là lỗi OCR đã đóng, không phải khoảng trống mapping.

E-0113 `Phân tích cho vay theo ngành nghề kinh doanh` trên tám BCTC hợp nhất
kiểm toán năm 2025 tìm đúng một vùng tại ACB p51, MBB p52, VPB p47, HDB p37,
VCB p40, BID p42 và VIB p38; CTG được xác nhận không có family trong đúng filing
đã bind. 102 dòng nguồn được `VERIFIED_BY_CODEX`, 22 trục tiền tệ đóng đúng và
45 lỗi dấu/ký tự/dấu thập phân của VietOCR được giữ thành bất đồng đã kiểm tra.

### E-0113-LI-001 — VCB — `Thương mại, dịch vụ`

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 40.
- Source label: `Thương mại, dịch vụ`.
- Visible values: `240.272.006 | 214.488.774`.
- Structure/accounting: nằm đúng trong graph ngành duy nhất và cả hai trục đều
  tham gia phương trình tổng đã đóng.
- Resolution: schema có leaf gộp 6073 `Thương mại, dịch vụ`; giữ nguyên một số
  nguồn và map một lần, không phân bổ sang các leaf thành phần.
- Status: `CLOSED — VERIFIED_BY_CODEX_TO_COMBINED_SCHEMA_LEAF_6073`.

### E-0113-LI-002 — CTG — family không có trong filing annual-2025 đã bind

- Scan scope: toàn bộ BCTC hợp nhất kiểm toán năm 2025, dùng fresh VietOCR
  Transformer và kiểm tra các cặp anchor gần đúng.
- Result: không có bảng phân tích cho vay theo ngành; các vùng gần giống thuộc
  family khác và không vượt owner/child/period/unit/total checks.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; không suy rộng sang filing
  CTG khác.

E-0114 `Phân tích chất lượng cho vay` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p50,
MBB p51, VPB p45, HDB p36, VCB p39, CTG p43, BID p42 và VIB p66. 40 dòng năm
nhóm nợ cùng ba dòng margin độc lập ACB/MBB/VPB được map; 16 phương trình tiền
và hai phương trình phần trăm đóng đúng. HDB giữ population thư tín dụng trả
chậm kế bên ngoài core; VIB chọn đúng cột `Cho vay khách hàng` trong bảng năm
cột và không biến ô trống thành 0. Hai vùng chất lượng chứng khoán của CTG là
đối chứng âm sai owner. 14 lỗi chữ/dấu của VietOCR được pixel giải quyết; không
có bất đồng số trong 86 ô tiền. Family annual-2025 này đã đóng hoàn toàn.

E-0115 `Phân tích dư nợ theo thời gian/thời hạn gốc` trên tám BCTC hợp nhất
kiểm toán năm 2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng
tại ACB p50, MBB p51, VPB p45, HDB p36, VCB p40, CTG p44, BID p42 và VIB
p38. Cả 24 hàng lõi `Nợ ngắn hạn`/`Nợ trung hạn`/`Nợ dài hạn` cùng hai hàng
margin độc lập của MBB/VPB đã được map; 52 ô tiền, 8 ô tỷ lệ VIB và 26 phương
trình khép đúng. HDB có dân số thư tín dụng trả chậm kế bên: dòng này được xác
minh nguồn, tham gia kiểm tra tổng lớn nhưng nằm ngoài lõi kỳ hạn và không phải
khoản mục chưa map. Chín bất đồng chữ/số VietOCR được giữ minh bạch và giải
quyết bằng pixel cộng với quan hệ kế toán. Family annual-2025 này đã đóng hoàn
toàn.

E-0116 `Phân tích cho vay theo loại hình tiền tệ` trên tám BCTC hợp nhất kiểm
toán năm 2025 không bổ sung dòng OPEN. Graph chung tìm đúng một vùng tại ACB
p51 và HDB p37; bốn hàng 757/758, tám ô tiền và tám phương trình đã được xác
minh. MBB, VPB, VCB, CTG, BID và VIB không có family này trong ranh giới note
`Cho vay khách hàng` của filing annual-2025. Các cặp VND/ngoại tệ trong bảng
lãi suất và bảng liên ngân hàng là đối chứng âm. Dân số thư tín dụng trả chậm
của HDB được xác minh source-only ngoài lõi. Hai lỗi số Transformer
`418.599.083`/`442.484.641` được pixel, PaddleOCR6 và phương trình bác bỏ để
dùng `418.599.063`/`442.484.841`.

E-0117 `Phân tích dư nợ cho vay theo khu vực địa lý` trên tám BCTC hợp nhất
kiểm toán năm 2025 không bổ sung dòng OPEN. Graph chung tìm đúng một vùng tại
ACB p77, MBB p91 và VIB p59–60; sáu khoản mục 5752/765, 12 ô tiền và sáu
phương trình đã được xác minh. Dấu `-` của ACB/VIB được bind từ pixel trước khi
chuẩn hóa thành 0. VPB p81, HDB p60 và BID p63 là đối chứng địa lý có population
dư nợ rộng hơn `Cho vay khách hàng`, nên không bị thu hẹp ngầm; VCB/CTG không
có vùng đúng family. Kết quả là ba vùng unique và năm bounded-report absences,
không còn khoản mục geography annual-2025 chờ map.

E-0118 `Phân tích theo loại hình doanh nghiệp/đối tượng khách hàng` trên tám
BCTC hợp nhất kiểm toán năm 2025 tìm đúng một vùng tại MBB p52, VPB p46, HDB
p36, VCB p40, BID p42 và VIB p39; ACB/CTG không có complete region trong exact
fresh-VietOCR scan. 57 khoản mục, 114 ô tiền, 86 ô tỷ lệ và sáu tổng nguồn đã
được kiểm tra độc lập. Hai dấu `-` của MBB được bind từ pixel rồi mới chuẩn hóa
thành 0. JSON nhiều tầng từ ảnh toàn trang của Gemma chỉ là challenger cấu trúc;
matcher vẫn quyết định bằng owner/con/trật tự/hình học/trục kỳ/đơn vị và phép
cộng. Hàng gộp VCB được giữ nguyên và map một lần vào leaf 6074.

### E-0118-LE-001 — VCB — `Hợp tác xã và công ty tư nhân`

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 40.
- Source label: `Hợp tác xã và công ty tư nhân`.
- Visible values: `937.036 | 1.371.552`.
- Structure/accounting: nằm trong graph enterprise/customer-type duy nhất; cả
  hai trục tham gia tổng `Cho vay khách hàng` đã đóng chính xác.
- Resolution: schema có leaf gộp 6074 `Hợp tác xã và công ty tư nhân`; không
  chia giá trị nguồn sang 776/774 và không ghi trùng.
- Status: `CLOSED — VERIFIED_BY_CODEX_TO_COMBINED_SCHEMA_LEAF_6074`.

E-0119 `Dự phòng rủi ro cho vay khách hàng` trên tám BCTC hợp nhất kiểm toán
năm 2025 không bổ sung dòng OPEN. Whole-PDF graph tìm đúng một vùng tại ACB
p51, MBB p53, VPB p48, HDB p38, VCB p41, CTG p44, BID p43 và VIB p39. 18
lane cha, 79 dòng movement và 18 phương trình roll-forward đã được xác minh;
chín dấu `-` được bind từ pixel trước khi chuẩn hóa thành 0. MBB `2.476` của
VietOCR bị pixel và PaddleOCR6 bác bỏ để dùng `2.478`. Cột tổng và các lane
phụ chỉ là đối chứng; không còn khoản mục annual-2025 của family này chờ map.

E-0079 `Thu nhập lãi và các khoản thu nhập tương tự` không bổ sung dòng OPEN:
cả tám vùng duy nhất đã map hết các dòng nguồn vào 1143–1150. Hai lỗi mất chữ
số đầu của VietOCR tại VIB được trục số nguồn/PaddleOCR và pixel bác bỏ, nên là
đối chứng OCR đã đóng chứ không phải khoảng trống mapping.

E-0080 đóng GN-001–GN-004 và IVP-001–IVP-004/IVP-008 theo quyết định của chủ
dự án. Ba cách gọi khoản vay ngân hàng trung ương dùng schema mới 6070; tiền
gửi có kỳ hạn KBNN dùng 6071; tiền gửi Bộ Tài chính được chuyển từ 1039 sang
6072. ACB đúng 5 năm dùng biên kỳ hạn bao gồm 5 năm, MBB dùng trực tiếp hai
leaf rộng 6010/6009, và trái phiếu tăng vốn BIDV dùng 1117. Tại MBB, 6010
`Dưới 5 năm` và 1112 `Trên 5 năm` là hai hàng trái phiếu tách biệt; 6009 nhận
nguyên dòng chứng chỉ tiền gửi `Trên 12 tháng`. Chỉ ba trục kỳ hạn toàn family
của VPB còn OPEN.

E-0081 `Chi phí lãi và các khoản tương tự chi phí lãi` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một vùng tại cả tám bank và map đủ owner/tổng
1151 cùng bốn dòng con 1152/1153/1154/1156. ReportNormId 1155 được ghi nhận
không xuất hiện trong đúng tám vùng family đã bind. Lỗi VietOCR MBB
`(3:975.549)` được trục số nguồn và pixel bác bỏ thành `(3.975.549)`; đây là
đối chứng OCR đã đóng, không phải khoảng trống mapping.

E-0082 `Thu nhập/chi phí/lãi thuần từ hoạt động dịch vụ` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại MBB/VPB/VIB, map 43 dòng
vào 1157–1174, 5986–5989 và 6021–6025, đồng thời đóng 18 phương trình. Hai
dấu gạch ở `Chi về dịch vụ tư vấn` của MBB được pixel-bind và chuẩn hóa 0.
ACB/HDB/CTG/BID chỉ có tổng trên KQKD; VCB có thêm đối chứng báo cáo bộ phận;
không vùng nào có các hàng con của note nên năm báo cáo được ghi bounded
non-observation, không tạo candidate hoặc dòng OPEN giả.

E-0083 `Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối` không bổ sung
dòng OPEN: whole-PDF graph tìm đúng một note chi tiết tại MBB p47, VPB p63 và
VIB p46, map 23 dòng vào 1175–1185 cùng 6026–6027 và đóng 18 phương trình.
MBB dùng biến thể gộp ngoại tệ giao ngay + vàng với tổng cha ở cuối; VPB tách
vàng riêng; VIB không có dòng vàng; VPB/VIB dùng tổng cha ở đầu. ACB/HDB/VCB/
CTG/BID chỉ có dòng tổng KQKD hoặc đối chứng chính sách/rủi ro/tỷ giá, không có
các hàng con của note; năm báo cáo được ghi bounded non-observation, không tạo
candidate hay dòng OPEN giả. VPB giữ đúng kỳ Q1/2026.

E-0084 `Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/VCB/CTG/
BID, map 28 dòng vào 1188–1191 và đóng 14 phương trình hai kỳ. Dấu `-` kỳ so
sánh của HDB được pixel-bind và chuẩn hóa 0. PDF HDB thực sự in nhãn dự phòng
`chứng khoán đầu tư` bên trong owner chứng khoán kinh doanh; nhãn nguồn được
giữ nguyên, còn containment, vị trí hàng và hai phương trình xác nhận vai trò
1191 nên đây là caveat đã đóng, không phải sửa OCR hay dòng OPEN. VIB chỉ có
note mua bán chứng khoán đầu tư p46; vùng này là đối chứng family khác và không
bị relabel. VPB giữ đúng kỳ Q1/2026.

E-0085 `Lãi/lỗ thuần từ mua bán chứng khoán đầu tư` không bổ sung dòng OPEN:
whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/CTG/BID/VIB,
map 28 dòng vào 1193–1196 và 6028, đồng thời đóng 14 phương trình hai kỳ. MBB
có thêm nhánh dự phòng giảm giá góp vốn, đầu tư dài hạn; VIB không có nhánh dự
phòng. Ba dấu gạch ACB và một dấu gạch MBB được pixel-bind rồi chuẩn hóa 0. VCB
chỉ có số tổng báo cáo bộ phận, không có các hàng con của note nên là bounded
non-observation chứ không tạo candidate hoặc dòng OPEN. VPB giữ đúng kỳ Q1/2026.

E-0086 `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư` không bổ sung
dòng OPEN: whole-PDF graph chỉ tìm đúng một dòng tổng hợp có hai giá trị tại
MBB p47. Hai phương trình với net chứng khoán kinh doanh và net chứng khoán đầu
tư đóng đúng; bảy PDF còn lại không in dòng tổng hợp tương đương trong phạm vi
nguồn đã bind.

E-0087 `Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/VCB/CTG/
BID, map 27 dòng vào 1198–1204 và đóng 16 phương trình. Năm dấu gạch được bind
nguồn/pixel và chuẩn hóa 0; hai proposal VietOCR `1` của VPB bị native source
`-` bác bỏ. VIB chỉ có dòng tổng KQKD, không có note chi tiết nên là bounded
non-observation, không tạo candidate. VPB giữ đúng kỳ Q1/2026.

E-0088 `Chi phí quản lý chung (Chi phí hoạt động)` quét đủ 453 trang và tìm
đúng một note tại cả tám PDF. 99 dòng schema/198 ô số cùng 30 phương trình đã
`VERIFIED_BY_CODEX`; một lỗi mất chữ số của VietOCR tại VCB bị pixel và trục số
nguồn bác bỏ. OE-001–OE-004 vẫn OPEN vì là bốn ý nghĩa chi phí riêng chưa có
leaf schema tương đương; chúng vẫn được giữ trong parent/tổng nguồn và không
cản các mapping chắc chắn khác. VPB giữ đúng kỳ Q1/2026.

E-0089 `Chi phí dự phòng rủi ro tín dụng` quét đủ 453 trang và tìm đúng một
note chi tiết tại MBB p49, VPB p66 và VIB p47. 15 mapping/30 ô số và 8 phương
trình đã `VERIFIED_BY_CODEX`; hai dấu gạch không có OCR line được pixel-bind,
hai dấu gạch VPB bị VietOCR đọc thành `1` được native source bác bỏ. E-0100 đã
đóng CRPE-001/CRPE-002 vào 1228 `Dự phòng khác` theo quyết định chủ dự án và
tái kiểm tra tổng nguồn. ACB/HDB/VCB/CTG/BID được ghi nhận bounded absence
cho đúng note chi tiết trong các PDF đã bind, không phải vắng mặt số tổng KQKD.

E-0090 `Thu nhập, chi phí và lãi thuần từ hoạt động khác` quét đủ 453 trang và
tìm đúng một note chi tiết tại MBB p47, VPB p64 và VIB p46. 23 mapping/46 ô số
và 14 phương trình đã `VERIFIED_BY_CODEX`; MBB dùng biến thể net-only,
VPB/VIB dùng parent thu nhập + parent chi phí + các nhánh tùy chọn + lãi thuần.
Hai dòng thanh lý tài sản của VPB được cộng có kiểm soát theo từng kỳ. E-0100
đã cộng OACT-001 vào 1239 `Khác` đúng một lần và tái đóng parent thu nhập.
ACB/HDB/VCB/CTG/BID là bounded detailed-note absence; tổng KQKD, segment và
diễn giải không bị relabel thành note chi tiết. VPB giữ đúng kỳ Q1/2026.

E-0091 `Chi phí thuế thu nhập doanh nghiệp` quét đủ 453 trang và tìm đúng một
bảng đối chiếu chi tiết tại MBB p50, VPB p59 và VIB p48. 28 mapping/56 ô số và
20 phương trình đã `VERIFIED_BY_CODEX`; toàn bộ schema 5723–5737 được quan sát
và xác minh qua các biến thể. Hai dấu `-` của VPB chỉ được chuẩn hóa thành 0 sau
khi trục số nguồn xác nhận. TAX-001 còn OPEN vì VIB chỉ ghi `Điều chỉnh khác`,
kỳ hiện tại để trống và kỳ so sánh là `163`; nhãn này không đủ để ép vào leaf
5733 về điều chỉnh thuế của các năm trước. ACB/HDB/VCB/CTG/BID là bounded
detailed-note absence; tổng KQKD/nghĩa vụ thuế/thuế hoãn lại không bị relabel.

E-0092 `Tiền và các khoản tương đương tiền` quét đủ 453 trang và tìm đúng một
vùng chi tiết tại ACB p8, MBB p50, VPB p66, VCB p40, CTG p47 và VIB p45. 31
mapping/60 ô số và 12 phương trình đã `VERIFIED_BY_CODEX`, phủ toàn bộ family
1248–1254. Hai ô chứng khoán không in số được giữ trống thay vì đổi thành 0.
Không còn dòng nguồn chưa map trong sáu vùng. HDB/BID là bounded detailed-note
absence; số dư đầu/cuối kỳ và chính sách gần giống không bị relabel.

E-0093 `Mua mới và thanh lý các công ty con` quét đủ 453 trang và không tìm
thấy bảng nào có đủ ba dòng 1256–1258. Cả tám PDF là bounded detailed-note
absence, không phải khẳng định không có lịch sử giao dịch. HDB có HDS trở thành
công ty con nhưng đang áp dụng phương pháp tạm thời; CTG có caption dòng tiền
mua/bán công ty con. Các đối chứng này thiếu tổng giá trị, tiền thanh toán và
tiền thực có trong công ty con nên không phát sinh mapping hay dòng OPEN.

E-0094 `Thu nhập nhân viên của ngân hàng` quét đủ 453 trang và tìm đúng một
vùng chi tiết tại ACB p26, VPB p66 và VIB p49. 13 mapping/26 ô số và 14
phương trình tổng hoặc tỷ lệ đã `VERIFIED_BY_CODEX`. VPB giữ đúng kỳ Q1/2026;
VIB dùng kỳ sáu tháng. E-0100 chia hai số bình quân ACB cho đúng sáu tháng,
lưu phân số chính xác và map vào 1267/1268. MBB/HDB/VCB/CTG/BID không có bảng thu nhập nhân
viên chi tiết trong các PDF đã bind.

E-0095 `Tình hình thực hiện nghĩa vụ với ngân sách nhà nước` quét đủ 453
trang và tìm đúng một vùng tại ACB p22, MBB p49, VPB p58, HDB p32, CTG p43,
BID p26 và VIB p47. 33 mapping/147 ô số và 37 phương trình đã
`VERIFIED_BY_CODEX`. HDB dùng thêm trục tăng do hợp nhất; CTG tách phải nộp,
phải thu và số thuần cuối kỳ. 13 dấu gạch chỉ được chuẩn hóa thành 0 sau khi
xem pixel. E-0100 đưa `Tiền thuê đất` vào 1279 `Các khoản phải nộp khác`; năm
dấu gạch nhìn thấy đều bằng 0 nên mapping gộp không làm đổi tổng. VCB là bounded detailed-note absence; VPB giữ đúng
kỳ Q1/2026.

E-0096 `Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ` quét đủ
453 trang và tìm đúng một vùng tại VPB p67, VCB p47 và VIB p49. 15 mapping/30
ô số và sáu phương trình tổng đã `VERIFIED_BY_CODEX`. VIB dùng parent `Của
khách hàng` trong note chung nên nhánh `Của các TCTD khác` và tài sản chính
ngân hàng đưa đi thế chấp không bị nhập nhầm. E-0100 đã gộp CC-001–CC-004 vào
1288 `Khác` đúng một lần theo bank; hai tổng VCB/VIB tiếp tục đóng chính xác. ACB/MBB/HDB/CTG/
BID là bounded detailed-note absence; VPB giữ đúng kỳ Q1/2026.

E-0097 `Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu`
quét đủ 453 trang và tìm đúng một vùng tại VPB p67 và VIB p49. Năm mapping/10
ô số và sáu quan hệ thành phần đã `VERIFIED_BY_CODEX`; ACB/MBB/HDB/VCB/CTG/
BID là bounded detailed-note absence. BPA-001 giữ nguyên parent gộp của VPB vì
tổng nguồn in cộng cả parent lẫn các con “Trong đó”, nên hai phép tái hiện tổng
chỉ là source-presentation reconciliation chứ không phải accounting identity.
BPA-002/BPA-003 giữ hai hàng GTCG chung của VIB thay vì ép vào chứng khoán kinh
doanh/đầu tư khi PDF không in phân rã. VPB giữ đúng kỳ Q1/2026.

E-0098 `Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra` quét đủ 453 trang và tìm
đúng một note chi tiết tại ACB p26, MBB p51, VPB p68, CTG p48 và VIB p50.
47 mapping/92 ô số và 34 phương trình đã `VERIFIED_BY_CODEX`. VIB map cột
giá trị thuần sau ký quỹ; cột gộp và ký quỹ được giữ làm accounting controls.
CL-001–CL-005 và CL-007–CL-014 còn OPEN vì là các leaf L/C, ký quỹ, bảo lãnh
chi tiết, swap lãi suất hoặc `Trong đó` chưa có schema tương đương. HDB/VCB/BID
chỉ có bảng B02a và là bounded detailed-note absence; VPB giữ đúng kỳ Q1/2026.

E-0099 `Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý` quét đủ 453
trang và tìm đúng một bảng tại VPB p86, VCB p44–45 và CTG p51. 64 mapping/55
ô số và 12 phương trình đã `VERIFIED_BY_CODEX`; một dấu gạch CTG được
pixel-bind rồi chuẩn hóa 0. ACB/MBB/HDB/BID/VIB là bounded detailed-table
absence; các bảng rủi ro tiền tệ/lãi suất/thanh khoản là đối chứng âm. FI-001–
FI-003 giữ OPEN vì nguồn in `(*)` và ghi rõ giá trị hợp lý không xác định được;
không đổi `(*)` thành 0 hay sao chép giá trị ghi sổ. VPB giữ đúng kỳ Q1/2026.

E-0101 `Rủi ro tiền tệ` là base whole-PDF scan: sáu vùng duy nhất tại MBB p58,
VPB p80, HDB p38–39, VCB p50–51, CTG p60, VIB p65–66; ACB/BID là bounded
absence. E-0105 đóng CRISK-001/003–006/008/010–011 bằng quyết định làm tròn
±1, dấu gạch ngoại bảng bằng 0 và phạm vi bảng VCB→1418. Chỉ CRISK-002/007/009
còn OPEN vì schema chưa có trục vàng; không gộp vàng vào `Tiền tệ khác`.

E-0102 `Rủi ro lãi suất` là base whole-PDF scan: sáu vùng duy nhất tại MBB p57,
VPB p78, HDB p40–41, VCB p48–49, CTG p55, VIB p62–63; ACB/BID là bounded
absence. E-0105 đóng toàn bộ IRISK-001–IRISK-026. Dấu gạch được pixel-bind
thành 0; HDB được sửa vai trò dòng theo tọa độ đầy đủ; Gemma 4 đọc độc lập
bảng xoay VIB và 36 phương trình bác các chữ số rơi của challenger cũ. Family
hiện không còn dòng OPEN; VietOCR/Gemma vẫn không được dùng đơn lẻ làm numeric
truth. VPB giữ đúng kỳ Q1/2026.

E-0103 `Rủi ro thanh khoản` là base whole-PDF scan: sáu vùng duy nhất tại MBB
p60, VPB p82, HDB p43, VCB p53, CTG p58, VIB p68–69; ACB/BID là bounded
absence. E-0105 đóng LRISK-001/006–019: dấu gạch tổng nợ quá hạn bằng 0 và
Gemma 4 + full-table pixels đọc đủ VIB, khép 16 phương trình. Chỉ LRISK-002–005
còn OPEN vì bốn residual VPB lần lượt 6.000/275.500/6.001/275.499 là trọng yếu,
không được coi là làm tròn. VPB giữ đúng kỳ Q1/2026.

E-0104 `Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo` quét đủ 453 trang
và tìm đúng một vùng tại MBB p61, VPB p90, CTG p61, BID p35 và VIB p71;
ACB/HDB/VCB là bounded detailed-table absence. Graph chung dùng owner tỷ giá,
hai trục kỳ, đơn vị VND/đồng hoặc policy quy đổi VND cấp tài liệu và tối thiểu
hai hàng mã tiền tệ thẳng hàng; không dùng bank/page làm rule. Pixel, trục số
Paddle/native và live schema xác minh 46 mapping/92 ô, đồng thời giữ đủ 122 ô
nguồn. FXRATE-001–FXRATE-015 là 15 dòng tiền/vàng ngoài schema 5935–5945;
chúng đã được xác minh nguồn nhưng vẫn `OPEN`, không bị bỏ hoặc ép vào leaf
khác. VPB giữ đúng kỳ Q1/2026; BID dùng policy VND nhìn thấy tại p13.

## Open review queue (always first)

| ID | Family | Bank | Trang | Khoản mục nguồn | Lý do còn mở |
| --- | --- | --- | ---: | --- | --- |
| FXRATE-001 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | CNY | Không có leaf CNY dưới schema 5935–5945. |
| FXRATE-002 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-003 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | NZD | Không có leaf NZD dưới schema 5935–5945. |
| FXRATE-004 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | Vàng (XAU) | Không có leaf vàng/XAU dưới schema 5935–5945. |
| FXRATE-005 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | NZD | Không có leaf NZD dưới schema 5935–5945. |
| FXRATE-006 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | NOK | Không có leaf NOK dưới schema 5935–5945. |
| FXRATE-007 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-008 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | HKD | Không có leaf HKD dưới schema 5935–5945. |
| FXRATE-009 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | CNY | Không có leaf CNY dưới schema 5935–5945. |
| FXRATE-010 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | KRW | Không có leaf KRW dưới schema 5935–5945. |
| FXRATE-011 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | LAK | Không có leaf LAK dưới schema 5935–5945. |
| FXRATE-012 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-013 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | HKD | Không có leaf HKD dưới schema 5935–5945. |
| FXRATE-014 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | NOK | Không có leaf NOK dưới schema 5935–5945. |
| FXRATE-015 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | XAU | Không có leaf vàng/XAU dưới schema 5935–5945. |
| LRISK-001 | Rủi ro thanh khoản | MBB | 60 | Quá hạn — tổng tài sản/tổng nợ/chênh lệch ròng | `CLOSED_E0105`: tổng nợ in dấu `-` được chuẩn hóa 0; `28.949.005 - 0 = 28.949.005`. |
| LRISK-002 | Rủi ro thanh khoản | VPB | 82 | 1–3 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `+6.000` so với chênh lệch in. |
| LRISK-003 | Rủi ro thanh khoản | VPB | 82 | 1–5 năm — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `-275.500` so với chênh lệch in. |
| LRISK-004 | Rủi ro thanh khoản | VPB | 82 | 3–12 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `-6.001` so với chênh lệch in. |
| LRISK-005 | Rủi ro thanh khoản | VPB | 82 | Đến 1 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `+275.499` so với chênh lệch in. |
| LRISK-006–LRISK-007 | Rủi ro thanh khoản | HDB | 43 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-008–LRISK-009 | Rủi ro thanh khoản | VCB | 53 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-010–LRISK-011 | Rủi ro thanh khoản | CTG | 58 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-012–LRISK-019 | Rủi ro thanh khoản | VIB | 68–69 | Tám trục, 48 ô kỳ hiện tại/so sánh | `CLOSED_E0105`: full-table pixels + Gemma 4 challenger khớp; 16 phương trình tài sản − nợ = chênh lệch khép đúng. |
| IRISK-001–IRISK-002 | Rủi ro lãi suất | MBB/VPB | 57/78 | Quá hạn MBB và tổng trạng thái VPB | `CLOSED_E0105`: dấu `-` = 0; hai phương trình khép đúng. |
| IRISK-003–IRISK-011 | Rủi ro lãi suất | HDB | 41 | Chín trục nội/ngoại/kết hợp | `CLOSED_E0105`: sửa vai trò dòng theo full-render geometry; 18 phương trình khép đúng. |
| IRISK-012–IRISK-015 | Rủi ro lãi suất | VCB | 49 | Bốn trạng thái kết hợp | `CLOSED_E0105`: ngoại bảng in dấu `-` = 0; kết hợp bằng nội bảng. |
| IRISK-016–IRISK-017 | Rủi ro lãi suất | CTG | 55 | Hai trục quá hạn | `CLOSED_E0105`: tổng nợ in dấu `-` = 0; hai phương trình khép đúng. |
| IRISK-018–IRISK-026 | Rủi ro lãi suất | VIB | 62–63 | Chín trục × năm vai trò × hai kỳ = 90 ô | `CLOSED_E0105`: 69 crop cũ + 10 crop bổ sung + 11 dash pixel được Gemma 4/pixel đọc lại; 36 phương trình khép đúng. |
| CRISK-001 | Rủi ro tiền tệ | VPB | 80 | EUR — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | `CLOSED_E0105`: giữ nguyên bốn số nguồn; residual đúng 1 được adjudicate là sai số trình bày/làm tròn, không sửa số. |
| CRISK-002 | Rủi ro tiền tệ | VPB | 80 | Vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Family 1352 chưa có nhánh currency-axis vàng; bốn ô vẫn khép nội bảng. |
| CRISK-003–CRISK-005 | Rủi ro tiền tệ | VPB | 80 | OTHER/TOTAL/USD | `CLOSED_E0105`: map trực tiếp trạng thái kết hợp nhìn thấy; residual TOTAL đúng 1 được giữ là sai số trình bày. |
| CRISK-006 | Rủi ro tiền tệ | HDB | 39 | Trạng thái nội, ngoại bảng — EUR | `CLOSED_E0105`: ngoại bảng in `-` = 0; `3.919 + 0 = 3.919`. |
| CRISK-007 | Rủi ro tiền tệ | HDB | 39 | Vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Schema chưa có nhánh currency-axis vàng. |
| CRISK-008 | Rủi ro tiền tệ | VCB | 51 | Tổng nợ phải trả — VND | `CLOSED_E0105`: tiêu đề/phạm vi bảng cho phép map giá trị vào 1418 theo quyết định chủ dự án. |
| CRISK-009 | Rủi ro tiền tệ | CTG | 60 | Vàng — tổng tài sản, trạng thái nội bảng/kết hợp | Nguồn để trống tổng nợ và ngoại bảng vàng; schema cũng chưa có nhánh vàng. |
| CRISK-010–CRISK-011 | Rủi ro tiền tệ | VIB | 65 | Trạng thái kết hợp EUR/USD kỳ hiện tại | `CLOSED_E0105`: ngoại bảng in `-` = 0; kết hợp bằng nội bảng trên cả hai trục. |
| FI-001 | Công cụ tài chính | VPB | 86 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Nguồn ghi không thể xác định giá trị hợp lý; ký hiệu không phải 0 và giá trị ghi sổ không thay thế được. |
| FI-002 | Công cụ tài chính | VCB | 45 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Không có giá trị số được công bố; giữ nguyên nhóm nguồn OPEN. |
| FI-003 | Công cụ tài chính | CTG | 51 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Không có giá trị số được công bố; giữ nguyên nhóm nguồn OPEN. |
| CL-001 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Thư tín dụng trả ngay | Parent 1295 chưa có leaf L/C trả ngay; số vẫn đóng đúng L/C thuần. |
| CL-002 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Thư tín dụng trả chậm | Parent 1295 chưa có leaf L/C trả chậm; số vẫn đóng đúng L/C thuần. |
| CL-003 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Trừ: tiền ký quỹ (L/C) | Đây là trục khấu trừ để ra L/C thuần, không phải leaf giá trị hiện có. |
| CL-004 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Bảo lãnh khác (dòng con) | Dòng con lặp lại tên parent `Bảo lãnh khác`; chưa có leaf riêng để không map hai lần vào 1300. |
| CL-005 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Trừ: tiền ký quỹ (bảo lãnh) | Trục khấu trừ đóng đúng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-007 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trừ: tiền ký quỹ (L/C) | Trục khấu trừ đóng đúng L/C thuần nhưng chưa có leaf schema. |
| CL-008 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết bảo lãnh khác | Dòng con nằm trong parent `Bảo lãnh khác`; chưa có leaf riêng để tránh double mapping. |
| CL-009 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trừ: tiền ký quỹ (bảo lãnh) | Trục khấu trừ đóng đúng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-010 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất tiền tệ chéo — nhận | Schema hoán đổi tiền tệ 1302/5743–5744 chưa có leaf swap lãi suất chéo nhận. |
| CL-011 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất tiền tệ chéo — trả | Schema chưa có leaf swap lãi suất chéo trả. |
| CL-012 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất một đồng tiền | Schema chưa có leaf swap lãi suất một đồng tiền. |
| CL-013 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết khác (dòng con) | Dòng con lặp tên parent 1304; giữ trong phương trình parent, không map hai lần. |
| CL-014 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang | Dòng `Trong đó` là non-additive và chưa có leaf riêng. |
| BPA-001 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VPB | 67 | Giấy tờ có giá đưa đi thế chấp, cầm cố | Parent gộp bằng hai con “Trong đó”, nhưng tổng nguồn lại cộng parent và hai con lần nữa; giữ source-only, không biến hierarchy double-count thành accounting identity. |
| BPA-002 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VIB | 49 | Giấy tờ có giá đưa đi thế chấp, cầm cố | Nguồn không tách chứng khoán kinh doanh/đầu tư nên không ép vào 1290/1291. |
| BPA-003 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VIB | 49 | Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu | Nguồn không tách loại chứng khoán; family 1289–1293 chưa có leaf mục đích sử dụng tương đương. |
| TAX-001 | Chi phí thuế thu nhập doanh nghiệp | VIB | 48 | Điều chỉnh khác | Nhãn rộng hơn leaf 5733; kỳ hiện tại để trống và không được coi là 0, kỳ so sánh `163` vẫn tham gia phương trình tổng thuế hiện hành đã xác minh. |
| OE-001 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi thuê tài sản | Chưa có leaf riêng dưới 1212 `Chi về tài sản`; dòng vẫn nằm trong parent nguồn đã xác minh. |
| OE-002 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi phí công nghệ thông tin | Chưa có leaf chi phí CNTT tương đương trong family 1205–1220. |
| OE-003 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi về thuế GTGT đầu vào không được khấu trừ | Chưa có leaf chi phí VAT đầu vào không khấu trừ tương đương. |
| OE-004 | Chi phí quản lý chung (Chi phí hoạt động) | CTG | 47 | Chi khác về TSCĐ | Chưa có leaf riêng dưới 1212; hai số nguồn vẫn đóng đúng phương trình `khấu hao + chi khác về TSCĐ = chi về tài sản`. |
| CAF-001 | Vốn và các quỹ | VPB | 60 | Quỹ đầu tư phát triển | Chưa có cột số dư vốn tương đương trong schema; giá trị vẫn nằm trong tổng vốn đã xác minh. |
| CAF-002 | Vốn và các quỹ | VPB | 60 | Cổ phiếu quỹ | Không đồng nhất với nhánh số lượng cổ phiếu 5953; dấu gạch không được tự dùng làm numeric authority. |
| CAF-003 | Vốn và các quỹ | HDB | 33 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; cột trống không bị đổi thành 0. |
| CAF-004 | Vốn và các quỹ | HDB | 33 | Quỹ đầu tư xây dựng cơ bản | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| CAF-005 | Vốn và các quỹ | VCB | 36 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong subtotal quỹ và tổng vốn đã xác minh. |
| CAF-006 | Vốn và các quỹ | CTG | 43 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; dòng trống không bị đổi thành 0. |
| CAF-007 | Vốn và các quỹ | CTG | 43 | Chênh lệch đánh giá lại tài sản | Chưa có cột số dư vốn tương đương trong schema. |
| CAF-008 | Vốn và các quỹ | CTG | 43 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| CAF-009 | Vốn và các quỹ | BID | 27–28 | Báo cáo tình hình thay đổi vốn chủ sở hữu | DIRECT_PIXEL_REVIEW_2026-08-24: p27/trang in 24 là bảng xoay, hàng/cột và số đọc rõ; p28 đã sang chi tiết vốn/cổ phiếu. RESOLVABLE_PENDING_GENERIC_FIX cho primitive bảng xoay, không còn là ambiguity nguồn. |
| CAF-010 | Vốn và các quỹ | VIB | 44–45 | Báo cáo tình hình thay đổi vốn chủ sở hữu | DIRECT_PIXEL_REVIEW_2026-08-24: p44/trang in 42 là bảng xoay, hàng/cột và số đọc rõ; p45 đã sang thuyết minh khác. RESOLVABLE_PENDING_GENERIC_FIX cho primitive bảng xoay, không còn là ambiguity nguồn. |
| OPL-001 | Các khoản phải trả và công nợ khác | ACB | 22 | Thu nhập chưa thực hiện | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-002 | Các khoản phải trả và công nợ khác | ACB | 22 | Quỹ phát triển khoa học và công nghệ | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-003 | Các khoản phải trả và công nợ khác | VPB | 57 | Các khoản khách hàng trả trước | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-004 | Các khoản phải trả và công nợ khác | VPB | 57 | Doanh thu chờ phân bổ | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-005 | Các khoản phải trả và công nợ khác | VPB | 57 | Dự phòng nghiệp vụ bảo hiểm | `CLOSED_E0132A`: map 1127 `Khác`, không ép sang 1125. |
| OPL-006 | Các khoản phải trả và công nợ khác | VPB | 57 | Các khoản treo chờ chuyển tiền | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-007 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả hoạt động thanh toán thẻ | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-008 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả nhà cung cấp | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-009 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả các khoản vay khách hàng của VPBankS | `CLOSED_E0132A`: map 1127 `Khác`; giữ nguyên nghĩa vụ công ty con. |
| OPL-010 | Các khoản phải trả và công nợ khác | VPB | 57 | Tiền giữ hộ và đợi thanh toán | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-011 | Các khoản phải trả và công nợ khác | CTG | 43 | Các khoản lãi, phí phải trả | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-012 | Các khoản phải trả và công nợ khác | VIB | 43 | Các khoản lãi, phí phải trả | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-013 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả cổ tức cho cổ đông | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả nội bộ. |
| OPL-014 | Các khoản phải trả và công nợ khác | VIB | 43 | Tiền giữ hộ và đợi thanh toán | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-015 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả thanh toán giữa các TCTD | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-016 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả chuyển tiền chờ thanh toán | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-017 | Các khoản phải trả và công nợ khác | VIB | 43 | Các khoản chờ thanh toán khác | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-018 | Các khoản phải trả và công nợ khác | VIB | 43 | Doanh thu chờ phân bổ | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| PM-001 | Dự phòng rủi ro cho vay khách hàng | VPB | 45 | Dự phòng chung, dự phòng cụ thể, dự phòng cho vay giao dịch ký quỹ và ứng trước | CLOSED_STALE_PERIOD_GAP: đây là ghi chú lịch sử của Q1/2026. Evidence store hiện đã có VPB Q2/2026 hợp nhất (doc 113, sha256:34cf838605a2f3e4bd273e8f0c3d248461787ae446bfee082b3a432254297900) và riêng lẻ (doc 114, sha256:9f5febbb673f0e69c8387326460a41c2f301afc0afb6f640bcdd429959b3512f); PM-001 không thuộc canonical OPEN. |
| OA-001 | Tài sản Có khác | VPB | 51 | Phải thu bán tài sản tài chính | Nghĩa nguồn rộng hơn 976 `Phải thu từ bán chứng khoán`; không thu hẹp ngầm. |
| OA-002 | Tài sản Có khác | VPB | 51 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có khoản mục con tương đương trong family 966–1023. |
| OA-003 | Tài sản Có khác | VPB | 52 | Số dư đầu kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-004 | Tài sản Có khác | VPB | 52 | Trích lập dự phòng rủi ro trong kỳ | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-005 | Tài sản Có khác | VPB | 52 | Số dư cuối kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-006 | Tài sản Có khác | VPB | 52 | Dự phòng tài sản Có rủi ro tín dụng | Đây là phân rã số dư dự phòng, không phải population chất lượng 1018. |
| OA-007 | Tài sản Có khác | VPB | 52 | Dự phòng cụ thể | Chưa có khoản mục dự phòng `Tài sản Có khác`. |
| OA-008 | Tài sản Có khác | VPB | 52 | Dự phòng rủi ro phải thu khó đòi | Chưa có khoản mục con tương đương. |
| OA-009 | Tài sản Có khác | VIB | 39 | Phải thu từ Ngân sách Nhà nước | Không đồng nhất với 979 `Phải thu từ NHNN Việt Nam`. |
| OA-010 | Tài sản Có khác | VIB | 39 | Phải thu từ hoạt động tài trợ thương mại | Chưa có khoản mục con tương đương. |
| OA-011 | Tài sản Có khác | VIB | 39 | Phải thu hoa hồng bảo hiểm | Chưa chứng minh tương đương khoản phải thu từ công ty bảo hiểm con. |
| OA-012 | Tài sản Có khác | VIB | 39 | Tài sản thuế TNDN hoãn lại | Chưa có khoản mục con tương đương trong family 966–1023. |
| IVP-005 | Phát hành giấy tờ có giá | VPB | 56 | Dưới 12 tháng | Trục kỳ hạn áp dụng cho toàn family gồm chứng chỉ tiền gửi và trái phiếu, không riêng một instrument leaf. |
| IVP-006 | Phát hành giấy tờ có giá | VPB | 56 | Từ trên 12 tháng đến 5 năm | Trục kỳ hạn toàn family, không được gán riêng vào CD/kỳ phiếu/trái phiếu. |
| IVP-007 | Phát hành giấy tờ có giá | VPB | 56 | Từ trên 5 năm trở lên | Trục kỳ hạn toàn family, không được gán riêng vào CD/kỳ phiếu/trái phiếu. |

The shared family locator follows a strict minimal-anchor search.  It enumerates
every parent+child pair first, then every child+child pair, over both complete and
near branch regions in the entire PDF.  If one pair is unique it stops; if pairs
collide it tries every remaining pair before expanding to parent+two-child or
three-child combinations.  Large monetary rows only prioritize which pair is
tested first.  They do not grant mapping authority.  The selected pair locates a
region but never truncates it: the retained graph still contains every observed
row, axis, optional branch, total and accounting relation.  Sibling order is not
fixed, while the parent must precede its descendant region.  No bank, filename,
page or note identifier participates in this decision.

| IDs | Current disposition |
| --- | --- |
| LG-001–LG-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; MBB/VIB alone have the exact customer-loan geography family. Five broader total-loan tables and VCB's segment report stay negative controls, never narrowed or relabelled |
| IDL-001–IDL-002 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận HDB/VCB bắt đầu thuyết minh từ family 592 |
| CBD-001–CBD-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; hai dòng cộng thành 2.148.359 và map vào ReportNormId 574 `Tiền gửi khác` |
| LT-001–LT-002 | `RESOLVED_VERIFIED_BY_CODEX` |
| LI-001, LI-008, LI-009 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT` |
| LI-002–LI-007, LI-010–LI-011 | `RESOLVED_VERIFIED_BY_CODEX` |
| LE-001–LE-011 | `RESOLVED` by exact family replay, non-additive graph equivalence, or pixel replay |
| CD-001–CD-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VPB `64.165` và VIB `174` map vào schema 770 đã đổi tên để bao quát MTV hoặc trên MTV có vốn Nhà nước trên 50% |
| PM-001 | `CLOSED_STALE_PERIOD_GAP`; superseded bởi hai filing VPB Q2/2026 đã bind trong evidence store; không thuộc canonical OPEN |
| SEC-001 | `RESOLVED_VERIFIED_BY_CODEX`; E-0067 đã xử lý AFS VIB, map trực tiếp 807/824 và chuyển riêng phép gộp TCTD sang IS-002 |
| CPM-001–CPM-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận các mốc bắt đầu thuyết minh loại trừ family 561 trong năm PDF |
| IS-001 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; BID p23 kế thừa tuyên bố `Triệu VND` nhìn thấy tại p13 của cùng PDF và toàn vùng AFS/HTM được replay-bound |
| IS-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VIB gộp đúng hai dòng TCTD theo từng kỳ vào ReportNormId 808, giữ nguyên hai thành phần và hai phương trình |
| DFI-001 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận VCB không có thuyết minh family 631 |
| IFA-001–IFA-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng biến động TSCĐ vô hình chi tiết trong PDF đã bind |
| IFA-006 | `RESOLVED_VERIFIED_BY_CODEX`; schema 6069 được thêm và map cho disclosure TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng tại VPB/VIB |
| IP-001–IP-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/VPB/HDB/VCB/CTG/BID/VIB không có bảng biến động bất động sản đầu tư chi tiết trong đúng PDF đã bind; statement, policy, cash-flow và expense mentions giữ làm đối chứng âm |
| OA-001–OA-012 | `OPEN_SCHEMA_OR_SEMANTIC_GAP`; 58 khoản mục chắc chắn vẫn đã map, 12 dòng này được giữ nguyên nguồn và không ép vào schema gần nhất |
| GN-001–GN-004 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; ba nhãn vay NHNN/Ngân hàng Trung ương map 6070, tiền gửi có kỳ hạn KBNN map 6071; BID `Tiền gửi Bộ Tài chính` được chuyển khỏi 1039 sang 6072 |
| EIR-001–EIR-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID chuyển từ tiền gửi khách hàng thẳng sang family nợ kế tiếp, không có note vốn nhận tài trợ/ủy thác trong PDF đã bind |
| EIR-006–EIR-007 | `RESOLVED_VERIFIED_BY_CODEX`; hai nguồn nhỏ chưa có leaf riêng — ODA của VPB và chương trình nhà ở qua NHNN của VIB — giữ nguyên nhãn nguồn và map vào leaf `Khác` 1099 |
| IVP-001–IVP-004, IVP-008 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; ACB đúng 5 năm map 1103/1111, MBB broad tenor map trực tiếp 6009/6010, BID trái phiếu tăng vốn map 1117 |
| IVP-005–IVP-007 | `OPEN_SOURCE_SCOPE_GAP`; ba kỳ hạn VPB áp dụng cho toàn family, chưa có phân bổ nhìn thấy theo từng công cụ |
| OPL-001–OPL-018 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; E-0132A map toàn bộ vào 1127 `Khác`, giữ nguyên 36 giá trị nguồn và không cộng lặp với parent/tổng |
| OE-001–OE-004 | `OPEN_SCHEMA_GAP`; 99 khoản mục chắc chắn vẫn đã map. Bốn dòng chi phí riêng được giữ trong parent/tổng và các phương trình nguồn, không ép vào leaf gần nghĩa |
| CRPE-001–CRPE-002 | `CLOSED_BY_PROJECT_OWNER_TO_1228`; E-0100 giữ nguyên bốn giá trị nguồn, map hai dòng vào `Dự phòng khác` và tái đóng đúng tổng VPB/VIB |
| CRPE-003–CRPE-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có note chi tiết 1221 trong PDF đã bind, dù có thể có dòng tổng KQKD hoặc diễn giải chính sách |
| OACT-001 | `CLOSED_BY_PROJECT_OWNER_TO_1239`; E-0100 cộng `41 / 9` vào dòng Khác hiện có đúng một lần và tái đóng parent thu nhập VPB |
| OACT-002–OACT-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có note hoạt động khác chi tiết trong PDF đã bind; tổng KQKD, segment và diễn giải là đối chứng âm |
| TAX-001 | `OPEN_SCHEMA_GAP_WITH_BLANK_CURRENT_AXIS`; 28 khoản mục chắc chắn vẫn đã map. Dòng VIB `Điều chỉnh khác` chỉ có số kỳ so sánh `163`; ô kỳ hiện tại trống không bị đổi thành 0 và nhãn không bị ép vào 5733 |
| TAX-002–TAX-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng đối chiếu chi phí thuế chi tiết trong PDF đã bind |
| CEQ-001–CEQ-002 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; HDB/BID không có bảng chi tiết tiền và tương đương tiền 1248–1254 trong PDF đã bind; số dư lưu chuyển tiền tệ và diễn giải chính sách là đối chứng âm |
| SAD-001–SAD-008 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; cả tám PDF không có bảng chi tiết 1255–1258. Giao dịch HDS của HDB và caption dòng tiền CTG được giữ làm đối chứng, không bị relabel |
| EI-001–EI-002 | `CLOSED_BY_PROJECT_OWNER_MONTHLY_DERIVATION`; E-0100 chia chính xác các số sáu tháng cho 6: lương `15 / 43÷3`, thu nhập `81÷2 / 247÷6`, rồi map 1267/1268 |
| SBO-001 | `CLOSED_BY_PROJECT_OWNER_TO_1279`; năm dấu gạch HDB được pixel-bind thành 0 và gộp vào `Các khoản phải nộp khác`, không làm đổi tổng |
| CC-001–CC-004 | `CLOSED_BY_PROJECT_OWNER_TO_1288`; E-0100 gộp một lần vào dòng Khác hiện có. VCB 1288 thành `688.039.608 / 687.893.688`; VIB thành `204.865.534 / 153.501.606`, và hai total đóng đúng |
| BPA-001–BPA-003 | `OPEN_SOURCE_HIERARCHY_OR_SCHEMA_GAP`; VPB parent gộp bị tổng nguồn cộng lặp với các con, còn hai hàng VIB không tách loại chứng khoán; không dòng nào bị ép vào hierarchy/leaf hẹp |
| CL-001–CL-005, CL-007–CL-014 | `OPEN_SCHEMA_OR_SOURCE_HIERARCHY_GAP`; 47 mapping chắc chắn và 34 phương trình vẫn đã xác minh; các leaf/trục khấu trừ/`Trong đó` chưa tương đương được giữ nguyên nguồn |
| CL-023–CL-025 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; HDB/VCB/BID có bảng B02a ngoài báo cáo chính nhưng không có note B05a chi tiết của family trong đúng PDF đã bind |
| FI-001–FI-003 | `OPEN_SOURCE_VALUE_UNAVAILABLE`; VPB/VCB/CTG in `(*)` thay cho phần lớn giá trị hợp lý. Ký hiệu này không được đổi thành 0 hoặc thay bằng giá trị ghi sổ |
| FI-007–FI-011 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/MBB/HDB/BID/VIB không có bảng chi tiết đồng thời trình bày giá trị ghi sổ và giá trị hợp lý trong đúng PDF đã bind |
| CRISK-001/003–006/008/010–011 | `CLOSED_BY_E0105_PROJECT_OWNER_ADJUDICATION`; dấu gạch ngoại bảng = 0, VCB VND→1418, hai residual đúng 1 giữ nguyên nguồn như sai số trình bày |
| CRISK-002/007/009 | `OPEN_NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH`; 11 ô vàng không bị gộp vào tiền tệ khác |
| CRISK-012–CRISK-013 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro tiền tệ chi tiết trong đúng PDF đã bind |
| IRISK-001–IRISK-026 | `CLOSED_BY_E0105_PIXEL_GEMMA4_AND_ACCOUNTING_REPLAY`; đủ 234 mapping/279 ô và 108 phương trình; không còn OPEN |
| IRISK-027–IRISK-028 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro lãi suất chi tiết trong đúng PDF đã bind |
| LRISK-001/006–019 | `CLOSED_BY_E0105_DASH_ZERO_PIXEL_GEMMA4_AND_ACCOUNTING_REPLAY`; MBB/HDB/VCB/CTG và toàn bộ VIB đã khép |
| LRISK-002–LRISK-005 | `OPEN_MATERIAL_SOURCE_PRESENTATION_RESIDUAL`; bốn trục VPB lệch 6.000/275.500/6.001/275.499, không coi là làm tròn |
| LRISK-020–LRISK-021 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro thanh khoản chi tiết trong đúng PDF đã bind |

## Financial instruments — carrying and fair value (`FINANCIAL_INSTRUMENTS`)

- **FI-001–FI-003 — OPEN:** VPB p86, VCB p45 và CTG p51 dùng `(*)` cho các
  ô giá trị hợp lý không xác định được. Ba nhóm được giữ nguyên nguồn; không
  suy diễn 0 và không sao chép số ghi sổ.
- **FI-007–FI-011 — confirmed bound-report absences:** ACB, MBB, HDB, BID và
  VIB không có bảng chi tiết mang đồng thời hai nhánh giá trị ghi sổ/giá trị
  hợp lý. Các bảng rủi ro là matched controls thuộc family kế tiếp.

## Currency risk (`CURRENCY_RISK`)

Current exact-replay results: E-0101 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique currency-risk regions and
  confirms two bounded absences. Flexible axis/row order and page continuation
  are admitted; interest, liquidity and fair-value tables remain controls.
- E-0105 raises the verified denominator to 120 mappings/136 value cells and
  51 exact equations. Visible dashes become zero; the two VPB residuals of one
  remain unchanged and are explicitly bounded as presentation rounding.
- **CRISK-002/007/009 — OPEN:** only the three gold axes remain because the
  live schema has no gold branch. No gold value is collapsed into `OTHER`.

## Interest-rate risk (`INTEREST_RATE_RISK`)

Current exact-replay results: E-0102 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique interest-rate-risk regions
  and confirms two bounded absences. Flexible repricing axes/order, split-line
  labels, optional internal/external states and adjacent-page continuation are
  admitted; currency, liquidity and fair-value tables remain controls.
- E-0105 closes every gap: 234 mappings/279 value cells and 108 exact
  equations across all six present banks. VIB p62–63 uses pixel-bound Gemma 4
  as an independent challenger and 36 equations; neither OCR reader alone is
  numeric authority. VPB remains Q1/2026.
- **No IRISK entry remains OPEN.**

## Liquidity risk (`LIQUIDITY_RISK`)

Current exact-replay results: E-0103 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique liquidity-risk regions and
  confirms two bounded absences. Combined/split overdue axes, flexible
  maturity buckets, source-row aggregation and continuation are admitted;
  currency, interest-rate and fair-value tables remain controls.
- E-0105 raises the verified denominator to 129 mappings/153 value cells and
  51 exact `assets - liabilities = net liquidity gap` equations. VIB p68–69
  is fully closed by full-table pixels, Gemma 4 challenge and 16 equations.
- **LRISK-002–LRISK-005 — OPEN:** only four material VPB residuals remain;
  they are not silently treated as rounding.

## End-period exchange rates (`EXCHANGE_RATE`)

Current exact-replay result:
`docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json`

- One bank-blind whole-PDF graph finds five unique exchange-rate regions at
  MBB p61, VPB p90, CTG p61, BID p35 and VIB p71 and confirms three bounded
  detailed-table absences. Flexible row order, punctuation/grouping variants,
  split period axes and document-level VND policy inheritance are admitted;
  currency-risk, interest-rate-risk, liquidity-risk and policy prose remain
  controls.
- 46 mappings/92 current-comparative value cells are independently verified.
  All 122 visible source cells remain present; VietOCR is text/geometry
  evidence only and the Paddle/native source axis plus pixels controls numbers.
- **FXRATE-001–FXRATE-015 — OPEN:** retain CNY/DKK/NZD/XAU at VPB,
  NZD/NOK/DKK/HKD/CNY/KRW/LAK at CTG and DKK/HKD/NOK/XAU at VIB. These are
  valid source rows with no live TM leaf under 5935–5945; none is discarded or
  forced into another currency.

## Project-owner catch-all and monthly-average closure (`E-0100`)

Exact-replay overlay:
`docs/experiments/E-0100-owner-adjudicated-catchall-average-closure-v1.json`

- Closes **10** prior OPEN source rows without rewriting E-0089/E-0090/E-0094/
  E-0095/E-0096: CRPE-001/002 → 1228, OACT-001 → 1239, EI-001/002 →
  derived 1267/1268, SBO-001 → 1279 and CC-001–004 → 1288.
- Catch-all rows are aggregated once with any existing same-ID row; 10
  accounting equations replay exactly. ACB's monthly values retain exact
  rational numerators/denominators rather than an untracked rounded float.

## Bank-owned pledged or discounted assets (`BANK_PLEDGED_OR_DISCOUNTED_ASSETS`)

Current exact-replay result:
`docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique bank-owned asset region at VPB p67 and
  VIB p49. ACB/MBB/HDB/VCB/CTG/BID have no detailed note in the supplied
  reports; customer collateral and borrowing-facility text remain controls.
- Five mappings, 10 value cells and six component relations are independently
  verified. Two additional VPB printed-total reproductions are explicitly not
  accounting identities because the source presentation double-counts a parent
  and its “Trong đó” children.
- **BPA-001–BPA-003 — OPEN:** the VPB combined parent and two unsplit VIB
  use-purpose rows remain source-only rather than being forced into narrower
  security-class leaves.

## Customer collateral held (`CUSTOMER_COLLATERAL_HELD`)

Current exact-replay result:
`docs/experiments/E-0096-customer-collateral-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique customer-scoped region at VPB p67,
  VCB p47 and VIB p49. ACB/MBB/HDB/CTG/BID have no detailed customer-collateral
  note in the supplied reports.
- 15 mappings, 30 value cells and six child-to-parent equations are independently
  verified. VIB's separate TCTD and own-pledged-asset branches are excluded.
- **CC-001–CC-004 — CLOSED by E-0100:** project-owner adjudication aggregates
  each bank's source rows into 1288 `Khác` together with its pre-existing
  catch-all row, once only. Both VCB and VIB parent totals close exactly.

## State-budget obligations (`STATE_BUDGET_OBLIGATIONS`)

Current exact-replay result:
`docs/experiments/E-0095-state-budget-obligations-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p22, MBB p49,
  VPB p58, HDB p32, CTG p43, BID p26 and VIB p47; VCB has no detailed note in
  the supplied report.
- 33 mappings, 147 value cells and 37 roll-forward/net equations are
  independently verified. Thirteen visible dashes are retained as pixel-bound
  zeroes. VPB is explicitly Q1/2026.
- **SBO-001 — CLOSED by E-0100:** HDB `Tiền thuê đất` maps to 1279 `Các khoản
  phải nộp khác`; all five visible source cells are dashes and normalize to 0.

## Employee income (`EMPLOYEE_INCOME`)

Current exact-replay result:
`docs/experiments/E-0094-employee-income-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p26, VPB p66
  and VIB p49; MBB/HDB/VCB/CTG/BID have no detailed employee-income note in
  the supplied reports.
- 13 mappings, 26 value cells and 14 additive/ratio equations are independently
  verified. VPB is explicitly Q1/2026; VIB is the six-month period.
- **EI-001–EI-002 — CLOSED by E-0100:** the six-month source values are divided
  by exactly six and retained as rational numbers before mapping 1267/1268.

## Subsidiary acquisitions and disposals (`SUBSIDIARY_ACQUISITION_DISPOSAL`)

Current exact-replay result:
`docs/experiments/E-0093-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json`

- The shared whole-PDF graph requires total consideration, cash settlement and
  cash held by the acquired/disposed subsidiary, plus period and unit evidence.
- No supplied PDF contains that complete detail table. All eight outcomes are
  bounded absences with zero mappings and zero open source rows.
- **SAD-001–SAD-008 — confirmed bound-report absences:** HDB's HDS acquisition
  narrative and CTG's investment cash-flow captions remain explicit controls;
  they do not establish the three schema rows 1256–1258.

## Cash and cash equivalents (`CASH_EQUIVALENTS`)

Current exact-replay result:
`docs/experiments/E-0092-cash-equivalents-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p8, MBB p50,
  VPB p66, VCB p40, CTG p47 and VIB p45. It covers total-before-components,
  combined interbank, demand/term split and optional-securities layouts.
- 31 mappings, 60 value cells and 12 accounting equations are independently
  verified, covering ReportNormId 1248–1254. No source row remains open.
- **CEQ-001–CEQ-002 — confirmed bound-report absences:** HDB and BID have no
  detailed component table; their cash-flow beginning/end balances and policy
  text remain negative controls, not mappings.

## Corporate income tax expense (`INCOME_TAX`)

Current exact-replay result:
`docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique detailed reconciliation at MBB
  p50, VPB p59 and VIB p48, using profit before tax, adjustments, taxable
  income, current tax and period/unit topology rather than bank/page routing.
- 28 mappings, 56 value cells and 20 accounting equations are independently
  verified. The mapped union covers ReportNormId 5723–5737. VPB remains Q1.
- **TAX-001 — OPEN:** VIB p48 `Điều chỉnh khác`; current-period cell is blank,
  comparative value is `163`. The source meaning is broader than 5733, so it
  remains explicit and is used only in the comparative printed-total equation.
- **TAX-002–TAX-006 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no detailed tax reconciliation; statement totals, tax-obligation
  movements and deferred-tax balances are retained as negative controls.

## Other activity income, expense and net (`OTHER_ACTIVITY`)

Current exact-replay result:
`docs/experiments/E-0090-other-activity-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique numbered note at MBB p47, VPB
  p64 and VIB p46. It accepts a net-only variant or gross income/expense
  parents with optional children and labeled/unlabeled net totals, without
  using bank, filename, note number or page as a rule.
- 23 mappings, 46 value cells and 14 accounting equations are independently
  verified. VPB's two visible asset-disposal rows are summed by authenticated
  components before one mapping to 1231.
- **OACT-001 — CLOSED by E-0100:** VPB p64 values `41 / 9` are aggregated once
  into 1239 `Khác`; the income-parent and net equations remain exact.
- **OACT-002–OACT-006 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no complete numbered detail note with period/unit axes,
  components and net total. Their KQKD totals, segment reports and explanatory
  text remain negative controls.

## Credit-risk provision expense (`CREDIT_RISK_PROVISION_EXPENSE`)

Current exact-replay result:
`docs/experiments/E-0089-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique numbered detailed note at MBB
  p49, VPB p66 and VIB p47. It accepts wrapped labels, optional rows, a customer
  parent with general/specific children and an unlabeled trailing total without
  using bank, filename, note number or page as a rule.
- 15 mappings, 30 value cells and eight accounting equations are independently
  verified. Combined customer/TCTD/purchased-debt rows use existing schema
  6031/6032/6033 rather than creating duplicate concepts.
- **CRPE-001–CRPE-002 — CLOSED by E-0100:** the VPB margin/advance row
  (`- / 29.368`) and VIB trade-finance-receivable row (`- / (244)`) map to
  1228 `Dự phòng khác`; both printed family totals replay exactly.
- **CRPE-003–CRPE-007 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no complete detailed note with period/unit axes, component rows
  and trailing total in the supplied PDFs. Statement aggregates, policies and
  explanatory mentions remain negative controls and are not relabelled.

<a id="open-equity-funds-legacy-current"></a>

## Capital and funds (`CAPITAL_AND_FUNDS`)

Current exact-replay result:
`docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in all eight
  reports, including geometry-selected 90-degree VietOCR rescue for rotated
  layouts; 19 near regions remain negative controls.
- ACB/MBB/VPB/HDB/VCB/CTG have 65 verified mappings, 131 numeric components and
  20 exact accounting equations. The supplied VPB PDF remains Q1/2026.
- CAF-001–CAF-008 are exact source columns without one equivalent schema leaf.
  CAF-009–CAF-010 retain BID/VIB as structure-only until an independent rotated
  numeric challenger is available; rotated VietOCR is text evidence only.

## Other payables and liabilities (`OTHER_PAYABLES_AND_LIABILITIES`)

Current exact-replay result:
`docs/experiments/E-0077-other-payables-liabilities-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in every report
  and retains 36 near controls. It requires only the owner plus internal and
  external payable branches; employee, tax, other-payable, risk, welfare,
  interest/fee and intermediate branches remain optional.
- Exact visible-pixel/source-numeric replay verifies 39 schema mappings, 78
  current/comparative components and 28 parent/detail/total equations. Two ACB
  risk-provision dashes are pixel-bound and normalized to zero.
- E-0132A closes OPL-001–OPL-018 to 1127 `Khác` under the project-owner rule
  for source rows without a dedicated leaf. Their amounts remain inside verified
  source parents/totals, and overlapping parent/detail views stay explicitly
  non-additive. VPB remains the supplied Q1/2026 source.

<a id="open-issued-valuable-papers-legacy-current"></a>

## Issued valuable papers (`ISSUED_VALUABLE_PAPERS`)

Current exact-replay result:
`docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in each of the
  eight reports and retains 29 near controls. It covers vertical instrument/
  tenor tables, book-value versus face-value lanes, combined promissory/bond
  parents and horizontal instrument columns without bank/page routing.
- 66 mappings, 124 value components and 36 accounting equations are
  `VERIFIED_BY_CODEX`. Four CTG dash cells are bound to exact render pixels and
  normalized to zero; empty cells are not promoted to zero.
- E-0080 closes ACB exact-five-year rows through the now-inclusive 1103/1111
  boundaries, maps MBB's printed broad tenors directly to 6009/6010 without
  inventing a narrower split, and maps BID's capital-increase bond to 1117.
  IVP-005–IVP-007 remain open only because VPB prints one whole-family tenor
  view without an instrument allocation. VPB is retained as Q1/2026.

## Entrusted/investment-risk capital (`ENTRUSTED_INVESTMENT_RISK_CAPITAL`)

Current exact-replay result:
`docs/experiments/E-0075-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region at MBB p43,
  VPB p56 and VIB p42, with no second complete match. It admits an aggregate
  organization/person row, a two-line ODA source and a three-line NHNN housing
  programme without bank/page routing.
- Six mappings/12 current-comparative components are `VERIFIED_BY_CODEX`; four
  printed child-to-total equations at MBB/VPB close exactly. The two small
  source-specific rows map to explicit schema catch-all 1099 rather than being
  forced into a semantically narrower currency/international-organization leaf.
- ACB/HDB/VCB/CTG/BID are absent only within the supplied reports. There are no
  open source rows for this family. VPB remains Q1/2026.

## Government and central-bank liabilities (`GOVERNMENT_NHNN_LIABILITIES`)

Current exact-replay result:
`docs/experiments/E-0074-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in each of the
  eight reports and retains 17 near regions as negative controls. It admits an
  aggregate-only table, detailed central-bank facilities, Treasury currency or
  tenor branches, repo rows and other liabilities without bank/page routing.
- 28 source mappings, 58 visible current/comparative components and 28 exact
  accounting equations are `VERIFIED_BY_CODEX`. Two source dashes omitted from
  OCR are independently bound to render pixels and normalized to zero.
- E-0080 adds broad parent 6070 for the three central-bank-loan wording
  variants and sibling 6071 for the Treasury term deposit. BID's Finance
  Ministry deposit is reclassified from catch-all 1039 to dedicated 6072.
  No source row remains open; VPB is correctly retained as Q1/2026.

## Other assets (`OTHER_ASSETS`)

Current exact-replay result:
`docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json`

- Whole-PDF fresh-VietOCR scan finds exactly one complete region in each of
  MBB p42, VPB p51–53 and VIB p39; no document has a second complete match.
  The shared graph admits split sibling notes, an explicit multi-page umbrella
  and an integrated table with subtables without bank/page routing.
- 58 source mappings, 126 visible current/comparative components and 30 exact
  accounting equations are `VERIFIED_BY_CODEX`. Five supplied reports are
  bounded absences between their long-term-investment and government-liability
  note boundaries.
- OA-001–OA-012 retain every source row that lacks an equivalent schema or has
  a broader/narrower meaning. They remain at the top of the open queue while
  the family itself is closed at its safely mapped core.

## Investment property (`INVESTMENT_PROPERTY_MOVEMENT`)

Current exact-replay result:
`docs/experiments/E-0072-investment-property-8bank-codex-verified-mapping-v1.json`

- The shared fixed-asset engine scans all 453 pages, partitions same-page
  current/comparative regions by their explicit period ends, and finds only
  MBB p41 as one unique current detailed region. The 31/12/2025 table is retained
  as comparison evidence rather than mixed into the 30/06/2026 values.
- Nine source mappings and eleven visible roll-forward, asset-column and
  carrying-value equations are `VERIFIED_BY_CODEX`. MBB's `Giá trị hao mòn`
  wording is accepted as the accumulated-depreciation branch. The visible DASH
  in current cost increases is pixel-bound and normalized to zero.
- IP-001–IP-007 close the other seven outcomes only for these supplied PDFs.
  Balance-sheet lines, accounting policies, cash-flow rows and combined
  fixed-asset/investment-property expenses remain negative controls. No source
  row in the verified MBB region remains open.

## Intangible fixed assets (`INTANGIBLE_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0071-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json`

- One shared fixed-asset graph scans all 453 pages and finds unique current-period
  regions at MBB p39, VPB p50 and VIB p38; MBB p40 remains comparison-only.
- 32 source mappings and 12 visible roll-forward/carrying-value equations are
  `VERIFIED_BY_CODEX`. ReportNormId 6068 groups gross-cost decreases 921–927;
  new ReportNormId 6069 preserves the distinct fully-amortized-but-still-in-use
  disclosure at VPB/VIB rather than forcing it into another movement row.
- IFA-001–IFA-005 close the five no-region outcomes only for the supplied PDFs.
  IFA-006 closes the schema gap. No intangible-fixed-asset row remains open;
  VPB keeps its Q1/2026 source-period caveat.

## Customer-loan geography (`LOAN_GEOGRAPHIC_CLASSIFICATION`)

Base exact-replay result:
`docs/experiments/E-0065-loan-geography-8bank-codex-verified-mapping-v1.json`

Project-owner absence closure:
`docs/experiments/E-0067D-loan-geography-project-owner-absence-closure-v1.json`

- One bank-blind graph scans all 453 pages and combines the geographic
  concentration heading with an exact customer-loan axis before reading the
  domestic/foreign structure. It supports geography by rows or columns and
  consecutive-period continuation, while retaining broader total-loan tables
  and geographic segment reports as negative controls.
- MBB p52 and VIB p53–54 are the only exact customer-loan populations. Four
  source rows (5752/765 for each bank), six period-value cells and three
  domestic-plus-foreign equations are `VERIFIED_BY_CODEX`. VIB's two visible
  foreign dashes stay typed `DASH` before zero normalization.
- LG-001–LG-006 are closed as bound-report absences for this exact family.
  ACB/VPB/HDB/CTG/BID retain their mechanically broader total-loan geography
  equations as negative controls; VCB retains its p42 segment-report matrix.
  None is silently narrowed, promoted, or treated as absent in another filing.

<a id="family-3-rnid-575-unresolved"></a>

## Technical/pre-review provenance appendix — Family 3 (`INTERBANK_DEPOSITS_AND_LOANS`)

Phụ lục này bảo toàn nguyên văn disposition và reason của machine sweep trước
pixel review. Mọi nhãn `OPEN` bên dưới là trạng thái **pre-V4/pre-review đã bị
E-0178 supersede**; current Family 3 có 0 unresolved. Chúng không thay thế formal
V4 pair hay bảng closed-history ở đầu file.

Historical pre-V4 all-filing artifacts:
`output/calibration/family-first-accounting-evidence-sweeps-v1/interbank-deposits-and-loans.json`
and
`output/calibration/family-first-accounting-schema-mappings-v1/interbank-deposits-and-loans.json`.

The two artifacts agree trial-for-trial on source identity, provenance,
disposition and exact unresolved reasons. Their immutable references are:
evidence SHA-256
`95915e902d369e326d8b394432687009551569d97d101773106affa38470655b`;
mapping SHA-256
`7413a9e1a3ac6150b07dc4910ce47cfe465eac21c40c3c9eaff5798db1044312`.
Here `pN` is the artifact physical `page_sequence`, not the printed folio;
`doc-line` is an inclusive complete-document line range. Every unresolved
trial has at least one selected region, so no row below uses an inferred page.

Primary cause is exclusive per filing: 16
`ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`, 15
`MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`, 6
`VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`, 4
`TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM` and 1
`CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN` = 42. Machine reasons are
preserved verbatim; downstream closure failures caused by an incomplete lane
are not counted again as a second primary cause.

Diễn giải nguyên nhân chính:

- `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE`: đã thấy đúng bảng/dòng nguồn
  nhưng chưa bind đủ cột giá trị, kỳ hoặc đơn vị cho mọi role nhìn thấy.
- `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES`: có từ hai vùng
  bảng ứng viên trở lên, nhưng chưa có duy nhất một vùng vượt qua đủ
  geometry/header/accounting gates; không chọn theo bank hay page.
- `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM`: subtotal/tổng in trên PDF không
  bằng chính xác population các component đang nhìn thấy, nên không được
  sửa số hoặc backsolve để ép khép.
- `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM`: dòng kết quả phía sau không
  khớp duy nhất với một phép cộng component hợp lệ.
- `CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN`: bảng qua trang nhưng chưa
  có bằng chứng reset-fenced để kế thừa kỳ và đơn vị từ trang trước.

<!-- INTERBANK_575_UNRESOLVED_FILINGS_BEGIN -->

| ID | Trial | Bank / kỳ / scope | PDF identity | Physical page / selected region | Primary root-cause category | Exact machine reason(s) |
| --- | ---: | --- | --- | --- | --- | --- |
| IDL-575-001 | 1 | ACB / Năm 2025 / hợp nhất | `vietstock_bctc/ACB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf`<br>`sha256:2f79c3db9e362eee72fcdfca330359e9d9cbf510fd5fe6cdeb98dcf39deae35b` | candidate 1: p7, doc-line 245–260<br>candidate 2: p46, doc-line 2635–2689 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:TERM_DEPOSIT_GROUP`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS` |
| IDL-575-002 | 3 | ACB / H1 2025 / hợp nhất | `vietstock_bctc/ACB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:94cbe09e3533cc2354055253811f33df40a6c56461cfe131b12e75cea7a36366` | candidate 1: p7, doc-line 242–257<br>candidate 2: p45, doc-line 2608–2659 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-003 | 5 | ACB / Q1 2025 / hợp nhất | `vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf`<br>`sha256:5a22f62d8b2853423f71fab7d09e42f96cf8dc3eacd9032836febb5550198db7` | p15, doc-line 959–995 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-004 | 6 | ACB / Q1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/ACB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf`<br>`sha256:d8258cc1695acfcf8ebe6edfff5fdaa67dddb30dc8f47571d8a5d59b7e0dbbd3` | p15, doc-line 933–971 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-005 | 11 | ACB / Q4 2025 / hợp nhất | `vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf`<br>`sha256:ad6cab1acd7556f8ee0372764f732f2efe8746b36b5517761f68762b095b07b7` | p16, doc-line 1043–1079 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-006 | 12 | ACB / Q4 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/ACB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf`<br>`sha256:28937fe83d897bd6466b2bb9e5831dbeda0f68cf81982c6ac1b15c6dec899f71` | p16, doc-line 1001–1039 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-007 | 17 | MBB / Q1 2025 / hợp nhất | `vietstock_bctc/MBB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf`<br>`sha256:09421ed8d0d7a6dd3eece828b64be46d053aff70b4870bb27afc405b0e27cd33` | p29, doc-line 1748–1785 | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSIT_GROUP` |
| IDL-575-008 | 18 | MBB / Q1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/MBB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf`<br>`sha256:c4aea54c740ce5c2b825b69752ef4779cd5cb05ab261f1b4399ddc633738903e` | p26, doc-line 1572–1601 | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0` |
| IDL-575-009 | 25 | VPB / Năm 2025 / hợp nhất | `vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf`<br>`sha256:f3298c72cbe58af1eefd8223d235843138761a45648cd7e60c5153ad21776ea0` | p42, doc-line 2397–2469 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-010 | 26 | VPB / Năm 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VPB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf`<br>`sha256:af79940cbde9bd50850fe0dfc4cf8ba78a8d0f4b5340e6f0cc0368a12cfbc788` | p36, doc-line 2059–2124 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-011 | 27 | VPB / H1 2025 / hợp nhất | `vietstock_bctc/VPB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:c9f27ab6b1d69611209dee51e5bd9dc91dd74f491abf4f25a01821964266eecf` | p44, doc-line 2395–2461 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-012 | 28 | VPB / H1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VPB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:a1e74b14a1d601e7bec8e18795bca623ce66b184f12dc6031a45e20558e3cf27` | p36, doc-line 2051–2116 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-013 | 37 | HDB / Năm 2025 / hợp nhất | `vietstock_bctc/HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf`<br>`sha256:dad39b45a99747f7290d0a478af2f71f018f4adc59a590e158cdea16dd090ac3` | p34, doc-line 2101–2149 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-014 | 38 | HDB / Năm 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/HDB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf`<br>`sha256:082e0fe75550085df0b73351afd3f3561ba1b716bbbf0157bcf1e11f34b78ae8` | p33, doc-line 2016–2064 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-015 | 39 | HDB / H1 2025 / hợp nhất | `vietstock_bctc/HDB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:fe89f3c5a0886370cbbc506364d784963d3fda8c44ad03f31e10313e9f02e11f` | p31, doc-line 1991–2052 | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0` |
| IDL-575-016 | 40 | HDB / H1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/HDB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:474bb77c099bdc0865a5aeaf16be18351b612325f717a9a39bc83f07aaf12cd9` | p30, doc-line 1910–1967 | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0` |
| IDL-575-017 | 41 | HDB / Q1 2025 / hợp nhất | `vietstock_bctc/HDB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf`<br>`sha256:5d163e501bea8f8b962c246ae9a811c756574a2d0efc83895609f5a415e5a28b` | p3, doc-line 41–51 | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP` |
| IDL-575-018 | 42 | HDB / Q1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/HDB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf`<br>`sha256:e4423025c872b514804c50d7d6882290cff6abe5e418a2b577dfd4fd565ac10a` | p3, doc-line 40–50 | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP` |
| IDL-575-019 | 43 | HDB / Q2 2025 / hợp nhất | `vietstock_bctc/HDB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf`<br>`sha256:58b2c92247a2c49312861b182ffdfab8cb813ccde8cc9231289a07a03a6c9f9c` | p3, doc-line 37–47 | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP` |
| IDL-575-020 | 44 | HDB / Q2 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/HDB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf`<br>`sha256:ef08f65eb1dc9f07dafdeec05372d9d8d267593549cff4b9acd7577fb415ac4f` | p3, doc-line 37–47 | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP` |
| IDL-575-021 | 45 | HDB / Q3 2025 / hợp nhất | `vietstock_bctc/HDB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf`<br>`sha256:88d7f95685de6c070fba76966b5a7f861aaec0eb9e5874aac0529b39b8d8355a` | p3, doc-line 38–48 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-022 | 46 | HDB / Q3 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/HDB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf`<br>`sha256:d9187258556cee67b17748e17c5721ca6721ac362b1364bb0ae406b45f8b749a` | p3, doc-line 38–48 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-023 | 62 | CTG / Năm 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/CTG/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf`<br>`sha256:87f852400bf25421aa80000436387f25c5382bfd0d72a4d67122493361b486e6` | p39–40, doc-line 2436–2484 | `CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN` | `COLUMN_CONTEXT:CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN` |
| IDL-575-024 | 64 | CTG / H1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/CTG/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:79714aee142d29b8673880e128cca1d9911ee93dadcd8b552bbbee6e9c8f08ac` | candidate 1: p11, doc-line 437–462<br>candidate 2: p21, doc-line 1344–1422 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_2:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-025 | 65 | CTG / Q1 2025 / hợp nhất | `vietstock_bctc/CTG/2025/BCTC Hợp nhất quý 1 năm 2025.pdf`<br>`sha256:244171fc77a8ab7e8685b90a74ea8a52f00f3ad622864b591affcea21f953065` | p4, doc-line 90–102 | `VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_LOAN_GROUP` |
| IDL-575-026 | 75 | BID / H1 2025 / hợp nhất | `vietstock_bctc/BID/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:1e12da259d3cd63629cf01d546135363a289f20bff85fcd6a1db2f0af3371b71` | p9, doc-line 334–349 | `TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM` | `HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0` |
| IDL-575-027 | 86 | VIB / Năm 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf`<br>`sha256:61e5cc0bbc8da93fa8aaa540afd8125c1517f45c801b0e450fc6efd1f6a53d20` | candidate 1: p9, doc-line 287–320<br>candidate 2: p37, doc-line 1965–2026 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-028 | 87 | VIB / H1 2025 / hợp nhất | `vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:aee7fe9d825852e656c0912513e9720bec872f009ce93013256380c949a1e424` | candidate 1: p9, doc-line 285–321<br>candidate 2: p37, doc-line 2018–2049 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-029 | 88 | VIB / H1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`<br>`sha256:1e56fffdff551caf6dec5b13c57e4817f54e84c5d0c51f818978d17f28173105` | candidate 1: p10, doc-line 277–310<br>candidate 2: p38, doc-line 1967–1997 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-030 | 89 | VIB / Q1 2025 / hợp nhất | `vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét quý 1 năm 2025.pdf`<br>`sha256:5b2b6a8d135a6dac734a8cc08cf8125be99776002f61287dcf1f2786d147e52d` | candidate 1: p9, doc-line 279–313<br>candidate 2: p37, doc-line 1989–2037 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:COLUMN_CONTEXT:DECLARED_UNIT_KIND_AXIS_LENGTH_DIFFERS_FROM_BODY_COLUMNS`<br>`CANDIDATE_1:COLUMN_CONTEXT:PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN`<br>`CANDIDATE_1:COLUMN_CONTEXT:UNIT_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-031 | 90 | VIB / Q1 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét quý 1 năm 2025.pdf`<br>`sha256:f58da65f95cc1979f35feb0ea93fa11c3d034ccdaf24bbbeb95a4141bc857568` | candidate 1: p10, doc-line 278–312<br>candidate 2: p37, doc-line 1946–1994 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-032 | 92 | VIB / Q2 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf`<br>`sha256:21d618c30b343908190c56066b2db54c7de1a886cf7556023b3b2f6d50012ed9` | candidate 1: p5, doc-line 129–161<br>candidate 2: p32, doc-line 1815–1845 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-033 | 93 | VIB / Q3 2025 / hợp nhất | `vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét 9 tháng đầu năm 2025.pdf`<br>`sha256:7ff7c257c012eba17ed732065a1df4bc6024f9bec50270fe1c7abc96a861e3cd` | candidate 1: p8, doc-line 270–306<br>candidate 2: p36, doc-line 2016–2049 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-034 | 94 | VIB / Q3 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét 9 tháng đầu năm 2025.pdf`<br>`sha256:b4abb04963bf0a4ce560ea65853e3aad6c9a26818f66ceb3d3f105af60774884` | candidate 1: p9, doc-line 290–326<br>candidate 2: p37, doc-line 1984–2014 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-035 | 95 | VIB / Q4 2025 / hợp nhất | `vietstock_bctc/VIB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf`<br>`sha256:e6276e8e43f3aa22c70ebb082fd212845dcde23e217b1c72f8116690c03bf008` | candidate 1: p5, doc-line 136–168<br>candidate 2: p33, doc-line 1844–1876 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-036 | 96 | VIB / Q4 2025 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf`<br>`sha256:5f8510194f53e98172092b8d4cb0ca1b237791d772035e58c2b61eecb42fac8f` | candidate 1: p5, doc-line 133–165<br>candidate 2: p32, doc-line 1780–1812 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-037 | 99 | ACB / Q1 2026 / hợp nhất | `vietstock_bctc/ACB/2026/20260422 - ACB - BCTC Hop nhat Quy 1 nam 2026.pdf`<br>`sha256:a85402445a34e80dd4248471c2d23d4cf4b349ab2455b91db457f3e6effbdd4a` | p16, doc-line 1021–1056 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-038 | 100 | ACB / Q1 2026 / công ty mẹ/riêng lẻ | `vietstock_bctc/ACB/2026/20260422 - ACB - BCTC Rieng le Quy 1 nam 2026.pdf`<br>`sha256:0b1c3d36212d77072fb53640073b2c6b888609d4e1f0369f92e10d53d8067c6c` | p16, doc-line 1001–1038 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-039 | 101 | ACB / Q2 2026 / hợp nhất | `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`<br>`sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86` | p16, doc-line 1030–1065 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-040 | 102 | ACB / Q2 2026 / công ty mẹ/riêng lẻ | `vietstock_bctc/ACB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`<br>`sha256:4bb54ef4451ecee9aa4e55b68e076dea2a4a2b9783d0d6165f7161bcc40438f7` | p16, doc-line 1013–1050 | `ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE` | `VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-041 | 139 | VIB / Q2 2026 / hợp nhất | `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`<br>`sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c` | candidate 1: p5, doc-line 135–163<br>candidate 2: p32, doc-line 1774–1806 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE` |
| IDL-575-042 | 140 | VIB / Q2 2026 / công ty mẹ/riêng lẻ | `vietstock_bctc/VIB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`<br>`sha256:98bd6458eb223b168acf4795703f6ae628dcec166ef0ef07d402fb86636a86ef` | candidate 1: p5, doc-line 132–160<br>candidate 2: p32, doc-line 1714–1747 | `MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES` | `CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_1:COLUMN_CONTEXT:BODY_DERIVED_COLUMN_AXIS_UNRESOLVED`<br>`CANDIDATE_1:COLUMN_CONTEXT:LOCAL_HEADER_REGION_UNRESOLVED`<br>`CANDIDATE_1:HIERARCHICAL_CLOSURE:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE`<br>`CANDIDATE_2:HIERARCHICAL_CLOSURE:TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS:0` |

<!-- INTERBANK_575_UNRESOLVED_FILINGS_END -->


- **HISTORICAL OPEN — ACB (10 filing):** annual-2025 consolidated p7/p46 and H1-2025
  consolidated p7/p45 contain both a summary and detailed region headed
  `Tiền gửi và cho vay các TCTD khác`; neither candidate has a fully bound
  column/body axis. Q1/Q4-2025 and Q1/Q2-2026, both scopes, p15–16 retain the
  same owner but one or more visible role rows lack a complete two-lane axis.
- **HISTORICAL OPEN — MBB (2 filing):** Q1-2025 consolidated p29 and parent p26,
  `Tiền gửi và cho vay các TCTD khác`; the printed deposit/family result differs
  from the exact component population currently bound. Source values are not
  repaired to force closure.
- **HISTORICAL OPEN — VPB (4 filing):** annual-2025 and H1-2025, both scopes, p42/p36 and
  p44/p36, owner `Tiền gửi và cấp tín dụng cho các TCTD khác`; one or more role
  rows lack a complete visible lane axis.
- **HISTORICAL OPEN — HDB (10 filing):** annual-2025 both scopes p34/p33 and Q3-2025 both
  scopes p3 have incomplete visible role lanes; H1-2025 p31/p30 has a trailing
  result that is not one exact family-component sum; Q1/Q2-2025, both scopes,
  p3 has a printed `Cho vay các TCTD khác` result that does not equal the
  visible component population. The owner is `Tiền gửi tại và cho vay các
  TCTD khác`.
- **HISTORICAL OPEN — CTG (3 filing):** annual-2025 parent p39 lacks proven cross-page
  period/unit inheritance; H1-2025 parent p11/p21 has two competing regions;
  Q1-2025 consolidated p4 has an interbank-loan result that does not equal the
  visible component population. Source owner: `Tiền gửi và cho vay các TCTD
  khác`.
- **HISTORICAL OPEN — BID (1 filing):** H1-2025 consolidated p9, `Tiền gửi và cho vay các
  TCTD khác`; the trailing result is not one exact sum of the bound family
  components.
- **HISTORICAL OPEN — VIB (12 filing):** annual-2025 parent, H1-2025 both scopes,
  Q1-2025 both scopes, Q2-2025 parent, Q3/Q4-2025 both scopes and Q2-2026 both
  scopes contain both summary and detailed regions headed `Tiền gửi và cho vay
  các TCTD khác`. Pages are respectively p9/p37, p9–10/p37–38, p9–10/p37,
  p5/p32, p8–9/p36–37, p5/p32–33 and p5/p32. Header/body geometry or complete
  role lanes do not yet choose one region uniquely; no bank/page routing is
  used to break the tie.
- **PRE-REVIEW MACHINE COUNTS:** 84/140 filing and 701 source mappings are
  `VERIFIED_BY_CODEX`; 14 filing are `NOT_OBSERVED_PROPOSAL_ONLY` (BID 12,
  CTG 2); machine sweep đã gắn 42 filing là `UNRESOLVED` trước pixel review.
  E-0178 supersede toàn bộ disposition hiện hành thành 126 verified / 14 bounded
  not-observed / 0 unresolved, nhưng không sửa artifact hay nhãn lịch sử ở đây.

## Deposits at central banks (`CENTRAL_BANK_DEPOSITS`)

Current exact-replay result:
`docs/experiments/E-0061-central-bank-deposits-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and binds the first family owner,
  central-bank parent, required currency children and first trailing two-period
  total. It records horizontal row/period layout and stops before reserve-ratio
  tables or the next TM family.
- MBB p30, VPB p38 and VIB p31 are the only unique complete detailed clusters.
  Ten source rows are `VERIFIED_BY_CODEX`, and four current-period equations
  close exactly. VPB retains its Q1/2026 source-period caveat.
- MBB's Laos and Cambodia rows are aggregated into ReportNormId 574 `Tiền gửi
  khác`: `934.855 + 1.213.504 = 2.148.359`; together with Vietnam deposits,
  `25.269.011 + 2.148.359 = 27.417.370`. The project owner
  confirmed that ACB/HDB/VCB/CTG/BID do not contain this TM family in the bound
  PDFs, based on each report's first TM family boundary; balance-sheet totals
  do not contradict that bounded note-level absence.

## Cash and precious metals (`CASH_PRECIOUS_METALS`)

Current exact-replay result:
`docs/experiments/E-0060-cash-precious-metals-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and requires a short owner, VND and
  foreign-currency cash children, visible period/unit axes and a trailing total.
  It finds exactly one complete region for MBB p30, VPB p38 and VIB p31.
- 12 source rows are `VERIFIED_BY_CODEX`: ReportNormId 562, 563, 565 and the
  exact family total 561 for each complete region. Three current-period
  `VND + foreign + monetary gold = total` equations close exactly.
- The project owner confirmed ACB/HDB/VCB/CTG/BID do not contain this TM family
  in the bound PDFs: ACB's notes start at the interbank family, while the other
  four start at trading securities. Balance-sheet totals and cash-flow/risk
  disclosures remain negative controls rather than manufactured note mappings.
- VPB retains its Q1/2026 source-period caveat.

## Trading securities (`TRADING_SECURITIES`)

> Historical fixed-eight checkpoint only.  It does not replace the current
> 140-filing denominator.  The authoritative current queue is the per-PDF
> `OPEN — family-first 140-filing` section at the top of this file and matches
> section 4 plus the summary row in `COMPLETED_TM_FAMILIES.md`.

Current exact-replay result:
`docs/experiments/E-0059-trading-securities-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages. It finds one unique trading region
  for ACB, MBB, VPB, HDB, VCB, CTG and BID, while rejecting accounting-policy
  prose, provision roll-forwards and investment securities as sibling families.
- 58 source rows are `VERIFIED_BY_CODEX`; 20 parent/child and
  gross/provision/net equations close exactly. First/last cluster items, PDF row
  order, period/unit columns and parent-total placement remain explicit.
- MBB uses the listed/unlisted branch. The other six mapped banks use the issuer
  branch. Unlabeled gross rows are admitted only when topology and the full
  accounting equation both agree.
- VIB p36 AFS was deliberately excluded here and is now resolved by E-0067 as
  the investment-securities family. VPB retains its Q1/2026 source-period caveat.

## Investment securities (`INVESTMENT_SECURITIES`)

Base exact-replay result:
`docs/experiments/E-0067-investment-securities-8bank-codex-verified-mapping-v1.json`

Project-owner closure:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- One bank-blind graph scans all 453 pages and finds exactly one complete
  investment region per PDF. It supports explicit or implicit family owners,
  AFS/HTM branches, provision and quality alternate views, VAMC, two-page
  continuation and first/last/next-family boundaries.
- ACB p19, MBB p35–36, VPB p47–48, HDB p29, VCB p32, CTG p40, BID p23 and
  VIB p36 now provide 99 verified source mappings/198 period cells; 39 visible
  parent-child or gross-provision-net equations close exactly.
- IS-001 is closed by the explicit document-level `Triệu VND` statement on BID
  p13 of the same PDF. IS-002 is closed by retaining both VIB source components
  and proving `5.894.320 + 32.879.230 = 38.773.550` and
  `12.104.102 + 28.252.422 = 40.356.524` before mapping one aggregate to 808.

## Other long-term investments (`OTHER_LONG_TERM_INVESTMENTS`)

Current exact-replay result:
`docs/experiments/E-0068-long-term-investments-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and finds exactly one complete
  region in each PDF: ACB p19, MBB p36, VPB p48, HDB p30, VCB p33, CTG p40,
  BID p24 and VIB p36. Optional joint-venture, associate, other-investment,
  organization/project and fund branches may be absent or reordered.
- All 29 reviewed source mappings and 58 period cells are
  `VERIFIED_BY_CODEX`; nine visible accounting equations close exactly. The
  HDB current associate DASH remains typed before zero normalization. VPB
  remains explicitly Q1/2026.
- Schema gaps for joint ventures and associates are closed by ReportNormId
  6066 and 6067 under parent 862. No source row from the bounded eight regions
  remains in the open queue; detailed organization rows are retained as
  corroboration and are not double-counted with their mapped parent.

## Tangible fixed assets (`TANGIBLE_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0069-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json`

- One bank-blind owner/cost/accumulated-depreciation/carrying-value graph scans
  all 453 pages and finds unique detailed regions at MBB p37, VPB p49 and VIB
  p37. MBB p38 is retained only as the prior-period continuation control.
- All 35 reviewed mappings and 12 visible roll-forward/carrying-value equations
  are `VERIFIED_BY_CODEX`. VIB's rotated page uses fresh same-model VietOCR for
  text and an independently sealed rotated PP-OCRv6 numeric challenger; four
  disagreements from the original rotated source OCR are resolved by pixels and
  exact accounting closure rather than semantic guessing.
- ACB/HDB/VCB/CTG/BID are confirmed absent only in the bound reports. Main
  statement balances and accounting-policy prose remain negative controls.
  There is no open mapping item for this family. VPB remains Q1/2026.

## Leased fixed assets (`LEASED_FIXED_ASSETS_ROLLFORWARD`)

Annual-2025 exact-replay result:
`docs/experiments/E-0124-annual-2025-leased-fixed-assets-8bank-bound-report-absence-v1.json`

- The reporting-period-general graph scans all eight audited consolidated
  annual-2025 PDFs, including split owner/branch lines and the complete rotated
  VietOCR rescue denominator. It finds zero complete and zero near 896–912
  regions. The automatically selected tangible→intangible boundaries are ACB
  p55→56, MBB p58→60, VPB p53→54, HDB p41→42, VCB p48→49, CTG p48→49, BID
  p47→48 and VIB p42→43.
- Thirty finance-lease company, policy, lending and income lines remain exact
  negative controls. No source row is OPEN and no mapping is manufactured.
  The family-local schema projection is insensitive to unrelated global schema
  insertions; live ReportNormId/name/parent compatibility is still required.

Current exact-replay result:
`docs/experiments/E-0070-leased-fixed-assets-8bank-bound-report-absence-v1.json`

- The shared fixed-asset graph scans all 453 pages and finds no complete or
  near-complete 896–912 region in ACB, MBB, VPB, HDB, VCB, CTG, BID or VIB.
- All eight dispositions are `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; this is
  bounded to the supplied PDFs and is not a broader bank/document absence
  claim.
- Twenty-four finance-lease company, policy, lending and income lines remain
  negative controls. No source row is open and no mapping is manufactured.

## Project-owner TM adjudications

Exact-replay decision artifact:
`docs/experiments/E-0067A-project-owner-tm-adjudications-v1.json`

- CBD-001/CBD-002 close into one ReportNormId 574 aggregate with exact source
  components and arithmetic retained.
- IDL-001/IDL-002 and DFI-001 close as bounded-report absences; the confirmation
  does not assert absence in another filing or bank.
- VIB p36 is explicitly confirmed under 804 → 805, with the live 804 children
  805/829/853/859 and last descendant 861; it is not trading 592.

## Loan-quality margin normalization

Exact-replay normalized result:
`docs/experiments/E-0067B-loan-quality-margin-separation-project-owner-v1.json`

- The already registered template identity 1944 is reused instead of allocating
  another duplicate-name ID. In this bounded context it is a direct child of
  family 746 and represents `Cho vay giao dịch ký quỹ và ứng trước tiền bán
  chứng khoán` independently from the five quality grades.
- ACB p18 and VPB p42 expose the row after the five-grade core, so ReportNormId
  747 remains unchanged and the visible row maps to 1944.
- MBB p31 exposes the same population as 5746 `Trong đó` under 747. The source
  disclosure is retained as a non-output bridge; normalized 747 is reduced by
  exactly 5746 on both axes and the same amount is emitted once as 1944.
- All 18 per-axis family/split equations close; no 5746+1944 double count is
  permitted. This closes the two former outside-core ACB/VPB populations.

## Customer-deposit and investment owner closure

Exact-replay result:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- CD-001/CD-002: the two-state-member-or-more labels at VPB p55 and VIB p42
  map to the owner-confirmed schema 770 name `Công ty TNHH MTV (hoặc trên MTV)
  vốn nhà nước trên 50%`; values `64.165` and `174` remain separately bound.
- IS-001: BID p23 inherits `Triệu VND` only from the visible document-level
  declaration at p13 of that same PDF. Fourteen mappings, 28 cells and ten
  accounting equations are independently replayed; the visible comparative
  dash remains typed before zero normalization.
- IS-002: VIB p36 retains the bond and certificate-of-deposit components and
  maps their per-period sums once to 808. No component is dropped or emitted a
  second time.

## Customer deposit (`CUSTOMER_DEPOSIT_CLASSIFICATION`)

Base exact-replay result:
`docs/experiments/E-0058-customer-deposit-8bank-codex-verified-mapping-v1.json`

Project-owner closure:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- Một graph bank-blind quét đủ 453 trang và tìm đúng một vùng hoàn chỉnh trong
  mỗi PDF. Biên đầu/cuối, thứ tự hàng nguồn, bố cục ngang/dọc, kỳ và trục tiền tệ
  đều được giữ lại.
- 120 dòng được xác minh; 43 phương trình cha = con, tổng cột và tổng
  bảng đóng chính xác. Cột tổng và cột phần trăm chỉ là đối chứng khi không phải
  một khoản mục độc lập.
- VIB p42 dòng `Công ty Nhà nước`: VietOCR Transformer đọc thiếu chữ số đầu
  (`3.034.518`), còn pixel PDF và numeric challenger PP-OCRv6 cùng cho
  `13.034.518`; kết quả dùng `13.034.518` và lưu nguyên disagreement.
- CD-001/CD-002 đã đóng: hai dòng VPB/VIB cùng map vào schema 770 theo quyết
  định của chủ dự án, giữ nguyên giá trị nguồn `64.165` và `174`. Không còn
  dòng nguồn chưa map trong family; VPB vẫn giữ đúng kỳ nguồn Q1/2026.

## Provision movement (`PROVISION_MOVEMENT_ROLLFORWARD`)

Annual-2025 exact-replay result:
`docs/experiments/E-0119-annual-2025-provision-movement-8bank-codex-verified-mapping-v1.json`

- ACB p51, MBB p53, VPB p48, HDB p38, VCB p41, CTG p44, BID p43 và VIB p39:
  `VERIFIED_BY_CODEX` cho đúng roll-forward 2025 của BCTC hợp nhất kiểm toán.
- 18 lane cha, 79 movement rows, 18 phương trình và chín DASH→0 đều đã đóng;
  không còn dòng OPEN trong family annual-2025.
- ACB/VPB map riêng margin/ứng trước 6061–6065. Cột tổng, địa lý và deferred-LC
  chỉ làm đối chứng, không xuất cộng trùng.

Kết quả kỳ hiện hành trước đó vẫn giữ riêng tại:
`docs/experiments/E-0057-provision-movement-8bank-codex-verified-mapping-v1.json`

- ACB p18, MBB p34, HDB p28, VCB p31, CTG p39, BID p23 và VIB p34:
  `VERIFIED_BY_CODEX` cho kỳ hiện tại Q2/2026.
- VPB p45: `VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT` cho kỳ
  01/01–31/03/2026. Ba lane chung/cụ thể/margin-ứng trước và toàn bộ movement
  hiện hữu đều đã map; chỉ nguồn Q2/2026 còn thiếu.
- MBB chỉ dùng cột `Tổng cộng`; các cột Việt Nam/nước ngoài là đối chứng.
  Kỳ so sánh của mọi bank không được dùng làm mapping authority.

## OCR and numeric evidence policy

- Vietnamese semantic anchors come from the fresh VietOCR Transformer cache;
  accentless normalization and bounded edit-distance matching only locate a
  candidate graph.  They never decide the mapping by themselves.
- PP-OCRv6 is an authenticated geometry/provider and may contribute an
  independent numeric proposal.  It is **not**, by itself, final numeric truth.
- Gemma is permitted only as a bounded rescue/challenger on a fixed difficult
  crop.  A Gemma answer cannot silently replace a digit, sign, decimal separator,
  DASH, blank, or missing cell and cannot become automatic numeric authority.
- An accepted number must remain bound to the exact crop and typed lane, survive
  independent digit/sign/DASH review, and satisfy the applicable row/total/
  roll-forward accounting equations.  Disagreement without decisive pixel and
  accounting evidence remains `UNRESOLVED`.

## Loan type (`LOAN_TYPE_CLASSIFICATION`)

Historical pre-adjudication result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v1.json`

Current exact-replay result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v2.json`

Result ID:
`lt8bcv2:result:f5765671514ac40550fe349633b2d95b693537d65e18e91101434904d3d652dd`

### LT-001 — ACB — government-directed lending

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 17 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cho vay theo chỉ định của Chính phủ`
- Visible source values: `-` / `-`; raw source status remains `DASH`.
- Project-owner decision: append an exact schema child for the visible label and
  normalize each independently reviewed visible DASH to numeric `0` for the
  template without erasing the raw DASH provenance.
- Accepted schema: ReportNormId `6057` (`Cho vay theo chỉ định của Chính phủ`),
  parent `717`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LT-002 — VPB — other credit

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 42 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cấp tín dụng khác`
- Visible values: `72.360.147 | 6,95% | 73.847.196 | 7,82%`
- Accepted schema: ReportNormId `726` (`Cho vay khác`).
- Project-owner decision: within this exact `Cho vay khách hàng` type-analysis
  graph, `Cấp tín dụng khác` is the source variant of `Cho vay khác`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

## Loan industry (`LOAN_INDUSTRY_CLASSIFICATION`)

Source scan: `lifdsv1:scan:a0b560c0ff0fb07fff7e49e4c9b38c2b3f9baa8aefb9d911f37d01a920b54a11`

Historical pre-adjudication result ID:
`li8bcv1:result:a7435794e8639f9aa53ada040d13abddf966b91ab839a9aa1391bf2cdba52c58`

Current exact-replay result:
`docs/experiments/E-0055-loan-industry-8bank-codex-verified-mapping-v2.json`

Current result ID:
`li8bcv2:result:3ac4ba987593baf8e0a03c3a1f2414dacf1008df38fc890519d72d2c9160cbdb`

Exact-replay builder:
`scripts/experiments/build_loan_industry_8bank_codex_verified_mapping_v1.py`

### LI-001 — ACB — industry family not present in bound report

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 33 physical pages, fresh VietOCR line axis
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Machine scan: no region survives the full-PDF parent/child-pair search plus
  period/unit/total/accounting checks; trying a smaller one-child graph does not
  manufacture an occurrence.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; this is not a claim about
  other ACB reports or the broader corpus.

### LI-002 — MBB — transport and storage

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải, Kho bãi`
- Visible values: `34.348.471 | 2,80% | 29.961.714 | 2,76%`
- Accepted schema: ReportNormId `736` (`Vận tải kho bãi và thông tin liên lạc`).
- Project-owner decision: `Vận tải, Kho bãi` is an admitted source variant of
  the combined schema concept; the separately visible information/communication
  row remains mapped to its own ReportNormId `740`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-003 — MBB — foreign branch population

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Visible values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Accepted schema: new ReportNormId `6058`, exact visible-label child under
  ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-004 — VPB — transport and storage

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải kho bãi`
- Visible values: `12.790.970 | 1,23% | 12.417.698 | 1,32%`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-005 — VPB — public administration/defence/social security

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Hoạt động của Đảng cộng sản, tổ chức chính trị-xã hội, quản lý Nhà nước, an ninh quốc phòng, bảo đảm xã hội bắt buộc`
- Visible values: `5.892 | 0,00% | 14.165 | 0,00%`
- Accepted schema: ReportNormId `745` (`Các ngành nghề khác`).
- Project-owner decision: this immaterial row is grouped into the explicit
  catch-all; it is not mapped to ReportNormId `744`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-006 — VPB — personal housing loan population

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở`
- Visible values: `139.410.297 | 13,39% | 130.375.600 | 13,81%`
- Accepted schema: new ReportNormId `6059`, exact visible-label child under
  ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-007 — HDB — transport and storage

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 27 / `Phân tích dư nợ cho vay theo ngành nghề đăng ký kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `26.889.305 | 25.142.909`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-008 — VCB — industry family not present in bound report

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 55 physical pages, fresh VietOCR line axis (including terminal
  geometry-only pages without inherited transcript)
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry; the visible loan analysis on page 31 is by maturity, not industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; no broader-corpus absence
  claim is made.

### LI-009 — CTG — industry family not present in bound report

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 61 physical pages, fresh VietOCR line axis
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry; the visible loan analysis on page 39 is by original loan tenor, not
  industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; no broader-corpus absence
  claim is made.

### LI-010 — BID — broad services

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 22 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Dịch vụ`
- Visible values: `534.960.928 | 444.190.319`
- Accepted schema: new ReportNormId `6060` (`Dịch vụ`), exact visible-label
  child under ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-011 — VIB — transport and storage

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ theo ngành nghề kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `11.771.262 | 2,96% | 12.478.803 | 3,27%`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

## Loan enterprise/customer type (`LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION`)

Fresh full-document scan:
`lefdsv1:scan:a8d2c5c3b49051773ca518a793a407ace5d9d9e2397675398f20f703143958d6`

Current exact-replay result:
`docs/experiments/E-0056-loan-enterprise-8bank-codex-verified-mapping-v1.json`

Result ID:
`le8bcv1:result:b6b858689f966259c4b2c8b4ea91bcc7c6bec906ce3cd060df9ebcb3eb5f27a9`

The enterprise/legal-form matcher found one unique complete region in MBB p32,
VPB p43, HDB p26, and VIB p34.  The other four PDFs do not expose that legal-form
branch, but each contains a distinct headerless **loan-type** region directly
under `Cho vay khách hàng`; those regions are already found and verified by the
owner-direct E-0054 graph.  They are not forced into the wrong schema parent
766.  In E-0056, 44 source rows are `VERIFIED_BY_CODEX`, including the exact
foreign-branch population concept 6058; no schema-semantic row remains
unresolved.  Six non-additive source group/total equations remain explicit.

### LE-001 — ACB — headerless owner-direct loan-type region

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 17, directly below `4. CHO VAY KHÁCH HÀNG:`.
- No branch title `Phân tích theo loại hình cho vay` is required.  The generic
  owner-direct graph binds the two period axes, unit scope, seven visible child
  roles and the closing total.
- Verified children include ReportNormIds `718`, `722`, `719`, `723`, `725`,
  `721`, and `724`; government-directed lending is separately mapped to `6057`.
- Resolving result: E-0054 V2
  `lt8bcv2:result:f5765671514ac40550fe349633b2d95b693537d65e18e91101434904d3d652dd`.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-002 — MBB — source-only “Cho vay các TCKT” group parent

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 32 / enterprise or customer-type analysis
- Pixel text / accentless: `Cho vay các TCKT` / `cho vay cac tckt`
- Visible values: `721.497.618 | 58,79% | 621.056.253 | 57,28%`
- Candidate schema: no new leaf is needed.  The visible legal-form descendants
  remain the higher-resolution representation.
- Review status: `RESOLVED_SOURCE_ONLY_GRAPH_NODE_RETAINED_FOR_CHECK`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_WOULD_DOUBLE_COUNT_LEGAL_FORM_CHILDREN`
- Reason: its visible legal-form descendants already partition and sum to this
  parent. Mapping both parent and descendants would double count.
- Resolution: retained as a source-only graph parent; its two-axis parent-child
  equation is replayed and closed in the E-0056 result.

### LE-003 — MBB — source-only “Cho vay cá nhân” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay cá nhân` / `cho vay ca nhan`
- Visible values: `478.995.719 | 39,01% | 437.686.958 | 40,38%`
- Accepted schema equivalence: ReportNormId `780` (`Hộ kinh doanh, cá nhân`).
- Review status: `RESOLVED_NON_ADDITIVE_SCHEMA_EQUIVALENCE`
- Resolution: `Cho vay cá nhân` and its immediately following 780 child have
  identical four-lane values.  E-0056 records the parent→780 equivalence but
  exports the numeric amount once only; parent and child must never be summed.

### LE-004 — MBB — source-only “Cho vay khác” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay khác` / `cho vay khac`
- Visible values: `937.382 | 0,08% | 904.945 | 0,09%`
- Accepted aggregate equivalence: ReportNormId `782` (`Khác`).
- Review status: `RESOLVED_NON_ADDITIVE_SCHEMA_EQUIVALENCE`
- Resolution: the source parent is explicitly associated with 782 as the
  aggregate/catch-all view, while its two visible children remain available as
  the detailed view.  E-0056 marks the relation non-additive, so an export must
  choose the aggregate or its descendants and cannot count both.

### LE-005 — MBB — foreign-branch population and its two children

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel parent: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Parent values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Pixel children: `Cho vay Doanh nghiệp` = `2.121.916 / 2.176.885`;
  `Cho vay cá nhân` = `7.173.788 / 7.153.744`
- Accepted schema: ReportNormId `6058`, whose canonical label is already exactly
  `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`.
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Resolution: the project reuses the existing exact concept rather than creating
  a duplicate ID merely because MBB repeats it in another source presentation.
  E-0056 maps the row once, preserves its two source children and parent-child
  equation, and marks the group relation non-additive.

### LE-006 — VPB — “Khác” monetary cells not attached by semantic geometry

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 43 / enterprise or customer-type analysis
- Pixel text / accentless: `Khác` / `khac`
- Raw VietOCR values: `2 | 0,00 | 2 | 0,00`
- Graph values: `missing | 0,00 | missing | 0,00`
- Candidate schema: ReportNormId `782`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `VISIBLE_MONETARY_CELLS_OUTSIDE_CURRENT_ROW_GEOMETRY_BAND`
- Reason: pixels clearly show both monetary values, but the current generic row
  association did not bind them. No zero/missing imputation is allowed.
- Resolution: exact visible monetary cells `2 / 2` are pixel-bound, close the
  accounting graph, and map to ReportNormId `782` (`Khác`).

### LE-007 — HDB — “Doanh nghiệp tư nhân” dash/current and 27/comparative

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 26 / enterprise or customer-type analysis
- Pixel text / accentless: `Doanh nghiệp tư nhân` / `doanh nghiep tu nhan`
- Pixel values: `- | 27` (`DASH`, not zero or missing)
- Fresh semantic graph values: `missing | 27`
- Candidate schema: ReportNormId `774`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `DASH_PIXEL_NOT_PRESENT_IN_FRESH_SEMANTIC_LINE_AXIS`
- Reason: the row identity is structurally clear, but the numeric verifier must
  preserve a typed dash rather than treating the absent OCR token as zero.
- Resolution: the raw value remains typed `DASH`, while its explicit normalized
  numeric interpretation is `0`; the comparative `27` is preserved. The row maps
  to ReportNormId `774`.

### LE-008 — VCB — headerless owner-direct loan-type region

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 30, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `722`, `719`, `723`, and `721` without
  requiring a printed branch title.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-009 — CTG — headerless owner-direct loan-type region

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 38, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `722`, `719`, `723`, `725`, `721`, and
  `726`; the visible DASH in `Cho vay khác` remains typed DASH with numeric
  interpretation zero.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-010 — BID — headerless owner-direct loan-type region

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 22, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `721`, `722`, `719`, and `723` plus the
  exact two-axis total.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-011 — VIB — VietOCR dropped one digit in “Công ty cổ phần khác”

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 34 / enterprise or customer-type analysis
- Label / accentless: `Công ty cổ phần khác` / `cong ty co phan khac`
- Raw VietOCR current value: `97.043.85`
- Independent PP-OCRv6 proposal: `97.043.851` with recognition score
  `0.9999531507492065`; this is corroborating numeric evidence, not sole truth.
- Independent pixel transcription: `97.043.851`
- Other visible lanes: `24,44% | 77.496.641 | 20,29%`
- Candidate schema: ReportNormId `773`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `FRESH_VIETOCR_DIGIT_OMISSION_BREAKS_CURRENT_PERIOD_ACCOUNTING_CLOSURE`
- Reason: the pixel value closes the printed total `397.083.447`; the raw OCR
  value does not. The correction must come from independent pixel-bound numeric
  verification, never silent string repair.
- Resolution: the exact crop-bound pixel value `97.043.851` is retained alongside
  the raw Transformer proposal and maps to ReportNormId `773`; total closure is exact.

## E-0066 / E-0120 — bounded whole-PDF controls for `Hoạt động mua nợ`

E-0120 repeats the complete-PDF scan on the eight audited consolidated
annual-2025 filings. It maps MBB p54, VPB p49, HDB p39 and VIB p40 with 15
schema rows, 30 cells and 19 exact equations. HDB's legitimate source variant
has no separate interest row, so 5739 is not fabricated. Five visible dashes
remain typed before zero normalization. These four entries are not open
mappings: the family is absent only inside each fixed supplied-PDF scope.

### PD-001 — ACB — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no region contains the owner `Hoạt động mua nợ`, the
  balance rows, the principal/interest detail and the next-family boundary.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-002 — VCB — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-003 — CTG — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-004 — BID — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

Resolving result: E-0066
`e0066:result:79e15086c88ca9283d450955da737a620012679f36071e39dce9a63962c76a3b`.

Annual-2025 resolving result: E-0120
`annual2025pd8bcv1:result:6c91fc19548f1ff71df439cf2d027d65e797aeb2c8f2a51b4776a732610909d2`.

## E-0157 — annual-2025 `Rủi ro thanh khoản`

- Review status: `RESOLVED_VERIFIED_BY_CODEX_NO_ANNUAL_OPEN_ROWS`.
- All eight audited consolidated annual-2025 PDFs contain one unique liquidity
  table. E-0157 verifies 181 mappings/181 cells and 54 exact equations; nine
  visible dashes are pixel-authenticated before normalization to zero.
- No annual-2025 source row remains in this ledger. The historical Q1/2026 VPB
  residuals LRISK-002–LRISK-005 remain attached only to that older filing and
  are not silently rewritten by the annual result.
- Result:
  `annual2025lrr8bcv1:result:671984613ccb960a8f1c491fc6b828c6b1b1e3544c7da5283be7c2fb34731b27`.

## E-0158 — annual-2025 `Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo`

- Review status: `OPEN_SCHEMA_GAPS_SOURCE_VALUES_VERIFIED`.
- MBB p103, VPB p98, HDB p69, CTG p85, BID p70 và VIB p77 là sáu vùng
  unique; ACB/VCB là hai bounded detailed-table absences. E-0158 xác minh
  55 mapping/110 ô schema trên tổng 74 hàng/148 ô nguồn.
- Xung đột duy nhất HDB/NZD comparative giữ cả VietOCR `14.382` và trục
  nguồn `14.362`; Gemma 4 crop-bound đọc `14.362`. Đây là challenger độc
  lập, không phải numeric truth và không tạo quy tắc sửa số tổng quát.
- Result:
  `annual2025fxrate8bcv1:result:add0abc2a953baa5115e0cbc881c654c681dea5e537350e4b3adbee4aca76c23`.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| AFXRATE-001 | VPB | 98 | CNY | Chưa có leaf CNY dưới schema 5935–5945. |
| AFXRATE-002 | VPB | 98 | DKK | Chưa có leaf DKK dưới schema 5935–5945. |
| AFXRATE-003 | VPB | 98 | NZD | Chưa có leaf NZD dưới schema 5935–5945. |
| AFXRATE-004 | VPB | 98 | XAU | Chưa có leaf vàng/XAU dưới schema 5935–5945. |
| AFXRATE-005 | HDB | 69 | CNY | Chưa có leaf CNY dưới schema 5935–5945. |
| AFXRATE-006 | HDB | 69 | HKD | Chưa có leaf HKD dưới schema 5935–5945. |
| AFXRATE-007 | HDB | 69 | KRW | Chưa có leaf KRW dưới schema 5935–5945. |
| AFXRATE-008 | HDB | 69 | NZD | Chưa có leaf NZD dưới schema 5935–5945. |
| AFXRATE-009 | CTG | 85 | NZD | Chưa có leaf NZD dưới schema 5935–5945. |
| AFXRATE-010 | CTG | 85 | NOK | Chưa có leaf NOK dưới schema 5935–5945. |
| AFXRATE-011 | CTG | 85 | DKK | Chưa có leaf DKK dưới schema 5935–5945. |
| AFXRATE-012 | CTG | 85 | HKD | Chưa có leaf HKD dưới schema 5935–5945. |
| AFXRATE-013 | CTG | 85 | CNY | Chưa có leaf CNY dưới schema 5935–5945. |
| AFXRATE-014 | CTG | 85 | KRW | Chưa có leaf KRW dưới schema 5935–5945. |
| AFXRATE-015 | CTG | 85 | LAK | Chưa có leaf LAK dưới schema 5935–5945. |
| AFXRATE-016 | VIB | 77 | DKK | Chưa có leaf DKK dưới schema 5935–5945. |
| AFXRATE-017 | VIB | 77 | HKD | Chưa có leaf HKD dưới schema 5935–5945. |
| AFXRATE-018 | VIB | 77 | NOK | Chưa có leaf NOK dưới schema 5935–5945. |
| AFXRATE-019 | VIB | 77 | XAU | Chưa có leaf vàng/XAU dưới schema 5935–5945. |

## E-0159 — annual-2025 `Tiền, vàng gửi và vay các TCTD khác` — nguồn vốn

- Review status: `OPEN_TWO_SOURCE_ONLY_AUXILIARY_ROWS`.
- ACB p61, MBB p64, VPB p58–59, HDB p44, VCB p52, CTG p51, BID p50 và
  VIB p45 là tám vùng unique. E-0159 xác minh 95 mapping/190 ô schema và
  40 phương trình dưới đúng root nguồn vốn 1040; family tài sản 575 là đối
  chứng âm và không được dùng chung mapping authority.
- Hai xung đột OCR số HDB đã được giải quyết bằng pixel, trục số nguồn và
  closure kế toán; chúng không phải dòng OPEN. Gemma 4 chỉ đọc lại hai crop
  làm challenger, không thay thế numeric authority.
- Result:
  `annual2025if8bcv1:result:0678d0d0bc4feaf02d5f6fbb72d6c744b29d8086f0449578931c3af698053395`.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| AIFUND-001 | VPB | 59 | Vốn vay từ Công ty Tài chính Quốc tế (IFC) | Chi tiết source-only, không cộng thêm vào subtotal vay và chưa có leaf chính xác dưới 1040–1052. |
| AIFUND-002 | HDB | 44 | Phải trả về nghiệp vụ UPAS LC | Parent trung gian chưa có leaf chính xác; hai dòng VND/ngoại tệ của nó đã được cộng đúng một lần vào aggregate vay 1049/1052, không map thêm parent. |

## E-0160 — annual-2025 `Kinh doanh và đầu tư chứng khoán` — khu vực địa lý

- Review status: `RESOLVED_VERIFIED_BY_CODEX_NO_ANNUAL_OPEN_ROWS`.
- ACB p77, MBB p91, VPB p81, HDB p60, BID p63 và VIB p59–60 có đúng một
  vùng hoàn chỉnh; 12 mapping/18 ô và 15 phương trình được xác minh. Năm dấu
  `-` có bbox pixel riêng trước khi chuẩn hóa về 0.
- VCB và CTG không có vùng thuyết minh hoàn chỉnh trong hai PDF đã bind. Các
  trang báo cáo bộ phận gần giống được giữ làm đối chứng âm, không map.
- Không còn dòng nguồn annual-2025 nào của family 5759–5761 trong ledger.
- Result:
  `annual2025sg8bcv1:result:5d80cb90d755c6b8ed1267a1fd640d1d2f959f62910eda3268e669633d7ae965`.

## E-0161 — annual-2025 `Báo cáo bộ phận hợp nhất`

- Review status: `OPEN_SOURCE_VARIANTS_WITH_SUPPORTED_SUBSET_VERIFIED`.
- Whole-PDF scan tìm đúng một vùng báo cáo bộ phận trong cả tám BCTC. Phần
  schema hỗ trợ đã được xác minh qua 73 binding cấu trúc, 208 mapping số và
  43 phương trình; VPB không có nhánh địa lý chi tiết, HDB/VIB không có nhánh
  lĩnh vực kinh doanh chi tiết.
- Hai ô VIB `Tài sản cố định — Miền Trung` là ô trống thật, không phải dấu
  `-` và không được đổi thành 0. Những trục nguồn rộng/hẹp khác schema được giữ
  source-only thay vì ép vào một leaf gần tên.
- Root 5750 `Giao dịch với các bên liên quan` có trạng thái
  `SKIPPED_BY_USER`. Nó không thuộc queue unresolved, không được scan/map và
  không được diễn giải thành bounded absence.
- Result:
  `annual2025csr8bcv1:result:8395c0524c6b1345910d057fc8bca97aba732231d7379e7c7d0eccb645f79707`.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| ASEG-001 | ACB | 95 | Cho thuê tài chính | Schema business segment 5807–5842 chưa có trục này. |
| ASEG-002 | ACB | 95 | Chứng khoán / Quản lý quỹ | Hai trục nguồn cần phép cộng được kiểm soát trước khi đưa vào trục gộp của schema. |
| ASEG-003 | ACB | 95 | Kết quả kinh doanh bộ phận | Nhãn nguồn không xác lập rõ đây là lợi nhuận trước thuế. |
| ASEG-004 | MBB | 87 | Nước ngoài | Không đồng nhất ngữ nghĩa với trục `Khu vực khác`. |
| ASEG-005 | MBB | 83 | Thu nhập / Chi phí nội bộ | DIRECT_PIXEL_REVIEW_2026-08-24: p83/trang in 79 đọc rõ bảng, cột loại trừ và các hàng nội bộ; RESOLVABLE_PENDING_GENERIC_FIX cho binding hàng đối trừ. |
| ASEG-006 | VPB | 96 | Hoạt động công ty tài chính | Schema business segment chưa có trục riêng. |
| ASEG-007 | VPB | 96 | Hoạt động chứng khoán | Hẹp hơn trục gộp `Chứng khoán và quản lý quỹ` trong schema. |
| ASEG-008 | HDB | 61 | Nước ngoài | Không đồng nhất ngữ nghĩa với trục `Khu vực khác`. |
| ASEG-009 | HDB | 61 | Kết quả kinh doanh bộ phận | Nhãn nguồn không xác lập rõ đây là lợi nhuận trước thuế. |
| ASEG-010 | VCB | 71 | Miền Trung và Tây Nguyên | Rộng hơn trục `Miền Trung`; không được tự thu hẹp. |
| ASEG-011 | VCB | 71 | Nước ngoài | Schema địa lý hiện chưa có trục tương ứng. |
| ASEG-012 | VCB | 72 | Dịch vụ tài chính phi ngân hàng / Chứng khoán / Khác | Các trục nguồn không đồng nhất với các trục business hiện có. |
| ASEG-013 | CTG | 82 | Dịch vụ tài chính phi ngân hàng / Khác | Các trục nguồn không đồng nhất với các trục business hiện có. |
| ASEG-014 | CTG | 82 | Bảng bộ phận kinh doanh xoay | DIRECT_PIXEL_REVIEW_2026-08-24: p82/trang in 80 đọc rõ toàn bảng và các số; RESOLVABLE_PENDING_GENERIC_FIX cho promote/bind đủ hàng bằng primitive generic. |
| ASEG-015 | BID | 37 | Cho thuê tài chính / Chứng khoán / Khác | Các trục nguồn không đồng nhất với các trục business hiện có. |
| ASEG-016 | BID | 38 | Trong nước / Nước ngoài | Không tương đương với ba trục Bắc/Trung/Nam của schema. |
| ASEG-017 | VIB | 61 | Tài sản cố định — Miền Trung | Ô nguồn nhìn thấy là trống, không phải dấu `-` hay số 0. |

## Family 28 current corpus — interest income (`INTEREST_INCOME`)

Current OFFICIAL exact-replay result:
`/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family28-interest-income/sweep.json`

- Census: 140 documents, `READY=136`, `NOT_OBSERVED=0`, `UNRESOLVED=4`,
  882 mappings and 310 exact source/derived equations. Every unresolved trial
  has `mappings=[]`.
- `F28-II-001` — BID ordinal 26, physical page 44, H1/2025: source
  `SECURITIES_INTEREST=4.973.626`, while visible components
  `126.852 + 4.846.773 = 4.973.625`. Machine reasons are
  `DECLARED_SOURCE_RESULT_COMPONENT_EQUATION_MISMATCH:SECURITIES_INTEREST`
  and `REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN`. Status:
  `NEEDS_ACCOUNTING_RECONCILIATION`; a fixed minimal observation prompt may
  reread the bounded cells, but code must not backsolve the missing unit.
- `F28-II-002` — MBB ordinal 78, physical page 46, H1/2025: comparative
  direct children sum to `33.113.197`, while the visible family subtotal is
  `33.213.197`. Machine reason is
  `REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN`. The malformed expense
  sibling `(8.656:569)` lies outside the exact family-root subtree and is not
  the cause. Status: `NEEDS_ACCOUNTING_RECONCILIATION`; reread only the bounded
  income cells/subtotal, never the equation-derived answer.
- `F28-II-003` — VPB ordinal 139, physical page 61, H1/2026 parent report; and
  `F28-II-004` — VPB ordinal 140, physical page 71, H1/2026 consolidated
  report: direct row `Thu nhập lãi tiền gửi và cho vay TCTD khác` participates
  in the exact family total but has no schema leaf with identical scope.
  Splitting it into deposit/customer-loan leaves or assigning it to the broader
  customer-plus-other-CI RNID 6075 would invent an allocation. Machine reason
  is `UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW`; status for both is
  `NEEDS_SCHEMA_DECISION`.

These four records remain source-authoritative negative gates. A later generic
repair/schema result may resolve them, but must retain this history and cite
its independent replay ID and commit.

## Family 29 current corpus — interest expense (`INTEREST_EXPENSE`)

Current OFFICIAL exact-replay result:
`/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family29-interest-expense/sweep.json`

- Census: 140 documents, `READY=140`, `NOT_OBSERVED=0`, `UNRESOLVED=0`,
  701 mappings and 140 exact source-root equations. Family29 adds no unresolved
  mapping entry.
- MBB ordinal 78 raw source cell `(8.656:569)` is retained verbatim. Its typed
  projection `-8.656.569` is accepted only because the complete direct expense
  frontier closes the visible comparative subtotal exactly; the mapping state
  records conditional equation provenance. This is representation
  normalization, not an equation-derived replacement or a provider retry.
- The release keeps exact role inventories: deposit interest 140, borrowing
  interest 135, issued-paper interest 140, finance-lease interest 6, other
  credit expense 140 and source-visible family root 140. Missing optional roles
  are absence, not unresolved rows.

The colon-separator and two-sided-subtotal adversarial fixtures remain
source-authoritative regression gates. A colon-bearing value without exact
equation closure, or a declared family role on both sides of one root carrier,
must return `UNRESOLVED` with `mappings=[]`.

## Append policy

Every later family appends entries here when a source row or complete region is
not safely mapped.  Resolved entries remain as history after an independently
replayed mapping supersedes them; the resolving result ID and commit are added
to the entry.  The following cases must be retained explicitly rather than
silently dropped:

- a visible source row with no exact schema concept;
- a plausible schema candidate whose scope is narrower, broader, or otherwise
  different from the source row;
- a VietOCR/pixel disagreement that can affect identity or numeric closure;
- a source-only parent, subtotal, optional branch, or continuation that is
  needed for graph/accounting closure but is not itself mapped;
- multiple structurally plausible regions in the same PDF;
- a whole-PDF scan with no complete region under the current contract.

For each future entry, use status `OPEN`, `NEEDS_PIXEL_REVIEW`,
`NEEDS_SCHEMA_DECISION`, `NEEDS_ACCOUNTING_RECONCILIATION`, or `RESOLVED`, in
addition to the exact machine reason.  `RESOLVED` entries remain in the file as
an audit trail and include the independent verification result ID and commit.
