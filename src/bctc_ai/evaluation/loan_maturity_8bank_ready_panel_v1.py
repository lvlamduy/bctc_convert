"""Compose the exact eight-bank maturity LINE panel behind a live capability.

The audit projection retains source provenance.  The anonymous projection and
page accessor deliberately do not: they expose only opaque order, raster bytes,
dimensions, and ordered LINE boxes for a downstream freezer.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import weakref
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import Image

from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    AuthenticatedLinePixelHydrationReceiptV1,
    project_authenticated_line_pixel_hydration_receipt_v1,
    read_authenticated_line_pixel_hydration_envelope_v1,
    read_authenticated_line_pixel_hydration_render_v1,
    validate_authenticated_line_pixel_hydration_envelope_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import (
    BANK_ORDER,
    EXPECTED_LOCATORS,
    AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
    project_authenticated_loan_maturity_8bank_panel_selection_v1,
    replay_loan_maturity_8bank_panel_prerequisite_v1,
    validate_authenticated_loan_maturity_8bank_panel_selection_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "ANONYMOUS_BATCH_FORMAT_VERSION",
    "AUDIT_RECEIPT_FORMAT_VERSION",
    "EXPECTED_LINE_COUNT_VECTOR",
    "EXPECTED_SAMPLE_COUNT",
    "AuthenticatedLoanMaturity8BankReadyPanelV1",
    "LoanMaturity8BankReadyPanelV1Error",
    "compose_authenticated_loan_maturity_8bank_ready_panel_v1",
    "project_authenticated_loan_maturity_8bank_anonymous_batch_v1",
    "project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1",
    "read_authenticated_loan_maturity_8bank_anonymous_page_v1",
    "validate_authenticated_loan_maturity_8bank_anonymous_batch_v1",
]


class LoanMaturity8BankReadyPanelV1Error(RuntimeError):
    """The exact live READY-panel authority cannot be established."""


ANONYMOUS_BATCH_FORMAT_VERSION = "LOAN_MATURITY_8BANK_ANONYMOUS_LINE_BATCH_V1"
AUDIT_RECEIPT_FORMAT_VERSION = "LOAN_MATURITY_8BANK_READY_PANEL_AUDIT_RECEIPT_V1"
EXPECTED_LINE_COUNT_VECTOR = (85, 109, 110, 101, 91, 88, 87, 164)
EXPECTED_SAMPLE_COUNT = 835
_READY_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_PAGE_ID_RE = re.compile(r"^page-[0-9]{4}$")
_ANONYMOUS_AUTHORITY = {
    "bank_or_source_provenance_exposed": False,
    "freezer_input_authority": False,
    "geometry_only_authority": True,
    "live_capability_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "raw_projection_self_authenticates": False,
    "semantic_authority": False,
    "transcript_exposed": False,
}
_AUDIT_AUTHORITY = {
    "audit_provenance_only": True,
    "live_capability_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "raw_receipt_self_authenticates": False,
    "semantic_authority": False,
}
_ANONYMOUS_FIELDS = {
    "authority",
    "batch_id",
    "format_version",
    "line_count_vector",
    "page_count",
    "pages",
    "sample_count",
    "state",
}
_ANONYMOUS_PAGE_FIELDS = {"line_count", "page_id", "pixel_height", "pixel_width"}
_AUDIT_FIELDS = {
    "authority",
    "audit_id",
    "format_version",
    "line_count_vector",
    "manifest_sha256",
    "manifest_size_bytes",
    "panel_selection_projection",
    "sample_count",
    "slots",
}
_AUDIT_SLOT_FIELDS = {
    "bank_code",
    "geometry_authority",
    "line_count",
    "line_axis_sha256",
    "physical_page",
    "render_sha256",
    "render_size_bytes",
    "source_pdf_sha256",
}


def _error(message: str) -> LoanMaturity8BankReadyPanelV1Error:
    return LoanMaturity8BankReadyPanelV1Error(message)


def _safe_relative(value: Path | str, label: str, suffix: str) -> Path:
    if type(value) is str:
        text = value
    elif isinstance(value, Path):
        text = value.as_posix()
    else:
        raise _error(f"{label} path type is invalid")
    path = Path(text)
    if (
        not text
        or "\\" in text
        or path.is_absolute()
        or text != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix != suffix
    ):
        raise _error(f"{label} is not canonical project-relative POSIX")
    return path


def _stable_nofollow_bytes(root: Path, relative: Path | str, label: str) -> bytes:
    path = _safe_relative(relative, label, Path(relative).suffix)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current = os.open(root, directory_flags)
    descriptor: int | None = None
    try:
        for part in path.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(path.parts[-1], file_flags, dir_fd=current)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity = lambda item: (  # noqa: E731
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if identity(before) != identity(after):
            raise _error(f"{label} changed during stable read")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise _error(f"{label} stable read size drifted")
        return payload
    except OSError as exc:
        raise _error(f"cannot stably read nofollow {label}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(current)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=lambda value: (_ for _ in ()).throw(_error(f"nonfinite {value}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _error(f"cannot decode {label}") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return cast(dict[str, Any], value)


def _png_dimensions(payload: bytes, label: str) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG":
                raise _error(f"{label} is not PNG")
            image.load()
            return image.size
    except OSError as exc:
        raise _error(f"{label} is not readable PNG") from exc


def _v2_page(root: Path, slot: dict[str, Any], expected_count: int) -> tuple[dict[str, Any], bytes]:
    freezer = slot["freezer_prerequisite"]
    result_ref = freezer["result_ref"]
    render_ref = freezer["render_ref"]
    result_payload = _stable_nofollow_bytes(root, result_ref["path"], "ready result")
    render_payload = _stable_nofollow_bytes(root, render_ref["path"], "ready render")
    if (
        len(result_payload) != result_ref["size_bytes"]
        or hashlib.sha256(result_payload).hexdigest() != result_ref["sha256"]
        or len(render_payload) != render_ref["size_bytes"]
        or hashlib.sha256(render_payload).hexdigest() != render_ref["sha256"]
    ):
        raise _error("ready V2 CAS artifact hash or size drifted")
    result = _strict_json(result_payload, "ready result")
    lines = result.get("lines")
    width, height = _png_dimensions(render_payload, "ready render")
    if result.get("format_version") != _READY_RESULT_FORMAT or type(lines) is not list:
        raise _error("ready V2 page identity drifted")
    boxes: list[list[int]] = []
    for index, line in enumerate(lines):
        if type(line) is not dict:
            raise _error("ready V2 page contains a non-LINE record")
        bbox = line.get("raw_pixel_bbox")
        if (
            type(bbox) is not list
            or len(bbox) != 4
            or any(type(item) is not int for item in bbox)
            or not (0 <= bbox[0] < bbox[2] <= width and 0 <= bbox[1] < bbox[3] <= height)
        ):
            raise _error(f"ready V2 line {index} bbox drifted")
        boxes.append(list(bbox))
    if len(boxes) != expected_count or freezer["authenticated_line_count"] != expected_count:
        raise _error("ready V2 exact line denominator drifted")
    if (
        _stable_nofollow_bytes(root, result_ref["path"], "final ready result") != result_payload
        or _stable_nofollow_bytes(root, render_ref["path"], "final ready render") != render_payload
    ):
        raise _error("ready V2 CAS artifact changed during replay")
    return {
        "geometry_authority": "REPLAYED_E0044_READY_V2_CAS",
        "line_bboxes": boxes,
        "line_count": len(boxes),
        "pixel_height": height,
        "pixel_width": width,
        "render_sha256": hashlib.sha256(render_payload).hexdigest(),
        "render_size_bytes": len(render_payload),
    }, render_payload


_MINT_TOKEN = object()


class AuthenticatedLoanMaturity8BankReadyPanelV1:
    """Opaque noncopyable live authority over eight exact anonymous pages."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _MINT_TOKEN:
            raise _error("authenticated READY panel cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated READY panel cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated READY panel cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated READY panel cannot be serialized")

    def __reduce_ex__(self, _protocol: int) -> None:
        raise _error("authenticated READY panel cannot be serialized")


@dataclass(frozen=True)
class _AuthenticatedState:
    root: Path
    manifest_relative: Path
    manifest_payload: bytes
    manifest_digest: str
    panel_payload: bytes
    panel_digest: str
    selection_payload: bytes
    selection_digest: str
    audit_payload: bytes
    audit_digest: str
    page_payloads: tuple[bytes, ...]
    page_digests: tuple[str, ...]
    renders: tuple[bytes, ...]
    render_digests: tuple[str, ...]
    prerequisite_capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...]


_AUTHENTICATED: weakref.WeakKeyDictionary[
    AuthenticatedLoanMaturity8BankReadyPanelV1, _AuthenticatedState
] = weakref.WeakKeyDictionary()


def _hydrated_page(
    capability: AuthenticatedLinePixelHydrationReceiptV1,
    slot: dict[str, Any],
    expected_count: int,
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    envelope = read_authenticated_line_pixel_hydration_envelope_v1(capability)
    validate_authenticated_line_pixel_hydration_envelope_v1(envelope, capability)
    receipt = project_authenticated_line_pixel_hydration_receipt_v1(capability)
    render = read_authenticated_line_pixel_hydration_render_v1(capability)
    locator = receipt["source_locator"]
    inventory = slot["inventory_evidence"]
    expected_locator = (slot["source_pdf_sha256"], slot["physical_page"])
    actual_locator = (locator["source_pdf_sha256"], locator["physical_page"])
    expected_state = (
        inventory["result_format_version"],
        inventory["route"],
        inventory["status"],
        inventory["unresolved"],
    )
    actual_state = (
        envelope["source_state"]["result_format_version"],
        envelope["source_state"]["route"],
        envelope["source_state"]["status"],
        envelope["source_state"]["unresolved"],
    )
    upstream_result = receipt["upstream_result_ref"]
    if (
        actual_locator != expected_locator
        or actual_state != expected_state
        or receipt["emitted_line_count"] != expected_count
        or envelope["metrics"]["emitted_line_count"] != expected_count
        or upstream_result["sha256"] != inventory["result_ref"]["sha256"]
        or upstream_result["size_bytes"] != inventory["result_ref"]["size_bytes"]
        or receipt["render_ref"]["sha256"] != hashlib.sha256(render).hexdigest()
        or receipt["render_ref"]["size_bytes"] != len(render)
    ):
        raise _error("hydration capability source-locator/state/result/denominator binding drifted")
    width, height = _png_dimensions(render, "hydrated render")
    render_binding = envelope["render_binding"]
    if (
        width != render_binding["pixel_width"]
        or height != render_binding["pixel_height"]
        or hashlib.sha256(render).hexdigest() != render_binding["sha256"]
        or len(render) != render_binding["size_bytes"]
    ):
        raise _error("hydration render bytes/dimensions drifted")
    boxes = [canonical_clone_v1(line["raw_pixel_bbox"]) for line in envelope["lines"]]
    return (
        {
            "geometry_authority": "LIVE_AUTHENTICATED_LINE_PIXEL_HYDRATION_V1",
            "line_bboxes": boxes,
            "line_count": len(boxes),
            "pixel_height": height,
            "pixel_width": width,
            "render_sha256": hashlib.sha256(render).hexdigest(),
            "render_size_bytes": len(render),
        },
        render,
        receipt,
    )


def _anonymous_projection(
    pages: tuple[dict[str, Any], ...], audit: dict[str, Any]
) -> dict[str, Any]:
    projection = {
        "authority": canonical_clone_v1(_ANONYMOUS_AUTHORITY),
        "format_version": ANONYMOUS_BATCH_FORMAT_VERSION,
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": len(pages),
        "pages": [
            {
                "line_count": page["line_count"],
                "page_id": f"page-{ordinal:04d}",
                "pixel_height": page["pixel_height"],
                "pixel_width": page["pixel_width"],
            }
            for ordinal, page in enumerate(pages, start=1)
        ],
        "sample_count": sum(page["line_count"] for page in pages),
        "state": "READY_FOR_SINGLE_OPAQUE_8_PAGE_FREEZE",
    }
    projection["batch_id"] = (
        "lm8brpv1:batch:"
        + hashlib.sha256(
            canonical_json_bytes_v1(
                {
                    "anonymous_projection": projection,
                    "audit_id": audit["audit_id"],
                }
            )
        ).hexdigest()
    )
    return _validate_anonymous_shape(projection)


def _validate_anonymous_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _ANONYMOUS_FIELDS:
        raise _error("anonymous READY batch must contain the exact closed field set")
    batch = cast(dict[str, Any], value)
    batch_id = batch["batch_id"]
    if (
        batch["format_version"] != ANONYMOUS_BATCH_FORMAT_VERSION
        or batch["state"] != "READY_FOR_SINGLE_OPAQUE_8_PAGE_FREEZE"
        or not same_typed_json_v1(batch["authority"], _ANONYMOUS_AUTHORITY)
        or type(batch_id) is not str
        or not batch_id.startswith("lm8brpv1:batch:")
        or _SHA_RE.fullmatch(batch_id.removeprefix("lm8brpv1:batch:")) is None
        or type(batch["page_count"]) is not int
        or batch["page_count"] != len(BANK_ORDER)
        or not same_typed_json_v1(batch["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or type(batch["sample_count"]) is not int
        or batch["sample_count"] != EXPECTED_SAMPLE_COUNT
    ):
        raise _error("anonymous READY batch identity or denominator drifted")
    pages = batch["pages"]
    if type(pages) is not list or len(pages) != len(BANK_ORDER):
        raise _error("anonymous READY batch must contain exactly eight pages")
    for ordinal, (raw_page, count) in enumerate(
        zip(pages, EXPECTED_LINE_COUNT_VECTOR, strict=True), start=1
    ):
        if type(raw_page) is not dict or set(raw_page) != _ANONYMOUS_PAGE_FIELDS:
            raise _error("anonymous READY page field set drifted")
        page_id = raw_page["page_id"]
        if (
            page_id != f"page-{ordinal:04d}"
            or type(page_id) is not str
            or _PAGE_ID_RE.fullmatch(page_id) is None
            or type(raw_page["line_count"]) is not int
            or raw_page["line_count"] != count
            or type(raw_page["pixel_width"]) is not int
            or raw_page["pixel_width"] <= 0
            or type(raw_page["pixel_height"]) is not int
            or raw_page["pixel_height"] <= 0
        ):
            raise _error("anonymous READY page order/denominator/dimensions drifted")
    return canonical_clone_v1(batch)


def _build_audit_receipt(
    selection: dict[str, Any], audit_slots: list[dict[str, Any]]
) -> dict[str, Any]:
    receipt = {
        "authority": canonical_clone_v1(_AUDIT_AUTHORITY),
        "format_version": AUDIT_RECEIPT_FORMAT_VERSION,
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "manifest_sha256": selection["manifest_sha256"],
        "manifest_size_bytes": selection["manifest_size_bytes"],
        "panel_selection_projection": canonical_clone_v1(selection),
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "slots": canonical_clone_v1(audit_slots),
    }
    receipt["audit_id"] = "lm8brpv1:audit:" + canonical_json_sha256_v1(receipt)
    return _validate_audit_receipt(receipt)


def _validate_audit_receipt(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _AUDIT_FIELDS:
        raise _error("READY-panel audit receipt field set drifted")
    receipt = cast(dict[str, Any], value)
    audit_id = receipt["audit_id"]
    if (
        receipt["format_version"] != AUDIT_RECEIPT_FORMAT_VERSION
        or not same_typed_json_v1(receipt["authority"], _AUDIT_AUTHORITY)
        or type(audit_id) is not str
        or not audit_id.startswith("lm8brpv1:audit:")
        or _SHA_RE.fullmatch(audit_id.removeprefix("lm8brpv1:audit:")) is None
        or not same_typed_json_v1(receipt["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or receipt["sample_count"] != EXPECTED_SAMPLE_COUNT
        or receipt["audit_id"]
        != "lm8brpv1:audit:"
        + canonical_json_sha256_v1(
            {key: item for key, item in receipt.items() if key != "audit_id"}
        )
    ):
        raise _error("READY-panel audit receipt identity or denominator drifted")
    if (
        receipt["manifest_sha256"] != receipt["panel_selection_projection"]["manifest_sha256"]
        or receipt["manifest_size_bytes"]
        != receipt["panel_selection_projection"]["manifest_size_bytes"]
    ):
        raise _error("READY-panel manifest selection binding drifted")
    slots = receipt["slots"]
    if type(slots) is not list or len(slots) != len(BANK_ORDER):
        raise _error("READY-panel audit receipt must contain eight slots")
    for ordinal, (raw_slot, bank, count) in enumerate(
        zip(slots, BANK_ORDER, EXPECTED_LINE_COUNT_VECTOR, strict=True), start=1
    ):
        if type(raw_slot) is not dict or set(raw_slot) != _AUDIT_SLOT_FIELDS:
            raise _error("READY-panel audit slot fields drifted")
        page, source_sha = EXPECTED_LOCATORS[bank]
        if (
            raw_slot["bank_code"] != bank
            or raw_slot["physical_page"] != page
            or raw_slot["source_pdf_sha256"] != source_sha
            or raw_slot["line_count"] != count
            or raw_slot["geometry_authority"]
            not in {
                "REPLAYED_E0044_READY_V2_CAS",
                "LIVE_AUTHENTICATED_LINE_PIXEL_HYDRATION_V1",
            }
        ):
            raise _error(f"READY-panel audit slot {ordinal} provenance drifted")
        for field in ("line_axis_sha256", "render_sha256"):
            if type(raw_slot[field]) is not str or _SHA_RE.fullmatch(raw_slot[field]) is None:
                raise _error("READY-panel audit hash identity drifted")
        if type(raw_slot["render_size_bytes"]) is not int or raw_slot["render_size_bytes"] <= 0:
            raise _error("READY-panel audit render size drifted")
    return canonical_clone_v1(receipt)


def _hydration_key_from_receipt_and_envelope(
    receipt: dict[str, Any], envelope: dict[str, Any]
) -> tuple[Any, ...]:
    locator = receipt["source_locator"]
    source_binding = envelope["source_binding"]
    source_state = envelope["source_state"]
    if (
        locator["source_pdf_sha256"] != source_binding["source_pdf_sha256"]
        or locator["physical_page"] != source_binding["physical_page"]
        or locator["source_size_bytes"] != source_binding["source_size_bytes"]
    ):
        raise _error("hydration receipt/envelope source locator drifted")
    return (
        locator["source_pdf_sha256"],
        locator["physical_page"],
        source_state["result_format_version"],
        source_state["route"],
        source_state["status"],
        source_state["unresolved"],
    )


def _expected_hydration_key(slot: dict[str, Any]) -> tuple[Any, ...]:
    inventory = slot["inventory_evidence"]
    return (
        slot["source_pdf_sha256"],
        slot["physical_page"],
        inventory["result_format_version"],
        inventory["route"],
        inventory["status"],
        inventory["unresolved"],
    )


def _hydration_capabilities_by_source_state(
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
) -> dict[tuple[Any, ...], AuthenticatedLinePixelHydrationReceiptV1]:
    if type(hydration_capabilities) is not tuple or len(hydration_capabilities) != 2:
        raise _error("READY panel requires one exact tuple of two live hydration capabilities")
    keyed: dict[tuple[Any, ...], AuthenticatedLinePixelHydrationReceiptV1] = {}
    seen_capabilities: set[int] = set()
    for capability in hydration_capabilities:
        if type(capability) is not AuthenticatedLinePixelHydrationReceiptV1:
            raise _error("READY panel received a raw, forged, or wrong hydration authority")
        if id(capability) in seen_capabilities:
            raise _error("READY panel received a duplicate hydration capability")
        seen_capabilities.add(id(capability))
        envelope = read_authenticated_line_pixel_hydration_envelope_v1(capability)
        validate_authenticated_line_pixel_hydration_envelope_v1(envelope, capability)
        receipt = project_authenticated_line_pixel_hydration_receipt_v1(capability)
        render = read_authenticated_line_pixel_hydration_render_v1(capability)
        if receipt["render_ref"]["sha256"] != hashlib.sha256(render).hexdigest() or receipt[
            "render_ref"
        ]["size_bytes"] != len(render):
            raise _error("hydration receipt/render live binding drifted")
        key = _hydration_key_from_receipt_and_envelope(receipt, envelope)
        if key in keyed:
            raise _error("READY panel received duplicate source-locator/state hydration")
        keyed[key] = capability
    return keyed


def _assemble_pages(
    root: Path,
    panel: dict[str, Any],
    selection: dict[str, Any],
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
) -> tuple[tuple[dict[str, Any], ...], tuple[bytes, ...], dict[str, Any]]:
    keyed_hydrations = _hydration_capabilities_by_source_state(hydration_capabilities)
    expected_hydration_keys = {
        _expected_hydration_key(slot)
        for slot in panel["slots"]
        if slot["freezer_prerequisite"]["state"] != "READY_FOR_OPAQUE_ALL_LINE_FREEZE"
    }
    if set(keyed_hydrations) != expected_hydration_keys or len(expected_hydration_keys) != 2:
        raise _error("hydration capabilities do not exactly cover blocked source-locator/states")

    pages: list[dict[str, Any]] = []
    renders: list[bytes] = []
    audit_slots: list[dict[str, Any]] = []
    for slot, expected_count in zip(panel["slots"], EXPECTED_LINE_COUNT_VECTOR, strict=True):
        if slot["freezer_prerequisite"]["state"] == "READY_FOR_OPAQUE_ALL_LINE_FREEZE":
            page, render = _v2_page(root, slot, expected_count)
        else:
            key = _expected_hydration_key(slot)
            page, render, _receipt = _hydrated_page(keyed_hydrations[key], slot, expected_count)
        pages.append(page)
        renders.append(render)
        audit_slots.append(
            {
                "bank_code": slot["bank_code"],
                "geometry_authority": page["geometry_authority"],
                "line_count": page["line_count"],
                "line_axis_sha256": canonical_json_sha256_v1(page["line_bboxes"]),
                "physical_page": slot["physical_page"],
                "render_sha256": page["render_sha256"],
                "render_size_bytes": page["render_size_bytes"],
                "source_pdf_sha256": slot["source_pdf_sha256"],
            }
        )
    if [page["line_count"] for page in pages] != list(EXPECTED_LINE_COUNT_VECTOR) or sum(
        page["line_count"] for page in pages
    ) != EXPECTED_SAMPLE_COUNT:
        raise _error("READY panel exact eight-page/835-LINE denominator drifted")
    audit = _build_audit_receipt(selection, audit_slots)
    return tuple(pages), tuple(renders), audit


def compose_authenticated_loan_maturity_8bank_ready_panel_v1(
    project_root: Path,
    manifest_path: Path,
    prerequisite_capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
) -> tuple[dict[str, Any], AuthenticatedLoanMaturity8BankReadyPanelV1]:
    """Compose the formal panel only from the replayed prerequisite and two live adapters."""

    if not isinstance(project_root, Path) or not isinstance(manifest_path, Path):
        raise _error("READY-panel project root and manifest must be pathlib Paths")
    if type(prerequisite_capability) is not AuthenticatedLoanMaturity8BankPanelPrerequisiteV1:
        raise _error("READY panel requires one exact live prerequisite capability")
    try:
        root = project_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _error("READY-panel project root cannot be resolved") from exc
    if not root.is_dir():
        raise _error("READY-panel project root is not a directory")
    manifest_relative = _safe_relative(manifest_path, "READY-panel manifest", ".json")
    manifest_payload = _stable_nofollow_bytes(root, manifest_relative, "READY-panel manifest")

    # Replay the exact current manifest/CAS authority independently, then bind
    # that replay to the caller's already-live prerequisite capability.
    panel, replayed_capability = replay_loan_maturity_8bank_panel_prerequisite_v1(
        root, manifest_relative
    )
    selection = project_authenticated_loan_maturity_8bank_panel_selection_v1(
        prerequisite_capability
    )
    validate_authenticated_loan_maturity_8bank_panel_selection_v1(selection, replayed_capability)
    validate_authenticated_loan_maturity_8bank_panel_selection_v1(
        selection, prerequisite_capability
    )
    if selection["manifest_sha256"] != hashlib.sha256(manifest_payload).hexdigest() or selection[
        "manifest_size_bytes"
    ] != len(manifest_payload):
        raise _error("live prerequisite capability does not bind the supplied manifest bytes")

    pages, renders, audit = _assemble_pages(root, panel, selection, hydration_capabilities)
    page_payloads = tuple(canonical_json_bytes_v1(page) for page in pages)
    audit_payload = canonical_json_bytes_v1(audit)
    panel_payload = canonical_json_bytes_v1(panel)
    selection_payload = canonical_json_bytes_v1(selection)
    capability = AuthenticatedLoanMaturity8BankReadyPanelV1(_MINT_TOKEN)
    _AUTHENTICATED[capability] = _AuthenticatedState(
        root=root,
        manifest_relative=manifest_relative,
        manifest_payload=bytes(manifest_payload),
        manifest_digest=hashlib.sha256(manifest_payload).hexdigest(),
        panel_payload=panel_payload,
        panel_digest=hashlib.sha256(panel_payload).hexdigest(),
        selection_payload=selection_payload,
        selection_digest=hashlib.sha256(selection_payload).hexdigest(),
        audit_payload=audit_payload,
        audit_digest=hashlib.sha256(audit_payload).hexdigest(),
        page_payloads=page_payloads,
        page_digests=tuple(hashlib.sha256(item).hexdigest() for item in page_payloads),
        renders=tuple(bytes(item) for item in renders),
        render_digests=tuple(hashlib.sha256(item).hexdigest() for item in renders),
        prerequisite_capability=prerequisite_capability,
        hydration_capabilities=hydration_capabilities,
    )
    # Exercise the complete live replay boundary before returning authority.
    projected = project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1(capability)
    if not same_typed_json_v1(projected, audit):
        raise _error("newly composed READY-panel audit identity drifted")
    return audit, capability


def _authenticated_state(
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[tuple[dict[str, Any], ...], tuple[bytes, ...], dict[str, Any]]:
    if type(capability) is not AuthenticatedLoanMaturity8BankReadyPanelV1:
        raise _error("READY-panel authority requires one exact live opaque capability")
    state = _AUTHENTICATED.get(capability)
    if state is None:
        raise _error("authenticated READY-panel capability is unknown or expired")
    if (
        hashlib.sha256(state.manifest_payload).hexdigest() != state.manifest_digest
        or hashlib.sha256(state.panel_payload).hexdigest() != state.panel_digest
        or hashlib.sha256(state.selection_payload).hexdigest() != state.selection_digest
        or hashlib.sha256(state.audit_payload).hexdigest() != state.audit_digest
        or tuple(hashlib.sha256(item).hexdigest() for item in state.page_payloads)
        != state.page_digests
        or tuple(hashlib.sha256(item).hexdigest() for item in state.renders) != state.render_digests
    ):
        raise _error("authenticated READY-panel in-memory bytes drifted")
    if (
        _stable_nofollow_bytes(state.root, state.manifest_relative, "live READY-panel manifest")
        != state.manifest_payload
    ):
        raise _error("authenticated READY-panel manifest changed after composition")

    try:
        panel = cast(dict[str, Any], decode_canonical_json_bytes_v1(state.panel_payload))
        selection = cast(dict[str, Any], decode_canonical_json_bytes_v1(state.selection_payload))
        stored_audit = _validate_audit_receipt(decode_canonical_json_bytes_v1(state.audit_payload))
        stored_pages = tuple(
            cast(dict[str, Any], decode_canonical_json_bytes_v1(payload))
            for payload in state.page_payloads
        )
    except (TypeError, ValueError) as exc:
        raise _error("authenticated READY-panel canonical bytes cannot be decoded") from exc

    validate_authenticated_loan_maturity_8bank_panel_selection_v1(
        selection, state.prerequisite_capability
    )
    replayed_panel, replayed_capability = replay_loan_maturity_8bank_panel_prerequisite_v1(
        state.root, state.manifest_relative
    )
    validate_authenticated_loan_maturity_8bank_panel_selection_v1(selection, replayed_capability)
    if not same_typed_json_v1(panel, replayed_panel):
        raise _error("authenticated READY-panel prerequisite snapshot drifted")

    pages, renders, audit = _assemble_pages(
        state.root,
        panel,
        selection,
        state.hydration_capabilities,
    )
    if (
        not same_typed_json_v1(list(pages), list(stored_pages))
        or renders != state.renders
        or not same_typed_json_v1(audit, stored_audit)
    ):
        raise _error("authenticated READY-panel live child authority drifted")
    return pages, renders, audit


def project_authenticated_loan_maturity_8bank_anonymous_batch_v1(
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> dict[str, Any]:
    """Project only anonymous page IDs, dimensions, and exact denominators."""

    pages, _renders, audit = _authenticated_state(capability)
    return _anonymous_projection(pages, audit)


def validate_authenticated_loan_maturity_8bank_anonymous_batch_v1(
    value: Any,
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> dict[str, Any]:
    """Bind an anonymous descriptive projection to its live READY capability."""

    candidate = _validate_anonymous_shape(value)
    expected = project_authenticated_loan_maturity_8bank_anonymous_batch_v1(capability)
    if not same_typed_json_v1(candidate, expected):
        raise _error("anonymous READY batch differs from its live capability")
    return candidate


def project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1(
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> dict[str, Any]:
    """Project provenance for audit; the returned dict grants no authority."""

    _pages, _renders, audit = _authenticated_state(capability)
    return canonical_clone_v1(audit)


def read_authenticated_loan_maturity_8bank_anonymous_page_v1(
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
    page_ordinal: int,
) -> dict[str, Any]:
    """Read one anonymous page's pixels and ordered bboxes from live authority."""

    if type(page_ordinal) is not int or not 1 <= page_ordinal <= len(BANK_ORDER):
        raise _error("anonymous page ordinal must be one integer from 1 through 8")
    pages, renders, _audit = _authenticated_state(capability)
    page = pages[page_ordinal - 1]
    page_id = f"page-{page_ordinal:04d}"
    return {
        "line_bboxes": canonical_clone_v1(page["line_bboxes"]),
        "line_count": page["line_count"],
        "page_id": page_id,
        "page_ordinal": page_ordinal,
        "pixel_height": page["pixel_height"],
        "pixel_width": page["pixel_width"],
        "render_png_bytes": bytes(renders[page_ordinal - 1]),
    }
