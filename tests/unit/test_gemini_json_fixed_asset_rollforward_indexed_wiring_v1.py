from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_fixed_asset_rollforward_family_v1 import (
    _compiled,
    _compiled_intangible,
    _compiled_investment_property,
    _compiled_leased,
    _intangible_page,
    _intangible_table,
    _investment_cost_fragment,
    _investment_property_page,
    _investment_property_table,
    _investment_summary_table,
    _leased_page,
    _page,
    _supplemental_table,
)

from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
    NOT_OBSERVED,
    READY,
    GeminiJsonFixedAssetRollforwardFamilyV1Error,
    build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1,
    evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_fixed_asset_rollforward_family_regions_v1,
    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1,
    validate_selected_fixed_asset_rollforward_family_query_evidence_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config" / "families" / name).read_bytes())


def _empty_page() -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [],
                "title_exact": "Thông tin chung",
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
    target_page = _page()
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
    evidence = query_selected_fixed_asset_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    cluster = evidence["accepted_clusters"][0]
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=(
            build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
                cluster["component_regions"],
                control_regions=cluster["control_regions"],
            )
        ),
    )
    trials = [
        _trial(evidence["selected_document_axis"][0], candidate, READY),
        _trial(evidence["selected_document_axis"][1], None, NOT_OBSERVED),
    ]
    return database, selected, evidence, trials, compiled


def _intangible_fixture(tmp_path):
    database = tmp_path / "intangible-pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target_page = _intangible_page(tables=[_intangible_table(), _supplemental_table()])
    target = _ingest(database, page_json=target_page)
    absent = _ingest(
        database,
        image_sha256="a" * 64,
        physical_page=1,
        prompt_sha256="b" * 64,
        source_logical_name="intangible-absent.pdf",
        source_sha256="c" * 64,
        page_json=_empty_page(),
    )
    selected = [target["page_json_version_id"], absent["page_json_version_id"]]
    compiled = _compiled_intangible()
    evidence = query_selected_fixed_asset_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    cluster = evidence["accepted_clusters"][0]
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
            cluster["component_regions"], control_regions=cluster["control_regions"]
        ),
    )
    trials = [
        _trial(evidence["selected_document_axis"][0], candidate, READY),
        _trial(evidence["selected_document_axis"][1], None, NOT_OBSERVED),
    ]
    return database, selected, evidence, trials, compiled


def _sweep(evidence: dict, trials: list[dict]) -> dict:
    return build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=_json("tm-tangible-fixed-assets-topology-v1.json"),
        evaluation_spec=_json("tm-tangible-fixed-assets-evaluation-v1.json"),
        schema_binding_spec=_json("tm-tangible-fixed-assets-schema-binding-v1.json"),
        trials=trials,
        indexed_query_evidence=evidence,
    )


def test_indexed_query_sweep_and_sqlite_candidate_replay(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 1,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    sweep = _sweep(evidence, trials)
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    assert sweep["metrics"] == {
        "document_count": 2,
        "mapping_count": len(trials[0]["mappings"]),
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 0,
    }
    assert (
        validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )
        == evidence
    )
    assert (
        validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )


def test_sqlite_replay_rejects_coherent_source_receipt_drift(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    forged = copy.deepcopy(trials)
    candidate = forged[0]["candidates"][0]
    candidate["closure_receipt"]["table_receipt"]["raw_row_inventory"][0]["label_exact"] = (
        "Không có trong SQLite"
    )
    candidate_material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjffarcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    forged[0]["selected_candidate_id"] = candidate["candidate_id"]
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="candidate does not replay exactly",
    ):
        validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=forged,
        )


def test_query_binding_rejects_candidate_deletion_and_frontier_drift(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _fixture(tmp_path)
    deleted = copy.deepcopy(trials)
    deleted[0].update(
        {
            "candidate_count": 0,
            "candidates": [],
            "mappings": [],
            "selected_candidate_id": None,
            "status": NOT_OBSERVED,
        }
    )
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="needs exactly one candidate",
    ):
        _sweep(evidence, deleted)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="does not replay"):
        validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=list(reversed(selected)),
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
        )


def test_indexed_query_replays_two_branch_leased_variant_and_tangible_negative(
    tmp_path,
) -> None:
    database = tmp_path / "leased-pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    leased_page = _leased_page()
    leased = _ingest(database, page_json=leased_page)
    tangible = _ingest(
        database,
        image_sha256="4" * 64,
        physical_page=2,
        prompt_sha256="5" * 64,
        source_logical_name="tangible.pdf",
        source_sha256="6" * 64,
        page_json=_page(),
    )
    selected = [leased["page_json_version_id"], tangible["page_json_version_id"]]
    compiled = _compiled_leased()
    evidence = query_selected_fixed_asset_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 1,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    cluster = evidence["accepted_clusters"][0]
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={leased["page_json_version_id"]: leased_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
            cluster["component_regions"], control_regions=cluster["control_regions"]
        ),
    )
    trials = [
        _trial(evidence["selected_document_axis"][0], candidate, READY),
        _trial(evidence["selected_document_axis"][1], None, NOT_OBSERVED),
    ]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "b" * 64,
        topology_spec=_json("tm-leased-fixed-assets-topology-v1.json"),
        evaluation_spec=_json("tm-leased-fixed-assets-evaluation-v1.json"),
        schema_binding_spec=_json("tm-leased-fixed-assets-schema-binding-v1.json"),
        trials=trials,
        indexed_query_evidence=evidence,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    assert (
        validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )


def test_zero_accepted_leased_frontier_rejects_foreign_ready_candidate(tmp_path) -> None:
    database = tmp_path / "leased-empty-frontier.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    leased_page = _leased_page()
    leased = _ingest(database, page_json=leased_page)
    tangible = _ingest(
        database,
        image_sha256="7" * 64,
        physical_page=2,
        prompt_sha256="8" * 64,
        source_logical_name="tangible-only.pdf",
        source_sha256="9" * 64,
        page_json=_page(),
    )
    compiled = _compiled_leased()
    source_evidence = query_selected_fixed_asset_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[leased["page_json_version_id"]],
        compiled_specs=compiled,
    )
    cluster = source_evidence["accepted_clusters"][0]
    foreign_candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={leased["page_json_version_id"]: leased_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
            cluster["component_regions"], control_regions=cluster["control_regions"]
        ),
    )
    empty_evidence = query_selected_fixed_asset_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[tangible["page_json_version_id"]],
        compiled_specs=compiled,
    )
    assert empty_evidence["accepted_clusters"] == []
    forged_trials = [_trial(empty_evidence["selected_document_axis"][0], foreign_candidate, READY)]
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="not-observed trial drifted",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "c" * 64,
            topology_spec=_json("tm-leased-fixed-assets-topology-v1.json"),
            evaluation_spec=_json("tm-leased-fixed-assets-evaluation-v1.json"),
            schema_binding_spec=_json("tm-leased-fixed-assets-schema-binding-v1.json"),
            trials=forged_trials,
            indexed_query_evidence=empty_evidence,
        )


def test_indexed_intangible_query_and_full_candidate_replay_include_supplemental_role(
    tmp_path,
) -> None:
    database, selected, evidence, trials, compiled = _intangible_fixture(tmp_path)
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 1,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    supplemental = [
        mapping
        for mapping in trials[0]["mappings"]
        if mapping["role"] == "FULLY_AMORTIZED_STILL_IN_USE"
    ]
    assert [
        (mapping["report_norm_id"], mapping["cell"]["coefficient"]) for mapping in supplemental
    ] == [(6069, 1234)]
    assert (
        validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )


def test_sqlite_replay_rejects_coherent_supplemental_source_locator_drift(tmp_path) -> None:
    database, selected, evidence, trials, compiled = _intangible_fixture(tmp_path)
    forged = copy.deepcopy(trials)
    candidate = forged[0]["candidates"][0]
    observation = candidate["closure_receipt"]["supplemental_disclosure_receipt"]["observations"][0]
    observation["source_locator"]["table_id"] = "t999"
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "FULLY_AMORTIZED_STILL_IN_USE"
    )
    mapping["source_refs"][0]["source_locator"]["table_id"] = "t999"
    mapping_material = {key: value for key, value in mapping.items() if key != "item_mapping_id"}
    mapping["item_mapping_id"] = "gjffarimv1:item:" + canonical_json_sha256_v1(mapping_material)
    candidate_material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjffarcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    forged[0]["selected_candidate_id"] = candidate["candidate_id"]
    forged[0]["mappings"] = copy.deepcopy(candidate["mappings"])
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="candidate does not replay exactly",
    ):
        validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=forged,
        )


def test_indexed_investment_property_replays_exact_multi_component_population(tmp_path) -> None:
    database = tmp_path / "investment-property-pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _investment_property_page(
        tables=[
            _investment_summary_table(),
            _investment_property_table(),
            _investment_cost_fragment(),
        ]
    )
    ingested = _ingest(database, page_json=page)
    selected = [ingested["page_json_version_id"]]
    compiled = _compiled_investment_property()
    evidence = query_selected_fixed_asset_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        compiled_specs=compiled,
    )
    assert evidence["query_receipt"]["disposition_counts"] == {
        NOT_OBSERVED: 0,
        READY: 1,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    }
    cluster = evidence["accepted_clusters"][0]
    assert len(cluster["component_regions"]) == 3
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=cluster["control_regions"]
    )
    assert receipt["format_version"].endswith("V2")
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={ingested["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    trials = [_trial(evidence["selected_document_axis"][0], candidate, READY)]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "d" * 64,
        topology_spec=_json("tm-investment-property-topology-v1.json"),
        evaluation_spec=_json("tm-investment-property-evaluation-v1.json"),
        schema_binding_spec=_json("tm-investment-property-schema-binding-v1.json"),
        trials=trials,
        indexed_query_evidence=evidence,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    assert (
        validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=evidence,
            trials=trials,
        )
        == trials
    )
    forged = copy.deepcopy(evidence)
    forged_cluster = forged["accepted_clusters"][0]
    forged_cluster["summary_control_comparison_receipt"]["status"] = "FORGED_SELF_SEAL"
    forged_cluster_material = {
        key: value for key, value in forged_cluster.items() if key != "cluster_id"
    }
    forged_cluster["cluster_id"] = "gjffarfcv1:cluster:" + canonical_json_sha256_v1(
        forged_cluster_material
    )
    disposition_cluster = forged["candidate_dispositions"][0]["cluster"]
    disposition_cluster["summary_control_comparison_receipt"]["status"] = "FORGED_SELF_SEAL"
    disposition_material = {
        key: value for key, value in disposition_cluster.items() if key != "cluster_id"
    }
    disposition_cluster["cluster_id"] = "gjffarfcv1:cluster:" + canonical_json_sha256_v1(
        disposition_material
    )
    forged["query_receipt"]["accepted_cluster_axis_sha256"] = canonical_json_sha256_v1(
        forged["accepted_clusters"]
    )
    forged["query_receipt"]["candidate_disposition_axis_sha256"] = canonical_json_sha256_v1(
        forged["candidate_dispositions"]
    )
    forged_material = {key: value for key, value in forged.items() if key != "query_evidence_id"}
    forged["query_evidence_id"] = "gjffareqv1:evidence:" + canonical_json_sha256_v1(forged_material)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="does not replay"):
        validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected,
            compiled_specs=compiled,
            indexed_query_evidence=forged,
        )
