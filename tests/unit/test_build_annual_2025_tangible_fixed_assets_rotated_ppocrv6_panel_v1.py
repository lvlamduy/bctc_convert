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
    _ROOT
    / "scripts/experiments/build_annual_2025_tangible_fixed_assets_rotated_ppocrv6_panel_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_tangible_fixed_assets_rotated_ppocrv6_panel_v1", _PATH
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
        payload = _png(40 + ordinal, 60 + ordinal, (ordinal * 20, 30, 40))
        pages.append(
            {
                "document_ordinal": ordinal + 5,
                "line_count": 10 + ordinal,
                "physical_page": 40 + ordinal,
                "render_payload": payload,
                "source_pdf_sha256": f"{ordinal:064x}",
                "source_render_ref": {
                    "path": f"source/render-{ordinal}.png",
                    "sha256": builder._sha256(payload),
                    "size_bytes": len(payload),
                },
                "source_semantic_line_axis_sha256": f"{ordinal + 10:064x}",
            }
        )
    return pages, {
        "crop_manifest": {
            "path": "source/crop.json",
            "sha256": "4" * 64,
            "size_bytes": 4,
        },
        "semantic_index": {
            "path": "source/index.json",
            "sha256": "5" * 64,
            "size_bytes": 5,
        },
        "structure_scan_id": builder.EXPECTED_SCAN_ID,
    }


def _write_reader_output(root: Path, manifest: dict[str, object]) -> None:
    for ordinal, page in enumerate(manifest["pages"], 1):
        page_root = root / builder.OUTPUT_ROOT / f"page-{ordinal:04d}"
        output_root = page_root / "reader-output"
        output_root.mkdir()
        rotated_ref = page["rotated_page_ref"]
        result = {
            "rec_boxes": [[10, 5, 30, 20], [31, 5, 55, 25]],
            "rec_scores": [0.99, 0.98],
            "rec_texts": ["17.253.570", "(938.137)"],
        }
        run = {
            "configuration": {
                "implicit_orientation_or_unwarp": False,
                "precision": "fp32",
            },
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
        (output_root / "ocr_result.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8"
        )
        (output_root / "run_manifest.json").write_text(
            json.dumps(run, ensure_ascii=False), encoding="utf-8"
        )


def test_build_and_verify_uses_only_graph_selected_rotated_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selection = _selection()
    monkeypatch.setattr(builder, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(builder, "OUTPUT_ROOT", Path("output/panel"))
    monkeypatch.setattr(builder, "MANIFEST_PATH", Path("output/panel/panel_manifest.json"))
    monkeypatch.setattr(builder, "_clean_git", lambda: {"commit": "a" * 40, "dirty": False})
    monkeypatch.setattr(builder, "_live_selection", lambda: copy.deepcopy(selection))

    manifest = builder.build_annual_2025_tangible_rotated_ppocrv6_panel_v1()
    _write_reader_output(tmp_path, manifest)
    projection = builder.read_verified_annual_2025_tangible_rotated_ppocrv6_panel_v1()

    assert projection["metrics"] == {"ocr_line_count": 6, "page_count": 3}
    assert [page["document_ordinal"] for page in projection["pages"]] == [6, 7, 8]
    assert all(page["rec_texts"] == ["17.253.570", "(938.137)"] for page in projection["pages"])
    assert projection["authority"]["bank_filename_or_page_number_used_as_selection_rule"] is False

    with pytest.raises(builder.Annual2025TangibleRotatedPPocrV6PanelError, match="overwrite"):
        builder.build_annual_2025_tangible_rotated_ppocrv6_panel_v1()


def test_manifest_rejects_bool_as_int_even_after_identity_rehash() -> None:
    pages, input_refs = _selection()
    material = {
        "authority": copy.deepcopy(builder._AUTHORITY),
        "format_version": builder.FORMAT_VERSION,
        "git_binding": {"commit": "a" * 40, "dirty": False},
        "input_refs": input_refs,
        "metrics": {"page_count": 3},
        "pages": [
            {key: value for key, value in page.items() if key in builder._PAGE_FIELDS}
            | {
                "rotated_page_ref": {
                    "path": f"output/page-{ordinal:04d}.png",
                    "sha256": f"{ordinal + 20:064x}",
                    "size_bytes": ordinal,
                }
            }
            for ordinal, page in enumerate(pages, 1)
        ],
        "selection_rule": "UNIQUE_COMPLETE_TANGIBLE_ASSET_REGION_AND_ROTATED_SOURCE_AXIS_TRUE",
        "state": "ROTATED_PPOCRV6_PAGE_PANEL_READY",
    }
    forged = {
        **material,
        "panel_id": "a2025tfarpv1:panel:" + builder.canonical_json_sha256_v1(material),
    }
    forged["authority"]["mapping_or_schema_authority"] = 0
    identity_material = copy.deepcopy(forged)
    identity_material.pop("panel_id")
    forged["panel_id"] = "a2025tfarpv1:panel:" + builder.canonical_json_sha256_v1(identity_material)

    with pytest.raises(
        builder.Annual2025TangibleRotatedPPocrV6PanelError,
        match="manifest shape",
    ):
        builder._validate_manifest(forged)
