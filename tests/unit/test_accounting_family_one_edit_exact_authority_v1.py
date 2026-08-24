from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import accounting_family_one_edit_exact_authority_v1 as subject
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as sweep_v1
from bctc_ai.evaluation import family_first_accounting_schema_mapping_v1 as mapping_v1


def _matcher(alias: str, within_role: str | None = None) -> dict[str, object]:
    return {"aliases": [alias], "within_role": within_role}


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Domestic deposits")],
                "presence": "OPTIONAL",
                "role": "DOMESTIC_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Foreign deposits")],
                "presence": "OPTIONAL",
                "role": "FOREIGN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [
                    _matcher("Vietnam dong balance", "DOMESTIC_GROUP"),
                    _matcher("Vietnam dong balance", "FOREIGN_GROUP"),
                ],
                "presence": "OPTIONAL",
                "role": "VND_BALANCE",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "FAMILY_ASSETS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 12,
            "max_continuation_pages": 0,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Family assets"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "FAMILY_ASSETS",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DOMESTIC_GROUP", "VND_BALANCE"]],
        "structural_reset_aliases": ["Next family"],
    }


def _nested_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Root section")],
                "presence": "OPTIONAL",
                "role": "ROOT",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [
                    _matcher("Inner contextual", "ROOT"),
                    _matcher("Inner standalone"),
                ],
                "presence": "OPTIONAL",
                "role": "INNER",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Leaf balance", "INNER")],
                "presence": "OPTIONAL",
                "role": "LEAF",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "NESTED_FAMILY",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 16,
            "max_continuation_pages": 0,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Nested family"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "NESTED_FAMILY",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["ROOT", "INNER", "LEAF"]],
        "structural_reset_aliases": ["Next family"],
    }


def _line(index: int, vietocr: str, source: str | None, *, left: int = 100) -> dict:
    return {
        "bbox": [left, 100 + index * 30, left + 420, 122 + index * 30],
        "source_line_index": index,
        "source_text": source,
        "vietocr_text": vietocr,
    }


def _pages(*lines: dict) -> list[dict]:
    return [{"lines": list(lines), "page_sequence": 1}]


def _selected(pages: list[dict], spec: dict | None = None) -> dict:
    retrieval_pages = [
        {
            "lines": [{**line, "source_text": None} for line in page["lines"]],
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]
    scan = topology_v1.build_accounting_family_topology_scan_v1(retrieval_pages, spec or _spec())
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    return scan["regions"][0]


def _expanded(pages: list[dict], region: dict, spec: dict | None = None) -> dict:
    return subject._canonical_expanded_occurrence_region_v1(
        topology_v1._pages(pages),
        spec or _spec(),
        region,
    )


def _three_level_pages(
    *,
    parent_source: str | None = "Family assets",
    group_source: str | None = "Domestic deposits",
    leaf_source: str | None = "Vietnam dong balance",
) -> list[dict]:
    return _pages(
        _line(0, "Family assetx", parent_source),
        _line(1, "Domestic depositx", group_source),
        _line(2, "Vietnam dong balancx", leaf_source),
        _line(3, "Next family", "Next family"),
    )


def test_parent_group_and_leaf_one_edit_retrievals_need_exact_same_span_source() -> None:
    pages = _three_level_pages()
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    assert receipt["status"] == "EXACT_SOURCE_AUTHORITY_BOUND"
    assert receipt["metrics"] == {
        "exact_bound_count": 3,
        "selected_one_edit_match_count": 3,
        "unresolved_match_count": 0,
    }
    assert [
        (item["match_scope"], item["role"], item["within_role"]) for item in receipt["checks"]
    ] == [
        ("FAMILY_PARENT", "FAMILY_ASSETS", None),
        ("EXPANDED_OCCURRENCE", "DOMESTIC_GROUP", None),
        ("EXPANDED_OCCURRENCE", "VND_BALANCE", "DOMESTIC_GROUP"),
    ]
    assert [item["occurrence_id"] for item in receipt["checks"]] == [
        None,
        _expanded(pages, region)["child_matches"][0]["occurrence_id"],
        _expanded(pages, region)["child_matches"][1]["occurrence_id"],
    ]
    assert all(
        item["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND" for item in receipt["checks"]
    )
    assert all(item["exact_channel"]["alias_pointer"] for item in receipt["checks"])


def test_canonical_coextensive_effective_child_is_retained_on_exact_parent() -> None:
    spec = _spec()
    spec["children"].append(
        {
            "matchers": [_matcher("Family assets")],
            "presence": "OPTIONAL",
            "role": "EXPLICIT_FAMILY_TOTAL",
            "role_kind": "TOTAL",
        }
    )
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic depositx", "Domestic deposits"),
        _line(2, "Vietnam dong balancx", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
    )
    region = _selected(pages, spec)
    expanded = _expanded(pages, region, spec)
    assert any(match["role"] == "EXPLICIT_FAMILY_TOTAL" for match in expanded["child_matches"])

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, spec, region, expanded
    )

    assert receipt["status"] == "EXACT_SOURCE_AUTHORITY_BOUND"
    assert all(item["role"] != "EXPLICIT_FAMILY_TOTAL" for item in receipt["checks"])


def test_missing_bound_source_text_fails_closed() -> None:
    pages = _three_level_pages(leaf_source=None)
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    leaf = next(item for item in receipt["checks"] if item["role"] == "VND_BALANCE")
    assert leaf["status"] == "MISSING_BOUND_SOURCE_TEXT"
    assert receipt["status"] == ("UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY")


def test_source_channel_that_is_still_one_edit_is_not_exact_authority() -> None:
    pages = _three_level_pages(leaf_source="Vietnam dong balancz")
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    leaf = next(item for item in receipt["checks"] if item["role"] == "VND_BALANCE")
    assert leaf["status"] == "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT"
    assert leaf["exact_channel"]["alias_pointer"] is None


def test_exact_alias_on_a_different_source_span_does_not_corroborate_retrieval() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balancx", "Unrelated source label"),
        _line(3, "Unrelated VietOCR label", "Vietnam dong balance"),
        _line(4, "Next family", "Next family"),
    )
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    assert receipt["checks"][0]["role"] == "VND_BALANCE"
    assert receipt["checks"][0]["source_line_indices"] == [2]
    assert receipt["checks"][0]["status"] == "EXACT_ALIAS_DIFFERENT_SOURCE_SPAN"


def test_same_exact_leaf_under_a_different_structural_parent_cannot_corroborate() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        # Retrieval sees DOMESTIC, while the independent source channel binds
        # the otherwise identical leaf to FOREIGN.
        _line(1, "Domestic deposits", "Foreign deposits"),
        _line(2, "Vietnam dong balancx", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
    )
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    leaf = next(item for item in receipt["checks"] if item["role"] == "VND_BALANCE")
    assert leaf["within_role"] == "DOMESTIC_GROUP"
    assert leaf["status"] == "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"
    assert leaf["exact_channel"]["context_binding"]["family_id"] == "FAMILY_ASSETS"


def test_nested_leaf_rejects_same_span_owner_from_context_free_matcher() -> None:
    pages = _pages(
        _line(0, "Nested family", "Nested family"),
        _line(1, "Root section", "Root section"),
        # Retrieval binds INNER beneath ROOT.  PP-OCR independently sees an
        # exact context-free INNER alias on that identical physical row.
        _line(2, "Inner contextuax", "Inner standalone"),
        _line(3, "Leaf balancx", "Leaf balance"),
        _line(4, "Next family", "Next family"),
    )
    spec = _nested_spec()
    region = _selected(pages, spec)
    expanded = _expanded(pages, region, spec)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, spec, region, expanded
    )

    retrieval_inner = next(match for match in expanded["child_matches"] if match["role"] == "INNER")
    assert retrieval_inner["matched_within_role"] == "ROOT"
    compiled = topology_v1._spec(spec)
    exact_hits, _source_pages = subject._source_exact_axes(topology_v1._pages(pages), compiled)
    source_axis = subject._decorate_exact_source_occurrences_v1(
        subject._context_bound_source_records(exact_hits, compiled, region),
        region,
    )
    source_inner = next(match for match in source_axis if match["role"] == "INNER")
    assert source_inner["source_line_index"] == retrieval_inner["source_line_index"]
    assert source_inner["matched_within_role"] is None
    leaf = next(item for item in receipt["checks"] if item["role"] == "LEAF")
    assert leaf["status"] == "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"


def test_nested_exact_owner_chain_is_recursive_and_source_tamper_fails_replay() -> None:
    pages = _pages(
        _line(0, "Nested familx", "Nested family"),
        _line(1, "Root sectiox", "Root section"),
        _line(2, "Inner contextuax", "Inner contextual"),
        _line(3, "Leaf balancx", "Leaf balance"),
        _line(4, "Next family", "Next family"),
    )
    spec = _nested_spec()
    region = _selected(pages, spec)
    expanded = _expanded(pages, region, spec)
    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, spec, region, expanded
    )

    assert receipt["status"] == "EXACT_SOURCE_AUTHORITY_BOUND"
    assert [(item["role"], item["status"]) for item in receipt["checks"]] == [
        ("NESTED_FAMILY", "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"),
        ("ROOT", "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"),
        ("INNER", "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"),
        ("LEAF", "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"),
    ]

    tampered_pages = copy.deepcopy(pages)
    tampered_pages[0]["lines"][2]["source_text"] = "Inner standalone"
    tampered = subject.build_accounting_family_one_edit_exact_authority_v1(
        tampered_pages, spec, region, expanded
    )
    tampered_leaf = next(item for item in tampered["checks"] if item["role"] == "LEAF")
    assert tampered_leaf["status"] == "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"

    ancestor_tampered_pages = copy.deepcopy(pages)
    ancestor_tampered_pages[0]["lines"][1]["source_text"] = "Root sectioz"
    ancestor_tampered = subject.build_accounting_family_one_edit_exact_authority_v1(
        ancestor_tampered_pages, spec, region, expanded
    )
    ancestor_tampered_leaf = next(
        item for item in ancestor_tampered["checks"] if item["role"] == "LEAF"
    )
    assert ancestor_tampered_leaf["status"] == "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="receipt does not replay exactly",
    ):
        subject.validate_accounting_family_one_edit_exact_authority_replay_v1(
            receipt,
            tampered_pages,
            spec,
            region,
            expanded,
        )


def test_repeated_nested_owners_bind_leaf_to_nearest_exact_source_occurrences() -> None:
    pages = _pages(
        _line(0, "Nested family", "Nested family"),
        _line(1, "Root section", "Root section"),
        _line(2, "Inner contextual", "Inner contextual"),
        _line(3, "Leaf balance", "Leaf balance"),
        _line(4, "Root section", "Root section"),
        _line(5, "Inner contextual", "Inner contextual"),
        _line(6, "Leaf balancx", "Leaf balance"),
        _line(7, "Next family", "Next family"),
    )
    spec = _nested_spec()
    region = _selected(pages, spec)
    expanded = _expanded(pages, region, spec)
    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, spec, region, expanded
    )

    leaf = next(item for item in receipt["checks"] if item["role"] == "LEAF")
    assert leaf["source_line_indices"] == [6]
    assert leaf["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"

    tampered_pages = copy.deepcopy(pages)
    tampered_pages[0]["lines"][5]["source_text"] = "Inner standalone"
    tampered = subject.build_accounting_family_one_edit_exact_authority_v1(
        tampered_pages, spec, region, expanded
    )
    tampered_leaf = next(item for item in tampered["checks"] if item["role"] == "LEAF")
    assert tampered_leaf["status"] == "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"


def test_exact_leaf_without_the_exact_selected_family_parent_cannot_corroborate() -> None:
    pages = _pages(
        _line(0, "Family assets", "Another family"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balancx", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
    )
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    assert receipt["checks"][0]["status"] == "EXACT_FAMILY_PARENT_CONTEXT_MISMATCH"


def test_repeated_exact_first_occurrence_cannot_corroborate_fuzzy_second_occurrence() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Vietnam dong balancx", "Vietnam dong balancz"),
        _line(4, "Next family", "Next family"),
    )
    region = _selected(pages)
    expanded = _expanded(pages, region)
    vnd_occurrences = [item for item in expanded["child_matches"] if item["role"] == "VND_BALANCE"]
    assert [item["source_line_index"] for item in vnd_occurrences] == [2, 3]

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, expanded
    )

    assert receipt["metrics"]["selected_one_edit_match_count"] == 1
    repeated = receipt["checks"][0]
    assert repeated["occurrence_id"] == vnd_occurrences[1]["occurrence_id"]
    assert repeated["source_line_indices"] == [3]
    assert repeated["status"] == "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT"
    assert f"OCCURRENCE_{vnd_occurrences[1]['occurrence_id']}" in receipt["unresolved_reasons"][0]


def test_expanded_one_edit_occurrence_without_occurrence_id_is_rejected() -> None:
    pages = _three_level_pages()
    region = _selected(pages)
    expanded = _expanded(pages, region)
    expanded["child_matches"][-1].pop("occurrence_id")

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence region does not replay exactly",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, expanded
        )


def test_caller_cannot_omit_a_selected_expanded_occurrence() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Vietnam dong balancx", "Vietnam dong balancz"),
        _line(4, "Next family", "Next family"),
    )
    region = _selected(pages)
    attacked = _expanded(pages, region)
    attacked["child_matches"].pop()

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence region does not replay exactly",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, attacked
        )


def test_caller_cannot_add_a_duplicate_physical_occurrence_with_a_coherent_id() -> None:
    pages = _three_level_pages()
    region = _selected(pages)
    attacked = _expanded(pages, region)
    duplicate = copy.deepcopy(attacked["child_matches"][-1])
    duplicate["role_occurrence_ordinal"] += 1
    duplicate["occurrence_id"] = subject._expected_occurrence_id_v1(duplicate)
    attacked["child_matches"].append(duplicate)

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence region does not replay exactly",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, attacked
        )


def test_caller_cannot_rebind_deterministic_ids_between_repeated_role_hits() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Vietnam dong balancx", "Vietnam dong balancz"),
        _line(4, "Next family", "Next family"),
    )
    region = _selected(pages)
    attacked = _expanded(pages, region)
    repeated = [match for match in attacked["child_matches"] if match["role"] == "VND_BALANCE"]
    repeated[0]["occurrence_id"], repeated[1]["occurrence_id"] = (
        repeated[1]["occurrence_id"],
        repeated[0]["occurrence_id"],
    )

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence region does not replay exactly",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, attacked
        )


def test_caller_cannot_rebind_leaf_to_a_non_nearest_structural_owner() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Foreign deposits", "Foreign deposits"),
        _line(4, "Vietnam dong balancx", "Vietnam dong balance"),
        _line(5, "Next family", "Next family"),
    )
    region = _selected(pages)
    attacked = _expanded(pages, region)
    domestic = next(
        match for match in attacked["child_matches"] if match["role"] == "DOMESTIC_GROUP"
    )
    second_leaf = [match for match in attacked["child_matches"] if match["role"] == "VND_BALANCE"][
        1
    ]
    assert second_leaf["scope_owner_role"] == "FOREIGN_GROUP"
    second_leaf["scope_owner_occurrence_id"] = domestic["occurrence_id"]
    second_leaf["scope_owner_role"] = domestic["role"]

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence region does not replay exactly",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, attacked
        )


def test_caller_cannot_move_fuzzy_occurrence_onto_an_exact_occurrence_span() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Vietnam dong balancx", "Vietnam dong balancz"),
        _line(4, "Next family", "Next family"),
    )
    region = _selected(pages)
    attacked = _expanded(pages, region)
    exact, fuzzy = [match for match in attacked["child_matches"] if match["role"] == "VND_BALANCE"]
    assert fuzzy["match_kind"].startswith("ONE_EDIT_ALIAS")
    for field in (
        "document_line_ordinal",
        "end_document_line_ordinal",
        "page_sequence",
        "source_line_index",
        "end_source_line_index",
    ):
        fuzzy[field] = exact[field]
    fuzzy["occurrence_id"] = subject._expected_occurrence_id_v1(fuzzy)

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence region does not replay exactly",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, attacked
        )


def test_receipt_tamper_and_coherent_identity_rehash_are_rejected_by_replay() -> None:
    pages = _three_level_pages()
    region = _selected(pages)
    expanded = _expanded(pages, region)
    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, expanded
    )
    tampered = copy.deepcopy(receipt)
    tampered["checks"][0]["retrieval_channel"]["surface"] = "forged"

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="receipt identity drifted",
    ):
        subject.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(tampered)

    # Even after an attacker updates the outer receipt identity, exact replay
    # from the bound pages and spec still rejects the modified channel.
    material = copy.deepcopy(tampered)
    material.pop("receipt_id")
    tampered["receipt_id"] = "afeoeav1:receipt:" + subject.canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_one_edit_exact_authority_replay_v1(
            tampered, pages, _spec(), region, expanded
        )

    occurrence_tampered = copy.deepcopy(receipt)
    child = next(
        item
        for item in occurrence_tampered["checks"]
        if item["match_scope"] == "EXPANDED_OCCURRENCE"
    )
    child["occurrence_id"] = "forged:occurrence"
    child["exact_channel"]["context_binding"]["occurrence_id"] = "forged:occurrence"
    child["exact_channel"]["context_binding_sha256"] = subject.canonical_json_sha256_v1(
        child["exact_channel"]["context_binding"]
    )
    material = copy.deepcopy(occurrence_tampered)
    material.pop("receipt_id")
    occurrence_tampered["receipt_id"] = "afeoeav1:receipt:" + subject.canonical_json_sha256_v1(
        material
    )
    subject.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
        occurrence_tampered
    )
    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_one_edit_exact_authority_replay_v1(
            occurrence_tampered, pages, _spec(), region, expanded
        )


def test_unselected_or_near_one_edit_match_cannot_veto_selected_exact_region() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
        _line(4, "Family assetx", None),
        _line(5, "Domestic depositx", None),
    )
    selected = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), selected, _expanded(pages, selected)
    )

    assert receipt["status"] == "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL"
    assert receipt["checks"] == []


def test_v4_integration_does_not_gate_a_discarded_complete_one_edit_candidate() -> None:
    pages = _pages(
        _line(0, "Family assets", "Family assets"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
        _line(4, "Family assetx", None),
        _line(5, "Domestic depositx", None),
        _line(6, "Vietnam dong balancx", None),
    )
    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, _spec())
    assert scan["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    selected_region = scan["regions"][0]
    assert not any(
        item["match_kind"].startswith("ONE_EDIT_ALIAS") for item in selected_region["child_matches"]
    )
    joined = [
        {
            "lines": [
                {
                    "bbox": copy.deepcopy(line["bbox"]),
                    "line_ordinal": line["source_line_index"],
                    "numeric_recognition": {"raw_prediction": line["source_text"] or ""},
                    "vietocr_text": line["vietocr_text"],
                }
                for line in pages[0]["lines"]
            ],
            "page_sequence": 1,
        }
    ]

    receipt, reasons = sweep_v1._selected_v4_one_edit_authority_v1(
        {
            "candidate_ordinal": 0,
            "row_axis": {"topology_region": _expanded(pages, selected_region)},
        },
        joined_pages=joined,
        family_spec=_spec(),
        topology_candidates={"regions": scan["regions"]},
    )

    assert reasons == []
    assert receipt["status"] == "NOT_REQUIRED_NO_SELECTED_ONE_EDIT_RETRIEVAL"


def test_enumeration_and_bounded_decorative_parenthetical_are_exact_transforms() -> None:
    pages = _pages(
        _line(0, "Family assetx", "1. Family assets (I)"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balance", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
    )
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(pages, region)
    )

    parent = receipt["checks"][0]
    assert parent["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
    assert parent["exact_channel"]["transform"] == (
        "ACCENTLESS_AFTER_ENUMERATION_PREFIX_AND_DECORATIVE_PARENTHETICAL_REMOVAL"
    )


def test_v4_evidence_integration_turns_failed_selected_receipt_into_trial_reasons() -> None:
    pages = _three_level_pages(leaf_source="Vietnam dong balancz")
    region = _selected(pages)
    joined = [
        {
            "lines": [
                {
                    "bbox": copy.deepcopy(line["bbox"]),
                    "line_ordinal": line["source_line_index"],
                    "numeric_recognition": {"raw_prediction": line["source_text"] or ""},
                    "vietocr_text": line["vietocr_text"],
                }
                for line in pages[0]["lines"]
            ],
            "page_sequence": 1,
        }
    ]
    selected = {
        "candidate_ordinal": 0,
        "row_axis": {"topology_region": _expanded(pages, region)},
    }

    receipt, reasons = sweep_v1._selected_v4_one_edit_authority_v1(
        selected,
        joined_pages=joined,
        family_spec=_spec(),
        topology_candidates={"regions": [region]},
    )

    assert receipt["status"] == ("UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY")
    assert reasons == receipt["unresolved_reasons"]
    assert any("BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT" in reason for reason in reasons)
    mapping = mapping_v1._trial(
        {
            "document_ordinal": 1,
            "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
            "private_provenance": {},
            "source_pdf_ref": {},
            "unresolved_reasons": reasons,
        },
        {},
        {},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec={},
    )
    assert mapping["mapping_status"] == "UNRESOLVED"
    assert mapping["mappings"] == []
