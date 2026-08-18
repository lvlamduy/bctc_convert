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
_PATH = _ROOT / "scripts/experiments/build_annual_2025_currency_risk_rotated_ppocrv6_panel_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_currency_risk_rotated_ppocrv6_panel_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _png(width: int, height: int) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), (30, 40, 50)).save(output, format="PNG")
    return output.getvalue()


def _selection() -> tuple[list[dict[str, object]], dict[str, object]]:
    payload = _png(40, 60)
    return [
        {
            "document_ordinal": 7,
            "line_count": 114,
            "physical_page": 65,
            "render_payload": payload,
            "source_pdf_sha256": "1" * 64,
            "source_render_ref": {
                "path": "source/render.png",
                "sha256": builder._CORE._sha256(payload),
                "size_bytes": len(payload),
            },
            "source_semantic_line_axis_sha256": "2" * 64,
        }
    ], {
        "crop_manifest": {"path": "source/crop.json", "sha256": "3" * 64, "size_bytes": 3},
        "rotated_rescue_crop_manifest": {
            "path": "source/rescue.json",
            "sha256": "4" * 64,
            "size_bytes": 4,
        },
        "semantic_index": {"path": "source/index.json", "sha256": "5" * 64, "size_bytes": 5},
        "structure_scan_id": builder.EXPECTED_SCAN_ID,
    }


def _write_reader_output(root: Path, manifest: dict[str, object]) -> Path:
    page = manifest["pages"][0]
    output_root = root / builder.OUTPUT_ROOT / "page-0001/reader-output"
    output_root.mkdir()
    rotated_ref = page["rotated_page_ref"]
    result = {
        "rec_boxes": [[5, 5, 50, 20]],
        "rec_scores": [0.99],
        "rec_texts": ["5.204.845 172.944.588 70.756.684 248.906.117"],
        "return_word_box": True,
        "text_word": [["5.204.845", "172.944.588", "70.756.684", "248.906.117"]],
        "text_word_boxes": [[[6, 5, 14, 20], [15, 5, 25, 20], [26, 5, 36, 20], [37, 5, 49, 20]]],
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
    result_path = output_root / "ocr_result.json"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    (output_root / "run_manifest.json").write_text(json.dumps(run), encoding="utf-8")
    return result_path


def _build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUTPUT_ROOT", Path("output/currency-panel"))
    monkeypatch.setattr(
        builder,
        "MANIFEST_PATH",
        Path("output/currency-panel/panel_manifest.json"),
    )
    monkeypatch.setattr(builder, "_currency_risk_selection", lambda: copy.deepcopy(_selection()))
    core = builder._configured_core()
    monkeypatch.setattr(core, "_clean_git", lambda: {"commit": "a" * 40, "dirty": False})
    return builder.build_annual_2025_currency_risk_rotated_ppocrv6_panel_v1()


def test_upright_page_is_the_canonical_table_geometry_space(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _build(tmp_path, monkeypatch)
    _write_reader_output(tmp_path, manifest)
    projection = builder.read_verified_annual_2025_currency_risk_rotated_ppocrv6_panel_v1()

    assert projection["metrics"] == {"ocr_line_count": 1, "page_count": 1}
    assert projection["pages"][0]["document_ordinal"] == 7
    assert projection["pages"][0]["text_word"][0][0] == "5.204.845"
    assert projection["authority"]["normalized_rotated_page_is_canonical_geometry_space"] is True
    assert (
        projection["authority"]["inverse_projection_to_source_pdf_required_for_table_reasoning"]
        is False
    )
    with Image.open(tmp_path / builder.OUTPUT_ROOT / "page-0001/rotated-page.png") as image:
        assert image.size == (60, 40)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("rec_boxes", [[5, 5, 61, 20]]),
        ("text_word_boxes", [[[6, 5, 14, 20], [15, 5, 25, 20], [26, 5, 36, 20], [37, 5, 61, 20]]]),
    ],
)
def test_boxes_outside_upright_page_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: list[object],
) -> None:
    manifest = _build(tmp_path, monkeypatch)
    result_path = _write_reader_output(tmp_path, manifest)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result[field] = replacement
    result_path.write_text(json.dumps(result), encoding="utf-8")

    with pytest.raises(
        builder.Annual2025CurrencyRiskRotatedPPocrV6PanelError,
        match="result or runtime identity drifted",
    ):
        builder.read_verified_annual_2025_currency_risk_rotated_ppocrv6_panel_v1()


def test_bank_page_and_inverse_projection_are_not_selection_authority() -> None:
    assert builder.SELECTION_RULE == (
        "UNIQUE_COMPLETE_CURRENCY_RISK_REGION_AND_GEOMETRY_ROTATED_SOURCE_AXIS_TRUE"
    )
    assert builder._AUTHORITY["bank_filename_or_page_number_used_as_selection_rule"] is False
    assert (
        builder._AUTHORITY["inverse_projection_to_source_pdf_required_for_table_reasoning"] is False
    )
