# Questions for user — current financial-statement ambiguities

Updated: 2026-08-08

- **CDKT unresolved:** 7 active issues — all 7 are `NEEDS_USER_REVIEW`; Codex continues work elsewhere without waiting.
- **KQKD unresolved:** 1 source-only row; 0 unresolved schema mappings.
- **LCTT unresolved:** 6 schema items (5 composite candidates + 1 label conflict) and 2 source-only composite rows.
- **TM unresolved:** 38 meaningful questions across audited pages 30–45; pages 46–61 are still being itemized.

CDKT schema reconciliation is exact: `77 = 61 MAPPED + 15 NOT_OBSERVED_IN_THIS_PDF + 1 UNRESOLVED`. The not-observed IDs are `4344, 4326, 4345, 4333, 4309, 4303, 4359, 4360, 4373, 4340, 4374, 4341, 4329, 4369, 4370`. Three source-only CDKT rows remain outside the denominator.

## NEEDS_USER_REVIEW

### Q001

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 23
- **Visible row label:** `TỔNG VỐN CHỦ SỞ HỮU`
- **Visible values/periods:** 149.745.325 at 31/03/2026; 142.022.525 at 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW`; strong `POSSIBLE_SCHEMA_GAP` outside the 77-item denominator.
- **Candidate ReportNormId(s):** none; 4305 is already used by the following grand-total row.
- **Why unresolved:** the schema has no distinct total-equity item, while both accounting equations reproduce the row exactly.
- **What Codex currently thinks:** do not force it to 4305 or 4375; a dedicated identity may be needed.
- **Question for user:** Should this row receive a new/existing ReportNormId, or intentionally remain source-only?

### Q002

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 0
- **Visible row label:** `NỢ PHẢI TRẢ`
- **Visible values/periods:** blank at both periods; structural heading, not zero.
- **Current status:** `SOURCE_ONLY_PDF_ROW`.
- **Candidate ReportNormId(s):** 4303 only as a weak diagnostic candidate.
- **Why unresolved:** 4303 is the broader umbrella `NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU`; the PDF splits liabilities and equity.
- **What Codex currently thinks:** retain source-only rather than distort 4303.
- **Question for user:** Is 4303 intentionally unpopulated for this split layout, or should this heading map to it?

### Q003

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 13
- **Visible row label:** `II. VỐN CHỦ SỞ HỮU`
- **Visible values/periods:** blank at both periods; structural heading.
- **Current status:** `SOURCE_ONLY_PDF_ROW`.
- **Candidate ReportNormId(s):** none admissible.
- **Why unresolved:** no schema item represents this section heading.
- **What Codex currently thinks:** retain source-only; never map it to a child value item.
- **Question for user:** Is this heading intentionally absent from the schema, or should it have a schema identity?

### Q004

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 22
- **Visible row label:** `Lợi ích của cổ đông không kiểm soát`
- **Visible values/periods:** 6.161.107 / 5.886.495 triệu đồng.
- **Current status:** visible row maps to 5699; schema item 4306 remains `UNRESOLVED`.
- **Candidate ReportNormId(s):** 5699, 4306.
- **Why unresolved:** the schema has two near-synonymous identities at different hierarchy positions.
- **What Codex currently thinks:** 5699 is structurally better; 4306 may be legacy or not applicable.
- **Question for user:** Which ID is authoritative, and should the other be deprecated, aliased, or kept distinct?

### Q005

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** main CDKT pages 3–4 versus quantitative notes
- **Visible row label:** fifteen schema details have no separate main-statement row.
- **Visible values/periods:** none on pages 3–4.
- **Current status:** `NOT_OBSERVED_IN_THIS_PDF` under the main-statement boundary.
- **Candidate ReportNormId(s):** the 15 IDs listed in the reconciliation header.
- **Why unresolved:** some details may occur only in notes; backfill would change the extraction boundary.
- **What Codex currently thinks:** keep CDKT and quantitative TM evidence separate unless the schema contract says otherwise.
- **Question for user:** May quantitative-note rows backfill CDKT IDs, or must CDKT use only the main statement?

### Q006

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 3, row 15
- **Visible row label:** `Chứng khoán đầu tư sẵn sàng để bán`
- **Visible values/periods:** 259.054.739 / 221.512.464 triệu đồng.
- **Current status:** mapped to 4350; supplied schema name says `...sẵn sàng để hàng`.
- **Candidate ReportNormId(s):** 4350.
- **Why unresolved:** mapping is clear, but the supplied schema appears to have a label typo.
- **What Codex currently thinks:** correct only the display name, not the identity.
- **Question for user:** May the schema/template name for 4350 be corrected from `để hàng` to `để bán`?

### Q012

- **Statement:** KQKD
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 6, logical row 12
- **Visible row label:** `TỔNG THU NHẬP HOẠT ĐỘNG`
- **Visible values/periods:** 17.430.206 / 15.322.697 triệu đồng for quarter current/comparative; the separately bound Q1 YTD pair repeats them.
- **Current status:** `SOURCE_ONLY_PDF_ROW` outside the 24-item denominator.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** the total is visible and accounting-valid, but the KQKD schema contains only its components.
- **What Codex currently thinks:** retain as provenance/validation unless a dedicated total identity is desired.
- **Question for user:** Should this total remain source-only, or should the schema add/identify a ReportNormId for it?

### Q013

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7
- **Visible row label:** `Tiền thu/(chi) bất động sản đầu tư`
- **Visible values/periods:** dash / dash for 01/01–31/03/2026 and comparative 2025.
- **Current status:** `SOURCE_ONLY_PDF_ROW`; schema IDs 4144/4145/4146 remain `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 4144, 4145, 4146.
- **Why unresolved:** the PDF presents one net/composite row; the schema separates purchase, sale proceeds and sale outflow.
- **What Codex currently thinks:** keep the composite row source-only and classify the three schema details as not observed unless the business contract defines a split.
- **Question for user:** Should this combined row map to one ID, remain source-only, or be split across the three IDs?

### Q014

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7
- **Visible row label:** `Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác`
- **Visible values/periods:** 490 / (71.299) triệu đồng for current/comparative duration.
- **Current status:** `SOURCE_ONLY_PDF_ROW`; schema IDs 4120/4121 remain `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 4120, 4121.
- **Why unresolved:** the PDF exposes one signed net row, while the schema separates cash paid and cash recovered.
- **What Codex currently thinks:** forcing the signed row into either directional ID loses the other business meaning.
- **Question for user:** Should the row map by sign to 4120/4121, remain source-only, or receive a net-flow schema identity?

### Q018

- **Statement:** LCTT
- **Document:** MBB consolidated Q1/2026, direct method
- **PDF page:** 7, row 24
- **Visible row label:** `Tăng/(Giảm) các công cụ tài chính phái sinh và các tài sản tài chính khác`
- **Visible values/periods:** (37.183) / 334.598 triệu đồng for current/comparative duration.
- **Current status:** `LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC`; values remain provenance-only.
- **Candidate ReportNormId(s):** 4140; 4131 is the earlier asset-side row and is already occupied.
- **Why unresolved:** both PP-OCR and DeepSeek read `tài sản tài chính khác`, while schema 4140 says `các khoản nợ tài chính khác`; the row sits inside the liability-change section.
- **What Codex currently thinks:** section/order favors 4140, but the visible/schema wording conflict is too material for automatic export.
- **Question for user:** Is the PDF wording an issuer typo/variant that should map to 4140, or should this row receive a different schema treatment?

## NEEDS_USER_REVIEW — NUMERIC CONFIRMATION

### Q010

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 11
- **Visible row label:** `Dự phòng các khoản nợ khác`
- **Visible values/periods:** current crop visibly reads 2.320; comparative is 2.188; triệu đồng.
- **Current status:** row maps to 4363; current-period value remains `UNRESOLVED_READER_DISAGREEMENT` in the sealed output.
- **Candidate ReportNormId(s):** 4363.
- **Why unresolved:** the sealed second reader returned `.20`, so exact agreement failed.
- **What Codex currently thinks:** 2.320 is correct. A targeted PP-OCR reread also produced 2.320, while the independent English numeric reader still drops the leading digit and the PDF page has no embedded text layer.
- **Question for user:** Please confirm whether the current-period value on this visible row is `2.320`.

### Q015

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 30, quantitative note for balances with the State Bank
- **Visible row label:** `Tiền gửi tại Ngân hàng Nhà nước Lào`
- **Visible values/periods:** 797.376 at 31/03/2026; 667.675 at 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP` in the first TM batch.
- **Candidate ReportNormId(s):** none identified in the current TM schema branch.
- **Why unresolved:** the schema exposes the aggregate State-Bank balance but no country-level child matching this visible row.
- **What Codex currently thinks:** keep the country row as provenance and map only the aggregate unless a country-detail identity exists.
- **Question for user:** Should this country row remain source-only, or is there an existing ReportNormId that should receive it?

### Q016

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 30, quantitative note for balances with the State Bank
- **Visible row label:** `Tiền gửi tại Ngân hàng Quốc gia Campuchia`
- **Visible values/periods:** 1.426.377 at 31/03/2026; 1.590.858 at 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP` in the first TM batch.
- **Candidate ReportNormId(s):** none identified in the current TM schema branch.
- **Why unresolved:** the schema exposes the aggregate State-Bank balance but no country-level child matching this visible row.
- **What Codex currently thinks:** preserve it separately; its values participate correctly in the aggregate equation.
- **Question for user:** Should this country row remain source-only, or is there an existing ReportNormId that should receive it?

### Q017

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 30, quantitative note for placements/loans to other credit institutions
- **Visible row label:** `Dự phòng rủi ro`
- **Visible values/periods:** (10.785) at 31/03/2026; (9.096) at 31/12/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 590, 583.
- **Why unresolved:** both schema labels describe provisions for balances with other credit institutions; the visible row is shorter than either schema label.
- **What Codex currently thinks:** 590 is stronger by row placement and exact subtotal equations; 583 remains a plausible semantic alternative.
- **Question for user:** Which ReportNormId is authoritative for this visible provision row: 590 or 583?

### Q019

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32
- **Visible row label:** `Công ty TNHH trên 1 Thành viên vốn Nhà nước lớn hơn 50%`
- **Visible values/periods:** 4.853.278 (0,43%) at 31/03/2026; 4.337.893 (0,40%) at 31/12/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 770.
- **Why unresolved:** schema 770 says `Công ty TNHH MTV vốn nhà nước trên 50%`, while the PDF explicitly says more than one member.
- **What Codex currently thinks:** the schema label may be stale or too narrow; automatic mapping is withheld.
- **Question for user:** Should this row map to 770, should label 770 be corrected, or is this a schema gap?

### Q020

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32–33
- **Visible row label:** `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- **Visible values/periods:** 8.815.772 (0,79%) at 31/03/2026; 9.330.629 (0,86%) at 31/12/2025; triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 765.
- **Why unresolved:** schema 765 `Nước ngoài` is under geographic analysis, while the visible concept may mean reporting-unit location.
- **What Codex currently thinks:** 765 is plausible but not safe enough for automatic export.
- **Question for user:** Is this row the authoritative value for ReportNormId 765?

### Q021

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 33
- **Visible row label:** `Giáo dục & Đào tạo`; `Y tế & hoạt động trợ giúp xã hội`
- **Visible values/periods:** 2.689.938 / 2.583.338 and 8.122.254 / 7.888.432 triệu đồng; current/comparative percentages 0,24%/0,24% and 0,72%/0,73%.
- **Current status:** `AMBIGUOUS_COMPOSITE`.
- **Candidate ReportNormId(s):** 737.
- **Why unresolved:** the PDF splits two industries, while schema 737 combines education and health.
- **What Codex currently thinks:** aggregate to 10.812.192 / 10.471.770 triệu đồng and 0,96% / 0,97%, without selecting either source row alone.
- **Question for user:** Should ReportNormId 737 receive this aggregate?

### Q022

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 33
- **Visible row label:** arts; other services; household employment activities.
- **Visible values/periods:** 1.531.664 / 1.708.707; 818.537 / 820.530; 264.294.420 / 239.172.416 triệu đồng, respectively.
- **Current status:** `AMBIGUOUS_CROSSWALK`.
- **Candidate ReportNormId(s):** 739, 745.
- **Why unresolved:** the PDF has three current sector rows but the older schema has two broader buckets.
- **What Codex currently thinks:** aggregate arts plus other services to 739 (2.350.201 / 2.529.237); map household employment to 745.
- **Question for user:** Please confirm this crosswalk and aggregation.

### Q023

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 34, FY2025 movement panel
- **Visible row label:** `Điều chỉnh theo Kiểm toán Nhà nước`
- **Visible values/periods:** specific provision 33.942; general provision (1.444); combined 32.498 triệu đồng.
- **Current status:** `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 798, 790.
- **Why unresolved:** the schema exposes only generic `Điều chỉnh khác` rows for the two provision types.
- **What Codex currently thinks:** map the specific/general components to 798/790, but retain the combined value as validation only.
- **Question for user:** Is `Điều chỉnh theo Kiểm toán Nhà nước` an allowed instance of schema `Điều chỉnh khác` for 798 and 790?

### Q024

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 34
- **Visible row label:** provision movements split by `Tại Việt Nam`, `Tại nước ngoài` and `Tổng cộng`.
- **Visible values/periods:** 77 auxiliary value/status slots across Q1/2026 and FY2025 panels.
- **Current status:** `SOURCE_ONLY_DIMENSION`.
- **Candidate ReportNormId(s):** 785–799 already represent the overall specific/general measures, not geography.
- **Why unresolved:** the schema has no geographic axis for this movement table.
- **What Codex currently thinks:** export only overall `Tổng cộng` specific/general values; retain domestic/foreign and combined columns as provenance and equation checks.
- **Question for user:** Is excluding the geographic subaxes from schema Excel intentional?

### Q025

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 35
- **Visible row label:** `Chứng khoán nợ do Chính phủ bảo lãnh`
- **Visible values/periods:** 22.128.777 at 31/03/2026; 22.204.008 at 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** 807 only as a weak aggregate candidate.
- **Why unresolved:** the PDF separates government-issued and government-guaranteed debt, while schema 807 names only government-issued debt.
- **What Codex currently thinks:** do not merge automatically; merging would make 807 equal 63.184.334 / 63.880.125 triệu đồng.
- **Question for user:** Should this row get a new/existing ID, be aggregated into 807, or remain source-only?

### Q026

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 35
- **Visible row label:** `Lãi của khoản nợ đã mua`
- **Visible values/periods:** dash / dash at 31/03/2026 and 31/12/2025.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** schema branch 800–803 has no interest child.
- **What Codex currently thinks:** retain the explicit dashes in provenance only.
- **Question for user:** Is this row intentionally source-only, or does it require a ReportNormId?

### Q027

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32–33
- **Visible row label:** percentage columns accompanying every loan-analysis row.
- **Visible values/periods:** 88 percentage cells across current and comparative snapshot axes.
- **Current status:** `SOURCE_ONLY_MEASURE`.
- **Candidate ReportNormId(s):** same item IDs as the amount rows; no percentage-specific schema IDs.
- **Why unresolved:** the target template has no explicit measure dimension distinguishing amount from percentage.
- **What Codex currently thinks:** export VND amounts only and retain percentages as provenance/accounting checks.
- **Question for user:** Should percentage values remain provenance-only?

### Q028

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 31, repeated on the maturity table and pages 32–33
- **Visible row label:** unlabeled bank-only loan subtotal before MBS margin/advance loans.
- **Visible values/periods:** 1.105.042.109 at 31/03/2026; 1.068.978.785 at 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** 716 is not suitable because it is the consolidated total including ReportNormId 1944.
- **Why unresolved:** the subtotal is visible and accounting-valid but has no distinct schema identity.
- **What Codex currently thinks:** keep it as validation; subtotal + 1944 = root 716.
- **Question for user:** Does this bank-only subtotal need a distinct ReportNormId?

### Q029

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 32
- **Visible row label:** `Cho vay các TCKT`; `Cho vay khác`; foreign-business loans; foreign-personal loans.
- **Visible values/periods:** 635.708.290 / 621.056.253; 836.450 / 904.945; 1.891.644 / 2.176.885; 6.924.128 / 7.153.744 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROWS`.
- **Candidate ReportNormId(s):** none exact; structural 766 and ambiguous parent 765 are not substitutes.
- **Why unresolved:** the PDF provides useful subtotal/detail concepts not represented exactly by current schema leaves.
- **What Codex currently thinks:** retain these as aggregation provenance and map their represented children where exact IDs exist.
- **Question for user:** Should any existing ReportNormId receive these four visible concepts?

### Q030

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 36, note 9
- **Visible row label:** `Dự phòng giảm giá`
- **Visible values/periods:** (91.228) at both 31/03/2026 and 31/12/2025; triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none in branch 862–867; 849 belongs to a different note and is not reusable.
- **Why unresolved:** the branch has gross 867 and net 862 but no provision child.
- **What Codex currently thinks:** retain source-only; it exactly validates gross plus provision equals net.
- **Question for user:** Is there an existing ID for this provision, should one be added, or is source-only intentional?

### Q031

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 36, note 9.1
- **Visible row label:** `Đầu tư vào tổ chức kinh tế, dự án dài hạn`; `Đầu tư vào các Quỹ đầu tư`
- **Visible values/periods:** 492.584 / 493.184 and 66.550 / 66.440 triệu đồng at current/comparative snapshots.
- **Current status:** `SOURCE_ONLY_DETAIL` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none exact; 867 is their aggregate only.
- **Why unresolved:** schema branch 862–867 has no matching child identities.
- **What Codex currently thinks:** map gross aggregate 867 and retain both details as provenance.
- **Question for user:** Should either detail receive an existing/new ReportNormId, or are both intentionally source-only?

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

### Q034

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38
- **Visible row label:** tangible gross-cost and accumulated-depreciation `Chênh lệch tỷ giá`
- **Visible values/periods:** page 37 totals 565 / 162; page 38 totals 8.606 / 2.225 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none exact under parents 869 and 883.
- **Why unresolved:** the schema has no FX movement leaf under either parent.
- **What Codex currently thinks:** these appear to be two missing movement identities.
- **Question for user:** Add/expose FX IDs under each parent, or keep these rows source-only?

### Q035

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 38
- **Visible row label:** `Điều chỉnh theo Kiểm toán Nhà nước` under accumulated depreciation
- **Visible values/periods:** total 1.221 triệu đồng; only the machinery/equipment class has value, other classes show dash.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** 887 only weakly as `Tăng khác`.
- **Why unresolved:** a named audit adjustment is not an exact match for the generic schema concept.
- **What Codex currently thinks:** do not force 887.
- **Question for user:** Map to 887, add a dedicated ID, or keep source-only?

### Q036

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 37–38
- **Visible row label:** tangible fixed-asset `Giá trị còn lại` at opening and closing
- **Visible values/periods:** page 38 total 3.750.696 → 3.805.533; page 37 total 3.805.533 → 3.717.028 triệu đồng.
- **Current status:** `SOURCE_ONLY_VALIDATION` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** the schema has cost/depreciation movements but no net-book-value opening/closing leaves.
- **What Codex currently thinks:** retain as exact gross-minus-accumulated validation.
- **Question for user:** Is validation-only intended, or should net-book-value IDs be added?

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

### Q040

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40
- **Visible row label:** intangible gross-cost and accumulated-amortization `Chênh lệch tỷ giá`
- **Visible values/periods:** page 39 totals 159 / 44; page 40 totals 1.263 / 391 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none under parents 914 and 929.
- **Why unresolved:** the schema has no FX movement leaf for either roll-forward.
- **What Codex currently thinks:** two movement identities appear missing.
- **Question for user:** Add/expose FX IDs under each parent, or keep source-only?

### Q041

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 39–40
- **Visible row label:** intangible fixed-asset `Giá trị còn lại` at opening and closing
- **Visible values/periods:** page 40 total 1.679.720 → 1.811.014; page 39 opens at 1.811.014 and closes at 1.783.634 triệu đồng.
- **Current status:** `SOURCE_ONLY_VALIDATION` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** the schema lacks net-book-value opening/closing leaves.
- **What Codex currently thinks:** retain as exact cost-minus-amortization and cross-page continuity validation.
- **Question for user:** Keep validation-only, or add net-book-value IDs?

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

### Q044

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 41
- **Visible row label:** investment-property `Giá trị còn lại` at opening and closing
- **Visible values/periods:** current panel 222.813 → 216.314; FY2025 234.115 → 222.813 triệu đồng.
- **Current status:** `SOURCE_ONLY_VALIDATION` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none.
- **Why unresolved:** schema lacks net-book-value opening/closing leaves.
- **What Codex currently thinks:** retain as exact gross-minus-depreciation validation.
- **Question for user:** Add net-book-value IDs or intentionally keep validation-only?

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

### Q046

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 42, note 13
- **Visible row label:** `Phải thu liên quan đến dịch vụ thanh toán`; `Phải thu miễn truy đòi theo bộ chứng từ`
- **Visible values/periods:** 861.287 / 1.525.624 and 11.281.653 / 8.046.079 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROWS` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none exact; 981 is occupied by explicit `Các khoản phải thu khác`.
- **Why unresolved:** current schema has no matching child identities.
- **What Codex currently thinks:** preserve separately and never double-map to 981.
- **Question for user:** Do these rows need existing/new IDs, or are they intentionally source-only?

### Q047

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 42, note 14
- **Visible row label:** `Tài sản Có khác`
- **Visible values/periods:** total 6.622.398 / 7.894.091 triệu đồng.
- **Current status:** `AMBIGUOUS_DUPLICATE_NAME`.
- **Candidate ReportNormId(s):** 966, 987.
- **Why unresolved:** the schema has broad 966 and nested duplicate 987; visible children 989 and 997 sum exactly to the total.
- **What Codex currently thinks:** child context strongly favors 987.
- **Question for user:** Confirm the total maps to 987 and 966 remains not observed?

### Q048

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 43, note 17
- **Visible row label:** `Tiền gửi của TCKT`; `Tiền gửi của cá nhân`
- **Visible values/periods:** 365.071.880 / 402.397.512 and 540.846.452 / 518.970.620 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW` / `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** none for TCKT aggregate; 1089 for personal deposits.
- **Why unresolved:** schema lacks the TCKT aggregate, while 1089 is broader (`Hộ kinh doanh, cá nhân`).
- **What Codex currently thinks:** keep TCKT provenance-only and map personal to 1089 only with confirmation.
- **Question for user:** Confirm 1089 and whether the TCKT aggregate needs an ID?

### Q049

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 43, note 18 derivatives
- **Visible row label:** net carrying-value columns for total, forward and swap contracts
- **Visible values/periods:** current (661.326)/(150.745)/(510.581); prior (698.507)/(19.293)/(679.214) triệu đồng.
- **Current status:** `SOURCE_ONLY_MEASURE` / `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none; branch 631–715 has contract/asset/liability identities only.
- **Why unresolved:** schema lacks the visible net measure.
- **What Codex currently thinks:** preserve as validation/provenance.
- **Question for user:** Keep source-only or add net-value IDs?

### Q050

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 44, note 20
- **Visible row label:** bond and certificate-of-deposit maturity buckets
- **Visible values/periods:** bond `<5y` 24.009.801 / 23.039.165; CD `≤12m` 85.267.048 / 76.253.073; CD `>12m` 79.970.220 / 64.577.077 triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROWS` / `AMBIGUOUS_BUCKETS`.
- **Candidate ReportNormId(s):** 1110/1111; 1102; 1103/1104.
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

### Q052

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 44, quantitative narrative disclosures
- **Visible row label:** own-bond/CD rates; issued shares; par value; stated capital
- **Visible values/periods:** 5,00–8,80%/year; 4,40–11,18%; 8.054.999.909 shares; 10.000 VND/share; 80.549.999 triệu đồng.
- **Current status:** `SOURCE_ONLY_QUANTITATIVE_FACTS`.
- **Candidate ReportNormId(s):** none native; capital cross-validates the table within rounding.
- **Why unresolved:** schema lacks quantitative fields for these narratives.
- **What Codex currently thinks:** retain as provenance/validation.
- **Question for user:** Keep source-only or add quantitative IDs?

### Q053

- **Statement:** TM
- **Document:** MBB consolidated Q1/2026
- **PDF page:** 45, notes 22.2–22.3
- **Visible row label:** EPS and share-count disclosure family
- **Visible values/periods:** profit 7.515.513 / 6.567.740 triệu đồng; weighted shares 8.054.999.909; EPS 933/815 VND/share; sold/outstanding/common shares 8.054.999.909; repurchased/preferred dash; registered shares blank.
- **Current status:** `POSSIBLE_SCHEMA_GAP`.
- **Candidate ReportNormId(s):** none in the current 1.385-item schema; profit only cross-validates 1131.
- **Why unresolved:** the full disclosure family is absent and rows use different units; blank, dash and zero are distinct.
- **What Codex currently thinks:** preserve it source-only unless the template is extended.
- **Question for user:** Add EPS/share-class IDs or keep source-only, and are the registered-share blanks intentional?

## CODEX_STILL_INVESTIGATING

- **TM:** pages 30–45 have been itemized or audited. Codex is continuing pages 46–61 and will promote only evidence-backed rows from audit candidates into mapping/Excel.

## RESOLVED_BY_CODEX

- **Q007 / 4329:** finance-lease fixed asset is `NOT_OBSERVED_IN_THIS_PDF`; visible rows belong to tangible/intangible parents.
- **Q008 / 4369:** finance-lease original cost is `NOT_OBSERVED_IN_THIS_PDF`; parent-subtype gating removed the false candidate.
- **Q009 / 4370:** finance-lease accumulated depreciation is `NOT_OBSERVED_IN_THIS_PDF`; parent-subtype gating removed the false candidate.
- **Q011 / scope:** visible title evidence binds MBB Q1/2026 to `CONSOLIDATED`; the older sealed E-0041 receipt remains unchanged and still records its historical `UNKNOWN` value.
- **LCTT 40 one-to-one rows:** resolved algorithmically by exact row order plus independent PP-OCR and DeepSeek semantic agreement; they are now `MAPPED`. The two composite rows, five composite candidate IDs and one label conflict remain unresolved in Q013–Q014 and Q018.
- **TM page 31 MBS row:** ReportNormId 1944 is an approved appended schema item matching `cho vay margin chứng khoán và ứng trước`; one primary occurrence maps there and repeats remain validation-only.
- **TM page 31 duplicate totals:** gross securities maps to 626, provision to 627, net to root 592 and consolidated loan total to 716; repeated subtotals/totals are retained only for zero-residual checks, not double-mapped.
