# TM ReportNormID 1944 append record

## Authority and identity

Q-BOOT-004 was approved on 2026-08-06. The authorized row is:

```text
statement_type = TM
ReportNormID = 1944
ReportNormName = Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán
previous ReportNormID in workbook order = 1943
next ReportNormID = none
source row = 1386
zero-based display order = 1384
```

ReportNormID magnitude is identity only. It must never be used to sort or move
this or any other row. The approved action appended 1944 after the existing last
row; it did not reorder any earlier item.

## Preservation evidence

The append was performed at the XLSX XML-package level, not by reserializing the
whole workbook through an office library:

```text
before SHA-256 = 6af23d7bf930fe6db7cbfb83df78c7c7ab876142757d1dde5707c1667b54a8a0
after SHA-256  = fa284e3af1f90c8a206308f63e6d35e77a9fbf1abcaf60abcb59877c47275140
```

Only `xl/worksheets/sheet1.xml` and `xl/sharedStrings.xml` changed. The eight
other ZIP members retain their exact prior SHA-256. The canonical identity hash
over all 1,384 pre-existing workbook rows is unchanged. Full evidence is in
`data/registered/schema_append_1944.json`.

The `vst_level` workbook was deliberately not edited. Its final rows belong to a
liquidity-risk hierarchy, which is not evidence that 1944 shares that parent.
The new schema item therefore has `parent_id = null` and
`hierarchy_source = null` until an authoritative hierarchy source is supplied.

## Collision and consumer coverage

The pre-append audit found no ID 1944 collision in the baseline schema,
supporting hierarchy, MongoDB template collection, or selected historical raw/YTD
keys. After the authorized append, global schema uniqueness is checked again.

`config/schemas/coverage-v1.yaml` selects every template item in workbook order
for all five consumers:

- `ROLE_A`
- `ROLE_B`
- `EXCEL_OUTPUT`
- `EVALUATION`
- `MANDATORY_SEARCH`

At this `BASE_SCHEMA` checkpoint the contract contained 1,593 IDs and each
consumer ended with 1944. Later universal-schema additions preserve those
identities while extending the denominator and presentation order.
For each document, Role A and Role B must independently record exactly one
terminal search outcome for every target ID. A searched-but-absent 1944 is
`NOT_OBSERVED`; it is never zero. A visible dash is `DASH`, a verified empty
cell is `BLANK`, and only a printed numeric zero is `OBSERVED_ZERO`.

## Verification and rebuild

```bash
.venv/bin/python scripts/migration/append_tm_1944.py --verify-only
.venv/bin/python scripts/migration/refresh_schema_1944_artifacts.py
.venv/bin/pytest -q tests/unit/test_schema_registry.py \
  tests/unit/test_schema_coverage.py \
  tests/unit/test_hierarchy_reference.py \
  tests/unit/test_workbook_export.py
```

The append command is idempotent when the verified audit is present and fails
closed for an unknown workbook hash, changed predecessor, duplicate ID, altered
prefix, unexpected ZIP-member change, or mismatched final workbook identity.
