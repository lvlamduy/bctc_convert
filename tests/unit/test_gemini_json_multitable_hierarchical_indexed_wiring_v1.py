from __future__ import annotations

import copy

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_multitable_hierarchical_family_v1 import (
    _compiled,
    _json,
    _summary_page,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    merge_region_repair_v1,
    region_repair_targets_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    initialize_region_repair_extension_v1,
    query_selected_multitable_hierarchical_family_regions_v1,
    record_page_json_region_repair_v1,
    validate_selected_multitable_hierarchical_family_candidate_replays_v1,
    validate_selected_multitable_hierarchical_family_query_evidence_v1,
)


def _empty_page() -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [],
                "title_exact": "Tài sản cố định",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


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
    target_page = _summary_page()
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
    evidence = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    cluster = evidence["accepted_clusters"][0]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=(
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                cluster["component_regions"]
            )
        ),
    )
    trials = [
        _trial(evidence["selected_document_axis"][0], candidate, READY),
        _trial(evidence["selected_document_axis"][1], None, NOT_OBSERVED),
    ]
    return database, selected, evidence, trials, compiled


def test_indexed_query_flat_sweep_and_sqlite_candidate_replay(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 1,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=_json("tm-other-assets-topology-v1.json"),
        evaluation_spec=_json("tm-other-assets-evaluation-v1.json"),
        schema_binding_spec=_json("tm-other-assets-schema-binding-v1.json"),
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
        validate_selected_multitable_hierarchical_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
        == evidence
    )
    assert (
        validate_selected_multitable_hierarchical_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )


def test_indexed_query_accepts_only_exact_replayed_derived_page_lineage(tmp_path) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _summary_page()
    base = _ingest(database, page_json=page)
    targets = region_repair_targets_v1(page, target_ids=["s1:t1:r2"])
    merged, receipt = merge_region_repair_v1(
        page,
        base_page_json_version_id=base["page_json_version_id"],
        targets=targets,
        repair={
            "all_targets_transcribed": True,
            "rows": [
                {
                    "label_exact": targets[0]["label_exact"],
                    "target_id": "s1:t1:r2",
                    "values_exact": ["61", "50"],
                }
            ],
            "uncertainty_exact": [],
        },
    )
    derived = _ingest(
        database,
        page_json=merged,
        prompt_sha256="f" * 64,
        prompt_variant="region-repair-row-values",
    )
    initialize_region_repair_extension_v1(database)
    record_page_json_region_repair_v1(
        database,
        merged_page_json_version_id=derived["page_json_version_id"],
        receipt=receipt,
    )

    evidence = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=[derived["page_json_version_id"]],
        compiled_specs=_compiled(),
    )
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 0,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }


def test_sqlite_replay_rejects_coherent_candidate_source_drift(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    forged = copy.deepcopy(trials)
    forged[0]["candidates"][0]["closure_receipt"]["table_receipts"][0]["classification"][
        "role_hits"
    ][0]["role"] = "ASSOCIATE"
    candidate = forged[0]["candidates"][0]
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    forged[0]["selected_candidate_id"] = candidate["candidate_id"]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=_json("tm-other-assets-topology-v1.json"),
        evaluation_spec=_json("tm-other-assets-evaluation-v1.json"),
        schema_binding_spec=_json("tm-other-assets-schema-binding-v1.json"),
        trials=forged,
        indexed_query_evidence=evidence,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_selected_multitable_hierarchical_family_candidate_replays_v1(
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
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="needs one candidate",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
            topology_spec=_json("tm-other-assets-topology-v1.json"),
            evaluation_spec=_json("tm-other-assets-evaluation-v1.json"),
            schema_binding_spec=_json("tm-other-assets-schema-binding-v1.json"),
            trials=deleted,
            indexed_query_evidence=evidence,
        )
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="does not replay"):
        validate_selected_multitable_hierarchical_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=list(reversed(selected)),
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
