from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import full_document_vietocr_accounting_axis_v1 as axis_module
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    ANNUAL_2025_EXPECTED_LINE_VECTOR,
    ANNUAL_2025_EXPECTED_PAGE_VECTOR,
    ANNUAL_2025_SOURCE_FORMAT_VERSION,
    EXPECTED_DOCUMENT_ORDER,
    EXPECTED_LINE_VECTOR,
    EXPECTED_PAGE_VECTOR,
    FullDocumentVietOCRAccountingAxisV1Error,
    project_full_document_vietocr_accounting_axis_v1,
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_accounting_axis_replay_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _ref(path: str, ordinal: int = 1) -> dict[str, object]:
    return {
        "path": path,
        "sha256": f"{ordinal:064x}",
        "size_bytes": ordinal,
    }


def _source_index() -> dict[str, object]:
    documents: list[dict[str, object]] = []
    semantic_axis: list[dict[str, str]] = []
    sample_ordinal = 0
    for document_ordinal, (code, page_count, line_count) in enumerate(
        zip(
            EXPECTED_DOCUMENT_ORDER,
            EXPECTED_PAGE_VECTOR,
            EXPECTED_LINE_VECTOR,
            strict=True,
        ),
        1,
    ):
        base, extra = divmod(line_count, page_count)
        pages: list[dict[str, object]] = []
        for physical_page in range(1, page_count + 1):
            page_lines = base + (physical_page <= extra)
            lines: list[dict[str, object]] = []
            for line_index in range(page_lines):
                sample_ordinal += 1
                sample_id = f"sample-{sample_ordinal:08d}"
                text = "" if sample_ordinal == 1 else f"Fresh line {sample_ordinal}"
                period_surfaces = {
                    (1, 5): "Tại ngày 31/12/2025",
                    (1, 6): "Tại ngày 31/12/2024",
                    (1, 7): "Ngày 1 tháng 1 năm 2025",
                    (2, 5): "Ngày 31 tháng 12 năm 2025",
                    (2, 6): "Ngày 31 tháng 12 năm 2024",
                }
                text = period_surfaces.get((physical_page, line_index), text)
                semantic_axis.append({"sample_id": sample_id, "vietocr_text": text})
                lines.append(
                    {
                        "crop_ref": _ref(f"output/development/full-vietocr/crops/{sample_id}.png"),
                        "line_axis_role": "LINE",
                        "mean_decoded_character_probability": 0.9,
                        "padded_source_bbox_raw_pixels": [0, line_index, 12, line_index + 2],
                        "processed_height": 32,
                        "processed_width": 128,
                        "sample_id": sample_id,
                        "source_bbox_raw_pixels": [1, line_index, 11, line_index + 1],
                        "source_line_index": line_index,
                        "vietocr_text": text,
                    }
                )
            pages.append(
                {
                    "geometry_mode": "RASTER_LINE_AXIS",
                    "line_count": page_lines,
                    "lines": lines,
                    "physical_page": physical_page,
                    "route": "PAGE_READER_V3",
                    "source_projection": {},
                    "terminal_status_preserved": False,
                    "upstream_status": "COMPLETE",
                }
            )
        documents.append(
            {
                "bank_code": code,
                "document_ordinal": document_ordinal,
                "page_count": page_count,
                "pages": pages,
                "source_pdf": _ref(f"corpus/{code}/report.pdf", document_ordinal),
            }
        )
    return {
        "authority": {
            "all_empty_predictions_preserved": True,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "old_ppocr_or_native_transcript_used_as_semantic_text": False,
            "ordered_semantic_proposal_authority": True,
            "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
        },
        "documents": documents,
        "format_version": "WAVE1_8DOCUMENT_VIETOCR_TRANSFORMER_SEMANTIC_INDEX_V1",
        "input_refs": {
            "crop_manifest": _ref("output/development/full-vietocr/crop_manifest.json", 9),
            "ocr_result": _ref("output/development/full-vietocr/ocr_result.json", 10),
            "reader_request": _ref("output/development/full-vietocr/request.json", 11),
            "run_manifest": _ref("output/development/full-vietocr/run_manifest.json", 12),
        },
        "metrics": {
            "document_count": 8,
            "empty_prediction_count": 1,
            "line_count_vector": list(EXPECTED_LINE_VECTOR),
            "page_count": sum(EXPECTED_PAGE_VECTOR),
            "page_count_vector": list(EXPECTED_PAGE_VECTOR),
            "sample_count": sum(EXPECTED_LINE_VECTOR),
            "semantic_axis_sha256": canonical_json_sha256_v1(semantic_axis),
            "terminal_page_count": 0,
        },
        "reader": {"profile": "REFERENCE_BLIND_VIETOCR_TRANSFORMER"},
        "state": "VERIFIED_COMPLETE_ORDERED_VIETOCR_TRANSFORMER_PROPOSALS",
    }


@pytest.fixture(scope="module")
def source_index() -> dict[str, object]:
    return _source_index()


@pytest.fixture(scope="module")
def projection(source_index: dict[str, object]) -> dict[str, object]:
    return project_full_document_vietocr_accounting_axis_v1(source_index)


def test_fixed_full_document_axis_preserves_exact_denominator_and_empty_text(
    projection: dict[str, object],
) -> None:
    assert projection["metrics"] == {
        "document_count": 8,
        "line_count_vector": list(EXPECTED_LINE_VECTOR),
        "page_count": 453,
        "page_count_vector": list(EXPECTED_PAGE_VECTOR),
        "sample_count": 34_341,
    }
    documents = projection["documents"]
    assert isinstance(documents, list)
    assert [document["document_provenance"] for document in documents] == list(
        EXPECTED_DOCUMENT_ORDER
    )
    first_line = documents[0]["pages"][0]["lines"][0]
    assert first_line == {
        "bbox": [1, 0, 11, 1],
        "source_line_index": 0,
        "source_text": None,
        "vietocr_text": "",
        "vietocr_text_accentless": "",
    }
    assert documents[0]["pages"][0]["lines"][1]["vietocr_text_accentless"] == "fresh line 2"
    assert set(first_line).isdisjoint({"bank_code", "physical_page", "source_pdf"})
    assert projection["authority"]["numeric_authority"] is False
    assert projection["authority"]["accentless_text_is_anchor_evidence_only"] is True
    assert "reporting_period_context" not in documents[0]


def test_audited_annual_2025_profile_is_fixed_to_the_verified_geometry_denominator() -> None:
    assert ANNUAL_2025_EXPECTED_PAGE_VECTOR == (100, 103, 100, 71, 84, 85, 74, 78)
    assert ANNUAL_2025_EXPECTED_LINE_VECTOR == (
        7343,
        8087,
        7249,
        5800,
        6539,
        6930,
        6321,
        6080,
    )
    assert sum(ANNUAL_2025_EXPECTED_PAGE_VECTOR) == 695
    assert sum(ANNUAL_2025_EXPECTED_LINE_VECTOR) == 54_349
    assert axis_module._source_profile(ANNUAL_2025_SOURCE_FORMAT_VERSION) == {
        "line_vector": ANNUAL_2025_EXPECTED_LINE_VECTOR,
        "page_vector": ANNUAL_2025_EXPECTED_PAGE_VECTOR,
    }


def test_document_reporting_period_contexts_are_a_separate_replay_bound_projection(
    source_index: dict[str, object],
) -> None:
    projection = project_full_document_vietocr_reporting_period_contexts_v1(source_index)

    assert projection["authority"]["reporting_period_context_is_proposal_only"] is True
    assert projection["authority"]["mapping_authority"] is False
    assert projection["authority"]["numeric_authority"] is False
    assert [record["document_provenance"] for record in projection["contexts"]] == list(
        EXPECTED_DOCUMENT_ORDER
    )
    for record in projection["contexts"]:
        context = record["reporting_period_context"]
        assert context["current_period_end"] == "31/12/2025"
        assert context["current_period_start"] == "01/01/2025"
        assert context["balance_comparative_period_end"] == "31/12/2024"
        assert context["period_kind"] == "ANNUAL"
        assert context["reporting_year"] == 2025
    assert (
        validate_full_document_vietocr_reporting_period_contexts_replay_v1(projection, source_index)
        == projection
    )


def test_coordinated_period_context_rehash_cannot_replace_document_dates(
    source_index: dict[str, object],
) -> None:
    projection = project_full_document_vietocr_reporting_period_contexts_v1(source_index)
    forged = copy.deepcopy(projection)
    forged["contexts"][0]["reporting_period_context"]["current_period_end"] = "31/12/2024"
    material = copy.deepcopy(forged)
    material.pop("projection_id")
    forged["projection_id"] = "fdvrpcv1:projection:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        FullDocumentVietOCRAccountingAxisV1Error,
        match="period contexts do not replay exactly",
    ):
        validate_full_document_vietocr_reporting_period_contexts_replay_v1(forged, source_index)


def test_projection_exactly_replays_against_the_source_semantic_index(
    projection: dict[str, object], source_index: dict[str, object]
) -> None:
    assert (
        validate_full_document_vietocr_accounting_axis_replay_v1(projection, source_index)
        == projection
    )


def test_unavailable_character_probability_preserves_the_ordered_text_line(
    source_index: dict[str, object],
) -> None:
    line = source_index["documents"][0]["pages"][0]["lines"][0]
    original = line["mean_decoded_character_probability"]
    line["mean_decoded_character_probability"] = None
    try:
        projected = project_full_document_vietocr_accounting_axis_v1(source_index)
        assert projected["documents"][0]["pages"][0]["lines"][0]["vietocr_text"] == ""
        assert projected["metrics"]["sample_count"] == 34_341
    finally:
        line["mean_decoded_character_probability"] = original


def test_coordinated_projection_rehash_cannot_replace_fresh_text(
    projection: dict[str, object], source_index: dict[str, object]
) -> None:
    forged = copy.deepcopy(projection)
    forged["documents"][0]["pages"][0]["lines"][0]["vietocr_text"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("projection_id")
    forged["projection_id"] = "fdvaav1:projection:" + canonical_json_sha256_v1(material)
    with pytest.raises(FullDocumentVietOCRAccountingAxisV1Error, match="replay exactly"):
        validate_full_document_vietocr_accounting_axis_replay_v1(forged, source_index)


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("metrics", "page_count_vector", 0), 33.0),
        (("documents", 0, "document_ordinal"), True),
        (("documents", 0, "pages", 0, "physical_page"), 1.0),
        (
            ("documents", 0, "pages", 0, "lines", 0, "source_line_index"),
            False,
        ),
        (
            (
                "documents",
                0,
                "pages",
                0,
                "lines",
                0,
                "mean_decoded_character_probability",
            ),
            True,
        ),
    ],
)
def test_source_index_rejects_bool_float_type_smuggling(
    source_index: dict[str, object], path: tuple[object, ...], bad_value: object
) -> None:
    cursor: object = source_index
    for key in path[:-1]:
        cursor = cursor[key]
    key = path[-1]
    original = cursor[key]
    cursor[key] = bad_value
    try:
        with pytest.raises(FullDocumentVietOCRAccountingAxisV1Error):
            project_full_document_vietocr_accounting_axis_v1(source_index)
    finally:
        cursor[key] = original


def test_empty_prediction_metric_is_recomputed_not_trusted(source_index: dict[str, object]) -> None:
    metrics = source_index["metrics"]
    original = metrics["empty_prediction_count"]
    metrics["empty_prediction_count"] = 0
    try:
        with pytest.raises(FullDocumentVietOCRAccountingAxisV1Error, match="fixed metrics"):
            project_full_document_vietocr_accounting_axis_v1(source_index)
    finally:
        metrics["empty_prediction_count"] = original


def test_unregistered_semantic_index_profile_is_rejected(
    source_index: dict[str, object],
) -> None:
    original = source_index["format_version"]
    source_index["format_version"] = "CALLER_SELECTED_UNPINNED_SEMANTIC_INDEX_V1"
    try:
        with pytest.raises(
            FullDocumentVietOCRAccountingAxisV1Error,
            match="format is not admitted",
        ):
            project_full_document_vietocr_accounting_axis_v1(source_index)
    finally:
        source_index["format_version"] = original
