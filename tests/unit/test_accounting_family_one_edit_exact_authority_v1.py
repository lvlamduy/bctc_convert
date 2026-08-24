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
    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, spec or _spec())
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    return scan["regions"][0]


def _expanded(region: dict) -> dict:
    expanded = copy.deepcopy(region)
    decorated = []
    for ordinal, raw_match in enumerate(expanded["child_matches"]):
        match = {
            **raw_match,
            "occurrence_id": f"test:occurrence:{ordinal}:{raw_match['role']}",
        }
        within_role = match.get("matched_within_role")
        owners = [item for item in decorated if item["role"] == within_role]
        owner = owners[-1] if owners else None
        match["scope_owner_occurrence_id"] = (
            owner["occurrence_id"] if owner is not None else "test:root"
        )
        match["scope_owner_role"] = owner["role"] if owner is not None else None
        decorated.append(match)
    expanded["child_matches"] = decorated
    return expanded


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
        pages, _spec(), region, _expanded(region)
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
        "test:occurrence:0:DOMESTIC_GROUP",
        "test:occurrence:1:VND_BALANCE",
    ]
    assert all(
        item["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND" for item in receipt["checks"]
    )
    assert all(item["exact_channel"]["alias_pointer"] for item in receipt["checks"])


def test_coextensive_effective_child_copied_from_parent_needs_its_own_role_alias() -> None:
    spec = _spec()
    spec["children"].append(
        {
            "matchers": [_matcher("Family assets")],
            "presence": "OPTIONAL",
            "role": "EXPLICIT_FAMILY_TOTAL",
            "role_kind": "TOTAL",
        }
    )
    pages = _three_level_pages()
    region = _selected(pages, spec)
    effective = copy.deepcopy(region)
    effective_total = {
        **copy.deepcopy(region["parent_match"]),
        "matched_within_role": None,
        "preferred_ordinal": 3,
        "presence": "OPTIONAL",
        "role": "EXPLICIT_FAMILY_TOTAL",
        "role_kind": "TOTAL",
    }
    effective["child_matches"].append(effective_total)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, spec, region, _expanded(effective)
    )

    assert receipt["status"] == "EXACT_SOURCE_AUTHORITY_BOUND"
    total = next(item for item in receipt["checks"] if item["role"] == "EXPLICIT_FAMILY_TOTAL")
    assert total["status"] == "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
    assert total["exact_channel"]["alias_pointer"] == "/children/3/matchers/0/aliases/0"


def test_missing_bound_source_text_fails_closed() -> None:
    pages = _three_level_pages(leaf_source=None)
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(region)
    )

    leaf = next(item for item in receipt["checks"] if item["role"] == "VND_BALANCE")
    assert leaf["status"] == "MISSING_BOUND_SOURCE_TEXT"
    assert receipt["status"] == ("UNRESOLVED_SELECTED_ONE_EDIT_WITHOUT_EXACT_SOURCE_AUTHORITY")


def test_source_channel_that_is_still_one_edit_is_not_exact_authority() -> None:
    pages = _three_level_pages(leaf_source="Vietnam dong balancz")
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(region)
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
        pages, _spec(), region, _expanded(region)
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
        pages, _spec(), region, _expanded(region)
    )

    leaf = next(item for item in receipt["checks"] if item["role"] == "VND_BALANCE")
    assert leaf["within_role"] == "DOMESTIC_GROUP"
    assert leaf["status"] == "EXACT_STRUCTURAL_PARENT_CONTEXT_MISMATCH"
    assert leaf["exact_channel"]["context_binding"]["family_id"] == "FAMILY_ASSETS"


def test_exact_leaf_without_the_exact_selected_family_parent_cannot_corroborate() -> None:
    pages = _pages(
        _line(0, "Family assets", "Another family"),
        _line(1, "Domestic deposits", "Domestic deposits"),
        _line(2, "Vietnam dong balancx", "Vietnam dong balance"),
        _line(3, "Next family", "Next family"),
    )
    region = _selected(pages)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, _expanded(region)
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
    occurrences = topology_v1.enumerate_accounting_family_role_occurrences_v1(
        pages, _spec(), region
    )
    assert [item["source_line_index"] for item in occurrences if item["role"] == "VND_BALANCE"] == [
        2,
        3,
    ]
    expanded = copy.deepcopy(region)
    expanded["child_matches"] = occurrences
    expanded = _expanded(expanded)

    receipt = subject.build_accounting_family_one_edit_exact_authority_v1(
        pages, _spec(), region, expanded
    )

    assert receipt["metrics"]["selected_one_edit_match_count"] == 1
    repeated = receipt["checks"][0]
    assert repeated["occurrence_id"] == "test:occurrence:2:VND_BALANCE"
    assert repeated["source_line_indices"] == [3]
    assert repeated["status"] == "BOUND_SOURCE_TEXT_REMAINS_ONE_EDIT_NOT_EXACT"
    assert "OCCURRENCE_test:occurrence:2:VND_BALANCE" in receipt["unresolved_reasons"][0]


def test_expanded_one_edit_occurrence_without_occurrence_id_is_rejected() -> None:
    pages = _three_level_pages()
    region = _selected(pages)
    expanded = _expanded(region)
    expanded["child_matches"][-1].pop("occurrence_id")

    with pytest.raises(
        subject.AccountingFamilyOneEditExactAuthorityV1Error,
        match="expanded occurrence identity axis drifted",
    ):
        subject.build_accounting_family_one_edit_exact_authority_v1(
            pages, _spec(), region, expanded
        )


def test_receipt_tamper_and_coherent_identity_rehash_are_rejected_by_replay() -> None:
    pages = _three_level_pages()
    region = _selected(pages)
    expanded = _expanded(region)
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
        pages, _spec(), selected, _expanded(selected)
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
        {"candidate_ordinal": 0, "row_axis": {"topology_region": _expanded(selected_region)}},
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
        pages, _spec(), region, _expanded(region)
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
        "row_axis": {"topology_region": _expanded(region)},
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
