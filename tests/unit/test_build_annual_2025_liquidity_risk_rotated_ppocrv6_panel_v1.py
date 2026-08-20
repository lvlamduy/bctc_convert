from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/build_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1.py"
SPEC = importlib.util.spec_from_file_location("annual_2025_liquidity_panel_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def _png(width: int, height: int) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), (30, 40, 50)).save(output, format="PNG")
    return output.getvalue()


def _selection() -> tuple[list[dict[str, object]], dict[str, object]]:
    pages = []
    payload = _png(40, 60)
    for ordinal in range(5):
        pages.append(
            {
                "document_ordinal": 6 + min(ordinal // 2, 2),
                "line_count": 100 + ordinal,
                "physical_page": 70 + ordinal,
                "render_payload": payload,
                "source_pdf_sha256": f"{ordinal + 1:064x}",
                "source_render_ref": {
                    "path": f"source/render-{ordinal}.png",
                    "sha256": builder._SUPPORT._CORE._sha256(payload),
                    "size_bytes": len(payload),
                },
                "source_semantic_line_axis_sha256": f"{ordinal + 11:064x}",
            }
        )
    return pages, {
        "crop_manifest": {"path": "source/crop.json", "sha256": "3" * 64, "size_bytes": 3},
        "rotated_rescue_crop_manifest": {
            "path": "source/rescue.json",
            "sha256": "4" * 64,
            "size_bytes": 4,
        },
        "semantic_index": {"path": "source/index.json", "sha256": "5" * 64, "size_bytes": 5},
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
            "rec_texts": [str(ordinal)],
            "return_word_box": True,
            "text_word": [[str(ordinal)]],
            "text_word_boxes": [[[6, 5, 49, 20]]],
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


def test_panel_keeps_exact_graph_and_geometry_selected_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUTPUT_ROOT", Path("output/liquidity-panel"))
    monkeypatch.setattr(
        builder, "MANIFEST_PATH", Path("output/liquidity-panel/panel_manifest.json")
    )
    monkeypatch.setattr(builder, "_liquidity_selection", lambda: copy.deepcopy(_selection()))
    core = builder._configured_core()
    monkeypatch.setattr(core, "_clean_git", lambda: {"commit": "a" * 40, "dirty": False})

    manifest = builder.build_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1()
    _write_reader_output(tmp_path, manifest)
    projection = builder.read_verified_annual_2025_liquidity_risk_rotated_ppocrv6_panel_v1()

    assert projection["metrics"] == {"ocr_line_count": 5, "page_count": 5}
    assert [page["document_ordinal"] for page in projection["pages"]] == [6, 6, 7, 7, 8]
    assert projection["authority"]["ppocrv6_is_independent_numeric_challenger_only"] is True
    for ordinal in range(1, 6):
        with Image.open(
            tmp_path / builder.OUTPUT_ROOT / f"page-{ordinal:04d}/rotated-page.png"
        ) as image:
            assert image.size == (60, 40)


def test_selection_is_graph_geometry_intersection_not_bank_or_page_rule() -> None:
    assert builder.SELECTION_RULE == (
        "UNIQUE_COMPLETE_LIQUIDITY_RISK_REGION_AND_GEOMETRY_ROTATED_SOURCE_AXIS_TRUE"
    )
    assert builder._AUTHORITY["bank_filename_or_page_number_used_as_selection_rule"] is False
    assert builder._AUTHORITY["rotated_page_selected_from_generic_graph_and_geometry"] is True
