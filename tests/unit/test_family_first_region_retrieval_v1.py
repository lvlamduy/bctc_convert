from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1
from bctc_ai.evaluation import family_first_region_retrieval_v1 as retrieval_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _packet(ordinal: int, *, page_count: int, line_count: int) -> dict[str, object]:
    return {
        "document_evidence_root_sha256": hashlib.sha256(
            f"evidence-{ordinal}".encode("ascii")
        ).hexdigest(),
        "document_id": f"document-{ordinal:04d}",
        "document_ordinal": ordinal,
        "line_count": line_count,
        "packet_id": f"packet-{ordinal:04d}",
        "page_count": page_count,
    }


def _database(
    path: Path,
    *,
    document_count: int = 140,
    multiple_candidates: bool = False,
    rare_typo: bool = False,
) -> SimpleNamespace:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    cache_v1._create_schema(connection)
    page_count = 10 if multiple_candidates else 3
    line_id = 0
    packets = []
    source_line_count = 0
    for document_ordinal in range(1, document_count + 1):
        texts_by_page: dict[int, list[str]] = {
            page: [f"Nội dung diễn giải trang {page}"] for page in range(1, page_count + 1)
        }
        texts_by_page[1] = ["Thuyết minh báo cáo tài chính"]
        texts_by_page[3] = ["Đơn vị: triệu VND"]
        if multiple_candidates and document_ordinal == 1:
            texts_by_page[2] = [
                "Phân tích theo khu vực địa lý",
                "Cho vay khách hàng",
            ]
            texts_by_page[8] = ["Trong nước", "Nước ngoài"]
        elif rare_typo and document_ordinal == 1:
            texts_by_page[2] = ["Khu vực dja lý"]
        elif document_ordinal == 1:
            texts_by_page[2] = ["Cho vay khách", "hàng theo khu vực địa lý"]
        elif document_ordinal == 2:
            texts_by_page[2] = ["chovay khách hàng"]
        elif document_ordinal == 3:
            texts_by_page[1] = ["Tiêu đề", "Cho vay khách"]
            texts_by_page[2] = ["hàng", "Dòng tiếp theo"]
        elif document_ordinal == 4:
            texts_by_page[1] = ["Cho vay khách hàng"]
            texts_by_page[2] = ["99. Báo cáo bộ phận", "Khoản mục khác"]
        line_count = sum(len(items) for items in texts_by_page.values())
        source_line_count += line_count
        packets.append(_packet(document_ordinal, page_count=page_count, line_count=line_count))
        connection.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                document_ordinal,
                f"document-{document_ordinal:04d}",
                "BANK",
                2025,
                "ANNUAL",
                "CONSOLIDATED",
                f"filing-{document_ordinal:04d}.pdf",
                hashlib.sha256(f"pdf-{document_ordinal}".encode("ascii")).hexdigest(),
                1,
                page_count,
                line_count,
            ),
        )
        for physical_page, texts in texts_by_page.items():
            connection.execute(
                "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document_ordinal,
                    physical_page,
                    len(texts),
                    1000,
                    1400,
                    "4" * 64,
                    1,
                    f"page-{physical_page}.json",
                    "5" * 64,
                    1,
                ),
            )
            for line_ordinal, text in enumerate(texts):
                line_id += 1
                accentless = retrieval_v1._accentless(text)
                connection.execute(
                    "INSERT INTO lines VALUES (" + ",".join("?" for _item in range(20)) + ")",
                    (
                        line_id,
                        document_ordinal,
                        physical_page,
                        line_ordinal,
                        f"sample-{line_id:09d}",
                        10,
                        20 + 30 * line_ordinal,
                        700,
                        45 + 30 * line_ordinal,
                        f"crop-{line_id}.png",
                        "6" * 64,
                        1,
                        text,
                        text,
                        accentless,
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
        "cache_id": "fixture-cache",
        "document_count": document_count,
        "format_version": cache_v1.CACHE_FORMAT_VERSION,
        "line_count": source_line_count,
        "page_count": document_count * page_count,
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
    return SimpleNamespace(
        database_path=path,
        manifest={
            "database_ref": {
                "path": path.name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            },
            "documents": packets,
            "manifest_id": "manifest-fixture",
            "metrics": {
                "document_count": document_count,
                "line_count": source_line_count,
                "page_count": document_count * page_count,
            },
        },
        root=path.parent,
    )


def _spec(*, zero_hit_policy: str = "FULL_DOCUMENT_FALLBACK") -> dict[str, object]:
    return {
        "anchors": [
            {
                "anchor_id": "CUSTOMER_LOAN",
                "canonical_alias_id": "CUSTOMER_LOAN_CANONICAL",
                "fts_probes": ["cho vay", "khach hang"],
                "max_edit_distance": 1,
                "role": "TARGET",
                "surface": "cho vay khach hang",
                "verified_historical_variants": [],
            }
        ],
        "family_id": "LOAN_GEOGRAPHY",
        "format_version": retrieval_v1.QUERY_SPEC_FORMAT_VERSION,
        "local_required_groups": [
            {
                "anchor_ids": ["CUSTOMER_LOAN"],
                "group_id": "CUSTOMER_LOAN_LOCAL",
                "mode": "ANY",
                "page_relation": "SAME_PAGE",
            }
        ],
        "max_hit_lines": 100,
        "max_selected_pages_per_document": 6,
        "neighbor_pages_after": 1,
        "neighbor_pages_before": 1,
        "seed_groups": [
            {
                "anchor_ids": ["CUSTOMER_LOAN"],
                "group_id": "CUSTOMER_LOAN_SEED",
                "mode": "ANY",
                "page_relation": "SAME_PAGE",
                "priority": 1,
            }
        ],
        "semantic_assignment_adapter_ref": None,
        "structural_reset_fragments": ["bao cao bo phan"],
        "structural_reset_max_line_ordinal": 1,
        "window_line_span": 2,
        "zero_hit_policy": zero_hit_policy,
    }


def _engine_ref() -> dict[str, object]:
    return {"path": "engine.py", "sha256": "7" * 64, "size_bytes": 1}


def _historical_variant_spec(tmp_path: Path) -> dict[str, object]:
    adapter = tmp_path / "historical_alias_adapter.py"
    payload = b"# semantic assignment adapter fixture\n"
    adapter.write_bytes(payload)
    spec = _spec()
    support_refs = [
        {
            "document_id": "document-0001",
            "physical_page": 2,
            "sample_ids": ["sample-000000002", "sample-000000003"],
        }
    ]
    variant = {
        "alias_id": "CUSTOMER_LOAN_HISTORICAL_001",
        "support_refs": support_refs,
        "surface": "Cho vay khách hàng",
        "verification_ref": (
            retrieval_v1.family_first_historical_variant_verification_id_v2(
                anchor_id="CUSTOMER_LOAN",
                alias_id="CUSTOMER_LOAN_HISTORICAL_001",
                surface="Cho vay khách hàng",
                support_refs=support_refs,
            )
        ),
    }
    spec["anchors"][0] = {
        "anchor_id": "CUSTOMER_LOAN",
        "canonical_alias_id": "CUSTOMER_LOAN_CANONICAL",
        "fts_probes": ["du no"],
        "max_edit_distance": 1,
        "role": "TARGET",
        "surface": "du no khach hang",
        "verified_historical_variants": [variant],
    }
    spec["semantic_assignment_adapter_ref"] = {
        "path": adapter.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    return spec


def _rehash_document_and_receipt(receipt: dict[str, object], ordinal: int) -> None:
    document = receipt["documents"][ordinal - 1]
    material = copy.deepcopy(document)
    material.pop("outcome_id")
    document["outcome_id"] = "fffrrv2:document:" + canonical_json_sha256_v1(material)
    receipt_material = copy.deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material)


def test_complete_140_document_receipt_keeps_wrapped_and_bounded_edit_hits(
    tmp_path: Path,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3")
    receipt = retrieval_v1._retrieve_from_state(state, _spec(), engine_ref=_engine_ref())
    receipt = retrieval_v1._validate_receipt_shape(receipt)

    assert receipt["metrics"]["document_count"] == 140
    assert len(receipt["documents"]) == 140
    assert receipt["metrics"]["zero_validated_hit_document_count"] == 136
    assert receipt["documents"][0]["index_outcome"] == "NONZERO_VALID_SEED_GROUP"
    assert receipt["documents"][0]["selected_pages"] == [1, 2, 3]
    assert any(
        item["start_locator"] == {"line_ordinal": 0, "physical_page": 2}
        and item["end_locator"] == {"line_ordinal": 1, "physical_page": 2}
        and "EXACT_ACCENTLESS" in item["channels"]
        for item in receipt["documents"][0]["local_occurrences"]
    )
    assert any(
        item["edit_distance"] == 1 and "BOUNDED_EDIT" in item["channels"]
        for item in receipt["documents"][1]["local_occurrences"]
    )
    assert receipt["documents"][4]["index_outcome"] == "ZERO_VALID_SEED_GROUP"
    assert receipt["documents"][4]["selection_mode"] == (
        "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
    )
    assert receipt["documents"][4]["selected_pages"] == [1, 2, 3]


def test_zero_hit_policy_cannot_weaken_full_document_fallback() -> None:
    spec = _spec(zero_hit_policy="RETURN_UNRESOLVED_NO_PAGES")
    with pytest.raises(retrieval_v1.FamilyFirstRegionRetrievalV1Error, match="identity"):
        retrieval_v1.validate_family_first_region_query_spec_v1(spec)


def test_accented_nfc_and_accentless_channels_are_separate_and_raw_is_unchanged(
    tmp_path: Path,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=4)
    spec = _spec()
    spec["anchors"][0]["surface"] = "cho vay khách hàng"
    receipt = retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())
    occurrence = next(
        item
        for item in receipt["documents"][0]["local_occurrences"]
        if item["end_locator"]["line_ordinal"] == 1
    )
    assert "EXACT_UNICODE" in occurrence["channels"]
    assert "EXACT_ACCENTLESS" in occurrence["channels"]
    assert [fragment["vietocr_text"] for fragment in occurrence["fragments"]] == [
        "Cho vay khách hàng theo khu vực địa lý"
    ]
    assert occurrence["joined_vietocr_text"] == "Cho vay khách hàng theo khu vực địa lý"


def test_fused_word_uses_bounded_edit_without_mutating_raw_surface(tmp_path: Path) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=4)
    receipt = retrieval_v1._retrieve_from_state(state, _spec(), engine_ref=_engine_ref())
    occurrence = receipt["documents"][1]["local_occurrences"][0]
    assert occurrence["edit_distance"] == 1
    assert "BOUNDED_EDIT" in occurrence["channels"]
    assert occurrence["fragments"][0]["vietocr_text"] == "chovay khách hàng"


def test_df_bounded_rare_trigrams_recover_one_edit_that_defeats_full_fts_probe(
    tmp_path: Path,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=3, rare_typo=True)
    spec = _spec()
    spec["anchors"][0] = {
        "anchor_id": "GEOGRAPHIC_AREA",
        "canonical_alias_id": "GEOGRAPHIC_AREA_CANONICAL",
        "fts_probes": ["khu vuc dia ly"],
        "max_edit_distance": 1,
        "role": "OWNER",
        "surface": "khu vực địa lý",
        "verified_historical_variants": [],
    }
    spec["seed_groups"][0]["anchor_ids"] = ["GEOGRAPHIC_AREA"]
    spec["local_required_groups"][0]["anchor_ids"] = ["GEOGRAPHIC_AREA"]
    receipt = retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())

    outcome = receipt["documents"][0]
    occurrence = outcome["seed_occurrences"][0]
    assert receipt["planner"]["anchor_statistics"][0]["raw_fts_hit_line_count"] == 0
    assert occurrence["stage"] == "GLOBAL_RARE_TRIGRAM_SEED"
    assert occurrence["edit_distance"] == 1
    assert "BOUNDED_EDIT" in occurrence["channels"]
    assert "FTS5_RARE_TRIGRAM_SEED" in occurrence["channels"]
    assert occurrence["joined_vietocr_text"] == "Khu vực dja lý"
    assert occurrence["rare_trigram_evidence"]["overlap_count"] >= 1
    selected = receipt["planner"]["anchor_statistics"][0]["rare_trigram_seed_plan"][
        "selected_grams"
    ]
    assert len(selected) >= 2
    assert all(item["line_frequency"] >= 1 for item in selected)
    with sqlite3.connect(state.database_path) as connection:
        for item in selected:
            direct = connection.execute(
                "SELECT COUNT(*), COUNT(DISTINCT l.document_ordinal), "
                "COUNT(DISTINCT printf('%d:%d', l.document_ordinal, l.physical_page)) "
                "FROM line_search s JOIN lines l ON l.line_id = s.rowid "
                "WHERE line_search MATCH ?",
                (retrieval_v1._fts_phrase(item["gram"]),),
            ).fetchone()
            assert direct == (
                item["line_frequency"],
                item["document_frequency"],
                item["page_frequency"],
            )
    assert outcome["index_outcome"] == "NONZERO_VALID_SEED_GROUP"


def test_all_satisfied_seed_groups_union_primary_and_fallback_candidate_regions(
    tmp_path: Path,
) -> None:
    state = _database(
        tmp_path / "ocr.sqlite3",
        document_count=1,
        multiple_candidates=True,
    )
    spec = _spec()
    spec["anchors"] = [
        {
            "anchor_id": "DOMESTIC",
            "canonical_alias_id": "DOMESTIC_CANONICAL",
            "fts_probes": ["trong nuoc"],
            "max_edit_distance": 0,
            "role": "CONTEXT",
            "surface": "trong nuoc",
            "verified_historical_variants": [],
        },
        {
            "anchor_id": "FOREIGN",
            "canonical_alias_id": "FOREIGN_CANONICAL",
            "fts_probes": ["nuoc ngoai"],
            "max_edit_distance": 0,
            "role": "CONTEXT",
            "surface": "nuoc ngoai",
            "verified_historical_variants": [],
        },
        {
            "anchor_id": "GEOGRAPHIC_AREA",
            "canonical_alias_id": "GEOGRAPHIC_AREA_CANONICAL",
            "fts_probes": ["khu vuc dia ly"],
            "max_edit_distance": 1,
            "role": "OWNER",
            "surface": "khu vực địa lý",
            "verified_historical_variants": [],
        },
    ]
    spec["seed_groups"] = [
        {
            "anchor_ids": ["DOMESTIC", "FOREIGN"],
            "group_id": "AXIS_FALLBACK",
            "mode": "ALL",
            "page_relation": "SAME_OR_ADJACENT_PAGE",
            "priority": 2,
        },
        {
            "anchor_ids": ["GEOGRAPHIC_AREA"],
            "group_id": "OWNER_PRIMARY",
            "mode": "ANY",
            "page_relation": "SAME_PAGE",
            "priority": 1,
        },
    ]
    spec["local_required_groups"] = []
    receipt = retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())

    outcome = receipt["documents"][0]
    assert [item["group_id"] for item in outcome["chosen_seed_groups"]] == [
        "OWNER_PRIMARY",
        "AXIS_FALLBACK",
    ]
    assert outcome["selected_pages"] == [1, 2, 3, 7, 8, 9]
    assert outcome["requires_full_document_review"] is False


def test_verified_historical_alias_support_replays_live_rows_and_keeps_canonical_raw(
    tmp_path: Path,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=3)
    spec = _historical_variant_spec(tmp_path)
    receipt = retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())

    verification = receipt["planner"]["historical_variant_support_verifications"][0]
    occurrence = receipt["documents"][0]["seed_occurrences"][0]
    assert verification["support_evidence_verified"] is True
    assert verification["semantic_assignment_authority"] is False
    assert [
        item["sample_id"] for item in verification["observed_supports"][0]["observed_locators"]
    ] == ["sample-000000002", "sample-000000003"]
    assert verification["observed_supports"][0]["channels"] == [
        "EXACT_UNICODE",
        "EXACT_ACCENTLESS",
    ]
    assert occurrence["matched_alias_id"] == "CUSTOMER_LOAN_HISTORICAL_001"
    assert occurrence["matched_alias_kind"] == "VERIFIED_HISTORICAL_VARIANT"
    assert receipt["query_spec"]["anchors"][0]["surface"] == "du no khach hang"


def test_region_local_scope_does_not_join_loan_page_two_to_axis_page_eight(
    tmp_path: Path,
) -> None:
    state = _database(
        tmp_path / "ocr.sqlite3",
        document_count=1,
        multiple_candidates=True,
    )
    spec = _spec()
    spec["anchors"] = [
        {
            "anchor_id": "DOMESTIC",
            "canonical_alias_id": "DOMESTIC_CANONICAL",
            "fts_probes": ["trong nuoc"],
            "max_edit_distance": 0,
            "role": "CONTEXT",
            "surface": "trong nuoc",
            "verified_historical_variants": [],
        },
        {
            "anchor_id": "FOREIGN",
            "canonical_alias_id": "FOREIGN_CANONICAL",
            "fts_probes": ["nuoc ngoai"],
            "max_edit_distance": 0,
            "role": "CONTEXT",
            "surface": "nuoc ngoai",
            "verified_historical_variants": [],
        },
        {
            "anchor_id": "GEOGRAPHIC_AREA",
            "canonical_alias_id": "GEOGRAPHIC_AREA_CANONICAL",
            "fts_probes": ["khu vuc dia ly"],
            "max_edit_distance": 1,
            "role": "OWNER",
            "surface": "khu vực địa lý",
            "verified_historical_variants": [],
        },
        {
            "anchor_id": "LOAN_GENERIC",
            "canonical_alias_id": "LOAN_GENERIC_CANONICAL",
            "fts_probes": ["cho vay"],
            "max_edit_distance": 0,
            "role": "TARGET",
            "surface": "cho vay",
            "verified_historical_variants": [],
        },
    ]
    spec["seed_groups"] = [
        {
            "anchor_ids": ["DOMESTIC", "FOREIGN"],
            "group_id": "AXIS_FALLBACK",
            "mode": "ALL",
            "page_relation": "SAME_OR_ADJACENT_PAGE",
            "priority": 2,
        },
        {
            "anchor_ids": ["GEOGRAPHIC_AREA"],
            "group_id": "OWNER_PRIMARY",
            "mode": "ANY",
            "page_relation": "SAME_PAGE",
            "priority": 1,
        },
    ]
    spec["local_required_groups"] = [
        {
            "anchor_ids": ["DOMESTIC", "FOREIGN"],
            "group_id": "GEOGRAPHIC_AXIS",
            "mode": "ALL",
            "page_relation": "SAME_OR_ADJACENT_PAGE",
        },
        {
            "anchor_ids": ["LOAN_GENERIC"],
            "group_id": "LOAN_POPULATION",
            "mode": "ANY",
            "page_relation": "SAME_OR_ADJACENT_PAGE",
        },
    ]
    receipt = retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())

    outcome = receipt["documents"][0]
    assert outcome["selection_mode"] == ("FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION")
    assert outcome["selected_pages"] == list(range(1, 11))
    assert {item["status"] for item in outcome["candidate_region_results"]} == {
        "REJECTED_LOCAL_REQUIRED_GROUPS"
    }


def test_forged_historical_alias_support_sample_is_rejected_against_live_sqlite(
    tmp_path: Path,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=3)
    spec = _historical_variant_spec(tmp_path)
    variant = spec["anchors"][0]["verified_historical_variants"][0]
    variant["support_refs"][0]["sample_ids"][-1] = "sample-999999999"
    variant["verification_ref"] = retrieval_v1.family_first_historical_variant_verification_id_v2(
        anchor_id="CUSTOMER_LOAN",
        alias_id=variant["alias_id"],
        surface=variant["surface"],
        support_refs=variant["support_refs"],
    )
    with pytest.raises(
        retrieval_v1.FamilyFirstRegionRetrievalV1Error,
        match="support",
    ):
        retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())


def test_historical_variant_cannot_be_reassigned_to_another_semantic_anchor(
    tmp_path: Path,
) -> None:
    spec = _historical_variant_spec(tmp_path)
    variant = spec["anchors"][0]["verified_historical_variants"].pop()
    spec["anchors"] = [
        spec["anchors"][0],
        {
            "anchor_id": "SECOND_SCOPE",
            "canonical_alias_id": "SECOND_SCOPE_CANONICAL",
            "fts_probes": ["second scope"],
            "max_edit_distance": 0,
            "role": "OWNER",
            "surface": "second scope",
            "verified_historical_variants": [variant],
        },
    ]
    with pytest.raises(
        retrieval_v1.FamilyFirstRegionRetrievalV1Error,
        match="does not bind its anchor",
    ):
        retrieval_v1.validate_family_first_region_query_spec_v2(spec)


def test_accentless_alias_collision_across_semantic_anchors_is_rejected() -> None:
    spec = _spec()
    spec["anchors"] = [
        {
            "anchor_id": "AREA_ACCENTED",
            "canonical_alias_id": "AREA_ACCENTED_CANONICAL",
            "fts_probes": ["khu vuc"],
            "max_edit_distance": 0,
            "role": "OWNER",
            "surface": "khu vực",
            "verified_historical_variants": [],
        },
        {
            "anchor_id": "AREA_ACCENTLESS",
            "canonical_alias_id": "AREA_ACCENTLESS_CANONICAL",
            "fts_probes": ["khu vuc"],
            "max_edit_distance": 0,
            "role": "OWNER",
            "surface": "khu vuc",
            "verified_historical_variants": [],
        },
    ]
    spec["seed_groups"][0]["anchor_ids"] = ["AREA_ACCENTED"]
    spec["local_required_groups"][0]["anchor_ids"] = ["AREA_ACCENTED"]
    with pytest.raises(
        retrieval_v1.FamilyFirstRegionRetrievalV1Error,
        match="collision",
    ):
        retrieval_v1.validate_family_first_region_query_spec_v2(spec)


def test_cross_page_split_anchor_retains_original_page_fragments_and_no_union_bbox(
    tmp_path: Path,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=4)
    receipt = retrieval_v1._retrieve_from_state(state, _spec(), engine_ref=_engine_ref())
    occurrence = next(
        item for item in receipt["documents"][2]["local_occurrences"] if len(item["fragments"]) == 2
    )
    assert [fragment["physical_page"] for fragment in occurrence["fragments"]] == [1, 2]
    assert "bbox" not in occurrence
    assert occurrence["start_locator"] == {"line_ordinal": 1, "physical_page": 1}
    assert occurrence["end_locator"] == {"line_ordinal": 0, "physical_page": 2}
    assert set(receipt["documents"][2]["selected_pages"]) >= {1, 2}


def test_structural_reset_stops_neighbor_expansion_and_records_blocker(tmp_path: Path) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=4)
    receipt = retrieval_v1._retrieve_from_state(state, _spec(), engine_ref=_engine_ref())
    outcome = receipt["documents"][3]
    assert outcome["selected_pages"] == [1]
    assert outcome["structural_reset_pages"] == [2]
    assert outcome["blocked_expansions"] == [
        {
            "direction": "AFTER",
            "from_page": 1,
            "physical_page": 2,
            "reason": "STRUCTURAL_RESET_AT_CANDIDATE_PAGE_START",
        }
    ]
    assert outcome["page_explanations"] == [{"physical_page": 1, "reasons": ["ANCHOR_TARGET"]}]


def test_filing_specific_routing_fields_are_rejected() -> None:
    forged = _spec()
    forged["bank"] = "ACB"
    with pytest.raises(retrieval_v1.FamilyFirstRegionRetrievalV1Error, match="routing"):
        retrieval_v1.validate_family_first_region_query_spec_v1(forged)


def test_query_overflow_falls_back_without_truncating_any_document(tmp_path: Path) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=5)
    spec = _spec()
    spec["anchors"][0] = {
        "anchor_id": "REPORT_NOTE",
        "canonical_alias_id": "REPORT_NOTE_CANONICAL",
        "fts_probes": ["bao cao", "thuyet minh"],
        "max_edit_distance": 0,
        "role": "OWNER",
        "surface": "thuyet minh bao cao tai chinh",
        "verified_historical_variants": [],
    }
    spec["seed_groups"][0]["anchor_ids"] = ["REPORT_NOTE"]
    spec["local_required_groups"][0]["anchor_ids"] = ["REPORT_NOTE"]
    spec["max_hit_lines"] = 1
    receipt = retrieval_v1._retrieve_from_state(state, spec, engine_ref=_engine_ref())
    assert receipt["metrics"]["raw_fts_hit_line_count"] == 4
    assert receipt["metrics"]["fallback_document_count"] == 5
    assert all(
        item["selection_mode"] == "FULL_DOCUMENT_FALLBACK_SEED_QUERY_OVERFLOW"
        and item["selected_pages"] == [1, 2, 3]
        for item in receipt["documents"]
    )


def test_self_rehashed_forged_outcome_is_rejected_by_authenticated_sql_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=3)
    monkeypatch.setattr(retrieval_v1.store_v1, "_live_store", lambda _capability: state)
    monkeypatch.setattr(retrieval_v1, "_engine_ref", lambda _root: _engine_ref())
    receipt = retrieval_v1.retrieve_authenticated_family_first_regions_v1(object(), _spec())
    assert receipt["source_binding"]["runtime_determinants"]["sqlite_version"]
    assert receipt["source_binding"]["runtime_determinants"]["rapidfuzz_distribution_version"]
    forged = copy.deepcopy(receipt)
    assert forged["documents"][0]["seed_occurrences"][0]["fragments"][0]["physical_page"] == 2
    forged["documents"][0]["selected_pages"] = [1, 3]
    _rehash_document_and_receipt(forged, 1)

    with pytest.raises(
        retrieval_v1.FamilyFirstRegionRetrievalV1Error,
        match="does not replay",
    ):
        retrieval_v1.validate_replayed_authenticated_family_first_region_receipt_v1(
            object(), _spec(), forged
        )


def test_self_rehashed_forged_occurrence_row_is_rejected_by_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _database(tmp_path / "ocr.sqlite3", document_count=3)
    monkeypatch.setattr(retrieval_v1.store_v1, "_live_store", lambda _capability: state)
    monkeypatch.setattr(retrieval_v1, "_engine_ref", lambda _root: _engine_ref())
    receipt = retrieval_v1.retrieve_authenticated_family_first_regions_v1(object(), _spec())
    forged = copy.deepcopy(receipt)
    occurrence = forged["documents"][0]["local_occurrences"][0]
    occurrence["joined_vietocr_text"] = "forged source row"
    occurrence_material = copy.deepcopy(occurrence)
    occurrence_material.pop("occurrence_id")
    occurrence["occurrence_id"] = "fffrrv2:occurrence:" + canonical_json_sha256_v1(
        occurrence_material
    )
    _rehash_document_and_receipt(forged, 1)

    with pytest.raises(
        retrieval_v1.FamilyFirstRegionRetrievalV1Error,
        match="does not replay",
    ):
        retrieval_v1.validate_replayed_authenticated_family_first_region_receipt_v1(
            object(), _spec(), forged
        )
