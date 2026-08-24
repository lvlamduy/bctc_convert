from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as sweep_v1
from bctc_ai.evaluation.accounting_family_coextensive_parent_total_v1 import (
    project_accounting_family_coextensive_parent_total_region_v1,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-topology-v4.json"
_V3_SPEC_PATH = _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-topology-v3.json"
_EVALUATION_PATH = _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
_V3_EVALUATION_PATH = (
    _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-evaluation-v3.json"
)
_V3_SCHEMA_BINDING_PATH = (
    _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-schema-binding-v3.json"
)
_SCHEMA_BINDING_PATH = (
    _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-schema-binding-v4.json"
)


def _spec() -> dict:
    return json.loads(_SPEC_PATH.read_text(encoding="utf-8"))


def _line(index: int, text: str, *, left: int = 100, top: int | None = None) -> dict:
    resolved_top = 100 + index * 32 if top is None else top
    width = 150 if left >= 800 else 620
    return {
        "bbox": [left, resolved_top, left + width, resolved_top + 24],
        "source_line_index": index,
        "source_text": None,
        "vietocr_text": text,
    }


def _page(lines: list[dict]) -> list[dict]:
    return [{"lines": lines, "page_sequence": 1}]


def test_v4_is_add_only_and_historical_v3_remains_byte_exact() -> None:
    v3_payload = _V3_SPEC_PATH.read_bytes()
    assert len(v3_payload) == 10_320
    assert hashlib.sha256(v3_payload).hexdigest() == (
        "816573106c32e7fa133cc2d371d3b5ff89a10ce307ef148655e04fb00c4614e5"
    )
    v3_evaluation_payload = _V3_EVALUATION_PATH.read_bytes()
    assert len(v3_evaluation_payload) == 2_280
    assert hashlib.sha256(v3_evaluation_payload).hexdigest() == (
        "0db7cfe8efe522822abf0ab8b716182300d0314c75f26af3197357a966aa9772"
    )
    v3_schema_payload = _V3_SCHEMA_BINDING_PATH.read_bytes()
    assert len(v3_schema_payload) == 1_386
    assert hashlib.sha256(v3_schema_payload).hexdigest() == (
        "e6e229e247d8dcb87870ce3a830992df60d82eb23ee748282969ae5bde216354"
    )
    family = _spec()
    compiled = topology_v1._spec(family)
    evaluation = json.loads(_EVALUATION_PATH.read_text(encoding="utf-8"))
    assert compiled["family_id"] == "INTERBANK_DEPOSITS_AND_LOANS"
    assert (
        sweep_v1._evaluation_spec(
            evaluation,
            compiled,
            raw_family_spec=family,
        )["format_version"]
        == sweep_v1.EVALUATION_SPEC_FORMAT_V4
    )


def test_v4_schema_exact_roles_partition_ambiguous_and_context_bound_sources() -> None:
    family = _spec()
    evaluation = json.loads(_EVALUATION_PATH.read_text(encoding="utf-8"))
    binding = json.loads(_SCHEMA_BINDING_PATH.read_text(encoding="utf-8"))
    roles = {child["role"]: child for child in family["children"]}
    source_only = set(
        evaluation["hierarchical_closure_spec"]["source_role_policy"]["source_only_veto_roles"]
    )

    assert roles["INTERBANK_DEPOSIT_OTHER"]["matchers"][0]["within_role"] == (
        "INTERBANK_DEPOSIT_GROUP"
    )
    assert roles["INTERBANK_LOAN_OTHER"]["matchers"][0]["within_role"] == ("INTERBANK_LOAN_GROUP")
    assert {item["role"]: item["report_norm_id"] for item in binding["role_bindings"]}[
        "INTERBANK_DEPOSIT_OTHER"
    ] == 584
    assert {item["role"]: item["report_norm_id"] for item in binding["role_bindings"]}[
        "INTERBANK_LOAN_OTHER"
    ] == 591

    for role, report_norm_id in (
        ("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND", 587),
        ("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY", 589),
    ):
        assert all(
            matcher["within_role"] == "INTERBANK_LOAN_GROUP" for matcher in roles[role]["matchers"]
        )
        assert {item["role"]: item["report_norm_id"] for item in binding["role_bindings"]}[
            role
        ] == report_norm_id
        assert role not in source_only
    assert roles["INTERBANK_LOAN_VND"]["role_kind"] == "ADDITIVE_CHILD"
    assert roles["INTERBANK_LOAN_FOREIGN_CURRENCY"]["role_kind"] == "ADDITIVE_CHILD"

    bindings = {item["role"] for item in binding["role_bindings"]}
    for target_role, ambiguous_role, owner_role in (
        (
            "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
            "EXPLICIT_INTERBANK_DEPOSIT_TOTAL_AMBIGUOUS",
            "INTERBANK_DEPOSIT_GROUP",
        ),
        (
            "EXPLICIT_INTERBANK_LOAN_TOTAL",
            "EXPLICIT_INTERBANK_LOAN_TOTAL_AMBIGUOUS",
            "INTERBANK_LOAN_GROUP",
        ),
    ):
        assert roles[target_role]["role_kind"] == "TOTAL"
        assert all(
            matcher["within_role"] == owner_role for matcher in roles[target_role]["matchers"]
        )
        assert roles[ambiguous_role]["role_kind"] == "NONADDITIVE_CHILD"
        assert all(matcher["within_role"] is None for matcher in roles[ambiguous_role]["matchers"])
        assert target_role not in source_only
        assert ambiguous_role in source_only
        assert {target_role, ambiguous_role} <= set(binding["ignored_roles"])
        assert {target_role, ambiguous_role}.isdisjoint(bindings)

    assert "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS" in source_only
    assert "INTERBANK_PROVISION_AMBIGUOUS" in source_only
    assert {
        "DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
        "TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
    } <= source_only
    assert "Dự phòng rủi ro" not in roles["TOTAL_INTERBANK_PROVISION"]["matchers"][0]["aliases"]
    assert "Dự phòng rủi ro" in roles["INTERBANK_PROVISION_AMBIGUOUS"]["matchers"][0]["aliases"]
    assert source_only <= set(binding["ignored_roles"])
    assert "Tiền gửi và vay từ NHNN và các TCTD khác" in family["hard_negative_aliases"]
    assert (
        "Các công cụ tài chính phái sinh và các tài sản tài chính khác"
        in family["structural_reset_aliases"]
    )


def test_money_table_stops_before_interest_percentage_and_quality_subtables() -> None:
    labels = [
        "TIỀN GỬI VÀ CẤP TÍN DỤNG CHO CÁC TỔ CHỨC TÍN DỤNG KHÁC",
        "Tiền gửi tại các TCTD khác",
        "Tiền gửi không kỳ hạn",
        "Bằng VND",
        "Bằng ngoại tệ",
        "Tiền gửi có kỳ hạn",
        "Bằng VND",
        "Bằng ngoại tệ",
        "Cấp tín dụng cho các TCTD khác",
        "Bằng VND",
        "Mức lãi suất tiền gửi có kỳ hạn và cấp tín dụng cho các TCTD khác vào thời điểm cuối năm như",
        "Tiền gửi có kỳ hạn bằng VND",
        "4,25 - 10,00",
        "Phân tích chất lượng dư nợ tiền gửi có kỳ hạn và cấp tín dụng cho các TCTD khác",
        "39",
    ]
    pages = _page([_line(index, text) for index, text in enumerate(labels)])

    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, _spec())

    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = scan["regions"][0]
    assert region["cluster_end_document_line_ordinal_exclusive"] == 10
    assert max(item["end_document_line_ordinal"] for item in region["child_matches"]) < 10
    assert all(item["surface"] != "Tiền gửi có kỳ hạn bằng VND" for item in region["child_matches"])
    assert all(item["surface"] != "39" for item in region["child_matches"])


def test_wrapped_provision_and_exact_owner_total_stay_inside_next_family_fence() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", top=100),
        _line(1, "392.701.135", left=900, top=100),
        _line(2, "280.052.369", left=1150, top=100),
        _line(3, "Tiền gửi tại các TCTD khác", top=150),
        _line(4, "381.762.553", left=900, top=150),
        _line(5, "268.366.137", left=1150, top=150),
        _line(6, "Cho vay các TCTD khác", top=200),
        _line(7, "10.938.582", left=900, top=200),
        _line(8, "11.686.232", left=1150, top=200),
        _line(9, "Dự phòng rủi ro tiền gửi tại và", top=250),
        _line(10, "(1.500.000)", left=900, top=250),
        _line(11, "(1.200.000)", left=1150, top=250),
        _line(12, "cho vay các TCTD khác", top=282),
        _line(13, "Chứng khoán kinh doanh", top=340),
        _line(14, "9", left=800, top=920),
    ]
    spec = _spec()
    pages = _page(lines)
    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, spec)

    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = scan["regions"][0]
    provision = next(
        item for item in region["child_matches"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    assert provision["source_line_indices"] == [9, 12]
    assert provision["end_document_line_ordinal"] == 12
    assert region["cluster_end_document_line_ordinal_exclusive"] == 13

    projected = project_accounting_family_coextensive_parent_total_region_v1(spec, scan, region)
    owner_total = next(
        item for item in projected["child_matches"] if item["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    parent = projected["parent_match"]
    assert (
        owner_total["document_line_ordinal"],
        owner_total["end_document_line_ordinal"],
        owner_total["source_line_index"],
        owner_total["end_source_line_index"],
    ) == (
        parent["document_line_ordinal"],
        parent["end_document_line_ordinal"],
        parent["source_line_index"],
        parent["end_source_line_index"],
    )
    assert all(item["surface"] != "9" for item in projected["child_matches"])


def test_wrapped_derivative_heading_is_an_exact_multiline_reset_not_family_other() -> None:
    labels = [
        "Tiền gửi và cho vay các TCTD khác",
        "Tiền gửi tại các TCTD khác",
        "Cho vay các TCTD khác",
        "Bằng VND",
        "Các công cụ tài chính phái sinh và các tài sản tài chính",
        "khác",
        "Giá trị hợp lý",
    ]
    pages = _page([_line(index, text, top=100 + index * 28) for index, text in enumerate(labels)])

    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, _spec())

    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = scan["regions"][0]
    assert region["cluster_end_document_line_ordinal_exclusive"] == 4
    assert "INTERBANK_DEPOSIT_OTHER" not in region["observed_roles"]
    assert "INTERBANK_LOAN_OTHER" not in region["observed_roles"]


def test_bid_liability_gold_and_foreign_currency_table_is_not_a_family3_region() -> None:
    labels = [
        "8. TIỀN GỬI VÀ VAY CÁC TCTD KHÁC",
        "Tiền gửi không kỳ hạn",
        "Bằng VND",
        "Bằng vàng và ngoại tệ",
        "Tiền gửi có kỳ hạn",
        "Bằng VND",
        "Bằng vàng và ngoại tệ",
        "Vay các TCTD khác",
        "Bằng VND",
        "Bằng vàng và ngoại tệ",
    ]
    pages = _page([_line(index, text) for index, text in enumerate(labels)])

    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, _spec())

    assert scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert scan["regions"] == []


def test_repeated_currency_aliases_bind_to_nearest_structural_parent() -> None:
    labels = [
        "Tiền gửi và cho vay các TCTD khác",
        "Tiền gửi không kỳ hạn",
        "Bằng VND",
        "Tiền gửi có kỳ hạn",
        "Bằng VND",
        "Cho vay các TCTD khác",
        "Bằng VND",
        "Chứng khoán kinh doanh",
    ]
    pages = _page([_line(index, text) for index, text in enumerate(labels)])

    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, _spec())

    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    occurrences = topology_v1.enumerate_accounting_family_role_occurrences_v1(
        pages, _spec(), scan["regions"][0]
    )
    matches = {
        item["role"]: item for item in occurrences if item.get("matched_within_role") is not None
    }
    assert (
        matches["DEMAND_DEPOSIT_VND"]["document_line_ordinal"],
        matches["DEMAND_DEPOSIT_VND"]["matched_within_role"],
    ) == (2, "DEMAND_DEPOSIT_GROUP")
    assert (
        matches["TERM_DEPOSIT_VND"]["document_line_ordinal"],
        matches["TERM_DEPOSIT_VND"]["matched_within_role"],
    ) == (4, "TERM_DEPOSIT_GROUP")
    assert (
        matches["INTERBANK_LOAN_VND"]["document_line_ordinal"],
        matches["INTERBANK_LOAN_VND"]["matched_within_role"],
    ) == (6, "INTERBANK_LOAN_GROUP")


def test_numeric_statement_and_policy_prose_remain_for_evidence_adjudication() -> None:
    statement = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng (TCTD) khác"),
        _line(1, "Tiền gửi tại các tổ chức tín dụng khác"),
        _line(2, "120.000.000", left=900),
        _line(3, "Cho vay các tổ chức tín dụng khác"),
        _line(4, "30.000.000", left=900),
    ]
    policy = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng (TCTD) khác"),
        _line(1, "Tiền gửi tại các tổ chức tín dụng khác"),
        _line(2, "Các khoản tiền gửi được ghi nhận theo chính sách kế toán"),
        _line(3, "Cho vay các tổ chức tín dụng khác"),
        _line(4, "Các khoản cho vay được phân loại theo quy định hiện hành"),
    ]

    scan = topology_v1.build_accounting_family_topology_scan_v1(
        [
            {"lines": statement, "page_sequence": 1},
            {"lines": policy, "page_sequence": 2},
        ],
        _spec(),
    )

    assert scan["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    assert [region["page_sequence"] for region in scan["regions"]] == [1, 2]
    assert all(
        {"INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"} <= set(region["observed_roles"])
        for region in scan["regions"]
    )


def test_ctg_wrapped_owner_is_exact_and_customer_loan_starts_the_next_family() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các tổ chức tín dụng", top=100),
        _line(1, '(TCTD") khác', top=124),
        _line(2, "422.318.628", left=900, top=124),
        _line(3, "374.863.906", left=1150, top=124),
        _line(4, "Tiền gửi tại các tổ chức tín dụng khác", top=170),
        _line(5, "419.162.106", left=900, top=170),
        _line(6, "371.252.257", left=1150, top=170),
        _line(7, "Cho vay các tổ chức tín dụng khác", top=210),
        _line(8, "3.156.522", left=900, top=210),
        _line(9, "3.611.649", left=1150, top=210),
        _line(10, "Cho vay khách hàng", top=250),
        _line(11, "1.850.880.450", left=900, top=250),
        _line(12, "1.672.377.122", left=1150, top=250),
    ]
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(_page(lines), spec)

    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = scan["regions"][0]
    assert region["parent_match"]["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert (
        region["parent_match"]["source_line_index"],
        region["parent_match"]["end_source_line_index"],
    ) == (0, 1)
    assert region["cluster_end_document_line_ordinal_exclusive"] == 10
    projected = project_accounting_family_coextensive_parent_total_region_v1(spec, scan, region)
    total = next(
        item for item in projected["child_matches"] if item["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    assert (total["source_line_index"], total["end_source_line_index"]) == (0, 1)
    assert all(item["source_line_index"] < 10 for item in projected["child_matches"])
