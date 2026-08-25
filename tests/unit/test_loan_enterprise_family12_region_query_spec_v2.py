from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1
from bctc_ai.evaluation import family_first_region_retrieval_v1 as retrieval_v1
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.loan_enterprise_family12_graph_v1 import (
    LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_SPEC_V2,
    LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2,
    LoanEnterpriseFamily12GraphV1Error,
    build_loan_enterprise_family12_region_query_spec_v2,
)
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
    build_loan_enterprise_family12_spec_v1,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENGINE_REF = {"path": "synthetic-engine.py", "sha256": "7" * 64, "size_bytes": 1}


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
            "synthetic-family12-document",
            "SYNTHETIC_BANK_BLIND",
            2025,
            "ANNUAL",
            "CONSOLIDATED",
            "synthetic.pdf",
            hashlib.sha256(b"synthetic-pdf").hexdigest(),
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
        "cache_id": "synthetic-family12-cache",
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
        "document_id": "synthetic-family12-document",
        "document_ordinal": 1,
        "line_count": line_count,
        "packet_id": "synthetic-family12-packet",
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
            "manifest_id": "synthetic-family12-manifest",
            "metrics": {
                "document_count": 1,
                "line_count": line_count,
                "page_count": page_count,
            },
        },
        root=_PROJECT_ROOT,
    )


def _retrieve(path: Path, pages: dict[int, list[str]], **kwargs: object) -> dict:
    state = _state(path, pages, **kwargs)
    query = build_loan_enterprise_family12_region_query_spec_v2(_PROJECT_ROOT)
    return retrieval_v1._retrieve_from_state(state, query, engine_ref=_ENGINE_REF)


def _outcome(receipt: dict) -> dict:
    return receipt["documents"][0]


def test_query_is_bank_blind_short_nfc_and_exact_local_semantic_proof() -> None:
    query = build_loan_enterprise_family12_region_query_spec_v2(_PROJECT_ROOT)
    family_spec = build_loan_enterprise_family12_spec_v1()
    branch_anchors = [item for item in query["anchors"] if item["anchor_id"].startswith("BRANCH_")]
    owner_anchors = [
        item for item in query["anchors"] if item["anchor_id"].startswith("OWNER_716_")
    ]
    role_anchors = [
        item for item in query["anchors"] if item["anchor_id"].startswith("SEMANTIC_ROLE_")
    ]
    local_anchor_ids = {
        anchor_id for group in query["local_required_groups"] for anchor_id in group["anchor_ids"]
    }

    assert query == LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_SPEC_V2
    assert [item["surface"] for item in branch_anchors] == [
        "Loại hình doanh nghiệp",
        "Theo đối tượng khách hàng",
    ]
    assert {item["anchor_id"]: item["surface"] for item in branch_anchors} == {
        component["component_id"]: component["aliases"][0]
        for component in family_spec["branch_components"]
    }
    assert {item["anchor_id"]: item["max_edit_distance"] for item in branch_anchors} == {
        component["component_id"]: int(component["bounded_edit_on_exact_miss"])
        for component in family_spec["branch_components"]
    }
    assert all(
        item["surface"] == unicodedata.normalize("NFC", item["surface"]) for item in branch_anchors
    )
    assert all(item["max_edit_distance"] == 1 for item in branch_anchors)
    assert {item["role"] for item in query["anchors"]} == {
        "CONTEXT",
        "OWNER",
        "TARGET",
    }
    assert {group["group_id"] for group in query["local_required_groups"]} == {
        "EXACT_FAMILY12_SEMANTIC_ROLE",
        "OWNER_716_LOCAL",
    }
    assert all(item["max_edit_distance"] == 0 for item in owner_anchors)
    expected_role_policy = {
        normalize_vietnamese_anchor_v1(alias): int(child["bounded_edit_on_exact_miss"])
        for child in family_spec["children"]
        for alias in child["aliases"]
        if not (child["report_norm_id"] == 782 and normalize_vietnamese_anchor_v1(alias) == "khac")
    }
    assert {
        normalize_vietnamese_anchor_v1(item["surface"]): item["max_edit_distance"]
        for item in role_anchors
    } == expected_role_policy
    assert all(item["anchor_id"] in local_anchor_ids for item in [*owner_anchors, *role_anchors])
    assert {item["group_id"]: item["priority"] for item in query["seed_groups"]} == {
        "FAMILY12_OWNER_SEED": 2,
        "FAMILY12_SHORT_BRANCH_SEED": 1,
    }
    assert query["neighbor_pages_before"] == 2
    assert query["zero_hit_policy"] == "FULL_DOCUMENT_FALLBACK"
    assert all(not item["verified_historical_variants"] for item in query["anchors"])
    forbidden = {"bank", "filename", "page", "period", "year"}
    assert not forbidden & set(query)
    assert "historical_evidence_summary" not in query


def test_local_owner_branch_and_exact_role_select_only_local_pages(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "positive.sqlite3",
        {
            1: ["Nội dung trước"],
            2: ["Cho vay khách hàng", "Loại hình doanh nghiệp", "Công ty TNHH"],
            3: ["Nội dung sau"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [1, 2, 3]
    assert outcome["requires_full_document_review"] is False
    assert all(item["status"] == "SATISFIED" for item in outcome["local_required_group_results"])


def test_rare_trigrams_recover_one_edit_branch_only_as_retrieval_evidence(
    tmp_path: Path,
) -> None:
    receipt = _retrieve(
        tmp_path / "rare.sqlite3",
        {
            1: [
                "Cho vay khách hàng",
                "Theo đối turọng khách hàng",
                "Công ty TNHH",
            ]
        },
    )
    outcome = _outcome(receipt)
    branch = next(
        item
        for item in outcome["seed_occurrences"]
        if item["anchor_id"] == "BRANCH_THEO_DOI_TUONG_KHACH_HANG"
    )

    assert branch["stage"] == "GLOBAL_RARE_TRIGRAM_SEED"
    assert branch["edit_distance"] == 1
    assert "BOUNDED_EDIT" in branch["channels"]
    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert "report_norm_id" not in branch


def test_distant_owner_and_child_poison_cannot_validate_branch_region(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "distant.sqlite3",
        {
            1: ["Nội dung"],
            2: ["Loại hình doanh nghiệp"],
            3: ["Nội dung"],
            4: ["Nội dung"],
            5: ["Nội dung"],
            6: ["Nội dung"],
            7: ["Nội dung"],
            8: ["Cho vay khách hàng", "Công ty TNHH"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [6, 7, 8]
    poisoned_branch = next(
        item
        for item in outcome["candidate_region_results"]
        if item["group_id"] == "FAMILY12_SHORT_BRANCH_SEED"
    )
    assert poisoned_branch["status"] == "REJECTED_LOCAL_REQUIRED_GROUPS"


@pytest.mark.parametrize(
    "fence",
    [
        "Tiền gửi của khách hàng",
        "Giao dịch với các bên liên quan",
        "Phân tích theo ngành nghề kinh doanh",
    ],
)
def test_deposit_related_and_sibling_reset_fence_prior_owner(
    tmp_path: Path,
    fence: str,
) -> None:
    receipt = _retrieve(
        tmp_path / (hashlib.sha256(fence.encode()).hexdigest() + ".sqlite3"),
        {
            1: ["Cho vay khách hàng"],
            2: [fence],
            3: ["Loại hình doanh nghiệp", "Công ty TNHH"],
            4: ["Nội dung"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["structural_reset_pages"] == [2]
    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION"
    owner_group = next(
        item
        for item in outcome["candidate_region_results"][0]["local_required_group_results"]
        if item["group_id"] == "OWNER_716_LOCAL"
    )
    assert owner_group["status"] == "NOT_SATISFIED"


def test_owner_carries_two_pages_when_intervening_page_is_supplied(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "carry-two.sqlite3",
        {
            1: ["Cho vay khách hàng"],
            2: ["Nội dung trung gian"],
            3: ["Loại hình doanh nghiệp", "Công ty TNHH"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [1, 2, 3]
    assert any(
        fragment["physical_page"] == 1
        for item in outcome["local_occurrences"]
        if item["anchor_id"].startswith("OWNER_716_")
        for fragment in item["fragments"]
    )


def test_zero_line_intervening_page_retains_supplied_page_axis(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "zero-line.sqlite3",
        {
            1: ["Cho vay khách hàng"],
            2: [],
            3: ["Loại hình doanh nghiệp", "Công ty TNHH"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [1, 2, 3]
    assert outcome["document_page_count"] == 3


def test_owner_seed_retains_distant_branchless_multirole_challenger(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "distant-branchless.sqlite3",
        {
            1: ["Nội dung trước"],
            2: ["Cho vay khách hàng", "Loại hình doanh nghiệp", "Công ty TNHH"],
            3: ["Nội dung sau"],
            4: ["Nội dung cách biệt"],
            5: ["Nội dung cách biệt"],
            6: ["Nội dung cách biệt"],
            7: ["Nội dung cách biệt"],
            8: ["Cho vay khách hàng", "Doanh nghiệp TNHH", "Công ty CP khxác"],
            9: ["Nội dung sau vùng thiếu nhánh"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [1, 2, 3, 6, 7, 8, 9]
    distant = next(
        item
        for item in outcome["candidate_region_results"]
        if item["group_id"] == "FAMILY12_OWNER_SEED" and item["seed_pages"] == [8]
    )
    assert distant["status"] == "ACCEPTED_LOCAL_REQUIRED_GROUPS"
    distant_roles = [
        item
        for item in outcome["local_occurrences"]
        if item["anchor_id"].startswith("SEMANTIC_ROLE_")
        and item["start_locator"]["physical_page"] == 8
    ]
    assert len({item["anchor_id"].split("_ALIAS_")[0] for item in distant_roles}) == 2
    assert any("BOUNDED_EDIT" in item["channels"] for item in distant_roles)


def test_owner_seed_cannot_borrow_roles_across_structural_reset(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "distant-reset.sqlite3",
        {
            1: ["Nội dung trước"],
            2: ["Cho vay khách hàng", "Loại hình doanh nghiệp", "Công ty TNHH"],
            3: ["Nội dung sau"],
            4: ["Nội dung cách biệt"],
            5: ["Nội dung cách biệt"],
            6: ["Nội dung cách biệt"],
            7: ["Cho vay khách hàng"],
            8: ["Tài sản cố định", "Doanh nghiệp TNHH", "Công ty CP khác"],
            9: ["Nội dung sau"],
        },
    )
    outcome = _outcome(receipt)

    assert outcome["selected_pages"] == [1, 2, 3]
    assert outcome["structural_reset_pages"] == [8]
    fenced = next(
        item
        for item in outcome["candidate_region_results"]
        if item["group_id"] == "FAMILY12_OWNER_SEED" and item["seed_pages"] == [7]
    )
    assert fenced["status"] == "REJECTED_LOCAL_REQUIRED_GROUPS"


def test_query_rehashes_exact_adapter_and_rejects_dependency_drift(tmp_path: Path) -> None:
    query = build_loan_enterprise_family12_region_query_spec_v2(_PROJECT_ROOT)
    reference = query["semantic_assignment_adapter_ref"]
    adapter = _PROJECT_ROOT / reference["path"]

    assert retrieval_v1.family_first_region_query_spec_id_v2(query) == (
        "fffrrv2:query:a2266e3e08aa5a33d65befe4c10b1f651a3aa3c8e5b07ebc7bfd27d15e4a1f8a"
    )
    assert reference["size_bytes"] == adapter.stat().st_size
    assert reference["sha256"] == hashlib.sha256(adapter.read_bytes()).hexdigest()
    for dependency in LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2.values():
        path = _PROJECT_ROOT / dependency["path"]
        assert dependency["size_bytes"] == path.stat().st_size
        assert dependency["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "shared_scoped_table_engine_ref" in (
        LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2
    )
    assert retrieval_v1.family_first_region_query_spec_id_v2(query) == (
        retrieval_v1.family_first_region_query_spec_id_v2(
            build_loan_enterprise_family12_region_query_spec_v2(_PROJECT_ROOT)
        )
    )
    forged = copy.deepcopy(query)
    forged["semantic_assignment_adapter_ref"]["sha256"] = "0" * 64
    assert retrieval_v1.family_first_region_query_spec_id_v2(forged) != (
        retrieval_v1.family_first_region_query_spec_id_v2(query)
    )

    copied_root = tmp_path / "copied-root"
    for content_ref in [
        reference,
        *LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2.values(),
    ]:
        target = copied_root / content_ref["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_PROJECT_ROOT / content_ref["path"], target)
    spec_ref = LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2["family_spec_ref"]
    spec_path = copied_root / spec_ref["path"]
    spec_path.write_bytes(spec_path.read_bytes() + b"\n")
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="trust closure drifted"):
        build_loan_enterprise_family12_region_query_spec_v2(copied_root)
    shutil.copyfile(_PROJECT_ROOT / spec_ref["path"], spec_path)
    scoped_ref = LOAN_ENTERPRISE_FAMILY12_REGION_QUERY_TRUST_CLOSURE_V2[
        "shared_scoped_table_engine_ref"
    ]
    scoped_path = copied_root / scoped_ref["path"]
    scoped_path.write_bytes(scoped_path.read_bytes() + b"\n")
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="trust closure drifted"):
        build_loan_enterprise_family12_region_query_spec_v2(copied_root)


def test_provider_row_reorder_preserves_document_region_proposal(tmp_path: Path) -> None:
    pages = {
        1: ["Nội dung trước"],
        2: ["Cho vay khách hàng", "Loại hình doanh nghiệp", "Công ty TNHH"],
        3: ["Nội dung sau"],
    }
    ordered = _retrieve(tmp_path / "ordered.sqlite3", pages)
    reordered = _retrieve(
        tmp_path / "reordered.sqlite3",
        pages,
        reverse_provider_rows=True,
    )

    assert ordered["documents"] == reordered["documents"]
    assert ordered["planner"] == reordered["planner"]
