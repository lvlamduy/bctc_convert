# Decision 0002: defer LCTT semantic branch labels

Status: reopened on 2026-08-05 after direct workbook inspection (`Q-BOOT-001`)

The supplied LCTT workbook places the profit-before-tax/adjustment block at workbook positions 1–57, with endpoint IDs 4155→4168. It places the cash receipt/payment block at positions 58–107, with endpoint IDs 4104→4116; ID 4154 is an interior item at position 63. Therefore integer comparisons such as `4104 <= id <= 4154` are forbidden for branch membership.

The user's earlier examples call 4162→4156 indirect and 4123→4124 direct. The latest response says 4104–4154 is indirect and 4155–4168 is direct while emphasizing workbook order. Those statements conflict with each other and with the visible row semantics/direct-title hierarchy workbook. The implementation preserves the two contiguous blocks and fails closed for semantic high-confidence acceptance until the labels/endpoints are reconciled.
