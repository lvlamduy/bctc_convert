from __future__ import annotations

from contextlib import contextmanager, nullcontext
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.source_structure import finalized_v3_survey_stream_v1 as stream_v1


def _page(number: int) -> stream_v1.AuthenticatedV3SurveyPage:
    return stream_v1.AuthenticatedV3SurveyPage(
        page_record={"number": number},
        page_result={"number": number},
    )


def test_single_use_stream_requires_one_complete_iteration() -> None:
    stream = stream_v1._SingleUseSurveyStream(  # noqa: SLF001
        ({"number": 1}, {"number": 2}),
        lambda record: _page(record["number"]),
        authority=stream_v1._FINALIZED_V3_PINS,  # noqa: SLF001
    )

    assert [page.page_record["number"] for page in stream] == [1, 2]
    assert stream.exhausted is True
    assert stream.delivered_count == 2
    with pytest.raises(stream_v1.FinalizedV3SurveyStreamError, match="single-use"):
        iter(stream)


def test_single_use_stream_rejects_second_iterator_claim() -> None:
    stream = stream_v1._SingleUseSurveyStream(  # noqa: SLF001
        ({"number": 1},),
        lambda record: _page(record["number"]),
        authority=stream_v1._FINALIZED_V3_PINS,  # noqa: SLF001
    )

    iterator = iter(stream)
    with pytest.raises(stream_v1.FinalizedV3SurveyStreamError, match="single-use"):
        iter(stream)
    assert next(iterator).page_record["number"] == 1


def _synthetic_authority() -> stream_v1._AuthenticatedAuthority:  # noqa: SLF001
    return stream_v1._AuthenticatedAuthority(  # noqa: SLF001
        control={"identity": "control"},
        page_records=({"number": 1}, {"number": 2}),
    )


def _patch_synthetic_session(
    monkeypatch: pytest.MonkeyPatch,
    manifests: list[list[Any]],
) -> None:
    @contextmanager
    def snapshot(_root: Path, _document_ids: list[str]):
        yield

    manifest_iterator = iter(manifests)
    monkeypatch.setattr(stream_v1.full_v3, "_v3_read_only_output_snapshot", snapshot)
    monkeypatch.setattr(
        stream_v1.full_v3,
        "_v3_output_live_manifest",
        lambda _root: next(manifest_iterator),
    )
    monkeypatch.setattr(
        stream_v1.full_v3,
        "_v3_bind_output_reads",
        lambda _root, _manifest: nullcontext(),
    )
    monkeypatch.setattr(
        stream_v1,
        "_authenticate_finalized_authority",
        lambda _root, _pins: _synthetic_authority(),
    )
    monkeypatch.setattr(
        stream_v1,
        "_load_authenticated_page",
        lambda _root, _control, record: _page(record["number"]),
    )


def test_pinned_context_accepts_complete_stream_and_unchanged_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stable = [["f", "authority", "unchanged"]]
    _patch_synthetic_session(monkeypatch, [stable, stable])

    with stream_v1._open_pinned_stream(  # noqa: SLF001
        tmp_path,
        stream_v1._FINALIZED_V3_PINS,  # noqa: SLF001
    ) as stream:
        assert [page.page_result["number"] for page in stream] == [1, 2]

    with pytest.raises(stream_v1.FinalizedV3SurveyStreamError, match="closed"):
        iter(stream)


def test_pinned_context_rejects_partial_consumption(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stable = [["f", "authority", "unchanged"]]
    _patch_synthetic_session(monkeypatch, [stable, stable])

    with pytest.raises(stream_v1.FinalizedV3SurveyStreamError, match=r"1/2"):
        with stream_v1._open_pinned_stream(  # noqa: SLF001
            tmp_path,
            stream_v1._FINALIZED_V3_PINS,  # noqa: SLF001
        ) as stream:
            next(iter(stream))


def test_pinned_context_rejects_output_manifest_change_after_full_consumption(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_synthetic_session(
        monkeypatch,
        [
            [["f", "authority", "before"]],
            [["f", "authority", "after"]],
        ],
    )

    with pytest.raises(stream_v1.FinalizedV3SurveyStreamError, match="output changed"):
        with stream_v1._open_pinned_stream(  # noqa: SLF001
            tmp_path,
            stream_v1._FINALIZED_V3_PINS,  # noqa: SLF001
        ) as stream:
            list(stream)


def _ocr_record_and_result() -> tuple[dict[str, Any], dict[str, Any]]:
    request = {
        "bank_identity_used": False,
        "filename_used": False,
        "role_a_used": False,
        "schema_used": False,
        "historical_values_used": False,
    }
    request_sha = stream_v1.full_v3._canonical_sha256(request)  # noqa: SLF001
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
        "status": "OCR_WORD_BOX_READ_COMPLETE",
        "request": request,
        "request_sha256": request_sha,
        "source_sha256": "a" * 64,
        "source_size_bytes": 10,
        "physical_page": 1,
        "route": "DOMINANT_RASTER_OCR",
        "source_blank_claimed": False,
        "input_render_ref": {"sha256": "b" * 64},
        "backend_payload_ref": {"sha256": "c" * 64},
        "lines": [],
        "words": [],
        "safety": {
            flag: False
            for flag in stream_v1._RESULT_SAFETY_FLAGS  # noqa: SLF001
        },
    }
    payload = stream_v1.full_v3._canonical_bytes(result)  # noqa: SLF001
    record = {
        "status": result["status"],
        "route": result["route"],
        "request": request,
        "request_sha256": request_sha,
        "source_sha256": result["source_sha256"],
        "source_size_bytes": result["source_size_bytes"],
        "physical_page": result["physical_page"],
        "result_ref": {
            "sha256": sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_ref": result["input_render_ref"],
        "backend_payload_ref": result["backend_payload_ref"],
        "line_axis_count": 0,
        "word_token_count": 0,
        "quarantined_span_count": 0,
        "unresolved": False,
    }
    return record, result


def test_result_binding_accepts_neutral_exact_ocr_pair() -> None:
    record, result = _ocr_record_and_result()

    stream_v1._validate_page_result_binding(record, result)  # noqa: SLF001


def test_result_binding_rejects_role_a_or_schema_safety_crossing() -> None:
    record, result = _ocr_record_and_result()
    result["safety"]["role_a_used"] = True
    payload = stream_v1.full_v3._canonical_bytes(result)  # noqa: SLF001
    record["result_ref"] = {
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }

    with pytest.raises(stream_v1.FinalizedV3SurveyStreamError, match="safety"):
        stream_v1._validate_page_result_binding(record, result)  # noqa: SLF001


def test_production_pins_are_exactly_27_unique_content_identities() -> None:
    pins = stream_v1._FINALIZED_V3_PINS  # noqa: SLF001

    assert pins.document_ids == tuple(sorted(pins.document_ids))
    assert len(pins.document_ids) == len(set(pins.document_ids)) == 27
    assert pins.document_count == 27
    assert all(item.startswith("sha256:") and len(item) == 71 for item in pins.document_ids)
    assert pins.request_count == 1_449
    assert pins.referenced_object_count == 4_254
    assert stream_v1.FINALIZED_V3_SURVEY_AUTHORITY_V1 is pins


def test_control_authentication_delegates_clean_executor_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    marker = RuntimeError("executor validation marker")
    monkeypatch.setattr(stream_v1, "_read_pinned_json", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(stream_v1.full_v3, "_v3_load_published_control", lambda _root: {})

    def reject(_root: Path, _control: dict[str, Any]) -> None:
        raise marker

    monkeypatch.setattr(stream_v1.full_v3, "_v3_validate_published_executor", reject)

    with pytest.raises(RuntimeError, match="executor validation marker") as raised:
        stream_v1._validate_control_and_aggregate(  # noqa: SLF001
            tmp_path,
            stream_v1.FINALIZED_V3_SURVEY_AUTHORITY_V1,
        )
    assert raised.value is marker


def test_stream_exposes_immutable_authenticated_authority() -> None:
    stream = stream_v1._SingleUseSurveyStream(  # noqa: SLF001
        (),
        lambda _record: _page(0),
        authority=stream_v1._FINALIZED_V3_PINS,  # noqa: SLF001
    )

    assert stream.authority.aggregate_identity_sha256 == (
        "45eea722bb298fd0ef8b77afef141f15311705bdd8c65a2ee6e4bfd232e1ab44"
    )
    assert stream.authority.control_identity_sha256 == (
        "abec67c1e15f5cc2bc7be08abe58652eda6f855879ea7a72afce2dbcee52ac36"
    )
    with pytest.raises(AttributeError):
        stream.authority.request_count = 0  # type: ignore[misc]
