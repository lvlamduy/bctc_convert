from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_combined_securities_net_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_combined_securities_net_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _axis() -> dict[str, object]:
    documents = []
    for ordinal, code in enumerate(scanner.EXPECTED_DOCUMENT_ORDER, 1):
        texts = ["Không có family này"]
        if code == "MBB":
            texts = [
                "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư",
                "Từ 01/01/2026 đến 30/06/2026",
                "Triệu đồng",
                "Lãi thuần từ chứng khoán kinh doanh, chứng",
                "khoán đầu tư",
                "253.111",
                "1.710.973",
            ]
        documents.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "pages": [
                    {
                        "lines": [
                            {
                                "bbox": (
                                    [600 + (i - 5) * 120, 80, 690 + (i - 5) * 120, 95]
                                    if code == "MBB" and i in {5, 6}
                                    else [10, i * 20, 500, i * 20 + 15]
                                ),
                                "semantic_text": text,
                                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                                "source_line_index": i,
                                "source_text": None,
                                "vietocr_text": text,
                            }
                            for i, text in enumerate(texts)
                        ],
                        "page_sequence": 1,
                        "primary_numeric_authority": True,
                    }
                ],
                "source_pdf": {"sha256": f"{ordinal:064x}"},
            }
        )
    return {
        "documents": documents,
        "projection_id": "axis:test",
        "semantic_axis_sha256": "1" * 64,
    }


def test_scan_retains_one_unique_document_and_seven_absences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_combined_securities_net_full_document_scan_v1({})
    assert result["metrics"] == {
        "complete_region_count": 1,
        "document_count": 8,
        "document_unique_structural_match_count": 1,
        "mapping_verified_count": 0,
        "near_region_count": 1,
        "unresolved_document_count": 7,
        "wrapped_complete_region_count": 1,
    }


def test_scan_replay_rejects_coordinated_tamper(monkeypatch: pytest.MonkeyPatch) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_combined_securities_net_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][1]["document_provenance"] = "ACB"
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "csnfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(
        scanner.CombinedSecuritiesNetFullDocumentScanV1Error, match="trial identity"
    ):
        scanner.validate_combined_securities_net_full_document_scan_replay_v1(forged, {})
