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
from bctc_ai.evaluation.interbank_deposits_loans_family3_region_query_v1 import (
    INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_SPEC_V2,
    INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1,
    InterbankDepositsLoansFamily3RegionQueryV1Error,
    build_interbank_deposits_loans_family3_region_query_spec_v2,
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
            "synthetic-family3-document",
            "SYNTHETIC_BANK_BLIND",
            2025,
            "ANNUAL",
            "CONSOLIDATED",
            "synthetic.pdf",
            hashlib.sha256(b"synthetic-family3-pdf").hexdigest(),
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
    for physical_page, line_ordinal, value in provider_rows:
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
                value,
                value,
                retrieval_v1._accentless(value),
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
        "cache_id": "synthetic-family3-cache",
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
        "document_id": "synthetic-family3-document",
        "document_ordinal": 1,
        "line_count": line_count,
        "packet_id": "synthetic-family3-packet",
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
            "manifest_id": "synthetic-family3-manifest",
            "metrics": {
                "document_count": 1,
                "line_count": line_count,
                "page_count": page_count,
            },
        },
        root=_PROJECT_ROOT,
    )


def _retrieve(path: Path, pages: dict[int, list[str]], **kwargs: Any) -> dict[str, Any]:
    query = build_interbank_deposits_loans_family3_region_query_spec_v2(_PROJECT_ROOT)
    return retrieval_v1._retrieve_from_state(
        _state(path, pages, **kwargs), query, engine_ref=_ENGINE_REF
    )


def _outcome(receipt: dict[str, Any]) -> dict[str, Any]:
    return receipt["documents"][0]


def _all_keys(value: Any) -> set[str]:
    if type(value) is dict:
        return set(value) | set().union(*(_all_keys(item) for item in value.values()), set())
    if type(value) is list:
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_query_is_declarative_distinct_role_and_shortlist_only() -> None:
    query = build_interbank_deposits_loans_family3_region_query_spec_v2(_PROJECT_ROOT)
    pair_groups = [
        group
        for group in query["seed_groups"]
        if group["group_id"].startswith("DISTINCT_CORE_PAIR")
    ]

    assert query == INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_SPEC_V2
    assert query["family_id"] == "INTERBANK_DEPOSITS_AND_LOANS"
    assert query["zero_hit_policy"] == "FULL_DOCUMENT_FALLBACK"
    assert query["neighbor_pages_before"] == query["neighbor_pages_after"] == 1
    assert len(pair_groups) == 172
    assert all(group["mode"] == "ALL" and len(group["anchor_ids"]) == 2 for group in pair_groups)
    assert all(
        group["anchor_ids"][0].split("_")[1:-1] != group["anchor_ids"][1].split("_")[1:-1]
        for group in pair_groups
    )
    assert {anchor["role"] for anchor in query["anchors"]} == {
        "HARD_NEGATIVE",
        "OWNER",
        "TARGET",
    }
    assert all(not anchor["verified_historical_variants"] for anchor in query["anchors"])
    bare_vnd_id = next(
        anchor["anchor_id"] for anchor in query["anchors"] if anchor["surface"] == "Bằng VND"
    )
    assert all(bare_vnd_id not in group["anchor_ids"] for group in query["seed_groups"])
    assert "Phân tích chất lượng" in query["structural_reset_fragments"]
    assert not {"bank", "filename", "page", "period", "year"} & set(query)


def test_explicit_owner_and_child_seed_one_local_region(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "positive.sqlite3",
            {
                1: ["Nội dung trước"],
                2: [
                    "Tiền gửi và cho vay các TCTD khác",
                    "Tiền gửi không kỳ hạn",
                ],
                3: ["Nội dung sau"],
            },
        )
    )

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["selected_pages"] == [1, 2, 3]
    assert outcome["requires_full_document_review"] is False
    assert outcome["local_required_group_results"][0]["status"] == "SATISFIED"


@pytest.mark.parametrize(
    "lines",
    [
        ["Tiền gửi và cho vay các TCTD khác"],
        ["Tiền gửi không kỳ hạn"],
    ],
)
def test_missing_owner_or_distinct_child_retains_full_document_fallback(
    tmp_path: Path,
    lines: list[str],
) -> None:
    suffix = hashlib.sha256("|".join(lines).encode()).hexdigest()
    outcome = _outcome(
        _retrieve(
            tmp_path / f"missing-{suffix}.sqlite3",
            {1: ["Mở đầu"], 2: lines, 3: ["Kết thúc"]},
        )
    )

    assert outcome["selection_mode"].startswith("FULL_DOCUMENT_FALLBACK")
    assert outcome["selected_pages"] == [1, 2, 3]
    assert outcome["requires_full_document_review"] is True
    assert outcome["fallback_reason"] == outcome["selection_mode"]


def test_two_distinct_structural_children_may_rescue_only_a_shortlist(tmp_path: Path) -> None:
    receipt = _retrieve(
        tmp_path / "branchless.sqlite3",
        {1: ["Tiền gửi không kỳ hạn", "Tiền gửi có kỳ hạn"], 2: ["Nội dung"]},
    )
    outcome = _outcome(receipt)

    assert outcome["selection_mode"] == "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
    assert outcome["requires_full_document_review"] is False
    assert any(
        group["group_id"].startswith("DISTINCT_CORE_PAIR")
        for group in outcome["chosen_seed_groups"]
    )
    assert receipt["authority"]["shortlist_authority"] is True
    assert receipt["authority"]["absence_authority"] is False
    assert receipt["authority"]["mapping_authority"] is False
    assert receipt["authority"]["numeric_authority"] is False
    assert receipt["authority"]["schema_authority"] is False
    assert not {
        "mapped_value",
        "numeric_evidence",
        "report_norm_id",
        "schema_binding",
    } & _all_keys(receipt["documents"])


def test_reset_page_fences_owner_from_later_child(tmp_path: Path) -> None:
    outcome = _outcome(
        _retrieve(
            tmp_path / "reset.sqlite3",
            {
                1: ["Tiền gửi và cho vay các TCTD khác"],
                2: ["Phân tích chất lượng"],
                3: ["Tiền gửi không kỳ hạn"],
            },
        )
    )

    assert outcome["structural_reset_pages"] == [2]
    assert outcome["selection_mode"] == "FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION"
    assert outcome["requires_full_document_review"] is True


def test_provider_row_reorder_preserves_region_proposal(tmp_path: Path) -> None:
    pages = {
        1: ["Nội dung trước"],
        2: ["Tiền gửi và cho vay các TCTD khác", "Tiền gửi không kỳ hạn"],
        3: ["Nội dung sau"],
    }
    ordered = _retrieve(tmp_path / "ordered.sqlite3", pages)
    reordered = _retrieve(tmp_path / "reordered.sqlite3", pages, reverse_provider_rows=True)

    assert ordered["documents"] == reordered["documents"]
    assert ordered["planner"] == reordered["planner"]


def test_query_id_and_content_refs_reject_tamper(tmp_path: Path) -> None:
    query = build_interbank_deposits_loans_family3_region_query_spec_v2(_PROJECT_ROOT)
    adapter_ref = query["semantic_assignment_adapter_ref"]
    adapter_path = _PROJECT_ROOT / adapter_ref["path"]

    assert retrieval_v1.family_first_region_query_spec_id_v2(query) == (
        "fffrrv2:query:4c4154f721a62a8bac531b7baaa7002f350da9ed71c5c345a4171f10de1ca956"
    )
    assert adapter_ref["size_bytes"] == adapter_path.stat().st_size
    assert adapter_ref["sha256"] == hashlib.sha256(adapter_path.read_bytes()).hexdigest()
    for reference in INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1.values():
        path = _PROJECT_ROOT / reference["path"]
        assert reference["size_bytes"] == path.stat().st_size
        assert reference["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    forged = copy.deepcopy(query)
    forged["semantic_assignment_adapter_ref"]["sha256"] = "0" * 64
    assert retrieval_v1.family_first_region_query_spec_id_v2(forged) != (
        retrieval_v1.family_first_region_query_spec_id_v2(query)
    )

    copied_root = tmp_path / "copied-root"
    for reference in [
        adapter_ref,
        *INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1.values(),
    ]:
        target = copied_root / reference["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_PROJECT_ROOT / reference["path"], target)
    topology_ref = INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1[
        "topology_spec_ref"
    ]
    topology_path = copied_root / topology_ref["path"]
    topology_path.write_bytes(topology_path.read_bytes() + b"\n")
    with pytest.raises(
        InterbankDepositsLoansFamily3RegionQueryV1Error,
        match="topology trust closure drifted",
    ):
        build_interbank_deposits_loans_family3_region_query_spec_v2(copied_root)
