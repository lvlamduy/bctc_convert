"""Bind one exact V2 source page to the authenticated VietOCR V3 run.

This experiment adapter carries no bank-specific routing rule.  It locates a
page only by the exact ``(source_sha256, physical_page)`` pair already present
in the live READY-panel lineage.  Ordinary OCR pages use their primary V2 LINE
atoms; a hydrated native page retains its primary native LINE atoms; and a
terminal OCR page remains explicitly unresolved while exposing only typed,
coarse supplemental line correspondence for audit.

The returned capability is live and opaque.  Every accessor replays the READY
panel, freeze, selected semantic receipt, and any required hydration receipt.
The projected dictionary is descriptive and never self-authenticates.
"""

from __future__ import annotations

import hashlib
import math
import pickle
import re
import unicodedata
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from bctc_ai.evaluation import loan_maturity_8bank_ready_panel_v1 as ready_v1
from bctc_ai.evaluation import vietocr_all_line_freezer_v3 as freezer_v3
from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    AuthenticatedLinePixelHydrationReceiptV1,
    project_authenticated_line_pixel_hydration_receipt_v1,
    read_authenticated_line_pixel_hydration_envelope_v1,
    read_authenticated_line_pixel_hydration_render_v1,
    validate_authenticated_line_pixel_hydration_envelope_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_ready_panel_v1 import (
    AuthenticatedLoanMaturity8BankReadyPanelV1,
    project_authenticated_loan_maturity_8bank_anonymous_batch_v1,
    project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1,
    read_authenticated_loan_maturity_8bank_anonymous_page_v1,
    validate_authenticated_loan_maturity_8bank_anonymous_batch_v1,
)
from bctc_ai.evaluation.vietocr_all_line_freezer_v3 import (
    AuthenticatedVietOCRAllLineFreezeV3,
    read_authenticated_vietocr_all_line_snapshot_v3,
)
from bctc_ai.source_structure import vietocr_semantic_receipt_v3 as receipt_v3
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import (
    SourceStructureContractV2Error,
    validate_source_evidence_projection_v2,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v3 import (
    AuthenticatedVietOCRSemanticReceiptV3,
    project_authenticated_vietocr_semantic_receipt_v3,
    read_authenticated_vietocr_semantic_proposals_v3,
)

__all__ = [
    "BINDING_FORMAT_VERSION",
    "AuthenticatedVietOCRSemanticPageBindingV3",
    "VietOCRSemanticPageBindingV3Error",
    "bind_authenticated_vietocr_semantic_page_v3",
    "project_authenticated_vietocr_semantic_page_binding_v3",
    "read_authenticated_vietocr_semantic_page_samples_v3",
    "validate_authenticated_vietocr_semantic_page_binding_v3",
]


class VietOCRSemanticPageBindingV3Error(RuntimeError):
    """The source page or one of its live V3 lineages failed exact replay."""


BINDING_FORMAT_VERSION = "BCTC_AI_VIETOCR_SEMANTIC_PAGE_BINDING_V3"
CLAIM_BOUNDARY = (
    "LIVE_READY_FREEZE_RECEIPT_TO_EXACT_SOURCE_LINE_CORRESPONDENCE_ONLY_"
    "TERMINAL_SUPPLEMENT_REMAINS_UNRESOLVED_NO_NUMERIC_PERIOD_UNIT_SCOPE_"
    "ACCOUNTING_MAPPING_SCHEMA_OR_ACCEPTANCE_AUTHORITY"
)
_BOUND = "BOUND_TO_EXACT_NONTERMINAL_SOURCE_LINE_AXIS"
_TERMINAL = "UNRESOLVED_TERMINAL_SOURCE_NUMERIC_AXIS_UNAVAILABLE"
_ORDINARY = "ORDINARY_V2_PRIMARY_LINES"
_NATIVE = "HYDRATED_NATIVE_PRIMARY_LINES"
_TERMINAL_SUPPLEMENT = "HYDRATED_TERMINAL_LINE_SUPPLEMENT"
_READY = "READY_FOR_OPAQUE_ALL_LINE_FREEZE"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_BINDING_ID_PREFIX = "vospbv3:binding:"
_TERMINAL_ATOM_PREFIX = "vospbv3:terminal-atom:"
_SAMPLE_RE = re.compile(r"^(page-[0-9]{4})-line-([0-9]{4})$")

_AUTHORITY = {
    "accounting_authority": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "geometry_correspondence_authenticated": True,
    "live_capability_required": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "raw_projection_self_authenticates": False,
    "schema_authority": False,
    "semantic_acceptance": False,
    "semantic_text_source_is_vietocr_vgg_transformer": True,
    "source_transcript_used_for_semantic_identity": False,
    "terminal_supplement_promoted_to_primary": False,
}
_FIELDS = {
    "authority",
    "binding_id",
    "binding_mode",
    "claim_boundary",
    "format_version",
    "freeze_id",
    "metrics",
    "page_id",
    "page_ordinal",
    "page_source_binding",
    "ready_batch_id",
    "samples",
    "semantic_receipt_id",
    "source_local_page_id",
    "source_projection_sha256",
    "status",
    "unresolved_reasons",
}
_SOURCE_FIELDS = {
    "bound_line_axis_sha256",
    "geometry_lineage",
    "hydration_receipt_id",
    "page_result_sha256",
    "physical_page",
    "ready_render_sha256",
    "request_sha256",
    "route",
    "source_page_result_line_axis_sha256",
    "source_pdf_sha256",
    "source_size_bytes",
    "terminal",
}
_METRIC_FIELDS = {
    "all_ready_lines_bound_once",
    "observation_v2_input_shape_compatible",
    "ready_line_count",
    "semantic_sample_count",
    "source_page_result_line_count",
    "source_primary_line_count",
    "terminal_supplement_line_count",
}
_SAMPLE_FIELDS = {
    "crop_ref",
    "mean_decoded_character_probability",
    "normalized_prediction",
    "padded_source_bbox_raw_pixels",
    "page_id",
    "processed_dimensions",
    "raw_prediction",
    "sample_id",
    "source_atom",
    "source_bbox_raw_pixels",
    "source_line_index",
}
_ATOM_FIELDS = {
    "canonical_bbox_mpt",
    "line_index",
    "pixel_bbox",
    "source_atom_id",
}
_CROP_REF_FIELDS = {"path", "sha256", "size_bytes"}
_OBJECT_REF_FIELDS = {"path", "sha256", "size_bytes"}


def _error(message: str) -> VietOCRSemanticPageBindingV3Error:
    return VietOCRSemanticPageBindingV3Error(message)


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return cast(dict[str, Any], value)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} is not one lowercase SHA-256")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} is not one positive integer")
    return value


def _bbox(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} is not one positive integer bbox")
    return list(value)


def _validated_cas_json_ref(value: Any, label: str) -> dict[str, Any]:
    """Validate one safe CAS path while allowing a contract-specific prefix."""

    reference = _exact(value, _OBJECT_REF_FIELDS, label)
    digest = _sha(reference["sha256"], f"{label} identity")
    _positive_int(reference["size_bytes"], f"{label} size")
    path_value = reference["path"]
    path = Path(path_value) if type(path_value) is str else None
    expected_tail = ("objects", "sha256", digest[:2], f"{digest}.json")
    if (
        path is None
        or path.is_absolute()
        or path.as_posix() != path_value
        or "\\" in path_value
        or any(part in {"", ".", ".."} for part in path.parts)
        or tuple(path.parts[-4:]) != expected_tail
    ):
        raise _error(f"{label} is not one safe content-addressed JSON reference")
    return reference


def _same_json_content_across_namespaces(first: Any, second: Any, label: str) -> bool:
    left = _validated_cas_json_ref(first, f"{label} first reference")
    right = _validated_cas_json_ref(second, f"{label} second reference")
    return left["sha256"] == right["sha256"] and left["size_bytes"] == right["size_bytes"]


def _require_capability_types(
    ready_capability: Any,
    freeze_capability: Any,
    semantic_receipt_capability: Any,
    hydration_capabilities: Any,
) -> tuple[AuthenticatedLinePixelHydrationReceiptV1, ...]:
    if type(ready_capability) is not AuthenticatedLoanMaturity8BankReadyPanelV1:
        raise _error("page binding requires one exact live READY-panel capability")
    if type(freeze_capability) is not AuthenticatedVietOCRAllLineFreezeV3:
        raise _error("page binding requires one exact live V3 freeze capability")
    if type(semantic_receipt_capability) is not AuthenticatedVietOCRSemanticReceiptV3:
        raise _error("page binding requires one exact live V3 semantic receipt")
    if type(hydration_capabilities) is not tuple or any(
        type(item) is not AuthenticatedLinePixelHydrationReceiptV1
        for item in hydration_capabilities
    ):
        raise _error("hydration authorities must be one exact tuple of live capabilities")
    if len({id(item) for item in hydration_capabilities}) != len(hydration_capabilities):
        raise _error("hydration capability tuple contains a duplicate handle")
    return hydration_capabilities


def _read_ready_live(
    capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    tuple[dict[str, Any], ...],
    tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
]:
    """Replay public READY roots and recover its already-validated private panel snapshot."""

    batch = project_authenticated_loan_maturity_8bank_anonymous_batch_v1(capability)
    validate_authenticated_loan_maturity_8bank_anonymous_batch_v1(batch, capability)
    audit = project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1(capability)
    # This private generic core performs the full child-capability replay.  The
    # experiment needs its exact result refs, which the public anonymous view
    # intentionally withholds from the reader lane.
    ready_v1._authenticated_state(capability)
    state = ready_v1._AUTHENTICATED.get(capability)
    if state is None:
        raise _error("live READY-panel private lineage expired during replay")
    try:
        panel = decode_canonical_json_bytes_v1(state.panel_payload)
    except (TypeError, ValueError) as exc:
        raise _error("READY-panel lineage snapshot is not canonical JSON") from exc
    if type(panel) is not dict or type(panel.get("slots")) is not list:
        raise _error("READY-panel private lineage shape drifted")
    raw_pages = tuple(
        read_authenticated_loan_maturity_8bank_anonymous_page_v1(capability, ordinal)
        for ordinal in range(1, len(panel["slots"]) + 1)
    )
    pages = []
    for page, slot in zip(raw_pages, audit["slots"], strict=True):
        render = page["render_png_bytes"]
        digest = hashlib.sha256(render).hexdigest()
        if (
            digest != slot["render_sha256"]
            or len(render) != slot["render_size_bytes"]
            or canonical_json_sha256_v1(page["line_bboxes"]) != slot["line_axis_sha256"]
        ):
            raise _error("READY anonymous page/audit render or line axis drifted")
        pages.append(
            {
                **page,
                "render_sha256": digest,
                "render_size_bytes": len(render),
            }
        )
    return (
        batch,
        audit,
        cast(dict[str, Any], panel),
        tuple(pages),
        state.hydration_capabilities,
    )


def _read_freeze_live(
    capability: AuthenticatedVietOCRAllLineFreezeV3,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
) -> tuple[dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]:
    projection, samples = read_authenticated_vietocr_all_line_snapshot_v3(capability)
    state, replay_projection, manifest = freezer_v3._validated_state(capability)
    if state.ready_capability is not ready_capability:
        raise _error("freeze does not descend from the supplied live READY handle")
    if not same_typed_json_v1(projection, replay_projection):
        raise _error("public and private live freeze projections differ")
    return projection, manifest, samples


def _read_receipt_live(
    capability: AuthenticatedVietOCRSemanticReceiptV3,
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    private = receipt_v3._receipt_payload(capability)
    run = receipt_v3._run_payload(private["run_capability"])
    if run["freeze"] is not freeze_capability:
        raise _error("semantic receipt does not descend from the supplied live freeze handle")
    return (
        project_authenticated_vietocr_semantic_receipt_v3(capability),
        read_authenticated_vietocr_semantic_proposals_v3(capability),
    )


def _read_hydrations_live(
    capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
) -> tuple[tuple[dict[str, Any], dict[str, Any], bytes], ...]:
    records = []
    for capability in capabilities:
        envelope = read_authenticated_line_pixel_hydration_envelope_v1(capability)
        validate_authenticated_line_pixel_hydration_envelope_v1(envelope, capability)
        receipt = project_authenticated_line_pixel_hydration_receipt_v1(capability)
        render = read_authenticated_line_pixel_hydration_render_v1(capability)
        records.append((envelope, receipt, render))
    return tuple(records)


def _selected_slot(
    source: dict[str, Any],
    audit: dict[str, Any],
    panel: dict[str, Any],
) -> tuple[int, dict[str, Any], dict[str, Any]]:
    locator = source["source_locator"]
    key = (locator["source_sha256"], locator["physical_page"])
    audit_slots = audit.get("slots")
    panel_slots = panel.get("slots")
    if (
        type(audit_slots) is not list
        or type(panel_slots) is not list
        or len(audit_slots) != len(panel_slots)
    ):
        raise _error("READY audit/private panel slot axes drifted")
    matches = [
        index
        for index, item in enumerate(audit_slots)
        if type(item) is dict and (item.get("source_pdf_sha256"), item.get("physical_page")) == key
    ]
    if len(matches) != 1:
        raise _error("source locator has no unique READY-panel slot")
    index = matches[0]
    audit_slot = audit_slots[index]
    panel_slot = panel_slots[index]
    if (
        type(panel_slot) is not dict
        or panel_slot.get("source_pdf_sha256") != key[0]
        or panel_slot.get("physical_page") != key[1]
    ):
        raise _error("READY audit/private slot locator binding drifted")
    inventory = panel_slot.get("inventory_evidence")
    if type(inventory) is not dict:
        raise _error("READY private slot lacks inventory evidence")
    expected_source_state = {
        "result_format_version": source["page_result_format_version"],
        "route": source["route"],
        "status": source["upstream_status"],
        "unresolved": source["terminal"],
    }
    for field, expected in expected_source_state.items():
        if not same_typed_json_v1(inventory.get(field), expected):
            raise _error(f"source projection/READY inventory {field} binding drifted")
    if not _same_json_content_across_namespaces(
        inventory.get("result_ref"),
        source["page_result_ref"],
        "source projection/READY result",
    ):
        raise _error("source projection/READY result content identity drifted")
    return index + 1, cast(dict[str, Any], audit_slot), cast(dict[str, Any], panel_slot)


def _hydration_for_source(
    source: dict[str, Any],
    ready_page: dict[str, Any],
    records: tuple[tuple[dict[str, Any], dict[str, Any], bytes], ...],
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    locator = source["source_locator"]
    matches = []
    for envelope, receipt, render in records:
        receipt_locator = receipt["source_locator"]
        if (
            receipt_locator["source_pdf_sha256"] == locator["source_sha256"]
            and receipt_locator["source_size_bytes"] == locator["source_size_bytes"]
            and receipt_locator["physical_page"] == locator["physical_page"]
        ):
            matches.append((envelope, receipt, render))
    if len(matches) != 1:
        raise _error("hydrated source has no unique matching live hydration receipt")
    envelope, receipt, render = matches[0]
    if (
        envelope["source_binding"]["request_sha256"] != locator["request_sha256"]
        # These independently validated references use different path
        # namespaces.  Content hash and size are their cross-contract identity.
        or not _same_json_content_across_namespaces(
            receipt["upstream_result_ref"],
            source["page_result_ref"],
            "hydration/source result",
        )
        or hashlib.sha256(render).hexdigest() != ready_page["render_sha256"]
        or len(render) != ready_page["render_size_bytes"]
        or [item["raw_pixel_bbox"] for item in envelope["lines"]] != ready_page["line_bboxes"]
    ):
        raise _error("hydration/source/READY render or line-axis binding drifted")
    return envelope, receipt, render


def _ordinary_atoms(source: dict[str, Any], ready_page: dict[str, Any]) -> list[dict[str, Any]]:
    lines = source["page_result"]["lines"]
    atoms: dict[int, dict[str, Any]] = {}
    for atom in source["neutral_page_v1"]["atoms"]:
        locator = atom["upstream_locator"]
        if (
            atom["kind"] == "LINE"
            and atom["authority"] == "AUTHENTICATED_PRIMARY"
            and locator["kind"] == "OCR_LINE_INDEX"
        ):
            index = locator["line_index"]
            if index in atoms:
                raise _error("ordinary source contains duplicate primary LINE indices")
            atoms[index] = atom
    if sorted(atoms) != list(range(len(lines))) or len(lines) != ready_page["line_count"]:
        raise _error("ordinary source primary LINE denominator differs from READY")
    ordered = [atoms[index] for index in range(len(lines))]
    for index, (line, atom, bbox) in enumerate(
        zip(lines, ordered, ready_page["line_bboxes"], strict=True)
    ):
        if (
            not same_typed_json_v1(line["raw_pixel_bbox"], bbox)
            or not same_typed_json_v1(atom["pixel_bbox"], bbox)
            or not same_typed_json_v1(atom["canonical_bbox_mpt"], line["canonical_bbox_mpt"])
        ):
            raise _error(f"ordinary source LINE {index} geometry differs from READY")
    return ordered


def _native_atoms(
    source: dict[str, Any],
    ready_page: dict[str, Any],
    envelope: dict[str, Any],
) -> list[dict[str, Any]]:
    lines = source["page_result"]["lines"]
    keyed: dict[tuple[int, int], dict[str, Any]] = {}
    for atom in source["neutral_page_v1"]["atoms"]:
        locator = atom["upstream_locator"]
        if (
            atom["kind"] == "LINE"
            and atom["authority"] == "AUTHENTICATED_PRIMARY"
            and locator["kind"] == "NATIVE_LINE_INDEX"
        ):
            key = (locator["block_number"], locator["line_number"])
            if key in keyed:
                raise _error("native source contains duplicate primary LINE identities")
            keyed[key] = atom
    if len(lines) != len(envelope["lines"]) or len(lines) != ready_page["line_count"]:
        raise _error("native source/hydration/READY LINE denominators differ")
    ordered = []
    for index, (line, hydrated, bbox) in enumerate(
        zip(lines, envelope["lines"], ready_page["line_bboxes"], strict=True)
    ):
        key = (line["block_number"], line["line_number"])
        atom = keyed.get(key)
        if (
            atom is None
            or hydrated["line_index"] != index
            or not same_typed_json_v1(hydrated["raw_pixel_bbox"], bbox)
            or not same_typed_json_v1(hydrated["canonical_bbox_mpt"], line["canonical_bbox_mpt"])
            or not same_typed_json_v1(atom["canonical_bbox_mpt"], line["canonical_bbox_mpt"])
        ):
            raise _error(f"native source LINE {index} geometry/identity differs from hydration")
        ordered.append(atom)
    if len(ordered) != ready_page["line_count"] or len(keyed) != len(ordered):
        raise _error("native source primary LINE denominator differs from READY")
    return ordered


def _terminal_atoms(source: dict[str, Any], envelope: dict[str, Any]) -> list[dict[str, Any]]:
    atoms = []
    for line in envelope["lines"]:
        material = {
            "canonical_bbox_mpt": line["canonical_bbox_mpt"],
            "line_index": line["line_index"],
            "source_local_page_id": source["source_local_page_id"],
            "source_geometry_sha256": line["source_geometry_sha256"],
        }
        atoms.append(
            {
                "authority": "TERMINAL_SUPPLEMENTAL_COARSE_LINE",
                "canonical_bbox_mpt": canonical_clone_v1(line["canonical_bbox_mpt"]),
                "pixel_bbox": canonical_clone_v1(line["raw_pixel_bbox"]),
                "source_local_id": _TERMINAL_ATOM_PREFIX + canonical_json_sha256_v1(material),
            }
        )
    return atoms


def _bound_samples(
    proposals: list[dict[str, Any]],
    manifest_samples: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    boxes: list[list[int]],
    *,
    pixel_width: int,
    pixel_height: int,
) -> list[dict[str, Any]]:
    if not (len(proposals) == len(manifest_samples) == len(atoms) == len(boxes)):
        raise _error("semantic/manifest/source/READY LINE denominators differ")
    bound = []
    left, top, right, bottom = freezer_v3.SOURCE_PADDING
    for index, (proposal, manifest, atom, bbox) in enumerate(
        zip(proposals, manifest_samples, atoms, boxes, strict=True)
    ):
        if (
            proposal["line_index"] != index
            or manifest["line_index"] != index
            or proposal["sample_id"] != manifest["sample_id"]
            or proposal["crop_sha256"] != manifest["crop_sha256"]
        ):
            raise _error("semantic proposal/freeze-manifest line order drifted")
        padded = [
            max(0, bbox[0] - left),
            max(0, bbox[1] - top),
            min(pixel_width, bbox[2] + right),
            min(pixel_height, bbox[3] + bottom),
        ]
        bound.append(
            {
                "crop_ref": {
                    "path": manifest["crop_path"],
                    "sha256": manifest["crop_sha256"],
                    "size_bytes": manifest["crop_size_bytes"],
                },
                "mean_decoded_character_probability": proposal[
                    "mean_decoded_character_probability"
                ],
                "normalized_prediction": proposal["normalized_prediction"],
                "padded_source_bbox_raw_pixels": padded,
                "page_id": proposal["page_id"],
                "processed_dimensions": [
                    proposal["processed_width"],
                    proposal["processed_height"],
                ],
                "raw_prediction": proposal["raw_prediction"],
                "sample_id": proposal["sample_id"],
                "source_atom": {
                    "canonical_bbox_mpt": canonical_clone_v1(atom["canonical_bbox_mpt"]),
                    "line_index": index,
                    "pixel_bbox": canonical_clone_v1(bbox),
                    "source_atom_id": atom["source_local_id"],
                },
                "source_bbox_raw_pixels": canonical_clone_v1(bbox),
                "source_line_index": index,
            }
        )
    return bound


def _validate_binding_shape(value: Any) -> dict[str, Any]:
    binding = _exact(value, _FIELDS, "V3 semantic page binding")
    identifier = binding["binding_id"]
    if (
        binding["format_version"] != BINDING_FORMAT_VERSION
        or binding["claim_boundary"] != CLAIM_BOUNDARY
        or binding["binding_mode"] not in {_ORDINARY, _NATIVE, _TERMINAL_SUPPLEMENT}
        or binding["status"] not in {_BOUND, _TERMINAL}
        or type(identifier) is not str
        or not identifier.startswith(_BINDING_ID_PREFIX)
        or _SHA_RE.fullmatch(identifier.removeprefix(_BINDING_ID_PREFIX)) is None
        or not same_typed_json_v1(binding["authority"], _AUTHORITY)
    ):
        raise _error("V3 semantic page binding identity/authority drifted")
    _sha(binding["source_projection_sha256"], "source projection identity")
    if (
        type(binding["page_ordinal"]) is not int
        or not 1 <= binding["page_ordinal"] <= 8
        or binding["page_id"] != f"page-{binding['page_ordinal']:04d}"
        or type(binding["source_local_page_id"]) is not str
        or not binding["source_local_page_id"].startswith("ssv2:page:")
        or type(binding["freeze_id"]) is not str
        or not binding["freeze_id"].startswith("voalfv3:freeze:")
        or type(binding["semantic_receipt_id"]) is not str
        or not binding["semantic_receipt_id"].startswith("voalsrv3:receipt:")
        or type(binding["ready_batch_id"]) is not str
        or not binding["ready_batch_id"].startswith("lm8brpv1:batch:")
    ):
        raise _error("V3 semantic page/source ordinal identity drifted")
    reasons = binding["unresolved_reasons"]
    expected_reasons = (
        []
        if binding["status"] == _BOUND
        else [
            "NUMERIC_SOURCE_LINE_AXIS_UNAVAILABLE",
            "SOURCE_PROJECTION_TERMINAL",
            "TERMINAL_SUPPLEMENT_NOT_AUTHENTICATED_PRIMARY",
        ]
    )
    if not same_typed_json_v1(reasons, expected_reasons):
        raise _error("V3 semantic page unresolved disposition drifted")
    source = _exact(binding["page_source_binding"], _SOURCE_FIELDS, "page source binding")
    for field in (
        "bound_line_axis_sha256",
        "page_result_sha256",
        "ready_render_sha256",
        "request_sha256",
        "source_page_result_line_axis_sha256",
        "source_pdf_sha256",
    ):
        _sha(source[field], f"page source {field}")
    _positive_int(source["physical_page"], "page source physical page")
    _positive_int(source["source_size_bytes"], "page source PDF size")
    if (
        type(source["terminal"]) is not bool
        or type(source["route"]) is not str
        or type(source["geometry_lineage"]) is not str
        or (
            source["hydration_receipt_id"] is not None
            and type(source["hydration_receipt_id"]) is not str
        )
    ):
        raise _error("page source typed lineage drifted")
    metrics = _exact(binding["metrics"], _METRIC_FIELDS, "page binding metrics")
    for field in (
        "ready_line_count",
        "semantic_sample_count",
        "source_page_result_line_count",
        "source_primary_line_count",
        "terminal_supplement_line_count",
    ):
        if type(metrics[field]) is not int or metrics[field] < 0:
            raise _error(f"page binding metric {field} drifted")
    for field in ("all_ready_lines_bound_once", "observation_v2_input_shape_compatible"):
        if type(metrics[field]) is not bool:
            raise _error(f"page binding metric {field} is not one exact boolean")
    samples = binding["samples"]
    if type(samples) is not list or len(samples) != metrics["semantic_sample_count"]:
        raise _error("page binding semantic sample denominator drifted")
    terminal = binding["binding_mode"] == _TERMINAL_SUPPLEMENT
    if (
        binding["status"] != (_TERMINAL if terminal else _BOUND)
        or source["terminal"] is not terminal
        or metrics["all_ready_lines_bound_once"] is not True
        or metrics["ready_line_count"] != len(samples)
        or metrics["observation_v2_input_shape_compatible"] is not (not terminal)
        or metrics["source_primary_line_count"] != (0 if terminal else len(samples))
        or metrics["terminal_supplement_line_count"] != (len(samples) if terminal else 0)
        or metrics["source_page_result_line_count"] != (0 if terminal else len(samples))
        or (source["hydration_receipt_id"] is None) is (binding["binding_mode"] != _ORDINARY)
        or (binding["binding_mode"] == _ORDINARY and source["route"] != "DOMINANT_RASTER_OCR")
        or (binding["binding_mode"] == _NATIVE and source["route"] != "CAUSAL_NATIVE_TEXT")
        or (terminal and source["route"] != "DOMINANT_RASTER_OCR")
    ):
        raise _error("V3 semantic page mode/status/denominator disposition drifted")
    for index, item in enumerate(samples):
        sample = _exact(item, _SAMPLE_FIELDS, f"bound semantic sample {index}")
        atom = _exact(sample["source_atom"], _ATOM_FIELDS, f"bound source atom {index}")
        crop_ref = _exact(sample["crop_ref"], _CROP_REF_FIELDS, f"bound crop ref {index}")
        sample_match = (
            _SAMPLE_RE.fullmatch(sample["sample_id"]) if type(sample["sample_id"]) is str else None
        )
        crop_path = Path(crop_ref["path"]) if type(crop_ref["path"]) is str else None
        expected_atom_prefix = _TERMINAL_ATOM_PREFIX if terminal else "ssv1:atom:"
        if (
            sample["source_line_index"] != index
            or atom["line_index"] != index
            or sample["page_id"] != binding["page_id"]
            or sample_match is None
            or sample_match.group(1) != binding["page_id"]
            or int(sample_match.group(2)) != index
            or not same_typed_json_v1(sample["source_bbox_raw_pixels"], atom["pixel_bbox"])
            or type(sample["normalized_prediction"]) is not str
            or unicodedata.normalize("NFC", sample["normalized_prediction"])
            != sample["normalized_prediction"]
            or sample["normalized_prediction"]
            != unicodedata.normalize("NFC", sample["raw_prediction"])
            or type(sample["raw_prediction"]) is not str
            or type(atom["source_atom_id"]) is not str
            or not atom["source_atom_id"].startswith(expected_atom_prefix)
            or type(crop_ref["path"]) is not str
            or not crop_ref["path"]
            or crop_path is None
            or crop_path.is_absolute()
            or "\\" in crop_ref["path"]
            or any(part in {"", ".", ".."} for part in crop_path.parts)
            or crop_path.suffix != ".png"
        ):
            raise _error(f"bound semantic sample {index} identity/order drifted")
        _bbox(sample["source_bbox_raw_pixels"], f"bound semantic sample {index} pixel bbox")
        _bbox(
            sample["padded_source_bbox_raw_pixels"],
            f"bound semantic sample {index} padded bbox",
        )
        raw_box = sample["source_bbox_raw_pixels"]
        padded_box = sample["padded_source_bbox_raw_pixels"]
        if not (
            padded_box[0] <= raw_box[0]
            and padded_box[1] <= raw_box[1]
            and padded_box[2] >= raw_box[2]
            and padded_box[3] >= raw_box[3]
        ):
            raise _error(f"bound semantic sample {index} padded bbox does not enclose source")
        _bbox(atom["canonical_bbox_mpt"], f"bound semantic sample {index} canonical bbox")
        _sha(crop_ref["sha256"], f"bound semantic sample {index} crop")
        _positive_int(crop_ref["size_bytes"], f"bound semantic sample {index} crop size")
        dimensions = sample["processed_dimensions"]
        if type(dimensions) is not list or len(dimensions) != 2:
            raise _error(f"bound semantic sample {index} processed dimensions drifted")
        _positive_int(dimensions[0], f"bound semantic sample {index} width")
        _positive_int(dimensions[1], f"bound semantic sample {index} height")
        probability = sample["mean_decoded_character_probability"]
        if (
            type(probability) is not float
            or not math.isfinite(probability)
            or not 0 <= probability <= 1
        ):
            raise _error(f"bound semantic sample {index} probability drifted")
    bound_axis = [
        {
            "canonical_bbox_mpt": item["source_atom"]["canonical_bbox_mpt"],
            "pixel_bbox": item["source_bbox_raw_pixels"],
            "source_atom_id": item["source_atom"]["source_atom_id"],
        }
        for item in samples
    ]
    if source["bound_line_axis_sha256"] != canonical_json_sha256_v1(bound_axis):
        raise _error("bound source LINE axis identity drifted")
    material = canonical_clone_v1(binding)
    del material["binding_id"]
    if identifier != _BINDING_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("V3 semantic page binding content identity drifted")
    return canonical_clone_v1(binding)


def _build_live_binding(
    source_projection_v2: Any,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3,
    semantic_receipt_capability: AuthenticatedVietOCRSemanticReceiptV3,
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
) -> dict[str, Any]:
    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except SourceStructureContractV2Error as exc:
        raise _error("source projection V2 failed exact validation") from exc
    batch, audit, panel, ready_pages, ready_hydrations = _read_ready_live(ready_capability)
    if len(ready_hydrations) != len(hydration_capabilities) or any(
        expected is not supplied
        for expected, supplied in zip(ready_hydrations, hydration_capabilities, strict=True)
    ):
        raise _error("hydration capabilities are not the exact READY-panel child handles")
    freeze, manifest, frozen_samples = _read_freeze_live(freeze_capability, ready_capability)
    receipt, semantic_samples = _read_receipt_live(semantic_receipt_capability, freeze_capability)
    hydrations = _read_hydrations_live(hydration_capabilities)
    if (
        manifest.get("input_batch_id") != batch["batch_id"]
        or receipt.get("freeze_id") != freeze["freeze_id"]
        or receipt.get("sample_count") != batch["sample_count"]
    ):
        raise _error("READY/freeze/semantic receipt live lineage drifted")
    page_ordinal, audit_slot, panel_slot = _selected_slot(source, audit, panel)
    ready_page = ready_pages[page_ordinal - 1]
    page_id = f"page-{page_ordinal:04d}"
    if ready_page["page_id"] != page_id:
        raise _error("READY page ordinal identity drifted")
    page_frozen = [item for item in frozen_samples if item["page_id"] == page_id]
    page_manifest = [item for item in manifest["samples"] if item["page_id"] == page_id]
    page_semantic = [item for item in semantic_samples if item["page_id"] == page_id]
    if (
        len(page_frozen) != ready_page["line_count"]
        or len(page_manifest) != ready_page["line_count"]
        or len(page_semantic) != ready_page["line_count"]
    ):
        raise _error("READY/freeze/semantic page denominator drifted")
    image = freezer_v3._png_rgb(ready_page["render_png_bytes"], "semantic binding READY render")
    for index, (box, frozen, proposal) in enumerate(
        zip(ready_page["line_bboxes"], page_frozen, page_semantic, strict=True)
    ):
        crop, _width, _height = freezer_v3._crop_bytes(
            image,
            freezer_v3._bbox(
                box,
                ready_page["pixel_width"],
                ready_page["pixel_height"],
                f"semantic binding line {index}",
            ),
        )
        expected_id = f"{page_id}-line-{index:04d}"
        digest = hashlib.sha256(crop).hexdigest()
        if (
            frozen["sample_id"] != expected_id
            or proposal["sample_id"] != expected_id
            or frozen["crop_sha256"] != digest
            or proposal["crop_sha256"] != digest
            or frozen["crop_png_bytes"] != crop
            or proposal["line_index"] != index
        ):
            raise _error(f"READY/freeze/semantic crop {index} binding drifted")

    prerequisite = panel_slot.get("freezer_prerequisite")
    if type(prerequisite) is not dict:
        raise _error("READY private slot lacks freezer prerequisite")
    hydration_receipt_id: str | None = None
    source_primary_count = 0
    terminal_supplement_count = 0
    if prerequisite.get("state") == _READY:
        if source["route"] != "DOMINANT_RASTER_OCR" or source["terminal"] is not False:
            raise _error("ordinary READY geometry selected a non-ordinary source")
        mode = _ORDINARY
        atoms = _ordinary_atoms(source, ready_page)
        geometry_lineage = audit_slot["geometry_authority"]
        source_primary_count = len(atoms)
    else:
        envelope, hydration_receipt, _render = _hydration_for_source(source, ready_page, hydrations)
        hydration_receipt_id = hydration_receipt["receipt_id"]
        geometry_lineage = envelope["adapter_id"]
        if source["route"] == "CAUSAL_NATIVE_TEXT" and source["terminal"] is False:
            mode = _NATIVE
            atoms = _native_atoms(source, ready_page, envelope)
            source_primary_count = len(atoms)
        elif source["route"] == "DOMINANT_RASTER_OCR" and source["terminal"] is True:
            mode = _TERMINAL_SUPPLEMENT
            atoms = _terminal_atoms(source, envelope)
            terminal_supplement_count = len(atoms)
        else:
            raise _error("hydrated source state has no admitted generic page-binding mode")
    proposals = [canonical_clone_v1(item) for item in page_semantic]
    bound = _bound_samples(
        proposals,
        page_manifest,
        atoms,
        ready_page["line_bboxes"],
        pixel_width=ready_page["pixel_width"],
        pixel_height=ready_page["pixel_height"],
    )
    terminal = mode == _TERMINAL_SUPPLEMENT
    status = _TERMINAL if terminal else _BOUND
    source_lines = source["page_result"]["lines"]
    bound_axis = [
        {
            "canonical_bbox_mpt": item["source_atom"]["canonical_bbox_mpt"],
            "pixel_bbox": item["source_bbox_raw_pixels"],
            "source_atom_id": item["source_atom"]["source_atom_id"],
        }
        for item in bound
    ]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "binding_mode": mode,
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": BINDING_FORMAT_VERSION,
        "freeze_id": freeze["freeze_id"],
        "metrics": {
            "all_ready_lines_bound_once": True,
            "observation_v2_input_shape_compatible": not terminal,
            "ready_line_count": ready_page["line_count"],
            "semantic_sample_count": len(bound),
            "source_page_result_line_count": len(source_lines),
            "source_primary_line_count": source_primary_count,
            "terminal_supplement_line_count": terminal_supplement_count,
        },
        "page_id": page_id,
        "page_ordinal": page_ordinal,
        "page_source_binding": {
            "bound_line_axis_sha256": canonical_json_sha256_v1(bound_axis),
            "geometry_lineage": geometry_lineage,
            "hydration_receipt_id": hydration_receipt_id,
            "page_result_sha256": source["page_result_sha256"],
            "physical_page": source["source_locator"]["physical_page"],
            "ready_render_sha256": ready_page["render_sha256"],
            "request_sha256": source["source_locator"]["request_sha256"],
            "route": source["route"],
            "source_page_result_line_axis_sha256": canonical_json_sha256_v1(source_lines),
            "source_pdf_sha256": source["source_locator"]["source_sha256"],
            "source_size_bytes": source["source_locator"]["source_size_bytes"],
            "terminal": source["terminal"],
        },
        "ready_batch_id": batch["batch_id"],
        "samples": bound,
        "semantic_receipt_id": receipt["receipt_id"],
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "status": status,
        "unresolved_reasons": (
            [
                "NUMERIC_SOURCE_LINE_AXIS_UNAVAILABLE",
                "SOURCE_PROJECTION_TERMINAL",
                "TERMINAL_SUPPLEMENT_NOT_AUTHENTICATED_PRIMARY",
            ]
            if terminal
            else []
        ),
    }
    binding = {
        **material,
        "binding_id": _BINDING_ID_PREFIX + canonical_json_sha256_v1(material),
    }
    return _validate_binding_shape(binding)


class AuthenticatedVietOCRSemanticPageBindingV3:
    """Opaque noncopyable live authority over one exact semantic page binding."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _TOKEN:
            raise _error("authenticated V3 page bindings can only be minted by live replay")

    def __copy__(self) -> Any:
        raise _error("authenticated V3 page bindings cannot be copied")

    __deepcopy__ = __copy__

    def __reduce__(self) -> Any:
        raise pickle.PicklingError("authenticated V3 page bindings cannot be serialized")


@dataclass(frozen=True, slots=True)
class _State:
    source_payload: bytes
    binding_payload: bytes
    digest: str
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3
    semantic_receipt_capability: AuthenticatedVietOCRSemanticReceiptV3
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...]


_TOKEN = object()
_STATES: weakref.WeakKeyDictionary[AuthenticatedVietOCRSemanticPageBindingV3, _State] = (
    weakref.WeakKeyDictionary()
)


def _state_digest(source_payload: bytes, binding_payload: bytes) -> str:
    return hashlib.sha256(
        len(source_payload).to_bytes(8, "big")
        + source_payload
        + len(binding_payload).to_bytes(8, "big")
        + binding_payload
    ).hexdigest()


def bind_authenticated_vietocr_semantic_page_v3(
    source_projection_v2: Any,
    ready_capability: AuthenticatedLoanMaturity8BankReadyPanelV1,
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3,
    semantic_receipt_capability: AuthenticatedVietOCRSemanticReceiptV3,
    hydration_capabilities: tuple[AuthenticatedLinePixelHydrationReceiptV1, ...],
) -> AuthenticatedVietOCRSemanticPageBindingV3:
    """Replay all live roots and mint one source-bound semantic page handle."""

    hydrations = _require_capability_types(
        ready_capability,
        freeze_capability,
        semantic_receipt_capability,
        hydration_capabilities,
    )
    binding = _build_live_binding(
        source_projection_v2,
        ready_capability,
        freeze_capability,
        semantic_receipt_capability,
        hydrations,
    )
    source = validate_source_evidence_projection_v2(source_projection_v2)
    source_payload = canonical_json_bytes_v1(source)
    binding_payload = canonical_json_bytes_v1(binding)
    capability = AuthenticatedVietOCRSemanticPageBindingV3(_TOKEN)
    _STATES[capability] = _State(
        source_payload=source_payload,
        binding_payload=binding_payload,
        digest=_state_digest(source_payload, binding_payload),
        ready_capability=ready_capability,
        freeze_capability=freeze_capability,
        semantic_receipt_capability=semantic_receipt_capability,
        hydration_capabilities=hydrations,
    )
    _authenticated_payload(capability)
    return capability


def _authenticated_payload(
    capability: AuthenticatedVietOCRSemanticPageBindingV3,
) -> dict[str, Any]:
    if type(capability) is not AuthenticatedVietOCRSemanticPageBindingV3:
        raise _error("V3 semantic page authority requires one exact opaque capability")
    state = _STATES.get(capability)
    if state is None:
        raise _error("V3 semantic page capability is unknown or expired")
    if _state_digest(state.source_payload, state.binding_payload) != state.digest:
        raise _error("V3 semantic page capability in-memory bytes drifted")
    try:
        source = decode_canonical_json_bytes_v1(state.source_payload)
        stored = decode_canonical_json_bytes_v1(state.binding_payload)
    except (TypeError, ValueError) as exc:
        raise _error("V3 semantic page capability bytes are not canonical JSON") from exc
    rebuilt = _build_live_binding(
        source,
        state.ready_capability,
        state.freeze_capability,
        state.semantic_receipt_capability,
        state.hydration_capabilities,
    )
    if type(stored) is not dict or not same_typed_json_v1(stored, rebuilt):
        raise _error("V3 semantic page binding changed during live-root replay")
    return _validate_binding_shape(stored)


def project_authenticated_vietocr_semantic_page_binding_v3(
    capability: AuthenticatedVietOCRSemanticPageBindingV3,
) -> dict[str, Any]:
    """Project a descriptive closed binding after complete live replay."""

    return canonical_clone_v1(_authenticated_payload(capability))


def read_authenticated_vietocr_semantic_page_samples_v3(
    capability: AuthenticatedVietOCRSemanticPageBindingV3,
) -> tuple[dict[str, Any], ...]:
    """Read ordered samples after replay; terminal samples retain supplemental status."""

    binding = _authenticated_payload(capability)
    return tuple(canonical_clone_v1(item) for item in binding["samples"])


def validate_authenticated_vietocr_semantic_page_binding_v3(
    value: Any,
    capability: AuthenticatedVietOCRSemanticPageBindingV3,
) -> dict[str, Any]:
    """Bind a descriptive projection back to its exact live opaque handle."""

    candidate = _validate_binding_shape(value)
    expected = _authenticated_payload(capability)
    if not same_typed_json_v1(candidate, expected):
        raise _error("V3 semantic page projection differs from its live capability")
    return canonical_clone_v1(candidate)
