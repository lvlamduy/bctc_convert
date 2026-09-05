from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
    evaluate_gemini_json_hierarchical_family_table_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION_ID = "gfpstorev1:json:" + "b" * 64


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_flat_family_specs_v1(
        _json("tm-interbank-deposits-loans-topology-v4.json"),
        _json("tm-interbank-deposits-loans-evaluation-v4.json"),
        _json("tm-interbank-deposits-loans-schema-binding-v4.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
    hierarchy: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            ([] if label is None else [label]) if hierarchy is None else hierarchy
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [None, current, comparative],
    }


def _page(rows: list[dict[str, Any]], *, title: str) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["Khoản mục"], "value_kind": "TEXT"},
                            {
                                "header_path_exact": ["31/12/2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31/12/2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": title,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate(page: dict[str, Any]) -> dict[str, Any]:
    return evaluate_gemini_json_hierarchical_family_table_v1(
        page_json=page,
        page_json_version_id=VERSION_ID,
        physical_page=1,
        section_id="s1",
        table_id="t1",
        compiled_specs=_compiled(),
    )


def test_literal_json_newline_escape_normalizes_as_visible_line_break() -> None:
    assert _normalized(r"tổ chức tín\ndụng khác") == _normalized("tổ chức tín\ndụng khác")


def test_statement_level_credit_provision_maps_to_family_provision_not_loan_provision() -> None:
    owner = "Tiền gửi tại các TCTD khác và cho vay các TCTD khác"
    page = _page(
        [
            _row(owner, "114", "84", kind="GROUP", hierarchy=[owner]),
            _row(
                "Tiền gửi tại các TCTD khác",
                "108",
                "75",
                hierarchy=[owner, "Tiền gửi tại các TCTD khác"],
            ),
            _row(
                "Cho vay các TCTD khác",
                "7",
                "10",
                hierarchy=[owner, "Cho vay các TCTD khác"],
            ),
            _row(
                "Dự phòng rủi ro cho vay các TCTD khác",
                "(1)",
                "(1)",
                hierarchy=[owner, "Dự phòng rủi ro cho vay các TCTD khác"],
            ),
        ],
        title="THUYẾT MINH BÁO CÁO TÀI CHÍNH",
    )

    candidate = _evaluate(page)

    assert candidate["status"] == READY
    role_to_id = {item["role"]: item["report_norm_id"] for item in candidate["mappings"]}
    assert role_to_id["TOTAL_INTERBANK_PROVISION"] == 5718
    assert "INTERBANK_LOAN_PROVISION" not in role_to_id


def test_provision_explicitly_nested_under_loan_keeps_loan_schema_role() -> None:
    owner = "Tiền gửi tại các TCTD khác và cho vay các TCTD khác"
    loan = "Cho vay các TCTD khác"
    page = _page(
        [
            _row("Tiền gửi tại các TCTD khác", "108", "75"),
            _row(loan, "7", "10", kind="GROUP", hierarchy=[loan]),
            _row("Bằng VND", "8", "11", hierarchy=[loan, "Bằng VND"]),
            _row(
                "Dự phòng rủi ro cho vay các TCTD khác",
                "(1)",
                "(1)",
                hierarchy=[loan, "Dự phòng rủi ro cho vay các TCTD khác"],
            ),
            _row(None, "115", "85", kind="TOTAL"),
        ],
        title=owner,
    )

    candidate = _evaluate(page)

    assert candidate["status"] == READY
    role_to_id = {item["role"]: item["report_norm_id"] for item in candidate["mappings"]}
    assert role_to_id["INTERBANK_LOAN_PROVISION"] == 590
    assert "TOTAL_INTERBANK_PROVISION" not in role_to_id
