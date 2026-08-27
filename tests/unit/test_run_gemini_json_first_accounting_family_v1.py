from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_accounting_family_v1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)


def _compiled() -> dict:
    paths = (
        "config/families/tm-interbank-deposits-loans-topology-v4.json",
        "config/families/tm-interbank-deposits-loans-evaluation-v4.json",
        "config/families/tm-interbank-deposits-loans-schema-binding-v4.json",
    )
    topology, evaluation, schema = (
        json.loads((ROOT / path).read_text(encoding="utf-8")) for path in paths
    )
    return target.compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)


def _mapping(role: str, report_norm_id: int, values: tuple[int, int]) -> dict:
    return {
        "columns": [{"value_kind": "MONEY"}, {"value_kind": "MONEY"}],
        "report_norm_id": report_norm_id,
        "role": role,
        "values": [
            {"coefficient": value, "source_text": str(value), "state": "RAW_SIGNED_INTEGER"}
            for value in values
        ],
    }


def _candidate(candidate_id: str, roles: list[tuple[str, int]]) -> dict:
    return {
        "candidate_id": candidate_id,
        "mappings": [
            _mapping(
                role,
                report_norm_id,
                (170, 139) if role == "INTERBANK_DEPOSITS_AND_LOANS" else (1, 1),
            )
            for role, report_norm_id in roles
        ],
    }


def _traceable_candidate(candidate_id: str, table_id: str, roles: list[tuple[str, int]]) -> dict:
    candidate = _candidate(candidate_id, roles)
    candidate.update(
        {
            "closure_receipt": {"rule": "EXACT", "table_id": table_id},
            "family_id": "INTERBANK_DEPOSITS_AND_LOANS",
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "physical_page": 7,
            "reasons": [],
            "section_id": "s1",
            "status": target.READY,
            "table_id": table_id,
        }
    )
    return candidate


def test_exact_role_rich_detail_uniquely_supersedes_its_summary() -> None:
    summary = _candidate(
        "summary",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("INTERBANK_DEPOSIT_GROUP", 576),
            ("INTERBANK_LOAN_GROUP", 585),
            ("TOTAL_INTERBANK_PROVISION", 5718),
        ],
    )
    detail = _candidate(
        "detail",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("INTERBANK_DEPOSIT_GROUP", 576),
            ("DEMAND_DEPOSIT_GROUP", 577),
            ("DEMAND_DEPOSIT_VND", 578),
            ("TERM_DEPOSIT_GROUP", 580),
            ("TERM_DEPOSIT_VND", 581),
            ("INTERBANK_LOAN_GROUP", 585),
            ("INTERBANK_LOAN_VND", 586),
            ("INTERBANK_LOAN_PROVISION", 590),
        ],
    )
    assert target._selected_ready_candidate([summary, detail], compiled_specs=_compiled()) == detail


def test_candidate_selection_rejects_root_drift_and_equal_detail_ambiguity() -> None:
    roles = [
        ("INTERBANK_DEPOSITS_AND_LOANS", 575),
        ("INTERBANK_DEPOSIT_GROUP", 576),
        ("INTERBANK_LOAN_GROUP", 585),
    ]
    first = _candidate("first", roles)
    second = _candidate("second", roles)
    assert target._selected_ready_candidate([first, second], compiled_specs=_compiled()) is None
    second["mappings"][0]["values"][0]["coefficient"] += 1
    assert target._selected_ready_candidate([first, second], compiled_specs=_compiled()) is None


def test_explicit_parent_binding_uniquely_supersedes_shape_only_child_cluster() -> None:
    roles = [
        ("INTERBANK_DEPOSITS_AND_LOANS", 575),
        ("INTERBANK_DEPOSIT_GROUP", 576),
        ("INTERBANK_LOAN_GROUP", 585),
    ]
    explicit = _candidate("explicit", roles)
    explicit["parent_binding_kind"] = "EXPLICIT_SECTION_OR_TABLE_TITLE"
    implied = _candidate("implied", roles)
    implied["parent_binding_kind"] = "UNIQUE_REQUIRED_CHILD_CLUSTER"
    implied["mappings"][0]["values"][0]["coefficient"] += 1
    assert (
        target._selected_ready_candidate([implied, explicit], compiled_specs=_compiled())
        == explicit
    )

    peer = _candidate("peer", roles)
    peer["parent_binding_kind"] = "EXPLICIT_PARENT_ROW"
    assert target._selected_ready_candidate([explicit, peer], compiled_specs=_compiled()) is None


def test_decisive_hard_negative_candidate_is_removed_from_family_disposition() -> None:
    candidate = {
        "reasons": ["HARD_NEGATIVE_FAMILY_TITLE_PRESENT"],
        "status": target.UNRESOLVED,
    }
    assert target._candidate_is_decisive_hard_negative(candidate)

    candidate["reasons"] = ["FAMILY_PARENT_NOT_VISIBLE"]
    assert not target._candidate_is_decisive_hard_negative(candidate)

    candidate["reasons"] = ["HARD_NEGATIVE_FAMILY_TITLE_PRESENT"]
    candidate["status"] = target.READY
    assert not target._candidate_is_decisive_hard_negative(candidate)


def test_stacked_regions_are_derived_from_one_hit_frontier_with_punctuation_variants() -> None:
    parent = "Các công cụ tài chính phái sinh và các tài sản/khoản nợ tài chính khác"
    hit = {
        "hierarchy_path_exact": [],
        "label_exact": "I. Giao dịch kỳ hạn tiền tệ",
        "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
        "physical_page": 38,
        "row_id": "r2",
        "section_id": "s2",
        "section_title_exact": (
            "8. CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(KHOẢN NỢ) TÀI CHÍNH KHÁC"
        ),
        "source_logical_name": "VIB/report.pdf",
        "table_has_explicit_parent_row": 0,
        "table_id": "t1",
        "table_title_exact": None,
    }
    regions = target._stacked_candidate_regions_from_hits_v1(
        [hit],
        anchor_alias_groups=[[[parent], ["Giao dịch kỳ hạn tiền tệ"]]],
        parent_aliases=[target.normalize_vietnamese_anchor_v1(parent)],
    )
    assert regions == [
        {
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "physical_page": 38,
            "section_id": "s2",
            "source_logical_name": "VIB/report.pdf",
            "table_id": "t1",
        }
    ]


def test_stacked_regions_require_distinct_rows_for_child_child_anchor() -> None:
    hit = {
        "hierarchy_path_exact": [],
        "label_exact": "Giao dịch hoán đổi tiền tệ",
        "page_json_version_id": "gfpstorev1:json:" + "2" * 64,
        "physical_page": 7,
        "row_id": "r1",
        "section_id": "s1",
        "section_title_exact": "Công cụ tài chính phái sinh",
        "source_logical_name": "bank/report.pdf",
        "table_has_explicit_parent_row": 0,
        "table_id": "t1",
        "table_title_exact": None,
    }
    assert (
        target._stacked_candidate_regions_from_hits_v1(
            [hit],
            anchor_alias_groups=[[["Giao dịch hoán đổi tiền tệ"], ["Giao dịch hoán đổi tiền tệ"]]],
            parent_aliases=["cong cu tai chinh phai sinh"],
        )
        == []
    )


def test_row_level_parent_authority_is_opt_in_for_recursive_json_engine() -> None:
    hit = {
        "hierarchy_path_exact": ["Tiền gửi và cho vay các TCTD khác"],
        "label_exact": "Tiền gửi và cho vay các TCTD khác",
        "section_title_exact": "BẢNG CÂN ĐỐI KẾ TOÁN",
        "table_has_explicit_parent_row": 1,
        "table_title_exact": None,
    }
    aliases = _compiled()["topology"]["parent"]["aliases"]
    assert not target._hit_has_explicit_parent(
        hit,
        allow_row_parent=False,
        parent_aliases=aliases,
    )
    assert target._hit_has_explicit_parent(
        hit,
        allow_row_parent=True,
        parent_aliases=aliases,
    )


def test_disjoint_equivalent_table_presentations_are_composed_without_double_counting() -> None:
    issuer = _traceable_candidate(
        "issuer",
        "t1",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("DEMAND_DEPOSIT_VND", 578),
        ],
    )
    currency = _traceable_candidate(
        "currency",
        "t2",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("TERM_DEPOSIT_VND", 581),
        ],
    )
    selected = target._selected_ready_candidate([issuer, currency], compiled_specs=_compiled())
    assert selected is not None
    assert selected["component_table_ids"] == ["t1", "t2"]
    assert [mapping["role"] for mapping in selected["mappings"]] == [
        "INTERBANK_DEPOSITS_AND_LOANS",
        "DEMAND_DEPOSIT_VND",
        "TERM_DEPOSIT_VND",
    ]
    assert selected["closure_receipt"]["component_candidate_ids"] == [
        "issuer",
        "currency",
    ]

    overlap = _traceable_candidate(
        "overlap",
        "t3",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("DEMAND_DEPOSIT_VND", 578),
        ],
    )
    assert target._selected_ready_candidate([issuer, overlap], compiled_specs=_compiled()) is None
    currency["section_id"] = "s2"
    assert target._selected_ready_candidate([issuer, currency], compiled_specs=_compiled()) is None

    currency["page_json_version_id"] = "gfpstorev1:json:" + "2" * 64
    currency["physical_page"] = 8
    issuer["mappings"][0]["columns"] = [
        {"header_path_exact": ["2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    currency["mappings"][0]["columns"] = [
        {"header_path_exact": ["2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024"], "value_kind": "MONEY"},
    ]
    adjacent = target._selected_ready_candidate([currency, issuer], compiled_specs=_compiled())
    assert adjacent is not None
    assert adjacent["component_page_json_version_ids"] == [
        issuer["page_json_version_id"],
        currency["page_json_version_id"],
    ]
    assert adjacent["closure_receipt"]["rule"].startswith("ADJACENT_CONTINUATION_")

    currency["physical_page"] = 9
    assert target._selected_ready_candidate([issuer, currency], compiled_specs=_compiled()) is None


def test_net_adjusted_table_supersedes_adjacent_gross_view_and_keeps_both_axes() -> None:
    net = _traceable_candidate(
        "net",
        "t1",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("DEMAND_DEPOSIT_VND", 578),
        ],
    )
    gross = _traceable_candidate(
        "gross",
        "t1",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("TERM_DEPOSIT_VND", 581),
        ],
    )
    columns = [
        {"header_path_exact": ["2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    net["mappings"][0]["columns"] = columns
    gross["mappings"][0]["columns"] = [
        {"header_path_exact": ["2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024"], "value_kind": "MONEY"},
    ]
    for value, coefficient in zip(net["mappings"][0]["values"], (90, 80), strict=True):
        value["coefficient"] = coefficient
        value["source_text"] = str(coefficient)
    for value, coefficient in zip(gross["mappings"][0]["values"], (100, 90), strict=True):
        value["coefficient"] = coefficient
        value["source_text"] = str(coefficient)
    net["closure_receipt"] = {
        "equations": [
            {
                "component_roles": [],
                "result_coefficients": [-10, -10],
                "result_role": "TOTAL_INTERBANK_PROVISION",
            },
            {
                "component_roles": [
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                    "TOTAL_INTERBANK_PROVISION",
                ],
                "result_coefficients": [90, 80],
                "result_role": "INTERBANK_DEPOSITS_AND_LOANS",
            },
        ]
    }
    gross["closure_receipt"] = {
        "equations": [
            {
                "component_roles": [
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                ],
                "result_coefficients": [100, 90],
                "result_role": "INTERBANK_DEPOSITS_AND_LOANS",
            }
        ]
    }
    gross["physical_page"] = 8
    gross["page_json_version_id"] = "gfpstorev1:json:" + "2" * 64
    selected = target._selected_ready_candidate([net, gross], compiled_specs=_compiled())
    assert selected is not None
    assert selected["physical_page"] == 7
    assert selected["closure_receipt"]["adjustment_coefficients"] == [-10, -10]
    assert [mapping["role"] for mapping in selected["mappings"]] == [
        "INTERBANK_DEPOSITS_AND_LOANS",
        "DEMAND_DEPOSIT_VND",
        "TERM_DEPOSIT_VND",
    ]

    gross["mappings"][0]["values"][0]["coefficient"] += 1
    assert target._selected_ready_candidate([net, gross], compiled_specs=_compiled()) is None
