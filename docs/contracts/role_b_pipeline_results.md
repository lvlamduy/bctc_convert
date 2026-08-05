# Role B pipeline-result contract

Role B contains the same observable tuple as Role A plus candidate list and score, selected schema, model votes, acceptance gate, rejection reason, validation status, and workbook cell. Frozen Role B processes cannot read Role A results.

`pipeline_vs_reference.csv` reports candidate presence, schema agreement, exact value, period, unit, sign, page, full tuple, missing, extra, and calibration metrics.
