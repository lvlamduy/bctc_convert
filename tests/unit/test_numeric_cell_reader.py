from __future__ import annotations

import json
from base64 import b64decode
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr.numeric_cell_reader import (
    NumericCellReaderError,
    classify_numeric_prediction,
    load_numeric_reader_config,
    load_reference_blind_numeric_request,
)

_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_numeric_reader_config_is_pinned_and_has_no_other_authority(project_root):
    config, path = load_numeric_reader_config(
        project_root, Path("config/models/numeric-recognizer-v1.toml")
    )

    assert path == project_root / "config/models/numeric-recognizer-v1.toml"
    assert config["authority"] == "NUMERIC_CELL_PROPOSAL_ONLY"
    assert set(config["forbidden_authority"]) == {
        "GEOMETRY",
        "PERIOD",
        "UNIT",
        "SCOPE",
        "LABEL",
        "REPORT_NORM_ID",
        "SCHEMA_MAPPING",
        "ACCOUNTING_REPAIR",
        "CONFIDENCE_PROMOTION",
    }


@pytest.mark.parametrize(
    ("text", "status"),
    [
        ("", "EMPTY_PROPOSAL"),
        ("  ", "EMPTY_PROPOSAL"),
        ("5.741.287", "NUMERIC_CHARACTERS_ONLY_PROPOSAL"),
        ("(23.194)", "NUMERIC_CHARACTERS_ONLY_PROPOSAL"),
        ("-", "NUMERIC_CHARACTERS_ONLY_PROPOSAL"),
        ("O.123", "REJECT_NON_NUMERIC_CHARACTERS"),
        ("total 123", "REJECT_NON_NUMERIC_CHARACTERS"),
    ],
)
def test_numeric_prediction_character_gate(text, status):
    assert classify_numeric_prediction(text) == status


def test_reference_blind_request_forwards_only_crop_path(project_root, tmp_path):
    root = project_root / "output" / "unit-numeric-reader-request"
    root.mkdir(parents=True, exist_ok=True)
    try:
        crop = root / "cell.png"
        crop.write_bytes(_PNG)
        registry = root / "crop_registry.json"
        registry.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "policy": "FIXED_GRID_NUMERIC_CELL_CROPS_V1",
                    "geometry_authority": "E0029_PP_OCRV6_FIXED_GRID",
                    "recognizer_input_fields": ["crop_path"],
                    "metrics": {"cell_count": 1},
                    "cells": [
                        {
                            "cell_id": "page-0003-row-001-axis-1",
                            "crop_path": "cell.png",
                            "crop_size_bytes": crop.stat().st_size,
                            "crop_sha256": sha256_file(crop),
                            "recognizer_payload": {"crop_path": "cell.png"},
                            "primary_raw_text": "forbidden-to-reader",
                            "primary_value": "123",
                            "row_label": "forbidden-to-reader",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        _registry, samples, _path = load_reference_blind_numeric_request(project_root, registry)

        assert samples == [
            {
                "cell_id": "page-0003-row-001-axis-1",
                "crop_path": crop.as_posix(),
                "crop_sha256": sha256_file(crop),
            }
        ]
        assert "primary_value" not in samples[0]
        assert "row_label" not in samples[0]
    finally:
        crop.unlink(missing_ok=True)
        registry.unlink(missing_ok=True)
        root.rmdir()


def test_numeric_request_rejects_extra_reader_payload(project_root):
    root = project_root / "output" / "unit-numeric-reader-forbidden"
    root.mkdir(parents=True, exist_ok=True)
    try:
        crop = root / "cell.png"
        crop.write_bytes(b"fixed-crop")
        registry = root / "crop_registry.json"
        registry.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "policy": "FIXED_GRID_NUMERIC_CELL_CROPS_V1",
                    "geometry_authority": "E0029_PP_OCRV6_FIXED_GRID",
                    "recognizer_input_fields": ["crop_path"],
                    "metrics": {"cell_count": 1},
                    "cells": [
                        {
                            "cell_id": "page-0003-row-001-axis-1",
                            "crop_path": "cell.png",
                            "crop_size_bytes": crop.stat().st_size,
                            "crop_sha256": sha256_file(crop),
                            "recognizer_payload": {
                                "crop_path": "cell.png",
                                "primary_value": "123",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(NumericCellReaderError, match="payload is unsafe"):
            load_reference_blind_numeric_request(project_root, registry)
    finally:
        crop.unlink(missing_ok=True)
        registry.unlink(missing_ok=True)
        root.rmdir()


def test_numeric_request_accepts_e0033_v2_registry(project_root):
    root = project_root / "output" / "unit-numeric-reader-v2"
    root.mkdir(parents=True, exist_ok=True)
    try:
        crop = root / "cell.png"
        crop.write_bytes(_PNG)
        registry = root / "crop_registry.json"
        registry.write_text(
            json.dumps(
                {
                    "format_version": 2,
                    "policy": "FIXED_GRID_NUMERIC_CELL_CROPS_V2",
                    "geometry_authority": "E0033_PP_OCRV6_FIXED_GRID",
                    "recognizer_input_fields": ["crop_path"],
                    "metrics": {"cell_count": 1},
                    "cells": [
                        {
                            "cell_id": "page-0003-row-001-axis-1",
                            "crop_path": "cell.png",
                            "crop_size_bytes": crop.stat().st_size,
                            "crop_sha256": sha256_file(crop),
                            "recognizer_payload": {"crop_path": "cell.png"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        loaded, samples, _ = load_reference_blind_numeric_request(project_root, registry)

        assert loaded["geometry_authority"] == "E0033_PP_OCRV6_FIXED_GRID"
        assert len(samples) == 1
    finally:
        crop.unlink(missing_ok=True)
        registry.unlink(missing_ok=True)
        root.rmdir()


def test_numeric_request_accepts_isolated_semantic_graph_v3_registry(project_root):
    root = project_root / "output" / "unit-numeric-reader-v3"
    root.mkdir(parents=True, exist_ok=True)
    try:
        crop = root / "cell.png"
        crop.write_bytes(_PNG)
        registry = root / "crop_registry.json"
        registry.write_text(
            json.dumps(
                {
                    "format_version": 3,
                    "policy": "SEMANTIC_GRAPH_V2_VALUE_POSITION_CROPS_V1",
                    "geometry_authority": "AUTHENTICATED_V3_LINE_GEOMETRY",
                    "recognizer_input_fields": ["crop_path"],
                    "reference_isolation": {
                        "accounting_or_family_roles_available_to_reader": False,
                        "expected_or_primary_numeric_text_or_value_available_to_reader": False,
                        "human_review_available_to_reader": False,
                        "label_owner_or_branch_text_available_to_reader": False,
                        "period_unit_or_scope_available_to_reader": False,
                        "schema_label_or_report_norm_id_available_to_reader": False,
                    },
                    "metrics": {"cell_count": 1},
                    "cells": [
                        {
                            "cell_id": "page-0001-row-001-axis-1",
                            "crop_path": "cell.png",
                            "crop_size_bytes": crop.stat().st_size,
                            "crop_sha256": sha256_file(crop),
                            "recognizer_payload": {"crop_path": "cell.png"},
                            "primary_value": "must-not-leak",
                            "typed_role": "must-not-leak",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        loaded, samples, _ = load_reference_blind_numeric_request(project_root, registry)

        assert loaded["format_version"] == 3
        assert samples == [
            {
                "cell_id": "page-0001-row-001-axis-1",
                "crop_path": crop.as_posix(),
                "crop_sha256": sha256_file(crop),
            }
        ]
        assert "primary_value" not in samples[0]
        assert "typed_role" not in samples[0]
    finally:
        crop.unlink(missing_ok=True)
        registry.unlink(missing_ok=True)
        root.rmdir()


def test_semantic_graph_v3_request_rejects_reference_isolation_drift(project_root):
    root = project_root / "output" / "unit-numeric-reader-v3-drift"
    root.mkdir(parents=True, exist_ok=True)
    try:
        registry = root / "crop_registry.json"
        registry.write_text(
            json.dumps(
                {
                    "format_version": 3,
                    "policy": "SEMANTIC_GRAPH_V2_VALUE_POSITION_CROPS_V1",
                    "geometry_authority": "AUTHENTICATED_V3_LINE_GEOMETRY",
                    "recognizer_input_fields": ["crop_path"],
                    "reference_isolation": {
                        "expected_or_primary_numeric_text_or_value_available_to_reader": True
                    },
                    "metrics": {"cell_count": 0},
                    "cells": [],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(NumericCellReaderError, match="identity drifted"):
            load_reference_blind_numeric_request(project_root, registry)
    finally:
        registry.unlink(missing_ok=True)
        root.rmdir()
