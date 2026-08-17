from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_annual_2025_capital_and_funds_rotated_ppocrv6_panel_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_capital_and_funds_rotated_ppocrv6_panel_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="PNG")
    return output.getvalue()


def _selection() -> tuple[list[dict[str, object]], dict[str, object]]:
    pages = []
    for ordinal in range(1, 4):
        payload = _png(40, 60, (ordinal * 20, 30, 40))
        pages.append(
            {
                "document_ordinal": ordinal + 5,
                "line_count": 90 + ordinal,
                "physical_page": 40 + ordinal,
                "render_payload": payload,
                "source_pdf_sha256": f"{ordinal:064x}",
                "source_render_ref": {
                    "path": f"source/render-{ordinal}.png",
                    "sha256": builder._CORE._sha256(payload),
                    "size_bytes": len(payload),
                },
                "source_semantic_line_axis_sha256": f"{ordinal + 10:064x}",
            }
        )
    return pages, {
        "crop_manifest": {"path": "source/crop.json", "sha256": "4" * 64, "size_bytes": 4},
        "rotated_rescue_crop_manifest": {
            "path": "source/rescue.json",
            "sha256": "5" * 64,
            "size_bytes": 5,
        },
        "semantic_index": {"path": "source/index.json", "sha256": "6" * 64, "size_bytes": 6},
        "structure_scan_id": builder.EXPECTED_SCAN_ID,
    }


def _write_reader_output(root: Path, manifest: dict[str, object]) -> None:
    for ordinal, page in enumerate(manifest["pages"], 1):
        output_root = root / builder.OUTPUT_ROOT / f"page-{ordinal:04d}/reader-output"
        output_root.mkdir()
        rotated_ref = page["rotated_page_ref"]
        result = {
            "rec_boxes": [[5, 5, 50, 20]],
            "rec_scores": [0.99],
            "rec_texts": ["15.152.519 11.582.717"],
            "return_word_box": True,
            "text_word": [["15.152.519", " ", "11.582.717"]],
            "text_word_boxes": [[[6, 5, 22, 20], [24, 5, 25, 20], [27, 5, 48, 20]]],
        }
        run = {
            "configuration": {"implicit_orientation_or_unwarp": False, "precision": "fp32"},
            "dataset_role": "CALIBRATION",
            "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
            "input": {
                "sha256": rotated_ref["sha256"],
                "size_bytes": rotated_ref["size_bytes"],
            },
            "runtime": {
                "models": [
                    {"repo_id": "PaddlePaddle/PP-OCRv6_medium_det"},
                    {"repo_id": "PaddlePaddle/PP-OCRv6_medium_rec"},
                ]
            },
            "state": "OCR_COMPLETE",
        }
        (output_root / "ocr_result.json").write_text(json.dumps(result), encoding="utf-8")
        (output_root / "run_manifest.json").write_text(json.dumps(run), encoding="utf-8")


def _build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUTPUT_ROOT", Path("output/capital-panel"))
    monkeypatch.setattr(builder, "MANIFEST_PATH", Path("output/capital-panel/panel_manifest.json"))
    monkeypatch.setattr(builder, "_capital_selection", lambda: copy.deepcopy(_selection()))
    core = builder._configured_core()
    monkeypatch.setattr(core, "_clean_git", lambda: {"commit": "a" * 40, "dirty": False})
    return builder.build_annual_2025_capital_and_funds_rotated_ppocrv6_panel_v1()


def test_full_page_rotation_becomes_the_canonical_geometry_space(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _build(tmp_path, monkeypatch)
    _write_reader_output(tmp_path, manifest)
    projection = builder.read_verified_annual_2025_capital_and_funds_rotated_ppocrv6_panel_v1()

    assert [page["document_ordinal"] for page in projection["pages"]] == [6, 7, 8]
    assert projection["metrics"] == {"ocr_line_count": 3, "page_count": 3}
    assert projection["authority"]["normalized_rotated_page_is_canonical_geometry_space"] is True
    assert (
        projection["authority"]["inverse_projection_to_source_pdf_required_for_table_reasoning"]
        is False
    )
    assert projection["pages"][0]["text_word"] == [["15.152.519", " ", "11.582.717"]]
    assert projection["pages"][0]["text_word_boxes"][0][0] == [6, 5, 22, 20]
    with Image.open(tmp_path / builder.OUTPUT_ROOT / "page-0001/rotated-page.png") as normalized:
        assert normalized.size == (60, 40)


def test_word_box_outside_normalized_page_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _build(tmp_path, monkeypatch)
    _write_reader_output(tmp_path, manifest)
    result_path = tmp_path / builder.OUTPUT_ROOT / "page-0001/reader-output/ocr_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["text_word_boxes"][0][2] = [27, 5, 61, 20]
    result_path.write_text(json.dumps(result), encoding="utf-8")

    with pytest.raises(
        builder.Annual2025CapitalAndFundsRotatedPPocrV6PanelError,
        match="result or runtime identity drifted",
    ):
        builder.read_verified_annual_2025_capital_and_funds_rotated_ppocrv6_panel_v1()


def test_bank_page_and_inverse_projection_are_not_routing_or_mapping_authority() -> None:
    assert builder.SELECTION_RULE == (
        "UNIQUE_COMPLETE_CAPITAL_AND_FUNDS_REGION_AND_GEOMETRY_ROTATED_SOURCE_AXIS_TRUE"
    )
    assert builder._AUTHORITY["bank_filename_or_page_number_used_as_selection_rule"] is False
    assert (
        builder._AUTHORITY["inverse_projection_to_source_pdf_required_for_table_reasoning"] is False
    )
