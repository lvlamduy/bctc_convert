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

Ledger total: **35 entries**.  Current open queue: **11**.  Closed history:
**21** row/graph resolutions and **3** confirmed bound-report family absences.
Later families append here rather than creating disconnected candidate lists.
Bank/report/page fields below are evidence locators only, never matching rules.

## Open review queue (always first)

| ID | Family | Bank | Trang | Khoản mục nguồn | Lý do còn mở |
| --- | --- | --- | ---: | --- | --- |
| CBD-001 | Tiền gửi tại NHNN | MBB | 30 | Tiền gửi tại Ngân hàng Nhà nước Lào | Dòng nằm đúng trong cụm và tham gia phương trình tổng, nhưng live TM schema chưa có child tiền gửi NHTW theo địa lý tương đương; không ép vào 574 `Tiền gửi khác`. |
| CBD-002 | Tiền gửi tại NHNN | MBB | 30 | Tiền gửi tại Ngân hàng Quốc gia Campuchia | Cùng khoảng trống schema với CBD-001; giữ `UNRESOLVED_SCHEMA_ITEM_ABSENT` và vẫn dùng làm thành phần kiểm tra tổng. |
| CD-001 | Tiền gửi của khách hàng / loại hình doanh nghiệp | VPB | 55 | Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50% | Giá trị hiện tại `64.165`; schema 1079 chỉ mô tả Công ty TNHH **một** thành viên có vốn Nhà nước trên 50%, nên chưa thể dùng thay thế. |
| CD-002 | Tiền gửi của khách hàng / loại hình doanh nghiệp | VIB | 42 | Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50% | Giá trị hiện tại `174`; cùng khoảng trống schema với CD-001. |
| PM-001 | Dự phòng rủi ro cho vay khách hàng | VPB | 45 | Dự phòng chung, dự phòng cụ thể, dự phòng cho vay giao dịch ký quỹ và ứng trước | Đã map và kiểm tra đủ kỳ 01/01–31/03/2026 của PDF được cung cấp; chưa có PDF VPB Q2/2026 nên không được relabel kết quả Q1 thành Q2. |
| SEC-001 | Chứng khoán / đầu tư sẵn sàng để bán | VIB | 36 | Chứng khoán đầu tư sẵn sàng để bán | Không có vùng trading hoàn chỉnh; vùng AFS là subfamily khác và chưa chạy lượt map AFS. Không tuyên bố family chứng khoán vắng mặt. |
| CPM-001 | Tiền, kim loại quý và đá quý | ACB | 3 | Tiền mặt, vàng bạc, đá quý | Whole-PDF scan chỉ thấy dòng tổng và một dòng cash-flow; không có bảng chi tiết `VND / ngoại tệ / vàng / tổng` để map các hàng con. Không tuyên bố family vắng mặt. |
| CPM-002 | Tiền, kim loại quý và đá quý | HDB | 3 | Tiền mặt, vàng | Whole-PDF scan chỉ thấy dòng tổng; các lần lặp tại p39–43 thuộc bảng ngoại tệ/rủi ro/công cụ tài chính, không phải note chi tiết. |
| CPM-003 | Tiền, kim loại quý và đá quý | VCB | 7 | Tiền mặt, vàng bạc, đá quý | Không có vùng chi tiết đủ owner + hai child tiền tệ + kỳ + đơn vị + trailing total; các lần lặp sau là cash-flow/risk controls. |
| CPM-004 | Tiền, kim loại quý và đá quý | CTG | 3 | Tiền mặt, vàng bạc, đá quý | Chỉ có dòng tổng và các bảng phân loại/rủi ro gần giống; không có bảng chi tiết VND/ngoại tệ/vàng. |
| CPM-005 | Tiền, kim loại quý và đá quý | BID | 4 | Tiền mặt, vàng bạc, đá quý | Chỉ có dòng tổng trên báo cáo tình hình tài chính; không có note chi tiết trong 37 trang đã quét. |

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
| CBD-001–CBD-002 | `OPEN_SCHEMA_GAP`; retained in graph/accounting, not coerced to `Tiền gửi khác` |
| LT-001–LT-002 | `RESOLVED_VERIFIED_BY_CODEX` |
| LI-001, LI-008, LI-009 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT` |
| LI-002–LI-007, LI-010–LI-011 | `RESOLVED_VERIFIED_BY_CODEX` |
| LE-001–LE-011 | `RESOLVED` by exact family replay, non-additive graph equivalence, or pixel replay |
| CD-001–CD-002 | `OPEN_SCHEMA_GAP`; không ép Công ty TNHH 2+ thành viên vào schema chỉ dành cho một thành viên |
| PM-001 | `OPEN_SOURCE_PERIOD_GAP`; không còn dòng nguồn chưa map trong PDF Q1 đã bind |
| SEC-001 | `OPEN_DISTINCT_SECURITIES_SUBFAMILY`; trading đã hoàn tất 7 bank, AFS VIB giữ riêng cho lượt kế tiếp |
| CPM-001–CPM-005 | `OPEN_NO_COMPLETE_DETAILED_NOTE_REGION`; chỉ có dòng tổng hoặc negative-control family, không ép thành bảng chi tiết và không tự tuyên bố absence |

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
- MBB's Laos and Cambodia rows remain CBD-001/CBD-002. They stay in the graph
  and total equation but have no exact live TM schema item. ACB/HDB/VCB/CTG/BID
  have no complete detailed region under this contract; no broad family-absence
  claim is made.

## Cash and precious metals (`CASH_PRECIOUS_METALS`)

Current exact-replay result:
`docs/experiments/E-0060-cash-precious-metals-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and requires a short owner, VND and
  foreign-currency cash children, visible period/unit axes and a trailing total.
  It finds exactly one complete region for MBB p30, VPB p38 and VIB p31.
- 12 source rows are `VERIFIED_BY_CODEX`: ReportNormId 562, 563, 565 and the
  exact family total 561 for each complete region. Three current-period
  `VND + foreign + monetary gold = total` equations close exactly.
- ACB/HDB/VCB/CTG/BID retain CPM-001–CPM-005. Balance-sheet totals, cash-flow
  disclosures, financial-instrument classifications and risk tables are
  explicit negative controls, not manufactured detailed-note mappings.
- VPB retains its Q1/2026 source-period caveat.

## Trading securities (`TRADING_SECURITIES`)

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
- VIB p36 AFS remains SEC-001. VPB retains its Q1/2026 source-period caveat.

## Customer deposit (`CUSTOMER_DEPOSIT_CLASSIFICATION`)

Current exact-replay result:
`docs/experiments/E-0058-customer-deposit-8bank-codex-verified-mapping-v1.json`

- Một graph bank-blind quét đủ 453 trang và tìm đúng một vùng hoàn chỉnh trong
  mỗi PDF. Biên đầu/cuối, thứ tự hàng nguồn, bố cục ngang/dọc, kỳ và trục tiền tệ
  đều được giữ lại.
- 118 dòng được `VERIFIED_BY_CODEX`; 43 phương trình cha = con, tổng cột và tổng
  bảng đóng chính xác. Cột tổng và cột phần trăm chỉ là đối chứng khi không phải
  một khoản mục độc lập.
- VIB p42 dòng `Công ty Nhà nước`: VietOCR Transformer đọc thiếu chữ số đầu
  (`3.034.518`), còn pixel PDF và numeric challenger PP-OCRv6 cùng cho
  `13.034.518`; kết quả dùng `13.034.518` và lưu nguyên disagreement.
- CD-001/CD-002 là hai dòng nguồn duy nhất còn chưa map. VPB vẫn giữ đúng kỳ
  nguồn Q1/2026.

## Provision movement (`PROVISION_MOVEMENT_ROLLFORWARD`)

Current exact-replay result:
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
