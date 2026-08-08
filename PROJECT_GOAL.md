# Project goal

## One end state

Input: one or more scanned, born-digital, or mixed Vietnamese bank financial-report PDFs.

Output: a complete Excel workbook derived from the evolving `UNIVERSAL_BANK_BCTC_SCHEMA` and recording the correct value, period, unit, sign, statement, scope, section, and cell-level provenance for every accepted observation. The supplied 1,593-item template is the stable `BASE_SCHEMA`, not a closed universe.

The current statement scope is CDKT, KQKD, the applicable LCTT branch, and quantitative TM. CSTC is excluded unless the user changes scope.

## Definition of done

A production run is complete only when all of the following are evidenced:

1. Inputs, code, config, model, and outputs have stable hashes and a run manifest.
2. Source PDFs remain unchanged and are the final authority.
3. OCR/layout/table extraction is reproducible from page checkpoints.
4. Period, unit, sign, scope, row, column, and schema binding are independently represented.
5. Every exported value has page/table/row/cell geometry and source-image provenance.
6. Blank, zero, dash, not applicable, and not observed remain distinct.
7. Uncertain or conflicting results fail closed to review or unresolved.
8. Role A machine reference and Role B production are isolated during frozen evaluation.
9. Applicable coverage and full-tuple accuracy are measured per statement and TM group against an explicit denominator.
10. The output workbook preserves every accepted ReportNormId and accounting meaning, uses explicit universal `DisplayOrder`/`ParentId`, represents evidence-backed additions, and includes PROVENANCE, REVIEW, UNRESOLVED, QUESTIONS, SCHEMA_ADDITIONS, and RUN_METADATA.
11. A versioned off-machine backup, MongoDB dump where applicable, and restore test all pass.

## Non-goals

- Reconstructing the lost implementation line by line.
- Treating MongoDB, an OCR model, a VLM, or an accounting equation as truth.
- Maximizing raw mappings at the cost of accuracy or traceability.
- Tuning on an untouched holdout.
