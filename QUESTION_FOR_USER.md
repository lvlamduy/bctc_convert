# Questions for user — current financial-statement ambiguities

Updated: 2026-08-09

- **CDKT unresolved:** 3 active source-driven schema/presentation decisions (`Q074`–`Q076`). `Q005` remains resolved as a statement-page observation boundary with explicit, non-overwriting note linkages.
- **KQKD unresolved:** 0 current item-level questions.
- **LCTT unresolved:** 1 active VPB schema decision shared with CDKT (`Q074`).
- **TM unresolved:** 0. The prior 21 questions were closed-schema artifacts and are now resolved by source-evidenced universal-schema identities or explicit provenance-only dimension treatment. Pages 55–56 and 59 are narrative-only.

MBB CDKT schema reconciliation is exact after the approved universal update and the dedicated off-balance pass: `97 = 73 MAPPED + 24 NOT_OBSERVED + 0 UNRESOLVED`. The original 16 absent identities remain, while the source-visible broader provision rows now own `6035`/`6036` and the narrower `4347`/`4352` are separately not observed. Page 5 maps structural/value identities `6038`–`6048`; `6037` and `6049`–`6053` are not observed. All 75 visible MBB rows and 150 physical value-status cells are accounted; note disclosures remain non-overwriting cross-statement links.

## NEEDS_USER_REVIEW — VPB universal-schema decisions

### Q074

- **Bank:** VPB
- **Period:** consolidated Q1/2026; current 31/03/2026 versus 31/12/2025 for CDKT, Q1/2026 versus Q1/2025 for LCTT.
- **Statement:** CDKT and direct LCTT.
- **PDF page:** 6 (CDKT rows 4 and 6) and 9 (LCTT row 20).
- **Visible row:** `Tiền gửi và vay các tổ chức tài chính ("TCTC"), TCTD khác`; `Vay các TCTC, TCTD khác`; `Tăng/(Giảm) tiền gửi, tiền vay từ các tổ chức tài chính, tổ chức tín dụng khác`.
- **Parent/neighbor context:** the CDKT parent equals its two visible deposit/borrowing children exactly in both snapshots; the LCTT row is the matching liability movement between the Government/NHNN and customer-deposit rows. Note 19.2 explicitly includes IFC funding, so `TCTC` is source meaning rather than OCR noise.
- **Visible values:** CDKT parent `311.527.853 / 295.199.519`; borrowing child `161.866.840 / 154.420.742`; LCTT movement `16.328.334 / (15.265.229)`; unit VND × 1,000,000.
- **Existing candidate ReportNormId(s):** 4319, 4360 and 4136, whose canonical meanings currently say only `TCTD khác`.
- **Proposed interpretation:** the VPB rows are genuine broader TCTC+TCTD concepts, not wording aliases of the narrower TCTD-only identities.
- **Proposed action:** create three new universal identities in the corresponding CDKT and direct-LCTT positions, while retaining 4319, 4360 and 4136 unchanged for banks that report only TCTD.
- **Question for user:** do you agree that explicit TCTC+TCTD disclosures must remain distinct from the existing TCTD-only identities?

### Q075

- **Bank:** VPB
- **Period:** consolidated Q1/2026; 31/03/2026 versus 31/12/2025.
- **Statement:** CDKT / `OFF_BALANCE_SHEET`.
- **PDF page:** 7, final numeric row.
- **Visible row:** `[unlabeled printed total]`.
- **Parent/neighbor context:** it follows the two groups `Nghĩa vụ nợ tiềm ẩn` and `Các khoản mục ngoại bảng khác` and equals their sum exactly in both periods.
- **Visible values:** `1.304.756.779 / 1.367.060.929`; unit VND × 1,000,000.
- **Existing candidate ReportNormId(s):** none. TM note identities are not reusable because they belong to another statement.
- **Proposed interpretation:** printed grand total of all off-balance groups, but the source row itself has no visible label.
- **Proposed action:** keep it as `UNRESOLVED_LABEL / SOURCE_ONLY_VALIDATION` unless a source-supported canonical label is approved; do not infer a name from arithmetic alone.
- **Question for user:** should this remain validation-only, or should the universal schema create a named total such as `TỔNG CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH`?

### Q076

- **Bank:** CTG.
- **Period:** consolidated Q2/2026; 30/06/2026 versus 31/12/2025.
- **Statement:** CDKT / `OFF_BALANCE_SHEET`.
- **PDF page:** 5.
- **Visible row:** `Cam kết giao dịch hoán đổi`.
- **Parent/neighbor context:** it is printed inside the foreign-exchange commitment group, after the separate `Cam kết mua ngoại tệ` and `Cam kết bán ngoại tệ` rows. Its value is the remaining swap component of the visible foreign-exchange total in both periods. The new universal branch currently has separate receive/pay swap legs `6044` and `6045`, but no combined swap subtotal.
- **Visible values:** `937.179.489 / 849.738.846`; unit VND × 1,000,000.
- **Existing candidate ReportNormId(s):** parent `6041`; component legs `6044`, `6045`. Neither leg alone is equivalent to the printed combined row.
- **Proposed interpretation:** this is a genuine reported subtotal for the two swap legs, not an alias of either leg and not the broader foreign-exchange total.
- **Proposed action:** create a new stable ReportNormId under `6041`, insert it after `6043`, and make `6044`/`6045` its children. For CTG, map the printed combined value to the new subtotal while retaining the unprinted legs as `NOT_OBSERVED`.
- **Question for user:** do you agree with adding the combined swap subtotal and reparenting the receive/pay swap legs beneath it?

## RESOLVED_BY_USER

### Q001

**Resolution:** `RESOLVED_BY_USER` — added ReportNormId `5712 TỔNG VỐN CHỦ SỞ HỮU`; visible values are mapped to 5712. Formula metadata records `5712 = 4325 + 4306`.

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 23
- **Visible row label:** `TỔNG VỐN CHỦ SỞ HỮU`
- **Visible values/periods:** 149.745.325 at 31/03/2026; 142.022.525 at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED` to 5712 in the 78-item CDKT schema.
- **Candidate ReportNormId(s):** 5712 (resolved).
- **Why previously unresolved:** the original schema had no distinct total-equity item, while both accounting equations reproduced the row exactly.
- **What Codex currently thinks:** the dedicated identity preserves the visible total without overloading 4305.
- **Answer incorporated:** add 5712 and map the valued row to it.

### Q002

**Resolution:** `RESOLVED_BY_USER` — the blank heading is a structural repeat of ReportNormId `4304`; it remains `BLANK`, never zero and never a duplicate target value.

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 0
- **Visible row label:** `NỢ PHẢI TRẢ`
- **Visible values/periods:** blank at both periods; structural heading, not zero.
- **Current status:** `STRUCTURAL_REPEAT` of 4304 with `BLANK / BLANK`.
- **Candidate ReportNormId(s):** 4304 (resolved).
- **Why previously unresolved:** the heading is moved above the valued 4304 row in this PDF layout.
- **What Codex currently thinks:** retain the blank structural occurrence and map the valued occurrence only once.
- **Answer incorporated:** treat the heading as the moved structural form of 4304.

### Q003

**Resolution:** `RESOLVED_BY_USER` — the blank heading is a structural repeat of `5712 TỔNG VỐN CHỦ SỞ HỮU`; the valued total later on the page is the primary observation.

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 13
- **Visible row label:** `II. VỐN CHỦ SỞ HỮU`
- **Visible values/periods:** blank at both periods; structural heading.
- **Current status:** `STRUCTURAL_REPEAT` of 5712 with `BLANK / BLANK`.
- **Candidate ReportNormId(s):** 5712 (resolved).
- **Why previously unresolved:** the original schema had no identity for the moved heading/valued-total pair.
- **What Codex currently thinks:** preserve both physical occurrences while emitting the target value once.
- **Answer incorporated:** treat the heading as the moved structural form of total equity.

### Q004

**Resolution:** `RESOLVED_BY_USER` — the visible row maps to `5699`; `4306` is retained as a separate schema identity and classified `NOT_OBSERVED_IN_THIS_PDF` for this document.

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 22
- **Visible row label:** `Lợi ích của cổ đông không kiểm soát`
- **Visible values/periods:** 6.161.107 / 5.886.495 triệu đồng.
- **Current status:** `MAPPED` to 5699; 4306 is `NOT_OBSERVED_IN_THIS_PDF` as a separate item.
- **Candidate ReportNormId(s):** 5699 (resolved); 4306 remains a distinct schema identity.
- **Why previously unresolved:** the schema has two related identities at different hierarchy positions.
- **What Codex currently thinks:** the user-confirmed 5699 assignment and separate 4306 disposition preserve both identities.
- **Answer incorporated:** map the visible row to 5699.

## RESOLVED_BY_CODEX — CDKT observation boundary

### Q005

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** main CDKT pages 3–4 versus quantitative notes
- **Visible row label:** the following 15 schema items have no separate visible row on the main CDKT pages:
  `4344 Tiền, vàng gửi tại các TCTD khác`; `4326 Cho vay các TCTD khác`;
  `4345 Dự phòng rủi ro cho vay các TCTD khác`; `4333 Đầu tư vào công ty con`;
  `4309 Lợi thế thương mại`; `4303 NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU`;
  `4359 Tiền gửi của các TCTD khác`; `4360 Vay các TCTD khác`;
  `4373 Vốn đầu tư XDCB`; `4340 Cổ phiếu quỹ`; `4374 Cổ phiếu ưu đãi`;
  `4341 Chênh lệch đánh giá lại tài sản`; `4329 Tài sản cố định thuê tài chính`;
  `4369 Nguyên giá tài sản cố định thuê tài chính`; `4370 Giá trị hao mòn lũy kế tài sản cố định thuê tài chính`.
- **Visible values/periods:** none on pages 3–4.
- **Current status:** `NOT_OBSERVED_ON_TARGET_STATEMENT_PAGES`; quantitative-note evidence is retained as explicit linkage metadata and never silently backfills the main-statement observation.
- **Candidate ReportNormId(s):** 4344, 4326, 4345, 4333, 4309, 4303, 4359, 4360, 4373, 4340, 4374, 4341, 4329, 4369, 4370.
- **Previous blocker:** some details occur only in quantitative notes, so treating the whole PDF as one undifferentiated observation surface would confuse note disclosure with a main-statement row.
- **Final implementation:** CDKT output reports only observations on the target statement pages. Note-page links `4344→TM 576`, `4326→TM 585`, and `4345→broader TM 5718` are linkage-only; no value is injected, imputed, or derived. This preserves both cross-statement evidence and exact observation ownership.

## RESOLVED — user decisions and universal-schema follow-up

### Q006

**Resolution:** `RESOLVED_BY_USER` — mapping remains `4350`; schema/template label was corrected from `...để hàng` to `...để bán` in the versioned business schema.

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 3, row 15
- **Visible row label:** `Chứng khoán đầu tư sẵn sàng để bán`
- **Visible values/periods:** 259.054.739 / 221.512.464 triệu đồng.
- **Current status:** `MAPPED` to 4350; the v2 schema name is corrected to `...sẵn sàng để bán`.
- **Candidate ReportNormId(s):** 4350.
- **Why previously unresolved:** mapping was clear, but the original supplied schema had a label typo.
- **What Codex currently thinks:** only the display name needed correction; the identity remains unchanged.
- **Answer incorporated:** correct the v2 display name and retain 4350.

### Q012

**Resolution:** `RESOLVED_BY_USER` — added ReportNormId `5713 TỔNG THU NHẬP HOẠT ĐỘNG`; the component equation `4385 + 4386 + 4387 + 4388 + 4389 + 4390 + 4393` reproduces both visible values exactly.

- **Statement:** KQKD
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 6, logical row 12
- **Visible row label:** `TỔNG THU NHẬP HOẠT ĐỘNG`
- **Visible values/periods:** 17.430.206 / 15.322.697 triệu đồng for quarter current/comparative; the separately bound Q1 YTD pair repeats them.
- **Current status:** `MAPPED` to 5713 in the 25-item KQKD schema.
- **Candidate ReportNormId(s):** 5713 (resolved).
- **Why previously unresolved:** the original schema contained the components but no visible total identity.
- **What Codex currently thinks:** the new target preserves the total and its exact component equation.
- **Answer incorporated:** add 5713 and map the visible total to it.

### Q013

**Resolution:** `RESOLVED_BY_CODEX` under the universal-schema policy — add aggregate ReportNormId `6034`; preserve both visible dashes as `DASH`, not zero.

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7
- **Visible row label:** `Tiền thu/(chi) bất động sản đầu tư`
- **Visible values/periods:** dash / dash for 01/01–31/03/2026 and comparative 2025.
- **Current status:** `MAPPED` to 6034 with `DASH / DASH`; component IDs 4144, 4145 and 4146 are `NOT_OBSERVED_IN_THIS_PDF` as separate rows.
- **Candidate ReportNormId(s):** 6034 (resolved aggregate); 4144–4146 remain its component children.
- **Why the earlier treatment changed:** 4144 is specifically the purchase component, while the visible PDF row is a distinct net receipt/payment aggregate. Reusing 4144 would narrow the source meaning.
- **Final implementation:** 6034 is inserted under 4111 immediately before its three components; the source row maps to 6034 and both dashes remain nonnumeric observation statuses.

### Q014

**Resolution:** `RESOLVED_BY_USER` — added aggregate ReportNormId `5714 Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác` immediately before 4120/4121; 4120 and 4121 remain its component children and are `NOT_OBSERVED_IN_THIS_PDF` as separate rows.

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7
- **Visible row label:** `Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác`
- **Visible values/periods:** 490 / (71.299) triệu đồng for current/comparative duration.
- **Current status:** `MAPPED` to 5714; 4120 and 4121 are `NOT_OBSERVED_IN_THIS_PDF` separately.
- **Candidate ReportNormId(s):** 5714 (resolved); formula components 4120 and 4121.
- **Why previously unresolved:** the PDF exposes one signed net row while the original schema separated cash paid and recovered.
- **What Codex currently thinks:** the new net identity preserves the visible business concept without a sign-based false split.
- **Answer incorporated:** add 5714 before its two component rows and map the visible row to it.

### Q018

**Resolution:** `RESOLVED_BY_USER` — map the visible wording variant to ReportNormId `4140`; the section/order evidence governs this bank-specific label variant.

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7, row 24
- **Visible row label:** `Tăng/(Giảm) các công cụ tài chính phái sinh và các tài sản tài chính khác`
- **Visible values/periods:** (37.183) / 334.598 triệu đồng for current/comparative duration.
- **Current status:** `MAPPED_BY_USER_WORDING_EQUIVALENCE` to 4140.
- **Candidate ReportNormId(s):** 4140 (resolved); 4131 is the earlier asset-side row and remains separately occupied.
- **Why previously unresolved:** both readers saw a bank-specific wording variant inside the liability-change section.
- **What Codex currently thinks:** section/order plus user confirmation makes 4140 authoritative for this row.
- **Answer incorporated:** treat the wording as equivalent and map to 4140.

## RESOLVED_BY_USER — numeric confirmation

### Q010

**Resolution:** `RESOLVED_BY_USER` — current-period visible value confirmed as `2.320` triệu đồng and exported as `2,320,000,000` VND for ReportNormId `4363`.

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 11
- **Visible row label:** `Dự phòng các khoản nợ khác`
- **Visible values/periods:** current crop visibly reads 2.320; comparative is 2.188; triệu đồng.
- **Current status:** `MAPPED_USER_CONFIRMED` to 4363; current value is 2.320 triệu đồng.
- **Candidate ReportNormId(s):** 4363.
- **Why previously unresolved:** the sealed second reader returned `.20`, so exact reader agreement failed.
- **What Codex currently thinks:** the visible/user-confirmed value and targeted PP-OCR reread support 2.320; the failed reader remains documented.
- **Answer incorporated:** export 2,320,000,000 VND for the current period.

## RESOLVED_BY_USER — TM

### Q015

**Resolution:** `RESOLVED_BY_USER` — both country rows are preserved separately in provenance and aggregated once into ReportNormId `574 Tiền gửi khác`: `797.376 + 1.426.377 = 2.223.753` and `667.675 + 1.590.858 = 2.258.533` triệu đồng.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 30, quantitative note for balances with the State Bank
- **Visible row label:** `Tiền gửi tại Ngân hàng Nhà nước Lào`
- **Visible values/periods:** 797.376 at 31/03/2026; 667.675 at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED_AGGREGATE_COMPONENT`.
- **Candidate ReportNormId(s):** 574 (resolved).
- **Why previously unresolved:** the schema exposes the aggregate State-Bank balance but no country-level child matching this visible row.
- **What Codex currently thinks:** the user-approved generic item 574 is the portable cross-bank treatment.
- **Answer incorporated:** map it as one component of 574.

### Q016

**Resolution:** `RESOLVED_BY_USER` — this row is the second source component of ReportNormId `574 Tiền gửi khác`; it is not emitted as a second target value.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 30, quantitative note for balances with the State Bank
- **Visible row label:** `Tiền gửi tại Ngân hàng Quốc gia Campuchia`
- **Visible values/periods:** 1.426.377 at 31/03/2026; 1.590.858 at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED_AGGREGATE_COMPONENT`.
- **Candidate ReportNormId(s):** 574 (resolved).
- **Why previously unresolved:** the schema exposes the aggregate State-Bank balance but no country-level child matching this visible row.
- **What Codex currently thinks:** preserve the country evidence separately and aggregate it with Q015 into 574.
- **Answer incorporated:** map it as the second component of 574.

### Q017

**Resolution:** `RESOLVED_BY_USER` — added ReportNormId `5718 Tổng dự phòng rủi ro tiền gửi và cho vay các tổ chức tín dụng khác` immediately after 591. The visible total maps to 5718; component IDs 583 and 590 remain separately unobserved in this PDF.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 30, quantitative note for placements/loans to other credit institutions
- **Visible row label:** `Dự phòng rủi ro`
- **Visible values/periods:** (10.785) at 31/03/2026; (9.096) at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED`; component rows `NOT_OBSERVED_IN_THIS_PDF`.
- **Candidate ReportNormId(s):** 5718 (resolved); formula components 583 and 590.
- **Why previously unresolved:** both component schema labels describe parts of the shorter visible total.
- **What Codex currently thinks:** the new total identity 5718 preserves the PDF meaning without falsely choosing either component.
- **Answer incorporated:** add and map 5718; retain 583 and 590 as formula components not separately observed here.

### Q019

**Resolution:** `RESOLVED_BY_USER` — map the visible row to ReportNormId `770`; the schema label is corrected to `Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%`.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32
- **Visible row label:** `Công ty TNHH trên 1 Thành viên vốn Nhà nước lớn hơn 50%`
- **Visible values/periods:** 4.853.278 (0,43%) at 31/03/2026; 4.337.893 (0,40%) at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED`.
- **Candidate ReportNormId(s):** 770 (resolved).
- **Why previously unresolved:** the former schema label was narrower than the visible wording.
- **What Codex currently thinks:** the corrected generic label safely covers both issuer wordings.
- **Answer incorporated:** map to 770 and use the corrected label.

## RESOLVED_BY_USER — TM continued

### Q020

**Resolution:** `RESOLVED_BY_USER` — ReportNormId `782 Khác` is the catch-all child of `766 Phân tích theo loại hình doanh nghiệp`. The visible foreign-branch/subsidiary row contributes to 782 together with the separate visible `Thành phần kinh tế khác` row; the target is emitted once and both source rows retain provenance.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32–33
- **Visible row label:** `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- **Visible values/periods:** 8.815.772 (0,79%) at 31/03/2026; 9.330.629 (0,86%) at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED` as a component of ReportNormId 782; page 33 is retained as duplicate validation.
- **Candidate ReportNormId(s):** 782 (resolved); 765 is explicitly rejected for this row.
- **Why previously unresolved:** the same wording could look geographic without respecting the visible parent section and schema hierarchy.
- **What Codex currently thinks:** hierarchy is decisive: 782 is under 766, and the single exported catch-all amount is 9.402.280 / 9.938.997 triệu đồng after adding `Thành phần kinh tế khác` 586.508 / 608.368.
- **Answer incorporated:** map through 782, preserve both source components, and never double-emit the catch-all target.

### Q021

**Resolution:** `RESOLVED_BY_USER` — schema item 737 is narrowed to `Giáo dục & Đào tạo`; new ReportNormId `5719 Y tế & hoạt động trợ giúp xã hội` is inserted immediately after it. The two PDF rows map separately.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 33
- **Visible row label:** `Giáo dục & Đào tạo`; `Y tế & hoạt động trợ giúp xã hội`
- **Visible values/periods:** 2.689.938 / 2.583.338 and 8.122.254 / 7.888.432 triệu đồng; current/comparative percentages 0,24%/0,24% and 0,72%/0,73%.
- **Current status:** `MAPPED` one-to-one: education→737; health/social work→5719.
- **Candidate ReportNormId(s):** 737 and 5719 (resolved).
- **Why previously unresolved:** the old schema combined two industries shown separately in the PDF.
- **What Codex currently thinks:** separate identities preserve the source rows and avoid an unnecessary derived aggregate.
- **Answer incorporated:** split the old combined item into two schema rows in PDF order.

### Q022

**Resolution:** `RESOLVED_BY_USER` — three missing industry rows were added as ReportNormIds 5720–5722 under parent 727 and mapped one-to-one.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 33
- **Visible row label:** `Ngành nghệ thuật vui chơi giải trí`; `Ngành hoạt động dịch vụ khác`; `Ngành hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất sản phẩm vật chất và dịch vụ tự tiêu dùng của hộ gia đình`.
- **Visible values/periods:** 1.531.664 / 1.708.707; 818.537 / 820.530; 264.294.420 / 239.172.416 triệu đồng, respectively.
- **Current status:** `MAPPED` one-to-one.
- **Candidate ReportNormId(s):** 5720, 5721 and 5722 (resolved); 739 and 745 are not reused.
- **Why previously unresolved:** the supplied schema lacked the three exact visible industries.
- **What Codex currently thinks:** dedicated leaves are safer than forcing a crosswalk into older broad buckets.
- **Answer incorporated:** add the three missing schema items in source order under 727.

### Q023

**Resolution:** `RESOLVED_BY_USER` — hierarchy is fixed as `783 = 784 + 792`; 784 contains general-provision movements and 792 contains specific-provision movements. For the FY2025 audit-adjustment row, the overall columns map 33.942→798 and (1.444)→790; 32.498 is validation only.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 34, FY2025 movement panel
- **Visible row label:** `Điều chỉnh theo Kiểm toán Nhà nước`
- **Visible values/periods:** specific provision 33.942; general provision (1.444); combined 32.498 triệu đồng.
- **Current status:** `MAPPED` on the FY2025 `Tổng cộng` specific/general axes.
- **Candidate ReportNormId(s):** 798 and 790 (resolved).
- **Why previously unresolved:** the PDF names the audit adjustment explicitly while the schema uses the broader movement label `Điều chỉnh khác`.
- **What Codex currently thinks:** the user-confirmed hierarchy and column context make both assignments exact; the combined column must not become a third target.
- **Answer incorporated:** map only the overall specific/general values and use their combined total as an equation check.

### Q024

**Resolution:** `RESOLVED_BY_USER` — the `Tại Việt Nam` and `Tại nước ngoài` subaxes are intentionally excluded from schema Excel. Only `Tổng cộng` specific/general axes are mapping-authoritative; geographic and combined columns remain provenance/validation.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 34
- **Visible row label:** provision movements split by `Tại Việt Nam`, `Tại nước ngoài` and `Tổng cộng`.
- **Visible values/periods:** 77 auxiliary value/status slots across Q1/2026 and FY2025 panels.
- **Current status:** `SOURCE_ONLY_DIMENSION` (confirmed intentional).
- **Candidate ReportNormId(s):** 785–799 already represent the overall specific/general measures, not geography.
- **Why previously unresolved:** the schema has no geographic axis for this movement table.
- **What Codex currently thinks:** the confirmed policy avoids duplicating provision movements across geography and total columns.
- **Answer incorporated:** do not export domestic/foreign details; retain all 77 auxiliary slots for provenance and accounting checks.

## RESOLVED_BY_USER — TM Q025–Q027

### Q025

**Resolution:** `RESOLVED_BY_USER` — add ReportNormId `5740 Chứng khoán nợ do Chính phủ bảo lãnh` immediately after 807, under parent 805, and map the visible row directly.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 35
- **Visible row label:** `Chứng khoán nợ do Chính phủ bảo lãnh`
- **Visible values/periods:** 22.128.777 at 31/03/2026; 22.204.008 at 31/12/2025; triệu đồng.
- **Current status:** `MAPPED` to the new dedicated identity 5740.
- **Candidate ReportNormId(s):** 5740 (resolved); 807 remains exclusively government-issued debt.
- **Why previously unresolved:** the PDF separates government-issued and government-guaranteed debt, while the supplied schema contained only the former.
- **What Codex currently thinks:** a sibling directly after 807 preserves the visible distinction and prevents an incorrect derived aggregate in 807.
- **Answer incorporated:** add the exact missing item and map both snapshot values one-to-one.

### Q026

**Resolution:** `RESOLVED_BY_USER` — add two distinct children under `800 Hoạt động mua nợ`: ReportNormId `5738 Nợ gốc đã mua` and `5739 Lãi của khoản nợ đã mua`, after 803 and before 804 in PDF order.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 35
- **Visible row label:** `Nợ gốc đã mua`; `Lãi của khoản nợ đã mua`.
- **Visible values/periods:** principal 2.287.269 / 2.465.314 triệu đồng; interest DASH / DASH at 31/03/2026 and 31/12/2025.
- **Current status:** `MAPPED` to 5738 and 5739; DASH remains an observation status, never zero.
- **Candidate ReportNormId(s):** 5738 and 5739 (resolved).
- **Why previously unresolved:** the supplied branch 800–803 did not contain either detail identity.
- **What Codex currently thinks:** both rows belong under purchased-debt activity; the principal duplicates the visible primary gross amount only as a validation fact, not as the same schema identity.
- **Answer incorporated:** add both missing items and preserve the principal duplicate check and interest DASH provenance.

### Q027

**Resolution:** `RESOLVED_BY_USER` — percentage columns are not schema targets. They remain source provenance and independently recomputed validation measures; only VND amounts are exported.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32–33
- **Visible row label:** percentage columns accompanying every loan-analysis row.
- **Visible values/periods:** 88 percentage cells across current and comparative snapshot axes.
- **Current status:** `SOURCE_ONLY_MEASURE` (confirmed intentional).
- **Candidate ReportNormId(s):** same item IDs as the amount rows; no percentage-specific schema IDs.
- **Why previously unresolved:** the target template has no explicit measure dimension distinguishing amount from percentage.
- **What Codex currently thinks:** retaining both printed and recomputed percentages gives a strong source check without creating duplicate value columns.
- **Answer incorporated:** keep percentages outside schema Excel and use them for provenance/validation.

## RESOLVED_BY_USER — TM Q028

### Q028

**Resolution:** `RESOLVED_BY_USER` — the visible bank-only amount is a source subtotal, not a separate target. Margin/advance loans are represented by context-specific identities inside each visible analysis branch, while legacy global ID 1944 stays parentless and workbook-last.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 31, repeated on the maturity table and pages 32–33
- **Visible row label:** unlabeled bank-only loan subtotal before MBS margin/advance loans.
- **Visible values/periods:** 1.105.042.109 at 31/03/2026; 1.068.978.785 at 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_SUBTOTAL` (confirmed); subtotal + margin/advance loans = 716 on both snapshot axes.
- **Candidate ReportNormId(s):** no ID for the subtotal. New context IDs are 5745 under 717 (loan type), 5746 under 747 (`Trong đó` quality), 5747 under 752 (maturity), 5748 under 766 (enterprise type), and 5749 under 727 (industry).
- **Why previously unresolved:** the subtotal was visible in several analyses, while schema only had the global parent 716 and parentless append-only ID 1944.
- **What Codex currently thinks:** each analysis needs its own identity because one ReportNormId cannot have five parents. Every context row carries 15.520.372 / 15.040.585 triệu đồng and remains cross-table duplicate evidence; no amounts are summed across analysis branches.
- **Answer incorporated:** preserve the subtotal as provenance, keep 1944 unchanged for its sealed global identity, and add the five hierarchy-specific margin/advance-loan leaves.

## RESOLVED_BY_CODEX — TM Q029

### Q029

**Resolution:** `RESOLVED_BY_CODEX` — the Q020 hierarchy decision fully determines all four rows. They are subtotal/detail provenance feeding already mapped children or catch-all 782; none needs a separate schema identity.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32
- **Visible row label:** `Cho vay các TCKT`; `Cho vay khác`; foreign-business loans; foreign-personal loans.
- **Visible values/periods:** 635.708.290 / 621.056.253; 836.450 / 904.945; 1.891.644 / 2.176.885; 6.924.128 / 7.153.744 triệu đồng.
- **Current status:** `SOURCE_ONLY_SUBTOTAL` / `SOURCE_ONLY_VALIDATION` (resolved algorithmically).
- **Candidate ReportNormId(s):** no direct target for the two subtotals; the foreign branch total and the exact `Khác` component feed 782, while their detailed source rows remain provenance.
- **Why previously unresolved:** the source has intermediate totals and details in addition to the final hierarchy leaves.
- **What Codex currently thinks:** `Cho vay các TCKT` validates its enterprise-type children; `Cho vay khác` validates 781 plus the exact catch-all component; foreign-business plus foreign-personal validates the foreign-branch component assigned to 782.
- **Resolution evidence:** every subtotal equation passes on both snapshot axes, 765 is not used, and no ReportNormId is emitted twice.

## RESOLVED_BY_CODEX — TM universal-schema migration

The following items were previously framed as forced mappings into a closed schema. Source re-audit established that they are either genuine accounting identities absent from the prior schema or non-row dimensions that belong in provenance. They no longer require user answers.

### Q032–Q033

- **Statement / pages:** TM, MBB consolidated Q1/2026, pages 37–38.
- **Visible concepts:** tangible-fixed-asset gross-cost and accumulated-depreciation increase, decrease, and other aggregates.
- **Final status:** `RESOLVED_BY_CODEX` — added source aggregate IDs 5991–5996 under their true gross-cost/depreciation parents. Detailed cause IDs remain children and are not selected by sign.

### Q037

- **Statement / pages:** TM, pages 37–41.
- **Visible concept:** asset-class columns across roll-forward rows.
- **Final status:** `RESOLVED_BY_CODEX — PROVENANCE_DIMENSION`; class axes and their 226 cells remain first-class observation/validation provenance. They are not duplicated as accounting-row IDs because they are columns, not distinct row identities.

### Q038–Q039

- **Statement / pages:** TM, pages 39–40.
- **Visible concepts:** intangible-asset gross-cost and accumulated-amortization increase/decrease/other aggregates.
- **Final status:** `RESOLVED_BY_CODEX` — added IDs 5997–6001 under their true parents. No detailed movement is inferred from a generic aggregate.

### Q042–Q043

- **Statement / page:** TM, page 41.
- **Visible concepts:** investment-property gross-cost and accumulated-depreciation increase/decrease/other aggregates.
- **Final status:** `RESOLVED_BY_CODEX` — added IDs 6002–6006; visible aggregate rows are preserved without sign-based force-mapping.

### Q045

- **Statement / page:** TM, page 42.
- **Visible concept:** `Chi phí xây dựng cơ bản, mua sắm TSCĐ`, 1.295.059 / 1.039.654 triệu đồng.
- **Final status:** `RESOLVED_BY_CODEX` — added combined source identity 6007 under parent 967 instead of forcing the row into either 968 or 969.

### Q050

- **Statement / page:** TM, page 44.
- **Visible concepts:** CD `Từ 12 tháng trở xuống`, CD `Trên 12 tháng`, and bond `Dưới 5 năm`.
- **Final status:** `RESOLVED_BY_CODEX` — added exact source-boundary IDs 6008–6010. Existing buckets with different boundaries are not reused or numerically allocated.

### Q051

- **Statement / page:** TM, page 44.
- **Visible concept:** equity component × movement grid.
- **Final status:** `RESOLVED_BY_CODEX` — added component identities 6011–6018 and printed movement parents 6019 `Trích lập/Tăng` and 6020 `Sử dụng/Giảm`; the latter own existing movement details 1130–1140 in source order. Matrix axes remain provenance where they are not row identities.

### Q055, Q057 and Q059

- **Statement / page:** TM, page 46.
- **Visible concepts:** combined payment/treasury income, debt-processing/valuation/asset-exploitation income, and combined payment/treasury expense.
- **Final status:** `RESOLVED_BY_CODEX` — added exact combined identities 6021, 6022 and 6023. No numeric split across narrower existing IDs is invented.

### Q061

- **Statement / page:** TM, page 46.
- **Visible concepts:** `Chi phí hoa hồng môi giới` and `Chi về hoạt động môi giới chứng khoán`.
- **Final status:** `RESOLVED_BY_CODEX` — added direct child identities 6024 and 6025. Existing broader ID 1170 is retained as an explicitly derived aggregate with both children, derivation method, period, unit, and provenance; it never replaces the printed child observations.

### Q064–Q065

- **Statement / page:** TM, page 47.
- **Visible concepts:** combined spot-FX-and-gold income and expense.
- **Final status:** `RESOLVED_BY_CODEX` — added exact combined identities 6026 and 6027 rather than selecting one narrower legacy component.

### Q066

- **Statement / page:** TM, page 47.
- **Visible concept:** `(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn`, `DASH / 20.861` triệu đồng.
- **Final status:** `RESOLVED_BY_CODEX` — added identity 6028 in the visible securities-note context; `DASH` remains nonnumeric and is never converted to zero.

### Q069

- **Statement / page:** TM, page 47.
- **Visible concept:** `Thu nhập/(Chi phí) khác`, 252.019 / 113.256 triệu đồng.
- **Final status:** `RESOLVED_BY_CODEX` — added signed-net child 6030 under new visible parent 6029 `Lãi thuần từ hoạt động kinh doanh khác`; no sign-based choice between separate income/expense IDs is made.

### Q071–Q073

- **Statement / page:** TM, page 49.
- **Visible concepts:** combined customer-loan provision, interbank-loan provision, and purchased-debt provision expense/reversal rows.
- **Final status:** `RESOLVED_BY_CODEX` — added exact aggregate identities 6031–6033 under 1221. General/specific leaves and VAMC-specific 1226 are not substituted for broader printed rows.

## RESOLVED_BY_CODEX — automatic schema additions completed

- **TM:** every quantitative page through page 61 has been itemized and reconciled. These 17 evidence-backed schema gaps are now added, hierarchy-bound and mapped; no user answer is required. Pages 55–56 and 59 are narrative-only.

### Q030

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 36, note 9
- **Visible row label:** `Dự phòng giảm giá`
- **Visible values/periods:** (91.228) at both 31/03/2026 and 31/12/2025; triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped ReportNormId 5959 `Dự phòng giảm giá` in branch 862–867.
- **Candidate ReportNormId(s):** none in branch 862–867; 849 belongs to a different note and is not reusable.
- **Previous blocker:** the branch had gross 867 and net 862 but no provision child.
- **Final implementation:** 5959 is source-mapped at both snapshots; `862 = 867 + 5959` is retained as validation only and passes exactly.

### Q031

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 36, note 9.1
- **Visible row label:** `Đầu tư vào tổ chức kinh tế, dự án dài hạn`; `Đầu tư vào các Quỹ đầu tư`
- **Visible values/periods:** 492.584 / 493.184 and 66.550 / 66.440 triệu đồng at current/comparative snapshots.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped ReportNormIds 5960 and 5961 under aggregate 867.
- **Candidate ReportNormId(s):** none exact; 867 is their aggregate only.
- **Previous blocker:** schema branch 862–867 had no matching child identities.
- **Final implementation:** both visible details are mapped separately and `867 = 5960 + 5961` is retained as validation only.

### Q034

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38
- **Visible row label:** tangible gross-cost and accumulated-depreciation `Chênh lệch tỷ giá`
- **Visible values/periods:** page 37 totals 565 / 162; page 38 totals 8.606 / 2.225 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped FX movement leaves 5962 under 869 and 5963 under 883.
- **Candidate ReportNormId(s):** none exact under parents 869 and 883.
- **Previous blocker:** the schema had no FX movement leaf under either parent.
- **Final implementation:** both total-axis source values are mapped for Q1/2026 and FY2025; roll-forward equations remain validation only.

### Q036

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38
- **Visible row label:** tangible fixed-asset `Giá trị còn lại` at opening and closing
- **Visible values/periods:** page 38 total 3.750.696 → 3.805.533; page 37 total 3.805.533 → 3.717.028 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added structural root 5964 and mapped opening/closing identities 5965/5966.
- **Candidate ReportNormId(s):** none.
- **Previous blocker:** the schema had cost/depreciation movements but no net-book-value opening/closing leaves.
- **Final implementation:** only printed TOTAL-axis values are mapped; gross minus accumulated depreciation and cross-panel continuity remain validation only.

### Q040

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40
- **Visible row label:** intangible gross-cost and accumulated-amortization `Chênh lệch tỷ giá`
- **Visible values/periods:** page 39 totals 159 / 44; page 40 totals 1.263 / 391 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped FX movement leaves 5967 under 914 and 5968 under 929.
- **Candidate ReportNormId(s):** none under parents 914 and 929.
- **Previous blocker:** the schema had no FX movement leaf for either roll-forward.
- **Final implementation:** both total-axis source values are mapped for Q1/2026 and FY2025; roll-forward equations remain validation only.

### Q041

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40
- **Visible row label:** intangible fixed-asset `Giá trị còn lại` at opening and closing
- **Visible values/periods:** page 40 total 1.679.720 → 1.811.014; page 39 opens at 1.811.014 and closes at 1.783.634 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added structural root 5969 and mapped opening/closing identities 5970/5971.
- **Candidate ReportNormId(s):** none.
- **Previous blocker:** the schema lacked net-book-value opening/closing leaves.
- **Final implementation:** only printed TOTAL-axis values are mapped; cost minus amortization and cross-page continuity remain validation only.

### Q044

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 41
- **Visible row label:** investment-property `Giá trị còn lại` at opening and closing
- **Visible values/periods:** current panel 222.813 → 216.314; FY2025 234.115 → 222.813 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added structural root 5972 and mapped opening/closing identities 5973/5974.
- **Candidate ReportNormId(s):** none.
- **Previous blocker:** the schema lacked net-book-value opening/closing leaves.
- **Final implementation:** only printed TOTAL-axis values are mapped; gross minus depreciation and cross-panel continuity remain validation only.

### Q046

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 42, note 13
- **Visible row label:** `Phải thu liên quan đến dịch vụ thanh toán`; `Phải thu miễn truy đòi theo bộ chứng từ`
- **Visible values/periods:** 861.287 / 1.525.624 and 11.281.653 / 8.046.079 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped receivable leaves 5975 and 5976 under parent 967.
- **Candidate ReportNormId(s):** none exact; 981 is occupied by explicit `Các khoản phải thu khác`.
- **Previous blocker:** the schema had no matching child identities.
- **Final implementation:** both visible rows are mapped in source order before catch-all 981; 981 remains reserved for explicit `Các khoản phải thu khác`.

### Q048

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 43, note 17
- **Visible row label:** `Tiền gửi của TCKT`; `Tiền gửi của cá nhân`
- **Visible values/periods:** 365.071.880 / 402.397.512 and 540.846.452 / 518.970.620 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped TCKT identity 5977; mapped personal deposits to cross-bank ID 1089.
- **Candidate ReportNormId(s):** none for TCKT aggregate; 1089 for personal deposits.
- **Previous blocker:** the schema lacked the TCKT aggregate, while 1089 is broader (`Hộ kinh doanh, cá nhân`).
- **Final implementation:** both printed rows are mapped and `1055 = 5977 + 1089` passes exactly for both snapshots as validation only.

### Q052

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 44, quantitative narrative disclosures
- **Visible row label:** own-bond/CD rates; issued shares; par value; stated capital
- **Visible values/periods:** 5,00–8,80%/year; 4,40–11,18%; 8.054.999.909 shares; 10.000 VND/share; 80.549.999 triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped unit-aware ReportNormIds 5978–5984.
- **Candidate ReportNormId(s):** none native; capital cross-validates the table within rounding.
- **Previous blocker:** the schema lacked quantitative fields for these narratives.
- **Final implementation:** four rate endpoints retain `PERCENT_PER_YEAR`, share count retains `SHARE`, par retains `VND_PER_SHARE`, and stated capital retains source `VND_MILLION`; the capital equation is validation only.

### Q053

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 45, notes 22.2–22.3
- **Visible row label:** EPS and share-count disclosure family
- **Visible values/periods:** profit 7.515.513 / 6.567.740 triệu đồng; weighted shares 8.054.999.909; EPS 933/815 VND/share; sold/outstanding/common shares 8.054.999.909; repurchased/preferred dash; registered shares blank.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped the EPS/share family as ReportNormIds 5946–5958.
- **Candidate ReportNormId(s):** resolved to 5946–5958; the profit row remains external validation of page-44 owner 1131.
- **Previous blocker:** the full disclosure family was absent and rows use different units; blank, dash and zero are distinct.
- **Final implementation:** 22 mapped observations preserve 12 `VALUE`, 8 pixel-backed `DASH`, and 2 `BLANK` cells; EPS uses `VND_PER_SHARE`, share counts use `SHARE`, and both EPS checks pass without duplicate ownership of 1131.

### Q054

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-interest note
- **Visible row label:** `Thu nhập từ lãi thuần`
- **Visible values/periods:** 14.913.117 for Q1/2026; 11.692.184 for Q1/2025; triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped net-interest identity 5985.
- **Candidate ReportNormId(s):** none; it equals visible income 1143 plus expense 1151.
- **Previous blocker:** the TM schema had gross income/expense identities but no distinct visible net-interest target.
- **Final implementation:** both printed values map to 5985 and `5985 = 1143 + 1151` passes exactly as validation only.

### Q056

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Thu từ dịch vụ tư vấn`
- **Visible values/periods:** 148.427 for Q1/2026; 98.268 for Q1/2025; triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped consulting-income identity 5986 under 1157.
- **Candidate ReportNormId(s):** none exact; 1166 is broader other-service income.
- **Previous blocker:** the schema had no explicit consulting-service income identity.
- **Final implementation:** both printed values map directly to 5986; catch-all 1166 is not overloaded.

### Q060

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Chi về dịch vụ tư vấn`
- **Visible values/periods:** DASH / DASH for Q1/2026 and Q1/2025; pixel-backed, not zero.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped consulting-expense identity 5987 under 1167.
- **Candidate ReportNormId(s):** none exact.
- **Previous blocker:** the schema lacked a consulting-service expense identity.
- **Final implementation:** both cells map to 5987 as pixel-backed `DASH`; neither is converted to zero.

### Q062

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Chi về xử lý nợ, thẩm định giá và khai thác tài sản`
- **Visible values/periods:** (38.259) for Q1/2026; (59.707) for Q1/2025; triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped combined expense identity 5988 under 1167.
- **Candidate ReportNormId(s):** none exact; 1174 is broader other-service expense.
- **Previous blocker:** the schema had no exact combined expense identity.
- **Final implementation:** both printed values map directly to 5988; broader catch-all 1174 is not overloaded.

### Q063

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Lãi thuần từ hoạt động dịch vụ`
- **Visible values/periods:** 1.708.744 for Q1/2026; 1.235.416 for Q1/2025; triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped net-service identity 5989.
- **Candidate ReportNormId(s):** none; it equals visible service income 1157 plus expense 1167.
- **Previous blocker:** the TM schema had gross income/expense identities but no distinct visible net-service target.
- **Final implementation:** both printed values map to 5989 and `5989 = 1157 + 1167` passes exactly as validation only.

### Q067

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, securities note
- **Visible row label:** `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư`
- **Visible values/periods:** (250.457) for Q1/2026; 678.047 for Q1/2025; triệu đồng.
- **Current status:** `RESOLVED_BY_CODEX` — added and mapped combined net-result identity 5990.
- **Candidate ReportNormId(s):** none; 1188 and 1193 are the two component net results.
- **Previous blocker:** the schema had each activity's net result but no combined visible total.
- **Final implementation:** both printed values map to 5990 and `5990 = 1188 + 1193` passes exactly as validation only.

## RESOLVED_BY_CODEX

### Q035

**Resolution:** `RESOLVED_BY_CODEX` — map the visible 1.221 triệu đồng total to ReportNormId 887 `Tăng khác`.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 38
- **Visible row label:** `Điều chỉnh theo Kiểm toán Nhà nước` under accumulated depreciation
- **Visible values/periods:** total 1.221 triệu đồng; only the machinery/equipment class has value, other classes show dash.
- **Current status:** `MAPPED_BY_CONTEXT` to 887; the class-level cells remain source provenance and the total-axis value is authoritative.
- **Candidate ReportNormId(s):** 887 (resolved).
- **Why previously unresolved:** a named audit adjustment is not an exact match for the generic schema concept.
- **What Codex currently thinks:** Q023 established that a named State Audit adjustment maps through the correctly parented generic other-adjustment movement; section, positive direction and hierarchy fix 887 here.
- **Resolution evidence:** the Q023 user decision supplies the generic-adjustment rule, and the row sits inside accumulated depreciation with a positive 1.221 total.

### Q049

**Resolution:** `RESOLVED_BY_CODEX` — retain the net carrying-value column as `SOURCE_ONLY_MEASURE` / `SOURCE_ONLY_VALIDATION`; do not create duplicate target identities.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 43, note 18 derivatives
- **Visible row label:** net carrying-value columns for total, forward and swap contracts
- **Visible values/periods:** current (661.326)/(150.745)/(510.581); prior (698.507)/(19.293)/(679.214) triệu đồng.
- **Current status:** `SOURCE_ONLY_MEASURE` / `SOURCE_ONLY_VALIDATION` (`RESOLVED_BY_CODEX`).
- **Candidate ReportNormId(s):** none; branch 631–715 has contract/asset/liability identities only.
- **Why previously unresolved:** schema lacks the visible net measure.
- **What Codex currently thinks:** net carrying value is the algebraic asset-plus-liability result on a secondary measure axis, so retaining and recomputing it gives validation without duplicating ReportNormIds.
- **Resolution evidence:** each visible net amount reconciles to its asset and liability columns; this is consistent with the confirmed Q027 treatment of secondary measure axes.

### Q058

**Resolution:** `RESOLVED_BY_CODEX` — map the visible brokerage-service row to ReportNormId 1160 `Dịch vụ chứng khoán`.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Thu từ hoạt động môi giới chứng khoán`
- **Visible values/periods:** 241.339 for Q1/2026; 133.456 for Q1/2025; triệu đồng.
- **Current status:** `MAPPED_BY_GENERIC_SCHEMA_EQUIVALENCE` to 1160.
- **Candidate ReportNormId(s):** 1160 (resolved).
- **Why previously unresolved:** the visible row is a subtype of the broader schema label.
- **What Codex currently thinks:** brokerage activity is an exact subtype of the portable cross-bank item `Dịch vụ chứng khoán`, so 1160 is authoritative.
- **Resolution evidence:** the source subtype is wholly contained by the generic 1160 label and lies in the correct service-income section.

### Q068

**Resolution:** `RESOLVED_BY_CODEX` — map `Thu từ các khoản nợ đã xử lý` to ReportNormId 1234.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, other-income/expense note
- **Visible row label:** `Thu từ các khoản nợ đã xử lý`
- **Visible values/periods:** 733.893 for Q1/2026; 1.003.397 for Q1/2025; triệu đồng.
- **Current status:** `MAPPED_BY_LABEL_ACTION` to 1234.
- **Candidate ReportNormId(s):** 1234 (resolved); 1230 is rejected for this recovery-action row.
- **Why previously unresolved:** both schema labels concern processed bad debt; 1234 explicitly says recovery, while 1230 is broader.
- **What Codex currently thinks:** the visible wording describes recovery action, which matches 1234; 1230 is the broader processed-bad-debt concept.
- **Resolution evidence:** 1234 explicitly denotes recovery of bad/processed/written-off debt, matching `Thu từ ... nợ đã xử lý` more precisely than 1230.

### Q070

**Resolution:** `RESOLVED_BY_CODEX` — retain the unlabeled derived total as `SOURCE_ONLY_VALIDATION`; do not create an unnamed schema target.

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, other-income/expense note
- **Visible row label:** `[unlabeled total]`
- **Visible values/periods:** 1.090.478 for Q1/2026; 1.179.210 for Q1/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_VALIDATION` (`RESOLVED_BY_CODEX`).
- **Candidate ReportNormId(s):** none.
- **Why previously unresolved:** the schema contains gross other-income/expense families but no distinct visible net total.
- **What Codex currently thinks:** the row is unlabeled and derived from the mapped gross other-income/expense families, so it has no stable independent source identity.
- **Resolution evidence:** the total reconciles the source table and has no printed label; keeping it validation-only preserves evidence without inventing a name.

- **Q007 / 4329:** finance-lease fixed asset is `NOT_OBSERVED_IN_THIS_PDF`; visible rows belong to tangible/intangible parents.
- **Q008 / 4369:** finance-lease original cost is `NOT_OBSERVED_IN_THIS_PDF`; parent-subtype gating removed the false candidate.
- **Q009 / 4370:** finance-lease accumulated depreciation is `NOT_OBSERVED_IN_THIS_PDF`; parent-subtype gating removed the false candidate.
- **Q011 / scope:** visible title evidence binds MBB Q1/2026 to `CONSOLIDATED`; the older sealed E-0041 receipt remains unchanged and still records its historical `UNKNOWN` value.
- **LCTT one-to-one rows:** 40 rows were resolved algorithmically by exact row order plus independent PP-OCR and DeepSeek semantic agreement. User decisions Q013/Q014/Q018 then close the remaining three visible rows; the resulting business schema has 43 mapped rows, 9 not-observed items and 57 direct-method-inapplicable items.
- **TM page 31 MBS row:** ReportNormId 1944 is an approved appended schema item matching `cho vay margin chứng khoán và ứng trước`; one primary occurrence maps there and repeats remain validation-only.
- **TM page 31 duplicate totals:** gross securities maps to 626, provision to 627, net to root 592 and consolidated loan total to 716; repeated subtotals/totals are retained only for zero-residual checks, not double-mapped.
- **Q047 / TM page 42:** `Tài sản Có khác` maps to ReportNormId 987. Schema hierarchy places 987 directly over the two visible children 989 and 997, whose values sum exactly to the displayed total in both periods; broader umbrella 966 is `NOT_OBSERVED_IN_THIS_PDF`.
