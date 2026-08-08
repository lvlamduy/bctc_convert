# Questions for user — current financial-statement ambiguities

Updated: 2026-08-08

- **CDKT unresolved:** 1 scope-policy question (`Q005`); item mapping and the confirmed Q010 value are reconciled.
- **KQKD unresolved:** 0 current item-level questions.
- **LCTT unresolved:** 0 current item-level questions.
- **TM unresolved:** 38 meaningful items = 21 `NEEDS_USER_REVIEW` + 17 `CODEX_STILL_INVESTIGATING` across audited/implemented pages 30–52; pages 50–52 add no user question, and pages 53–61 are still being itemized.

CDKT schema reconciliation is exact after the approved schema update: `78 = 62 MAPPED + 16 NOT_OBSERVED_IN_THIS_PDF`. The not-observed IDs are `4344, 4326, 4345, 4333, 4309, 4303, 4359, 4360, 4373, 4340, 4374, 4341, 4329, 4369, 4370, 4306`. All 64 visible rows now have an explicit mapping or structural-repeat disposition.

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

## NEEDS_USER_REVIEW

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
- **Current status:** `NOT_OBSERVED_IN_THIS_PDF` under the main-statement boundary.
- **Candidate ReportNormId(s):** 4344, 4326, 4345, 4333, 4309, 4303, 4359, 4360, 4373, 4340, 4374, 4341, 4329, 4369, 4370.
- **Why unresolved:** some details may occur only in quantitative notes; using note values in the CDKT output would change the current main-statement-only extraction boundary.
- **What Codex currently thinks:** keep CDKT and quantitative TM evidence separate unless the schema contract says otherwise.
- **Question for user:** For example, if TM notes separately disclose `4344 Tiền, vàng gửi tại các TCTD khác` and `4326 Cho vay các TCTD khác`, should those note values populate the corresponding CDKT template rows even though pages 3–4 show only an aggregate? More generally, may quantitative-note rows backfill these 15 CDKT IDs, or must CDKT output use only rows visible on the main statement?

## RESOLVED_BY_USER — continued

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

**Resolution:** `RESOLVED_BY_USER` — map the visible combined row to ReportNormId `4144`; preserve both visible dashes as `DASH`, not zero.

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7
- **Visible row label:** `Tiền thu/(chi) bất động sản đầu tư`
- **Visible values/periods:** dash / dash for 01/01–31/03/2026 and comparative 2025.
- **Current status:** `MAPPED` to 4144 with `DASH / DASH`; 4145 and 4146 are `NOT_OBSERVED_IN_THIS_PDF`.
- **Candidate ReportNormId(s):** 4144 (resolved).
- **Why previously unresolved:** the PDF presents one combined row while the schema contains several related movements.
- **What Codex currently thinks:** the user-confirmed 4144 treatment must preserve both dashes and never infer zero.
- **Answer incorporated:** map the combined row to 4144.

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

## NEEDS_USER_REVIEW — TM

### Q032

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38, note 10 tangible fixed assets
- **Visible row label:** gross-cost `Tăng trong kỳ`, `Giảm trong kỳ`, and `Tăng/(Giảm) khác`
- **Visible values/periods:** page 38 total increases 754.094 and decreases (354.092); page 37 totals 56.387, (6.224), and (480) triệu đồng.
- **Current status:** `SOURCE_ONLY_AGGREGATE`; the last row is also `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** increases 871–875; decreases 876–878/880–881; other 875/881.
- **Why unresolved:** the PDF aggregates movement causes that the schema separates.
- **What Codex currently thinks:** do not split; the negative sign weakly favors 881 for page 37 `other` but is insufficient authority.
- **Question for user:** Keep these aggregates source-only, select a detail by context/sign, or add aggregate IDs?

### Q033

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38, tangible accumulated depreciation
- **Visible row label:** `Tăng trong kỳ`, `Giảm trong kỳ`, and `Tăng/(Giảm) khác`
- **Visible values/periods:** page 38 totals 551.766 / (201.454); page 37 totals 144.587 / (5.996) / dash; triệu đồng.
- **Current status:** `SOURCE_ONLY_AGGREGATE`.
- **Candidate ReportNormId(s):** increases 885–887; decreases 888–890/892–894; other 887/894.
- **Why unresolved:** aggregate rows cannot prove which detailed schema movement produced them.
- **What Codex currently thinks:** 885 is plausible for increase but unsafe to force.
- **Question for user:** Retain aggregate/components unresolved, select detail IDs, or add aggregate IDs?

### Q037

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–41
- **Visible row label:** asset-class columns in tangible and intangible fixed-asset roll-forwards
- **Visible values/periods:** 226 class-level auxiliary slots outside the total-column schema.
- **Current status:** `SOURCE_ONLY_DIMENSION`.
- **Candidate ReportNormId(s):** same movement IDs as total rows; schema has no asset-class measure axis.
- **Why unresolved:** exporting every class into the same ID would duplicate targets.
- **What Codex currently thinks:** export total only; retain class axes for provenance and equation checks.
- **Question for user:** Is excluding asset-class subaxes from schema Excel intentional?

### Q038

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40, note 11 intangible gross cost
- **Visible row label:** `Tăng trong kỳ`; `Tăng/(giảm) khác`
- **Visible values/periods:** page 39 increase total 77.097; page 40 increase 823.072 and other (10.622) triệu đồng.
- **Current status:** `SOURCE_ONLY_AGGREGATE` / `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** increase 916–920; other 920/927; liquidation 925 is already exact.
- **Why unresolved:** the generic aggregate does not identify a detailed movement; sign only weakly favors 927 for `other`.
- **What Codex currently thinks:** retain increases as aggregate; select 927 only if a sign/context policy is approved.
- **Question for user:** Keep source-only, select 927 by sign, or add aggregate IDs?

### Q039

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40, intangible accumulated amortization
- **Visible row label:** `Tăng trong kỳ`, `Giảm trong kỳ`, and `Tăng/(giảm) khác`
- **Visible values/periods:** page 39 increase 104.592; page 40 increase 601.304, decrease (21.406), other (3.348) triệu đồng.
- **Current status:** `SOURCE_ONLY_AGGREGATE` / `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** increase 931–933; decrease 934–940 (938 strongest); other 933/940.
- **Why unresolved:** the labels are generic and may combine several detailed schema movements.
- **What Codex currently thinks:** context/sign suggest 931/938/940 but are not sufficient authority.
- **Question for user:** Approve those mappings, retain aggregate source-only, or add aggregate IDs?

### Q042

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 41, note 12 investment property
- **Visible row label:** gross-cost `Tăng`, `Giảm`, and `Tăng/(Giảm) khác`
- **Visible values/periods:** current other total (4.971); FY2025 increase 4.971 and decrease (10.260) triệu đồng; other displayed cells include dash.
- **Current status:** `SOURCE_ONLY_AGGREGATE` / `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 945–954; the negative current `other` weakly favors 954.
- **Why unresolved:** the PDF aggregates movement causes that the schema separates.
- **What Codex currently thinks:** do not split or force a detail ID.
- **Question for user:** Keep source-only/components not observed, approve sign-based 954, or add aggregate IDs?

### Q043

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 41, accumulated depreciation
- **Visible row label:** `Tăng trong kỳ`; `Tăng/(Giảm) khác`
- **Visible values/periods:** current increase 1.528; FY2025 increase 6.145 and other (132) triệu đồng.
- **Current status:** `SOURCE_ONLY_AGGREGATE` / `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** increase 958–960; other 960/964.
- **Why unresolved:** generic aggregate labels do not identify detailed movement leaves.
- **What Codex currently thinks:** 958/964 are plausible but insufficiently evidenced.
- **Question for user:** Approve those IDs, retain aggregates source-only, or add aggregate IDs?

### Q045

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 42, note 13
- **Visible row label:** `Chi phí xây dựng cơ bản, mua sắm TSCĐ`
- **Visible values/periods:** 1.295.059 at 31/03/2026; 1.039.654 at 31/12/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_COMPOSITE`.
- **Candidate ReportNormId(s):** 968, 969.
- **Why unresolved:** one PDF row combines two distinct schema concepts and cannot be split from visible evidence.
- **What Codex currently thinks:** retain as a source-only aggregate.
- **Question for user:** Map to one ID, add an aggregate ID, or retain source-only?

### Q050

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 44, note 20
- **Visible row label:** bond and certificate-of-deposit maturity buckets
- **Visible values/periods:** bond `<5y` 24.009.801 / 23.039.165; CD `≤12m` 85.267.048 / 76.253.073; CD `>12m` 79.970.220 / 64.577.077 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROWS` / `AMBIGUOUS_BUCKETS`.
- **Candidate ReportNormId(s):** 1110/1111; 1102/1103; 1103/1104.
- **Why unresolved:** published and schema maturity boundaries overlap differently; `≤12m` conflicts with schema `<12m` plus `12m–<5y`.
- **What Codex currently thinks:** no automatic split or forced bucket.
- **Question for user:** Approve a source-only boundary policy or provide the authoritative crosswalk/allocation?

### Q051

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 44, note 22.1 equity movement grid
- **Visible row label:** component balances and movements from opening 142.022.525 to closing 149.745.325 triệu đồng.
- **Visible values/periods:** profit +7.515.513, reserves/funds/FX/NCI movements, and total changes +7.810.203 −87.403.
- **Current status:** `SOURCE_ONLY_COMPONENT_GRID` / `AMBIGUOUS_MOVEMENTS`.
- **Candidate ReportNormId(s):** exact 1128/1129/1131/1141; unresolved 1130 and 1132–1140.
- **Why unresolved:** PDF is an equity-component × movement grid; schema is a generic movement list.
- **What Codex currently thinks:** map exact opening/profit/closing only and preserve the rest of the grid.
- **Question for user:** Retain source-only, or define mappings for component balances and movement aggregates?

### Q055

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Thu từ dịch vụ thanh toán và ngân quỹ`
- **Visible values/periods:** 1.460.480 for Q1/2026; 755.554 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 1158, 1159.
- **Why unresolved:** one source subtotal combines payment/cash and treasury/guarantee concepts that the schema separates.
- **What Codex currently thinks:** the visible values cannot be split safely.
- **Question for user:** Map this combined row to one ID, add an aggregate ID, or retain it source-only?

### Q057

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Thu từ xử lý nợ, thẩm định giá và khai thác tài sản`
- **Visible values/periods:** 38.898 for Q1/2026; 126.730 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 1162.
- **Why unresolved:** 1162 covers warehouse management/asset valuation, only part of the combined visible concept.
- **What Codex currently thinks:** semantic overlap is insufficient for automatic mapping.
- **Question for user:** Should this combined row map to 1162?

### Q059

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Chi về dịch vụ thanh toán và ngân quỹ`
- **Visible values/periods:** (675.848) for Q1/2026; (551.556) for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 1168, 1169.
- **Why unresolved:** the PDF combines payment and treasury services while the schema separates them.
- **What Codex currently thinks:** no evidence supports a numeric split.
- **Question for user:** Map to one ID, add an aggregate ID, or retain source-only?

### Q061

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Chi phí hoa hồng môi giới`; `Chi về hoạt động môi giới chứng khoán`
- **Visible values/periods:** (539.743) and (59.748) for Q1/2026; (232.408) and (32.105) for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_AGGREGATE`.
- **Candidate ReportNormId(s):** 1170 for both source rows.
- **Why unresolved:** two visible rows may jointly implement the one broader schema target, but no subtotal is printed.
- **What Codex currently thinks:** the likely aggregate is (599.491) / (264.513), while both source rows must remain in provenance.
- **Question for user:** Should both rows be summed into 1170, or should only one row map there?

### Q064

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, foreign-exchange/gold note
- **Visible row label:** `Thu từ kinh doanh ngoại tệ giao ngay và vàng`
- **Visible values/periods:** 662.413 for Q1/2026; 983.504 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING` (combined source row).
- **Candidate ReportNormId(s):** 1177, 1178.
- **Why unresolved:** one visible row combines spot foreign-exchange and gold income that the schema separates.
- **What Codex currently thinks:** the values cannot be split from the PDF.
- **Question for user:** Add/use a combined target, map to one ID, or retain the row source-only?

### Q065

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, foreign-exchange/gold note
- **Visible row label:** `Chi về kinh doanh ngoại tệ giao ngay và vàng`
- **Visible values/periods:** (486.848) for Q1/2026; (221.138) for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING` (combined source row).
- **Candidate ReportNormId(s):** 1183, 1184.
- **Why unresolved:** one visible row combines spot foreign-exchange and gold expense that the schema separates.
- **What Codex currently thinks:** the values cannot be split from the PDF.
- **Question for user:** Add/use a combined target, map to one ID, or retain the row source-only?

### Q066

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, securities note
- **Visible row label:** `(Trích lập)/hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài hạn`
- **Visible values/periods:** DASH for Q1/2026; 20.861 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`; DASH remains status, not zero.
- **Candidate ReportNormId(s):** 1197, 1218.
- **Why unresolved:** label semantics favor 1218, while the row's securities-section position favors 1197 `Khác`.
- **What Codex currently thinks:** 1218 is the stronger label match, but cross-section reuse needs business confirmation.
- **Question for user:** Should this row map to 1218, 1197, or remain source-only?

### Q069

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, other-income/expense note
- **Visible row label:** `Thu nhập/(Chi phí) khác`
- **Visible values/periods:** 252.019 for Q1/2026; 113.256 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING` (signed net row).
- **Candidate ReportNormId(s):** 1239, 1246.
- **Why unresolved:** the PDF exposes one signed net row while the schema separates other income and other expense.
- **What Codex currently thinks:** a sign-based choice would lose the combined business meaning.
- **Question for user:** Add/use a net target, map by sign, or retain source-only?

### Q071

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 49, credit-risk provision note
- **Visible row label:** `Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay khách hàng`
- **Visible values/periods:** 3.451.261 for Q1/2026; 2.973.316 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING` (combined source row).
- **Candidate ReportNormId(s):** 1224, 1225.
- **Why unresolved:** the PDF combines general and specific customer-loan provisions that the schema separates.
- **What Codex currently thinks:** no visible evidence supports a split.
- **Question for user:** Add/use an aggregate target, map to another existing ID, or keep this row source-only?

### Q072

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 49, credit-risk provision note
- **Visible row label:** `Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay TCTD`
- **Visible values/periods:** 1.648 for Q1/2026; 76 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING` (combined source row).
- **Candidate ReportNormId(s):** 1222, 1223.
- **Why unresolved:** the PDF combines general and specific interbank provision movements that the schema separates.
- **What Codex currently thinks:** preserve the combined evidence rather than invent a split.
- **Question for user:** Add/use an aggregate target, map to another existing ID, or keep this row source-only?

### Q073

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 49, credit-risk provision note
- **Visible row label:** `Chi phí/(Hoàn nhập) dự phòng mua nợ`
- **Visible values/periods:** 1.775 for Q1/2026; 24.681 for Q1/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** 1226 `Trích lập dự phòng trái phiếu đặc biệt VAMC`.
- **Why unresolved:** the visible purchased-debt concept is broader than the VAMC-specific schema item.
- **What Codex currently thinks:** do not narrow the row to VAMC without business confirmation.
- **Question for user:** Map this row to 1226, add a generic purchased-debt provision item, or keep it source-only?

## CODEX_STILL_INVESTIGATING

- **TM:** pages 30–52 have been itemized or implemented. Codex is continuing pages 53–61 and will promote only evidence-backed rows from audit candidates into mapping/Excel.

### Q030

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 36, note 9
- **Visible row label:** `Dự phòng giảm giá`
- **Visible values/periods:** (91.228) at both 31/03/2026 and 31/12/2025; triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a dedicated provision identity in branch 862–867.
- **Candidate ReportNormId(s):** none in branch 862–867; 849 belongs to a different note and is not reusable.
- **Why unresolved:** the branch has gross 867 and net 862 but no provision child.
- **What Codex currently thinks:** the provision row is a clear missing schema identity; its parent/order will follow the visible 862–867 branch, and gross plus provision must continue to equal net.
- **No user answer required:** Codex will add and map the dedicated provision identity, then retain the exact gross-plus-provision-equals-net check.

### Q031

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 36, note 9.1
- **Visible row label:** `Đầu tư vào tổ chức kinh tế, dự án dài hạn`; `Đầu tư vào các Quỹ đầu tư`
- **Visible values/periods:** 492.584 / 493.184 and 66.550 / 66.440 triệu đồng at current/comparative snapshots.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add two dedicated detail identities under aggregate 867.
- **Candidate ReportNormId(s):** none exact; 867 is their aggregate only.
- **Why unresolved:** schema branch 862–867 has no matching child identities.
- **What Codex currently thinks:** both labels are clear source details of 867 and should be represented separately while 867 remains their aggregate.
- **No user answer required:** Codex will add both detail identities under 867 and validate their aggregate.

### Q034

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38
- **Visible row label:** tangible gross-cost and accumulated-depreciation `Chênh lệch tỷ giá`
- **Visible values/periods:** page 37 totals 565 / 162; page 38 totals 8.606 / 2.225 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add separate FX movement leaves under parents 869 and 883.
- **Candidate ReportNormId(s):** none exact under parents 869 and 883.
- **Why unresolved:** the schema has no FX movement leaf under either parent.
- **What Codex currently thinks:** the exact FX labels and source hierarchy determine two new leaves; no accounting interpretation from the user is needed.
- **No user answer required:** Codex will add one FX movement leaf under 869 and one under 883, preserving both periods.

### Q036

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38
- **Visible row label:** tangible fixed-asset `Giá trị còn lại` at opening and closing
- **Visible values/periods:** page 38 total 3.750.696 → 3.805.533; page 37 total 3.805.533 → 3.717.028 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add total-axis tangible net-book-value opening/closing identities.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** the schema has cost/depreciation movements but no net-book-value opening/closing leaves.
- **What Codex currently thinks:** opening and closing net book value are clear total-axis identities; gross minus accumulated depreciation remains an independent validation.
- **No user answer required:** Codex will add tangible net-book-value opening/closing identities and retain all reconciliation checks.

### Q040

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40
- **Visible row label:** intangible gross-cost and accumulated-amortization `Chênh lệch tỷ giá`
- **Visible values/periods:** page 39 totals 159 / 44; page 40 totals 1.263 / 391 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add separate FX movement leaves under parents 914 and 929.
- **Candidate ReportNormId(s):** none under parents 914 and 929.
- **Why unresolved:** the schema has no FX movement leaf for either roll-forward.
- **What Codex currently thinks:** the exact FX labels and source hierarchy determine two new leaves; no accounting interpretation from the user is needed.
- **No user answer required:** Codex will add one FX movement leaf under 914 and one under 929, preserving both periods.

### Q041

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40
- **Visible row label:** intangible fixed-asset `Giá trị còn lại` at opening and closing
- **Visible values/periods:** page 40 total 1.679.720 → 1.811.014; page 39 opens at 1.811.014 and closes at 1.783.634 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add total-axis intangible net-book-value opening/closing identities.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** the schema lacks net-book-value opening/closing leaves.
- **What Codex currently thinks:** opening and closing net book value are clear total-axis identities; cost minus amortization and cross-page continuity remain independent validations.
- **No user answer required:** Codex will add intangible net-book-value opening/closing identities and retain all reconciliation checks.

### Q044

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 41
- **Visible row label:** investment-property `Giá trị còn lại` at opening and closing
- **Visible values/periods:** current panel 222.813 → 216.314; FY2025 234.115 → 222.813 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add investment-property net-book-value opening/closing identities.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** schema lacks net-book-value opening/closing leaves.
- **What Codex currently thinks:** opening and closing net book value are clear identities; gross minus depreciation remains an independent validation.
- **No user answer required:** Codex will add investment-property net-book-value opening/closing identities and retain all reconciliation checks.

### Q046

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 42, note 13
- **Visible row label:** `Phải thu liên quan đến dịch vụ thanh toán`; `Phải thu miễn truy đòi theo bộ chứng từ`
- **Visible values/periods:** 861.287 / 1.525.624 and 11.281.653 / 8.046.079 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add two dedicated receivable leaves under the source-indicated receivables parent.
- **Candidate ReportNormId(s):** none exact; 981 is occupied by explicit `Các khoản phải thu khác`.
- **Why unresolved:** current schema has no matching child identities.
- **What Codex currently thinks:** dedicated leaves are safer than overloading 981; final parent placement will follow visible indentation and hierarchy validation.
- **No user answer required:** Codex will add two dedicated receivable leaves in source hierarchy order and will not reuse 981.

### Q048

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 43, note 17
- **Visible row label:** `Tiền gửi của TCKT`; `Tiền gửi của cá nhân`
- **Visible values/periods:** 365.071.880 / 402.397.512 and 540.846.452 / 518.970.620 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add the exact TCKT aggregate and map personal deposits to generic cross-bank ID 1089.
- **Candidate ReportNormId(s):** none for TCKT aggregate; 1089 for personal deposits.
- **Why unresolved:** schema lacks the TCKT aggregate, while 1089 is broader (`Hộ kinh doanh, cá nhân`).
- **What Codex currently thinks:** the exact TCKT aggregate needs its own identity under 1075, while `Tiền gửi của cá nhân` is a safe subtype mapping to generic cross-bank ID 1089.
- **No user answer required:** Codex will add `Tiền gửi của TCKT` under 1075 and map `Tiền gửi của cá nhân` to 1089.

### Q052

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 44, quantitative narrative disclosures
- **Visible row label:** own-bond/CD rates; issued shares; par value; stated capital
- **Visible values/periods:** 5,00–8,80%/year; 4,40–11,18%; 8.054.999.909 shares; 10.000 VND/share; 80.549.999 triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add unit-aware quantitative identities for the disclosed rates, shares, par value and stated capital.
- **Candidate ReportNormId(s):** none native; capital cross-validates the table within rounding.
- **Why unresolved:** schema lacks quantitative fields for these narratives.
- **What Codex currently thinks:** these are explicit quantitative disclosures, so the schema should retain them with native rate/share/VND units instead of hiding them as provenance-only.
- **No user answer required:** Codex will add the quantitative identities with their native units and range semantics.

### Q053

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 45, notes 22.2–22.3
- **Visible row label:** EPS and share-count disclosure family
- **Visible values/periods:** profit 7.515.513 / 6.567.740 triệu đồng; weighted shares 8.054.999.909; EPS 933/815 VND/share; sold/outstanding/common shares 8.054.999.909; repurchased/preferred dash; registered shares blank.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add the EPS/share-count/share-class disclosure family.
- **Candidate ReportNormId(s):** none in the current 1.417-item TM schema; profit only cross-validates 1131.
- **Why unresolved:** the full disclosure family is absent and rows use different units; blank, dash and zero are distinct.
- **What Codex currently thinks:** the disclosure family should be added with unit-aware values and distinct `BLANK`/`DASH` statuses; the profit row remains a cross-check of 1131.
- **No user answer required:** Codex will add the EPS/share family and preserve `BLANK`, `DASH`, share-count and VND/share semantics distinctly.

### Q054

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-interest note
- **Visible row label:** `Thu nhập từ lãi thuần`
- **Visible values/periods:** 14.913.117 for Q1/2026; 11.692.184 for Q1/2025; triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a named net-interest total identity.
- **Candidate ReportNormId(s):** none; it equals visible income 1143 plus expense 1151.
- **Why unresolved:** the TM schema has gross income/expense identities but no distinct visible net-interest target.
- **What Codex currently thinks:** the named net-interest row merits a distinct aggregate identity with formula `1143 + 1151`.
- **No user answer required:** Codex will add the net-interest identity and require `1143 + 1151` to reproduce both visible values.

### Q056

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Thu từ dịch vụ tư vấn`
- **Visible values/periods:** 148.427 for Q1/2026; 98.268 for Q1/2025; triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a dedicated consulting-service income identity under 1157.
- **Candidate ReportNormId(s):** none exact; 1166 is broader other-service income.
- **Why unresolved:** the current schema has no explicit consulting-service income identity.
- **What Codex currently thinks:** consulting-service income is a clear missing leaf and should not be silently folded into 1166.
- **No user answer required:** Codex will add a dedicated consulting-service income child under 1157.

### Q060

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Chi về dịch vụ tư vấn`
- **Visible values/periods:** DASH / DASH for Q1/2026 and Q1/2025; pixel-backed, not zero.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a dedicated consulting-service expense identity under 1167.
- **Candidate ReportNormId(s):** none exact.
- **Why unresolved:** the schema lacks a consulting-service expense identity.
- **What Codex currently thinks:** consulting-service expense is a clear missing leaf; both printed dashes remain `DASH`, never zero.
- **No user answer required:** Codex will add a dedicated consulting-service expense child under 1167 and preserve `DASH / DASH`.

### Q062

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Chi về xử lý nợ, thẩm định giá và khai thác tài sản`
- **Visible values/periods:** (38.259) for Q1/2026; (59.707) for Q1/2025; triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a dedicated combined debt-processing/valuation/asset-exploitation expense identity under 1167.
- **Candidate ReportNormId(s):** none exact; 1174 is broader other-service expense.
- **Why unresolved:** the schema has no exact combined expense identity.
- **What Codex currently thinks:** the exact combined visible expense needs a dedicated leaf and should not be silently folded into broader 1174.
- **No user answer required:** Codex will add the exact combined expense child under 1167 rather than overloading 1174.

### Q063

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 46, net-service note
- **Visible row label:** `Lãi thuần từ hoạt động dịch vụ`
- **Visible values/periods:** 1.708.744 for Q1/2026; 1.235.416 for Q1/2025; triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a named net-service total identity.
- **Candidate ReportNormId(s):** none; it equals visible service income 1157 plus expense 1167.
- **Why unresolved:** the TM schema has gross income/expense identities but no distinct visible net-service target.
- **What Codex currently thinks:** the named net-service row merits a distinct aggregate identity with formula `1157 + 1167`.
- **No user answer required:** Codex will add the net-service identity and require `1157 + 1167` to reproduce both visible values.

### Q067

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 47, securities note
- **Visible row label:** `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư`
- **Visible values/periods:** (250.457) for Q1/2026; 678.047 for Q1/2025; triệu đồng.
- **Current status:** `AUTOMATIC_SCHEMA_ADDITION_QUEUED — no user answer required`; add a combined trading/investment-securities net-result identity.
- **Candidate ReportNormId(s):** none; 1188 and 1193 are the two component net results.
- **Why unresolved:** the schema has each activity's net result but no combined visible total.
- **What Codex currently thinks:** the named combined net result merits a distinct aggregate identity with formula `1188 + 1193`.
- **No user answer required:** Codex will add the combined securities net-result identity and require `1188 + 1193` to reproduce both visible values.

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
- **LCTT one-to-one rows:** 40 rows were resolved algorithmically by exact row order plus independent PP-OCR and DeepSeek semantic agreement. User decisions Q013/Q014/Q018 then close the remaining three visible rows; the resulting business schema has 43 mapped rows, 8 not-observed items and 57 direct-method-inapplicable items.
- **TM page 31 MBS row:** ReportNormId 1944 is an approved appended schema item matching `cho vay margin chứng khoán và ứng trước`; one primary occurrence maps there and repeats remain validation-only.
- **TM page 31 duplicate totals:** gross securities maps to 626, provision to 627, net to root 592 and consolidated loan total to 716; repeated subtotals/totals are retained only for zero-residual checks, not double-mapped.
- **Q047 / TM page 42:** `Tài sản Có khác` maps to ReportNormId 987. Schema hierarchy places 987 directly over the two visible children 989 and 997, whose values sum exactly to the displayed total in both periods; broader umbrella 966 is `NOT_OBSERVED_IN_THIS_PDF`.
