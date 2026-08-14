from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_EXPERIMENTS = _ROOT / "scripts/experiments"
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))


def _load():
    name = "build_e0049_mbb_maturity_mapping_readiness_test"
    path = _EXPERIMENTS / "build_e0049_mbb_maturity_mapping_readiness.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


subject = _load()


def _item(role: str, report_norm_id: int | None) -> dict:
    return {
        "automatic_checks": {
            "exact_digit_and_sign_agreement": "PASS",
            "source_crop_identity": "PASS",
            "source_graph_value_role": "PASS",
            "two_axis_core_closure": "PASS",
        },
        "disposition": (
            "SOURCE_ONLY_VALIDATION_MAPPING_INELIGIBLE"
            if role == "TOTAL"
            else "SCHEMA_CANDIDATE_MAPPING_UNRESOLVED"
        ),
        "numeric_values": ["1", "2"],
        "report_norm_id": report_norm_id,
        "source_line_indices": [1, 2],
        "typed_role": role,
    }


def _result() -> dict:
    value = {
        "automated_checks": {"numeric_verification_id": "numeric"},
        "candidate_items": [
            _item("SHORT_TERM", 753),
            _item("MEDIUM_TERM", 754),
            _item("LONG_TERM", 755),
            _item("TOTAL", None),
        ],
        "claim_boundary": subject.CLAIM_BOUNDARY,
        "exceptional_review_queue": [
            {
                "automatic_disposition": "UNRESOLVED",
                "code": code,
                "evidence": {},
                "review_scope": "TEST",
            }
            for code in (
                "DOCUMENT_STATEMENT_CONTEXT_INHERITANCE_NOT_AUTHENTICATED",
                "MEDIUM_TERM_SEMANTIC_PIXEL_TRANSCRIPTION_RECONCILIATION_REQUIRED",
                "VISIBLE_OPTIONAL_MARGIN_CHILD_NOT_ADJUDICATED",
            )
        ],
        "experiment_id": subject.EXPERIMENT_ID,
        "format_version": subject.FORMAT_VERSION,
        "inputs": {},
        "metrics": {
            "candidate_value_row_count": 3,
            "exceptional_review_item_count": 3,
            "mapping_verified_row_count": 0,
            "numeric_verified_cell_count": 8,
            "source_only_validation_row_count": 1,
            "unresolved_mapping_row_count": 3,
        },
        "near_neighbours": [
            {
                "disposition": "VISIBLE_OUTSIDE_STRICT_THREE_ROW_CORE_NOT_ADJUDICATED",
                "report_norm_id": 5747,
                "status": "UNRESOLVED",
                "whole_document_absence_claim": False,
            },
            {
                "disposition": "SCHEMA_CONTEXT_UNRESOLVED_ORPHAN_MAPPING_INELIGIBLE",
                "report_norm_id": 1944,
                "status": "UNRESOLVED",
                "whole_document_absence_claim": False,
            },
        ],
        "readiness_id": "",
        "safety": copy.deepcopy(subject._SAFETY),
        "state": subject.STATE,
        "status": subject.STATUS,
    }
    value["readiness_id"] = subject._readiness_id(value)
    return value


def test_shape_keeps_candidates_numeric_and_mapping_separate() -> None:
    value = _result()

    assert subject._validate_shape(value) == value
    assert value["metrics"]["numeric_verified_cell_count"] == 8
    assert value["metrics"]["mapping_verified_row_count"] == 0
    assert value["candidate_items"][-1]["report_norm_id"] is None
    assert value["near_neighbours"][0]["whole_document_absence_claim"] is False


def test_verified_mapping_claim_is_rejected_after_coordinated_rehash() -> None:
    value = _result()
    value["candidate_items"][0]["disposition"] = "VERIFIED_BY_CODEX"
    value["readiness_id"] = subject._readiness_id(value)

    with pytest.raises(
        subject.E0049MBBMappingReadinessError,
        match="identity or safety boundary",
    ):
        subject._validate_shape(value)


def test_near_neighbour_document_absence_claim_is_rejected() -> None:
    value = _result()
    value["near_neighbours"][0]["whole_document_absence_claim"] = True
    value["readiness_id"] = subject._readiness_id(value)

    with pytest.raises(
        subject.E0049MBBMappingReadinessError,
        match="near-neighbour boundary",
    ):
        subject._validate_shape(value)


def test_public_validation_rejects_self_rehashed_exception_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _result()
    monkeypatch.setattr(
        subject,
        "build_e0049_mbb_maturity_mapping_readiness_v1",
        lambda _root: copy.deepcopy(expected),
    )
    forged = copy.deepcopy(expected)
    forged["exceptional_review_queue"].pop()
    forged["readiness_id"] = subject._readiness_id(forged)

    with pytest.raises(subject.E0049MBBMappingReadinessError):
        subject.validate_e0049_mbb_maturity_mapping_readiness_v1(forged, _ROOT)


def test_exception_queue_is_derived_from_exact_bound_lines() -> None:
    samples = [
        {
            "crop_ref": {"path": f"crop-{index}.png", "sha256": f"{index:064x}", "size_bytes": 1},
            "raw_prediction": "ordinary",
            "sample_id": f"sample-{index}",
            "source_atom": {"canonical_bbox_mpt": [0, 0, 1, 1], "source_atom_id": f"atom-{index}"},
            "source_bbox_raw_pixels": [0, 0, 1, 1],
            "source_line_index": index,
        }
        for index in range(108)
    ]
    samples[94]["raw_prediction"] = "Nợ trùng hạn"
    for index, text in zip(
        range(102, 108),
        ("margin one", "margin two", "16.828.054", "15.040.585", "grand one", "grand two"),
        strict=True,
    ):
        samples[index]["raw_prediction"] = text
    binding = {
        "samples": samples,
        "source_local_page_id": "source-page",
        "source_projection_sha256": "1" * 64,
    }
    source = {"page_result": {"lines": [{"raw_text": f"source-{index}"} for index in range(108)]}}

    queue, context = subject._exception_queue(source, binding)

    assert context["status"] == "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
    assert [item["code"] for item in queue] == [
        "DOCUMENT_STATEMENT_CONTEXT_INHERITANCE_NOT_AUTHENTICATED",
        "MEDIUM_TERM_SEMANTIC_PIXEL_TRANSCRIPTION_RECONCILIATION_REQUIRED",
        "VISIBLE_OPTIONAL_MARGIN_CHILD_NOT_ADJUDICATED",
    ]
    assert queue[1]["evidence"]["semantic_proposal_text"] == "Nợ trùng hạn"
    assert queue[2]["evidence"]["schema_near_neighbour_report_norm_id"] == 5747
