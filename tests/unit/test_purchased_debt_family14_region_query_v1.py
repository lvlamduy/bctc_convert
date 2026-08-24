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
from bctc_ai.evaluation.purchased_debt_family14_region_query_v1 import (
    CLAIM_BOUNDARY,
    PURCHASED_DEBT_FAMILY14_REGION_QUERY_SPEC_V2,
    PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1,
    RECOVERY_STATUS_V1,
    PurchasedDebtFamily14RegionQueryV1Error,
    build_purchased_debt_family14_region_query_spec_v2,
    build_purchased_debt_family14_schema_role_declaration_v1,
    build_purchased_debt_family14_topology_scan_v1,
    build_purchased_debt_family14_topology_spec_v1,
    validate_purchased_debt_family14_topology_replay_v1,
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


def _state(path: Path, pages: dict[int, list[str]]) -> SimpleNamespace:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    cache_v1._create_schema(connection)
    page_count = max(pages)
    source_rows = [
        (physical_page, line_ordinal, text)
        for physical_page in range(1, page_count + 1)
        for line_ordinal, text in enumerate(pages.get(physical_page, []))
    ]
    line_count = len(source_rows)
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            1,
            "synthetic-family14-document",
            "SYNTHETIC_BANK_BLIND",
            2025,
            "ANNUAL",
            "CONSOLIDATED",
            "synthetic.pdf",
            hashlib.sha256(b"synthetic-family14-pdf").hexdigest(),
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
    for line_id, (physical_page, line_ordinal, text) in enumerate(source_rows, 1):
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
        "cache_id": "synthetic-family14-cache",
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
        "document_id": "synthetic-family14-document",
        "document_ordinal": 1,
        "line_count": line_count,
        "packet_id": "synthetic-family14-packet",
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
            "manifest_id": "synthetic-family14-manifest",
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
) -> dict[str, Any]:
    query = query or build_purchased_debt_family14_region_query_spec_v2(_PROJECT_ROOT)
    return retrieval_v1._retrieve_from_state(
        _state(path, pages), query, engine_ref=_ENGINE_REF
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
    receipt["documents"][0]["outcome_id"] = (
        "fffrrv2:document:" + canonical_json_sha256_v1(document_material)
    )
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material)


def test_topology_and_live_schema_declaration_are_diagnostic_only() -> None:
    topology = build_purchased_debt_family14_topology_spec_v1()
    declaration = build_purchased_debt_family14_schema_role_declaration_v1()
    by_role = {child["role"]: child for child in topology["children"]}

    assert topology["format_version"] == "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3"
    assert topology["parent"] == {
        "aliases": ["Hoạt động mua nợ", "Hoạt động mua nợ (tiếp theo)"],
        "resolution_mode": "EXPLICIT_ONLY",
        "role": "PURCHASED_DEBT_OWNER",
    }
    assert topology["required_role_combinations"] == [
        ["PURCHASE_VND_BALANCE_ROW", "PROVISION_BALANCE_ROW", "PRINCIPAL_DETAIL_ROW"]
    ]
    assert topology["limits"] == {
        "max_cluster_span_lines": 96,
        "max_continuation_pages": 1,
        "max_label_line_span": 3,
    }
    assert all(child["role_kind"] == "NONADDITIVE_CHILD" for child in by_role.values())
    assert by_role["PURCHASE_FX_BALANCE_ROW"]["presence"] == "OPTIONAL"
    assert by_role["INTEREST_DETAIL_ROW"]["presence"] == "OPTIONAL"
    assert declaration["root"] == {"display_order": 262, "report_norm_id": 800}
    live_roles = [
        declaration["roles"][role]
        for role in [
            "PURCHASE_VND_BALANCE_ROW",
            "PURCHASE_FX_BALANCE_ROW",
            "PROVISION_BALANCE_ROW",
            "PRINCIPAL_DETAIL_ROW",
            "INTEREST_DETAIL_ROW",
        ]
    ]
    assert [role["report_norm_id"] for role in live_roles] == [801, 802, 803, 5738, 5739]
    assert [role["display_order"] for role in live_roles] == [263, 264, 265, 266, 267]
    assert declaration["next_family"] == {"display_order": 268, "report_norm_id": 804}
    assert not any(declaration["authority"].values())
    assert {"report_norm_id", "accounting_equation", "signed_value", "unit"}.isdisjoint(
        _all_keys(topology)
    )


@pytest.mark.parametrize(
    "provision,interest",
    [
        ("Dự phòng rủi ro", None),
        ("Dự phòng chung", "Lãi từ các khoản nợ đã mua"),
        ("Dự phòng rủi ro mua nợ", "Lãi của khoản nợ đã mua"),
        (
            "Dự phòng rủi ro hoạt động mua nợ",
            "Lãi từ các khoản nợ đã mua và chênh lệch giá mua nợ",
        ),
    ],
)
def test_legacy_analogues_accept_required_triple_with_optional_interest(
    provision: str, interest: str | None
) -> None:
    surfaces = ["Hoạt động mua nợ", "Mua nợ bằng VND", provision, "Nợ gốc đã mua"]
    if interest is not None:
        surfaces.append(interest)
    pages = [_page(surfaces, 1)]
    result = build_purchased_debt_family14_topology_scan_v1(pages)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    minimal = result["regions"][0]["minimal_unique_anchor"]
    assert minimal["combination_size"] == 2
    assert minimal["pair_before_triple_search"] is True
    assert validate_purchased_debt_family14_topology_replay_v1(result, pages) == result


def test_continuation_and_optional_fx_are_structural_only() -> None:
    result = build_purchased_debt_family14_topology_scan_v1(
        [
            _page(
                [
                    "Hoạt động mua nợ (tiếp theo)",
                    "Mua nợ bằng VND",
                    "Mua nợ bằng ngoại tệ",
                    "Dự phòng chung",
                ],
                1,
            ),
            _page(["Nợ gốc đã mua"], 2),
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["continuation_page_count"] == 1
    assert result["regions"][0]["minimal_unique_anchor"]["combination_size"] == 2


def test_ownerless_distinctive_pair_falls_back_pending_reset_fenced_oracle(
    tmp_path: Path,
) -> None:
    pages = {
        1: ["Mua nợ bằng VND", "Dự phòng rủi ro mua nợ"],
        2: ["Nội dung sau"],
    }
    outcome = _outcome(_retrieve(tmp_path / "branchless-pair.sqlite3", pages))
    topology = build_purchased_debt_family14_topology_scan_v1(
        [_page(pages[1], 1), _page(pages[2], 2)]
    )

    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert outcome["selected_pages"] == [1, 2]
    assert outcome["chosen_seed_groups"] == []
    assert topology["regions"] == []
    assert RECOVERY_STATUS_V1["absence_authority"] is False
    assert RECOVERY_STATUS_V1["branchless_distinct_role_pair"] == (
        "NOT_IMPLEMENTED_PENDING_OWNER_LOCAL_RESET_FENCED_ORACLE"
    )
    assert RECOVERY_STATUS_V1["ownerless_distinctive_rescue_scope"] == (
        "DECLARED_SAME_PAGE_ONLY_NOT_ACTIVE"
    )


@pytest.mark.parametrize(
    "generic,distinctive",
    [
        ("Dự phòng rủi ro", "Mua nợ bằng VND"),
        ("Dự phòng chung", "Nợ gốc đã mua"),
    ],
)
def test_ownerless_generic_provision_pairs_never_seed(
    tmp_path: Path, generic: str, distinctive: str
) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / ("generic-" + str(len(generic)) + ".sqlite3"),
            {1: [generic, distinctive], 2: ["Nội dung sau"]},
        )
    )

    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert outcome["chosen_seed_groups"] == []


def test_optional_only_owner_cannot_validate_local_region(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "optional-only-owner.sqlite3",
            {
                1: ["Nội dung trước"],
                2: ["Hoạt động mua nợ", "Phân tích chất lượng hoạt động mua nợ"],
                3: ["Nội dung sau"],
            },
        )
    )

    assert outcome["selection_mode"] == (
        "FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION"
    )
    assert outcome["selected_pages"] == [1, 2, 3]


def test_same_page_reset_pair_needs_explicit_owner_to_shortlist(tmp_path: Path) -> None:
    ownerless = _outcome(
        _retrieve(
            tmp_path / "same-page-reset-ownerless.sqlite3",
            {
                1: ["Mua nợ bằng VND", "Chứng khoán đầu tư", "Nợ gốc đã mua"],
                2: ["Sau"],
            },
        )
    )
    owned = _outcome(
        _retrieve(
            tmp_path / "same-page-reset-owned.sqlite3",
            {
                1: [
                    "Hoạt động mua nợ",
                    "Mua nợ bằng VND",
                    "Chứng khoán đầu tư",
                    "Nợ gốc đã mua",
                ],
                2: ["Sau"],
            },
        )
    )

    assert ownerless["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert owned["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert [group["group_id"] for group in owned["chosen_seed_groups"]] == [
        "EXPLICIT_PURCHASED_DEBT_OWNER"
    ]
    assert RECOVERY_STATUS_V1["same_page_reset_interval_fencing"] == (
        "NOT_IMPLEMENTED_BY_PAGE_LEVEL_QUERY_SHORTLIST"
    )


def test_cross_page_reset_separated_ownerless_pair_falls_back(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "cross-page-reset-ownerless.sqlite3",
            {
                1: ["Mua nợ bằng VND"],
                2: ["Chứng khoán đầu tư", "Nợ gốc đã mua"],
                3: ["Sau"],
            },
        )
    )

    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert outcome["selected_pages"] == [1, 2, 3]


def test_reset_and_hard_negative_fence_required_roles() -> None:
    result = build_purchased_debt_family14_topology_scan_v1(
        [
            _page(
                [
                    "Hoạt động mua nợ",
                    "Mua nợ bằng VND",
                    "Chi phí dự phòng rủi ro tín dụng",
                    "Dự phòng chung",
                    "Nợ gốc đã mua",
                ],
                1,
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_region_count"] == 0


def test_window_one_forbids_wrapped_owner_and_query_selects_before_after_one(
    tmp_path: Path,
) -> None:
    split = _outcome(
        _retrieve(
            tmp_path / "split.sqlite3",
            {1: ["Hoạt động mua"], 2: ["nợ"], 3: ["Nội dung sau"]},
        )
    )
    indexed = _outcome(
        _retrieve(
            tmp_path / "indexed.sqlite3",
            {
                1: ["Nội dung trước"],
                2: [
                    "Hoạt động mua nợ",
                    "Mua nợ bằng VND",
                    "Dự phòng chung",
                    "Nợ gốc đã mua",
                ],
                3: ["Nội dung sau"],
                4: ["Ngoài vùng"],
            },
        )
    )

    assert split["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert indexed["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert indexed["selected_pages"] == [1, 2, 3]
    assert indexed["chosen_seed_groups"][0]["group_id"] == (
        "EXPLICIT_PURCHASED_DEBT_OWNER"
    )
    assert RECOVERY_STATUS_V1["same_page_reset_interval_fencing"] == (
        "NOT_IMPLEMENTED_BY_PAGE_LEVEL_QUERY_SHORTLIST"
    )
    assert RECOVERY_STATUS_V1["indexed_result_requirement"] == (
        "LATER_FULL_DOCUMENT_RESET_FENCED_TERMINAL_ORACLE"
    )


def test_zero_overflow_fallback_and_reset_fenced_branchless_challenger(
    tmp_path: Path,
) -> None:
    zero = _outcome(
        _retrieve(
            tmp_path / "zero.sqlite3",
            {1: ["Mở đầu"], 2: ["Không liên quan"], 3: ["Kết thúc"]},
        )
    )
    overflow_query = build_purchased_debt_family14_region_query_spec_v2(_PROJECT_ROOT)
    overflow_query["max_hit_lines"] = 1
    overflow = _outcome(
        _retrieve(
            tmp_path / "overflow.sqlite3",
            {1: ["Hoạt động mua nợ"], 2: ["Hoạt động mua nợ"], 3: ["Sau"]},
            query=overflow_query,
        )
    )
    reset = _outcome(
        _retrieve(
            tmp_path / "reset.sqlite3",
            {
                1: ["Hoạt động mua nợ"],
                2: ["Chứng khoán đầu tư", "Mua nợ bằng VND", "Dự phòng chung"],
                3: ["Nợ gốc đã mua"],
            },
        )
    )

    assert zero["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    assert overflow["selection_mode"] == "FULL_DOCUMENT_FALLBACK_SEED_QUERY_OVERFLOW"
    assert reset["selection_mode"] == (
        "FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION"
    )
    assert reset["structural_reset_pages"] == [2]
    assert zero["selected_pages"] == overflow["selected_pages"] == reset["selected_pages"] == [
        1,
        2,
        3,
    ]


def test_query_is_bank_blind_non_authoritative_and_exactly_frozen() -> None:
    query = build_purchased_debt_family14_region_query_spec_v2(_PROJECT_ROOT)

    assert query == PURCHASED_DEBT_FAMILY14_REGION_QUERY_SPEC_V2
    assert query["neighbor_pages_before"] == query["neighbor_pages_after"] == 1
    assert query["window_line_span"] == 1
    assert query["zero_hit_policy"] == "FULL_DOCUMENT_FALLBACK"
    assert query["max_selected_pages_per_document"] == 24
    assert query["seed_groups"] == [
        {
            "anchor_ids": ["OWNER_PURCHASED_DEBT_01", "OWNER_PURCHASED_DEBT_02"],
            "group_id": "EXPLICIT_PURCHASED_DEBT_OWNER",
            "mode": "ANY",
            "page_relation": "SAME_OR_ADJACENT_PAGE",
            "priority": 1,
        }
    ]
    assert query["local_required_groups"][0]["anchor_ids"] == [
        "TARGET_INTEREST_DETAIL_ROW_01",
        "TARGET_INTEREST_DETAIL_ROW_02",
        "TARGET_INTEREST_DETAIL_ROW_03",
        "TARGET_INTEREST_DETAIL_ROW_04",
        "TARGET_PRINCIPAL_DETAIL_ROW_01",
        "TARGET_PROVISION_BALANCE_ROW_03",
        "TARGET_PROVISION_BALANCE_ROW_04",
        "TARGET_PURCHASE_FX_BALANCE_ROW_01",
        "TARGET_PURCHASE_VND_BALANCE_ROW_01",
    ]
    assert "SHORTLIST_ONLY" in CLAIM_BOUNDARY
    assert {
        "absence_authority",
        "accounting_equation",
        "mapping_authority",
        "numeric_authority",
        "report_norm_id",
        "schema_authority",
        "signed_value",
    }.isdisjoint(_all_keys(query))


def test_literal_refs_query_reorder_and_dependency_tamper(tmp_path: Path) -> None:
    query = build_purchased_debt_family14_region_query_spec_v2(_PROJECT_ROOT)
    adapter_ref = query["semantic_assignment_adapter_ref"]
    adapter_path = _PROJECT_ROOT / adapter_ref["path"]

    assert retrieval_v1.family_first_region_query_spec_id_v2(query) == (
        "fffrrv2:query:ed7aee7c70d33b4c394d0b189ab9fe1ab0dd45f3cdecc177e078f031ba7bf119"
    )
    assert adapter_ref["size_bytes"] == adapter_path.stat().st_size
    assert adapter_ref["sha256"] == hashlib.sha256(adapter_path.read_bytes()).hexdigest()
    for reference in PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1.values():
        path = _PROJECT_ROOT / reference["path"]
        assert reference["size_bytes"] == path.stat().st_size
        assert reference["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    reordered = copy.deepcopy(query)
    reordered["anchors"].reverse()
    with pytest.raises(retrieval_v1.FamilyFirstRegionRetrievalV1Error, match="sorted"):
        retrieval_v1.family_first_region_query_spec_id_v2(reordered)

    copied_root = tmp_path / "copied-root"
    for reference in [
        adapter_ref,
        *PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1.values(),
    ]:
        target = copied_root / reference["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_PROJECT_ROOT / reference["path"], target)
    dependency = PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1[
        "shared_region_retrieval_engine_ref"
    ]
    dependency_path = copied_root / dependency["path"]
    dependency_path.write_bytes(dependency_path.read_bytes() + b"\n")
    with pytest.raises(PurchasedDebtFamily14RegionQueryV1Error, match="trust closure"):
        build_purchased_debt_family14_region_query_spec_v2(copied_root)


def test_public_receipt_replay_rejects_coherently_rehashed_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(
        tmp_path / "public-replay.sqlite3",
        {
            1: ["Nội dung trước"],
            2: ["Hoạt động mua nợ", "Mua nợ bằng VND", "Dự phòng chung"],
            3: ["Nợ gốc đã mua"],
        },
    )
    query = build_purchased_debt_family14_region_query_spec_v2(_PROJECT_ROOT)
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
