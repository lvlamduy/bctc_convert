from __future__ import annotations

import sys
from collections import defaultdict, deque
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import fitz
import pytest

from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    build_causal_native_text_evidence_v2,
)
from bctc_ai.source_structure import local_accounting_graph_v1 as lag
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.contracts_v2 import validate_source_evidence_projection_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIT_TEST_ROOT = PROJECT_ROOT / "tests/unit"
if str(UNIT_TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(UNIT_TEST_ROOT))

from test_source_structure_evidence_projection_v2 import (  # noqa: E402
    _json_object_ref,
    _native_ordering_identity,
    _provider_ledger,
    _request,
    _synthetic_ocr_pair,
)

_QUALITY_ROWS = (
    ("Nợ đủ tiêu chuẩn", "100", "90"),
    ("Nợ cần chú ý", "20", "15"),
    ("Nợ dưới tiêu chuẩn", "10", "8"),
    ("Nợ nghi ngờ", "5", "4"),
    ("Nợ có khả năng mất vốn", "3", "2"),
    ("Tổng cộng", "138", "119"),
)


def _pixel_box(x0: int, y0: int, x1: int, y1: int) -> list[int]:
    return [x0, y0, x1, y1]


def _canonical_polygon(pixel_box: list[int]) -> list[list[int]]:
    x0, y0, x1, y1 = pixel_box
    # The reused exact OCR fixture has a 1,200 x 1,600 render for a
    # 600,000 x 800,000 mpt unrotated page: exactly 500 mpt per pixel.
    return [
        [x0 * 500, y0 * 500],
        [x1 * 500, y0 * 500],
        [x1 * 500, y1 * 500],
        [x0 * 500, y1 * 500],
    ]


def _ocr_line(text: str, pixel_box: list[int]) -> tuple[dict, dict]:
    polygon = _canonical_polygon(pixel_box)
    canonical_box = [
        min(point[0] for point in polygon),
        min(point[1] for point in polygon),
        max(point[0] for point in polygon),
        max(point[1] for point in polygon),
    ]
    word = {
        "raw_text": text,
        "score": None,
        "score_kind": "PP_OCRV6_LINE_SCORE_ONLY",
        "normalized_pixel_bbox": pixel_box,
        "canonical_bbox_mpt": canonical_box,
        "canonical_polygon_mpt": polygon,
    }
    line = {
        "raw_text": text,
        "score": 0.95,
        "score_kind": "PP_OCRV6_LINE_RECOGNITION_SCORE",
        "raw_pixel_bbox": pixel_box,
        "raw_pixel_polygon": [
            [pixel_box[0], pixel_box[1]],
            [pixel_box[2], pixel_box[1]],
            [pixel_box[2], pixel_box[3]],
            [pixel_box[0], pixel_box[3]],
        ],
        "canonical_bbox_mpt": canonical_box,
        "canonical_polygon_mpt": polygon,
        "words": [deepcopy(word)],
    }
    return line, word


def _quality_visible_lines(*, owner_text: str) -> list[tuple[str, list[int]]]:
    visible_lines = [
        (owner_text, _pixel_box(80, 100, 570, 134)),
        ("Phân tích chất lượng nợ cho vay", _pixel_box(80, 150, 650, 184)),
        ("31/12/2025", _pixel_box(700, 205, 850, 239)),
        ("31/12/2024", _pixel_box(900, 205, 1_050, 239)),
        ("Đơn vị: triệu VND", _pixel_box(80, 250, 410, 284)),
    ]
    for row_index, (label, left_value, right_value) in enumerate(_QUALITY_ROWS):
        y0 = 330 + row_index * 75
        visible_lines.extend(
            (
                (label, _pixel_box(80, y0, 650, y0 + 34)),
                (left_value, _pixel_box(735, y0, 815, y0 + 34)),
                (right_value, _pixel_box(935, y0, 1_015, y0 + 34)),
            )
        )
    return visible_lines


def _exact_quality_ocr_projection(*, owner_text: str) -> dict:
    record, result = _synthetic_ocr_pair()
    visible_lines = _quality_visible_lines(owner_text=owner_text)

    pairs = [_ocr_line(text, box) for text, box in visible_lines]
    result["lines"] = [line for line, _word in pairs]
    result["words"] = [word for _line, word in pairs]
    result["metrics"] = {
        "line_count": len(pairs),
        "word_token_count": len(pairs),
        "minimum_line_score": 0.95,
        "mean_line_score": 0.95,
        "lines_below_0_8": 0,
        "lines_below_0_9": 0,
    }

    result_ref = _json_object_ref(result)
    record["result_ref"] = deepcopy(result_ref)
    record["upstream_v2_adoption"]["source_refs"]["result_ref"] = deepcopy(result_ref)
    record["line_axis_count"] = len(pairs)
    record["nonempty_line_axis_count"] = len(pairs)
    record["accepted_line_count"] = len(pairs)
    record["word_token_count"] = len(pairs)
    return project_authenticated_page_v2(page_record=record, page_result=result)


def _exact_quality_native_projection(monkeypatch: pytest.MonkeyPatch, *, owner_text: str) -> dict:
    document = fitz.open()
    document.new_page(width=600, height=800)
    source_bytes = document.tobytes(garbage=4, deflate=True)
    document.close()
    source_sha = sha256(source_bytes).hexdigest()
    provider_ledger = _provider_ledger()
    request, request_sha = _request(
        route="CAUSAL_NATIVE_TEXT",
        source_sha=source_sha,
        source_size=len(source_bytes),
        provider_identity=provider_ledger["sha256"],
    )

    lines = []
    words = []
    for ordinal, (text, pixel_box) in enumerate(_quality_visible_lines(owner_text=owner_text)):
        polygon = _canonical_polygon(pixel_box)
        canonical_box = [
            min(point[0] for point in polygon),
            min(point[1] for point in polygon),
            max(point[0] for point in polygon),
            max(point[1] for point in polygon),
        ]
        word = {
            "raw_text": text,
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": canonical_box,
            "block_number": ordinal,
            "line_number": 0,
            "word_number": 0,
        }
        lines.append(
            {
                "raw_text": text,
                "score": None,
                "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
                "canonical_bbox_mpt": canonical_box,
                "block_number": ordinal,
                "line_number": 0,
                "words": [deepcopy(word)],
            }
        )
        words.append(word)
    raw_payload = {
        "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "native_text_quality": "USABLE_TEXT_LAYER",
        "corruption_markers": [],
        "lines": lines,
        "words": words,
        "quarantined_spans": [],
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }
    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        lambda *_args, **_kwargs: deepcopy(raw_payload),
    )
    built_backend, result = build_causal_native_text_evidence_v2(
        request=request,
        request_sha256=request_sha,
        source_bytes=source_bytes,
        document_id=f"sha256:{source_sha}",
        physical_page=1,
        provider_runtime_ledger=provider_ledger,
        causal_policy_path=PROJECT_ROOT / "config/ocr/causal-native-text-v1.yaml",
        quality_policy_path=PROJECT_ROOT / "config/ocr/native-text-quality-v2.yaml",
        native_ordering_policy_identity=_native_ordering_identity(),
        full_control_identity_sha256="7" * 64,
    )
    metrics = result["metrics"]
    record = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
        "request_ordinal": 1,
        "document_id": f"sha256:{source_sha}",
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
        "physical_page": 1,
        "route": "CAUSAL_NATIVE_TEXT",
        "request_sha256": request_sha,
        "request": request,
        "status": result["status"],
        "origin": "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2",
        "upstream_status": None,
        "upstream_origin": None,
        "upstream_unresolved": None,
        "render_ref": None,
        "backend_payload_ref": _json_object_ref(built_backend),
        "result_ref": _json_object_ref(result),
        "upstream_v2_adoption": None,
        "line_axis_count": metrics["line_count"],
        "nonempty_line_axis_count": metrics["line_count"],
        "exact_empty_line_axis_count": 0,
        "accepted_line_count": metrics["line_count"],
        "word_token_count": metrics["word_token_count"],
        "quarantined_span_count": metrics["ghost_quarantined_span_count"],
        "ordering_quarantined_raw_line_run_count": metrics[
            "ordering_quarantined_raw_line_run_count"
        ],
        "ordering_quarantined_raw_word_count": metrics["ordering_quarantined_raw_word_count"],
        "noncontiguous_line_identity_count": metrics["noncontiguous_line_identity_count"],
        "word_box_correction_count": 0,
        "word_box_corrected_edge_count": 0,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
        "unresolved": False,
    }
    return project_authenticated_page_v2(page_record=record, page_result=result)


def _source_spans(projection: dict) -> dict[str, deque[dict]]:
    spans: dict[str, deque[dict]] = defaultdict(deque)
    for atom in projection["neutral_page_v1"]["atoms"]:
        if atom["kind"] != "LINE" or atom["authority"] != "AUTHENTICATED_PRIMARY":
            continue
        spans[atom["raw_text"]].append(
            {
                "text": atom["raw_text"],
                "canonical_bbox_mpt": deepcopy(atom["canonical_bbox_mpt"]),
                "source_atom_ids": [atom["source_local_id"]],
            }
        )
    return spans


def _take(spans: dict[str, deque[dict]], text: str) -> dict:
    return spans[text].popleft()


def _quality_observation(projection: dict, *, owner_text: str) -> dict:
    spans = _source_spans(projection)
    owner = _take(spans, owner_text)
    branch = _take(spans, "Phân tích chất lượng nợ cho vay")
    axes = [
        {"header": _take(spans, "31/12/2025")},
        {"header": _take(spans, "31/12/2024")},
    ]
    unit = _take(spans, "Đơn vị: triệu VND")
    rows = []
    for label, left_value, right_value in _QUALITY_ROWS:
        rows.append(
            {
                "label": _take(spans, label),
                "value_positions": [
                    {
                        "axis_index": axis_index,
                        "state": "OBSERVED_VALUE",
                        "raw_text": raw_text,
                        **{
                            key: value
                            for key, value in _take(spans, raw_text).items()
                            if key != "text"
                        },
                    }
                    for axis_index, raw_text in enumerate((left_value, right_value))
                ],
            }
        )
    boxes = [
        owner["canonical_bbox_mpt"],
        branch["canonical_bbox_mpt"],
        unit["canonical_bbox_mpt"],
        *(axis["header"]["canonical_bbox_mpt"] for axis in axes),
        *(row["label"]["canonical_bbox_mpt"] for row in rows),
        *(position["canonical_bbox_mpt"] for row in rows for position in row["value_positions"]),
    ]
    region = {
        "canonical_bbox_mpt": [
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        ],
        "owner_label": owner,
        "branch_label": branch,
        "rows": rows,
        "axes": axes,
        "local_unit_labels": [unit],
        "adjacent_row_boundaries_verified": True,
    }
    return {
        "format_version": lag.LOCAL_ACCOUNTING_OBSERVATION_FORMAT_VERSION_V1,
        "source_local_page_id": projection["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(projection),
        "regions": [region],
    }


def _infer_exact_quality(*, owner_text: str) -> tuple[dict, dict]:
    projection = _exact_quality_ocr_projection(owner_text=owner_text)
    # This is the production validator, not the compact monkeypatch used by
    # the LAG unit tests.
    assert validate_source_evidence_projection_v2(projection) == projection
    graph = lag.infer_local_accounting_graph_v1(
        projection,
        _quality_observation(projection, owner_text=owner_text),
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    return projection, graph


def test_exact_ocr_v2_source_projection_reaches_quality_core_accepted() -> None:
    projection, graph = _infer_exact_quality(owner_text="Cho vay khách hàng")

    assert projection["page_record_v2"]["route"] == "DOMINANT_RASTER_OCR"
    assert graph["status"] == lag.GraphStatusV1.CORE_ACCEPTED.value
    assert graph["accepted_counts"] == {
        "TABLE": 1,
        "LOGICAL_ROW": 6,
        "VALUE_POSITION": 12,
        "AXIS": 2,
        "HIERARCHY": 18,
    }
    assert graph["arithmetic_check"] == {
        "status": "CORROBORATED",
        "evaluated_axis_indexes": [0, 1],
    }
    assert graph["canonicalization_eligible"] is False
    assert graph["export_eligible"] is False


def test_exact_ocr_v2_matched_owner_control_remains_explicit_unresolved() -> None:
    _projection, graph = _infer_exact_quality(owner_text="Chứng khoán đầu tư")

    assert graph["status"] == lag.GraphStatusV1.EXPLICIT_UNRESOLVED.value
    assert graph["accepted_counts"] == {
        "TABLE": 0,
        "LOGICAL_ROW": 0,
        "VALUE_POSITION": 0,
        "AXIS": 0,
        "HIERARCHY": 0,
    }
    assert "OWNER_NOT_RESOLVED" in graph["unresolved_reasons"]
    assert graph["canonicalization_eligible"] is False
    assert graph["export_eligible"] is False


def test_exact_native_v2_source_projection_reaches_same_quality_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = _exact_quality_native_projection(
        monkeypatch,
        owner_text="Cho vay khách hàng",
    )
    assert validate_source_evidence_projection_v2(projection) == projection

    graph = lag.infer_local_accounting_graph_v1(
        projection,
        _quality_observation(projection, owner_text="Cho vay khách hàng"),
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )

    assert projection["page_record_v2"]["route"] == "CAUSAL_NATIVE_TEXT"
    assert graph["status"] == lag.GraphStatusV1.CORE_ACCEPTED.value
    assert graph["accepted_counts"]["TABLE"] == 1
    assert graph["accepted_counts"]["LOGICAL_ROW"] == 6
    assert graph["accepted_counts"]["VALUE_POSITION"] == 12
    assert graph["accepted_counts"]["AXIS"] == 2
    assert graph["arithmetic_check"]["status"] == "CORROBORATED"
