# Unresolved mapping and adjudication review ledger

Updated: 2026-08-14 (UTC)

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

Ledger total: **24 entries**.  Current open queue: **5** loan-enterprise/customer-
type entries.  Closed history: **16** row/graph resolutions and **3** confirmed
bound-report family absences.  Later families append here rather than creating disconnected
candidate lists. Bank/report/page fields below are evidence locators only, never
matching rules.

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
| LT-001–LT-002 | `RESOLVED_VERIFIED_BY_CODEX` |
| LI-001, LI-008, LI-009 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT` |
| LI-002–LI-007, LI-010–LI-011 | `RESOLVED_VERIFIED_BY_CODEX` |
| LE-001, LE-005, LE-008–LE-010 | `OPEN` / `UNRESOLVED` |
| LE-002–LE-004, LE-006–LE-007, LE-011 | `RESOLVED` by source-graph or pixel replay |

## Loan type (`LOAN_TYPE_CLASSIFICATION`)

Historical pre-adjudication result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v1.json`

Current exact-replay result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v2.json`

Result ID:
`lt8bcv2:result:509d9e7caa0b47a025072aee65b4d574b1c3bf78e697068ce9f92119f43caf9a`

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
`li8bcv2:result:94571f22af35070a47e43cd6d0a86e97e3eb8b5c7ee1270330256ac0f3562a1b`

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
`le8bcv1:result:e7543dbf436af23ce15a7229a2296671bd935b2be063350d7ce67bc01b3b9cf2`

The generic matcher found one unique complete region in MBB p32, VPB p43,
HDB p26, and VIB p34. It found no complete region in the other four PDFs. The
four positive regions are now independently pixel/schema/accounting replayed:
43 schema rows are `VERIFIED_BY_CODEX`; one source population branch remains
`UNRESOLVED`; six source-only group/total equations are verified without being
misrepresented as schema children.

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
- Review status: `RESOLVED_SOURCE_ONLY_GRAPH_NODE_NOT_MAPPED`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_WOULD_DOUBLE_COUNT_LEGAL_FORM_CHILDREN`
- Reason: its visible legal-form descendants already partition and sum to this
  parent. Mapping both parent and descendants would double count.
- Resolution: retained as a source-only graph parent; its two-axis parent-child
  equation is replayed and closed in the E-0056 result.

### LE-003 — MBB — source-only “Cho vay cá nhân” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay cá nhân` / `cho vay ca nhan`
- Visible values: `478.995.719 | 39,01% | 437.686.958 | 40,38%`
- Nearest schema candidate: ReportNormId `780` (`Hộ kinh doanh, cá nhân`)
- Review status: `RESOLVED_SOURCE_ONLY_GRAPH_NODE_NOT_MAPPED`
- Machine reason: `SOURCE_GROUP_PARENT_COEXTENSIVE_WITH_VISIBLE_CHILD_NOT_MAPPED_TWICE`
- Reason: the immediately following child has the same values and is the exact
  schema label. The parent remains graph-only unless schema policy explicitly
  prefers it over the child.
- Resolution: the exact child is mapped; the coextensive parent remains graph-only,
  preventing double counting.

### LE-004 — MBB — source-only “Cho vay khác” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay khác` / `cho vay khac`
- Visible values: `937.382 | 0,08% | 904.945 | 0,09%`
- Candidate schema: none for the grouped parent
- Review status: `RESOLVED_SOURCE_ONLY_GRAPH_NODE_NOT_MAPPED`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_SPLIT_INTO_ADMIN_PUBLIC_AND_OTHER_CHILDREN`
- Reason: its two visible children close exactly to the parent and have distinct
  schema concepts; the parent must not be mapped as another child.
- Resolution: both children are mapped independently; the source parent is kept
  only as a replayed accounting node.

### LE-005 — MBB — foreign-branch population and its two children

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel parent: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Parent values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Pixel children: `Cho vay Doanh nghiệp` = `2.121.916 / 2.176.885`;
  `Cho vay cá nhân` = `7.173.788 / 7.153.744`
- Candidate schema: none as a child of ReportNormId `766`; ReportNormId `6058`
  belongs to the distinct industry family under parent `727` and is not reused here.
- Review status: `UNRESOLVED`
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
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `FRESH_VIETOCR_DIGIT_OMISSION_BREAKS_CURRENT_PERIOD_ACCOUNTING_CLOSURE`
- Reason: the pixel value closes the printed total `397.083.447`; the raw OCR
  value does not. The correction must come from independent pixel-bound numeric
  verification, never silent string repair.
- Resolution: the exact crop-bound pixel value `97.043.851` is retained alongside
  the raw Transformer proposal and maps to ReportNormId `773`; total closure is exact.

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
