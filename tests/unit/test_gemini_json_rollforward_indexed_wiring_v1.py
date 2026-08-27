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
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonFlatAccountingFamilyV1Error,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
    build_gemini_json_rollforward_region_query_receipt_v1,
    evaluate_gemini_json_rollforward_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
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


def _candidate_for_page(selected: dict, page_json: dict, indexed: dict, compiled: dict) -> dict:
    regions = _engine_regions(indexed)
    return evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version={selected["page_json_version_id"]: page_json},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(regions),
    )


def _trial(
    *,
    ordinal: int,
    source: str,
    source_sha256: str,
    status: str,
    candidate: dict | None = None,
) -> dict:
    selected = candidate if candidate is not None and status == READY else None
    return {
        "candidate_count": int(candidate is not None),
        "candidates": [] if candidate is None else [candidate],
        "document_ordinal": ordinal,
        "mappings": [] if selected is None else selected["mappings"],
        "reasons": (
            []
            if status in {READY, NOT_OBSERVED}
            else (
                candidate["reasons"]
                if candidate is not None
                else ["PARTIAL_REQUIRED_ANCHOR_FRONTIER_ONLY"]
            )
        ),
        "selected_candidate_id": None if selected is None else selected["candidate_id"],
        "source_logical_name": source,
        "source_sha256": source_sha256,
        "status": status,
    }


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


def test_cross_document_ready_candidate_cannot_replace_a_near_only_trial(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    near_page = _page(_stacked_table())
    near_page["sections"][0]["tables"][0]["rows"].pop()
    near = _ingest(
        database,
        source_logical_name="a-near.pdf",
        source_sha256="a" * 64,
        image_sha256="1" * 64,
        page_json=near_page,
    )
    ready_page = _page(_stacked_table())
    ready = _ingest(
        database,
        source_logical_name="b-ready.pdf",
        source_sha256="b" * 64,
        image_sha256="2" * 64,
        page_json=ready_page,
    )
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[
            near["page_json_version_id"],
            ready["page_json_version_id"],
        ],
        compiled_specs=compiled,
    )
    assert len(indexed["accepted_regions"]) == 1
    assert indexed["accepted_regions"][0]["source_logical_name"] == "b-ready.pdf"
    assert "a-near.pdf" in {
        disposition["source_logical_name"]
        for disposition in indexed["candidate_dispositions"]
        if type(disposition["classification"]) is dict
        and disposition["classification"]["local_owner_visible"]
    }
    ready_candidate = _candidate_for_page(ready, ready_page, indexed, compiled)
    assert ready_candidate["status"] == READY
    valid_trials = [
        _trial(
            ordinal=1,
            source="a-near.pdf",
            source_sha256="a" * 64,
            status=UNRESOLVED,
        ),
        _trial(
            ordinal=2,
            source="b-ready.pdf",
            source_sha256="b" * 64,
            status=READY,
            candidate=ready_candidate,
        ),
    ]
    valid = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=valid_trials,
        indexed_query_evidence=indexed,
    )
    assert validate_gemini_json_flat_family_sweep_v1(valid) == valid

    attacked = deepcopy(valid)
    attacked["trials"][0] = _trial(
        ordinal=1,
        source="a-near.pdf",
        source_sha256="a" * 64,
        status=READY,
        candidate=deepcopy(ready_candidate),
    )
    attacked["metrics"] = {
        "document_count": 2,
        "mapping_count": len(ready_candidate["mappings"]) * 2,
        "not_observed_count": 0,
        "ready_count": 2,
        "unresolved_count": 0,
    }
    attacked_material = {key: value for key, value in attacked.items() if key != "sweep_id"}
    attacked["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(attacked_material)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="not query-evidence bound",
    ):
        validate_gemini_json_flat_family_sweep_v1(attacked)
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="sweep bindings do not replay exactly",
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[
                near["page_json_version_id"],
                ready["page_json_version_id"],
            ],
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
            trials=attacked["trials"],
        )
    with pytest.raises(GeminiJsonFlatAccountingFamilyV1Error):
        ingest_gemini_accounting_family_sweep_v1(
            tmp_path / "attacked.sqlite3",
            sweep=attacked,
            corpus_index_ref={
                "path": "index.json",
                "sha256": "4" * 64,
                "size_bytes": 1,
            },
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="EXPERIMENTAL",
        )


def test_empty_selected_query_cannot_admit_a_foreign_ready_candidate(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    empty_page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [],
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
    }
    empty = _ingest(
        database,
        source_logical_name="a-empty.pdf",
        source_sha256="a" * 64,
        image_sha256="1" * 64,
        page_json=empty_page,
    )
    ready_page = _page(_stacked_table())
    ready = _ingest(
        database,
        source_logical_name="z-foreign.pdf",
        source_sha256="f" * 64,
        image_sha256="2" * 64,
        page_json=ready_page,
    )
    topology, evaluation, schema, compiled = _specs()
    empty_evidence = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[empty["page_json_version_id"]],
        compiled_specs=compiled,
    )
    assert empty_evidence["candidate_dispositions"] == []
    assert empty_evidence["accepted_regions"] == []
    assert empty_evidence["selected_document_axis"][0]["source_logical_name"] == "a-empty.pdf"
    foreign_evidence = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[ready["page_json_version_id"]],
        compiled_specs=compiled,
    )
    foreign_candidate = _candidate_for_page(ready, ready_page, foreign_evidence, compiled)
    attacked_trials = [
        _trial(
            ordinal=1,
            source="a-empty.pdf",
            source_sha256="a" * 64,
            status=READY,
            candidate=foreign_candidate,
        )
    ]
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="not query-evidence bound",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=attacked_trials,
            indexed_query_evidence=empty_evidence,
        )
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="sweep bindings do not replay exactly",
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[empty["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=empty_evidence,
            trials=attacked_trials,
        )


def test_near_only_and_empty_source_dispositions_are_exactly_bound(tmp_path: Path) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    near_page = _page(_stacked_table())
    near_page["sections"][0]["tables"][0]["rows"].pop()
    near = _ingest(
        database,
        source_logical_name="a-near.pdf",
        source_sha256="a" * 64,
        image_sha256="1" * 64,
        page_json=near_page,
    )
    empty_page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [],
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
    }
    empty = _ingest(
        database,
        source_logical_name="b-empty.pdf",
        source_sha256="b" * 64,
        image_sha256="2" * 64,
        page_json=empty_page,
    )
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[
            near["page_json_version_id"],
            empty["page_json_version_id"],
        ],
        compiled_specs=compiled,
    )
    trials = [
        _trial(
            ordinal=1,
            source="a-near.pdf",
            source_sha256="a" * 64,
            status=UNRESOLVED,
        ),
        _trial(
            ordinal=2,
            source="b-empty.pdf",
            source_sha256="b" * 64,
            status=NOT_OBSERVED,
        ),
    ]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    assert sweep["metrics"] == {
        "document_count": 2,
        "mapping_count": 0,
        "not_observed_count": 1,
        "ready_count": 0,
        "unresolved_count": 1,
    }
    attacked = deepcopy(trials)
    attacked[0]["status"] = NOT_OBSERVED
    attacked[0]["reasons"] = []
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="near-only trial binding drifted",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=attacked,
            indexed_query_evidence=indexed,
        )
