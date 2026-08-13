"""Fail-closed prerequisite contract for the eight-bank maturity panel.

Bank/page locators exist only in the post-freeze evaluation provenance.  A
formal freezer envelope can be emitted only from an opaque live capability
minted after this module has replayed the exact manifest and every referenced
source artifact.  The envelope binds that manifest; only its nested freezer
input is anonymous, and this V1 never emits one while adapter receipts are
unimplemented.

This module does not discover pages, run OCR, implement a future receipt, or
grant semantic, numeric, mapping, accounting, or production authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import weakref
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import Image

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)


class LoanMaturityPanelPrerequisiteV1Error(ValueError):
    """The closed panel, source replay, or anonymous batch boundary drifted."""


class AuthenticatedLoanMaturity8BankPanelPrerequisiteV1:
    """Opaque live capability minted only by complete local artifact replay."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _MINT_TOKEN:
            raise _error("authenticated panel prerequisite cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated panel prerequisite cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated panel prerequisite cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated panel prerequisite cannot be serialized")


FORMAT_VERSION = "LOAN_MATURITY_8BANK_VIETOCR_PANEL_PREREQUISITE_V1"
BATCH_FORMAT_VERSION = "V3_AUTHENTICATED_LINE_MULTIPAGE_BATCH_INPUT_V1"
FORMAL_ENVELOPE_FORMAT_VERSION = "LOAN_MATURITY_8BANK_FORMAL_FREEZER_ENVELOPE_V1"
NONFORMAL_PROPOSAL_FORMAT_VERSION = "LOAN_MATURITY_8BANK_NONFORMAL_BATCH_PROPOSAL_V1"
SELECTION_PROJECTION_FORMAT_VERSION = (
    "LOAN_MATURITY_8BANK_AUTHENTICATED_PANEL_SELECTION_PROJECTION_V1"
)
EXPERIMENT_ID = "E-0044"
FAMILY_ID = "LOAN_MATURITY_BUCKETS"
PANEL_ROLE = "POST_FREEZE_EVALUATION_PROVENANCE_ONLY"
SELECTION_CLAIM = (
    "FIXED_EVALUATION_PANEL_FROM_SOURCE_ONLY_INVENTORY_NOT_A_GENERIC_DISCOVERY_OR_ROUTING_RULE"
)

BANK_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
EXPECTED_LOCATORS = {
    "ACB": (18, "db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86"),
    "MBB": (31, "a86757a4499953264ca22dd57ae2e3257057631107742e1d04ad1ecd0e2c23d1"),
    "VPB": (42, "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"),
    "HDB": (26, "dae87ce9d04a135515dc0211591b21f44d3421eaeccd8258122bfeef3fe5877f"),
    "VCB": (31, "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"),
    "CTG": (39, "f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318"),
    "BID": (22, "73d9ead38e4e60b2241ae7d41a6e5382f8f2e5cc59f2e7a70ca0bedb95792003"),
    "VIB": (33, "416a104007cb0ed20ca43f9771a698f789b812866f7937617ec42be85e0c852c"),
}

READY = "READY_FOR_OPAQUE_ALL_LINE_FREEZE"
BLOCKED = "BLOCKED_HYDRATION"
READY_PANEL = "READY_FOR_SINGLE_OPAQUE_8_PAGE_FREEZE"
BLOCKED_PANEL = "BLOCKED_PENDING_COMPLETE_8_SLOT_HYDRATION"

NATIVE_ADAPTER_ID = "GENERIC_NATIVE_LINE_PIXEL_BINDING_ADAPTER_V1"
RASTER_ADAPTER_ID = "GENERIC_RASTER_LINE_GEOMETRY_REHYDRATOR_V1"
NATIVE_BLOCKERS = (
    "FREEZER_V2_REJECTS_NATIVE_RESULT_FORMAT",
    "NATIVE_PAGE_HAS_NO_AUTHENTICATED_PIXEL_RENDER_BINDING",
)
RASTER_BLOCKERS = (
    "FREEZER_V2_REJECTS_V3_RESULT_FORMAT",
    "TERMINAL_ZERO_AUTHENTICATED_LINE_AXIS",
)

RECEIPT_CONTRACT = "GENERIC_VIETOCR_ALL_LINE_SEMANTIC_RECEIPT_V3_REQUIRED"
V2_INCOMPATIBILITY = (
    "V2_IS_IMMUTABLY_PINNED_TO_A_PRIOR_SELECTED_RUN_GIT_COMMIT_AND_MUST_NOT_BE_RELABELLED"
)

AUTHORITY = {
    "authenticated_adapter_receipt_authority": False,
    "bank_filename_or_physical_page_available_to_reader": False,
    "completed_vietocr_run_authority": False,
    "geometry_or_numeric_authority": False,
    "post_freeze_evaluation_provenance_only": True,
    "receipt_v3_implementation_authority": False,
    "semantic_accounting_or_schema_authority": False,
}
UNIFORM_RUN_REQUIREMENT = {
    "all_eight_slots_required": True,
    "architecture": "vgg19_bn_transformer",
    "fresh_run_state": "PROSPECTIVE_BLOCKED_NO_RUN_OR_RECEIPT_AUTHORITY",
    "legacy_or_per_bank_ocr_authority": False,
    "legacy_outputs_prohibited_as_authority_for_bank_codes": ["MBB", "CTG"],
    "fp32_inference_required": True,
    "model_name": "VietOCR VGG Transformer",
    "model_config_sha256_required": True,
    "model_weights_sha256_required": True,
    "onnx_allowed": False,
    "package_version": "0.3.13",
    "pytorch_runtime_identity_required": True,
    "receipt_contract": RECEIPT_CONTRACT,
    "receipt_contract_implemented_by_this_artifact": False,
    "receipt_v2_incompatibility": V2_INCOMPATIBILITY,
    "receipt_v2_reuse_allowed": False,
    "single_fresh_reader_request_result_run_required": True,
    "transformer_outputs_are_semantic_proposals_only": True,
}

_OBJECT_ROOT = "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256"
_READY_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
_NATIVE_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
_V3_RESULT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
_ADAPTER_REQUIRED_OUTPUT = "AUTHENTICATED_V2_RESULT_RENDER_BINDING_WITH_POSITIVE_COMPLETE_LINE_AXIS"

_INVENTORY_IDENTITIES: dict[str, tuple[Any, ...]] = {
    "ACB": (
        85,
        _READY_RESULT_FORMAT,
        "3d767ca44f550011478aec93c913e20b984d34d02636ac027a7166588f93b0f9",
        272559,
        "f873f85c3496d56042a79731e51b5c56bb3d912c4ab95c18bd7ee54aafa00a81",
        881433,
        "DOMINANT_RASTER_OCR",
        "OCR_WORD_BOX_READ_COMPLETE",
        False,
    ),
    "MBB": (
        109,
        _READY_RESULT_FORMAT,
        "e570d96970aea800da7c49a81bf167f2cccfea431ca4d402a6757d68b87dc668",
        342165,
        "f253a2af180ad5e0a2e4c82600a89f43889a94f503b95ce623e68f10a6a53ba2",
        285224,
        "DOMINANT_RASTER_OCR",
        "OCR_WORD_BOX_READ_COMPLETE",
        False,
    ),
    "VPB": (
        110,
        _NATIVE_RESULT_FORMAT,
        "eb22ccd4e2e212c888b6c7ca8eccecee3d5ccbd0035ef67ef7051aed5a5821d8",
        132520,
        None,
        None,
        "CAUSAL_NATIVE_TEXT",
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        False,
    ),
    "HDB": (
        101,
        _READY_RESULT_FORMAT,
        "f4d6f5826b33d929fcaaf2ba2aa88bdf8728538c9a95b12a013c58f7cd681ce2",
        375934,
        "a90ca4dfbd71893233554eb78e3e866526e19edba6eddd1a9ba9e51398847009",
        923063,
        "DOMINANT_RASTER_OCR",
        "OCR_WORD_BOX_READ_COMPLETE",
        False,
    ),
    "VCB": (
        0,
        _V3_RESULT_FORMAT,
        "610520a41c1a1474b3e060b37537fead86ca43b7035e6063dd25d2cb040780a9",
        5197,
        "46a6eb710fdfbfe3aff4fbe33e8295b2876eeff421b8eefd0ebcc4aa7830aedd",
        1025602,
        "DOMINANT_RASTER_OCR",
        "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        True,
    ),
    "CTG": (
        88,
        _READY_RESULT_FORMAT,
        "d69830fb760a4d45423a6e276c456d6e5dac048b6f7ea5a17904679042c5b7f8",
        369660,
        "b85de39b03a481ee0eb7303b552a72b037401d3d564850a24c64326e679a2b04",
        171140,
        "DOMINANT_RASTER_OCR",
        "OCR_WORD_BOX_READ_COMPLETE",
        False,
    ),
    "BID": (
        87,
        _READY_RESULT_FORMAT,
        "40743637735ec8e1e8f6a080f60ad230218ca4f9fefed699518179a705db3d0f",
        427284,
        "c8486972b896b760b4e7fac01d2ba69ba55127fedd680f88495dc94eae8a7331",
        1286825,
        "DOMINANT_RASTER_OCR",
        "OCR_WORD_BOX_READ_COMPLETE",
        False,
    ),
    "VIB": (
        164,
        _READY_RESULT_FORMAT,
        "bd641f0e9d9710081bd7c5a7acf711bbd9c9db91b0125b88dafc44181fb7b854",
        564164,
        "38ea68385a43a4d211f81cc68a7d62657fda43a0b136d67e9403d9d348fa584d",
        116028,
        "DOMINANT_RASTER_OCR",
        "OCR_WORD_BOX_READ_COMPLETE",
        False,
    ),
}

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOP_FIELDS = {
    "authority",
    "bank_order",
    "experiment_id",
    "family_id",
    "format_version",
    "panel_role",
    "selection_claim",
    "slot_count",
    "slots",
    "state",
    "uniform_run_requirement",
}
_SLOT_FIELDS = {
    "bank_code",
    "freezer_prerequisite",
    "inventory_evidence",
    "physical_page",
    "source_pdf_sha256",
}
_INVENTORY_FIELDS = {
    "authenticated_line_count",
    "render_ref",
    "result_format_version",
    "result_ref",
    "route",
    "status",
    "unresolved",
}
_FREEZER_FIELDS = {
    "adapter_receipt_ref",
    "authenticated_line_count",
    "blocker_codes",
    "hydration_adapter",
    "render_ref",
    "result_ref",
    "state",
}
_ADAPTER_FIELDS = {
    "adapter_id",
    "bank_identity_or_filename_routing_allowed",
    "required_output",
    "selection_basis",
}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_REQUEST_FIELDS = {
    "bank_identity_used",
    "filename_used",
    "format_version",
    "git_commit",
    "historical_values_used",
    "implementation_ledger_sha256",
    "input_ledger_sha256",
    "physical_page",
    "pre_ocr_feature_fingerprint_sha256",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "render_specification",
    "role_a_used",
    "route",
    "route_plan_sha256",
    "schema_used",
    "selection_receipt_sha256",
    "sentinel_sha256",
    "source_sha256",
    "source_size_bytes",
}
_REQUEST_FALSE_FIELDS = {
    "bank_identity_used",
    "filename_used",
    "historical_values_used",
    "role_a_used",
    "schema_used",
}
_REQUEST_SHA_FIELDS = {
    "implementation_ledger_sha256",
    "input_ledger_sha256",
    "pre_ocr_feature_fingerprint_sha256",
    "provider_identity_sha256",
    "route_plan_sha256",
    "selection_receipt_sha256",
    "sentinel_sha256",
}
_RENDER_SPECIFICATION = {
    "alpha": False,
    "annotations": "INCLUDED",
    "colorspace": "RGB",
    "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
}
_SELECTION_PROJECTION_FIELDS = {
    "authority",
    "bank_order",
    "experiment_id",
    "family_id",
    "format_version",
    "manifest_sha256",
    "manifest_size_bytes",
    "panel_state",
    "projection_id",
    "slots",
}
_SELECTION_PROJECTION_SLOT_FIELDS = {
    "bank_code",
    "physical_page",
    "source_pdf_sha256",
}
_SELECTION_PROJECTION_AUTHORITY = {
    "completed_vietocr_run_authority": False,
    "hydration_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "recognition_routing_authority": False,
    "selection_provenance_only": True,
    "semantic_authority": False,
}
_SELECTION_PROJECTION_ID_PREFIX = "lm8bpsv1:projection:"
_SELECTION_PROJECTION_ID_RE = re.compile(
    rf"^{re.escape(_SELECTION_PROJECTION_ID_PREFIX)}[0-9a-f]{{64}}$"
)

_MINT_TOKEN = object()
_AUTHENTICATED_PANELS: weakref.WeakKeyDictionary[
    AuthenticatedLoanMaturity8BankPanelPrerequisiteV1, tuple[bytes, str, bytes, str]
] = weakref.WeakKeyDictionary()


def _error(message: str) -> LoanMaturityPanelPrerequisiteV1Error:
    return LoanMaturityPanelPrerequisiteV1Error(message)


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} must contain the exact closed field set")
    return cast(dict[str, Any], value)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a lowercase SHA-256")
    return value


def _cas_ref(sha256: str, size_bytes: int, suffix: str) -> dict[str, Any]:
    return {
        "path": f"{_OBJECT_ROOT}/{sha256[:2]}/{sha256}.{suffix}",
        "sha256": sha256,
        "size_bytes": size_bytes,
    }


def _ref(value: Any, label: str, suffix: str) -> dict[str, Any]:
    reference = _exact(value, _REF_FIELDS, label)
    sha256 = _sha(reference["sha256"], f"{label} hash")
    size_bytes = reference["size_bytes"]
    if type(size_bytes) is not int or size_bytes <= 0:
        raise _error(f"{label} size is invalid")
    expected = _cas_ref(sha256, size_bytes, suffix)
    if not same_typed_json_v1(reference, expected):
        raise _error(f"{label} is not one canonical project-relative CAS reference")
    return canonical_clone_v1(expected)


def _embedded_render_ref(value: Any, expected: dict[str, Any], label: str) -> dict[str, Any]:
    """Validate the producer schema's object-root-relative render binding."""

    reference = _exact(value, _REF_FIELDS, label)
    sha256 = _sha(reference["sha256"], f"{label} hash")
    size_bytes = reference["size_bytes"]
    if type(size_bytes) is not int or size_bytes <= 0:
        raise _error(f"{label} size is invalid")
    producer_relative = {
        "path": f"objects/sha256/{sha256[:2]}/{sha256}.png",
        "sha256": sha256,
        "size_bytes": size_bytes,
    }
    if (
        not same_typed_json_v1(reference, producer_relative)
        or sha256 != expected["sha256"]
        or size_bytes != expected["size_bytes"]
    ):
        raise _error(f"{label} does not bind the exact replayed render")
    return canonical_clone_v1(reference)


def _expected_inventory(bank_code: str) -> dict[str, Any]:
    (
        line_count,
        result_format,
        result_sha,
        result_size,
        render_sha,
        render_size,
        route,
        status,
        unresolved,
    ) = _INVENTORY_IDENTITIES[bank_code]
    return {
        "authenticated_line_count": line_count,
        "render_ref": (None if render_sha is None else _cas_ref(render_sha, render_size, "png")),
        "result_format_version": result_format,
        "result_ref": _cas_ref(result_sha, result_size, "json"),
        "route": route,
        "status": status,
        "unresolved": unresolved,
    }


def _adapter_payload(adapter_id: str, selection_basis: str) -> dict[str, Any]:
    return {
        "adapter_id": adapter_id,
        "bank_identity_or_filename_routing_allowed": False,
        "required_output": _ADAPTER_REQUIRED_OUTPUT,
        "selection_basis": selection_basis,
    }


def _expected_adapter(inventory: dict[str, Any]) -> dict[str, Any] | None:
    """Select hydration only from the closed source state, never bank identity."""

    source_state = (
        inventory["result_format_version"],
        inventory["route"],
        inventory["status"],
        inventory["render_ref"] is None,
        inventory["authenticated_line_count"] == 0,
        inventory["unresolved"],
    )
    if source_state == (
        _NATIVE_RESULT_FORMAT,
        "CAUSAL_NATIVE_TEXT",
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        True,
        False,
        False,
    ):
        return _adapter_payload(NATIVE_ADAPTER_ID, "SOURCE_ROUTE_AND_MISSING_RENDER_BINDING_ONLY")
    if source_state == (
        _V3_RESULT_FORMAT,
        "DOMINANT_RASTER_OCR",
        "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        False,
        True,
        True,
    ):
        return _adapter_payload(RASTER_ADAPTER_ID, "SOURCE_ROUTE_AND_ZERO_LINE_TERMINAL_STATE_ONLY")
    return None


def _validate_blocked_prerequisite(
    freezer: dict[str, Any], inventory: dict[str, Any], *, label: str
) -> None:
    if any(
        freezer[field] is not None
        for field in (
            "result_ref",
            "render_ref",
            "authenticated_line_count",
            "adapter_receipt_ref",
        )
    ):
        raise _error(f"{label} blocked slot cannot expose a partial freezer input")
    expected_adapter = _expected_adapter(inventory)
    if expected_adapter is None:
        raise _error(f"{label} resolved inventory cannot regress to hydration-blocked")
    expected_blockers = list(
        NATIVE_BLOCKERS if expected_adapter["adapter_id"] == NATIVE_ADAPTER_ID else RASTER_BLOCKERS
    )
    if freezer["blocker_codes"] != expected_blockers or not same_typed_json_v1(
        freezer["hydration_adapter"], expected_adapter
    ):
        raise _error(f"{label} hydration blocker/adapter identity drifted")
    if expected_adapter["adapter_id"] == NATIVE_ADAPTER_ID and not (
        inventory["result_format_version"] == _NATIVE_RESULT_FORMAT
        and inventory["route"] == "CAUSAL_NATIVE_TEXT"
        and inventory["render_ref"] is None
        and inventory["authenticated_line_count"] > 0
    ):
        raise _error(f"{label} native hydration condition drifted")
    if expected_adapter["adapter_id"] == RASTER_ADAPTER_ID and not (
        inventory["result_format_version"] == _V3_RESULT_FORMAT
        and inventory["route"] == "DOMINANT_RASTER_OCR"
        and inventory["render_ref"] is not None
        and inventory["authenticated_line_count"] == 0
        and inventory["unresolved"] is True
    ):
        raise _error(f"{label} raster hydration condition drifted")


def validate_loan_maturity_8bank_panel_prerequisite_v1(value: Any) -> dict[str, Any]:
    """Shape-check a proposal only; this function does not mint replay authority."""

    panel = _exact(value, _TOP_FIELDS, "panel prerequisite")
    if (
        panel["format_version"] != FORMAT_VERSION
        or panel["experiment_id"] != EXPERIMENT_ID
        or panel["family_id"] != FAMILY_ID
        or panel["panel_role"] != PANEL_ROLE
        or panel["selection_claim"] != SELECTION_CLAIM
        or not same_typed_json_v1(panel["bank_order"], list(BANK_ORDER))
        or type(panel["slot_count"]) is not int
        or panel["slot_count"] != len(BANK_ORDER)
        or not same_typed_json_v1(panel["authority"], AUTHORITY)
        or not same_typed_json_v1(panel["uniform_run_requirement"], UNIFORM_RUN_REQUIREMENT)
    ):
        raise _error("panel identity, provenance boundary, or prospective fresh-run policy drifted")
    if type(panel["slots"]) is not list or len(panel["slots"]) != len(BANK_ORDER):
        raise _error("panel must preserve exactly eight slots")

    blocker_count = 0
    seen_results: set[str] = set()
    seen_renders: set[str] = set()
    for ordinal, (raw_slot, expected_bank) in enumerate(
        zip(panel["slots"], BANK_ORDER, strict=True), start=1
    ):
        label = f"slot {ordinal:02d}"
        slot = _exact(raw_slot, _SLOT_FIELDS, label)
        expected_page, expected_source_sha256 = EXPECTED_LOCATORS[expected_bank]
        if (
            type(slot["bank_code"]) is not str
            or slot["bank_code"] != expected_bank
            or type(slot["physical_page"]) is not int
            or slot["physical_page"] != expected_page
            or slot["source_pdf_sha256"] != expected_source_sha256
        ):
            raise _error(f"{label} fixed evaluation provenance drifted")
        _sha(slot["source_pdf_sha256"], f"{label} source PDF")

        inventory = _exact(slot["inventory_evidence"], _INVENTORY_FIELDS, f"{label} inventory")
        _ref(inventory["result_ref"], f"{label} inventory result", "json")
        if inventory["render_ref"] is not None:
            _ref(inventory["render_ref"], f"{label} inventory render", "png")
        if not same_typed_json_v1(inventory, _expected_inventory(expected_bank)):
            raise _error(f"{label} exact source-only inventory identity drifted")

        freezer = _exact(
            slot["freezer_prerequisite"], _FREEZER_FIELDS, f"{label} freezer prerequisite"
        )
        if freezer["state"] == READY:
            result_ref = _ref(freezer["result_ref"], f"{label} freezer result", "json")
            render_ref = _ref(freezer["render_ref"], f"{label} freezer render", "png")
            count = freezer["authenticated_line_count"]
            if type(count) is not int or count <= 0 or freezer["blocker_codes"] != []:
                raise _error(f"{label} ready freezer prerequisite is incomplete")
            adapter = _expected_adapter(inventory)
            if adapter is None:
                if (
                    freezer["adapter_receipt_ref"] is not None
                    or freezer["hydration_adapter"] is not None
                    or not (
                        same_typed_json_v1(result_ref, inventory["result_ref"])
                        and same_typed_json_v1(render_ref, inventory["render_ref"])
                        and count == inventory["authenticated_line_count"]
                    )
                ):
                    raise _error(f"{label} resolved inventory/freezer identity drifted")
            else:
                raise _error(
                    f"{label} cannot transition to ready in V1 without a versioned "
                    "authenticated adapter-receipt replay contract"
                )
            if result_ref["sha256"] in seen_results or render_ref["sha256"] in seen_renders:
                raise _error("panel contains duplicate freezer page inputs")
            seen_results.add(result_ref["sha256"])
            seen_renders.add(render_ref["sha256"])
        elif freezer["state"] == BLOCKED:
            blocker_count += 1
            _validate_blocked_prerequisite(freezer, inventory, label=label)
        else:
            raise _error(f"{label} freezer state is invalid")

    expected_state = BLOCKED_PANEL if blocker_count else READY_PANEL
    if panel["state"] != expected_state:
        raise _error("panel aggregate hydration state drifted")
    return canonical_clone_v1(panel)


def _safe_relative_path(value: Path | str, label: str, suffix: str) -> Path:
    if type(value) is str:
        text = value
    elif isinstance(value, Path):
        text = value.as_posix()
    else:
        raise _error(f"{label} path type is invalid")
    if not text or "\\" in text:
        raise _error(f"{label} path is not canonical project-relative POSIX")
    path = Path(text)
    if (
        path.is_absolute()
        or text != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix != suffix
    ):
        raise _error(f"{label} path is not canonical project-relative POSIX")
    return path


def _stable_nofollow_bytes(root: Path, relative: Path | str, label: str) -> bytes:
    path = _safe_relative_path(relative, label, Path(relative).suffix)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        current = os.open(root, directory_flags)
    except OSError as exc:
        raise _error(f"cannot open project root for {label}") from exc
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

        def identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
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
    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite constant {value}")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _error(f"cannot decode {label} as strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return cast(dict[str, Any], value)


def _remember_snapshot(
    snapshots: dict[str, bytes], relative: str, payload: bytes, label: str
) -> None:
    previous = snapshots.setdefault(relative, payload)
    if previous != payload:
        raise _error(f"{label} changed between repeated reads")


def _read_ref(
    root: Path,
    reference: dict[str, Any],
    label: str,
    suffix: str,
    snapshots: dict[str, bytes],
) -> bytes:
    ref = _ref(reference, label, suffix)
    payload = _stable_nofollow_bytes(root, ref["path"], label)
    if len(payload) != ref["size_bytes"] or hashlib.sha256(payload).hexdigest() != ref["sha256"]:
        raise _error(f"{label} is hash- or size-drifted")
    _remember_snapshot(snapshots, ref["path"], payload, label)
    return payload


def _png_dimensions(payload: bytes, label: str) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format != "PNG":
                raise _error(f"{label} is not a PNG render")
            image.load()
            width, height = image.size
    except (OSError, ValueError) as exc:
        raise _error(f"{label} is not a readable PNG render") from exc
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise _error(f"{label} dimensions are invalid")
    return width, height


def _validate_result_common(
    result: dict[str, Any],
    *,
    slot: dict[str, Any],
    expected_format: str,
    expected_route: str,
    expected_status: str,
    expected_line_count: int,
    expected_render_ref: dict[str, Any] | None,
    label: str,
) -> list[dict[str, Any]]:
    lines = result.get("lines")
    request = _exact(result.get("request"), _REQUEST_FIELDS, f"{label} request")
    request_sha256 = _sha(result.get("request_sha256"), f"{label} request identity")
    request_source_size = request["source_size_bytes"]
    safety = result.get("safety")
    metrics = result.get("metrics")
    for field in _REQUEST_SHA_FIELDS:
        _sha(request[field], f"{label} request {field}")
    if (
        result.get("format_version") != expected_format
        or result.get("route") != expected_route
        or result.get("status") != expected_status
        or type(result.get("physical_page")) is not int
        or result.get("physical_page") != slot["physical_page"]
        or result.get("source_sha256") != slot["source_pdf_sha256"]
        or type(lines) is not list
        or len(lines) != expected_line_count
        or any(type(line) is not dict for line in lines)
        or request.get("format_version") != "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1"
        or request_sha256 != hashlib.sha256(canonical_json_bytes_v1(request)).hexdigest()
        or request.get("source_sha256") != slot["source_pdf_sha256"]
        or type(request_source_size) is not int
        or request_source_size <= 0
        or type(result.get("source_size_bytes")) is not int
        or result.get("source_size_bytes") != request_source_size
        or type(request.get("physical_page")) is not int
        or request.get("physical_page") != slot["physical_page"]
        or request.get("route") != expected_route
        or any(request[field] is not False for field in _REQUEST_FALSE_FIELDS)
        or type(request.get("git_commit")) is not str
        or re.fullmatch(r"[0-9a-f]{40}", request["git_commit"]) is None
        or result.get("provider_identity_sha256") != request["provider_identity_sha256"]
        or result.get("render_runtime_identity_sha256") != request["render_runtime_identity_sha256"]
        or result.get("source_blank_claimed") is not False
        or type(safety) is not dict
        or not safety
        or any(value is not False for value in safety.values())
        or type(metrics) is not dict
        or type(metrics.get("line_count")) is not int
        or metrics.get("line_count") != expected_line_count
        or type(result.get("words")) is not list
    ):
        raise _error(f"{label} producer identity, firewall, or line denominator drifted")
    if expected_render_ref is None:
        if (
            request["render_runtime_identity_sha256"] is not None
            or request["render_specification"] is not None
        ):
            raise _error(f"{label} native producer unexpectedly selected a render")
    else:
        _sha(request["render_runtime_identity_sha256"], f"{label} render runtime")
        render_specification = request["render_specification"]
        if (
            type(render_specification) is not dict
            or set(render_specification) != {*_RENDER_SPECIFICATION, "dpi"}
            or any(
                render_specification[field] != expected
                for field, expected in _RENDER_SPECIFICATION.items()
            )
            or type(render_specification["dpi"]) is not int
            or render_specification["dpi"] not in {200, 300}
        ):
            raise _error(f"{label} render producer specification drifted")
    binding = result.get("input_render_ref")
    if expected_render_ref is None:
        if binding is not None:
            raise _error(f"{label} unexpectedly acquired a render binding")
    else:
        _embedded_render_ref(binding, expected_render_ref, f"{label} embedded render")
    return cast(list[dict[str, Any]], lines)


def _validate_line_bboxes(lines: list[dict[str, Any]], width: int, height: int, label: str) -> None:
    for index, line in enumerate(lines):
        bbox = line.get("raw_pixel_bbox")
        if (
            type(bbox) is not list
            or len(bbox) != 4
            or any(type(value) is not int for value in bbox)
        ):
            raise _error(f"{label} line {index} has no exact raw-pixel bbox")
        x0, y0, x1, y1 = bbox
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise _error(f"{label} line {index} bbox lies outside its render")


def _mint_panel(
    panel: dict[str, Any],
    manifest_payload: bytes,
) -> AuthenticatedLoanMaturity8BankPanelPrerequisiteV1:
    payload = canonical_json_bytes_v1(validate_loan_maturity_8bank_panel_prerequisite_v1(panel))
    capability = AuthenticatedLoanMaturity8BankPanelPrerequisiteV1(_MINT_TOKEN)
    _AUTHENTICATED_PANELS[capability] = (
        payload,
        hashlib.sha256(payload).hexdigest(),
        manifest_payload,
        hashlib.sha256(manifest_payload).hexdigest(),
    )
    return capability


def _panel_payload(
    capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(capability) is not AuthenticatedLoanMaturity8BankPanelPrerequisiteV1:
        raise _error("formal freezer input requires one replay-authenticated panel capability")
    stored = _AUTHENTICATED_PANELS.get(capability)
    if stored is None:
        raise _error("authenticated panel prerequisite is unknown or expired")
    payload, digest, manifest_payload, manifest_digest = stored
    if (
        hashlib.sha256(payload).hexdigest() != digest
        or hashlib.sha256(manifest_payload).hexdigest() != manifest_digest
    ):
        raise _error("authenticated panel prerequisite bytes drifted")
    panel = validate_loan_maturity_8bank_panel_prerequisite_v1(
        decode_canonical_json_bytes_v1(payload)
    )
    replayed_manifest = validate_loan_maturity_8bank_panel_prerequisite_v1(
        _strict_json(manifest_payload, "authenticated panel manifest snapshot")
    )
    if not same_typed_json_v1(panel, replayed_manifest):
        raise _error("authenticated manifest snapshot and canonical panel drifted")
    return panel, {
        "experiment_id": panel["experiment_id"],
        "format_version": panel["format_version"],
        "manifest_sha256": manifest_digest,
        "manifest_size_bytes": len(manifest_payload),
        "prospective_semantic_receipt_contract": panel["uniform_run_requirement"][
            "receipt_contract"
        ],
    }


def replay_loan_maturity_8bank_panel_prerequisite_v1(
    project_root: Path, manifest_path: Path
) -> tuple[dict[str, Any], AuthenticatedLoanMaturity8BankPanelPrerequisiteV1]:
    """Replay all exact local refs and mint an immutable live capability."""

    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise _error("project root is not a directory")
    manifest_relative = _safe_relative_path(manifest_path, "panel manifest", ".json")
    manifest_payload = _stable_nofollow_bytes(root, manifest_relative, "panel manifest")
    panel = validate_loan_maturity_8bank_panel_prerequisite_v1(
        _strict_json(manifest_payload, "panel manifest")
    )
    snapshots: dict[str, bytes] = {manifest_relative.as_posix(): manifest_payload}

    for ordinal, slot in enumerate(panel["slots"], start=1):
        label = f"slot {ordinal:02d}"
        inventory = slot["inventory_evidence"]
        inventory_result_payload = _read_ref(
            root, inventory["result_ref"], f"{label} inventory result", "json", snapshots
        )
        inventory_result = _strict_json(inventory_result_payload, f"{label} inventory result")
        if inventory["render_ref"] is None:
            inventory_dimensions = None
        else:
            inventory_render_payload = _read_ref(
                root,
                inventory["render_ref"],
                f"{label} inventory render",
                "png",
                snapshots,
            )
            inventory_dimensions = _png_dimensions(
                inventory_render_payload, f"{label} inventory render"
            )
        inventory_lines = _validate_result_common(
            inventory_result,
            slot=slot,
            expected_format=inventory["result_format_version"],
            expected_route=inventory["route"],
            expected_status=inventory["status"],
            expected_line_count=inventory["authenticated_line_count"],
            expected_render_ref=inventory["render_ref"],
            label=f"{label} inventory result",
        )
        if inventory["result_format_version"] == _READY_RESULT_FORMAT:
            assert inventory_dimensions is not None
            _validate_line_bboxes(
                inventory_lines, *inventory_dimensions, f"{label} inventory result"
            )

        freezer = slot["freezer_prerequisite"]
        if freezer["state"] != READY:
            continue
        freezer_result_payload = _read_ref(
            root, freezer["result_ref"], f"{label} freezer result", "json", snapshots
        )
        freezer_render_payload = _read_ref(
            root, freezer["render_ref"], f"{label} freezer render", "png", snapshots
        )
        freezer_dimensions = _png_dimensions(freezer_render_payload, f"{label} freezer render")
        freezer_result = _strict_json(freezer_result_payload, f"{label} freezer result")
        freezer_lines = _validate_result_common(
            freezer_result,
            slot=slot,
            expected_format=_READY_RESULT_FORMAT,
            expected_route="DOMINANT_RASTER_OCR",
            expected_status="OCR_WORD_BOX_READ_COMPLETE",
            expected_line_count=freezer["authenticated_line_count"],
            expected_render_ref=freezer["render_ref"],
            label=f"{label} freezer result",
        )
        if not freezer_lines:
            raise _error(f"{label} freezer result has no positive all-LINE denominator")
        _validate_line_bboxes(freezer_lines, *freezer_dimensions, f"{label} freezer result")

    for relative, expected in snapshots.items():
        if _stable_nofollow_bytes(root, relative, f"final snapshot {relative}") != expected:
            raise _error(f"{relative} changed during panel replay")
    return panel, _mint_panel(panel, manifest_payload)


def _anonymous_freezer_input_or_none_v1(panel: dict[str, Any]) -> dict[str, Any] | None:
    blocked = [slot for slot in panel["slots"] if slot["freezer_prerequisite"]["state"] != READY]
    if blocked:
        return None
    return {
        "dataset_role": "DEVELOPMENT_REPLAY",
        "format_version": BATCH_FORMAT_VERSION,
        "pages": [
            {
                "render_ref": canonical_clone_v1(slot["freezer_prerequisite"]["render_ref"]),
                "result_ref": canonical_clone_v1(slot["freezer_prerequisite"]["result_ref"]),
            }
            for slot in panel["slots"]
        ],
    }


def _build_nonformal_opaque_freezer_input_proposal_v1(panel: dict[str, Any]) -> dict[str, Any]:
    """Build a conspicuously non-formal shape proposal without replay authority."""

    validated = validate_loan_maturity_8bank_panel_prerequisite_v1(panel)
    candidate = _anonymous_freezer_input_or_none_v1(validated)
    return {
        "authority": {
            "formal_replay_authority": False,
            "reader_facing_payload": False,
        },
        "candidate_opaque_freezer_input": candidate,
        "format_version": NONFORMAL_PROPOSAL_FORMAT_VERSION,
        "panel_state": validated["state"],
        "state": (
            "NONFORMAL_BLOCKED_SHAPE_ONLY_PROPOSAL"
            if candidate is None
            else "NONFORMAL_COMPLETE_SHAPE_ONLY_PROPOSAL"
        ),
    }


def _formal_envelope_v1(
    panel: dict[str, Any], prerequisite_binding: dict[str, Any]
) -> dict[str, Any]:
    opaque_input = _anonymous_freezer_input_or_none_v1(panel)
    return {
        "authority": {
            "authenticated_adapter_receipt_authority": False,
            "authenticated_prerequisite_manifest_replay": True,
            "completed_vietocr_run_authority": False,
            "reader_facing_payload": False,
            "semantic_receipt_authority": False,
        },
        "format_version": FORMAL_ENVELOPE_FORMAT_VERSION,
        "opaque_freezer_input": opaque_input,
        "panel_state": panel["state"],
        "prerequisite_binding": canonical_clone_v1(prerequisite_binding),
        "state": (
            "AUTHENTICATED_PREREQUISITE_REPLAY_BLOCKED_NO_FREEZER_INPUT"
            if opaque_input is None
            else "AUTHENTICATED_PREREQUISITE_REPLAY_READY_FOR_TRUSTED_FREEZER"
        ),
    }


def build_formal_panel_replay_envelope_v1(
    capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
) -> dict[str, Any]:
    """Bind the exact replayed manifest while retaining non-reader provenance."""

    panel, prerequisite_binding = _panel_payload(capability)
    return _formal_envelope_v1(panel, prerequisite_binding)


def _selection_projection_v1(
    panel: dict[str, Any], prerequisite_binding: dict[str, Any]
) -> dict[str, Any]:
    payload = {
        "authority": canonical_clone_v1(_SELECTION_PROJECTION_AUTHORITY),
        "bank_order": canonical_clone_v1(panel["bank_order"]),
        "experiment_id": panel["experiment_id"],
        "family_id": panel["family_id"],
        "format_version": SELECTION_PROJECTION_FORMAT_VERSION,
        "manifest_sha256": prerequisite_binding["manifest_sha256"],
        "manifest_size_bytes": prerequisite_binding["manifest_size_bytes"],
        "panel_state": panel["state"],
        "slots": [
            {
                "bank_code": slot["bank_code"],
                "physical_page": slot["physical_page"],
                "source_pdf_sha256": slot["source_pdf_sha256"],
            }
            for slot in panel["slots"]
        ],
    }
    payload["projection_id"] = (
        f"{_SELECTION_PROJECTION_ID_PREFIX}"
        f"{hashlib.sha256(canonical_json_bytes_v1(payload)).hexdigest()}"
    )
    return cast(dict[str, Any], canonical_clone_v1(payload))


def _validate_selection_projection_shape_v1(value: Any) -> dict[str, Any]:
    projection = _exact(
        value, _SELECTION_PROJECTION_FIELDS, "authenticated panel selection projection"
    )
    manifest_size_bytes = projection["manifest_size_bytes"]
    projection_id = projection["projection_id"]
    if (
        projection["format_version"] != SELECTION_PROJECTION_FORMAT_VERSION
        or projection["experiment_id"] != EXPERIMENT_ID
        or projection["family_id"] != FAMILY_ID
        or not same_typed_json_v1(projection["bank_order"], list(BANK_ORDER))
        or projection["panel_state"] not in {BLOCKED_PANEL, READY_PANEL}
        or not same_typed_json_v1(projection["authority"], _SELECTION_PROJECTION_AUTHORITY)
        or type(manifest_size_bytes) is not int
        or manifest_size_bytes <= 0
        or type(projection_id) is not str
        or _SELECTION_PROJECTION_ID_RE.fullmatch(projection_id) is None
    ):
        raise _error("authenticated panel selection projection identity drifted")
    _sha(projection["manifest_sha256"], "selection projection manifest")
    slots = projection["slots"]
    if type(slots) is not list or len(slots) != len(BANK_ORDER):
        raise _error("selection projection must preserve exactly eight slots")
    for ordinal, (raw_slot, expected_bank) in enumerate(
        zip(slots, BANK_ORDER, strict=True), start=1
    ):
        slot = _exact(
            raw_slot,
            _SELECTION_PROJECTION_SLOT_FIELDS,
            f"selection projection slot {ordinal:02d}",
        )
        if (
            type(slot["bank_code"]) is not str
            or slot["bank_code"] != expected_bank
            or type(slot["physical_page"]) is not int
            or slot["physical_page"] <= 0
        ):
            raise _error(f"selection projection slot {ordinal:02d} identity drifted")
        _sha(
            slot["source_pdf_sha256"],
            f"selection projection slot {ordinal:02d} source PDF",
        )
    identity_payload = canonical_clone_v1(projection)
    del identity_payload["projection_id"]
    expected_projection_id = (
        f"{_SELECTION_PROJECTION_ID_PREFIX}"
        f"{hashlib.sha256(canonical_json_bytes_v1(identity_payload)).hexdigest()}"
    )
    if projection_id != expected_projection_id:
        raise _error("authenticated panel selection projection hash identity drifted")
    return canonical_clone_v1(projection)


def project_authenticated_loan_maturity_8bank_panel_selection_v1(
    capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
) -> dict[str, Any]:
    """Project replay-authenticated selection provenance, never reader routing."""

    panel, prerequisite_binding = _panel_payload(capability)
    return _validate_selection_projection_shape_v1(
        _selection_projection_v1(panel, prerequisite_binding)
    )


def validate_authenticated_loan_maturity_8bank_panel_selection_v1(
    value: Any,
    capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
) -> dict[str, Any]:
    """Bind a closed selection projection back to its live replay capability."""

    projection = _validate_selection_projection_shape_v1(value)
    expected = project_authenticated_loan_maturity_8bank_panel_selection_v1(capability)
    if not same_typed_json_v1(projection, expected):
        raise _error("selection projection does not match its replay capability")
    return canonical_clone_v1(projection)


def build_opaque_freezer_input_v1(
    capability: AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
) -> dict[str, Any]:
    """Emit a formal envelope only when all eight replayed inputs are ready."""

    panel, prerequisite_binding = _panel_payload(capability)
    blocked = [slot for slot in panel["slots"] if slot["freezer_prerequisite"]["state"] != READY]
    if blocked:
        details = ", ".join(
            f"{slot['bank_code']}:{'+'.join(slot['freezer_prerequisite']['blocker_codes'])}"
            for slot in blocked
        )
        raise _error(f"refusing a partial eight-slot freezer batch; blocked={details}")
    return _formal_envelope_v1(panel, prerequisite_binding)


__all__ = [
    "AuthenticatedLoanMaturity8BankPanelPrerequisiteV1",
    "BANK_ORDER",
    "BLOCKED",
    "BLOCKED_PANEL",
    "EXPECTED_LOCATORS",
    "EXPERIMENT_ID",
    "FORMAT_VERSION",
    "FORMAL_ENVELOPE_FORMAT_VERSION",
    "LoanMaturityPanelPrerequisiteV1Error",
    "READY",
    "READY_PANEL",
    "RECEIPT_CONTRACT",
    "SELECTION_PROJECTION_FORMAT_VERSION",
    "build_formal_panel_replay_envelope_v1",
    "build_opaque_freezer_input_v1",
    "project_authenticated_loan_maturity_8bank_panel_selection_v1",
    "replay_loan_maturity_8bank_panel_prerequisite_v1",
    "validate_authenticated_loan_maturity_8bank_panel_selection_v1",
    "validate_loan_maturity_8bank_panel_prerequisite_v1",
]
