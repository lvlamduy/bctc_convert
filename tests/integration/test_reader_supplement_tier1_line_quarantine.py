from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

from bctc_ai.corpus import wave1_role_b_full_reader_v3 as full_v3
from bctc_ai.corpus.ppocrv6_line_quarantine import (
    build_ppocrv6_page_outlying_child_line_quarantine,
    validate_ppocrv6_page_outlying_child_line_quarantine,
)
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    canonical_payload_sha256,
)
from bctc_ai.ocr.ppocrv6_page_session import validate_ppocrv6_payload
from bctc_ai.source_structure import finalized_v3_survey_stream_v1 as finalized_v3

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _authenticated_aggregate() -> dict:
    pins = finalized_v3.FINALIZED_V3_SURVEY_AUTHORITY_V1
    aggregate = finalized_v3._read_pinned_json(  # noqa: SLF001 - pinned public authority
        PROJECT_ROOT / full_v3.OUTPUT_RELATIVE_ROOT / "full-reader-aggregate.json",
        label="finalized V3 aggregate for bounded reader-supplement integration",
        expected_sha256=pins.aggregate_artifact_sha256,
        expected_size_bytes=pins.aggregate_size_bytes,
    )
    assert aggregate["aggregate_identity_sha256"] == pins.aggregate_identity_sha256
    assert len(aggregate["page_records"]) == pins.request_count == 1_449
    return aggregate


def _authenticated_backend(record: dict) -> dict:
    payload, _identity = full_v3._v3_read_object(  # noqa: SLF001 - authenticated CAS reader
        PROJECT_ROOT,
        record["backend_payload_ref"],
        ".json",
        "bounded reader-supplement source backend",
    )
    backend = full_v3._json_object(  # noqa: SLF001 - canonical source-object parser
        payload,
        "bounded reader-supplement source backend",
    )
    assert full_v3._same_typed_json(  # noqa: SLF001 - exact reference binding
        backend["request"], record["request"]
    )
    assert backend["request_sha256"] == record["request_sha256"]
    assert full_v3._same_typed_json(  # noqa: SLF001 - exact reference binding
        backend["render_ref"], record["render_ref"]
    )
    adoption = record.get("upstream_v2_adoption")
    if adoption is not None:
        assert full_v3._same_typed_json(  # noqa: SLF001 - authenticated source ref
            adoption["source_refs"]["backend_payload_ref"], record["backend_payload_ref"]
        )
    return backend


def _normalization_inputs(backend: dict) -> tuple[dict, list[int], dict]:
    metadata = backend.get("normalization_failure")
    if metadata is None:
        metadata = backend["word_box_normalization_ledger"]
    raw = backend["raw_provider_payload"]
    assert canonical_payload_sha256(raw) == metadata["raw_payload_sha256"]
    authority = {
        "policy": deepcopy(WORD_BOX_NORMALIZATION_POLICY),
        "policy_sha256": metadata["policy_sha256"],
        "control_identity_sha256": metadata["control_identity_sha256"],
        "normalization_producer_implementation_ledger_sha256": metadata[
            "normalization_producer_implementation_ledger_sha256"
        ],
    }
    return raw, metadata["pixel_dimensions"], authority


def test_exact_terminals_legacy_corrections_and_bounded_normal_controls() -> None:
    records = _authenticated_aggregate()["page_records"]
    terminals = [
        record for record in records if record["status"] == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
    ]
    legacy_corrected = [
        record
        for record in records
        if record["status"] == "OCR_WORD_BOX_READ_COMPLETE"
        and type(record["word_box_correction_count"]) is int
        and record["word_box_correction_count"] > 0
    ]
    normal_controls = [
        record
        for record in records
        if record["status"] == "OCR_WORD_BOX_READ_COMPLETE"
        and type(record["word_box_correction_count"]) is int
        and record["word_box_correction_count"] == 0
    ][:20]
    assert (len(terminals), len(legacy_corrected), len(normal_controls)) == (57, 20, 20)

    accounting: Counter[tuple[str, str]] = Counter()
    line_reasons: Counter[str] = Counter()
    for cohort, cohort_records in (
        ("terminal", terminals),
        ("legacy_corrected", legacy_corrected),
        ("normal", normal_controls),
    ):
        for record in cohort_records:
            backend = _authenticated_backend(record)
            raw, dimensions, authority = _normalization_inputs(backend)
            before = deepcopy(raw)
            normalized, quarantine, normalization = (
                build_ppocrv6_page_outlying_child_line_quarantine(
                    raw,
                    pixel_width=dimensions[0],
                    pixel_height=dimensions[1],
                    normalization_authority=authority,
                )
            )
            assert raw == before
            validate_ppocrv6_page_outlying_child_line_quarantine(
                raw,
                normalized,
                quarantine,
                normalization,
                pixel_width=dimensions[0],
                pixel_height=dimensions[1],
                normalization_authority=authority,
            )
            strict_counts = validate_ppocrv6_payload(
                normalized,
                pixel_width=dimensions[0],
                pixel_height=dimensions[1],
            )
            assert strict_counts == {
                "line_count": quarantine["retained_line_count"],
                "word_token_count": quarantine["retained_word_count"],
            }
            assert normalization["raw_payload_sha256"] == quarantine["retained_payload_sha256"]

            accounting[(cohort, "pages")] += 1
            for name in (
                "raw_line_count",
                "retained_line_count",
                "quarantined_line_count",
                "raw_word_count",
                "retained_word_count",
                "quarantined_word_count",
            ):
                accounting[(cohort, name)] += quarantine[name]
            for line in quarantine["quarantined_lines"]:
                line_reasons.update(line["reasons"])

            if cohort == "terminal":
                assert quarantine["status"] == "WHOLE_LINES_QUARANTINED"
            else:
                assert quarantine["status"] == "NO_CHANGE"
                assert normalization == backend["word_box_normalization_ledger"]
            if cohort == "normal":
                assert normalized == raw

    assert {
        name: accounting[("terminal", name)]
        for name in (
            "pages",
            "raw_line_count",
            "retained_line_count",
            "quarantined_line_count",
            "raw_word_count",
            "retained_word_count",
            "quarantined_word_count",
        )
    } == {
        "pages": 57,
        "raw_line_count": 4_155,
        "retained_line_count": 4_074,
        "quarantined_line_count": 81,
        "raw_word_count": 58_667,
        "retained_word_count": 58_558,
        "quarantined_word_count": 109,
    }
    assert line_reasons == {
        "PAGE_OVERSHOOT_GT_1PX": 80,
        "POST_CLIP_NONPOSITIVE": 2,
        "POST_CLIP_OUTSIDE_PARENT_REC_BOX": 9,
    }
    assert accounting[("legacy_corrected", "quarantined_line_count")] == 0
    assert accounting[("legacy_corrected", "quarantined_word_count")] == 0
    assert sum(record["word_box_correction_count"] for record in legacy_corrected) == 22
    assert sum(record["word_box_corrected_edge_count"] for record in legacy_corrected) == 22
    assert accounting[("normal", "quarantined_line_count")] == 0
    assert accounting[("normal", "quarantined_word_count")] == 0
