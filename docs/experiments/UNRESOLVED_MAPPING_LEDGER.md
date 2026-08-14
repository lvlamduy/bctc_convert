# Unresolved mapping review ledger

Updated: 2026-08-14 (UTC)

This is the cumulative human-readable queue requested for source items and
family regions that could not yet be mapped safely.  `NO_COMPLETE_REGION` means
only that the current exact full-document fresh-VietOCR structure scan did not
find a complete region; it is **not** a claim that the family is absent from the
PDF.  A candidate ReportNormId is a comparison target, not an accepted mapping.

Current queue: **13 entries** — 2 loan-type source rows, 8 loan-industry source
rows, and 3 loan-industry reports with no complete region under the current
contract. Later families append here rather than creating disconnected candidate
lists. Bank/report/page fields below are evidence locators only, never matching
rules.

## Loan type (`LOAN_TYPE_CLASSIFICATION`)

Source result: `docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v1.json`

### LT-001 — ACB — government-directed lending

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 17 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cho vay theo chỉ định của Chính phủ`
- Visible values: `-` / `-` (DASH, not zero)
- Candidate schema: ReportNormId `720`
- Status: `UNRESOLVED_SOURCE_LABEL_NOT_EQUIVALENT_TO_SCHEMA_FUNDED_SOURCE`
- Reason: the source describes government direction; schema 720 describes loans
  funded from Government or international-organization capital.  Direction and
  funding source are not interchangeable.

### LT-002 — VPB — other credit

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 42 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cấp tín dụng khác`
- Visible values: `72.360.147 | 6,95% | 73.847.196 | 7,82%`
- Candidate schema: ReportNormId `726` (`Cho vay khác`)
- Status: `UNRESOLVED_BROADER_CREDIT_SCOPE_NOT_EQUIVALENT_TO_OTHER_LOANS`
- Reason: “credit granted” is broader than loans; topology and arithmetic do not
  justify narrowing it to “other loans”.

## Loan industry (`LOAN_INDUSTRY_CLASSIFICATION`)

Source scan: `lifdsv1:scan:372cf97156d69a2c99177236a44bf1d7fa0592687a711f0ea1ba23bfc4c78a62`

Live verified-result ID:
`li8bcv1:result:a7435794e8639f9aa53ada040d13abddf966b91ab839a9aa1391bf2cdba52c58`

Exact-replay builder:
`scripts/experiments/build_loan_industry_8bank_codex_verified_mapping_v1.py`

### LI-001 — ACB — no complete industry region

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 33 physical pages, fresh VietOCR line axis
- Status: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Reason: no region jointly satisfied customer-loan owner + industry branch + at
  least five typed industry rows + two-period/unit axes + total topology.
- Whole-document family absence claimed: **no**

### LI-002 — MBB — transport and storage

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải, Kho bãi`
- Visible values: `34.348.471 | 2,80% | 29.961.714 | 2,76%`
- Candidate schema: ReportNormId `736` (`Vận tải kho bãi và thông tin liên lạc`)
- Status: `UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW`
- Reason: the source exposes transport/storage and information/communication as
  separate rows; schema 736 combines them.  Mapping either source row alone
  would change scope.

### LI-003 — MBB — foreign branch population

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Visible values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Candidate schema: none
- Status: `UNRESOLVED_GEOGRAPHIC_BRANCH_POPULATION_NOT_ONE_INDUSTRY_SCHEMA_CHILD`
- Reason: this is a geographic/entity population, not one industry category.

### LI-004 — VPB — transport and storage

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải kho bãi`
- Visible values: `12.790.970 | 1,23% | 12.417.698 | 1,32%`
- Candidate schema: ReportNormId `736`
- Status: `UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW`
- Reason: same aggregation mismatch as LI-002.

### LI-005 — VPB — public administration/defence/social security

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Hoạt động của Đảng cộng sản, tổ chức chính trị-xã hội, quản lý Nhà nước, an ninh quốc phòng, bảo đảm xã hội bắt buộc`
- Visible values: `5.892 | 0,00% | 14.165 | 0,00%`
- Candidate schema: ReportNormId `744` (`Hoạt động tổ chức cơ quan quốc tế`)
- Status: `UNRESOLVED_PUBLIC_ADMINISTRATION_NOT_EQUIVALENT_TO_INTERNATIONAL_ORGANIZATIONS`
- Reason: domestic public administration/defence is not international organizations.

### LI-006 — VPB — personal housing loan population

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở`
- Visible values: `139.410.297 | 13,39% | 130.375.600 | 13,81%`
- Candidate schema: none under ReportNormId `727`
- Status: `UNRESOLVED_NO_EXACT_INDUSTRY_CHILD_FOR_PERSONAL_HOUSING_LOAN_POPULATION`
- Reason: this is a lending-purpose population; the current industry schema has
  no exact child for it.

### LI-007 — HDB — transport and storage

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 27 / `Phân tích dư nợ cho vay theo ngành nghề đăng ký kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `26.889.305 | 25.142.909`
- Candidate schema: ReportNormId `736`
- Status: `UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW`
- Reason: same aggregation mismatch as LI-002.

### LI-008 — VCB — no complete industry region

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 55 physical pages, fresh VietOCR line axis (including terminal
  geometry-only pages without inherited transcript)
- Status: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Whole-document family absence claimed: **no**

### LI-009 — CTG — no complete industry region

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 61 physical pages, fresh VietOCR line axis
- Status: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Whole-document family absence claimed: **no**

### LI-010 — BID — broad services

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 22 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Dịch vụ`
- Visible values: `534.960.928 | 444.190.319`
- Candidate schema: ReportNormId `739` (`Dịch vụ cá nhân và cộng đồng`)
- Status: `UNRESOLVED_BROAD_SERVICES_NOT_EQUIVALENT_TO_PERSONAL_AND_COMMUNITY_SERVICES`
- Reason: the visible category is broader than the candidate schema child.

### LI-011 — VIB — transport and storage

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ theo ngành nghề kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `11.771.262 | 2,96% | 12.478.803 | 3,27%`
- Candidate schema: ReportNormId `736`
- Status: `UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW`
- Reason: same aggregation mismatch as LI-002.

## Append policy

Every later family appends entries here when a source row or complete region is
not safely mapped.  Entries are removed only after an independently replayed
mapping supersedes them; the resolving result ID and commit must then be added
to the entry first.
