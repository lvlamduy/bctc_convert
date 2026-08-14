from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/provision_movement_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("provision_movement_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
provision = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = provision
_SPEC.loader.exec_module(provision)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + 140, y + 22],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _panel(
    *,
    owner: str = "Biến động dự phòng rủi ro cho vay khách hàng",
    header: str = "Dự phòng chung",
    start_y: int = 0,
    include_fx: bool = True,
) -> list[tuple[str, int, int]]:
    surfaces = [(owner, 0, start_y), (header, 0, start_y + 32)]
    rows = [
        ("Số dư đầu kỳ", "100"),
        ("Trích lập dự phòng trong kỳ", "20"),
        ("Sử dụng dự phòng để xử lý các khoản nợ", "(10)"),
    ]
    if include_fx:
        rows.append(("Chênh lệch tỷ giá", "2"))
    rows.extend([("Điều chỉnh khác", "(2)"), ("Số dư cuối kỳ", "110")])
    for ordinal, (label, value) in enumerate(rows):
        y = start_y + 70 + ordinal * 42
        surfaces.extend([(label, 0, y), (value, 650, y)])
    return surfaces


def test_flat_optional_movement_and_accounting_graph_is_unique() -> None:
    result = provision.build_provision_movement_variant_graph_document_v1([_page(_panel())])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"] == {
        "accounting_corroborated_lane_count": 1,
        "complete_provision_region_count": 1,
        "continuation_region_count": 0,
        "movement_panel_count": 1,
        "near_region_count": 0,
        "numeric_authority_count": 0,
        "schema_mapping_count": 0,
    }
    graph = result["graphs"][0]
    assert graph["roles"] == ["OPENING", "PROVISION", "USE", "FX", "OTHER", "CLOSING"]
    assert graph["minimal_anchor"]["combination_size"] == 2
    assert graph["panels"][0]["accounting_checks"][0]["status"] == (
        "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
    )


def test_two_general_specific_panels_and_extra_lane_headers_share_one_region() -> None:
    first = _panel(header="Tại Việt Nam - Dự phòng chung", include_fx=False)
    second = _panel(
        owner="Dự phòng rủi ro cho vay khách hàng",
        header="Tại nước ngoài - Dự phòng cụ thể - Tổng cộng",
        start_y=360,
        include_fx=False,
    )
    # A repeated owner on the same page is a near owner, not a bank-specific route;
    # both complete movement panels still belong to one semantic family region.
    result = provision.build_provision_movement_variant_graph_document_v1([_page(first + second)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["movement_panel_count"] == 2
    assert result["metrics"]["complete_provision_region_count"] == 1


def test_adjacent_repeated_owner_continuation_completes_one_region() -> None:
    first = [
        ("Biến động dự phòng rủi ro cho vay khách hàng", 0, 0),
        ("Dự phòng chung", 0, 35),
        ("Số dư đầu kỳ", 0, 80),
        ("100", 650, 80),
        ("Trích lập dự phòng trong kỳ", 0, 125),
        ("20", 650, 125),
    ]
    second = [
        ("Biến động dự phòng rủi ro cho vay khách hàng (tiếp theo)", 0, 0),
        ("Sử dụng dự phòng để xử lý các khoản nợ", 0, 45),
        ("(10)", 650, 45),
        ("Số dư cuối kỳ", 0, 90),
        ("110", 650, 90),
    ]

    result = provision.build_provision_movement_variant_graph_document_v1(
        [_page(first), _page(second, page_sequence=2)]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["graphs"][0]["page_sequences"] == [1, 2]
    assert result["metrics"]["continuation_region_count"] == 1


def test_policy_expense_and_snapshot_regions_are_negative_controls() -> None:
    pages = [
        _page(
            [
                ("Chi phí dự phòng rủi ro cho vay khách hàng", 0, 0),
                ("Số dư đầu kỳ", 0, 45),
                ("100", 650, 45),
                ("Trích lập dự phòng trong kỳ", 0, 90),
                ("10", 650, 90),
                ("Số dư cuối kỳ", 0, 135),
                ("110", 650, 135),
            ]
        ),
        _page(
            [
                ("Dự phòng rủi ro cho vay khách hàng", 0, 0),
                ("Số dư đầu kỳ", 0, 45),
                ("100", 650, 45),
                ("Số dư cuối kỳ", 0, 90),
                ("100", 650, 90),
            ],
            page_sequence=2,
        ),
    ]

    result = provision.build_provision_movement_variant_graph_document_v1(pages)

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_provision_region_count"] == 0
    assert result["metrics"]["near_region_count"] == 1


def test_exact_replay_rejects_coordinated_semantic_role_tamper() -> None:
    pages = [_page(_panel())]
    result = provision.build_provision_movement_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["graphs"][0]["panels"][0]["rows"][1]["role"] = "OTHER"
    graph_material = copy.deepcopy(forged["graphs"][0])
    graph_material.pop("graph_id")
    forged["graphs"][0]["graph_id"] = "pmvgv1:graph:" + provision.canonical_json_sha256_v1(
        graph_material
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "pmvgv1:result:" + provision.canonical_json_sha256_v1(result_material)

    with pytest.raises(provision.ProvisionMovementVariantGraphV1Error, match="replay exactly"):
        provision.validate_provision_movement_variant_graph_replay_v1(forged, pages)


def test_typed_inputs_and_complete_page_order_fail_closed() -> None:
    page = _page(_panel())
    poisoned = copy.deepcopy(page)
    poisoned["primary_numeric_authority"] = 0
    with pytest.raises(provision.ProvisionMovementVariantGraphV1Error, match="exact bool"):
        provision.build_provision_movement_variant_graph_document_v1([poisoned])

    skipped = _page(_panel(), page_sequence=2)
    with pytest.raises(provision.ProvisionMovementVariantGraphV1Error, match="gap-free"):
        provision.build_provision_movement_variant_graph_document_v1([skipped])
