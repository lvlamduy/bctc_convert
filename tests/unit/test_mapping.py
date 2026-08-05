from __future__ import annotations

from bctc_ai.mapping.alignment import ObservedRow, align_ordered_rows
from bctc_ai.mapping.lctt import (
    CashFlowMethod,
    CashFlowRules,
    assign_cash_flow_schema_branches,
    classify_cash_flow_method,
    load_cash_flow_rules,
)
from bctc_ai.mapping.scope import (
    classify_mapping_scope,
    classify_mapping_scopes,
    load_scope_policy,
)
from bctc_ai.schema.registry import SchemaItem


def _item(identifier: int, name: str, order: int) -> SchemaItem:
    return SchemaItem(
        schema_id=identifier,
        canonical_name=name,
        normalized_name=name.casefold(),
        statement_type="CDKT",
        display_order=order,
    )


def test_duplicate_label_is_resolved_by_neighbor_block_and_order(project_root):
    schema = [
        _item(1, "Tiền mặt", 0),
        _item(2, "Khác", 1),
        _item(3, "Tổng tài sản ngắn hạn", 2),
        _item(4, "Tài sản cố định", 3),
        _item(5, "Khác", 4),
        _item(6, "Tổng tài sản dài hạn", 5),
    ]
    rows = [
        ObservedRow("r1", "Tài sản cố định", 0, "CDKT"),
        ObservedRow("r2", "Khác", 1, "CDKT"),
        ObservedRow("r3", "Tổng tài sản dài hạn", 2, "CDKT"),
    ]
    policy = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")
    result = align_ordered_rows(
        rows,
        schema,
        scope_policy=policy,
        minimum_match_score=0.30,
    )
    selected = {match.row_id: match.schema_id for match in result.matches}
    assert selected == {"r1": 4, "r2": 5, "r3": 6}


def test_off_balance_items_are_not_candidates_for_cdkt(project_root):
    policy = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")
    for label in (
        "Bảo lãnh vay vốn",
        "Cam kết giao dịch hối đoái",
        "Tài sản và chứng từ khác",
    ):
        decision = classify_mapping_scope("CDKT", label, policy)
        assert not decision.allowed
        assert decision.detected_section == "OFF_BALANCE_SHEET"
    assert classify_mapping_scope("TM", "Bảo lãnh vay vốn", policy).allowed


def test_off_balance_heading_excludes_entire_following_cdkt_section(project_root):
    policy = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")
    decisions = classify_mapping_scopes(
        [
            ("CDKT", "CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG"),
            ("CDKT", "Cam kết khác"),
            ("CDKT", "Hạn mức tín dụng chưa sử dụng"),
            ("KQKD", "Thu nhập lãi"),
        ],
        policy,
    )

    assert [decision.allowed for decision in decisions] == [False, False, False, True]
    assert decisions[1].inherited_from_section
    assert decisions[2].detected_section == "OFF_BALANCE_SHEET"


def test_page_heading_can_seed_off_balance_scope_for_table_rows(project_root):
    policy = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")
    decisions = classify_mapping_scopes(
        [("CDKT", "Cam kết khác"), ("CDKT", "Nợ khó đòi đã xử lý")],
        policy,
        initial_section_label="CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG",
    )

    assert all(not decision.allowed for decision in decisions)
    assert all(decision.inherited_from_section for decision in decisions)


def test_lctt_method_uses_ordered_anchor_pairs(project_root):
    rules = load_cash_flow_rules(project_root / "config/mapping/lctt.yaml")
    indirect = classify_cash_flow_method(
        ["Lợi nhuận trước thuế", "Điều chỉnh cho các khoản", "Khấu hao TSCĐ"],
        rules,
    )
    assert indirect.method is CashFlowMethod.INDIRECT
    assert not indirect.semantic_high_confidence_allowed
    direct = classify_cash_flow_method(
        [
            "Thu nhập lãi và các khoản thu nhập tương tự nhận được",
            "Chi phí lãi và các chi phí tương tự đã trả",
        ],
        rules,
    )
    assert direct.method is CashFlowMethod.DIRECT
    reversed_rows = classify_cash_flow_method(
        ["Điều chỉnh cho các khoản", "Lợi nhuận trước thuế"],
        rules,
    )
    assert reversed_rows.method is CashFlowMethod.UNKNOWN


def test_mapping_and_cash_flow_classification_fail_closed_without_policy():
    row = ObservedRow("r1", "Tiền mặt", 0, "CDKT")
    schema = [_item(1, "Tiền mặt", 0)]
    result = align_ordered_rows([row], schema, scope_policy=None)
    assert result.matches == []
    assert result.unmatched_row_ids == ["r1"]
    assert not classify_mapping_scope("CDKT", "Tiền mặt", None).allowed
    assert (
        classify_cash_flow_method(["Lợi nhuận trước thuế"], None).method is CashFlowMethod.UNKNOWN
    )


def test_cash_flow_schema_blocks_follow_workbook_order_not_numeric_ranges(tmp_path):
    rules = CashFlowRules(
        version=1,
        authority="TEST",
        semantic_authority_status="TEST",
        maximum_anchor_distance=2,
        label_sequences={
            CashFlowMethod.INDIRECT: (("profit", "adjustment"),),
            CashFlowMethod.DIRECT: (("received", "paid"),),
        },
        schema_order_blocks={
            CashFlowMethod.INDIRECT: ((500, 100),),
            CashFlowMethod.DIRECT: ((900, 200),),
        },
        source_path=tmp_path / "rules.yaml",
    )
    assignments = assign_cash_flow_schema_branches([500, 700, 100, 900, 300, 200], rules)
    assert assignments == {
        500: CashFlowMethod.INDIRECT,
        700: CashFlowMethod.INDIRECT,
        100: CashFlowMethod.INDIRECT,
        900: CashFlowMethod.DIRECT,
        300: CashFlowMethod.DIRECT,
        200: CashFlowMethod.DIRECT,
    }
