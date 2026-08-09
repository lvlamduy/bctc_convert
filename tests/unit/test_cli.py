from __future__ import annotations

from types import SimpleNamespace

import pytest

from bctc_ai.cli.main import build_parser
from bctc_ai.export import native_canonical_excel as canonical_export_module
from bctc_ai.export import native_rows as export_module


def test_history_index_cli_uses_uri_environment_and_safe_defaults():
    arguments = build_parser().parse_args(["history-index"])

    assert arguments.mongo_uri_env == "BCTC_HISTORY_MONGO_URI"
    assert arguments.output == "data/local/historical_weak_reference.duckdb"
    assert arguments.registry == "data/registered/historical_weak_reference_registry.json"
    assert arguments.replace is False


def test_history_index_cli_fails_before_build_when_uri_environment_is_missing(monkeypatch, capsys):
    monkeypatch.delenv("BCTC_HISTORY_MONGO_URI", raising=False)
    arguments = build_parser().parse_args(["history-index"])

    assert arguments.handler(arguments) == 2
    assert "is not set" in capsys.readouterr().err


def test_review_audit_cli_has_rebuild_safe_defaults():
    arguments = build_parser().parse_args(["review-audit"])
    assert arguments.policy == "config/reference/human-review-v1.yaml"
    assert not arguments.allow_missing_sources


def test_s3_backup_offload_and_hydrate_cli_defaults_are_fail_safe():
    parser = build_parser()
    backup = parser.parse_args(["s3-backup", "--staging", "/tmp/staging"])
    assert backup.config == "config/backup/s3-v1.toml"
    assert backup.full_content_restore is None
    assert backup.workers is None

    offload = parser.parse_args(
        [
            "s3-offload",
            "--manifest",
            "/tmp/manifest.json",
            "--run-record",
            "/tmp/run.json",
            "--asset-class",
            "source_pdf",
        ]
    )
    assert not offload.apply

    hydrate = parser.parse_args(
        [
            "s3-hydrate",
            "--manifest-key",
            "bctc-ai/snapshots/id/manifest.json",
            "--manifest-sha256",
            "a" * 64,
            "--logical-path",
            "vietstock_bctc/AAA/report.pdf",
        ]
    )
    assert hydrate.logical_path == ["vietstock_bctc/AAA/report.pdf"]
    assert hydrate.asset_class == []


def test_export_native_rows_cli_has_bounded_defaults_and_reports_publication(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path.resolve()
    workbook = root / "output/calibration/export/native-rows.xlsx"
    provenance = root / "output/calibration/export/native-rows.provenance.json"
    expected_sha256 = "a" * 64
    arguments = build_parser().parse_args(
        [
            "--project-root",
            str(root),
            "export-native-rows",
            "--rows",
            "output/calibration/native-rows.json",
            "--rows-sha256",
            expected_sha256,
            "--workbook",
            workbook.relative_to(root).as_posix(),
            "--provenance",
            provenance.relative_to(root).as_posix(),
        ]
    )
    assert arguments.policy == "config/export/native-statement-rows-excel-v1.yaml"
    assert arguments.rows_policy == "config/rows/native-statement-rows-v1.yaml"

    calls = []

    def fake_export(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            workbook_path=workbook,
            provenance_path=provenance,
            workbook_sha256="b" * 64,
            provenance_sha256="c" * 64,
            workbook_size_bytes=82002,
            provenance_size_bytes=7263,
            summary={
                "financial_table_span_row_count": 130,
                "outside_financial_table_span_row_count": 4,
                "all_source_row_count": 134,
                "financial_table_span_cell_count": 248,
                "outside_financial_table_span_cell_count": 4,
                "all_source_cell_count": 252,
            },
        )

    monkeypatch.setattr(export_module, "export_registered_native_rows_excel", fake_export)

    assert arguments.handler(arguments) == 0
    assert calls == [
        {
            "project_root": root,
            "rows_path": root / "output/calibration/native-rows.json",
            "expected_sha256": expected_sha256,
            "workbook_path": workbook,
            "provenance_path": provenance,
            "policy_path": root / "config/export/native-statement-rows-excel-v1.yaml",
            "rows_policy_path": root / "config/rows/native-statement-rows-v1.yaml",
        }
    ]
    stdout = capsys.readouterr().out
    assert "NATIVE_ROWS_EXCEL_WORKBOOK=output/calibration/export/native-rows.xlsx" in stdout
    assert "NATIVE_ROWS_EXCEL_WORKBOOK_SHA256=" + "b" * 64 in stdout
    assert "NATIVE_ROWS_EXCEL_WORKBOOK_BYTES=82002" in stdout
    assert (
        "NATIVE_ROWS_EXCEL_PROVENANCE="
        "output/calibration/export/native-rows.provenance.json" in stdout
    )
    assert "NATIVE_ROWS_EXCEL_PROVENANCE_SHA256=" + "c" * 64 in stdout
    assert "NATIVE_ROWS_EXCEL_PROVENANCE_BYTES=7263" in stdout
    assert "NATIVE_ROWS_EXCEL_FINANCIAL_TABLE_SPAN_ROWS=130" in stdout
    assert "NATIVE_ROWS_EXCEL_OUTSIDE_FINANCIAL_TABLE_SPAN_ROWS=4" in stdout
    assert "NATIVE_ROWS_EXCEL_ALL_SOURCE_ROWS=134" in stdout
    assert "NATIVE_ROWS_EXCEL_FINANCIAL_TABLE_SPAN_CELLS=248" in stdout
    assert "NATIVE_ROWS_EXCEL_OUTSIDE_FINANCIAL_TABLE_SPAN_CELLS=4" in stdout
    assert "NATIVE_ROWS_EXCEL_ALL_SOURCE_CELLS=252" in stdout
    assert str(root) not in stdout


def test_export_native_canonical_cli_forwards_trusted_pair_and_reports_relative_outputs(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path.resolve()
    workbook = root / "output/calibration/export/native-canonical.xlsx"
    provenance = root / "output/calibration/export/native-canonical.provenance.json"
    mapping_sha256 = "d" * 64
    rows_sha256 = "e" * 64
    arguments = build_parser().parse_args(
        [
            "--project-root",
            str(root),
            "export-native-canonical",
            "--mapping",
            "output/calibration/native-canonical.json",
            "--mapping-sha256",
            mapping_sha256,
            "--rows",
            "output/calibration/native-rows.json",
            "--rows-sha256",
            rows_sha256,
            "--workbook",
            workbook.relative_to(root).as_posix(),
            "--provenance",
            provenance.relative_to(root).as_posix(),
        ]
    )
    assert arguments.policy == "config/export/native-canonical-excel-v1.yaml"
    assert arguments.mapping_policy == "config/mapping/native-canonical-v1.yaml"
    assert arguments.rows_policy == "config/rows/native-statement-rows-v1.yaml"
    calls = []

    def fake_export(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            workbook_path=workbook,
            provenance_path=provenance,
            workbook_sha256="f" * 64,
            provenance_sha256="1" * 64,
            workbook_size_bytes=112_233,
            provenance_size_bytes=4_455,
            summary={
                "source_row_count": 134,
                "source_cell_count": 252,
                "source_disposition_counts": {
                    "EXISTING_ITEM": 127,
                    "NEW_ITEM_PROPOSAL": 3,
                    "AMBIGUOUS": 0,
                    "UNRESOLVED": 1,
                    "STRUCTURAL": 3,
                },
                "new_item_proposal_count": 3,
                "producer_schema_item_count": 1933,
            },
        )

    monkeypatch.setattr(
        canonical_export_module,
        "export_registered_native_canonical_excel",
        fake_export,
    )
    assert arguments.handler(arguments) == 0
    assert calls == [
        {
            "project_root": root,
            "mapping_path": root / "output/calibration/native-canonical.json",
            "mapping_expected_sha256": mapping_sha256,
            "rows_path": root / "output/calibration/native-rows.json",
            "rows_expected_sha256": rows_sha256,
            "workbook_path": workbook,
            "provenance_path": provenance,
            "export_policy_path": root / "config/export/native-canonical-excel-v1.yaml",
            "mapping_policy_path": root / "config/mapping/native-canonical-v1.yaml",
            "rows_policy_path": root / "config/rows/native-statement-rows-v1.yaml",
        }
    ]
    stdout = capsys.readouterr().out
    assert "NATIVE_CANONICAL_EXCEL_STATUS=ACCEPTED_NATIVE_CANONICAL_EXCEL_EXPORT" in stdout
    assert (
        "NATIVE_CANONICAL_EXCEL_WORKBOOK=output/calibration/export/native-canonical.xlsx" in stdout
    )
    assert "NATIVE_CANONICAL_EXCEL_WORKBOOK_SHA256=" + "f" * 64 in stdout
    assert "NATIVE_CANONICAL_EXCEL_WORKBOOK_BYTES=112233" in stdout
    assert (
        "NATIVE_CANONICAL_EXCEL_PROVENANCE="
        "output/calibration/export/native-canonical.provenance.json" in stdout
    )
    assert "NATIVE_CANONICAL_EXCEL_PROVENANCE_SHA256=" + "1" * 64 in stdout
    assert "NATIVE_CANONICAL_EXCEL_PROVENANCE_BYTES=4455" in stdout
    assert "NATIVE_CANONICAL_EXCEL_SOURCE_ROWS=134" in stdout
    assert "NATIVE_CANONICAL_EXCEL_SOURCE_CELLS=252" in stdout
    assert "NATIVE_CANONICAL_EXCEL_EXISTING_ITEMS=127" in stdout
    assert "NATIVE_CANONICAL_EXCEL_NEW_ITEM_PROPOSALS=3" in stdout
    assert "NATIVE_CANONICAL_EXCEL_AMBIGUOUS=0" in stdout
    assert "NATIVE_CANONICAL_EXCEL_UNRESOLVED=1" in stdout
    assert "NATIVE_CANONICAL_EXCEL_STRUCTURAL=3" in stdout
    assert "NATIVE_CANONICAL_EXCEL_SCHEMA_ITEMS=1933" in stdout
    assert str(root) not in stdout


def test_export_native_canonical_cli_requires_both_trusted_input_hashes():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "export-native-canonical",
                "--mapping",
                "output/calibration/native-canonical.json",
                "--rows",
                "output/calibration/native-rows.json",
                "--rows-sha256",
                "a" * 64,
                "--workbook",
                "output/calibration/export/native-canonical.xlsx",
                "--provenance",
                "output/calibration/export/native-canonical.provenance.json",
            ]
        )
