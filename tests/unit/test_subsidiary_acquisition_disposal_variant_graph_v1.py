from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/subsidiary_acquisition_disposal_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "subsidiary_acquisition_disposal_variant_graph_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], sequence: int = 1) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        numeric = re.fullmatch(r"\(?[0-9][0-9.,]*\)?", text) is not None
        lines.append(
            {
                "bbox": [750 if numeric else 60, index * 25, 920, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": sequence, "primary_numeric_authority": True}


def _complete() -> list[str]:
    return [
        "Mua mới và thanh lý các công ty con",
        "Kỳ này",
        "Triệu đồng",
        "Tổng giá trị mua hoặc thanh lý",
        "100.000",
        "Phần giá trị mua được thanh toán bằng tiền và các khoản tương đương tiền",
        "80.000",
        "Số tiền và các khoản tương đương tiền thực có trong công ty con được mua",
        "20.000",
    ]


def test_three_required_rows_form_one_complete_graph() -> None:
    result = matcher.build_subsidiary_acquisition_disposal_variant_graph_document_v1(
        [_page(_complete())]
    )
    assert result["status"] == "COMPLETE"
    assert result["uniqueness"] == {
        "complete_region_count": 1,
        "status": "UNIQUE_FULL_MATCH",
    }


@pytest.mark.parametrize(
    "texts",
    [
        ["Hợp nhất kinh doanh", "Giao dịch mua công ty con được hạch toán theo giá mua"],
        ["Tiền chi đầu tư, góp vốn vào các đơn vị khác", "Chi đầu tư mua công ty con"],
        ["HDS trở thành công ty con kể từ ngày mua"],
    ],
)
def test_policy_cash_flow_and_acquisition_narratives_are_near_controls(
    texts: list[str],
) -> None:
    result = matcher.build_subsidiary_acquisition_disposal_variant_graph_document_v1([_page(texts)])
    assert result["metrics"]["complete_region_count"] == 0
    assert result["status"] == "NO_COMPLETE_REGION"


def test_missing_cash_held_row_fails_closed() -> None:
    texts = _complete()[:-2]
    result = matcher.build_subsidiary_acquisition_disposal_variant_graph_document_v1([_page(texts)])
    assert result["metrics"]["complete_region_count"] == 0


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_complete())]
    result = matcher.build_subsidiary_acquisition_disposal_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "sadvv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(
        matcher.SubsidiaryAcquisitionDisposalVariantGraphV1Error,
        match="drifted|replay exactly",
    ):
        matcher.validate_subsidiary_acquisition_disposal_variant_graph_replay_v1(forged, pages)
