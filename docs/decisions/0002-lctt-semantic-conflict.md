# Decision 0002: bind LCTT semantic branches by template order

Status: resolved by the user on 2026-08-06 (`Q-BOOT-001`)

The supplied LCTT workbook places the profit-before-tax/adjustment block at workbook positions 1–57, with endpoint IDs 4155→4168. It places the cash receipt/payment block at positions 58–107, with endpoint IDs 4104→4116; ID 4154 is an interior item at position 63. Therefore integer comparisons such as `4104 <= id <= 4154` are forbidden for branch membership.

The authoritative resolution is: workbook positions 1–57, with endpoints 4155→4168 and the profit-before-tax/adjustment anchors, are `INDIRECT`; positions 58–107, with endpoints 4104→4116 and the cash-received/cash-paid anchors, are `DIRECT`. The endpoints describe slices in template display order and must never be interpreted as numeric intervals.

`config/mapping/lctt-v2.yaml` records the resolved policy. Historical `lctt.yaml` and E-0010/E-0011/E-0013 artifacts retain their original fail-closed state so their hashes and claims remain reproducible. Resolution permits a PDF method classified as DIRECT or INDIRECT to select the same-named workbook block; it does not promote OCR cells, resolve an UNKNOWN/CONFLICT filing, or relax schema/value/period/unit/sign/provenance gates.
