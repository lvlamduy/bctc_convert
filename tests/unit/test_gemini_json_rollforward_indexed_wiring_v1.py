from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_rollforward_accounting_family_v1 import (
    _lane_page,
    _lane_table,
    _page,
    _period_table,
    _stacked_table,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
    build_gemini_json_rollforward_region_query_receipt_v1,
    evaluate_gemini_json_rollforward_family_cluster_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_rollforward_family_regions_v1,
    validate_selected_rollforward_family_query_evidence_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _specs() -> tuple[dict, dict, dict, dict]:
    topology = _json("tm-provision-movement-rollforward-topology-v1.json")
    evaluation = _json("tm-provision-movement-rollforward-evaluation-v1.json")
    schema = _json("tm-provision-movement-rollforward-schema-binding-v1.json")
    return (
        topology,
        evaluation,
        schema,
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _engine_regions(indexed: dict) -> list[dict]:
    fields = (
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    )
    return [{field: region[field] for field in fields} for region in indexed["accepted_regions"]]


@pytest.mark.parametrize(
    ("page_json", "layout_kind", "component_count"),
    [
        (_page(_stacked_table()), "STACKED_PERIOD_BLOCKS", 1),
        (
            _page(
                _period_table("Tại ngày 31 tháng 12 năm 2025"),
                _period_table("Tại ngày 31 tháng 12 năm 2024"),
            ),
            "PERIOD_TABLES_LANE_COLUMNS",
            2,
        ),
        (
            _lane_page(
                ["Dự phòng chung", "Dự phòng cụ thể"],
                _lane_table(),
                _lane_table(),
            ),
            "LANE_TABLES_PERIOD_COLUMNS",
            2,
        ),
    ],
)
def test_selected_rollforward_query_projects_each_layout_without_unselected_pages(
    tmp_path: Path,
    page_json: dict,
    layout_kind: str,
    component_count: int,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    selected = _ingest(database, page_json=page_json)
    unselected = _ingest(
        database,
        physical_page=8,
        image_sha256="1" * 64,
        page_json=page_json,
    )
    compiled = _specs()[3]

    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )

    assert len(indexed["accepted_regions"]) == component_count
    assert {region["layout_kind"] for region in indexed["accepted_regions"]} == {layout_kind}
    assert {region["page_json_version_id"] for region in indexed["accepted_regions"]} == {
        selected["page_json_version_id"]
    }
    assert unselected["page_json_version_id"] not in {
        disposition["page_json_version_id"] for disposition in indexed["candidate_dispositions"]
    }
    assert indexed["query_receipt"]["exact_region_count"] == component_count
    assert (
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[selected["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
        )
        == indexed
    )


def test_selected_rollforward_query_persists_typed_veto_and_rejects_hash_tamper(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page_json = _page(_stacked_table())
    page_json["sections"][0]["title_exact"] = "Thư tín dụng cho khách hàng"
    page_json["sections"][0]["narratives_exact"] = [
        "Dự phòng rủi ro cho vay khách hàng và thư tín dụng"
    ]
    selected = _ingest(database, page_json=page_json)
    compiled = _specs()[3]
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )

    assert indexed["accepted_regions"] == []
    assert indexed["candidate_dispositions"][0]["disposition"] == ("RESET_OR_HARD_NEGATIVE_VETO")
    attacked = deepcopy(indexed)
    attacked["candidate_dispositions"][0]["row_axis_sha256"] = "f" * 64
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="does not replay exactly",
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[selected["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=attacked,
        )


def test_rollforward_sweep_replays_and_store_dispatches_movement_roles(
    tmp_path: Path,
) -> None:
    page_database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(page_database)
    page_json = _page(_stacked_table())
    selected = _ingest(page_database, page_json=page_json)
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        page_database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )
    regions = _engine_regions(indexed)
    candidate = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version={selected["page_json_version_id"]: page_json},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(regions),
    )
    assert candidate["status"] == READY
    assert candidate["mappings"]
    assert all(
        "movement_role" in mapping and "role" not in mapping for mapping in candidate["mappings"]
    )
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": "report.pdf",
        "source_sha256": "b" * 64,
        "status": READY,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
        indexed_query_evidence=indexed,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep

    family_database = tmp_path / "families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        family_database,
        sweep=sweep,
        corpus_index_ref={"path": "index.json", "sha256": "4" * 64, "size_bytes": 1},
        implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
        run_kind="EXPERIMENTAL",
    )
    assert load_gemini_accounting_family_sweep_v1(family_database, stored["family_run_id"]) == sweep
    with sqlite3.connect(family_database) as connection:
        roles = {row[0] for row in connection.execute("SELECT role FROM family_mapping").fetchall()}
    assert roles == {mapping["movement_role"] for mapping in candidate["mappings"]}
