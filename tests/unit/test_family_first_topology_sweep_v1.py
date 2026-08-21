from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology
from bctc_ai.evaluation import family_first_topology_sweep_v1 as sweep
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Tiền mặt bằng VND"],
                "presence": "REQUIRED",
                "role": "CASH_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền mặt bằng ngoại tệ"],
                "presence": "REQUIRED",
                "role": "CASH_FOREIGN",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Vàng tiền tệ"],
                "presence": "OPTIONAL",
                "role": "MONETARY_GOLD",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": topology.SPEC_FORMAT_VERSION,
        "hard_negative_aliases": ["Tiền và các khoản tương đương tiền"],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền mặt, vàng bạc, đá quý"],
            "resolution_mode": "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER",
            "role": "CASH_PRECIOUS_METALS",
        },
        "structural_reset_aliases": ["Tiền gửi tại Ngân hàng Nhà nước"],
    }


def _document(ordinal: int, *, matched: bool) -> dict[str, object]:
    labels = (
        ["Tiền mặt, vàng bạc, đá quý", "Tiền mặt bằng VND", "Tiền mặt bằng ngoại tệ"]
        if matched
        else ["Thuyết minh khác"]
    )
    return {
        "document_ordinal": ordinal,
        "pages": [
            {
                "lines": [
                    {
                        "line_ordinal": line_ordinal,
                        "source_bbox_raw_pixels": [
                            10,
                            10 + 30 * line_ordinal,
                            300,
                            30 + 30 * line_ordinal,
                        ],
                        "vietocr_text": label,
                    }
                    for line_ordinal, label in enumerate(labels)
                ],
                "physical_page": 1,
            }
        ],
        "private_provenance": {
            "bank": "ACB" if ordinal == 1 else "MBB",
            "period": "Q1",
            "scope": "CONSOLIDATED",
            "year": 2026,
        },
        "source_pdf_ref": {
            "path": f"source-{ordinal}.pdf",
            "sha256": f"{ordinal:064x}",
            "size_bytes": ordinal,
        },
    }


def test_sweep_routes_no_provenance_into_shared_matcher(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sweep,
        "project_authenticated_family_first_semantic_index_v1",
        lambda _cap: {
            "index_id": "ffsiv1:index:" + "1" * 64,
            "metrics": {"document_count": 2},
        },
    )
    documents = {1: _document(1, matched=True), 2: _document(2, matched=False)}
    monkeypatch.setattr(
        sweep,
        "read_authenticated_family_first_semantic_document_v1",
        lambda _cap, *, document_ordinal: copy.deepcopy(documents[document_ordinal]),
    )
    original = sweep.topology_v1.build_accounting_family_topology_scan_v1

    def guarded(pages, family_spec):
        assert "bank" not in repr(pages).lower()
        assert "source-" not in repr(pages)
        return original(pages, family_spec)

    monkeypatch.setattr(sweep.topology_v1, "build_accounting_family_topology_scan_v1", guarded)
    result = sweep.build_authenticated_family_first_topology_sweep_v1(object(), _spec())
    assert result["metrics"] == {
        "accepted_unique_topology_proposal_count": 1,
        "document_count": 2,
        "mapping_verified_count": 0,
        "multiple_or_nonunique_document_count": 0,
        "no_complete_region_document_count": 0,
        "not_observed_count": 1,
        "unresolved_document_count": 0,
    }
    assert result["trials"][0]["private_provenance"]["bank"] == "ACB"
    assert result["trials"][0]["topology_scan"]["status"] == ("ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL")


def test_sweep_shape_rejects_coordinated_metric_elevation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sweep,
        "project_authenticated_family_first_semantic_index_v1",
        lambda _cap: {
            "index_id": "ffsiv1:index:" + "1" * 64,
            "metrics": {"document_count": 1},
        },
    )
    monkeypatch.setattr(
        sweep,
        "read_authenticated_family_first_semantic_document_v1",
        lambda *_args, **_kwargs: _document(1, matched=True),
    )
    result = sweep.build_authenticated_family_first_topology_sweep_v1(object(), _spec())
    tampered = copy.deepcopy(result)
    tampered["metrics"]["mapping_verified_count"] = 1
    material = copy.deepcopy(tampered)
    material.pop("sweep_id")
    tampered["sweep_id"] = "fftsv1:sweep:" + canonical_json_sha256_v1(material)
    with pytest.raises(sweep.FamilyFirstTopologySweepV1Error, match="metrics"):
        sweep._validate(tampered)
