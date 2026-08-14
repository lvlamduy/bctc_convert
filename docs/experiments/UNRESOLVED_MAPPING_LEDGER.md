# Unresolved mapping review ledger

Updated: 2026-08-14 (UTC)

This is the cumulative human-readable queue requested for source items and
family regions that could not yet be mapped safely.  `NO_COMPLETE_REGION` means
only that the current exact full-document fresh-VietOCR structure scan did not
find a complete region; it is **not** a claim that the family is absent from the
PDF.  A candidate ReportNormId is a comparison target, not an accepted mapping.

This is the single cross-family review file.  Every new unresolved entry records,
when applicable: family, bank, report and reporting period, exact PDF/page/region
locator, raw VietOCR Transformer text, accentless normalized text, independent
pixel transcription when they disagree, visible values and axes, nearest schema
candidate, accounting/structure checks that passed or failed, the unresolved
reason, and the next evidence needed.  Bank/report/page fields are evidence
locators only and are never parser or mapping conditions.

Current queue: **24 entries** — 2 loan-type entries, 11 loan-industry entries,
and 11 loan-enterprise/customer-type entries. Later families append here rather
than creating disconnected candidate lists. Bank/report/page fields below are
evidence locators only, never matching rules.

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

## Loan enterprise/customer type (`LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION`)

Fresh full-document scan:
`lefdsv1:scan:17a22fbc9dae25a31863395f4760fdfe0341a5a1eec9dc570696e93365963bb4`

The generic matcher found one unique complete region in MBB p32, VPB p43,
HDB p26, and VIB p34. It found no complete region in the other four PDFs. The
four positive regions are structural proposals only; pixel/schema/numeric
verification is still downstream.

### LE-001 — ACB — no complete enterprise/customer-type region

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 33 physical pages, fresh VietOCR line axis
- Review status: `OPEN`
- Machine reason: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Whole-document family absence claimed: **no**

### LE-002 — MBB — source-only “Cho vay các TCKT” group parent

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 32 / enterprise or customer-type analysis
- Pixel text / accentless: `Cho vay các TCKT` / `cho vay cac tckt`
- Visible values: `721.497.618 | 58,79% | 621.056.253 | 57,28%`
- Candidate schema: none as a child of ReportNormId `766`
- Review status: `NEEDS_SCHEMA_DECISION`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_WOULD_DOUBLE_COUNT_LEGAL_FORM_CHILDREN`
- Reason: its visible legal-form descendants already partition and sum to this
  parent. Mapping both parent and descendants would double count.

### LE-003 — MBB — source-only “Cho vay cá nhân” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay cá nhân` / `cho vay ca nhan`
- Visible values: `478.995.719 | 39,01% | 437.686.958 | 40,38%`
- Nearest schema candidate: ReportNormId `780` (`Hộ kinh doanh, cá nhân`)
- Review status: `NEEDS_SCHEMA_DECISION`
- Machine reason: `SOURCE_GROUP_PARENT_COEXTENSIVE_WITH_VISIBLE_CHILD_NOT_MAPPED_TWICE`
- Reason: the immediately following child has the same values and is the exact
  schema label. The parent remains graph-only unless schema policy explicitly
  prefers it over the child.

### LE-004 — MBB — source-only “Cho vay khác” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay khác` / `cho vay khac`
- Visible values: `937.382 | 0,08% | 904.945 | 0,09%`
- Candidate schema: none for the grouped parent
- Review status: `NEEDS_SCHEMA_DECISION`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_SPLIT_INTO_ADMIN_PUBLIC_AND_OTHER_CHILDREN`
- Reason: its two visible children close exactly to the parent and have distinct
  schema concepts; the parent must not be mapped as another child.

### LE-005 — MBB — foreign-branch population and its two children

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel parent: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Parent values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Pixel children: `Cho vay Doanh nghiệp` = `2.121.916 / 2.176.885`;
  `Cho vay cá nhân` = `7.173.788 / 7.153.744`
- Candidate schema: none as a child of ReportNormId `766`
- Review status: `NEEDS_SCHEMA_DECISION`
- Machine reason: `GEOGRAPHIC_POPULATION_BRANCH_NOT_ONE_ENTERPRISE_LEGAL_FORM_CHILD`
- Reason: this is a geographic reporting population with its own enterprise and
  individual split, not a legal-form row. It is retained to close the core
  subtotal but is not mapped.

### LE-006 — VPB — “Khác” monetary cells not attached by semantic geometry

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 43 / enterprise or customer-type analysis
- Pixel text / accentless: `Khác` / `khac`
- Raw VietOCR values: `2 | 0,00 | 2 | 0,00`
- Graph values: `missing | 0,00 | missing | 0,00`
- Candidate schema: ReportNormId `782`
- Review status: `NEEDS_ACCOUNTING_RECONCILIATION`
- Machine reason: `VISIBLE_MONETARY_CELLS_OUTSIDE_CURRENT_ROW_GEOMETRY_BAND`
- Reason: pixels clearly show both monetary values, but the current generic row
  association did not bind them. No zero/missing imputation is allowed.

### LE-007 — HDB — “Doanh nghiệp tư nhân” dash/current and 27/comparative

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 26 / enterprise or customer-type analysis
- Pixel text / accentless: `Doanh nghiệp tư nhân` / `doanh nghiep tu nhan`
- Pixel values: `- | 27` (`DASH`, not zero or missing)
- Fresh semantic graph values: `missing | 27`
- Candidate schema: ReportNormId `774`
- Review status: `NEEDS_PIXEL_REVIEW`
- Machine reason: `DASH_PIXEL_NOT_PRESENT_IN_FRESH_SEMANTIC_LINE_AXIS`
- Reason: the row identity is structurally clear, but the numeric verifier must
  preserve a typed dash rather than treating the absent OCR token as zero.

### LE-008 — VCB — no complete enterprise/customer-type region

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 55 physical pages, fresh VietOCR line axis including the five
  terminal geometry-only pages
- Review status: `OPEN`
- Machine reason: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Whole-document family absence claimed: **no**

### LE-009 — CTG — no complete enterprise/customer-type region

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 61 physical pages, fresh VietOCR line axis
- Review status: `OPEN`
- Machine reason: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Whole-document family absence claimed: **no**

### LE-010 — BID — no complete enterprise/customer-type region

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 37 physical pages, fresh VietOCR line axis
- Review status: `OPEN`
- Machine reason: `NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN`
- Whole-document family absence claimed: **no**

### LE-011 — VIB — VietOCR dropped one digit in “Công ty cổ phần khác”

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 34 / enterprise or customer-type analysis
- Label / accentless: `Công ty cổ phần khác` / `cong ty co phan khac`
- Raw VietOCR current value: `97.043.85`
- Independent pixel transcription: `97.043.851`
- Other visible lanes: `24,44% | 77.496.641 | 20,29%`
- Candidate schema: ReportNormId `773`
- Review status: `NEEDS_PIXEL_REVIEW`
- Machine reason: `FRESH_VIETOCR_DIGIT_OMISSION_BREAKS_CURRENT_PERIOD_ACCOUNTING_CLOSURE`
- Reason: the pixel value closes the printed total `397.083.447`; the raw OCR
  value does not. The correction must come from independent pixel-bound numeric
  verification, never silent string repair.

## Append policy

Every later family appends entries here when a source row or complete region is
not safely mapped.  Entries are removed only after an independently replayed
mapping supersedes them; the resolving result ID and commit must then be added
to the entry first.  The following cases must be retained explicitly rather than
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
