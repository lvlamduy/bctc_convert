from __future__ import annotations

import json
import math

import duckdb
import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.reference.historical import (
    RAW_SERIES,
    YTD_SERIES,
    HistoricalValueState,
    extract_historical_document,
    load_historical_reference_policy,
    lookup_resolved_historical_reference,
    verify_historical_weak_reference,
    write_historical_reference_database,
)
from bctc_ai.schema.registry import SchemaItem


def _schema_item(identifier: int, name: str, statement: str, order: int) -> SchemaItem:
    return SchemaItem(
        schema_id=identifier,
        canonical_name=name,
        normalized_name=name.casefold(),
        statement_type=statement,
        display_order=order,
    )


def _document() -> dict[str, object]:
    return {
        "_id": "fixture-document",
        "stock_id": "VPB",
        "stock_industry": "bank",
        "term_type": "quaterly",
        "data": {
            "NormTerm": ["Q1/2024", "Q2/2024", "Q3/2024"],
            "Q": [1, 2, 3],
            "Y": [2024, 2024, 2024],
            "Stock_ID": ["VPB", "VPB", "VPB"],
            "4302": [100.0, -0.0, None],
            "4385": [10.0, math.nan, 30.0],
            "YTD_4385": [10.0, 25.0, 55.0],
            "1944": [1.0, 2.0, 3.0],
            "YTD_1944": [1.0, 3.0, 6.0],
            "45": [0.1, 0.2, 0.3],
            "Cumulative_4385": [10.0, 25.0, 55.0],
        },
    }


def test_historical_policy_is_versioned_and_fails_closed(project_root, tmp_path):
    source = project_root / "config/reference/historical-weak-reference.yaml"
    policy = load_historical_reference_policy(source)
    assert policy["source"]["collection"] == "data_chart"
    assert policy["safety"]["mapping_candidate_generation_allowed"] is False
    weakened = tmp_path / "weakened.yaml"
    weakened.write_text(
        source.read_text(encoding="utf-8").replace(
            "pdf_confidence_promotion_allowed: false",
            "pdf_confidence_promotion_allowed: true",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="weakens a forbidden safety gate"):
        load_historical_reference_policy(weakened)


def test_extract_history_maps_only_schema_ids_and_explicit_ytd_series():
    schema = {
        4302: _schema_item(4302, "Tài sản", "CDKT", 0),
        4385: _schema_item(4385, "Thu nhập lãi thuần", "KQKD", 0),
    }

    result = extract_historical_document(_document(), schema)

    assert len(result.cells) == 9
    assert result.mapped_raw_ids == (4302, 4385)
    assert result.mapped_ytd_ids == (4385,)
    assert result.unknown_numeric_features == (45, 1944)
    assert result.unknown_ytd_features == ("YTD_1944",)
    assert "Cumulative_4385" in result.excluded_named_features
    assert result.source_contains_proposed_id is True

    negative_zero = next(
        cell for cell in result.cells if cell.report_norm_id == 4302 and cell.norm_term == "Q2/2024"
    )
    assert negative_zero.value_state == HistoricalValueState.ZERO
    assert negative_zero.raw_value == "-0.0"
    assert negative_zero.negative_zero is True
    nan_cell = next(
        cell
        for cell in result.cells
        if cell.report_norm_id == 4385
        and cell.norm_term == "Q2/2024"
        and cell.series_kind == RAW_SERIES
    )
    assert nan_cell.value_state == HistoricalValueState.NAN
    assert nan_cell.numeric_value is None


def test_extract_history_rejects_misaligned_series_length():
    document = _document()
    document["data"]["4302"] = [1.0]
    schema = {4302: _schema_item(4302, "Tài sản", "CDKT", 0)}

    with pytest.raises(ValueError, match="does not match NormTerm length"):
        extract_historical_document(document, schema)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"stock_industry": "other"}, "outside the bank allowlist"),
        ({"term_type": "monthly"}, "unsupported historical term_type"),
    ],
)
def test_extract_history_rejects_out_of_scope_or_unknown_periods(mutation, message):
    document = _document()
    document.update(mutation)
    schema = {4302: _schema_item(4302, "Tài sản", "CDKT", 0)}

    with pytest.raises(ValueError, match=message):
        extract_historical_document(document, schema)


def test_database_lookup_requires_resolved_id_and_cannot_promote_pdf(tmp_path):
    schema = {
        4302: _schema_item(4302, "Tài sản", "CDKT", 0),
        4385: _schema_item(4385, "Thu nhập lãi thuần", "KQKD", 0),
    }
    cells = extract_historical_document(_document(), schema).cells
    database = tmp_path / "history.duckdb"

    written = write_historical_reference_database(
        database,
        cells,
        archive_sha256="a" * 64,
        metadata={"authority": "HISTORICAL_WEAK_REFERENCE_ONLY"},
    )

    assert written["row_count"] == 9
    assert written["size_bytes"] > 0
    raw = lookup_resolved_historical_reference(
        database,
        stock_id="vpb",
        report_norm_id=4385,
        norm_term="Q1/2024",
    )
    assert len(raw) == 1
    assert raw[0].series_kind == RAW_SERIES
    assert raw[0].numeric_value == 10.0
    assert raw[0].unit_status == "UNKNOWN"
    assert raw[0].scope_status == "UNKNOWN"
    assert raw[0].can_map_pdf is False
    assert raw[0].can_promote_pdf is False

    nan_match = lookup_resolved_historical_reference(
        database,
        stock_id="VPB",
        report_norm_id=4385,
        norm_term="Q2/2024",
    )[0]
    assert nan_match.value_state == HistoricalValueState.NAN
    assert nan_match.numeric_value is None
    negative_zero = lookup_resolved_historical_reference(
        database,
        stock_id="VPB",
        report_norm_id=4302,
        norm_term="Q2/2024",
    )[0]
    assert negative_zero.raw_value == "-0.0"
    assert negative_zero.negative_zero is True

    with_ytd = lookup_resolved_historical_reference(
        database,
        stock_id="VPB",
        report_norm_id=4385,
        norm_term="Q1/2024",
        include_upstream_ytd=True,
    )
    assert {match.series_kind for match in with_ytd} == {RAW_SERIES, YTD_SERIES}
    connection = duckdb.connect(str(database))
    try:
        with pytest.raises(duckdb.ConstraintException):
            connection.execute(
                "UPDATE weak_reference_cells SET can_promote_pdf = true WHERE stock_id = 'VPB'"
            )
    finally:
        connection.close()
    with pytest.raises(FileExistsError):
        write_historical_reference_database(
            database,
            cells,
            archive_sha256="a" * 64,
            metadata={},
        )


def test_local_reference_verifier_checks_hashes_rows_and_safety_contract(tmp_path):
    schema = {4302: _schema_item(4302, "Tài sản", "CDKT", 0)}
    cells = extract_historical_document(_document(), schema).cells
    database = tmp_path / "data/local/history.duckdb"
    written = write_historical_reference_database(
        database,
        cells,
        archive_sha256="a" * 64,
        metadata={"authority": "HISTORICAL_WEAK_REFERENCE_ONLY"},
    )
    module = tmp_path / "src/implementation.py"
    policy = tmp_path / "config/policy.yaml"
    module.parent.mkdir(parents=True)
    policy.parent.mkdir(parents=True)
    module.write_text("VERSION = 1\n", encoding="utf-8")
    policy.write_text("version: 1\n", encoding="utf-8")
    registered = tmp_path / "data/registered"
    registered.mkdir(parents=True)
    (registered / "mongodb_dump_registry.json").write_text(
        json.dumps({"archive": {"sha256": "a" * 64}}), encoding="utf-8"
    )
    registry = {
        "status": "PASS_WEAK_REFERENCE_ONLY",
        "database": {**written, "path": "data/local/history.duckdb"},
        "implementation": {
            "module": "src/implementation.py",
            "module_sha256": sha256_file(module),
            "policy": "config/policy.yaml",
            "policy_sha256": sha256_file(policy),
        },
        "source": {"archive": {"sha256": "a" * 64}},
        "schema": {
            "append_safe_from_historical_key_collision_perspective": True,
            "source_contains_proposed_id": False,
            "proposed_id": 1944,
        },
        "safety_contract": {
            "mapping_candidate_generation_allowed": False,
            "pdf_confidence_promotion_allowed": False,
            "pdf_value_overwrite_allowed": False,
            "upstream_ytd_can_supply_pdf_derivation_operand": False,
            "lookup_requires_resolved_report_norm_id": True,
            "unit": "UNKNOWN",
            "scope": "UNKNOWN",
        },
        "cells": {"count": len(cells)},
        "scope": {"registered_bank_count": 1},
    }
    registry_path = registered / "historical_weak_reference_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    passed = verify_historical_weak_reference(tmp_path, registry_path)
    assert passed["status"] == "PASS"
    assert all(passed["checks"].values())

    module.write_text("VERSION = 2\n", encoding="utf-8")
    failed = verify_historical_weak_reference(tmp_path, registry_path)
    assert failed["status"] == "FAIL"
    assert failed["checks"]["module_sha256"] is False


def test_local_reference_verifier_reports_missing_index(tmp_path):
    result = verify_historical_weak_reference(tmp_path)

    assert result["status"] == "NOT_CONFIGURED"
    assert result["database_present"] is False
