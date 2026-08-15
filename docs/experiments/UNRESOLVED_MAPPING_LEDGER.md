# Unresolved mapping and adjudication review ledger

Updated: 2026-08-15 (UTC)

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

Ledger total: **75 entries**.  Current open queue: **17**.  Closed history:
**29** row/graph resolutions and **29** confirmed bound-report family absences.
Later families append here rather than creating disconnected candidate lists.
Bank/report/page fields below are evidence locators only, never matching rules.

## Open review queue (always first)

| ID | Family | Bank | Trang | Khoản mục nguồn | Lý do còn mở |
| --- | --- | --- | ---: | --- | --- |
| PM-001 | Dự phòng rủi ro cho vay khách hàng | VPB | 45 | Dự phòng chung, dự phòng cụ thể, dự phòng cho vay giao dịch ký quỹ và ứng trước | Đã map và kiểm tra đủ kỳ 01/01–31/03/2026 của PDF được cung cấp; chưa có PDF VPB Q2/2026 nên không được relabel kết quả Q1 thành Q2. |
| GN-001 | Các khoản nợ Chính phủ và NHNN | ACB | 20 | Vay Ngân hàng Nhà nước | Nguồn không nêu loại nghiệp vụ cụ thể trong các nhánh 1025–1033; không ép số dư vay tổng hợp vào một nhánh gần nhất. |
| GN-002 | Các khoản nợ Chính phủ và NHNN | CTG | 41 | Vay NHNN | Nguồn không nêu loại nghiệp vụ cụ thể trong các nhánh 1025–1033; không ép số dư vay tổng hợp vào một nhánh gần nhất. |
| GN-003 | Các khoản nợ Chính phủ và NHNN | BID | 24 | Vay Ngân hàng Trung ương | Nguồn không nêu loại nghiệp vụ cụ thể trong các nhánh 1025–1033; không ép số dư vay tổng hợp vào một nhánh gần nhất. |
| GN-004 | Các khoản nợ Chính phủ và NHNN | BID | 24 | Tiền gửi có kỳ hạn của KBNN | Schema 1035 chỉ mô tả tiền gửi thanh toán của Kho bạc; chưa có khoản mục riêng tương đương tiền gửi có kỳ hạn. |
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
| PM-001 | `OPEN_SOURCE_PERIOD_GAP`; không còn dòng nguồn chưa map trong PDF Q1 đã bind |
| SEC-001 | `RESOLVED_VERIFIED_BY_CODEX`; E-0067 đã xử lý AFS VIB, map trực tiếp 807/824 và chuyển riêng phép gộp TCTD sang IS-002 |
| CPM-001–CPM-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận các mốc bắt đầu thuyết minh loại trừ family 561 trong năm PDF |
| IS-001 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; BID p23 kế thừa tuyên bố `Triệu VND` nhìn thấy tại p13 của cùng PDF và toàn vùng AFS/HTM được replay-bound |
| IS-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VIB gộp đúng hai dòng TCTD theo từng kỳ vào ReportNormId 808, giữ nguyên hai thành phần và hai phương trình |
| DFI-001 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận VCB không có thuyết minh family 631 |
| IFA-001–IFA-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng biến động TSCĐ vô hình chi tiết trong PDF đã bind |
| IFA-006 | `RESOLVED_VERIFIED_BY_CODEX`; schema 6069 được thêm và map cho disclosure TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng tại VPB/VIB |
| IP-001–IP-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/VPB/HDB/VCB/CTG/BID/VIB không có bảng biến động bất động sản đầu tư chi tiết trong đúng PDF đã bind; statement, policy, cash-flow và expense mentions giữ làm đối chứng âm |
| OA-001–OA-012 | `OPEN_SCHEMA_OR_SEMANTIC_GAP`; 58 khoản mục chắc chắn vẫn đã map, 12 dòng này được giữ nguyên nguồn và không ép vào schema gần nhất |
| GN-001–GN-004 | `OPEN_SCHEMA_OR_SEMANTIC_GAP`; 28 khoản mục chắc chắn vẫn đã map, bốn dòng tổng hợp/khác nghĩa này không bị ép vào nhánh gần nhất |

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
- GN-001–GN-004 retain three unspecified central-bank-loan aggregates and one
  Treasury term-deposit row for which the live schema has no exact leaf. VPB is
  correctly retained as Q1/2026; no result is relabelled as Q2.

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

## Deposits at and loans to other credit institutions (`INTERBANK_DEPOSITS_AND_LOANS`)

Current exact-replay result:
`docs/experiments/E-0062-interbank-deposits-loans-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages, binds the first family owner through
  demand/term deposits, currency children, interbank loans and the last printed
  subtotal or family total. It admits `cho vay`/`vay`, optional deposit-parent
  labels, gold+foreign-currency wording, non-additive discount details and an
  explicit document-level unit declaration.
- ACB p16, MBB p30, VPB p39, CTG p41, BID p25 and VIB p32 are unique complete
  clusters. 63 source rows are `VERIFIED_BY_CODEX`; 23 accounting equations
  close exactly. Three ACB visible dashes remain typed `DASH` before the
  project-owner-approved zero normalization. VPB retains its Q1/2026 caveat.
- HDB/VCB are now confirmed not present in the bound reports by the project
  owner: both supplied note sections begin at trading securities. Their totals
  and foreign-exchange/fair-value controls remain negative controls.

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

## E-0066 — bounded whole-PDF non-observation controls for `Hoạt động mua nợ`

These four entries satisfy the ledger requirement for every no-complete-region
outcome. They are not open mappings: the supplied PDFs were scanned completely,
and the family is recorded as absent only inside that fixed source scope.

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
