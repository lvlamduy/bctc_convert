from __future__ import annotations

import json

from bctc_ai.core.text import parse_financial_number
from bctc_ai.evaluation.reader_outputs import compare_reader_rows, parse_paddle_vl_page
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.validation.reader_agreement import ReaderRow


def _row(identifier, label, values):
    return ReaderRow(
        source_row_ids=(identifier,),
        label=label,
        note_reference=None,
        cells=tuple(parse_financial_number(value) for value in values),
    )


def test_paddle_table_parser_preserves_merged_numeric_cell_as_invalid(tmp_path):
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps(
            {
                "input_path": "scan.png",
                "parsing_res_list": [
                    {"block_label": "text", "block_content": "BÁO CÁO LƯU CHUYỂN TIỀN TỆ"},
                    {
                        "block_label": "table",
                        "block_bbox": [1, 2, 30, 40],
                        "block_content": (
                            "<table><tr><td></td><td>TM</td><td>2024</td><td>2023</td></tr>"
                            "<tr><td>Tăng vốn</td><td></td><td>198.242 (5.140.484)</td>"
                            "<td>52.664</td></tr></table>"
                        ),
                    },
                ],
            }
        )
    )

    page = parse_paddle_vl_page(path)

    assert page.tables[0].header == ("", "TM", "2024", "2023")
    assert page.tables[0].rows[0].cells[0].observation.value == "INVALID"
    assert "LƯU CHUYỂN" in page.context_text


def test_numeric_disagreement_escalates_without_changing_order(project_root):
    reference = (_row("r1", "Thu nhập lãi", ("100", "90")),)
    candidate = (_row("c1", "Thu nhập lãi", ("999", "90")),)
    policy = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")

    result = compare_reader_rows(
        reference,
        candidate,
        statement_type="KQKD",
        scope_policy=policy,
    )

    assert result["counts"]["alignment_actions"] == {"MATCH": 1}
    assert result["counts"]["exact_reference_financial_cells"] == 1
    assert result["alignment"][0]["escalation"] == "TARGETED_NUMERIC_REREAD_DISAGREEMENT"
    assert result["alignment"][0]["confidence_effect"] == "NO_PROMOTION"


def test_page_context_excludes_every_off_balance_candidate_row(project_root):
    rows = (
        _row("c1", "Bảo lãnh vay vốn", ("1", "2")),
        _row("c2", "Cam kết khác", ("3", "4")),
    )
    policy = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")

    result = compare_reader_rows(
        rows,
        rows,
        statement_type="CDKT",
        scope_policy=policy,
        candidate_context_text="CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG",
    )

    assert result["counts"]["scope_allowed_candidate_rows"] == 0
    assert result["counts"]["scope_excluded_candidate_rows"] == 2
