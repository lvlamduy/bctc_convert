from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_customer_deposit_family_v1 import (
    _compiled,
    _customer,
    _ordinary_type,
    _page,
)

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonCustomerDepositFamilyV1Error,
    build_gemini_json_customer_deposit_region_query_receipt_v1,
    evaluate_gemini_json_customer_deposit_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_customer_deposit_family_regions_v1,
    validate_selected_customer_deposit_family_candidate_replays_v1,
    validate_selected_customer_deposit_family_query_evidence_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _empty_page() -> dict:
    return _page(title="Tài sản cố định")


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


def _fixture(tmp_path: Path) -> tuple[Path, list[str], dict, list[dict], dict]:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target_page = _page(_ordinary_type())
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
    evidence = query_selected_customer_deposit_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    cluster = evidence["accepted_clusters"][0]
    candidate = evaluate_gemini_json_customer_deposit_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    trials = [
        _trial(evidence["selected_document_axis"][0], candidate, READY),
        _trial(evidence["selected_document_axis"][1], None, NOT_OBSERVED),
    ]
    return database, selected, evidence, trials, compiled


def test_indexed_query_sweep_and_sqlite_candidate_replay(tmp_path: Path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 1,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    assert evidence["query_receipt"]["accepted_cluster_count"] == 1
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=_json("tm-customer-deposit-classification-topology-v1.json"),
        evaluation_spec=_json("tm-customer-deposit-classification-evaluation-v1.json"),
        schema_binding_spec=_json("tm-customer-deposit-classification-schema-binding-v1.json"),
        trials=trials,
        indexed_query_evidence=evidence,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    assert sweep["metrics"] == {
        "document_count": 2,
        "mapping_count": 5,
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 0,
    }
    assert (
        validate_selected_customer_deposit_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
        == evidence
    )
    assert (
        validate_selected_customer_deposit_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )


def test_sqlite_replay_rejects_coherent_candidate_source_drift(tmp_path: Path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    forged = copy.deepcopy(trials)
    forged[0]["candidates"][0]["closure_receipt"]["type_currency_view"]["source_inventory"][0][
        "label_exact"
    ] = "Không có trong SQLite"
    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="candidate does not replay exactly",
    ):
        validate_selected_customer_deposit_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=forged,
        )


def test_query_binding_rejects_candidate_deletion_and_frontier_drift(tmp_path: Path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    deleted = copy.deepcopy(trials)
    deleted[0]["candidate_count"] = 0
    deleted[0]["candidates"] = []
    deleted[0]["mappings"] = []
    deleted[0]["selected_candidate_id"] = None
    deleted[0]["status"] = NOT_OBSERVED
    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="exactly one candidate",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-customer-deposit-classification-topology-v1.json"),
            evaluation_spec=_json("tm-customer-deposit-classification-evaluation-v1.json"),
            schema_binding_spec=_json("tm-customer-deposit-classification-schema-binding-v1.json"),
            trials=deleted,
            indexed_query_evidence=evidence,
        )
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="does not replay exactly",
    ):
        validate_selected_customer_deposit_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=list(reversed(selected)),
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )


def test_indexed_query_keeps_ambiguous_selected_component_out_of_candidate_axis(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    ambiguous_customer = _customer()
    label = "Hợp tác xã và hộ kinh doanh, cá nhân"
    ambiguous_customer["rows"][1]["label_exact"] = label
    ambiguous_customer["rows"][1]["hierarchy_path_exact"] = [label]
    selected = _ingest(
        database,
        page_json=_page(_ordinary_type(), ambiguous_customer),
    )
    selected_ids = [selected["page_json_version_id"]]
    compiled = _compiled()
    evidence = query_selected_customer_deposit_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )

    assert evidence["accepted_clusters"] == []
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 0,
        READY: 0,
        UNRESOLVED: 1,
    }
    cluster = evidence["candidate_dispositions"][0]["cluster"]
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "SOURCE_ROW_ROLE_MATCH_IS_AMBIGUOUS" in cluster["reasons"]
    assert (
        validate_selected_customer_deposit_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
        == evidence
    )

    forged = copy.deepcopy(evidence)
    forged["candidate_dispositions"][0]["cluster"]["status"] = READY
    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="disposition cluster binding drifted",
    ):
        validate_selected_customer_deposit_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=forged,
        )
