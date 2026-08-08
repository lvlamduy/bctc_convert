from __future__ import annotations

import datetime as datetime_module
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from bctc_ai.export.cdkt_development import (
    CDKTDevelopmentExportError,
    build_cdkt_development_artifacts,
    export_cdkt_development,
)

_TEMPLATE = Path("template/Bank_CDKT_ReportNormId.v2.xlsx")
_SEALED = Path(
    "output/calibration/e0041-mbb-cdkt-post-mapping-development-excel/mbb-cdkt-development.xlsx"
)


def _build(project_root: Path):
    return build_cdkt_development_artifacts(
        template_path=project_root / _TEMPLATE,
        sealed_workbook_path=project_root / _SEALED,
        workbook_name="mbb-cdkt-development.xlsx",
    )


def _headers(sheet) -> dict[str, int]:
    return {str(sheet.cell(1, column).value): column for column in range(1, sheet.max_column + 1)}


def test_cdkt_business_update_reconciles_78_items_and_preserves_source_statuses(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from openpyxl.writer import excel as excel_writer

    save_clock = iter(
        (
            datetime_module.datetime(2030, 1, 2, 3, 4, 5),
            datetime_module.datetime(2040, 6, 7, 8, 9, 10),
        )
    )

    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            value = next(save_clock)
            return value.replace(tzinfo=tz) if tz is not None else value

    monkeypatch.setattr(
        excel_writer,
        "datetime",
        SimpleNamespace(datetime=FakeDateTime, timezone=datetime_module.timezone),
    )
    first = _build(project_root)
    second = _build(project_root)
    assert first.workbook_bytes == second.workbook_bytes
    assert first.coverage_bytes == second.coverage_bytes
    assert (first.observed_value_count, first.derived_value_count, first.exported_value_count) == (
        114,
        2,
        116,
    )
    assert first.fully_verified is False

    coverage = json.loads(first.coverage_bytes)
    assert coverage["coverage"] == {
        "derived_value_count": 2,
        "exported_value_count": 116,
        "mapped_schema_count": 62,
        "not_observed_schema_count": 16,
        "observed_value_count": 114,
        "physical_cell_count": 128,
        "physical_status_counts": {"BLANK": 9, "DASH": 5, "VALUE": 114},
        "reconciled_schema_count": 78,
        "source_row_count": 64,
    }
    assert coverage["decisions"]["Q010"]["canonical_value_vnd"] == 2_320_000_000
    assert coverage["formula_checks"] == {
        "4305_equals_4304_plus_5712": {"passed": True},
        "4325_components": {"passed": True, "status": "DERIVED_FROM_COMPONENTS"},
        "5712_equals_4325_plus_4306": {
            "passed": True,
            "status": "VISIBLE_TOTAL_WITH_4306_NOT_OBSERVED",
        },
    }

    template = load_workbook(project_root / _TEMPLATE, data_only=False)
    workbook = load_workbook(BytesIO(first.workbook_bytes), data_only=False)
    try:
        assert workbook.properties.created == datetime_module.datetime(2000, 1, 1)
        assert workbook.properties.modified == datetime_module.datetime(2000, 1, 1)
        assert workbook.sheetnames == [
            "CDKT",
            "PROVENANCE",
            "VALIDATION_DIAGNOSTICS",
            "RUN_METADATA",
        ]
        main = workbook["CDKT"]
        for row in range(1, 80):
            for column in range(1, 4):
                assert main.cell(row, column).value == template.active.cell(row, column).value
                assert main.cell(row, column).style_id == template.active.cell(row, column).style_id
        by_id = {main.cell(row, 2).value: row for row in range(2, 80)}
        assert len(by_id) == 78
        assert main.cell(by_id[4350], 3).value == "Chứng khoán đầu tư sẵn sàng để bán"
        assert main.cell(by_id[4363], 4).value == 2_320_000_000
        assert main.cell(by_id[4363], 6).value == "VALUE"
        assert main.cell(by_id[4306], 6).value == "NOT_OBSERVED_IN_THIS_PDF"
        assert main.cell(by_id[4325], 4).value == 149_745_325_000_000
        assert main.cell(by_id[4325], 6).value == "DERIVED_FROM_COMPONENTS"
        assert main.cell(by_id[5712], 4).value == 149_745_325_000_000
        assert main.cell(by_id[5712], 5).value == 142_022_525_000_000
        assert (
            main.cell(by_id[4304], 4).value + main.cell(by_id[5712], 4).value
            == main.cell(by_id[4305], 4).value
        )
        assert (
            sum(
                main.cell(row, column).value is not None
                for row in range(2, 80)
                for column in (4, 5)
            )
            == 116
        )

        provenance = workbook["PROVENANCE"]
        headers = _headers(provenance)
        records = [
            {name: provenance.cell(row, column).value for name, column in headers.items()}
            for row in range(2, provenance.max_row + 1)
        ]
        p4r0 = [record for record in records if record["RowId"] == "page-0004-row-000-label"]
        p4r13 = [record for record in records if record["RowId"] == "page-0004-row-013-label"]
        p4r23 = [record for record in records if record["RowId"] == "page-0004-row-023-label"]
        assert {record["ReportNormId"] for record in p4r0} == {4304}
        assert {record["Status"] for record in p4r0} == {"BLANK"}
        assert {record["ReportNormId"] for record in p4r13} == {5712}
        assert {record["Status"] for record in p4r13} == {"BLANK"}
        assert {record["ReportNormId"] for record in p4r23} == {5712}
        assert {record["Status"] for record in p4r23} == {"VALUE"}
        confirmed = next(
            record
            for record in records
            if record["RowId"] == "page-0004-row-011-label" and record["AxisOrdinal"] == 0
        )
        assert confirmed["ExportedCanonicalValue"] == 2_320_000_000
        assert confirmed["NumericVerificationStatus"] == "USER_CONFIRMED_VISIBLE_VALUE"
        assert all(record["Scope"] == "CONSOLIDATED" for record in records)

        assert not any(
            cell.data_type == "f" or (isinstance(cell.value, str) and cell.value.startswith("="))
            for sheet in workbook.worksheets
            for row in sheet.iter_rows()
            for cell in row
        )
    finally:
        workbook.close()
        template.close()


def test_cdkt_export_refuses_overwrite_and_schema_identity_drift(
    tmp_path: Path,
    project_root: Path,
):
    workbook_path = tmp_path / "mbb-cdkt-development.xlsx"
    coverage_path = tmp_path / "coverage.json"
    result = export_cdkt_development(
        template_path=project_root / _TEMPLATE,
        sealed_workbook_path=project_root / _SEALED,
        workbook_path=workbook_path,
        coverage_path=coverage_path,
    )
    assert workbook_path.stat().st_size == result.workbook_size_bytes
    assert coverage_path.stat().st_size == result.coverage_size_bytes
    with pytest.raises(CDKTDevelopmentExportError, match="already exists"):
        export_cdkt_development(
            template_path=project_root / _TEMPLATE,
            sealed_workbook_path=project_root / _SEALED,
            workbook_path=workbook_path,
            coverage_path=coverage_path,
        )

    template = load_workbook(project_root / _TEMPLATE)
    template.active.cell(78, 2, 999_999)
    drift_path = tmp_path / "drift.xlsx"
    template.save(drift_path)
    template.close()
    with pytest.raises(CDKTDevelopmentExportError, match="business-schema identities"):
        build_cdkt_development_artifacts(
            template_path=drift_path,
            sealed_workbook_path=project_root / _SEALED,
            workbook_name="mbb-cdkt-development.xlsx",
        )
