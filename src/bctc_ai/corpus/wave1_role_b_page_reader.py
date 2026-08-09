from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import tomllib
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

import fitz
import yaml

from bctc_ai.core.hashing import sha256_bytes


class WaveOneRoleBPageReaderError(RuntimeError):
    """Wave 1 page-read evidence cannot be produced without guessing."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-role-b-page-reader-v1.yaml")
IMPLEMENTATION_RELATIVE_PATHS = (
    POLICY_RELATIVE_PATH,
    Path("config/ocr/causal-native-text-v1.yaml"),
    Path("config/ocr/native-text-quality-v2.yaml"),
    Path("src/bctc_ai/core/contracts.py"),
    Path("src/bctc_ai/core/coordinates.py"),
    Path("src/bctc_ai/core/hashing.py"),
    Path("src/bctc_ai/core/text.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_page_reader.py"),
    Path("src/bctc_ai/ocr/_causal_visibility_core.py"),
    Path("src/bctc_ai/ocr/causal_native_text.py"),
    Path("src/bctc_ai/ocr/native_text_quality_v2.py"),
    Path("src/bctc_ai/ocr/pdf_text.py"),
    Path("src/bctc_ai/ocr/ppocrv6_page_session.py"),
    Path("src/bctc_ai/rendering/page_reader.py"),
    Path("src/bctc_ai/storage/content_store.py"),
    Path("scripts/corpus/run_wave1_role_b_page_reader.py"),
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROUTES = ("DOMINANT_RASTER_OCR", "CAUSAL_NATIVE_TEXT", "UNRESOLVED_PAGE_ROUTE")
_SELECTION_FIELDS = ("bank", "document_id", "sha256", "size_bytes", "relative_path")


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _stable_bytes(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise WaveOneRoleBPageReaderError(
            f"{label} cannot be opened as a non-symlink file"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise WaveOneRoleBPageReaderError(f"{label} is not a regular file")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or len(payload) != before.st_size:
        raise WaveOneRoleBPageReaderError(f"{label} changed while being read")
    return payload


def _project_path(project_root: Path, value: str, label: str) -> Path:
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise WaveOneRoleBPageReaderError(f"{label} is not a canonical project path")
    lexical = project_root / Path(*pure.parts)
    current = project_root
    for part in pure.parts:
        current = current / part
        try:
            identity = current.stat(follow_symlinks=False)
        except FileNotFoundError:
            break
        if stat.S_ISLNK(identity.st_mode):
            raise WaveOneRoleBPageReaderError(f"{label} traverses a symlink")
    resolved = lexical.resolve()
    if not resolved.is_relative_to(project_root) or resolved != lexical:
        raise WaveOneRoleBPageReaderError(f"{label} escapes the project root")
    return resolved


def load_wave_one_role_b_page_reader_policy(
    path: Path,
    project_root: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    expected_path = project_root / POLICY_RELATIVE_PATH
    supplied_path = Path(os.path.abspath(path))
    if supplied_path != expected_path:
        raise WaveOneRoleBPageReaderError("Wave 1 page-reader policy path drifted")
    validated_path = _project_path(
        project_root,
        POLICY_RELATIVE_PATH.as_posix(),
        "Wave 1 page-reader policy",
    )
    try:
        policy = yaml.safe_load(_stable_bytes(validated_path, "page-reader policy"))
    except yaml.YAMLError as error:
        raise WaveOneRoleBPageReaderError("Wave 1 page-reader policy is invalid YAML") from error
    expected_root = {
        "version": 1,
        "policy": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READER_V1",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
    }
    expected_root_fields = {
        *expected_root,
        "upstream",
        "routing",
        "render",
        "sentinel",
        "readers",
        "execution",
        "safety",
        "expected_accounting",
        "output",
    }
    if (
        not isinstance(policy, dict)
        or set(policy) != expected_root_fields
        or any(policy.get(key) != value for key, value in expected_root.items())
    ):
        raise WaveOneRoleBPageReaderError("Wave 1 page-reader policy identity drifted")
    upstream = policy.get("upstream")
    routing = policy.get("routing")
    render = policy.get("render")
    sentinel = policy.get("sentinel")
    readers = policy.get("readers")
    safety = policy.get("safety")
    expected = policy.get("expected_accounting")
    output = policy.get("output")
    execution = policy.get("execution")
    if any(
        not isinstance(section, dict)
        for section in (
            upstream,
            routing,
            render,
            sentinel,
            readers,
            execution,
            safety,
            expected,
            output,
        )
    ):
        raise WaveOneRoleBPageReaderError("Wave 1 page-reader policy sections are malformed")
    if (
        set(upstream)
        != {
            "mode",
            "selection_receipt_binding",
            "inventory",
            "pre_ocr_structure",
        }
        or upstream.get("mode") != "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY"
        or upstream.get("selection_receipt_binding") != "DERIVE_AND_RECONCILE_AT_RUNTIME"
    ):
        raise WaveOneRoleBPageReaderError("selection receipt is not dynamically bound")
    for identity in (upstream.get("inventory"), upstream.get("pre_ocr_structure")):
        if not isinstance(identity, dict) or set(identity) != {"path", "sha256", "size_bytes"}:
            raise WaveOneRoleBPageReaderError("upstream artifact identity fields drifted")
    required_route = {
        "dominant_raster_route": "DOMINANT_RASTER_OCR",
        "causal_native_route": "CAUSAL_NATIVE_TEXT",
        "unresolved_route": "UNRESOLVED_PAGE_ROUTE",
        "dominant_raster_predicate": "HAS_DOMINANT_DISPLAYED_RASTER",
        "causal_native_predicate": "SUBSTANTIVE_NONZERO_ALPHA_TEXT_AND_NONDOMINANT_RASTER",
        "bank_identity_used": False,
        "filename_used": False,
        "role_a_used": False,
        "schema_used": False,
    }
    if set(routing) != set(required_route) or any(
        routing.get(key) != value for key, value in required_route.items()
    ):
        raise WaveOneRoleBPageReaderError("page-reader route contract drifted")
    required_render = {
        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
        "colorspace": "RGB",
        "alpha": False,
        "annotations": "INCLUDED",
        "default_dpi": 200,
        "preserved_source_dpi_band": "300",
        "preserved_band_render_dpi": 300,
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "matrix_convention": "COLUMN_VECTOR_3X3_RATIONAL",
    }
    if (
        set(render)
        != {
            *required_render,
            "implicit_orientation_classification",
            "implicit_unwarping",
            "implicit_textline_orientation",
        }
        or any(render.get(key) != value for key, value in required_render.items())
        or any(
            render.get(key) is not False
            for key in (
                "implicit_orientation_classification",
                "implicit_unwarping",
                "implicit_textline_orientation",
            )
        )
    ):
        raise WaveOneRoleBPageReaderError("page-reader render contract drifted")
    expected_sentinel = {
        "status": "STRUCTURAL_CAPACITY_SENTINEL_ONLY",
        "route": "DOMINANT_RASTER_OCR",
        "stratum_fields": [
            "dominant_image_effective_dpi_band",
            "effective_orientation",
            "source_route_quadrant",
            "pdf_rotation_degrees",
        ],
        "rank_material": "SELECTION_RECEIPT_PIPE_SOURCE_SHA256_PIPE_PHYSICAL_PAGE",
        "primary_per_nonempty_stratum": 1,
        "largest_strata_extra_count": 4,
        "extra_ordinal_within_stratum": 2,
        "bank_identity_used": False,
    }
    if set(sentinel) != set(expected_sentinel) or any(
        sentinel.get(key) != value for key, value in expected_sentinel.items()
    ):
        raise WaveOneRoleBPageReaderError("structural sentinel contract drifted")
    expected_execution = {
        "maximum_document_workers": 2,
        "minimum_free_space_bytes": 53687091200,
        "per_document_locking": "FLOCK_EXCLUSIVE",
        "checkpoint": "ATOMIC_AFTER_EVERY_PAGE",
        "orphan_adoption": "FULL_REQUEST_IDENTITY_ONLY",
        "overwrite_allowed": False,
    }
    if set(execution) != set(expected_execution) or any(
        execution.get(key) != value for key, value in expected_execution.items()
    ):
        raise WaveOneRoleBPageReaderError("page-reader execution contract drifted")
    expected_reader_fields = {"ppocrv6", "causal_native"}
    expected_ppocr = {
        "configuration_path": "config/models/pp-ocrv6-word-box.yaml",
        "runtime_manifest_path": "config/models/gpu-runtime.toml",
        "runtime_freeze_path": "config/models/gpu-requirements.freeze.txt",
        "model_keys": ["pp_ocrv6_medium_det", "pp_ocrv6_medium_rec"],
        "device": "cpu",
        "precision": "fp32",
        "mkldnn": False,
        "cpu_threads_per_session": 6,
        "max_document_workers": 2,
        "network_policy": "PYTHON_AUDIT_SOCKET_CONNECT_DENIED",
    }
    expected_native = {
        "policy_path": "config/ocr/causal-native-text-v1.yaml",
        "quality_policy_path": "config/ocr/native-text-quality-v2.yaml",
        "ocr_fallback_allowed": False,
    }
    if (
        set(readers) != expected_reader_fields
        or not isinstance(readers.get("ppocrv6"), dict)
        or not isinstance(readers.get("causal_native"), dict)
        or set(readers["ppocrv6"]) != set(expected_ppocr)
        or set(readers["causal_native"]) != set(expected_native)
        or any(readers["ppocrv6"].get(key) != value for key, value in expected_ppocr.items())
        or any(readers["causal_native"].get(key) != value for key, value in expected_native.items())
    ):
        raise WaveOneRoleBPageReaderError("page-reader provider contract drifted")
    false_safety = (
        "dataset_role_inputs_allowed",
        "role_a_inputs_allowed",
        "schema_inputs_allowed",
        "prior_mapping_outputs_allowed",
        "historical_values_allowed",
        "statement_classification_allowed",
        "table_classification_allowed",
        "row_reconstruction_allowed",
        "cell_semantics_allowed",
        "absence_declarations_allowed",
        "bank_specific_parser_rules_allowed",
    )
    if any(safety.get(key) is not False for key in false_safety):
        raise WaveOneRoleBPageReaderError("page-reader safety boundary drifted")
    if safety.get("selected_source_pdf_allowlist") != (
        "DERIVED_EXACTLY_FROM_RECEIPT_BOUND_INVENTORY"
    ):
        raise WaveOneRoleBPageReaderError("source PDF allowlist is not receipt-bound")
    expected_allowed = [
        "config/corpus/bank-corpus-wave-1-role-b-page-reader-v1.yaml",
        "output/development/bank-corpus-survey-v1/corpus-inventory.json",
        "output/development/bank-corpus-survey-v1/wave-1-pre-ocr-structure-features.json",
        "config/models/pp-ocrv6-word-box.yaml",
        "config/models/gpu-runtime.toml",
        "config/models/gpu-requirements.freeze.txt",
        "config/ocr/causal-native-text-v1.yaml",
        "config/ocr/native-text-quality-v2.yaml",
    ]
    expected_forbidden = [
        "dataset_roles",
        "role-a",
        "role_a",
        "schema",
        "mapping",
        "historical",
        "question_for_user",
        "experiment",
    ]
    expected_safety_fields = {
        "allowed_project_inputs",
        "selected_source_pdf_allowlist",
        "forbidden_path_fragments",
        *false_safety,
    }
    if (
        set(safety) != expected_safety_fields
        or safety.get("allowed_project_inputs") != expected_allowed
        or safety.get("forbidden_path_fragments") != expected_forbidden
    ):
        raise WaveOneRoleBPageReaderError("page-reader input allowlist drifted")
    expected_accounting = {
        "selected_document_count": 27,
        "total_physical_page_count": 1449,
        "route_page_counts": {
            "DOMINANT_RASTER_OCR": 1356,
            "CAUSAL_NATIVE_TEXT": 93,
            "UNRESOLVED_PAGE_ROUTE": 0,
        },
        "ocr_render_dpi_page_counts": {"200": 1250, "300": 106},
        "ocr_structural_stratum_count": 20,
        "structural_sentinel_page_count": 24,
    }
    if set(expected) != set(expected_accounting) or expected != expected_accounting:
        raise WaveOneRoleBPageReaderError("expected Wave 1 accounting contract drifted")
    expected_output = {
        "format": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V1",
        "object_store_directory": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/objects",
        "checkpoint_directory": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/checkpoints",
        "plan_filename": "wave-1-role-b-page-read-plan.json",
        "manifest_filename": "wave-1-role-b-page-reads.json",
        "canonical_json": True,
        "exclusive_no_overwrite": True,
    }
    if set(output) != set(expected_output) or output != expected_output:
        raise WaveOneRoleBPageReaderError("page-reader output contract drifted")
    return policy


def _bound_json(
    project_root: Path,
    identity: dict[str, Any],
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(identity, dict):
        raise WaveOneRoleBPageReaderError(f"{label} identity is malformed")
    path = _project_path(project_root, str(identity.get("path", "")), label)
    payload = _stable_bytes(path, label)
    expected_hash = identity.get("sha256")
    expected_size = identity.get("size_bytes")
    if (
        not isinstance(expected_hash, str)
        or not _SHA256.fullmatch(expected_hash)
        or len(payload) != expected_size
        or sha256_bytes(payload) != expected_hash
    ):
        raise WaveOneRoleBPageReaderError(f"{label} byte identity drifted")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WaveOneRoleBPageReaderError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise WaveOneRoleBPageReaderError(f"{label} must be a JSON object")
    return value, {
        "phase": "PLAN",
        "kind": label.upper().replace(" ", "_"),
        "path": identity["path"],
        "sha256": expected_hash,
        "size_bytes": expected_size,
    }


def _route(features: dict[str, Any]) -> str:
    if features.get("has_dominant_displayed_raster") is True:
        return "DOMINANT_RASTER_OCR"
    if (
        features.get("has_dominant_displayed_raster") is False
        and features.get("substantive_nonzero_alpha_text_layer") is True
        and features.get("source_route_quadrant") == "TEXT_LAYER_AND_NONDOMINANT_RASTER"
    ):
        return "CAUSAL_NATIVE_TEXT"
    return "UNRESOLVED_PAGE_ROUTE"


def _sentinel_rank(selection_receipt: str, source_sha256: str, page: int) -> str:
    return hashlib.sha256(f"{selection_receipt}|{source_sha256}|{page}".encode("ascii")).hexdigest()


def _sentinel_records(
    documents: list[dict[str, Any]], selection_receipt: str
) -> tuple[list[dict[str, Any]], int]:
    strata: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for document in documents:
        for page in document["pages"]:
            if page["route"] != "DOMINANT_RASTER_OCR":
                continue
            key = (
                str(page["source_effective_dpi_band"]),
                page["effective_orientation"],
                page["source_route_quadrant"],
                page["pdf_rotation_degrees"],
            )
            candidate = {
                "bank": document["bank"],
                "document_id": document["document_id"],
                "source_sha256": document["sha256"],
                "page": page["page"],
                "route": page["route"],
                "render_dpi": page["render_dpi"],
                "stratum": list(key),
                "rank_sha256": _sentinel_rank(selection_receipt, document["sha256"], page["page"]),
            }
            strata[key].append(candidate)
    for candidates in strata.values():
        candidates.sort(key=lambda item: item["rank_sha256"])
    selected = [strata[key][0] for key in sorted(strata)]
    largest = sorted(strata, key=lambda key: (-len(strata[key]), key))[:4]
    for key in largest:
        if len(strata[key]) < 2:
            raise WaveOneRoleBPageReaderError("largest sentinel stratum has no second member")
        selected.append(strata[key][1])
    for ordinal, record in enumerate(selected, start=1):
        record["sentinel_ordinal"] = ordinal
        record["selection_role"] = (
            "PRIMARY_STRATUM_REPRESENTATIVE"
            if ordinal <= len(strata)
            else "SECOND_MEMBER_OF_LARGEST_STRATUM"
        )
    return selected, len(strata)


def build_wave_one_role_b_route_plan(
    project_root: Path,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    """Build the deterministic source-first route plan without model execution."""

    project_root = project_root.resolve()
    policy_path = (policy_path or project_root / POLICY_RELATIVE_PATH).resolve()
    policy = load_wave_one_role_b_page_reader_policy(policy_path, project_root)
    inventory, inventory_ledger = _bound_json(
        project_root, policy["upstream"]["inventory"], "published corpus inventory"
    )
    pre_ocr, pre_ocr_ledger = _bound_json(
        project_root,
        policy["upstream"]["pre_ocr_structure"],
        "published pre OCR structure",
    )
    expected_inventory_identity = {
        "format_version": "BANK_CORPUS_SURVEY_INVENTORY_RESULT_V1",
        "status": "COMPLETE_REGISTERED_BANK_PDF_METADATA_INVENTORY",
        "claim_boundary": "REGISTERED_PDF_METADATA_AND_SOURCE_FIRST_SURVEY_SELECTION_ONLY",
        "policy": "BANK_CORPUS_BREADTH_FIRST_SURVEY_V1",
    }
    expected_pre_ocr_identity = {
        "format_version": "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES_V1",
        "status": "COMPLETE_PRE_OCR_FEATURE_ACCOUNTING_STRUCTURE_SURVEY_PENDING",
        "claim_boundary": "SELECTED_WAVE_1_PRE_OCR_PAGE_GEOMETRY_ROUTING_AND_FEATURE_CANDIDATES_ONLY",
        "policy": "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES_POLICY_V1",
    }
    if any(inventory.get(key) != value for key, value in expected_inventory_identity.items()):
        raise WaveOneRoleBPageReaderError("published inventory claim boundary drifted")
    if any(pre_ocr.get(key) != value for key, value in expected_pre_ocr_identity.items()):
        raise WaveOneRoleBPageReaderError("published pre-OCR claim boundary drifted")
    expected_pre_authority = {
        "kind": "FIXED_WAVE_1_PRE_OCR_STRUCTURE_POLICY_V1",
        "path": "config/corpus/bank-corpus-wave-1-pre-ocr-structure-v1.yaml",
        "sha256": "112064f2395c2ef3fc2481631f86ea09fdd1f5328edd9d03c31893dcc8bd3069",
        "size_bytes": 6065,
        "policy": "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES_POLICY_V1",
        "claim_boundary": "SELECTED_WAVE_1_PRE_OCR_PAGE_GEOMETRY_ROUTING_AND_FEATURE_CANDIDATES_ONLY",
    }
    if pre_ocr.get("authority") != expected_pre_authority:
        raise WaveOneRoleBPageReaderError("published pre-OCR fixed authority drifted")
    pre_safety = pre_ocr.get("safety")
    required_pre_false = (
        "ocr_allowed",
        "render_visibility_validation_allowed",
        "statement_acceptance_allowed",
        "table_acceptance_allowed",
        "axis_acceptance_allowed",
        "financial_value_semantic_extraction_allowed",
        "verbatim_financial_value_retention_allowed",
        "schema_inputs_allowed",
        "canonical_mapping_allowed",
        "role_a_inputs_allowed",
        "historical_values_allowed",
        "bank_specific_parser_rules_allowed",
        "absence_declarations_allowed",
    )
    if (
        not isinstance(pre_safety, dict)
        or any(pre_safety.get(key) is not False for key in required_pre_false)
        or pre_safety.get("source_pdf_hash_and_size_revalidation_required") is not True
    ):
        raise WaveOneRoleBPageReaderError("published pre-OCR safety boundary drifted")
    pre_accounting = pre_ocr.get("accounting")
    required_pre_accounting = {
        "schema_used": False,
        "canonical_mapping_attempted": False,
        "role_a_used": False,
        "historical_values_used": False,
        "bank_specific_routing_used": False,
        "absence_claims_allowed": False,
        "ocr_processed_page_count": 0,
        "render_visibility_validated_page_count": 0,
        "statement_type_classified_page_count": 0,
        "accepted_table_count": 0,
        "source_accounted_logical_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "financial_value_semantically_extracted_count": 0,
        "absence_declaration_count": 0,
    }
    if not isinstance(pre_accounting, dict) or any(
        pre_accounting.get(key) != value for key, value in required_pre_accounting.items()
    ):
        raise WaveOneRoleBPageReaderError("published pre-OCR semantic accounting drifted")
    selected = inventory.get("wave_1", {}).get("selected_documents")
    pre_documents = pre_ocr.get("documents")
    if not isinstance(selected, list) or not isinstance(pre_documents, list):
        raise WaveOneRoleBPageReaderError("receipt-bound upstream document lists are malformed")
    selection_projection = [
        {key: record.get(key) for key in _SELECTION_FIELDS} for record in selected
    ]
    selection_receipt = sha256_bytes(canonical_json_bytes(selection_projection))
    if (
        inventory.get("wave_1", {}).get("selection_receipt_sha256") != selection_receipt
        or pre_ocr.get("selection_receipt_sha256") != selection_receipt
    ):
        raise WaveOneRoleBPageReaderError("dynamic selection receipt reconciliation failed")
    if len(selected) != len(pre_documents):
        raise WaveOneRoleBPageReaderError("inventory and pre-OCR document counts differ")

    source_ledger: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    route_counts: Counter[str] = Counter()
    dpi_counts: Counter[str] = Counter()
    total_pages = 0
    seen_banks: set[str] = set()
    seen_documents: set[str] = set()
    for inventory_document, pre_document in zip(selected, pre_documents, strict=True):
        identity = {key: inventory_document.get(key) for key in _SELECTION_FIELDS}
        expected_pre = {key: pre_document.get(key) for key in _SELECTION_FIELDS}
        if identity != expected_pre:
            raise WaveOneRoleBPageReaderError("pre-OCR document identity differs from inventory")
        bank = identity["bank"]
        document_id = identity["document_id"]
        if (
            not isinstance(bank, str)
            or not bank
            or not isinstance(identity["sha256"], str)
            or not _SHA256.fullmatch(identity["sha256"])
            or document_id != f"sha256:{identity['sha256']}"
            or isinstance(identity["size_bytes"], bool)
            or not isinstance(identity["size_bytes"], int)
            or identity["size_bytes"] <= 0
            or not isinstance(identity["relative_path"], str)
        ):
            raise WaveOneRoleBPageReaderError("receipt-selected document identity is invalid")
        if bank in seen_banks or document_id in seen_documents:
            raise WaveOneRoleBPageReaderError("Wave 1 selection is not one document per bank")
        seen_banks.add(bank)
        seen_documents.add(document_id)
        source_path = _project_path(project_root, identity["relative_path"], "selected source PDF")
        source_payload = _stable_bytes(source_path, "selected source PDF")
        if (
            len(source_payload) != identity["size_bytes"]
            or sha256_bytes(source_payload) != identity["sha256"]
        ):
            raise WaveOneRoleBPageReaderError("selected source PDF byte identity drifted")
        raw_pages = pre_document.get("pages")
        if not isinstance(raw_pages, list) or len(raw_pages) != pre_document.get("page_count"):
            raise WaveOneRoleBPageReaderError("pre-OCR page accounting is malformed")
        pages = []
        for expected_page, raw_page in enumerate(raw_pages, start=1):
            if raw_page.get("page_number") != expected_page:
                raise WaveOneRoleBPageReaderError("pre-OCR physical page sequence drifted")
            features = raw_page.get("features")
            fingerprint = raw_page.get("feature_fingerprint_sha256")
            if (
                not isinstance(features, dict)
                or not isinstance(fingerprint, str)
                or not _SHA256.fullmatch(fingerprint)
            ):
                raise WaveOneRoleBPageReaderError("pre-OCR page feature identity is malformed")
            route = _route(features)
            source_band = features.get("dominant_image_effective_dpi_band")
            render_dpi = None
            if route == "DOMINANT_RASTER_OCR":
                render_dpi = (
                    policy["render"]["preserved_band_render_dpi"]
                    if source_band == policy["render"]["preserved_source_dpi_band"]
                    else policy["render"]["default_dpi"]
                )
                dpi_counts[str(render_dpi)] += 1
            page_record = {
                "page": expected_page,
                "pre_ocr_feature_fingerprint_sha256": fingerprint,
                "route": route,
                "render_dpi": render_dpi,
                "source_effective_dpi_band": source_band,
                "effective_orientation": features.get("effective_orientation"),
                "source_route_quadrant": features.get("source_route_quadrant"),
                "pdf_rotation_degrees": features.get("pdf_rotation_degrees"),
                "effective_rect_mpt": features.get("effective_rect_mpt"),
                "crop_box_mpt": features.get("crop_box_mpt"),
                "media_box_mpt": features.get("media_box_mpt"),
                "claim_boundary": "PAGE_ROUTE_AND_READER_REQUEST_ONLY",
                "statement_status": "NOT_CLASSIFIED",
                "table_status": "NOT_CLASSIFIED",
                "row_status": "NOT_RECONSTRUCTED",
                "cell_status": "NOT_INTERPRETED",
                "absence_claimed": False,
            }
            pages.append(page_record)
            route_counts[route] += 1
            total_pages += 1
        documents.append(
            {
                **identity,
                "page_count": len(pages),
                "pages": pages,
                "route_page_counts": {
                    route: sum(page["route"] == route for page in pages) for route in _ROUTES
                },
            }
        )
        source_ledger.append(
            {
                "phase": "PLAN",
                "kind": "RECEIPT_SELECTED_SOURCE_PDF",
                "path": identity["relative_path"],
                "sha256": identity["sha256"],
                "size_bytes": identity["size_bytes"],
                "document_id": document_id,
                "page_count": len(pages),
            }
        )

    sentinel, stratum_count = _sentinel_records(documents, selection_receipt)
    sentinel_sha256 = canonical_json_sha256(sentinel)
    accounting = {
        "selected_document_count": len(documents),
        "total_physical_page_count": total_pages,
        "route_page_counts": {route: route_counts[route] for route in _ROUTES},
        "ocr_render_dpi_page_counts": dict(sorted(dpi_counts.items())),
        "ocr_structural_stratum_count": stratum_count,
        "structural_sentinel_page_count": len(sentinel),
        "statement_page_classification_count": 0,
        "table_classification_count": 0,
        "logical_row_reconstruction_count": 0,
        "financial_cell_interpretation_count": 0,
        "absence_declaration_count": 0,
    }
    if any(accounting.get(key) != value for key, value in policy["expected_accounting"].items()):
        raise WaveOneRoleBPageReaderError(f"Wave 1 route accounting drifted: {accounting!r}")
    route_projection = [
        {
            "document_id": document["document_id"],
            "source_sha256": document["sha256"],
            "source_size_bytes": document["size_bytes"],
            "page_count": document["page_count"],
            "pages": [
                {
                    key: page[key]
                    for key in (
                        "page",
                        "pre_ocr_feature_fingerprint_sha256",
                        "route",
                        "render_dpi",
                        "source_effective_dpi_band",
                        "effective_orientation",
                        "source_route_quadrant",
                        "pdf_rotation_degrees",
                        "effective_rect_mpt",
                        "crop_box_mpt",
                        "media_box_mpt",
                    )
                }
                for page in document["pages"]
            ],
        }
        for document in documents
    ]
    route_plan_sha256 = canonical_json_sha256(
        {
            "selection_receipt_sha256": selection_receipt,
            "routes": route_projection,
            "render_contract": policy["render"],
        }
    )
    input_ledger = sorted(
        [inventory_ledger, pre_ocr_ledger, *source_ledger],
        key=lambda record: (record["phase"], record["kind"], record["path"]),
    )
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_PLAN_V1",
        "status": "COMPLETE_DETERMINISTIC_PAGE_READ_PLAN_EXECUTION_NOT_RUN",
        "policy": policy["policy"],
        "claim_boundary": policy["claim_boundary"],
        "selection_receipt_sha256": selection_receipt,
        "route_plan_sha256": route_plan_sha256,
        "sentinel_sha256": sentinel_sha256,
        "route_plan_projection": route_projection,
        "input_ledger": input_ledger,
        "input_ledger_sha256": canonical_json_sha256(input_ledger),
        "accounting": accounting,
        "sentinel": sentinel,
        "documents": documents,
        "safety": {
            "source_pdf_allowlist_basis": "RECEIPT_BOUND_INVENTORY_ONLY",
            "dataset_role_used": False,
            "role_a_used": False,
            "schema_used": False,
            "historical_values_used": False,
            "bank_specific_routing_used": False,
            "statement_or_table_semantics_attempted": False,
            "absence_claimed": False,
        },
    }


def _git_identity(project_root: Path, *, require_clean: bool) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    dirty = bool(status.strip())
    if require_clean and dirty:
        raise WaveOneRoleBPageReaderError(
            "refusing page-reader evidence planning from a dirty Git worktree"
        )
    return {"commit": commit, "dirty": dirty}


def _git_blob_sha256(project_root: Path, commit: str, relative_path: Path) -> str:
    process = subprocess.run(
        ["git", "show", f"{commit}:{relative_path.as_posix()}"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if process.returncode:
        raise WaveOneRoleBPageReaderError(
            f"implementation is not committed: {relative_path.as_posix()}"
        )
    return sha256_bytes(process.stdout)


def build_implementation_ledger(project_root: Path, commit: str) -> dict[str, Any]:
    records = []
    for relative_path in IMPLEMENTATION_RELATIVE_PATHS:
        path = (project_root / relative_path).resolve()
        if not path.is_relative_to(project_root):
            raise WaveOneRoleBPageReaderError("implementation path escapes project root")
        payload = _stable_bytes(path, f"implementation {relative_path.as_posix()}")
        digest = sha256_bytes(payload)
        if _git_blob_sha256(project_root, commit, relative_path) != digest:
            raise WaveOneRoleBPageReaderError(
                f"implementation bytes differ from Git blob: {relative_path.as_posix()}"
            )
        records.append(
            {
                "phase": "READ",
                "kind": "IMPLEMENTATION",
                "path": relative_path.as_posix(),
                "sha256": digest,
                "size_bytes": len(payload),
            }
        )
    records.sort(key=lambda record: record["path"])
    return {"records": records, "sha256": canonical_json_sha256(records)}


def _file_inventory(root: Path, *, locator: str) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise WaveOneRoleBPageReaderError(f"model directory is invalid: {locator}")
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WaveOneRoleBPageReaderError(f"model inventory contains symlink: {locator}")
        if path.is_file():
            payload = _stable_bytes(path, f"model file {locator}")
            records.append(
                {
                    "path": f"{locator}/{path.relative_to(root).as_posix()}",
                    "sha256": sha256_bytes(payload),
                    "size_bytes": len(payload),
                }
            )
    if not records:
        raise WaveOneRoleBPageReaderError(f"model directory is empty: {locator}")
    return {
        "locator": locator,
        "files": records,
        "file_count": len(records),
        "size_bytes": sum(record["size_bytes"] for record in records),
        "sha256": canonical_json_sha256(records),
    }


def build_runtime_model_ledger(
    project_root: Path,
    policy: dict[str, Any],
    model_cache: Path,
) -> dict[str, Any]:
    reader = policy["readers"]["ppocrv6"]
    runtime_path = _project_path(project_root, reader["runtime_manifest_path"], "runtime manifest")
    runtime_payload = _stable_bytes(runtime_path, "runtime manifest")
    runtime = tomllib.loads(runtime_payload.decode("utf-8"))
    package_names = tuple(sorted(runtime.get("packages", {})))
    if not package_names:
        raise WaveOneRoleBPageReaderError("isolated runtime package contract is empty")
    isolation_directory = runtime.get("isolation_directory")
    if not isinstance(isolation_directory, str) or not isolation_directory:
        raise WaveOneRoleBPageReaderError("isolated Paddle runtime locator is absent")
    runtime_python = project_root / isolation_directory / "bin/python"
    if not runtime_python.is_file() or (project_root / isolation_directory).is_symlink():
        raise WaveOneRoleBPageReaderError("isolated Paddle runtime interpreter is absent")
    interpreter_payload = _stable_bytes(
        runtime_python.resolve(), "isolated Paddle runtime interpreter target"
    )
    probe_source = (
        "import importlib.metadata,json,paddle;"
        f"names={package_names!r};"
        "print(json.dumps({'packages':{n:importlib.metadata.version(n) for n in names},"
        "'python':f'{__import__(\"sys\").version_info.major}.{__import__(\"sys\").version_info.minor}',"
        "'device':paddle.device.get_device(),"
        "'compiled_with_cuda':paddle.device.is_compiled_with_cuda()},sort_keys=True))"
    )
    probe = subprocess.run(
        [runtime_python.as_posix(), "-c", probe_source],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONNOUSERSITE": "1"},
    )
    if probe.returncode:
        raise WaveOneRoleBPageReaderError("isolated Paddle runtime probe failed")
    try:
        probed_runtime = json.loads(probe.stdout)
    except json.JSONDecodeError as error:
        raise WaveOneRoleBPageReaderError("isolated Paddle runtime probe is invalid") from error
    installed = probed_runtime.get("packages")
    expected_packages = {name: runtime["packages"][name] for name in package_names}
    if installed != expected_packages:
        raise WaveOneRoleBPageReaderError("installed PP-OCRv6 packages drifted")
    if (
        probed_runtime.get("device") != "cpu"
        or probed_runtime.get("compiled_with_cuda") is not False
    ):
        raise WaveOneRoleBPageReaderError("isolated Paddle runtime device drifted")
    if probed_runtime.get("python") != runtime.get("python"):
        raise WaveOneRoleBPageReaderError("isolated Paddle Python version drifted")
    config_records = []
    for kind, key in (
        ("PPOCRV6_CONFIGURATION", "configuration_path"),
        ("RUNTIME_MANIFEST", "runtime_manifest_path"),
        ("RUNTIME_FREEZE", "runtime_freeze_path"),
    ):
        path = _project_path(project_root, reader[key], kind)
        payload = _stable_bytes(path, kind)
        config_records.append(
            {
                "phase": "READ",
                "kind": kind,
                "path": reader[key],
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    models = []
    model_cache = model_cache.resolve()
    for key in reader["model_keys"]:
        specification = runtime["models"][key]
        directory = model_cache / "official_models" / specification["cache_directory"]
        inventory = _file_inventory(
            directory, locator=f"MODEL_CACHE/official_models/{specification['cache_directory']}"
        )
        weights = directory / specification["weights_file"]
        weight_payload = _stable_bytes(weights, f"pinned model weights {key}")
        if (
            len(weight_payload) != specification["weights_size_bytes"]
            or sha256_bytes(weight_payload) != specification["weights_sha256"]
        ):
            raise WaveOneRoleBPageReaderError(f"pinned model weight identity drifted: {key}")
        models.append(
            {
                "key": key,
                "repo_id": specification["repo_id"],
                "revision": specification["revision"],
                "weights_file": specification["weights_file"],
                "weights_size_bytes": specification["weights_size_bytes"],
                "weights_sha256": specification["weights_sha256"],
                "inventory": inventory,
            }
        )
    identity = {
        "provider": "PP_OCRV6_MEDIUM_WORD_BOX_CPU",
        "packages": installed,
        "runtime_interpreter": f"{isolation_directory}/bin/python",
        "runtime_interpreter_target_sha256": sha256_bytes(interpreter_payload),
        "runtime_interpreter_target_size_bytes": len(interpreter_payload),
        "python": probed_runtime["python"],
        "runtime_device_probe": {
            "device": probed_runtime["device"],
            "compiled_with_cuda": probed_runtime["compiled_with_cuda"],
        },
        "device": reader["device"],
        "precision": reader["precision"],
        "mkldnn": reader["mkldnn"],
        "cpu_threads_per_session": reader["cpu_threads_per_session"],
        "network_policy": reader["network_policy"],
        "config_records": sorted(config_records, key=lambda record: record["path"]),
        "models": models,
    }
    identity["sha256"] = canonical_json_sha256(identity)
    return identity


def seal_wave_one_role_b_execution_plan(
    project_root: Path,
    *,
    model_cache: Path,
    require_clean_git: bool = True,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    policy_path = project_root / POLICY_RELATIVE_PATH
    policy = load_wave_one_role_b_page_reader_policy(policy_path, project_root)
    route_plan = build_wave_one_role_b_route_plan(project_root, policy_path)
    git = _git_identity(project_root, require_clean=require_clean_git)
    implementation = build_implementation_ledger(project_root, git["commit"])
    runtime = build_runtime_model_ledger(project_root, policy, model_cache)
    render_runtime_identity = {
        "provider": "PYMUPDF_FULL_COMPOSITED_DISPLAYED_PAGE_RGB_V1",
        "pymupdf_distribution_version": importlib.metadata.version("pymupdf"),
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_runtime_versions": list(fitz.version),
        "render_contract": policy["render"],
        "implementation_ledger_sha256": implementation["sha256"],
    }
    render_runtime_identity["sha256"] = canonical_json_sha256(render_runtime_identity)
    native_config_records = []
    for key in ("policy_path", "quality_policy_path"):
        relative = policy["readers"]["causal_native"][key]
        path = _project_path(project_root, relative, "causal native configuration")
        payload = _stable_bytes(path, "causal native configuration")
        native_config_records.append(
            {
                "path": relative,
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    native_identity = {
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_distribution_version": importlib.metadata.version("pymupdf"),
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_runtime_versions": list(fitz.version),
        "config_records": native_config_records,
        "ocr_fallback_allowed": False,
    }
    native_identity["sha256"] = canonical_json_sha256(native_identity)
    for document in route_plan["documents"]:
        request_hashes = []
        for page in document["pages"]:
            provider_identity = (
                runtime["sha256"]
                if page["route"] == "DOMINANT_RASTER_OCR"
                else native_identity["sha256"]
                if page["route"] == "CAUSAL_NATIVE_TEXT"
                else None
            )
            request = {
                "format_version": "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1",
                "selection_receipt_sha256": route_plan["selection_receipt_sha256"],
                "route_plan_sha256": route_plan["route_plan_sha256"],
                "sentinel_sha256": route_plan["sentinel_sha256"],
                "input_ledger_sha256": route_plan["input_ledger_sha256"],
                "source_sha256": document["sha256"],
                "source_size_bytes": document["size_bytes"],
                "physical_page": page["page"],
                "pre_ocr_feature_fingerprint_sha256": page["pre_ocr_feature_fingerprint_sha256"],
                "route": page["route"],
                "render_specification": (
                    {
                        "source": policy["render"]["source"],
                        "dpi": page["render_dpi"],
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    }
                    if page["route"] == "DOMINANT_RASTER_OCR"
                    else None
                ),
                "git_commit": git["commit"],
                "implementation_ledger_sha256": implementation["sha256"],
                "provider_identity_sha256": provider_identity,
                "render_runtime_identity_sha256": (
                    render_runtime_identity["sha256"]
                    if page["route"] == "DOMINANT_RASTER_OCR"
                    else None
                ),
                "bank_identity_used": False,
                "filename_used": False,
                "role_a_used": False,
                "schema_used": False,
                "historical_values_used": False,
            }
            page["request"] = request
            page["request_sha256"] = canonical_json_sha256(request)
            request_hashes.append(page["request_sha256"])
        document["request_set_sha256"] = canonical_json_sha256(request_hashes)
    route_plan.update(
        status="READY_FOR_ROLE_B_PAGE_READ_EXECUTION",
        git=git,
        implementation_ledger=implementation,
        ppocrv6_runtime_model_ledger=runtime,
        render_runtime_ledger=render_runtime_identity,
        causal_native_runtime_ledger=native_identity,
    )
    execution_projection = {
        "selection_receipt_sha256": route_plan["selection_receipt_sha256"],
        "route_plan_sha256": route_plan["route_plan_sha256"],
        "sentinel_sha256": route_plan["sentinel_sha256"],
        "input_ledger_sha256": route_plan["input_ledger_sha256"],
        "git": git,
        "implementation_ledger_sha256": implementation["sha256"],
        "ppocrv6_runtime_model_ledger_sha256": runtime["sha256"],
        "render_runtime_ledger_sha256": render_runtime_identity["sha256"],
        "causal_native_runtime_ledger_sha256": native_identity["sha256"],
        "document_request_sets": [
            {
                "document_id": document["document_id"],
                "request_set_sha256": document["request_set_sha256"],
            }
            for document in route_plan["documents"]
        ],
    }
    route_plan["execution_plan_sha256"] = canonical_json_sha256(execution_projection)
    git_after_reads = _git_identity(project_root, require_clean=require_clean_git)
    if git_after_reads != git:
        raise WaveOneRoleBPageReaderError(
            "Git identity changed while the execution plan was being sealed"
        )
    return route_plan
