from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_stacked_period_lane_axis_v1 as lane_axis_v1
from bctc_ai.evaluation.accounting_stacked_period_lane_axis_v1 import (
    AccountingStackedPeriodLaneAxisV1Error,
    build_accounting_stacked_period_lane_axis_v1,
    validate_accounting_stacked_period_lane_axis_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
TOPOLOGY = json.loads(
    (ROOT / "config/families/tm-derivative-financial-instruments-topology-v1.json").read_text(
        encoding="utf-8"
    )
)
LAYOUT = json.loads(
    (ROOT / "config/families/tm-derivative-financial-instruments-layout-v1.json").read_text(
        encoding="utf-8"
    )
)


def _line(text: str, bbox: list[int], ordinal: int) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"crop/{ordinal}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 1,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": text, "reader_score": 0.99},
        "sample_id": f"sample-{ordinal}",
        "vietocr_text": text,
    }


def _pages() -> list[dict[str, object]]:
    raw = [
        ("CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN TÀI CHÍNH KHÁC", [40, 30, 900, 60]),
        ("Tại ngày 30/06/2026", [700, 80, 1050, 110]),
        ("Tổng giá trị của hợp đồng", [770, 120, 960, 150]),
        ("Tài sản", [1010, 120, 1110, 150]),
        ("Công nợ", [1210, 120, 1320, 150]),
        ("Tổng cộng", [1410, 120, 1530, 150]),
        ("Triệu VND", [800, 160, 930, 190]),
        ("Triệu VND", [1010, 160, 1140, 190]),
        ("Triệu VND", [1210, 160, 1340, 190]),
        ("Triệu VND", [1410, 160, 1540, 190]),
        ("Giao dịch kỳ hạn tiền tệ", [50, 220, 500, 250]),
        ("1.000", [820, 220, 920, 250]),
        ("(20)", [1230, 220, 1310, 250]),
        ("(20)", [1430, 220, 1510, 250]),
        ("Giao dịch hoán đổi tiền tệ", [50, 270, 530, 300]),
        ("2.000", [820, 270, 920, 300]),
        ("30", [1030, 270, 1100, 300]),
        ("30", [1430, 270, 1500, 300]),
        ("Giao dịch hoán đổi lãi suất", [50, 320, 530, 350]),
        ("3.000", [820, 320, 920, 350]),
        ("40", [1030, 320, 1100, 350]),
        ("(5)", [1230, 320, 1310, 350]),
        ("35", [1430, 320, 1500, 350]),
        ("Tại ngày 31/12/2025", [700, 400, 1050, 430]),
        ("Tổng giá trị của hợp đồng", [770, 440, 960, 470]),
        ("Tài sản", [1010, 440, 1110, 470]),
        ("Công nợ", [1210, 440, 1320, 470]),
        ("Tổng cộng", [1410, 440, 1530, 470]),
        ("Giao dịch kỳ hạn tiền tệ", [50, 520, 500, 550]),
        ("900", [820, 520, 920, 550]),
        ("10", [1030, 520, 1100, 550]),
        ("10", [1430, 520, 1500, 550]),
        ("Giao dịch hoán đổi tiền tệ", [50, 570, 530, 600]),
        ("1.800", [820, 570, 920, 600]),
        ("(15)", [1230, 570, 1310, 600]),
        ("(15)", [1430, 570, 1510, 600]),
        ("Giao dịch hoán đổi lãi suất", [50, 620, 530, 650]),
        ("2.700", [820, 620, 920, 650]),
        ("20", [1030, 620, 1100, 650]),
        ("(7)", [1230, 620, 1310, 650]),
        ("13", [1430, 620, 1500, 650]),
        ("Cho vay khách hàng", [50, 720, 500, 750]),
    ]
    return [
        {
            "lines": [_line(text, bbox, ordinal) for ordinal, (text, bbox) in enumerate(raw)],
            "page_sequence": 1,
            "page_width": 1600,
        }
    ]


def _horizontal_pages() -> list[dict[str, object]]:
    raw = [
        ("CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN TÀI CHÍNH KHÁC", [40, 30, 900, 60]),
        ("31/12/2025", [540, 80, 760, 110]),
        ("31/12/2024", [1040, 80, 1260, 110]),
        ("Giá trị", [500, 120, 650, 145]),
        ("hợp đồng", [500, 146, 650, 171]),
        ("Giá trị", [735, 120, 865, 145]),
        ("ghi sổ", [735, 146, 865, 171]),
        ("Giá trị", [1000, 120, 1150, 145]),
        ("hợp đồng", [1000, 146, 1150, 171]),
        ("Giá trị", [1235, 120, 1365, 145]),
        ("ghi sổ", [1235, 146, 1365, 171]),
        ("Hợp đồng hoán đổi tiền tệ", [50, 220, 500, 250]),
        ("204.012.086", [535, 220, 665, 250]),
        ("384.075", [755, 220, 845, 250]),
        ("340.865.305", [1035, 220, 1165, 250]),
        ("1.328.364", [1250, 220, 1350, 250]),
        ("Hợp đồng kỳ hạn tiền tệ", [50, 280, 500, 310]),
        ("(199.035)", [535, 280, 665, 310]),
        ("(9.157)", [755, 280, 845, 310]),
        ("(16.245.514)", [1035, 280, 1165, 310]),
        ("(13.930)", [1250, 280, 1350, 310]),
        ("Cho vay khách hàng", [50, 400, 500, 430]),
    ]
    return [
        {
            "lines": [_line(text, bbox, ordinal) for ordinal, (text, bbox) in enumerate(raw)],
            "page_sequence": 1,
            "page_width": 1600,
        }
    ]


def _topology_pages(pages: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "lines": [
                {
                    "bbox": line["bbox"],
                    "source_line_index": line["line_ordinal"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in pages[0]["lines"]
            ],
            "page_sequence": 1,
        }
    ]


def _build() -> dict[str, object]:
    pages = _pages()
    scan = topology_v1.build_accounting_family_topology_scan_v1(_topology_pages(pages), TOPOLOGY)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    return build_accounting_stacked_period_lane_axis_v1(pages, TOPOLOGY, scan["regions"][0], LAYOUT)


def test_stacked_period_blocks_keep_sparse_rows_and_meaningful_lane_roles() -> None:
    axis = _build()
    assert axis["status"] == "STACKED_PERIOD_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert [item["role"] for item in axis["lane_axis"]] == [
        "CONTRACT_VALUE",
        "ASSET_CARRYING_VALUE",
        "LIABILITY_CARRYING_VALUE",
        "NET_VALUE",
    ]
    assert [block["period_role"] for block in axis["blocks"]] == [
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    ]
    assert [len(block["rows"]) for block in axis["blocks"]] == [3, 3]
    current_forward = axis["blocks"][0]["rows"][0]
    assert [item["lane_role"] for item in current_forward["values"]] == [
        "CONTRACT_VALUE",
        "LIABILITY_CARRYING_VALUE",
        "NET_VALUE",
    ]
    assert current_forward["missing_lane_roles"] == ["ASSET_CARRYING_VALUE"]


def test_exact_replay_rejects_period_lane_or_sparse_cell_mutation() -> None:
    pages = _pages()
    axis = _build()
    assert (
        validate_accounting_stacked_period_lane_axis_replay_v1(axis, pages, TOPOLOGY, LAYOUT)
        == axis
    )
    for mutation in ("period", "lane", "cell"):
        forged = copy.deepcopy(axis)
        if mutation == "period":
            forged["blocks"][0]["period_role"] = "COMPARATIVE_PERIOD"
        elif mutation == "lane":
            forged["lane_axis"][0]["role"] = "NET_VALUE"
        else:
            forged["blocks"][0]["rows"][0]["missing_lane_roles"] = []
        material = copy.deepcopy(forged)
        material.pop("axis_id")
        from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

        forged["axis_id"] = "asplav1:axis:" + canonical_json_sha256_v1(material)
        with pytest.raises(AccountingStackedPeriodLaneAxisV1Error):
            validate_accounting_stacked_period_lane_axis_replay_v1(forged, pages, TOPOLOGY, LAYOUT)


def test_header_alias_loss_fails_closed_without_changing_topology() -> None:
    pages = _pages()
    scan = topology_v1.build_accounting_family_topology_scan_v1(_topology_pages(pages), TOPOLOGY)
    layout = copy.deepcopy(LAYOUT)
    asset = next(item for item in layout["lane_roles"] if item["role"] == "ASSET_CARRYING_VALUE")
    asset["aliases"] = ["Một header không tồn tại"]
    axis = build_accounting_stacked_period_lane_axis_v1(pages, TOPOLOGY, scan["regions"][0], layout)
    assert axis["status"] == "UNRESOLVED_STACKED_PERIOD_OR_LANE_AXIS"
    assert axis["unresolved_reasons"] == ["VISIBLE_HEADER_TO_BODY_LANE_SEQUENCE_NOT_UNIQUE"]


def test_long_header_alias_allows_one_character_ocr_rescue_only() -> None:
    rescued = lane_axis_v1._header_match(
        [
            {
                "bbox": [1000, 100, 1400, 130],
                "page_sequence": 1,
                "source_line_index": 5,
                "vietocr_text": "Tổng giá trị ghi số kế loán",
            }
        ],
        ["tong gia tri ghi so ke toan"],
        3,
    )
    assert rescued is not None
    assert rescued["match_kind"] == "BOUNDED_EDIT_RESCUED_HEADER_ALIAS"
    assert rescued["edit_distance"] == 1

    assert (
        lane_axis_v1._header_match(
            [
                {
                    "bbox": [1000, 100, 1400, 130],
                    "page_sequence": 1,
                    "source_line_index": 5,
                    "vietocr_text": "Một cột hoàn toàn khác",
                }
            ],
            ["tong gia tri ghi so ke toan"],
            3,
        )
        is None
    )


def test_noncollinear_tall_ocr_artifacts_cannot_compose_a_short_header_alias() -> None:
    assert (
        lane_axis_v1._header_match(
            [
                {
                    "bbox": [100, 100, 200, 130],
                    "page_sequence": 1,
                    "source_line_index": 1,
                    "vietocr_text": "Header bình thường",
                },
                {
                    "bbox": [1200, 140, 1400, 230],
                    "page_sequence": 1,
                    "source_line_index": 2,
                    "vietocr_text": "tại",
                },
                {
                    "bbox": [1500, 240, 1600, 330],
                    "page_sequence": 1,
                    "source_line_index": 3,
                    "vietocr_text": "sản",
                },
            ],
            ["tai san"],
            3,
        )
        is None
    )


def test_horizontal_period_groups_reuse_one_role_axis_without_transposing_pixels() -> None:
    pages = _horizontal_pages()
    scan = topology_v1.build_accounting_family_topology_scan_v1(_topology_pages(pages), TOPOLOGY)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    axis = build_accounting_stacked_period_lane_axis_v1(pages, TOPOLOGY, scan["regions"][0], LAYOUT)
    assert axis["status"] == "STACKED_PERIOD_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert axis["orientation"] == "HORIZONTAL_PERIOD_GROUPS"
    assert [block["period_role"] for block in axis["blocks"]] == [
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    ]
    assert [item["role"] for item in axis["lane_axis"]] == [
        "CONTRACT_VALUE",
        "SIGNED_CARRYING_VALUE",
        "CONTRACT_VALUE",
        "SIGNED_CARRYING_VALUE",
    ]
    assert [item["column_ordinal"] for item in axis["lane_axis"]] == [0, 1, 2, 3]
    assert [len(block["rows"]) for block in axis["blocks"]] == [2, 2]
    assert [value["sample_id"] for value in axis["blocks"][0]["rows"][0]["values"]] == [
        "sample-12",
        "sample-13",
    ]
    assert [value["sample_id"] for value in axis["blocks"][1]["rows"][0]["values"]] == [
        "sample-14",
        "sample-15",
    ]


def test_horizontal_period_groups_can_expose_only_one_signed_carrying_lane() -> None:
    source = _horizontal_pages()[0]
    removed = {3, 4, 7, 8, 12, 14, 17, 19}
    retained = [line for ordinal, line in enumerate(source["lines"]) if ordinal not in removed]
    pages = [
        {
            "lines": [
                _line(line["vietocr_text"], line["bbox"], ordinal)
                for ordinal, line in enumerate(retained)
            ],
            "page_sequence": 1,
            "page_width": 1600,
        }
    ]
    scan = topology_v1.build_accounting_family_topology_scan_v1(_topology_pages(pages), TOPOLOGY)
    axis = build_accounting_stacked_period_lane_axis_v1(pages, TOPOLOGY, scan["regions"][0], LAYOUT)

    assert axis["status"] == "STACKED_PERIOD_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert axis["orientation"] == "HORIZONTAL_PERIOD_GROUPS"
    assert [item["role"] for item in axis["lane_axis"]] == [
        "SIGNED_CARRYING_VALUE",
        "SIGNED_CARRYING_VALUE",
    ]
    assert [len(block["rows"]) for block in axis["blocks"]] == [2, 2]
