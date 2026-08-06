from __future__ import annotations

import json
from pathlib import Path

import cv2
import fitz
import numpy as np
import pytest
import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.preprocessing.targeted_run import (
    TargetedRereadRunError,
    build_targeted_reread_inputs,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fixture(tmp_path: Path, policy_source: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "project"
    source = root / "data" / "source.pdf"
    source.parent.mkdir(parents=True)
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((20, 25), "Năm 2025                 Năm 2024", fontsize=8)
    page.insert_text((20, 50), "Tiền mặt              1.000       900", fontsize=8)
    document.save(source)
    document.close()

    render = root / "output" / "baseline" / "page-0001.png"
    render.parent.mkdir(parents=True)
    image = np.full((200, 400, 3), 255, dtype=np.uint8)
    cv2.putText(image, "2025     2024", (220, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))
    cv2.putText(image, "Cash 1000 900", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))
    assert cv2.imwrite(str(render), image)

    result = root / "output" / "role-c" / "ocr_result.json"
    render_relative = render.relative_to(root).as_posix()
    boxes = [
        [20, 80, 180, 100],
        [230, 80, 280, 100],
        [320, 80, 370, 100],
        [230, 15, 280, 35],
        [320, 15, 370, 35],
    ]
    _write_json(
        result,
        {
            "input_path": render.as_posix(),
            "return_word_box": True,
            "rec_texts": ["Cash", "1.000", "900", "2025", "2024"],
            "rec_scores": [0.99] * 5,
            "rec_boxes": boxes,
            "rec_polys": [[[box[0], box[1]], [box[2], box[3]]] for box in boxes],
            "text_word_boxes": [[] for _ in boxes],
        },
    )
    source_identity = {
        "path": source.relative_to(root).as_posix(),
        "sha256": sha256_file(source),
        "size_bytes": source.stat().st_size,
    }
    render_identity = {
        "path": render_relative,
        "sha256": sha256_file(render),
    }
    result_identity = {
        "path": result.relative_to(root).as_posix(),
        "sha256": sha256_file(result),
    }
    seal = root / "output" / "role-c" / "seal.json"
    _write_json(
        seal,
        {
            "state": "GEOMETRY_OCR_COMPLETE",
            "source_sha256": source_identity["sha256"],
            "pages": [
                {
                    "page": 1,
                    "ocr_result": result_identity,
                    "render": render_identity,
                }
            ],
        },
    )
    page_record = {
        "page": 1,
        "statement_type": "CDKT",
        "mapping_eligible": True,
        "role_b": {"tables": [{"status": "PARSED"}]},
        "role_c": {
            "result": result_identity,
            "line_height": 20,
            "table_bbox": [20, 15, 380, 150],
            "axes": [{"header_line_index": 3}, {"header_line_index": 4}],
            "rows": [
                {
                    "geometry": {
                        "y_anchor": 90,
                        "index_line_indices": [],
                        "label_line_indices": [0],
                        "note_line_indices": [],
                        "value_line_indices": [[1], [2]],
                    }
                }
            ],
        },
        "comparison": {
            "alignment": [
                {
                    "escalation": "TARGETED_NUMERIC_DISAGREEMENT_REREAD",
                    "role_b_indices": [0],
                    "role_c_indices": [0],
                }
            ]
        },
    }
    upstream = root / "docs" / "e0015.json"
    _write_json(
        upstream,
        {
            "experiment_id": "E-0015",
            "dataset_role": "CALIBRATION",
            "status": ("PASS_STRUCTURAL_COMPARISON_WITH_RETAINED_DISAGREEMENTS_NO_ACCURACY_CLAIM"),
            "documents": [
                {
                    "key": "TEST_BANK",
                    "source": source_identity,
                    "reader_seals": {
                        "role_c": {
                            "path": seal.relative_to(root).as_posix(),
                            "sha256": sha256_file(seal),
                        }
                    },
                    "pages": [page_record],
                }
            ],
        },
    )
    policy = root / "config" / "targeted-reread-v1.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes(policy_source.read_bytes())
    config = root / "config" / "e0016.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "experiment_id": "E-0016",
                "dataset_role": "CALIBRATION",
                "design": "TEST_TARGETED_REREAD",
                "upstream": {
                    "structural_fusion_artifact": {
                        "path": upstream.relative_to(root).as_posix(),
                        "sha256": sha256_file(upstream),
                    },
                    "targeted_reread_policy": {
                        "path": policy.relative_to(root).as_posix(),
                        "sha256": sha256_file(policy),
                    },
                },
                "expected_input_contract": {
                    "document_count": 1,
                    "page_count": 1,
                    "planned_page_count": 1,
                    "planned_region_count": 1,
                    "full_table_structural_region_count": 0,
                    "row_band_structural_region_count": 0,
                    "numeric_cell_strip_region_count": 1,
                    "skipped_mapping_ineligible_page_count": 0,
                    "no_reread_trigger_page_count": 0,
                    "unsupported_escalation_count": 0,
                    "source_pdf_rerendered_region_count": 1,
                    "report_norm_ids_proposed_or_added": 0,
                },
                "safety": {"automatic_value_replacement_permitted": False},
                "claim_boundary": "Synthetic unit fixture; no value selection.",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    for relative in (
        "scripts/experiments/build_e0016_targeted_reread_inputs.py",
        "src/bctc_ai/preprocessing/targeted_run.py",
        "src/bctc_ai/preprocessing/targeted_reread.py",
        "src/bctc_ai/preprocessing/targeted_render.py",
        "src/bctc_ai/preprocessing/quality.py",
        "src/bctc_ai/core/atomic.py",
        "src/bctc_ai/core/hashing.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return root, config, source, upstream


def test_targeted_run_verifies_chain_and_rerenders_from_source_pdf(tmp_path, project_root):
    root, config, source, _ = _fixture(
        tmp_path, project_root / "config/preprocessing/targeted-reread-v1.yaml"
    )
    source_hash = sha256_file(source)
    output = root / "output" / "e0016"

    payload = build_targeted_reread_inputs(
        project_root=root,
        config_path=config,
        output_directory=output,
        git_state={"commit": "unit-test", "dirty": False},
    )

    assert payload["status"] == "PASS_INPUT_CONTRACT_NO_VALUE_SELECTION"
    assert payload["metrics"]["planned_region_count"] == 1
    assert payload["metrics"]["numeric_cell_strip_region_count"] == 1
    assert payload["safety"]["automatic_value_replacement"] is False
    assert sha256_file(source) == source_hash
    manifest = payload["documents"][0]["pages"][0]["render_manifest"]
    assert sha256_file(output / manifest["path"]) == manifest["sha256"]
    assert (output / "documents/test-bank/page-0001/region-0001/original.png").is_file()


def test_targeted_run_refuses_dirty_formal_evidence(tmp_path, project_root):
    root, config, _, _ = _fixture(
        tmp_path, project_root / "config/preprocessing/targeted-reread-v1.yaml"
    )

    with pytest.raises(TargetedRereadRunError, match="dirty worktree"):
        build_targeted_reread_inputs(
            project_root=root,
            config_path=config,
            output_directory=root / "output/e0016",
            git_state={"commit": "unit-test", "dirty": True},
        )


def test_targeted_run_detects_upstream_hash_drift(tmp_path, project_root):
    root, config, _, upstream = _fixture(
        tmp_path, project_root / "config/preprocessing/targeted-reread-v1.yaml"
    )
    upstream.write_text("{}\n", encoding="utf-8")

    with pytest.raises(TargetedRereadRunError, match="hash drift"):
        build_targeted_reread_inputs(
            project_root=root,
            config_path=config,
            output_directory=root / "output/e0016",
            git_state={"commit": "unit-test", "dirty": False},
        )
