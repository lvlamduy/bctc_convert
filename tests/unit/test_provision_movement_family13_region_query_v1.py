from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1
from bctc_ai.evaluation import family_first_region_retrieval_v1 as retrieval_v1
from bctc_ai.evaluation.accounting_family_topology_v1 import (
    build_accounting_family_topology_scan_v1,
)
from bctc_ai.evaluation.provision_movement_family13_region_query_v1 import (
    CLAIM_BOUNDARY,
    PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_SPEC_V2,
    PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1,
    RECOVERY_STATUS_V1,
    ProvisionMovementFamily13RegionQueryV1Error,
    build_provision_movement_family13_region_query_spec_v2,
    build_provision_movement_family13_schema_role_declaration_v1,
    build_provision_movement_family13_topology_spec_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENGINE_REF = {"path": "synthetic-engine.py", "sha256": "7" * 64, "size_bytes": 1}


def _line(index: int, text: str) -> dict[str, object]:
    return {
        "bbox": [40, 30 * index, 900, 30 * index + 22],
        "source_line_index": index,
        "source_text": None,
        "vietocr_text": text,
    }


def _page(surfaces: list[str], page_sequence: int) -> dict[str, object]:
    return {
        "lines": [_line(index, surface) for index, surface in enumerate(surfaces)],
        "page_sequence": page_sequence,
    }


def _state(
    path: Path,
    pages: dict[int, list[str]],
    *,
    reverse_provider_rows: bool = False,
) -> SimpleNamespace:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    cache_v1._create_schema(connection)
    page_count = max(pages)
    line_count = sum(len(lines) for lines in pages.values())
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            1,
            "synthetic-family13-document",
            "SYNTHETIC_BANK_BLIND",
            2025,
            "ANNUAL",
            "CONSOLIDATED",
            "synthetic.pdf",
            hashlib.sha256(b"synthetic-family13-pdf").hexdigest(),
            1,
            page_count,
            line_count,
        ),
    )
    for physical_page in range(1, page_count + 1):
        lines = pages.get(physical_page, [])
        connection.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                physical_page,
                len(lines),
                1_000,
                1_400,
                "4" * 64,
                1,
                f"page-{physical_page}.json",
                "5" * 64,
                1,
            ),
        )
    source_rows = [
        (physical_page, line_ordinal, text)
        for physical_page in range(1, page_count + 1)
        for line_ordinal, text in enumerate(pages.get(physical_page, []))
    ]
    line_ids = {
        (physical_page, line_ordinal): ordinal
        for ordinal, (physical_page, line_ordinal, _text) in enumerate(source_rows, 1)
    }
    provider_rows = list(reversed(source_rows)) if reverse_provider_rows else source_rows
    for physical_page, line_ordinal, text in provider_rows:
        line_id = line_ids[(physical_page, line_ordinal)]
        connection.execute(
            "INSERT INTO lines VALUES (" + ",".join("?" for _item in range(20)) + ")",
            (
                line_id,
                1,
                physical_page,
                line_ordinal,
                f"sample-{line_id:06d}",
                20,
                40 + 35 * line_ordinal,
                800,
                68 + 35 * line_ordinal,
                f"crop-{line_id}.png",
                "6" * 64,
                1,
                text,
                text,
                retrieval_v1._accentless(text),
                0.9,
                512,
                32,
                "",
                0.8,
            ),
        )
    connection.execute(
        "INSERT INTO line_search(rowid, vietocr_text, accentless_text) "
        "SELECT line_id, vietocr_text, accentless_text FROM lines"
    )
    metadata = {
        "authority": {},
        "cache_id": "synthetic-family13-cache",
        "document_count": 1,
        "format_version": cache_v1.CACHE_FORMAT_VERSION,
        "line_count": line_count,
        "page_count": page_count,
        "schema_version": 1,
        "sources": {},
    }
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            (key, json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
            for key, value in metadata.items()
        ],
    )
    connection.commit()
    connection.close()
    payload = path.read_bytes()
    packet = {
        "document_evidence_root_sha256": hashlib.sha256(b"synthetic-evidence").hexdigest(),
        "document_id": "synthetic-family13-document",
        "document_ordinal": 1,
        "line_count": line_count,
        "packet_id": "synthetic-family13-packet",
        "page_count": page_count,
    }
    return SimpleNamespace(
        database_path=path,
        manifest={
            "database_ref": {
                "path": path.name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            },
            "documents": [packet],
            "manifest_id": "synthetic-family13-manifest",
            "metrics": {
                "document_count": 1,
                "line_count": line_count,
                "page_count": page_count,
            },
        },
        root=_PROJECT_ROOT,
    )


def _retrieve(
    path: Path,
    pages: dict[int, list[str]],
    *,
    query: dict[str, Any] | None = None,
    reverse_provider_rows: bool = False,
) -> dict[str, Any]:
    query = query or build_provision_movement_family13_region_query_spec_v2(_PROJECT_ROOT)
    return retrieval_v1._retrieve_from_state(
        _state(path, pages, reverse_provider_rows=reverse_provider_rows),
        query,
        engine_ref=_ENGINE_REF,
    )


def _outcome(receipt: dict[str, Any]) -> dict[str, Any]:
    return receipt["documents"][0]


def _all_keys(value: Any) -> set[str]:
    if type(value) is dict:
        return set(value) | set().union(*(_all_keys(item) for item in value.values()), set())
    if type(value) is list:
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def _rehash_document_and_receipt(receipt: dict[str, Any]) -> None:
    document_material = copy.deepcopy(receipt["documents"][0])
    document_material.pop("outcome_id")
    receipt["documents"][0]["outcome_id"] = "fffrrv2:document:" + canonical_json_sha256_v1(
        document_material
    )
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material)


def test_topology_is_nonadditive_triple_and_retains_both_decrease_leaves() -> None:
    topology = build_provision_movement_family13_topology_spec_v1()
    declaration = build_provision_movement_family13_schema_role_declaration_v1()
    by_role = {child["role"]: child for child in topology["children"]}

    assert topology["format_version"] == "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3"
    assert topology["parent"]["resolution_mode"] == "EXPLICIT_ONLY"
    assert topology["parent"]["aliases"] == [
        "Dự phòng rủi ro cho vay khách hàng",
        "Biến động số dư dự phòng rủi ro cho vay khách hàng",
        "Biến động số dư dự phòng rủi ro cho vay KH",
    ]
    assert topology["limits"] == {
        "max_cluster_span_lines": 96,
        "max_continuation_pages": 1,
        "max_label_line_span": 3,
    }
    assert topology["required_role_combinations"] == [
        ["OPENING_BALANCE_ROW", "PROVISION_OR_REVERSAL_ROW", "CLOSING_BALANCE_ROW"]
    ]
    assert all(
        child["role_kind"] == "NONADDITIVE_CHILD"
        for child in topology["children"]
        if child["role"].endswith("_ROW")
    )
    assert by_role["GENERAL_PROVISION_LANE"]["role_kind"] == "STRUCTURAL_GROUP"
    assert by_role["SPECIFIC_PROVISION_LANE"]["role_kind"] == "STRUCTURAL_GROUP"
    assert declaration["root_report_norm_id"] == 783
    assert declaration["lanes"]["GENERAL"]["DECREASE"] == 789
    assert declaration["lanes"]["SPECIFIC"]["DECREASE"] == 797
    assert not any(declaration["authority"].values())
    forbidden = {
        "accounting_equation",
        "mapping_authority",
        "numeric_authority",
        "report_norm_id",
        "signed_value",
        "unit",
    }
    assert forbidden.isdisjoint(_all_keys(topology))

    topology["children"][0]["role"] = "TAMPERED"
    declaration["lanes"]["GENERAL"]["DECREASE"] = 0
    assert build_provision_movement_family13_topology_spec_v1()["children"][0]["role"] != (
        "TAMPERED"
    )
    assert (
        build_provision_movement_family13_schema_role_declaration_v1()["lanes"]["GENERAL"][
            "DECREASE"
        ]
        == 789
    )


def test_topology_accepts_exact_triple_and_one_role_deficit_continuation() -> None:
    same_page = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Dự phòng rủi ro cho vay khách hàng",
                    "Số dư đầu kỳ",
                    "Trích lập dự phòng trong kỳ",
                    "Số dư cuối kỳ",
                ],
                1,
            )
        ],
        build_provision_movement_family13_topology_spec_v1(),
    )
    continued = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Dự phòng rủi ro cho vay khách hàng",
                    "Số dư đầu năm",
                    "Trích lập dự phòng trong năm",
                ],
                1,
            ),
            _page(["Số dư cuối năm"], 2),
        ],
        build_provision_movement_family13_topology_spec_v1(),
    )

    assert same_page["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert same_page["regions"][0]["minimal_unique_anchor"]["combination_size"] == 2
    assert continued["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert continued["regions"][0]["continuation_page_count"] == 1


def test_topology_reset_prevents_cross_family_triple() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Dự phòng rủi ro cho vay khách hàng",
                    "Số dư đầu kỳ",
                    "Hoạt động mua nợ",
                    "Trích lập dự phòng trong kỳ",
                    "Số dư cuối kỳ",
                ],
                1,
            )
        ],
        build_provision_movement_family13_topology_spec_v1(),
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_region_count"] == 0


def test_query_contract_is_strict_primary_only_and_fail_closed() -> None:
    query = build_provision_movement_family13_region_query_spec_v2(_PROJECT_ROOT)

    assert query == PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_SPEC_V2
    assert query["family_id"] == "PROVISION_MOVEMENT_ROLLFORWARD"
    assert query["neighbor_pages_before"] == 2
    assert query["neighbor_pages_after"] == 1
    assert query["window_line_span"] == 1
    assert query["zero_hit_policy"] == "FULL_DOCUMENT_FALLBACK"
    assert query["seed_groups"] == [
        {
            "anchor_ids": ["PRIMARY_OWNER_01", "PRIMARY_OWNER_02", "PRIMARY_OWNER_03"],
            "group_id": "PRIMARY_PROVISION_MOVEMENT_OWNER",
            "mode": "ANY",
            "page_relation": "SAME_PAGE",
            "priority": 1,
        }
    ]
    assert {group["group_id"] for group in query["local_required_groups"]} == {
        "CORE_MOVEMENT_ROLE_LOCAL"
    }
    assert {anchor["role"] for anchor in query["anchors"]} == {
        "HARD_NEGATIVE",
        "OWNER",
        "TARGET",
    }
    assert all(
        not anchor["anchor_id"].startswith(("SECONDARY_", "LOAN_POPULATION_", "RESCUE_"))
        for anchor in query["anchors"]
    )
    assert "SHORTLIST_ONLY" in CLAIM_BOUNDARY
    assert "NO_COMPLETE_FAMILY_RETRIEVAL_ABSENCE" in CLAIM_BOUNDARY
    assert RECOVERY_STATUS_V1 == {
        "absence_authority": False,
        "branchless_recovery": "NOT_IMPLEMENTED_PENDING_RESET_FENCED_INTERVAL_PRIMITIVE",
        "complete_family_retrieval_authority": False,
        "indexed_result_requirement": "FULL_DOCUMENT_RESET_FENCED_TOPOLOGY_AND_TERMINAL_ORACLE",
        "same_page_reset_interval_fencing": "SAME_PAGE_RESET_INTERVAL_FENCING_NOT_IMPLEMENTED",
        "secondary_owner_recovery": "NOT_IMPLEMENTED_PENDING_RESET_FENCED_INTERVAL_PRIMITIVE",
        "shortlist_authority": True,
    }
    assert not {
        "absence_authority",
        "mapping_authority",
        "numeric_authority",
        "report_norm_id",
        "schema_authority",
    } & _all_keys(query)


def test_primary_owner_selects_only_before_two_after_one_region(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "primary.sqlite3",
            {
                1: ["Nội dung trước hai trang"],
                2: ["Nội dung trước một trang"],
                3: ["Biến động số dư dự phòng rủi ro cho vay KH", "Số dư đầu kỳ"],
                4: ["Nội dung tiếp theo"],
                5: ["Nội dung ngoài vùng"],
            },
        )
    )

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [1, 2, 3, 4]
    assert outcome["requires_full_document_review"] is False
    assert all(item["status"] == "SATISFIED" for item in outcome["local_required_group_results"])


def test_generic_secondary_with_complete_core_is_not_a_query_or_topology_owner(
    tmp_path: Path,
) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "secondary.sqlite3",
            {
                1: ["Nội dung trước"],
                2: [
                    "Cho vay khách hàng",
                    "Thay đổi dự phòng rủi ro tín dụng",
                    "Số dư đầu kỳ",
                    "Trích lập dự phòng trong kỳ",
                    "Số dư cuối kỳ",
                ],
                3: ["Nội dung sau"],
            },
        )
    )
    topology = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Thay đổi dự phòng rủi ro tín dụng",
                    "Số dư đầu kỳ",
                    "Trích lập dự phòng trong kỳ",
                    "Số dư cuối kỳ",
                ],
                1,
            )
        ],
        build_provision_movement_family13_topology_spec_v1(),
    )

    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert outcome["requires_full_document_review"] is True
    assert topology["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"


def test_same_page_reset_auditor_repro_is_disclosed_indexed_candidate_only(
    tmp_path: Path,
) -> None:
    receipt = _retrieve(
        tmp_path / "same-page-reset.sqlite3",
        {
            1: [
                "Hoạt động mua nợ",
                "Dự phòng rủi ro cho vay khách hàng",
                "Số dư đầu kỳ",
            ],
            2: ["Sau"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["structural_reset_pages"] == [1]
    assert outcome["requires_full_document_review"] is False
    assert RECOVERY_STATUS_V1["same_page_reset_interval_fencing"] == (
        "SAME_PAGE_RESET_INTERVAL_FENCING_NOT_IMPLEMENTED"
    )
    assert RECOVERY_STATUS_V1["indexed_result_requirement"] == (
        "FULL_DOCUMENT_RESET_FENCED_TOPOLOGY_AND_TERMINAL_ORACLE"
    )
    assert receipt["authority"]["shortlist_authority"] is True
    assert receipt["authority"]["absence_authority"] is False


def test_hard_negative_embedding_primary_is_candidate_only_and_topology_rejects(
    tmp_path: Path,
) -> None:
    lines = [
        "Dự phòng rủi ro cho vay khách hàng",
        "Số dư đầu kỳ",
        "Chính sách dự phòng rủi ro tín dụng",
        "Trích lập dự phòng trong kỳ",
        "Số dư cuối kỳ",
    ]
    outcome = _outcome(
        _retrieve(
            tmp_path / "embedded-hard-negative.sqlite3",
            {1: lines, 2: ["Sau"]},
        )
    )
    topology = build_accounting_family_topology_scan_v1(
        [_page(lines, 1)],
        build_provision_movement_family13_topology_spec_v1(),
    )

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["structural_reset_pages"] == [1]
    assert RECOVERY_STATUS_V1["complete_family_retrieval_authority"] is False
    assert topology["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert topology["near_regions"][0]["unresolved_reasons"]


def test_cross_page_loan_and_core_split_cannot_seed_removed_rescue(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "cross-page-split.sqlite3",
            {
                1: ["Cho vay khách hàng"],
                2: ["Số dư đầu kỳ", "Trích lập dự phòng trong kỳ", "Số dư cuối kỳ"],
                3: ["Sau"],
            },
        )
    )

    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert outcome["requires_full_document_review"] is True


def test_reset_fences_primary_from_later_core_roles(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "cross-reset.sqlite3",
            {
                1: ["Dự phòng rủi ro cho vay khách hàng"],
                2: [
                    "Hoạt động mua nợ",
                    "Số dư đầu kỳ",
                    "Trích lập dự phòng trong kỳ",
                    "Số dư cuối kỳ",
                ],
                3: ["Nội dung sau"],
            },
        )
    )

    assert outcome["structural_reset_pages"] == [2]
    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION"
    assert outcome["requires_full_document_review"] is True


def test_zero_and_anchor_query_overflow_both_fall_back_complete_document(
    tmp_path: Path,
) -> None:
    zero = _outcome(
        _retrieve(
            tmp_path / "zero.sqlite3",
            {1: ["Mở đầu"], 2: ["Không có bảng liên quan"], 3: ["Kết thúc"]},
        )
    )
    overflow_query = build_provision_movement_family13_region_query_spec_v2(_PROJECT_ROOT)
    overflow_query["max_hit_lines"] = 1
    overflow = _outcome(
        _retrieve(
            tmp_path / "overflow.sqlite3",
            {
                1: ["Dự phòng rủi ro cho vay khách hàng"],
                2: ["Dự phòng rủi ro cho vay khách hàng"],
                3: ["Kết thúc"],
            },
            query=overflow_query,
        )
    )

    assert zero["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert zero["selected_pages"] == [1, 2, 3]
    assert overflow["selection_mode"] == "FULL_DOCUMENT_FALLBACK_SEED_QUERY_OVERFLOW"
    assert overflow["selected_pages"] == [1, 2, 3]
    assert (
        zero["requires_full_document_review"] is overflow["requires_full_document_review"] is True
    )


def test_provider_reorder_preserves_exact_region_receipt_material(tmp_path: Path) -> None:
    pages = {
        1: ["Nội dung trước"],
        2: ["Dự phòng rủi ro cho vay khách hàng", "Số dư đầu kỳ"],
        3: ["Nội dung sau"],
    }
    ordered = _retrieve(tmp_path / "ordered.sqlite3", pages)
    reordered = _retrieve(tmp_path / "reordered.sqlite3", pages, reverse_provider_rows=True)

    assert ordered["documents"] == reordered["documents"]
    assert ordered["planner"] == reordered["planner"]


def test_literal_refs_query_id_reorder_and_dependency_tamper(tmp_path: Path) -> None:
    query = build_provision_movement_family13_region_query_spec_v2(_PROJECT_ROOT)
    adapter_ref = query["semantic_assignment_adapter_ref"]
    adapter_path = _PROJECT_ROOT / adapter_ref["path"]

    assert retrieval_v1.family_first_region_query_spec_id_v2(query) == (
        "fffrrv2:query:31dc50101db32c2b85cfc9de112bf5f088b6b033ac0a8a9a09926924da45bfe7"
    )
    assert adapter_ref["size_bytes"] == adapter_path.stat().st_size
    assert adapter_ref["sha256"] == hashlib.sha256(adapter_path.read_bytes()).hexdigest()
    for reference in PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1.values():
        path = _PROJECT_ROOT / reference["path"]
        assert reference["size_bytes"] == path.stat().st_size
        assert reference["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    reordered = copy.deepcopy(query)
    reordered["anchors"].reverse()
    with pytest.raises(retrieval_v1.FamilyFirstRegionRetrievalV1Error, match="sorted"):
        retrieval_v1.family_first_region_query_spec_id_v2(reordered)
    forged = copy.deepcopy(query)
    forged["semantic_assignment_adapter_ref"]["sha256"] = "0" * 64
    assert retrieval_v1.family_first_region_query_spec_id_v2(forged) != (
        retrieval_v1.family_first_region_query_spec_id_v2(query)
    )

    copied_root = tmp_path / "copied-root"
    for reference in [
        adapter_ref,
        *PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1.values(),
    ]:
        target = copied_root / reference["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_PROJECT_ROOT / reference["path"], target)
    dependency = PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1[
        "shared_region_retrieval_engine_ref"
    ]
    dependency_path = copied_root / dependency["path"]
    dependency_path.write_bytes(dependency_path.read_bytes() + b"\n")
    with pytest.raises(ProvisionMovementFamily13RegionQueryV1Error, match="trust closure"):
        build_provision_movement_family13_region_query_spec_v2(copied_root)


def test_public_v2_receipt_replay_rejects_coherently_rehashed_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(
        tmp_path / "public-replay.sqlite3",
        {
            1: ["Nội dung trước"],
            2: ["Dự phòng rủi ro cho vay khách hàng", "Số dư đầu kỳ"],
            3: ["Nội dung sau"],
        },
    )
    query = build_provision_movement_family13_region_query_spec_v2(_PROJECT_ROOT)
    monkeypatch.setattr(retrieval_v1.store_v1, "_live_store", lambda _capability: state)
    monkeypatch.setattr(retrieval_v1, "_engine_ref", lambda _root: _ENGINE_REF)
    receipt = retrieval_v1.retrieve_authenticated_family_first_regions_v2(object(), query)

    assert (
        retrieval_v1.validate_replayed_authenticated_family_first_region_receipt_v2(
            object(), query, receipt
        )
        == receipt
    )
    assert receipt["authority"]["shortlist_authority"] is True
    assert receipt["authority"]["absence_authority"] is False
    assert receipt["authority"]["mapping_authority"] is False
    assert receipt["authority"]["numeric_authority"] is False
    assert receipt["authority"]["schema_authority"] is False

    forged = copy.deepcopy(receipt)
    forged["documents"][0]["selected_pages"] = [1]
    _rehash_document_and_receipt(forged)
    with pytest.raises(retrieval_v1.FamilyFirstRegionRetrievalV1Error, match="does not replay"):
        retrieval_v1.validate_replayed_authenticated_family_first_region_receipt_v2(
            object(), query, forged
        )
