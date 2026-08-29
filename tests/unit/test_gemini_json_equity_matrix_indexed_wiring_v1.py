from __future__ import annotations

import copy

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_equity_matrix_accounting_family_v1 import (
    _compiled,
    _component_column_table,
    _json,
    _page,
    _section,
)

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    GeminiJsonEquityMatrixAccountingFamilyV1Error,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_equity_matrix_family_regions_v1,
    validate_selected_equity_matrix_family_candidate_replays_v1,
    validate_selected_equity_matrix_family_query_evidence_v1,
)


def _empty_page() -> dict:
    return _page(_section("Tài sản cố định"))


def _trial(document: dict, candidate: dict | None, status: str) -> dict:
    return {
        "candidate_count": int(candidate is not None),
        "candidates": [] if candidate is None else [candidate],
        "document_ordinal": document["document_ordinal"],
        "mappings": candidate["mappings"] if candidate is not None and status == READY else [],
        "reasons": [] if status in {READY, NOT_OBSERVED} else candidate["reasons"],
        "selected_candidate_id": (
            candidate["candidate_id"] if candidate is not None and status == READY else None
        ),
        "source_logical_name": document["source_logical_name"],
        "source_sha256": document["source_sha256"],
        "status": status,
    }


def _fixture(tmp_path):
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target_page = _page(_section("Vốn chủ sở hữu", _component_column_table()))
    target = _ingest(database, page_json=target_page)
    absent = _ingest(
        database,
        image_sha256="1" * 64,
        physical_page=1,
        prompt_sha256="2" * 64,
        source_logical_name="absent.pdf",
        source_sha256="3" * 64,
        page_json=_empty_page(),
    )
    selected = [target["page_json_version_id"], absent["page_json_version_id"]]
    compiled = _compiled()
    evidence = query_selected_equity_matrix_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    cluster = evidence["accepted_clusters"][0]
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    trials = [
        _trial(evidence["selected_document_axis"][0], candidate, READY),
        _trial(evidence["selected_document_axis"][1], None, NOT_OBSERVED),
    ]
    return database, selected, evidence, trials, compiled


def test_indexed_query_sweep_and_sqlite_candidate_replay(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 1,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    assert evidence["query_receipt"]["accepted_cluster_count"] == 1
    assert evidence["query_receipt"]["accepted_fragment_count"] == 1
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=_json("tm-capital-and-funds-topology-v1.json"),
        evaluation_spec=_json("tm-capital-and-funds-evaluation-v1.json"),
        schema_binding_spec=_json("tm-capital-and-funds-schema-binding-v1.json"),
        trials=trials,
        indexed_query_evidence=evidence,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    assert sweep["metrics"] == {
        "document_count": 2,
        "mapping_count": len(trials[0]["mappings"]),
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 0,
    }
    assert (
        validate_selected_equity_matrix_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
        == evidence
    )
    assert (
        validate_selected_equity_matrix_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )


def test_sqlite_replay_rejects_coherently_rehashed_candidate_source_drift(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    forged = copy.deepcopy(trials)
    candidate = forged[0]["candidates"][0]
    candidate["closure_receipt"]["component_axis"][0]["members_exact"] = ["Vốn giả"]
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    forged[0]["selected_candidate_id"] = candidate["candidate_id"]
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="mapping schema binding drifted|does not replay",
    ):
        validate_selected_equity_matrix_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=forged,
        )


def test_query_binding_rejects_candidate_deletion_and_frontier_drift(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    deleted = copy.deepcopy(trials)
    deleted[0]["candidate_count"] = 0
    deleted[0]["candidates"] = []
    deleted[0]["mappings"] = []
    deleted[0]["selected_candidate_id"] = None
    deleted[0]["status"] = NOT_OBSERVED
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="exactly one candidate",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-capital-and-funds-topology-v1.json"),
            evaluation_spec=_json("tm-capital-and-funds-evaluation-v1.json"),
            schema_binding_spec=_json("tm-capital-and-funds-schema-binding-v1.json"),
            trials=deleted,
            indexed_query_evidence=evidence,
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="does not replay exactly"):
        validate_selected_equity_matrix_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=list(reversed(selected)),
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
