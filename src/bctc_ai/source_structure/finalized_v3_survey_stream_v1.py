"""Read the one finalized Wave-1 V3 authority as a bounded survey stream.

This adapter does not discover a corpus and does not open source PDFs. It is
deliberately pinned to the finalized 27-document/1,449-request V3 artifact. A
successful context authenticates its aggregate, control, document indexes,
page records, and complete CAS inventory while holding the V3 read-only
snapshot. Each page result is then read from that bound CAS generation.

The stream is single use and must be consumed completely. Native backend
payloads are validated inside the adapter and are never exposed to callers.
"""

from __future__ import annotations

import stat
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.corpus import wave1_role_b_full_reader_v3 as full_v3

__all__ = [
    "AuthenticatedV3SurveyPage",
    "FINALIZED_V3_SURVEY_AUTHORITY_V1",
    "FinalizedV3SurveyAuthority",
    "FinalizedV3SurveyStreamError",
    "open_finalized_v3_survey_stream_v1",
]


class FinalizedV3SurveyStreamError(RuntimeError):
    """The pinned V3 authority cannot safely supply a complete survey stream."""


@dataclass(frozen=True)
class AuthenticatedV3SurveyPage:
    """One exact V3 record/result pair; no native backend is exposed."""

    page_record: dict[str, Any]
    page_result: dict[str, Any]


@dataclass(frozen=True)
class FinalizedV3SurveyAuthority:
    """Immutable public identity/count receipt for the only admitted V3 corpus."""

    aggregate_artifact_sha256: str
    aggregate_size_bytes: int
    aggregate_identity_sha256: str
    control_artifact_sha256: str
    control_size_bytes: int
    control_identity_sha256: str
    sealed_plan_sha256: str
    document_ids: tuple[str, ...]
    document_count: int
    request_count: int
    referenced_object_count: int


# Retain the private type name for the already-frozen authentication helpers.
_FinalizedV3Pins = FinalizedV3SurveyAuthority


_DOCUMENT_IDS = (
    "sha256:031a48ab510b901bef9b418fd70f6b10bc4c98d846f242d30b324d21ac9fd604",
    "sha256:221e11e2fa500543df6aa4f7e2cf3c58465596accd1e58827225ad6ab70bf7c5",
    "sha256:30bb8394f9fb62750250700d4dd7ef0e8e60a4e938f4561458ccdbf7964b7ff9",
    "sha256:36160cdcecbd2382d1501ee3a65ab5a33f75f413c06a39858d8a49f4b4c93023",
    "sha256:3a66122194e4dd2e0ca18d584beeacb81279cf71e276eface59d17e72813dcfd",
    "sha256:416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c",
    "sha256:47d3b2d6b5a4ab6855ad1568127928204e7097f490748c07274e2ed9704f5fe3",
    "sha256:50b860c97df7b69869530ce73f3a55a980f166745ed11bbab3e61ab31d38915f",
    "sha256:57bc956a4b2358d4a8f79998e88f00f7c0987c2a3b3e5b03e03d813763ee4ead",
    "sha256:614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde",
    "sha256:65f4e0c533607919a7fec4af0f3eb46942c781c86eae4eb6ebef7697dbf5ff88",
    "sha256:73d9ead38e4e60b2241ae7d41a6e5382f8f2e5cc59f2e7a70ca0bedb95792003",
    "sha256:7fa4a8ff1ae6f7c03a8f8bbd881afa3929d8ff5730f5eb5ef0780ddf08695958",
    "sha256:7fd70735610eecb95add47b7a3d77af4cf2c1c37cd81dd956ebb0d12cfde0cc7",
    "sha256:86f53ef458dcacfcdc83c148964b5d281308975f1eae154b515ae308be9eccb1",
    "sha256:97bbb69be33f7aa7c3d3ce81bca6737b275bbcf3d6082190bb764a08370d38f3",
    "sha256:9b2b1c3b4bf6f90c941508189c4498e812e5197785ad8cc9884637c141edee8e",
    "sha256:a86757a4499953264ca22dd57ae2e3257057631107742e1d04ad1ecd0e2c23d1",
    "sha256:b50173a5c871d979f1cdcb42bcb8f3bb1860a27afe9b72bfa90f3edca1f07ff0",
    "sha256:c707a7d3ac856d180d0cadaeb084150f5dbd9217d5c1c4f356088891a8e594f3",
    "sha256:dae87ce9d04a135515dc0211591b21f44d3421eaeccd8258122bfeef3fe5877f",
    "sha256:db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86",
    "sha256:f487e84717165912dda50f64dc8fe2ec580ffc1a5bfb25f072513c39a9c4444e",
    "sha256:f48d1f9c7f50794919f0c77bf7acbdab7d5d0106e56741555affd783ddeb1fb6",
    "sha256:f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318",
    "sha256:fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223",
    "sha256:fed898a015c903208b68e586b958647c0245cc98111fe09ac782b9db1c32f78d",
)

FINALIZED_V3_SURVEY_AUTHORITY_V1 = FinalizedV3SurveyAuthority(
    aggregate_artifact_sha256=("b2b41986d4e534a3afe4799fb00462854e66f76b61e23cb36090c98aab53f0b3"),
    aggregate_size_bytes=6_796_775,
    aggregate_identity_sha256=("45eea722bb298fd0ef8b77afef141f15311705bdd8c65a2ee6e4bfd232e1ab44"),
    control_artifact_sha256=("4d8e3206e6518c2e61104aa9cda6bcea310211fa2e5bec39c38b919abe4536e8"),
    control_size_bytes=2_401_205,
    control_identity_sha256=("abec67c1e15f5cc2bc7be08abe58652eda6f855879ea7a72afce2dbcee52ac36"),
    sealed_plan_sha256=("d056323fde832ec2865ef5ac28a3fb045537ef6ecf3c505a7b5b0bbb68ad29c3"),
    document_ids=_DOCUMENT_IDS,
    document_count=27,
    request_count=1_449,
    referenced_object_count=4_254,
)
_FINALIZED_V3_PINS = FINALIZED_V3_SURVEY_AUTHORITY_V1


@dataclass(frozen=True)
class _AuthenticatedAuthority:
    control: dict[str, Any]
    page_records: tuple[dict[str, Any], ...]


_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_OCR_RESULT_FORMATS = {
    "OCR_WORD_BOX_READ_COMPLETE": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY": ("BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"),
}
_NATIVE_RESULT_FORMATS = {
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE": (
        "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
    ),
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": (
        "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
    ),
}
_ZERO_INTERPRETATION_FIELDS = (
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
)
_REQUEST_PROVENANCE_FLAGS = (
    "bank_identity_used",
    "filename_used",
    "role_a_used",
    "schema_used",
    "historical_values_used",
)
_RESULT_SAFETY_FLAGS = (
    "absence_claimed",
    "bank_registry_metadata_used",
    "filename_metadata_used",
    "historical_values_used",
    "mapping_used",
    "role_a_used",
    "schema_used",
    "statement_classified",
    "table_classified",
    "rows_reconstructed",
    "cells_interpreted",
)


def _fail(message: str) -> FinalizedV3SurveyStreamError:
    return FinalizedV3SurveyStreamError(message)


def _read_pinned_json(
    path: Path,
    *,
    label: str,
    expected_sha256: str,
    expected_size_bytes: int,
) -> dict[str, Any]:
    payload, identity = full_v3._v3_read_nofollow(path, label)  # noqa: SLF001
    if (
        stat.S_IMODE(identity.st_mode) != 0o444
        or identity.st_nlink != 1
        or len(payload) != expected_size_bytes
        or sha256(payload).hexdigest() != expected_sha256
    ):
        raise _fail(f"{label} differs from its finalized artifact pin")
    value = full_v3._json_object(payload, label)  # noqa: SLF001
    if payload != full_v3._canonical_bytes(value):  # noqa: SLF001
        raise _fail(f"{label} is not its canonical JSON representation")
    return value


def _validate_control_and_aggregate(
    project_root: Path,
    pins: _FinalizedV3Pins,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output_root = project_root / full_v3.OUTPUT_RELATIVE_ROOT
    observed_control = _read_pinned_json(
        output_root / "full-reader-execution-control.json",
        label="finalized V3 control",
        expected_sha256=pins.control_artifact_sha256,
        expected_size_bytes=pins.control_size_bytes,
    )
    control = full_v3._v3_load_published_control(project_root)  # noqa: SLF001
    full_v3._v3_validate_published_executor(project_root, control)  # noqa: SLF001
    if (
        not full_v3._same_typed_json(control, observed_control)  # noqa: SLF001
        or control.get("control_identity_sha256") != pins.control_identity_sha256
        or control.get("sealed_plan", {}).get("sha256") != pins.sealed_plan_sha256
    ):
        raise _fail("finalized V3 control authority drifted")

    aggregate = _read_pinned_json(
        output_root / "full-reader-aggregate.json",
        label="finalized V3 aggregate",
        expected_sha256=pins.aggregate_artifact_sha256,
        expected_size_bytes=pins.aggregate_size_bytes,
    )
    logical = aggregate.get("aggregate_identity_sha256")
    logical_payload = {
        key: value for key, value in aggregate.items() if key != "aggregate_identity_sha256"
    }
    if (
        aggregate.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V2"
        or aggregate.get("status")
        != "COMPLETE_WAVE_1_PAGE_REQUEST_ACCOUNTING_WITH_UNRESOLVED_READS"
        or logical != pins.aggregate_identity_sha256
        or full_v3._canonical_sha256(logical_payload) != logical  # noqa: SLF001
        or not full_v3._same_typed_json(  # noqa: SLF001
            aggregate.get("sealed_plan"), control.get("sealed_plan")
        )
        or aggregate.get("claim_boundary") != control.get("claim_boundary")
        or aggregate.get("control")
        != {
            "identity_sha256": pins.control_identity_sha256,
            "artifact": {
                "path": "full-reader-execution-control.json",
                "sha256": pins.control_artifact_sha256,
                "size_bytes": pins.control_size_bytes,
            },
        }
    ):
        raise _fail("finalized V3 aggregate authority drifted")
    return control, aggregate


def _validate_record_denominator(
    control: dict[str, Any],
    aggregate: dict[str, Any],
    pins: _FinalizedV3Pins,
) -> list[dict[str, Any]]:
    records = aggregate.get("page_records")
    indexes = aggregate.get("document_indexes")
    accounting = aggregate.get("accounting")
    if (
        type(records) is not list
        or type(indexes) is not list
        or type(accounting) is not dict
        or len(records) != pins.request_count
        or len(indexes) != len(pins.document_ids)
        or accounting.get("document_count") != len(pins.document_ids)
        or accounting.get("request_count") != pins.request_count
        or accounting.get("source_accounted_page_count") != pins.request_count
        or accounting.get("referenced_object_count") != pins.referenced_object_count
        or accounting.get("unique_object_count") != pins.referenced_object_count
        or accounting.get("ocr_page_count") != 1_356
        or accounting.get("native_page_count") != 93
        or accounting.get("terminal_unresolved_page_count") != 59
        or any(accounting.get(field) != 0 for field in _ZERO_INTERPRETATION_FIELDS)
    ):
        raise _fail("finalized V3 denominator or claim boundary drifted")

    control_documents = control.get("documents")
    if type(control_documents) is not list:
        raise _fail("finalized V3 control document axis drifted")
    control_document_ids = tuple(sorted(item.get("document_id") for item in control_documents))
    if control_document_ids != pins.document_ids:
        raise _fail("finalized V3 control document set drifted")
    expected_by_request = full_v3._v3_control_index(control)  # noqa: SLF001

    request_ids: set[str] = set()
    result_paths: set[str] = set()
    observed_document_ids: set[str] = set()
    for ordinal, record in enumerate(records, start=1):
        if type(record) is not dict:
            raise _fail("finalized V3 page record axis contains a non-object")
        request_sha = record.get("request_sha256")
        expected = expected_by_request.get(request_sha)
        request = record.get("request")
        if (
            record.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2"
            or record.get("request_ordinal") != ordinal
            or expected is None
            or request_sha in request_ids
            or type(request) is not dict
            or full_v3._canonical_sha256(request) != request_sha  # noqa: SLF001
            or any(request.get(flag) is not False for flag in _REQUEST_PROVENANCE_FLAGS)
            or any(record.get(field) != 0 for field in _ZERO_INTERPRETATION_FIELDS)
        ):
            raise _fail("finalized V3 page record identity or safety drifted")
        for field in (
            "request_ordinal",
            "document_id",
            "source_sha256",
            "source_size_bytes",
            "physical_page",
            "route",
            "request_sha256",
            "request",
        ):
            if not full_v3._same_typed_json(record.get(field), expected.get(field)):  # noqa: SLF001
                raise _fail("finalized V3 page record/control binding drifted")
        document_id = record.get("document_id")
        result_ref = record.get("result_ref")
        if (
            document_id not in pins.document_ids
            or record.get("source_sha256") != document_id.removeprefix("sha256:")
            or type(result_ref) is not dict
            or type(result_ref.get("path")) is not str
            or result_ref["path"] in result_paths
            or type(record.get("unresolved")) is not bool
            or record.get("line_axis_count")
            != record.get("nonempty_line_axis_count", -1)
            + record.get("exact_empty_line_axis_count", -1)
            or record.get("accepted_line_count") != record.get("nonempty_line_axis_count")
        ):
            raise _fail("finalized V3 page record accounting drifted")
        request_ids.add(request_sha)
        result_paths.add(result_ref["path"])
        observed_document_ids.add(document_id)
    if (
        request_ids != set(expected_by_request)
        or observed_document_ids != set(pins.document_ids)
        or len(result_paths) != pins.request_count
    ):
        raise _fail("finalized V3 request/document coverage drifted")

    route_counts = Counter(record["route"] for record in records)
    status_counts = Counter(record["status"] for record in records)
    if route_counts != {_OCR_ROUTE: 1_356, _NATIVE_ROUTE: 93} or status_counts != {
        "OCR_WORD_BOX_READ_COMPLETE": 1_299,
        "UNRESOLVED_OCR_WORD_BOX_GEOMETRY": 57,
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE": 91,
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": 2,
    }:
        raise _fail("finalized V3 route/status partition drifted")
    return records


def _validate_document_indexes(
    project_root: Path,
    control: dict[str, Any],
    aggregate: dict[str, Any],
    records: list[dict[str, Any]],
    pins: _FinalizedV3Pins,
) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["document_id"]].append(record)
    references = aggregate["document_indexes"]
    if tuple(item.get("document_id") for item in references) != pins.document_ids:
        raise _fail("finalized V3 document-index order/set drifted")
    observed_records: list[dict[str, Any]] = []
    for reference in references:
        document_id = reference["document_id"]
        index = full_v3._v3_read_document_index(project_root, reference)  # noqa: SLF001
        head = index.get("final_checkpoint_sha256")
        if type(head) is not str:
            raise _fail("finalized V3 document index lacks its checkpoint head")
        document_by_request = {record["request_sha256"]: record for record in grouped[document_id]}
        completion_records = [
            document_by_request[request_sha]
            for request_sha in full_v3._v3_document_completion_order(  # noqa: SLF001
                control, document_id
            )
        ]
        expected = full_v3._v3_document_index_payload(  # noqa: SLF001
            control,
            document_id,
            completion_records,
            head,
        )
        if not full_v3._same_typed_json(index, expected):  # noqa: SLF001
            raise _fail("finalized V3 document index/page-record binding drifted")
        observed_records.extend(index["page_records"])
    observed_records.sort(key=lambda item: item["request_ordinal"])
    if not full_v3._same_typed_json(observed_records, records):  # noqa: SLF001
        raise _fail("finalized V3 document indexes do not exactly cover the aggregate")


def _authenticate_finalized_authority(
    project_root: Path,
    pins: _FinalizedV3Pins,
) -> _AuthenticatedAuthority:
    control, aggregate = _validate_control_and_aggregate(project_root, pins)
    records = _validate_record_denominator(control, aggregate, pins)
    _validate_document_indexes(project_root, control, aggregate, records, pins)
    inventory = full_v3._v3_output_inventory(  # noqa: SLF001
        project_root,
        records,
        aggregate_allowed=True,
    )
    if inventory != {
        "referenced_object_count": pins.referenced_object_count,
        "unique_object_count": pins.referenced_object_count,
    }:
        raise _fail("finalized V3 exact object inventory drifted")
    return _AuthenticatedAuthority(
        control=control,
        page_records=tuple(records),
    )


def _validate_page_result_binding(
    record: dict[str, Any],
    result: dict[str, Any],
) -> None:
    request = record["request"]
    route = record["route"]
    expected_formats = _OCR_RESULT_FORMATS if route == _OCR_ROUTE else _NATIVE_RESULT_FORMATS
    expected_format = expected_formats.get(record["status"])
    result_ref = record["result_ref"]
    canonical_result = full_v3._canonical_bytes(result)  # noqa: SLF001
    if (
        expected_format is None
        or result.get("format_version") != expected_format
        or result.get("status") != record["status"]
        or not full_v3._same_typed_json(result.get("request"), request)  # noqa: SLF001
        or len(canonical_result) != result_ref["size_bytes"]
        or sha256(canonical_result).hexdigest() != result_ref["sha256"]
    ):
        raise _fail("finalized V3 page result identity/status drifted")
    for field in (
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
    ):
        if not full_v3._same_typed_json(result.get(field), record[field]):  # noqa: SLF001
            raise _fail("finalized V3 page result/record binding drifted")
    safety = result.get("safety")
    lines = result.get("lines")
    words = result.get("words")
    if (
        type(safety) is not dict
        or any(safety.get(flag) is not False for flag in _RESULT_SAFETY_FLAGS)
        or result.get("source_blank_claimed") is not False
        or type(lines) is not list
        or type(words) is not list
        or len(lines) != record["line_axis_count"]
        or len(words) != record["word_token_count"]
        or record["unresolved"]
        != (
            record["status"]
            in {
                "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
                "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
            }
        )
    ):
        raise _fail("finalized V3 page result accounting/safety drifted")
    if route == _OCR_ROUTE:
        if (
            not full_v3._same_typed_json(  # noqa: SLF001
                result.get("input_render_ref"), record["render_ref"]
            )
            or not full_v3._same_typed_json(  # noqa: SLF001
                result.get("backend_payload_ref"), record["backend_payload_ref"]
            )
            or record["quarantined_span_count"] != 0
        ):
            raise _fail("finalized V3 OCR result reference binding drifted")
    else:
        if (
            record["render_ref"] is not None
            or result.get("document_id") != record["document_id"]
            or result.get("backend_payload_sha256") != record["backend_payload_ref"]["sha256"]
            or type(result.get("quarantined_spans")) is not list
            or len(result["quarantined_spans"]) != record["quarantined_span_count"]
        ):
            raise _fail("finalized V3 native result reference binding drifted")


def _load_authenticated_page(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
) -> AuthenticatedV3SurveyPage:
    if record["route"] == _NATIVE_ROUTE:
        _backend, result = full_v3._v3_validate_native_page_record_shape(  # noqa: SLF001
            project_root,
            control,
            record,
        )
        del _backend
    elif record["route"] == _OCR_ROUTE:
        payload, _identity = full_v3._v3_read_object(  # noqa: SLF001
            project_root,
            record["result_ref"],
            ".json",
            "finalized V3 OCR survey result",
        )
        result = full_v3._json_object(payload, "finalized V3 OCR survey result")  # noqa: SLF001
    else:  # The aggregate validator closes this branch; retain fail-closed locality.
        raise _fail("finalized V3 survey page route drifted")
    _validate_page_result_binding(record, result)
    return AuthenticatedV3SurveyPage(
        page_record=deepcopy(record),
        page_result=result,
    )


class _SingleUseSurveyStream:
    def __init__(
        self,
        records: tuple[dict[str, Any], ...],
        loader: Callable[[dict[str, Any]], AuthenticatedV3SurveyPage],
        *,
        authority: FinalizedV3SurveyAuthority,
    ) -> None:
        self._records = records
        self._loader = loader
        self._authority = authority
        self._started = False
        self._closed = False
        self._delivered = 0

    @property
    def exhausted(self) -> bool:
        return self._delivered == len(self._records)

    @property
    def authority(self) -> FinalizedV3SurveyAuthority:
        """Return the immutable authority authenticated before stream delivery."""

        return self._authority

    @property
    def delivered_count(self) -> int:
        return self._delivered

    def close(self) -> None:
        self._closed = True

    def __iter__(self) -> Iterator[AuthenticatedV3SurveyPage]:
        if self._closed:
            raise _fail("finalized V3 survey stream is closed")
        if self._started:
            raise _fail("finalized V3 survey stream is single-use")
        self._started = True
        return self._consume()

    def _consume(self) -> Iterator[AuthenticatedV3SurveyPage]:
        while self._delivered < len(self._records):
            if self._closed:
                raise _fail("finalized V3 survey stream closed during consumption")
            page = self._loader(self._records[self._delivered])
            self._delivered += 1
            yield page


@contextmanager
def _open_pinned_stream(
    project_root: Path,
    pins: _FinalizedV3Pins,
) -> Iterator[_SingleUseSurveyStream]:
    project_root = project_root.resolve()
    stream: _SingleUseSurveyStream | None = None
    with full_v3._v3_read_only_output_snapshot(  # noqa: SLF001
        project_root,
        list(pins.document_ids),
    ):
        manifest_before = full_v3._v3_output_live_manifest(project_root)  # noqa: SLF001
        try:
            with full_v3._v3_bind_output_reads(project_root, manifest_before):  # noqa: SLF001
                authority = _authenticate_finalized_authority(project_root, pins)
                stream = _SingleUseSurveyStream(
                    authority.page_records,
                    lambda record: _load_authenticated_page(
                        project_root,
                        authority.control,
                        record,
                    ),
                    authority=pins,
                )
                yield stream
        finally:
            active_error = sys.exc_info()[1]
            if stream is not None:
                stream.close()
            manifest_after = full_v3._v3_output_live_manifest(project_root)  # noqa: SLF001
            if not full_v3._same_typed_json(manifest_after, manifest_before):  # noqa: SLF001
                raise _fail("finalized V3 output changed while supplying survey evidence") from (
                    active_error
                )
            if stream is not None and not stream.exhausted:
                raise _fail(
                    "finalized V3 survey stream was only partially consumed "
                    f"({stream.delivered_count}/{len(authority.page_records)})"
                ) from active_error


def open_finalized_v3_survey_stream_v1(
    project_root: Path,
) -> AbstractContextManager[_SingleUseSurveyStream]:
    """Open the exact finalized V3 authority; every one of 1,449 pages is required.

    ``project_root`` only locates the fixed project authority. No bank, filing,
    page path, filename, Role-A result, schema, source PDF, or model cache is an
    input to this adapter.
    """

    return _open_pinned_stream(project_root, _FINALIZED_V3_PINS)
