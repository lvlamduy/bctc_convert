from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import (
    gemini_json_loan_interest_accrual_classification_family_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA256 = "1" * 64
PAGE = "gfpstorev1:json:" + "2" * 64


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_bytes())


def _compiled() -> dict:
    return subject.compile_gemini_json_loan_interest_accrual_classification_family_specs_v1(
        _json(
            "config/families/"
            "tm-loan-interest-accrual-classification-topology-v1.json"
        ),
        _json(
            "config/families/"
            "tm-loan-interest-accrual-classification-evaluation-v1.json"
        ),
        _json(
            "config/families/"
            "tm-loan-interest-accrual-classification-schema-binding-v1.json"
        ),
    )


def _region(*, page: str = PAGE, selected_page_ordinal: int = 1) -> dict:
    return {
        "component_roles": ["INTEREST_FEE_RECEIVABLES"],
        "document_id": "gfpstorev1:document:" + "3" * 64,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": page,
        "physical_page": selected_page_ordinal,
        "section_id": "s1",
        "selected_page_ordinal": selected_page_ordinal,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }


def _mapping(report_norm_id: int, *, role: str) -> dict:
    return {
        "report_norm_id": report_norm_id,
        "role": role,
        "row_id": "r1",
        "source_refs": [
            {
                "hierarchy_path_exact": [role],
                "label_exact": role,
                "locator": _region(),
                "money_column_ordinals": [1, 2],
                "row_id": "r1",
                "row_kind": "ITEM",
                "row_ordinal": 1,
            }
        ],
        "state": "SOURCE_OBSERVED_ROLE_ROW",
        "unit": "MILLION_VND",
        "values": [
            {"coefficient": 1, "source_text": "1", "state": "RAW_SIGNED_INTEGER"},
            {
                "coefficient": None,
                "source_text": None,
                "state": "BLANK_SOURCE_CELL",
            },
        ],
    }


def _sweep(family_id: str, *mappings: dict) -> dict:
    return {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "4" * 64,
        "family_id": family_id,
        "sweep_id": "sweep:" + family_id,
        "trials": [
            {
                "document_ordinal": 1,
                "mappings": list(mappings),
                "source_logical_name": "bank/2025/report.pdf",
                "source_sha256": SOURCE_SHA256,
            }
        ],
    }


def test_compile_owns_only_982_through_986_and_never_emits_context_root() -> None:
    compiled = _compiled()

    assert compiled["bindings"] == subject.OWNED_ROLE_BINDINGS
    assert compiled["schema"]["family_root_report_norm_id"] == 966
    assert compiled["schema"]["root_mapping_policy"] == "STRUCTURAL_CONTEXT_ONLY"
    assert compiled["evaluation"]["derived_role_equations"] == []
    assert compiled["evaluation"]["corroboration_pairs"] == []
    assert "lai phi phai thu tu cho vay" in compiled["aliases_by_role"][
        "CREDIT_INTEREST"
    ]
    assert "lai phai thu tu tien gui va cho vay cac tctd khac" in (
        compiled["aliases_by_role"]["DEPOSIT_INTEREST"]
    )
    assert "lai phi phai thu tu giao dich hoan doi" in (
        compiled["aliases_by_role"]["DERIVATIVE_INTEREST"]
    )
    assert "lai phai thu tu chung khoan dau tu" in compiled["aliases_by_role"][
        "OTHER_INTEREST"
    ]
    assert not any(
        "chuong trinh ho tro lai suat" in alias
        for aliases in compiled["aliases_by_role"].values()
        for alias in aliases
    )


def test_cross_family_gate_rejects_legacy_ownership_even_on_another_row() -> None:
    f26 = _sweep(
        subject.FAMILY_ID,
        _mapping(982, role="INTEREST_FEE_RECEIVABLES"),
    )
    f22 = _sweep(
        subject.LEGACY_OWNER_FAMILY_ID,
        _mapping(983, role="CREDIT_INTEREST"),
    )

    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="handoff is incomplete",
    ):
        subject.build_loan_interest_accrual_cross_family_disjointness_receipt_v1(
            f26_sweep=f26, other_assets_sweep=f22
        )


def test_cross_family_gate_seals_clean_same_corpus_source_axis() -> None:
    f26 = _sweep(
        subject.FAMILY_ID,
        _mapping(982, role="INTEREST_FEE_RECEIVABLES"),
    )
    f22_mapping = copy.deepcopy(_mapping(967, role="RECEIVABLES"))
    f22_mapping["source_refs"][0]["row_id"] = "r2"
    f22_mapping["source_refs"][0]["row_ordinal"] = 2
    f22 = _sweep(subject.LEGACY_OWNER_FAMILY_ID, f22_mapping)

    receipt = (
        subject.build_loan_interest_accrual_cross_family_disjointness_receipt_v1(
            f26_sweep=f26, other_assets_sweep=f22
        )
    )

    assert receipt["overlap_count"] == 0
    assert receipt["owned_report_norm_ids"] == [982, 983, 984, 985, 986]
    assert receipt["trial_source_axis_count"] == 1


def test_cross_family_gate_rejects_same_id_with_different_source_axis() -> None:
    f26 = _sweep(
        subject.FAMILY_ID,
        _mapping(982, role="INTEREST_FEE_RECEIVABLES"),
    )
    f22 = _sweep(subject.LEGACY_OWNER_FAMILY_ID)
    f22["trials"][0]["source_sha256"] = "9" * 64

    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="same exact source corpus",
    ):
        subject.build_loan_interest_accrual_cross_family_disjointness_receipt_v1(
            f26_sweep=f26, other_assets_sweep=f22
        )


def test_partial_source_lane_is_retained_as_null_not_equation_zero() -> None:
    region = _region()
    page = {
        "sections": [
            {
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Các khoản lãi, phí phải thu"],
                                "label_exact": "Các khoản lãi, phí phải thu",
                                "row_id": "r1",
                                "row_kind": "ITEM",
                                "values_exact": ["1", None],
                            }
                        ],
                        "unit_exact": "Triệu đồng",
                    }
                ]
            }
        ]
    }

    def classify(*_: object, **__: object) -> dict:
        return {
            "money_column_ordinals": [1, 2],
            "role_hits": [
                {"role": "INTEREST_FEE_RECEIVABLES", "row_ordinal": 1}
            ],
        }

    def evaluate(**_: object) -> dict:
        return {
            "closure_receipt": {
                "table_receipts": [
                    {"lane_axis": {"complete": True, "lane_keys": ["A", "B"]}}
                ]
            }
        }

    original_classify = subject.classify_gemini_json_multitable_hierarchical_table_v1
    original_evaluate = (
        subject.evaluate_gemini_json_multitable_hierarchical_family_cluster_v1
    )
    subject.classify_gemini_json_multitable_hierarchical_table_v1 = classify
    subject.evaluate_gemini_json_multitable_hierarchical_family_cluster_v1 = evaluate
    try:
        observation = subject._primary_observation(
            region,
            page_json_by_version={PAGE: page},
            compiled_specs=_compiled(),
        )
    finally:
        subject.classify_gemini_json_multitable_hierarchical_table_v1 = original_classify
        subject.evaluate_gemini_json_multitable_hierarchical_family_cluster_v1 = (
            original_evaluate
        )

    mapping = observation["mapping"]

    assert mapping["values"][0]["coefficient"] == 1
    assert mapping["values"][1] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }


def test_primary_note_corroboration_never_turns_blank_into_zero() -> None:
    primary = _mapping(982, role="INTEREST_FEE_RECEIVABLES")
    note = copy.deepcopy(primary)

    corroborated, receipt = subject._mapping_values_corroborate(
        primary, note, compiled_specs=_compiled()
    )
    assert corroborated is True
    assert receipt["lane_receipts"][1]["corroborated"] is True

    note["values"][1] = {
        "coefficient": 0,
        "source_text": "-",
        "state": "RAW_SIGNED_INTEGER",
    }
    corroborated, receipt = subject._mapping_values_corroborate(
        primary, note, compiled_specs=_compiled()
    )
    assert corroborated is False
    assert receipt["lane_receipts"][1] == {
        "corroborated": False,
        "lane_ordinal": 2,
        "note_coefficient": 0,
        "primary_coefficient": None,
    }


def test_vab_duplicate_presentations_choose_rounded_highest_precision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vnd = _region(page=PAGE, selected_page_ordinal=1)
    million = _region(
        page="gfpstorev1:json:" + "5" * 64,
        selected_page_ordinal=2,
    )

    def observation(region: dict, **_: object) -> dict:
        is_vnd = region["page_json_version_id"] == PAGE
        values = (
            [4_803_118_026_101, 4_676_753_561_658]
            if is_vnd
            else [4_803_118, 4_676_754]
        )
        return {
            "candidate": {},
            "magnitude_power10": 0 if is_vnd else 6,
            "mapping": {
                "values": [
                    {
                        "coefficient": value,
                        "source_text": str(value),
                        "state": "RAW_SIGNED_INTEGER",
                    }
                    for value in values
                ]
            },
            "reasons": [],
            "region": copy.deepcopy(region),
            "unit": "VND" if is_vnd else "MILLION_VND",
            "unit_rule": "LOCAL_PRIMARY_TABLE_EXPLICIT_UNIT",
        }

    monkeypatch.setattr(subject, "_primary_observation", observation)

    selected, receipt = subject._select_primary_region(
        [million, vnd], page_json_by_version={}, compiled_specs={}
    )

    assert selected == [vnd]
    assert receipt["rule"] == (
        "ROUNDED_LOWER_PRECISION_DUPLICATES_SELECT_HIGHEST_PRECISION_SOURCE"
    )


def test_duplicate_primary_presentations_preserve_matching_blank_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vnd = _region(page=PAGE, selected_page_ordinal=1)
    million = _region(
        page="gfpstorev1:json:" + "5" * 64,
        selected_page_ordinal=2,
    )

    def observation(region: dict, **_: object) -> dict:
        is_vnd = region["page_json_version_id"] == PAGE
        coefficient = 4_803_118_026_101 if is_vnd else 4_803_118
        return {
            "candidate": {},
            "magnitude_power10": 0 if is_vnd else 6,
            "mapping": {
                "values": [
                    {
                        "coefficient": coefficient,
                        "source_text": str(coefficient),
                        "state": "RAW_SIGNED_INTEGER",
                    },
                    {
                        "coefficient": None,
                        "source_text": None,
                        "state": "BLANK_SOURCE_CELL",
                    },
                ]
            },
            "reasons": [],
            "region": copy.deepcopy(region),
            "unit": "VND" if is_vnd else "MILLION_VND",
            "unit_rule": "LOCAL_PRIMARY_TABLE_EXPLICIT_UNIT",
        }

    monkeypatch.setattr(subject, "_primary_observation", observation)

    selected, receipt = subject._select_primary_region(
        [million, vnd], page_json_by_version={}, compiled_specs={}
    )

    assert selected == [vnd]
    assert receipt["observations"][0]["values"][1]["state"] == "BLANK_SOURCE_CELL"
    assert receipt["rule"] == (
        "ROUNDED_LOWER_PRECISION_DUPLICATES_SELECT_HIGHEST_PRECISION_SOURCE"
    )


def test_duplicate_primary_numeric_conflict_remains_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _region(page=PAGE, selected_page_ordinal=1)
    second = _region(page="gfpstorev1:json:" + "6" * 64, selected_page_ordinal=2)

    def observation(region: dict, **_: object) -> dict:
        coefficient = 100 if region["page_json_version_id"] == PAGE else 999
        return {
            "candidate": {},
            "magnitude_power10": 0,
            "mapping": {
                "values": [
                    {
                        "coefficient": coefficient,
                        "source_text": str(coefficient),
                        "state": "RAW_SIGNED_INTEGER",
                    },
                    {
                        "coefficient": coefficient,
                        "source_text": str(coefficient),
                        "state": "RAW_SIGNED_INTEGER",
                    },
                ]
            },
            "reasons": [],
            "region": copy.deepcopy(region),
            "unit": "VND",
            "unit_rule": "LOCAL_PRIMARY_TABLE_EXPLICIT_UNIT",
        }

    monkeypatch.setattr(subject, "_primary_observation", observation)

    selected, receipt = subject._select_primary_region(
        [first, second], page_json_by_version={}, compiled_specs={}
    )

    assert len(selected) == 2
    assert receipt["rule"] == "ALL_PRIMARY_SOURCE_PRESENTATIONS_RETAINED_UNRESOLVED"


def test_mixed_primary_and_detail_note_merge_emits_total_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = _region()
    note_page = "gfpstorev1:json:" + "7" * 64
    note = _region(page=note_page, selected_page_ordinal=2)
    note["fragment_ordinal"] = 2
    note["component_roles"] = ["CREDIT_INTEREST", "INTEREST_FEE_RECEIVABLES"]
    primary_mapping = _mapping(982, role="INTEREST_FEE_RECEIVABLES")
    note_total = copy.deepcopy(primary_mapping)
    note_total["source_refs"][0]["locator"] = copy.deepcopy(note)
    child = _mapping(983, role="CREDIT_INTEREST")
    child["source_refs"][0]["locator"] = copy.deepcopy(note)

    def source_table(page: dict, **_: object) -> tuple[dict, dict]:
        return (
            {
                "content_kind": (
                    "PRIMARY_STATEMENT" if page["primary"] else "NOTE_DISCLOSURE"
                ),
                "statement_type": "BALANCE_SHEET",
            },
            {},
        )

    def observation(region: dict, **_: object) -> dict:
        return {
            "candidate": {},
            "magnitude_power10": 6,
            "mapping": copy.deepcopy(primary_mapping),
            "reasons": [],
            "region": copy.deepcopy(region),
            "table_receipt": {},
            "unit": "MILLION_VND",
            "unit_rule": "LOCAL_PRIMARY_TABLE_EXPLICIT_UNIT",
        }

    def evaluate(**_: object) -> dict:
        return {
            "closure_receipt": {"query_receipt": {"note": True}},
            "mappings": [note_total, child],
            "reasons": [],
            "status": subject.READY,
        }

    monkeypatch.setattr(subject, "_source_table", source_table)
    monkeypatch.setattr(subject, "_primary_observation", observation)
    monkeypatch.setattr(
        subject,
        "evaluate_gemini_json_multitable_hierarchical_family_cluster_v1",
        evaluate,
    )

    candidate = subject._evaluate_candidate(
        regions=[primary, note],
        page_json_by_version={PAGE: {"primary": True}, note_page: {"primary": False}},
        compiled_specs=_compiled(),
    )

    assert candidate["status"] == subject.READY
    assert [mapping["report_norm_id"] for mapping in candidate["mappings"]] == [
        982,
        983,
    ]
    assert candidate["mappings"][0]["source_refs"][0]["locator"] == _region()
    assert candidate["closure_receipt"][
        "primary_detail_note_total_corroboration"
    ]["corroborated"] is True


def test_detail_promotion_requires_local_explicit_family_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = {
        "document_id": "gfpstorev1:document:" + "3" * 64,
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    page_axis = [
        {
            **document,
            "page_json_version_id": PAGE,
            "physical_page": 1,
            "selected_page_ordinal": 1,
        }
    ]
    page = {
        "sections": [
            {
                "content_kind": "NOTE_DISCLOSURE",
                "statement_type": "BALANCE_SHEET",
                "tables": [{"context": "explicit"}],
            },
            {
                "content_kind": "NOTE_DISCLOSURE",
                "statement_type": "BALANCE_SHEET",
                "tables": [{"context": "row_population_only"}],
            },
        ]
    }

    def classify(_: dict, __: dict, table: dict, **___: object) -> dict:
        return {
            "context_resolution_kind": (
                "EXPLICIT_TABLE_TITLE"
                if table["context"] == "explicit"
                else "DECLARED_ROW_POPULATION_SCOPE"
            ),
            "context_roles": ["INTEREST_FEE_RECEIVABLES"],
            "family_presence_anchor_visible": True,
            "role_hits": [
                {"role": "CREDIT_INTEREST", "row_ordinal": 1},
            ],
        }

    monkeypatch.setattr(
        subject,
        "classify_gemini_json_multitable_hierarchical_table_v1",
        classify,
    )

    selected, receipt = subject._explicit_detail_regions(
        document=document,
        selected_page_axis=page_axis,
        page_json_by_version={PAGE: page},
        compiled_specs={},
    )

    assert [(region["section_id"], region["table_id"]) for region in selected] == [
        ("s1", "t1")
    ]
    assert receipt["rejected_population_scoped_tables"][0]["section_id"] == "s2"
    assert receipt["rejected_population_scoped_tables"][0]["rule"] == (
        "NONLOCAL_ROW_POPULATION_CONTEXT_CANNOT_PROMOTE_A_DETAIL_TABLE"
    )


def test_source_row_coverage_fails_closed_on_unmapped_explicit_detail() -> None:
    mapping = _mapping(983, role="CREDIT_INTEREST")
    page = {
        "sections": [
            {
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Lãi phải thu từ cho vay"],
                                "label_exact": "Lãi phải thu từ cho vay",
                                "row_id": "r1",
                                "values_exact": ["1", "2"],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    cluster = {
        "declared_money_table_inventory": [
            {
                "classification": {
                    "context_resolution_kind": "EXPLICIT_TABLE_TITLE",
                    "context_roles": ["INTEREST_FEE_RECEIVABLES"],
                    "money_column_ordinals": [1, 2],
                    "owner_visible": True,
                    "role_hits": [{"role": "CREDIT_INTEREST", "row_ordinal": 1}],
                    "typed_control_disposition": None,
                },
                "disposition": "SELECTED_FAMILY_COMPONENT",
                "page_json_version_id": PAGE,
                "physical_page": 1,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}]
        },
        "trials": [{"candidates": [], "mappings": [mapping]}],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )
    assert receipt["disposition_counts"] == {"MAPPED_EXACT_SOURCE_ROW": 1}
    assert receipt["violation_count"] == 0

    sweep["trials"][0]["mappings"] = []
    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep, page_json_by_document={1: {PAGE: page}}
        )


def test_source_row_coverage_rejects_nonlocal_child_but_classifies_total_control() -> None:
    page = {
        "sections": [
            {
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Các khoản lãi, phí phải thu"],
                                "label_exact": "Các khoản lãi, phí phải thu",
                                "row_id": "r1",
                                "values_exact": ["1", "2"],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    classification = {
        "context_resolution_kind": None,
        "context_roles": [],
        "money_column_ordinals": [1, 2],
        "owner_visible": False,
        "role_hits": [
            {"role": "INTEREST_FEE_RECEIVABLES", "row_ordinal": 1}
        ],
        "typed_control_disposition": None,
    }
    cluster = {
        "declared_money_table_inventory": [
            {
                "classification": classification,
                "disposition": "SOURCE_ONLY_UNMAPPED",
                "page_json_version_id": PAGE,
                "physical_page": 1,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {"candidate_dispositions": [{"cluster": cluster}]},
        "trials": [{"candidates": [], "mappings": []}],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )
    assert receipt["disposition_counts"] == {
        "REJECTED_NONLOCAL_TOTAL_CONTROL_CONTEXT": 1
    }

    classification["role_hits"] = [{"role": "CREDIT_INTEREST", "row_ordinal": 1}]
    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep, page_json_by_document={1: {PAGE: page}}
        )


def test_source_row_coverage_exception_is_exactly_general_receivables_context() -> None:
    source_ref = _mapping(983, role="CREDIT_INTEREST")["source_refs"][0]
    source_ref["hierarchy_path_exact"] = [
        "Các khoản phải thu",
        "Phải thu liên quan đến các chương trình hỗ trợ lãi suất",
    ]
    source_ref["label_exact"] = (
        "Phải thu liên quan đến các chương trình hỗ trợ lãi suất"
    )
    page = {
        "sections": [
            {
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Các khoản phải thu",
                                    "Phải thu liên quan đến các chương trình hỗ trợ lãi suất",
                                ],
                                "label_exact": source_ref["label_exact"],
                                "values_exact": ["1", "2"],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    cluster = {
        "declared_money_table_inventory": [],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}]
        },
        "trials": [
            {
                "candidates": [
                    {
                        "closure_receipt": {
                            "source_only_unmapped_rows": [
                                {"source_ref": copy.deepcopy(source_ref)}
                            ]
                        }
                    }
                ],
                "document_ordinal": 1,
                "mappings": [],
            }
        ],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )
    assert len(receipt["target_like_non_family_exclusion_axis"]) == 1
    assert receipt["violation_count"] == 0

    sweep["trials"][0]["candidates"][0]["closure_receipt"][
        "source_only_unmapped_rows"
    ][0]["source_ref"]["label_exact"] = "Lãi phải thu từ cho vay"
    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep, page_json_by_document={1: {PAGE: page}}
        )


def test_source_row_coverage_scans_unclassified_rows_outside_candidate_receipts() -> None:
    page = {
        "sections": [
            {
                "tables": [
                    {
                        "title_exact": "Các khoản lãi, phí phải thu",
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Một nhóm chưa được khai báo"
                                ],
                                "label_exact": "Lãi phải thu từ nguồn mới",
                                "row_id": "r1",
                                "values_exact": ["1", "2"],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    cluster = {
        "declared_money_table_inventory": [],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}],
            "selected_page_axis": [
                {"page_json_version_id": PAGE, "physical_page": 1}
            ],
        },
        "trials": [{"candidates": [], "mappings": []}],
    }

    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep, page_json_by_document={1: {PAGE: page}}
        )


@pytest.mark.parametrize(
    ("label_exact", "expected"),
    [
        ("Lãi phải thu từ cho vay", True),
        ("Phí phải thu khác", True),
        ("Lai phai thu tu tien gui", True),
        ("Accrued interest receivable", True),
        (
            "Các khoản phải thu từ các hợp đồng mua và cam kết bán lại chứng khoán",
            False,
        ),
        (
            "Khoản nợ phải thu hồi của TCTD phi ngân hàng",
            False,
        ),
    ],
)
def test_raw_target_detector_is_accent_and_token_sensitive(
    label_exact: str, expected: bool
) -> None:
    assert subject._target_like_receivable_label(label_exact) is expected


def test_raw_target_surface_recovers_row_local_label_loss_only() -> None:
    assert subject._target_like_receivable_source_surface(
        label_exact=None,
        hierarchy_path_exact=["11.2 Các khoản lãi, phí phải thu", None],
    ) == {
        "origin": "HIERARCHY_TERMINAL_EXACT",
        "surface_exact": "11.2 Các khoản lãi, phí phải thu",
        "value_ordinal": None,
    }
    assert subject._target_like_receivable_source_surface(
        label_exact="Công ty liên quan",
        hierarchy_path_exact=[
            "Công ty liên quan",
            "Lãi phải thu từ cho vay khách hàng",
        ],
    ) == {
        "origin": "HIERARCHY_TERMINAL_EXACT",
        "surface_exact": "Lãi phải thu từ cho vay khách hàng",
        "value_ordinal": None,
    }
    assert subject._target_like_receivable_source_surface(
        label_exact="2.",
        hierarchy_path_exact=["A", "XI.", "2."],
        columns=[
            {"value_kind": "TEXT"},
            {"value_kind": "MONEY"},
            {"value_kind": "MONEY"},
        ],
        values_exact=["Các khoản lãi, phí phải thu", "3.346", "2.778"],
    ) == {
        "origin": "EXPLICIT_TEXT_VALUE_CELL",
        "surface_exact": "Các khoản lãi, phí phải thu",
        "value_ordinal": 1,
    }
    assert (
        subject._target_like_receivable_source_surface(
            label_exact="Khoản phải thu khác",
            hierarchy_path_exact=[
                "Các khoản lãi, phí phải thu",
                "Khoản phải thu khác",
            ],
        )
        is None
    )
    narrative = (
        "Một đoạn thuyết minh dài "
        + "về lãi dự thu và chính sách kế toán " * 20
    )
    assert subject._target_like_receivable_source_surface(
        label_exact=None,
        hierarchy_path_exact=[None],
        columns=[{"value_kind": "TEXT"}],
        values_exact=[narrative],
    ) == {
        "origin": "NARRATIVE_TEXT_VALUE_CELL",
        "surface_exact": narrative,
        "value_ordinal": 1,
    }
    assert subject._raw_target_context_disposition(
        label_exact=narrative,
        hierarchy_path_exact=[None],
        section_title_exact=None,
        table_title_exact=None,
        inventory_disposition=None,
        target_surface_origin="NARRATIVE_TEXT_VALUE_CELL",
    )["coverage"] == "OUTSIDE_FAMILY26_NARRATIVE_POLICY_OR_RISK_TEXT"


def test_split_label_and_amount_rows_are_one_accounted_source_representation() -> None:
    aggregate_path = [
        "A",
        "TÀI SẢN",
        "XII",
        "Tài sản Có khác",
        "2",
        "Các khoản lãi, phí phải thu",
    ]
    page = {
        "sections": [
            {
                "title_exact": "Báo cáo tình hình tài chính",
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": aggregate_path,
                                "label_exact": "2",
                                "row_id": "r1",
                                "row_kind": "ITEM",
                                "values_exact": ["14(b)", "3.346", "2.778"],
                            },
                            {
                                "hierarchy_path_exact": aggregate_path,
                                "label_exact": "Các khoản lãi, phí phải thu",
                                "row_id": "r2",
                                "row_kind": "ITEM",
                                "values_exact": ["14(b)", "3.346", "2.778"],
                            },
                        ]
                    }
                ],
            }
        ]
    }
    aggregate = _mapping(982, role="INTEREST_FEE_RECEIVABLES")
    aggregate["row_id"] = "r2"
    aggregate["source_refs"][0].update(
        {
            "hierarchy_path_exact": aggregate_path,
            "label_exact": "Các khoản lãi, phí phải thu",
            "money_column_ordinals": [2, 3],
            "row_id": "r2",
            "row_ordinal": 2,
        }
    )
    classification = {
        "context_resolution_kind": "DECLARED_ROW_POPULATION_SCOPE",
        "context_roles": [],
        "money_column_ordinals": [2, 3],
        "owner_visible": True,
        "role_hits": [
            {"role": "INTEREST_FEE_RECEIVABLES", "row_ordinal": 2}
        ],
        "typed_control_disposition": None,
    }
    cluster = {
        "declared_money_table_inventory": [
            {
                "classification": classification,
                "disposition": "SELECTED_FAMILY_COMPONENT",
                "page_json_version_id": PAGE,
                "physical_page": 1,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}],
            "selected_page_axis": [
                {"page_json_version_id": PAGE, "physical_page": 1}
            ],
        },
        "trials": [
            {
                "candidates": [],
                "document_ordinal": 1,
                "mappings": [aggregate],
            }
        ],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )

    assert receipt["raw_target_like_disposition_counts"] == {
        "ACCOUNTED_CLASSIFIED_SOURCE_ROW": 1,
        "CORROBORATED_ADJACENT_DUPLICATE_SOURCE_REPRESENTATION": 1,
    }
    split = next(
        item
        for item in receipt["raw_target_like_row_axis"]
        if item["row_ordinal"] == 1
    )
    assert split["target_surface_exact"] == "Các khoản lãi, phí phải thu"
    assert split["duplicate_source_row_representation_ref"]["row_ordinal"] == 2
    assert receipt["violation_count"] == 0


def test_text_cell_primary_presentation_requires_exact_source_corroboration() -> None:
    page = {
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "statement_type": "BALANCE_SHEET",
                "title_exact": "Báo cáo tình hình tài chính",
                "tables": [
                    {
                        "columns": [
                            {"value_kind": "TEXT"},
                            {"value_kind": "TEXT"},
                            {"value_kind": "MONEY"},
                            {"value_kind": "MONEY"},
                        ],
                        "rows": [
                            {
                                "hierarchy_path_exact": ["A", "XI", "2"],
                                "label_exact": "2",
                                "row_id": "r1",
                                "row_kind": "ITEM",
                                "values_exact": [
                                    "Các khoản lãi, phí phải thu",
                                    None,
                                    "8.303.657",
                                    "4.745.521",
                                ],
                            }
                        ],
                        "unit_exact": "Triệu VND",
                    }
                ],
            }
        ]
    }
    aggregate = _mapping(982, role="INTEREST_FEE_RECEIVABLES")
    aggregate["values"] = [
        {
            "coefficient": 8_303_657,
            "source_text": "8.303.657",
            "state": "RAW_SIGNED_INTEGER",
        },
        {
            "coefficient": 4_745_521,
            "source_text": "4.745.521",
            "state": "RAW_SIGNED_INTEGER",
        },
    ]
    aggregate["item_mapping_id"] = "gjmthfmv1:item:" + "5" * 64
    cluster = {
        "declared_money_table_inventory": [],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}],
            "selected_page_axis": [
                {"page_json_version_id": PAGE, "physical_page": 1}
            ],
        },
        "trials": [
            {
                "candidates": [],
                "document_ordinal": 1,
                "mappings": [aggregate],
            }
        ],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep,
        page_json_by_document={1: {PAGE: page}},
        compiled_specs=_compiled(),
    )

    assert receipt["raw_target_like_disposition_counts"] == {
        "CORROBORATED_TEXT_CELL_PRIMARY_PRESENTATION": 1
    }
    row = receipt["raw_target_like_row_axis"][0]
    assert row["target_surface_origin"] == "EXPLICIT_TEXT_VALUE_CELL"
    assert row["target_surface_value_ordinal"] == 1
    assert row["primary_text_cell_corroboration"]["corroborated"] is True
    assert receipt["violation_count"] == 0

    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][2] = (
        "8.303.658"
    )
    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep,
            page_json_by_document={1: {PAGE: page}},
            compiled_specs=_compiled(),
        )


@pytest.mark.parametrize(
    ("section_title", "table_title", "hierarchy", "label", "coverage"),
    [
        (
            "Các chỉ tiêu ngoài báo cáo tình hình tài chính",
            None,
            ["Lãi cho vay và phí phải thu chưa thu được"],
            "Lãi cho vay và phí phải thu chưa thu được",
            "OUTSIDE_FAMILY26_OFF_BALANCE_UNCOLLECTED_INTEREST_FEE",
        ),
        (
            "Giao dịch với các bên liên quan",
            "Số dư cuối kỳ",
            ["Công ty liên quan", "Lãi dự thu cho tiền vay"],
            "Lãi dự thu cho tiền vay",
            "OUTSIDE_FAMILY26_RELATED_PARTY_BALANCE_OR_TRANSACTION",
        ),
        (
            "Giao dịch với các bên liên quan",
            "Số dư cuối kỳ",
            ["Công ty liên quan", "Lãi phải thu từ cho vay khách hàng"],
            "Công ty liên quan",
            "OUTSIDE_FAMILY26_RELATED_PARTY_BALANCE_OR_TRANSACTION",
        ),
        (
            "Tài sản Có khác",
            "Các khoản phải thu",
            ["Phải thu bên ngoài", "Phải thu từ cho vay hỗ trợ lãi suất"],
            "Phải thu từ cho vay hỗ trợ lãi suất",
            "OUTSIDE_FAMILY26_GENERAL_RECEIVABLES_INTEREST_SUPPORT_PROGRAM",
        ),
    ],
)
def test_source_row_coverage_records_explicit_outside_family_dispositions(
    section_title: str,
    table_title: str | None,
    hierarchy: list[str],
    label: str,
    coverage: str,
) -> None:
    page = {
        "sections": [
            {
                "title_exact": section_title,
                "tables": [
                    {
                        "title_exact": table_title,
                        "rows": [
                            {
                                "hierarchy_path_exact": hierarchy,
                                "label_exact": label,
                                "row_id": "r1",
                                "values_exact": ["1", "2"],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    cluster = {
        "declared_money_table_inventory": [],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}],
            "selected_page_axis": [
                {"page_json_version_id": PAGE, "physical_page": 1}
            ],
        },
        "trials": [{"candidates": [], "mappings": []}],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )

    assert receipt["violation_count"] == 0
    assert receipt["raw_target_like_disposition_counts"] == {coverage: 1}
    assert receipt["raw_target_like_row_axis"][0]["context_evidence_exact"]


def test_composite_related_party_row_does_not_promote_family26_aggregate() -> None:
    disposition = subject._raw_target_context_disposition(
        label_exact="Các khoản lãi, phí phải thu và các khoản phải thu khác",
        hierarchy_path_exact=[
            "Thành viên Hội đồng Quản trị và người có liên quan",
            "Các khoản lãi, phí phải thu và các khoản phải thu khác",
        ],
        section_title_exact="Giao dịch với các bên liên quan",
        table_title_exact="Số dư cuối kỳ",
        inventory_disposition="OUTSIDE_SELECTED_OWNER_FENCE",
    )

    assert disposition["coverage"] == (
        "OUTSIDE_FAMILY26_RELATED_PARTY_BALANCE_OR_TRANSACTION"
    )
    assert not subject._is_exact_family26_aggregate_surface(
        "Các khoản lãi, phí phải thu và các khoản phải thu khác"
    )


def test_related_party_continuation_uses_exact_section_narrative_scope() -> None:
    disposition = subject._raw_target_context_disposition(
        label_exact="Các khoản lãi Ngân hàng phải thu",
        hierarchy_path_exact=[
            "Công ty Cổ phần Vàng bạc Đá quý Doji",
            "Các khoản lãi Ngân hàng phải thu",
        ],
        section_title_exact=None,
        table_title_exact=None,
        inventory_disposition="OUTSIDE_SELECTED_OWNER_FENCE",
        section_narratives_exact=[
            "Số dư với các bên liên quan tại thời điểm báo cáo như sau:"
        ],
    )

    assert disposition == {
        "coverage": "OUTSIDE_FAMILY26_RELATED_PARTY_BALANCE_OR_TRANSACTION",
        "context_evidence_exact": [
            "Số dư với các bên liên quan tại thời điểm báo cáo như sau:"
        ],
        "rule": "RELATED_PARTY_AXIS_IS_NOT_THE_BALANCE_SHEET_ACCRUAL_SUBTREE",
    }


def _detail_total_coverage_fixture(*, total_value: str = "1") -> tuple[dict, dict]:
    page = {
        "sections": [
            {
                "title_exact": "Thuyết minh báo cáo tài chính",
                "tables": [
                    {
                        "unit_exact": "Triệu đồng",
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "15. Các khoản lãi, phí phải thu",
                                    "Lãi phải thu từ hoạt động tín dụng",
                                ],
                                "label_exact": (
                                    "Lãi phải thu từ hoạt động tín dụng"
                                ),
                                "row_id": "r1",
                                "row_kind": "ITEM",
                                "values_exact": ["1", None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "15. Các khoản lãi, phí phải thu",
                                    "Cộng",
                                ],
                                "label_exact": "Cộng",
                                "row_id": "r2",
                                "row_kind": "TOTAL",
                                "values_exact": [total_value, None],
                            },
                            {
                                "hierarchy_path_exact": ["16. Tài sản có khác"],
                                "label_exact": "16. Tài sản có khác",
                                "row_id": "r3",
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "16. Tài sản có khác",
                                    "Cộng",
                                ],
                                "label_exact": "Cộng",
                                "row_id": "r4",
                                "row_kind": "TOTAL",
                                "values_exact": ["99", "88"],
                            },
                        ],
                    }
                ],
            }
        ]
    }
    aggregate = _mapping(982, role="INTEREST_FEE_RECEIVABLES")
    child = _mapping(983, role="CREDIT_INTEREST")
    candidate = {
        "closure_receipt": {
            "table_receipts": [
                {
                    "classification": {
                        "context_roles": ["INTEREST_FEE_RECEIVABLES"],
                        "family_presence_anchor_visible": True,
                        "money_column_ordinals": [1, 2],
                        "role_hits": [
                            {"role": "CREDIT_INTEREST", "row_ordinal": 1}
                        ],
                        "total_rows": [
                            {"row_kind": "TOTAL", "row_ordinal": 2},
                            {"row_kind": "TOTAL", "row_ordinal": 4},
                        ],
                        "typed_control_disposition": None,
                    },
                    "lane_axis": {
                        "complete": True,
                        "money_column_ordinals": [1, 2],
                    },
                    "region": _region(),
                    "unit_axis": {
                        "canonical_unit": "MILLION_VND",
                        "complete": True,
                    },
                }
            ]
        },
        "mappings": [aggregate, child],
    }
    cluster = {
        "declared_money_table_inventory": [
            {
                "classification": {
                    "context_resolution_kind": "EXPLICIT_SOLE_TABLE_SECTION_TITLE",
                    "context_roles": ["INTEREST_FEE_RECEIVABLES"],
                    "money_column_ordinals": [1, 2],
                    "owner_visible": False,
                    "role_hits": [
                        {"role": "CREDIT_INTEREST", "row_ordinal": 1}
                    ],
                    "typed_control_disposition": None,
                },
                "disposition": "SELECTED_FAMILY_COMPONENT",
                "page_json_version_id": PAGE,
                "physical_page": 1,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}],
            "selected_page_axis": [
                {"page_json_version_id": PAGE, "physical_page": 1}
            ],
        },
        "trials": [
            {
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [child],
                "source_logical_name": "bank/2025/report.pdf",
                "source_sha256": SOURCE_SHA256,
            }
        ],
    }
    return sweep, page


def test_visible_adjacent_detail_total_is_covered_without_duplicate_mapping() -> None:
    sweep, page = _detail_total_coverage_fixture()

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )

    total_rows = [
        item
        for item in receipt["source_row_axis"]
        if item.get("coverage")
        == "CORROBORATED_VISIBLE_FAMILY26_DETAIL_TOTAL_CONTROL"
    ]
    assert [(item["row_ordinal"], item["report_norm_id"]) for item in total_rows] == [
        (2, 982)
    ]
    assert total_rows[0]["lane_corroboration_receipts"][1] == {
        "corroborated": True,
        "expected_existing_mapping_coefficient": None,
        "lane_ordinal": 2,
        "source_observed_total_coefficient": None,
        "source_observed_total_state": "BLANK_SOURCE_CELL",
    }
    assert len(sweep["trials"][0]["mappings"]) == 1
    assert all(item["row_ordinal"] != 4 for item in receipt["source_row_axis"])
    assert {
        item["row_ordinal"]: item["coverage"]
        for item in receipt["candidate_table_total_row_axis"]
    } == {
        2: "CORROBORATED_VISIBLE_FAMILY26_DETAIL_TOTAL_CONTROL",
        4: "OUTSIDE_FAMILY26_FOLLOWING_OTHER_NOTE_TOTAL",
    }
    following = receipt["candidate_table_total_row_axis"][1]
    boundary_axis = following["receipt_context_axis"][0][
        "following_scope_boundary_axis"
    ]
    assert [item["row_ordinal"] for item in boundary_axis] == [2, 3]
    assert boundary_axis[0]["boundary_evidence_kinds"] == [
        "INTERVENING_STRUCTURAL_ROW"
    ]
    assert boundary_axis[1]["boundary_evidence_kinds"] == [
        "INTERVENING_STRUCTURAL_ROW",
        "INTERVENING_HIERARCHY_ROOT_TRANSITION",
    ]
    assert boundary_axis[1]["hierarchy_root_exact"] == "16. Tài sản có khác"


def test_later_total_without_intervening_scope_boundary_fails_closed() -> None:
    page = {
        "sections": [
            {
                "title_exact": "Thuyết minh báo cáo tài chính",
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Phải thu",
                                    "Lãi phải thu từ hoạt động tín dụng",
                                ],
                                "label_exact": (
                                    "Lãi phải thu từ hoạt động tín dụng"
                                ),
                                "row_id": "r1",
                                "row_kind": "ITEM",
                                "values_exact": ["1", None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Phải thu",
                                    "Khoản phải thu khác",
                                ],
                                "label_exact": "Khoản phải thu khác",
                                "row_id": "r2",
                                "row_kind": "ITEM",
                                "values_exact": ["2", None],
                            },
                            {
                                "hierarchy_path_exact": ["Phải thu", "Cộng"],
                                "label_exact": "Cộng",
                                "row_id": "r3",
                                "row_kind": "TOTAL",
                                "values_exact": ["3", None],
                            },
                        ]
                    }
                ],
            }
        ]
    }
    trials = [
        {
            "candidates": [
                {
                    "closure_receipt": {
                        "table_receipts": [
                            {
                                "classification": {
                                    "context_resolution_kind": (
                                        "DECLARED_ROW_POPULATION_SCOPE"
                                    ),
                                    "context_roles": [],
                                    "family_presence_anchor_visible": True,
                                    "money_column_ordinals": [1, 2],
                                    "role_hits": [
                                        {
                                            "role": "CREDIT_INTEREST",
                                            "row_ordinal": 1,
                                        }
                                    ],
                                    "total_rows": [
                                        {
                                            "row_kind": "TOTAL",
                                            "row_ordinal": 3,
                                        }
                                    ],
                                    "typed_control_disposition": None,
                                },
                                "region": _region(),
                            }
                        ]
                    },
                    "mappings": [],
                }
            ],
            "document_ordinal": 1,
            "source_logical_name": "bank/2025/report.pdf",
            "source_sha256": SOURCE_SHA256,
        }
    ]

    axis = subject._candidate_table_total_disposition_rows(
        trials=trials,
        page_json_by_document={1: {PAGE: page}},
        detail_total_controls=[],
    )

    assert axis[0]["coverage"] == (
        "VIOLATION_UNCLASSIFIED_CANDIDATE_TABLE_TOTAL"
    )
    assert axis[0]["receipt_context_axis"][0][
        "following_scope_boundary_axis"
    ] == []


def test_nonclosing_visible_adjacent_detail_total_fails_closed() -> None:
    sweep, page = _detail_total_coverage_fixture(total_value="9")

    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep, page_json_by_document={1: {PAGE: page}}
        )


def test_structural_other_assets_parent_total_is_not_claimed_by_family26() -> None:
    aggregate = _mapping(982, role="INTEREST_FEE_RECEIVABLES")
    page = {
        "sections": [
            {
                "title_exact": "15. Tài sản Có khác",
                "tables": [
                    {
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Các khoản lãi, phí phải thu"
                                ],
                                "label_exact": "Các khoản lãi, phí phải thu",
                                "row_id": "r1",
                                "row_kind": "ITEM",
                                "values_exact": ["1", None],
                            },
                            {
                                "hierarchy_path_exact": ["Tài sản Có khác"],
                                "label_exact": "Tài sản Có khác",
                                "row_id": "r2",
                                "row_kind": "TOTAL",
                                "values_exact": ["9", "8"],
                            },
                        ]
                    }
                ],
            }
        ]
    }
    classification = {
        "context_resolution_kind": "DECLARED_ROW_POPULATION_SCOPE",
        "context_roles": [],
        "family_presence_anchor_visible": True,
        "money_column_ordinals": [1, 2],
        "owner_visible": True,
        "role_hits": [
            {"role": "INTEREST_FEE_RECEIVABLES", "row_ordinal": 1}
        ],
        "total_rows": [{"row_kind": "TOTAL", "row_ordinal": 2}],
        "typed_control_disposition": None,
    }
    cluster = {
        "declared_money_table_inventory": [
            {
                "classification": classification,
                "disposition": "SELECTED_FAMILY_COMPONENT",
                "page_json_version_id": PAGE,
                "physical_page": 1,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
        "document_ordinal": 1,
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    candidate = {
        "closure_receipt": {
            "table_receipts": [
                {
                    "classification": classification,
                    "region": _region(),
                }
            ]
        },
        "mappings": [aggregate],
    }
    sweep = {
        "family_id": subject.FAMILY_ID,
        "indexed_query_evidence": {
            "candidate_dispositions": [{"cluster": cluster}],
            "selected_page_axis": [
                {"page_json_version_id": PAGE, "physical_page": 1}
            ],
        },
        "trials": [
            {
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [aggregate],
                "source_logical_name": "bank/2025/report.pdf",
                "source_sha256": SOURCE_SHA256,
            }
        ],
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )

    total = receipt["candidate_table_total_row_axis"][0]
    assert total["coverage"] == (
        "OUTSIDE_FAMILY26_STRUCTURAL_PARENT_OTHER_ASSETS_TOTAL"
    )
    assert (total["report_norm_id"], total["role"]) == (
        966,
        "OTHER_ASSETS_STRUCTURAL_CONTEXT",
    )
    assert receipt["violation_count"] == 0


def test_authenticated_note_total_source_ref_is_on_coverage_axis() -> None:
    sweep, page = _detail_total_coverage_fixture()
    candidate = sweep["trials"][0]["candidates"][0]
    candidate["closure_receipt"]["primary_detail_note_total_corroboration"] = {
        "corroborated": True,
        "lane_receipts": [
            {
                "corroborated": True,
                "lane_ordinal": 1,
                "note_coefficient": 1,
                "primary_coefficient": 1,
            },
            {
                "corroborated": True,
                "lane_ordinal": 2,
                "note_coefficient": None,
                "primary_coefficient": None,
            },
        ],
        "note_source_refs": [
            {
                "hierarchy_path_exact": [
                    "15. Các khoản lãi, phí phải thu",
                    "Cộng",
                ],
                "label_exact": "Cộng",
                "locator": _region(),
                "money_column_ordinals": [1, 2],
                "row_id": "r2",
                "row_kind": "TOTAL",
                "row_ordinal": 2,
            }
        ],
        "receipt_id": "glicafv1:corroboration:" + "5" * 64,
    }

    receipt = subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
        sweep=sweep, page_json_by_document={1: {PAGE: page}}
    )

    total = next(
        item
        for item in receipt["source_row_axis"]
        if item.get("row_ordinal") == 2
    )
    assert total["coverage_evidence_kind"] == (
        "PRIMARY_DETAIL_NOTE_TOTAL_CORROBORATION_RECEIPT"
    )
    assert total["coverage_proof_id"].startswith("glicafv1:corroboration:")

    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "9"
    with pytest.raises(
        subject.GeminiJsonLoanInterestAccrualClassificationFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        subject.build_loan_interest_accrual_source_row_coverage_receipt_v1(
            sweep=sweep, page_json_by_document={1: {PAGE: page}}
        )
