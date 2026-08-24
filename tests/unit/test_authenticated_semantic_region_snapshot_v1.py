from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

import bctc_ai.evaluation.loan_enterprise_family12_graph_v1 as family12_module
from bctc_ai.evaluation.authenticated_semantic_region_snapshot_v1 import (
    AuthenticatedSemanticRegionSnapshotV1Error,
    FamilyFirstRegionReceiptContractV2Error,
    build_authenticated_semantic_region_snapshot_v1,
    validate_authenticated_semantic_region_snapshot_replay_v1,
    validate_family_first_region_retrieval_receipt_v2,
)
from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
    FamilyFirstRegionRetrievalV1Error,
    family_first_region_query_spec_id_v2,
)
from bctc_ai.evaluation.loan_enterprise_family12_graph_v1 import (
    LoanEnterpriseFamily12GraphV1Error,
    build_loan_enterprise_family12_authenticated_snapshot_graphs_v1,
    build_loan_enterprise_family12_region_query_spec_v2,
    validate_loan_enterprise_family12_authenticated_snapshot_graphs_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_RETRIEVAL_CLAIM = (
    "AUTHENTICATED_IMMUTABLE_SQLITE_EXACT_ACCENTLESS_FTS5_TRIGRAM_AND_"
    "BOUNDED_EDIT_REGION_SHORTLIST_COMPLETE_DOCUMENT_DENOMINATOR_ONLY_NO_"
    "ABSENCE_MAPPING_NUMERIC_ACCOUNTING_SCHEMA_OR_EXPORT_AUTHORITY"
)
_RETRIEVAL_AUTHORITY = {
    "absence_authority": False,
    "accounting_authority": False,
    "cache_or_receipt_self_authenticating": False,
    "complete_document_outcome_denominator": True,
    "historical_variant_semantic_assignment_authority": False,
    "historical_variant_support_presence_is_mapping_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "shortlist_authority": True,
    "source_database_must_be_authenticated": True,
}


def _ref(label: str) -> dict[str, object]:
    payload = label.encode()
    return {
        "path": f"fixture/{label}.bin",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _line(ordinal: int, text: str, *, y: int, numeric: str = "") -> dict:
    return {
        "bbox": [40 if not numeric else 730, y, 650 if not numeric else 850, y + 28],
        "crop_ref": _ref(f"crop-{ordinal}-{y}"),
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.91},
        "sample_id": f"sample-{ordinal}-{y}",
        "vietocr_text": text,
    }


def _packet(
    *,
    page_count: int,
    line_count: int,
    ordinal: int = 1,
    suffix: str = "positive",
) -> dict:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": "SYNTHETIC",
        "document_evidence_root_sha256": hashlib.sha256(f"evidence-{suffix}".encode()).hexdigest(),
        "document_id": f"document-{suffix}",
        "document_ordinal": ordinal,
        "line_count": line_count,
        "page_count": page_count,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": _ref(f"source-{suffix}"),
        "year": 2025,
    }
    return {
        **material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(material),
    }


def _snapshot(
    pages: dict[int, list[dict]],
    *,
    ordinal: int = 1,
    packet_page_count: int | None = None,
    suffix: str = "positive",
) -> dict:
    selected_pages = sorted(pages)
    dimensions = [
        {
            "physical_page": page,
            "pixel_height": 1_400,
            "pixel_width": 1_000,
            "render_sha256": hashlib.sha256(f"render-{page}".encode()).hexdigest(),
            "render_size_bytes": 100 + page,
        }
        for page in selected_pages
    ]
    joined_pages = [
        {"lines": pages[page], "page_sequence": page, "page_width": 1_000}
        for page in selected_pages
    ]
    packet = _packet(
        page_count=packet_page_count or max(selected_pages),
        line_count=sum(len(lines) for lines in pages.values()),
        ordinal=ordinal,
        suffix=suffix,
    )
    selection_material = {
        "document_id": packet["document_id"],
        "document_ordinal": ordinal,
        "joined_pages": joined_pages,
        "selected_page_dimensions": dimensions,
    }
    selection_id = "ffoqcv1:selection:" + canonical_json_sha256_v1(selection_material)
    material = {
        "document_packet": packet,
        "joined_pages": joined_pages,
        "manifest_id": "ffdesv1:manifest:fixture",
        "query_selection_id": selection_id,
        "selected_page_dimensions": dimensions,
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return {
        **material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(material),
    }


def _positive_snapshot(*, ordinal: int = 1, suffix: str = "positive") -> dict:
    return _snapshot(
        {
            1: [
                _line(0, "Cho vay khách hàng", y=40),
                _line(1, "Loại hình doanh nghiệp", y=110),
                _line(2, "Công ty TNHH", y=200),
                _line(3, "100", y=200, numeric="100"),
            ]
        },
        ordinal=ordinal,
        suffix=suffix,
    )


def _receipt(
    snapshots: dict | list[dict],
    *,
    fallback_ordinals: set[int] | None = None,
) -> dict:
    if type(snapshots) is dict:
        snapshots = [snapshots]
    fallback_ordinals = fallback_ordinals or set()
    query = build_loan_enterprise_family12_region_query_spec_v2(_ROOT)
    outcomes = []
    for ordinal, snapshot in enumerate(snapshots, 1):
        packet = snapshot["document_packet"]
        selected_pages = [item["page_sequence"] for item in snapshot["joined_pages"]]
        fallback = ordinal in fallback_ordinals
        outcome_material = {
            "blocked_expansions": [],
            "candidate_region_results": [],
            "chosen_seed_groups": [],
            "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
            "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
            "document_id": packet["document_id"],
            "document_line_count": packet["line_count"],
            "document_ordinal": ordinal,
            "document_packet_id": packet["packet_id"],
            "document_page_count": packet["page_count"],
            "fallback_reason": ("FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP" if fallback else None),
            "index_outcome": ("ZERO_VALID_SEED_GROUP" if fallback else "NONZERO_VALID_SEED_GROUP"),
            "local_occurrences": [],
            "local_required_group_results": [],
            "page_explanations": [],
            "requires_full_document_review": fallback,
            "seed_group_results": [],
            "seed_occurrences": [],
            "selected_pages": selected_pages,
            "selection_mode": (
                "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
                if fallback
                else "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
            ),
            "structural_reset_pages": [],
        }
        outcomes.append(
            {
                **outcome_material,
                "outcome_id": ("fffrrv2:document:" + canonical_json_sha256_v1(outcome_material)),
            }
        )
    query_id = family_first_region_query_spec_id_v2(query)
    material = {
        "authority": copy.deepcopy(_RETRIEVAL_AUTHORITY),
        "claim_boundary": _RETRIEVAL_CLAIM,
        "documents": outcomes,
        "family_id": query["family_id"],
        "format_version": "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2",
        "metrics": {
            "document_count": len(snapshots),
            "fallback_document_count": len(fallback_ordinals),
            "occurrence_count": 0,
            "raw_fts_hit_line_count": 0,
            "raw_rare_trigram_hit_line_count": 0,
            "seed_occurrence_count": 0,
            "selected_page_count": sum(len(snapshot["joined_pages"]) for snapshot in snapshots),
            "source_line_count": sum(
                snapshot["document_packet"]["line_count"] for snapshot in snapshots
            ),
            "source_page_count": sum(
                snapshot["document_packet"]["page_count"] for snapshot in snapshots
            ),
            "zero_validated_hit_document_count": len(fallback_ordinals),
        },
        "planner": {
            "anchor_statistics": [],
            "historical_variant_support_verifications": [],
            "seed_anchor_ids": sorted(
                {anchor_id for group in query["seed_groups"] for anchor_id in group["anchor_ids"]}
            ),
            "strategy": ("DECLARATIVE_ALL_SATISFIED_SEED_GROUP_COVERAGE_THEN_LOCAL_VALIDATION"),
        },
        "query_spec": query,
        "source_binding": {
            "database_ref": _ref("database"),
            "engine_ref": _ref("engine"),
            "manifest_id": snapshots[0]["manifest_id"],
            "query_spec_id": query_id,
            "runtime_determinants": {},
        },
        "state": "DIRECT_RECOMPUTED_COMPLETE_DOCUMENT_REGION_SHORTLIST",
    }
    return {
        **material,
        "receipt_id": "fffrrv2:receipt:" + canonical_json_sha256_v1(material),
    }


def _rehash_snapshot(snapshot: dict) -> None:
    selection_material = {
        "document_id": snapshot["document_packet"]["document_id"],
        "document_ordinal": snapshot["document_packet"]["document_ordinal"],
        "joined_pages": snapshot["joined_pages"],
        "selected_page_dimensions": snapshot["selected_page_dimensions"],
    }
    snapshot["query_selection_id"] = "ffoqcv1:selection:" + canonical_json_sha256_v1(
        selection_material
    )
    material = copy.deepcopy(snapshot)
    material.pop("snapshot_id")
    snapshot["snapshot_id"] = "ffdesv1:selected:" + canonical_json_sha256_v1(material)


def _rehash_receipt(receipt: dict) -> None:
    for outcome in receipt["documents"]:
        outcome_material = copy.deepcopy(outcome)
        outcome_material.pop("outcome_id")
        outcome["outcome_id"] = "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material)
    material = copy.deepcopy(receipt)
    material.pop("receipt_id")
    receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(material)


def _authenticated_replay(
    monkeypatch: pytest.MonkeyPatch,
    authoritative_receipt: dict,
    authenticated_snapshots: list[dict],
) -> tuple[object, list[dict], list[tuple]]:
    capability = object()
    calls = []
    read_calls = []
    snapshots_by_ordinal = {
        snapshot["document_packet"]["document_ordinal"]: snapshot
        for snapshot in authenticated_snapshots
    }

    def replay(candidate_capability: object, query: dict, candidate_receipt: dict) -> dict:
        calls.append(candidate_receipt)
        if candidate_capability is not capability:
            raise FamilyFirstRegionRetrievalV1Error("wrong live capability")
        if query != authoritative_receipt["query_spec"]:
            raise FamilyFirstRegionRetrievalV1Error("query does not replay")
        if candidate_receipt != authoritative_receipt:
            raise FamilyFirstRegionRetrievalV1Error(
                "region retrieval receipt does not replay from authenticated SQLite"
            )
        return copy.deepcopy(candidate_receipt)

    def read(
        candidate_capability: object,
        *,
        document_page_selections: tuple,
    ) -> tuple:
        if candidate_capability is not capability:
            raise FamilyFirstRegionRetrievalV1Error("wrong live capability")
        read_calls.append(document_page_selections)
        snapshots = []
        for ordinal, _selected_pages in document_page_selections:
            snapshot = snapshots_by_ordinal[ordinal]
            snapshots.append(copy.deepcopy(snapshot))
        return tuple(snapshots)

    monkeypatch.setattr(
        family12_module,
        "validate_replayed_authenticated_family_first_region_receipt_v2",
        replay,
    )
    monkeypatch.setattr(
        family12_module.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        read,
    )
    return capability, calls, read_calls


def _build_authenticated_batch(
    monkeypatch: pytest.MonkeyPatch,
    receipt: dict,
    snapshots: list[dict],
) -> tuple[dict, list[dict], list[tuple], object]:
    capability, calls, read_calls = _authenticated_replay(
        monkeypatch,
        receipt,
        snapshots,
    )
    result = build_loan_enterprise_family12_authenticated_snapshot_graphs_v1(
        capability,
        receipt,
    )
    return result, calls, read_calls, capability


def test_generic_bridge_preserves_value_text_and_all_evidence_bindings() -> None:
    snapshot = _positive_snapshot()
    result = build_authenticated_semantic_region_snapshot_v1(snapshot)
    value_line = result["region_pages"][0]["lines"][-1]

    assert value_line["source_text"] == "100"
    assert value_line["vietocr_text"] == "100"
    assert result["line_bindings"][-1]["ppocrv6_surface"] == "100"
    assert result["line_bindings"][-1]["ppocrv6_reader_score"] == 0.91
    assert result["line_bindings"][-1]["sample_id"] == "sample-3-200"
    assert result["line_bindings"][-1]["crop_ref"] == _ref("crop-3-200")
    assert (
        result["page_bindings"][0]["render_ref"]["sha256"]
        == (snapshot["selected_page_dimensions"][0]["render_sha256"])
    )
    assert result["authority"]["numeric_reader_surface_is_numeric_authority"] is False
    assert validate_authenticated_semantic_region_snapshot_replay_v1(result, snapshot) == result


def test_zero_line_page_is_explicit_and_owner_carries_across_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(
        {
            1: [_line(0, "Cho vay khách hàng", y=40)],
            2: [],
            3: [
                _line(0, "Loại hình doanh nghiệp", y=110),
                _line(1, "Công ty TNHH", y=200),
                _line(2, "100", y=200, numeric="100"),
            ],
        },
        suffix="zero-line",
    )
    projection = build_authenticated_semantic_region_snapshot_v1(snapshot)
    receipt = _receipt(snapshot)
    batch, calls, read_calls, _ = _build_authenticated_batch(
        monkeypatch,
        receipt,
        [snapshot],
    )
    result = batch["documents"][0]

    assert [page["page_sequence"] for page in projection["region_pages"]] == [1, 2, 3]
    assert projection["region_pages"][1]["lines"] == []
    assert projection["metrics"]["zero_line_page_count"] == 1
    assert result["graph"]["metrics"]["region_count"] == 1
    assert result["graph"]["metrics"]["cross_page_owner_region_count"] == 1
    assert len(calls) == 1
    assert read_calls == [((1, (1, 2, 3)),)]


def test_provider_reorder_canonicalizes_to_same_projection() -> None:
    snapshot = _snapshot(
        {
            1: [_line(0, "Cho vay khách hàng", y=40)],
            2: [_line(0, "Loại hình doanh nghiệp", y=110), _line(1, "Công ty TNHH", y=200)],
        },
        suffix="reorder",
    )
    reordered = copy.deepcopy(snapshot)
    reordered["joined_pages"].reverse()
    reordered["selected_page_dimensions"].reverse()
    for page in reordered["joined_pages"]:
        page["lines"].reverse()

    assert build_authenticated_semantic_region_snapshot_v1(reordered) == (
        build_authenticated_semantic_region_snapshot_v1(snapshot)
    )


@pytest.mark.parametrize(
    "mutation",
    ["dimension", "packet", "snapshot", "crop", "line"],
)
def test_generic_bridge_rejects_bound_evidence_tamper(mutation: str) -> None:
    snapshot = _positive_snapshot()
    if mutation == "dimension":
        snapshot["selected_page_dimensions"][0]["pixel_height"] += 1
    elif mutation == "packet":
        snapshot["document_packet"]["document_id"] = "forged"
    elif mutation == "snapshot":
        snapshot["snapshot_id"] = "ffdesv1:selected:forged"
    elif mutation == "crop":
        snapshot["joined_pages"][0]["lines"][0]["crop_ref"]["sha256"] = "0" * 64
    else:
        snapshot["joined_pages"][0]["lines"][0]["vietocr_text"] = "forged"

    with pytest.raises(AuthenticatedSemanticRegionSnapshotV1Error):
        build_authenticated_semantic_region_snapshot_v1(snapshot)


def test_f12_batch_exactly_binds_receipt_snapshot_and_graph_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _positive_snapshot()
    receipt = _receipt(snapshot)
    batch, calls, read_calls, capability = _build_authenticated_batch(
        monkeypatch,
        receipt,
        [snapshot],
    )
    result = batch["documents"][0]

    assert result["graph"]["metrics"]["unique_binding_proposal_count"] == 1
    assert result["evidence_binding"]["receipt_id"] == receipt["receipt_id"]
    assert result["evidence_binding"]["snapshot_id"] == snapshot["snapshot_id"]
    assert result["evidence_binding"]["outcome_id"] == receipt["documents"][0]["outcome_id"]
    assert result["authority"]["mapping_authority"] is False
    assert "snapshot_projection" not in result
    projection_binding = result["snapshot_projection_binding"]
    assert projection_binding["projection_id"] == result["evidence_binding"]["projection_id"]
    assert set(projection_binding) == {
        "line_bindings_sha256",
        "metrics",
        "page_bindings_sha256",
        "projection_id",
        "region_pages_sha256",
        "source_binding",
    }
    assert batch["evidence_binding"]["receipt_id"] == receipt["receipt_id"]
    assert batch["authority"]["authenticated_receipt_public_replay_required"] is True
    assert len(calls) == 1
    assert read_calls == [((1, (1,)),)]
    calls.clear()
    read_calls.clear()
    assert (
        validate_loan_enterprise_family12_authenticated_snapshot_graphs_replay_v1(
            batch,
            capability,
            receipt,
        )
        == batch
    )
    assert len(calls) == 1
    assert read_calls == [((1, (1,)),)]


def test_f12_full_fallback_document_remains_bounded_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(
        {1: [_line(0, "Nội dung khác", y=40)], 2: []},
        suffix="fallback",
    )
    receipt = _receipt(snapshot, fallback_ordinals={1})
    batch, calls, read_calls, _ = _build_authenticated_batch(
        monkeypatch,
        receipt,
        [snapshot],
    )
    result = batch["documents"][0]

    assert result["outcome"]["fallback_reason"] == ("FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP")
    assert result["graph"]["metrics"]["region_count"] == 0
    assert result["graph"]["metrics"]["bounded_absence_count"] == 1
    assert batch["metrics"]["fallback_document_count"] == 1
    assert len(calls) == 1
    assert read_calls == [((1, (1, 2)),)]


def test_f12_batch_rejects_omitted_page_and_receipt_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full = _snapshot(
        {
            1: [_line(0, "Cho vay khách hàng", y=40)],
            2: [],
            3: [_line(0, "Loại hình doanh nghiệp", y=110)],
        },
        suffix="full-selection",
    )
    receipt = _receipt(full)
    omitted = _snapshot(
        {1: full["joined_pages"][0]["lines"], 3: full["joined_pages"][2]["lines"]},
        packet_page_count=3,
        suffix="full-selection",
    )
    omitted["document_packet"] = copy.deepcopy(full["document_packet"])
    _rehash_snapshot(omitted)
    capability, calls, read_calls = _authenticated_replay(
        monkeypatch,
        receipt,
        [omitted],
    )
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="binding drifted"):
        build_loan_enterprise_family12_authenticated_snapshot_graphs_v1(
            capability,
            receipt,
        )
    assert len(calls) == 1
    assert read_calls == [((1, (1, 2, 3)),)]

    forged_receipt = copy.deepcopy(receipt)
    forged_receipt["documents"][0]["document_line_count"] += 1
    _rehash_receipt(forged_receipt)
    calls.clear()
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="replay|drifted"):
        build_loan_enterprise_family12_authenticated_snapshot_graphs_v1(
            capability,
            forged_receipt,
        )
    assert len(calls) == 1


def test_f12_batch_replays_receipt_once_for_complete_source_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshots = [
        _positive_snapshot(ordinal=ordinal, suffix=f"document-{ordinal}")
        for ordinal in range(1, 19)
    ]
    receipt = _receipt(snapshots)
    batch, calls, read_calls, _ = _build_authenticated_batch(
        monkeypatch,
        receipt,
        snapshots,
    )

    assert len(calls) == 1
    assert [len(call) for call in read_calls] == [16, 2]
    assert [item["document_ordinal"] for item in batch["documents"]] == list(range(1, 19))
    assert [item["document_id"] for item in batch["documents"]] == [
        snapshot["document_packet"]["document_id"] for snapshot in snapshots
    ]
    assert batch["metrics"]["document_count"] == 18


def test_f12_batch_live_replay_rejects_coherent_fallback_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_snapshot = _snapshot(
        {1: [_line(0, "Nội dung khác", y=40)], 2: []},
        suffix="fallback-downgrade",
    )
    authoritative_receipt = _receipt(full_snapshot, fallback_ordinals={1})
    omitted_snapshot = _snapshot(
        {1: full_snapshot["joined_pages"][0]["lines"]},
        packet_page_count=2,
        suffix="fallback-downgrade",
    )
    omitted_snapshot["document_packet"] = copy.deepcopy(full_snapshot["document_packet"])
    _rehash_snapshot(omitted_snapshot)
    downgraded_receipt = _receipt(omitted_snapshot)
    capability, calls, read_calls = _authenticated_replay(
        monkeypatch,
        authoritative_receipt,
        [full_snapshot],
    )

    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="authenticated SQLite"):
        build_loan_enterprise_family12_authenticated_snapshot_graphs_v1(
            capability,
            downgraded_receipt,
        )
    assert len(calls) == 1
    assert read_calls == []
    with pytest.raises(TypeError):
        build_loan_enterprise_family12_authenticated_snapshot_graphs_v1(
            capability,
            authoritative_receipt,
            [omitted_snapshot],
        )


@pytest.mark.parametrize("field", ["authority", "claim_boundary"])
def test_generic_receipt_rejects_coordinated_authority_or_claim_rehash(field: str) -> None:
    snapshot = _positive_snapshot()
    receipt = _receipt(snapshot)
    if field == "authority":
        receipt["authority"]["mapping_authority"] = True
    else:
        receipt["claim_boundary"] = "FORGED_CLAIM"
    _rehash_receipt(receipt)

    query = build_loan_enterprise_family12_region_query_spec_v2(_ROOT)
    with pytest.raises(FamilyFirstRegionReceiptContractV2Error, match="identity drifted"):
        validate_family_first_region_retrieval_receipt_v2(
            receipt,
            query,
            query["family_id"],
        )


def test_pure_replays_reject_coherently_self_rehashed_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _positive_snapshot()
    projection = build_authenticated_semantic_region_snapshot_v1(snapshot)
    forged_projection = copy.deepcopy(projection)
    forged_projection["metrics"]["line_count"] += 1
    material = copy.deepcopy(forged_projection)
    material.pop("projection_id")
    forged_projection["projection_id"] = "asrsv1:projection:" + canonical_json_sha256_v1(material)
    with pytest.raises(AuthenticatedSemanticRegionSnapshotV1Error, match="replay"):
        validate_authenticated_semantic_region_snapshot_replay_v1(forged_projection, snapshot)

    receipt = _receipt(snapshot)
    batch, calls, read_calls, capability = _build_authenticated_batch(
        monkeypatch,
        receipt,
        [snapshot],
    )
    forged_batch = copy.deepcopy(batch)
    forged_batch["metrics"]["line_count"] += 1
    material = copy.deepcopy(forged_batch)
    material.pop("result_id")
    forged_batch["result_id"] = "lef12asv1:batch:" + canonical_json_sha256_v1(material)
    calls.clear()
    read_calls.clear()
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="replay"):
        validate_loan_enterprise_family12_authenticated_snapshot_graphs_replay_v1(
            forged_batch,
            capability,
            receipt,
        )
    assert len(calls) == 1
    assert read_calls == [((1, (1,)),)]
