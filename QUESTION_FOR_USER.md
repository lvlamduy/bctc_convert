# Questions for user — current financial-statement ambiguities

Updated: 2026-08-08

- **CDKT unresolved/review-worthy:** 11 tracked issues — 6 `NEEDS_USER_REVIEW`, 5 `CODEX_STILL_INVESTIGATING`.
- **KQKD unresolved:** 0 enumerated; 24 schema items are not yet item-level assessed.
- **LCTT unresolved:** 0 enumerated; 107 schema items are not yet item-level assessed.
- **TM unresolved:** 0 enumerated; 1,385 schema items are not yet item-level assessed.

CDKT schema reconciliation is exact: `77 = 61 MAPPED + 12 NOT_OBSERVED_IN_THIS_PDF + 3 AMBIGUOUS_MAPPING + 1 UNRESOLVED`. The three source-only PDF rows below are outside that 77-item denominator. The 12 confidently not-observed IDs are `4344, 4326, 4345, 4333, 4309, 4303, 4359, 4360, 4373, 4340, 4374, 4341`.

## NEEDS_USER_REVIEW

### Q001

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 23
- **Visible row label:** `TỔNG VỐN CHỦ SỞ HỮU`
- **Visible values/periods:** 149.745.325 at 31/03/2026; 142.022.525 at 31/12/2025; unit triệu đồng.
- **Current status:** `SOURCE_ONLY_PDF_ROW`; strong `POSSIBLE_SCHEMA_GAP` outside the 77-item denominator.
- **Candidate ReportNormId(s):** none; 4305 is already correctly used by the following grand-total row.
- **Why unresolved:** the 77-item CDKT schema has no distinct total-equity item, although both accounting equations reproduce the visible values exactly.
- **What Codex currently thinks:** do not force this row to 4305 or 4375; a dedicated schema identity is likely needed if this subtotal belongs in the output.
- **Question for user:** Should this row receive a new/existing business ReportNormId, or intentionally remain source-only?

### Q002

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 0
- **Visible row label:** `NỢ PHẢI TRẢ`
- **Visible values/periods:** blank at both 31/03/2026 and 31/12/2025; structural heading, not zero.
- **Current status:** `SOURCE_ONLY_PDF_ROW`.
- **Candidate ReportNormId(s):** 4303 only as a weak diagnostic candidate.
- **Why unresolved:** schema 4303 is the broader umbrella `NỢ PHẢ TRẢ VÀ VỐN CHỦ SỞ HỮU`, while the PDF splits liabilities and equity into separate headings.
- **What Codex currently thinks:** retain this heading as source-only rather than collapsing it into 4303.
- **Question for user:** Is 4303 meant to stay unpopulated for this split layout, or should this heading map to it?

### Q003

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 13
- **Visible row label:** `II. VỐN CHỦ SỞ HỮU`
- **Visible values/periods:** blank at both periods; structural heading, not zero.
- **Current status:** `SOURCE_ONLY_PDF_ROW`.
- **Candidate ReportNormId(s):** none admissible; 4303 is only a weak diagnostic match.
- **Why unresolved:** no schema item represents this separate section heading.
- **What Codex currently thinks:** retain source-only; do not map to a child value item.
- **Question for user:** Is this heading intentionally absent from the schema, or should it have a schema identity?

### Q004

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 22
- **Visible row label:** `Lợi ích của cổ đông không kiểm soát`
- **Visible values/periods:** 6.161.107 at 31/03/2026; 5.886.495 at 31/12/2025; unit triệu đồng.
- **Current status:** visible row is mapped to 5699; schema item 4306 remains `UNRESOLVED`.
- **Candidate ReportNormId(s):** 5699 and 4306.
- **Why unresolved:** the schema contains two near-synonymous identities at different hierarchy positions.
- **What Codex currently thinks:** 5699 is structurally better because the row is inside `Vốn và các quỹ`; 4306 may be legacy/not-applicable.
- **Question for user:** Which ID is authoritative, and should the other be deprecated, an alias, or a distinct item?

### Q005

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** main CDKT pages 3–4 versus quantitative notes
- **Visible row label:** twelve schema details have no separate row on pages 3–4.
- **Visible values/periods:** none on the main statement.
- **Current status:** `NOT_OBSERVED_IN_THIS_PDF` for the main-statement boundary.
- **Candidate ReportNormId(s):** 4344, 4326, 4345, 4333, 4309, 4303, 4359, 4360, 4373, 4340, 4374, 4341.
- **Why unresolved:** some details may occur only in notes; importing them into CDKT would change the extraction boundary.
- **What Codex currently thinks:** keep main-statement CDKT and quantitative TM evidence separate unless the schema contract explicitly requires note backfill.
- **Question for user:** Should CDKT values be populated only from the main statement, or may note-detail rows backfill these CDKT IDs?

### Q006

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 3, row 15
- **Visible row label:** `Chứng khoán đầu tư sẵn sàng để bán`
- **Visible values/periods:** 259.054.739 at 31/03/2026; 221.512.464 at 31/12/2025; unit triệu đồng.
- **Current status:** mapped to 4350; values verified, but schema display name says `...sẵn sàng để hàng`.
- **Candidate ReportNormId(s):** 4350.
- **Why unresolved:** the supplied schema appears to contain a label typo; schema edits require explicit authority.
- **What Codex currently thinks:** mapping is correct and only the display name is wrong.
- **Question for user:** May the schema/template name for 4350 be corrected from `để hàng` to `để bán`?

## CODEX_STILL_INVESTIGATING

### Q007

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 3, rows 23 and 26
- **Visible row label:** `Tài sản cố định hữu hình`; `Tài sản cố định vô hình`.
- **Visible values/periods:** 3.717.028/3.805.533 and 1.783.634/1.811.014 triệu đồng.
- **Current status:** schema item 4329 `Tài sản cố định thuê tài chính` is `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 4329 against source rows already mapped to 4328 and 4330.
- **Why unresolved:** generic `Tài sản cố định` tokens create a candidate despite the visible subtype mismatch.
- **What Codex currently thinks:** 4329 is `NOT_OBSERVED_IN_THIS_PDF`; subtype/parent gating should remove the false candidate.
- **Question for user:** No action required yet; please flag only if a finance-lease row is visibly present on page 3.

### Q008

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 3, rows 24–25 and 27–28
- **Visible row label:** two `Nguyên giá tài sản cố định` rows under the visible tangible/intangible parents.
- **Visible values/periods:** 9.473.484/9.423.236 and 5.762.160/5.684.904 triệu đồng.
- **Current status:** schema item 4369 `Nguyên giá tài sản cố định thuê tài chính` is `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 4369.
- **Why unresolved:** the child label lacks the subtype text; current candidate scoring underweights the physical parent subtype.
- **What Codex currently thinks:** 4369 is not observed; enforce parent-path subtype consistency.
- **Question for user:** No action required yet; Codex is fixing the structural gate.

### Q009

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 3, rows 25 and 28
- **Visible row label:** two `Hao mòn tài sản cố định` rows under tangible/intangible parents.
- **Visible values/periods:** (5.756.456)/(5.617.703) and (3.978.526)/(3.873.890) triệu đồng.
- **Current status:** schema item 4370 `Giá trị hao mòn lũy kế tài sản cố định thuê tài chính` is `AMBIGUOUS_MAPPING`.
- **Candidate ReportNormId(s):** 4370.
- **Why unresolved:** same parent-subtype leakage as Q008.
- **What Codex currently thinks:** 4370 is not observed; require parent-path subtype consistency.
- **Question for user:** No action required yet; Codex is fixing the structural gate.

### Q010

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** 4, row 11
- **Visible row label:** `Dự phòng các khoản nợ khác`
- **Visible values/periods:** current crop visibly reads `2.320`; comparative is verified `2.188`; unit triệu đồng.
- **Current status:** row maps to 4363, but current-period value is `UNRESOLVED_READER_DISAGREEMENT` (`2.320` versus challenger `.20`).
- **Candidate ReportNormId(s):** 4363.
- **Why unresolved:** exact two-reader agreement fails even though the source crop visibly retains the leading digit.
- **What Codex currently thinks:** value is 2.320; add a bounded independent reread rather than weakening the general agreement rule.
- **Question for user:** No action required yet; Codex is testing a localized numeric fallback.

### Q011

- **Statement:** CDKT
- **Document:** MBB Q1/2026
- **PDF page:** statement title/page context
- **Visible row label:** title evidence contains `HỢP NHẤT`.
- **Visible values/periods:** 31/03/2026 current, 31/12/2025 comparative; unit triệu đồng.
- **Current status:** report scope remains `UNKNOWN` in the sealed output.
- **Candidate ReportNormId(s):** not applicable; candidate scopes are `CONSOLIDATED` and `SEPARATE`.
- **Why unresolved:** the current scope binder did not admit the visible title evidence into the final contract.
- **What Codex currently thinks:** scope should be `CONSOLIDATED`; fix and test the title-to-scope binding.
- **Question for user:** No action required yet; Codex is resolving this from visible evidence.
