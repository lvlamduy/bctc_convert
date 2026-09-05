from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from bctc_ai.evaluation.loan_geography_scoped_table_adapter_v1 import (
    LoanGeographyScopedTableAdapterV1Error,
    loan_geography_presentation_disposition_v1,
)

ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    ROOT / "docs/experiments/staging/family-audit-19-bank/"
    "FAMILY_11_LOAN_GEOGRAPHIC_CLASSIFICATION.md"
)
_LEDGER_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|.*\|\s*(?:READY|NOT_OBSERVED)\s*→\s*"
    r"(?:\*\*)?(READY|UNRESOLVED|SOURCE_ONLY|NOT_OBSERVED)(?:\*\*)?\s*\|"
)


def _audit_rows() -> dict[int, tuple[str, str]]:
    rows: dict[int, tuple[str, str]] = {}
    for line in AUDIT.read_text(encoding="utf-8").splitlines():
        match = _LEDGER_ROW.match(line)
        if match is None:
            continue
        ordinal = int(match.group(1))
        assert ordinal not in rows
        rows[ordinal] = (match.group(2), line)
    return rows


def test_human_audit_ledger_partitions_all_204_documents_without_collapsing_source_only() -> None:
    rows = _audit_rows()

    assert sorted(rows) == list(range(1, 205))
    assert Counter(disposition for disposition, _line in rows.values()) == {
        "READY": 73,
        "UNRESOLVED": 3,
        "SOURCE_ONLY": 101,
        "NOT_OBSERVED": 27,
    }


def test_three_nvb_300m_source_conflicts_remain_unresolved_in_the_audit_oracle() -> None:
    rows = _audit_rows()

    assert {
        ordinal for ordinal, (disposition, _line) in rows.items() if disposition == "UNRESOLVED"
    } == {75, 78, 82}
    for ordinal in (75, 78, 82):
        disposition, source_line = rows[ordinal]
        assert disposition == "UNRESOLVED"
        assert "300.000" in source_line
        assert "SỐ LIỆU NGUỒN MÂU THUẪN NỘI BỘ" in source_line


def test_no_visible_mappable_item_is_left_behind_by_the_204_document_oracle() -> None:
    rows = _audit_rows()
    ready = {ordinal: line for ordinal, (status, line) in rows.items() if status == "READY"}
    source_only = {
        ordinal: line for ordinal, (status, line) in rows.items() if status == "SOURCE_ONLY"
    }

    assert len(ready) == 73
    assert all("RNID5752" in line and "RNID765" in line for line in ready.values())
    broad_ready = {
        ordinal for ordinal, line in ready.items() if "Header/metric: “Tổng dư nợ cho vay”;" in line
    }
    assert broad_ready == {22, 25, 26, 102}
    assert all("khớp chính xác" in ready[ordinal] for ordinal in broad_ready)

    assert len(source_only) == 101
    assert {
        ordinal
        for ordinal, line in source_only.items()
        if "NGOÀI PHẠM VI NGÔN NGỮ ĐƯỢC CHỌN" in line
    } == {151}
    assert all(
        any(marker in line for marker in ("Nhãn rộng", "Quần thể trộn", "sau dự phòng (net)"))
        for ordinal, line in source_only.items()
        if ordinal != 151
    )


def test_broad_structural_evidence_projects_to_source_only_not_true_absence() -> None:
    assert (
        loan_geography_presentation_disposition_v1("BROAD_POPULATION_BOUNDED_ABSENCE")
        == "SOURCE_ONLY"
    )
    assert loan_geography_presentation_disposition_v1("NOT_OBSERVED") == "NOT_OBSERVED"
    assert loan_geography_presentation_disposition_v1("UNRESOLVED") == "UNRESOLVED"
    # Structural matching alone deliberately does not confer numeric READY authority.
    assert (
        loan_geography_presentation_disposition_v1("EXACT_CUSTOMER_LOAN_GEOGRAPHY")
        == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    )
    with pytest.raises(
        LoanGeographyScopedTableAdapterV1Error,
        match="structural disposition is invalid",
    ):
        loan_geography_presentation_disposition_v1("READY")


def test_family_config_gates_broad_metric_with_declarative_external_control() -> None:
    evaluation = json.loads(
        (ROOT / "config/families/tm-loan-geographic-classification-evaluation-v1.json").read_text(
            encoding="utf-8"
        )
    )
    policy = evaluation["dual_axis_projection_policy"]

    assert policy["source_blank_mapping_policy"] == "PRESERVE_BLANK_OMIT_MAPPING"
    assert {
        "Cho vay khách hàng - gộp",
        "Tổng dư nợ cho vay các TCKT và cá nhân",
        "Cho vay và cho thuê tài chính khách hàng",
    } <= set(policy["metric_aliases"])
    # This broad surface is queryable only behind the authenticated external
    # population-control policy; the generic engine receives no family label.
    assert "Tổng dư nợ cho vay" in policy["metric_aliases"]
    external = policy["external_population_control"]
    assert external["control_report_norm_id"] == 716
    assert external["query_gate_metric_aliases"] == ["Tổng dư nợ cho vay"]
    assert set(external["query_gate_metric_aliases"]) <= set(
        external["controlled_metric_aliases"]
    )
