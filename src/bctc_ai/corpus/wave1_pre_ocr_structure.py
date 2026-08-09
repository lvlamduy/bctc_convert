from __future__ import annotations

import json
import math
import os
import re
import stat
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file


class WaveOnePreOCRStructureError(ValueError):
    """Wave 1 pre-OCR evidence cannot be accounted without guessing."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-pre-ocr-structure-v1.yaml")
IMPLEMENTATION_RELATIVE_PATH = Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py")
OUTPUT_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-pre-ocr-structure-features.json"
)

_POLICY_SHA256 = "112064f2395c2ef3fc2481631f86ea09fdd1f5328edd9d03c31893dcc8bd3069"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROUTE_VOCABULARY = (
    "SCAN_ROUTE",
    "MIXED_PAGE_HYBRID_ROUTE",
    "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION",
    "NATIVE_SEARCHABLE_ROUTE",
    "UNRESOLVED_SOURCE_ROUTE",
)
_ROUTE_QUADRANT_VOCABULARY = (
    "TEXT_LAYER_AND_DOMINANT_RASTER",
    "TEXT_LAYER_AND_NONDOMINANT_RASTER",
    "NO_TEXT_LAYER_AND_DOMINANT_RASTER",
    "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER",
)


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _read_stable_bytes(path: Path, label: str) -> bytes:
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise WaveOnePreOCRStructureError(f"{label} changed while it was read")
    return payload


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise WaveOnePreOCRStructureError(f"{label} must be a nonempty project-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise WaveOnePreOCRStructureError(f"{label} is not canonical")
    return value


def _resolve_under_root(project_root: Path, relative: Any, label: str) -> Path:
    canonical = _canonical_relative_path(relative, label)
    path = (project_root / Path(*PurePosixPath(canonical).parts)).resolve()
    if not path.is_relative_to(project_root):
        raise WaveOnePreOCRStructureError(f"{label} escapes the project root")
    return path


def _load_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WaveOnePreOCRStructureError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise WaveOnePreOCRStructureError(f"{label} must be a JSON object")
    return value


def load_wave_one_pre_ocr_structure_policy(path: Path, project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    canonical_path = (project_root / POLICY_RELATIVE_PATH).resolve()
    if path.resolve() != canonical_path:
        raise WaveOnePreOCRStructureError(
            f"Wave 1 pre-OCR structure features require canonical policy {POLICY_RELATIVE_PATH}"
        )
    encoded = _read_stable_bytes(path, "Wave 1 pre-OCR structure policy")
    if sha256_bytes(encoded) != _POLICY_SHA256:
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR structure policy bytes drifted")
    try:
        policy = yaml.safe_load(encoded)
    except yaml.YAMLError as error:
        raise WaveOnePreOCRStructureError(
            "Wave 1 pre-OCR structure policy is invalid YAML"
        ) from error
    if not isinstance(policy, dict):
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR structure policy must be an object")
    if set(policy) != {
        "version",
        "policy",
        "claim_boundary",
        "upstream_binding",
        "feature_extraction",
        "safety",
        "expected_accounting",
        "output",
    }:
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR structure policy fields drifted")
    if (
        policy.get("version") != 1
        or policy.get("policy") != "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES_POLICY_V1"
        or policy.get("claim_boundary")
        != "SELECTED_WAVE_1_PRE_OCR_PAGE_GEOMETRY_ROUTING_AND_FEATURE_CANDIDATES_ONLY"
    ):
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR structure policy identity drifted")
    upstream = policy.get("upstream_binding")
    if not isinstance(upstream, dict):
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR upstream binding is malformed")
    for name in ("inventory", "source_profile"):
        specification = upstream.get(name)
        if not isinstance(specification, dict):
            raise WaveOnePreOCRStructureError(f"Wave 1 pre-OCR {name} binding is malformed")
        _resolve_under_root(project_root, specification.get("path"), name)
    output = policy.get("output")
    if not isinstance(output, dict):
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR output contract is malformed")
    configured_output = f"{output.get('output_directory')}/{output.get('filename')}"
    if configured_output != OUTPUT_RELATIVE_PATH.as_posix():
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR output path drifted")
    _resolve_under_root(project_root, configured_output, "Wave 1 pre-OCR output")
    return policy


def _load_bound_published_json(
    project_root: Path,
    specification: dict[str, Any],
    *,
    label: str,
    kind: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _resolve_under_root(project_root, specification.get("path"), label)
    if path.is_symlink() or not path.is_file():
        raise WaveOnePreOCRStructureError(f"{label} is not a regular local file")
    encoded = _read_stable_bytes(path, label)
    if len(encoded) != specification.get("size_bytes") or sha256_bytes(
        encoded
    ) != specification.get("sha256"):
        raise WaveOnePreOCRStructureError(f"{label} identity drifted")
    payload = _load_json_object(encoded, label)
    for field in ("format_version", "status", "claim_boundary"):
        if payload.get(field) != specification.get(field):
            raise WaveOnePreOCRStructureError(f"{label} {field} drifted")
    return payload, {
        "kind": kind,
        "binding_mode": "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY",
        "rebuilt_by_this_run": False,
        "path": specification["path"],
        "sha256": specification["sha256"],
        "size_bytes": specification["size_bytes"],
        "format_version": specification["format_version"],
        "status": specification["status"],
        "claim_boundary": specification["claim_boundary"],
    }


def _integer_millipoint(value: float) -> int:
    return int(round(float(value) * 1_000))


def _rect_millipoints(rectangle: Any) -> list[int]:
    return [
        _integer_millipoint(rectangle.x0),
        _integer_millipoint(rectangle.y0),
        _integer_millipoint(rectangle.x1),
        _integer_millipoint(rectangle.y1),
    ]


def _geometry_family(
    width_mpt: int,
    height_mpt: int,
    *,
    references: dict[str, list[int]],
    maximum_distance_ppm: int,
) -> tuple[str, int]:
    short_side, long_side = sorted((width_mpt, height_mpt))
    candidates: list[tuple[int, str]] = []
    for name in sorted(references):
        reference_short, reference_long = references[name]
        distance = math.sqrt(
            ((short_side - reference_short) / reference_short) ** 2
            + ((long_side - reference_long) / reference_long) ** 2
        )
        candidates.append((int(round(distance * 1_000_000)), name))
    distance_ppm, family = min(candidates)
    if distance_ppm > maximum_distance_ppm:
        return "OTHER_GEOMETRY", distance_ppm
    return family, distance_ppm


def _run_length_records(values: list[Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page_number, value in enumerate(values, start=1):
        if not records or records[-1]["value"] != value:
            records.append(
                {
                    "start_page": page_number,
                    "end_page": page_number,
                    "length": 1,
                    "value": value,
                }
            )
        else:
            records[-1]["end_page"] = page_number
            records[-1]["length"] += 1
    return records


def _feature_run_lengths(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"length": record["length"], "value": record["value"]} for record in records]


def _drawing_features(drawings: list[dict[str, Any]], tolerance_mpt: int) -> dict[str, int]:
    tolerance = tolerance_mpt / 1_000
    observed: Counter[str] = Counter()
    for drawing in drawings:
        observed["stroked_drawing_path_count"] += drawing.get("color") is not None
        observed["filled_drawing_path_count"] += drawing.get("fill") is not None
        for item in drawing.get("items", ()):
            if not item:
                continue
            observed["drawing_item_count"] += 1
            kind = item[0]
            if kind == "l" and len(item) >= 3:
                first, second = item[1], item[2]
                if abs(first.y - second.y) <= tolerance:
                    observed["horizontal_line_item_count"] += 1
                elif abs(first.x - second.x) <= tolerance:
                    observed["vertical_line_item_count"] += 1
                else:
                    observed["other_line_item_count"] += 1
            elif kind == "re":
                observed["rectangle_item_count"] += 1
            elif kind == "c":
                observed["curve_item_count"] += 1
            elif kind == "qu":
                observed["quadrilateral_item_count"] += 1
            else:
                observed["other_drawing_item_count"] += 1
    return {
        "drawing_path_count": len(drawings),
        **{
            field: observed[field]
            for field in (
                "stroked_drawing_path_count",
                "filled_drawing_path_count",
                "drawing_item_count",
                "horizontal_line_item_count",
                "vertical_line_item_count",
                "other_line_item_count",
                "rectangle_item_count",
                "curve_item_count",
                "quadrilateral_item_count",
                "other_drawing_item_count",
            )
        },
    }


def _text_layer_features(
    raw_text: dict[str, Any],
    *,
    threshold: int,
    form_code_pattern: re.Pattern[str],
) -> tuple[dict[str, Any], list[str]]:
    text_spans = [
        span
        for block in raw_text.get("blocks", [])
        if block.get("type") == 0
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    ]
    alpha_span_counts: Counter[str] = Counter()
    alpha_character_counts: Counter[str] = Counter()
    nonzero_alpha_parts: list[str] = []
    for span in text_spans:
        alpha = span.get("alpha")
        alpha_key = str(alpha)
        alpha_span_counts[alpha_key] += 1
        characters = [
            character["c"]
            for character in span.get("chars", ())
            if isinstance(character.get("c"), str)
        ]
        alpha_character_counts[alpha_key] += sum(
            not character.isspace() for character in characters
        )
        if isinstance(alpha, int) and alpha > 0:
            nonzero_alpha_parts.append("".join(characters))

    zero_alpha_characters = alpha_character_counts["0"]
    nonzero_alpha_characters = sum(
        count
        for alpha, count in alpha_character_counts.items()
        if alpha.isdigit() and int(alpha) > 0
    )
    unknown_alpha_characters = sum(alpha_character_counts.values()) - (
        zero_alpha_characters + nonzero_alpha_characters
    )
    zero_alpha_spans = alpha_span_counts["0"]
    nonzero_alpha_spans = sum(
        count for alpha, count in alpha_span_counts.items() if alpha.isdigit() and int(alpha) > 0
    )
    total_characters = sum(alpha_character_counts.values())
    candidates = sorted(
        {
            re.sub(r"\s+", "", match.group(0)).upper()
            for match in form_code_pattern.finditer(" ".join(nonzero_alpha_parts))
        }
    )
    features = {
        "extractable_non_whitespace_character_count": total_characters,
        "zero_alpha_non_whitespace_character_count": zero_alpha_characters,
        "nonzero_alpha_non_whitespace_character_count": nonzero_alpha_characters,
        "unknown_alpha_non_whitespace_character_count": unknown_alpha_characters,
        "text_span_count": len(text_spans),
        "zero_alpha_span_count": zero_alpha_spans,
        "nonzero_alpha_span_count": nonzero_alpha_spans,
        "unknown_alpha_span_count": len(text_spans) - zero_alpha_spans - nonzero_alpha_spans,
        "text_span_count_by_alpha": dict(sorted(alpha_span_counts.items())),
        "text_non_whitespace_character_count_by_alpha": dict(
            sorted(alpha_character_counts.items())
        ),
        "has_any_extractable_text_layer": total_characters > 0,
        "substantive_extractable_text_layer": total_characters >= threshold,
        "substantive_nonzero_alpha_text_layer": nonzero_alpha_characters >= threshold,
        "substantive_zero_alpha_text_layer": zero_alpha_characters >= threshold,
        "nonzero_alpha_text_layer_form_code_unique_normalized_token_count": len(candidates),
    }
    return features, candidates


_PAGE_FEATURE_FINGERPRINT_FIELDS = (
    "media_box_mpt",
    "crop_box_mpt",
    "effective_rect_mpt",
    "effective_width_mpt",
    "effective_height_mpt",
    "pdf_rotation_degrees",
    "effective_orientation",
    "geometry_family_candidate",
    "geometry_family_distance_ppm",
    "cropbox_differs_from_mediabox",
    "source_route_quadrant",
    "extractable_non_whitespace_character_count",
    "zero_alpha_non_whitespace_character_count",
    "nonzero_alpha_non_whitespace_character_count",
    "unknown_alpha_non_whitespace_character_count",
    "text_span_count",
    "zero_alpha_span_count",
    "nonzero_alpha_span_count",
    "unknown_alpha_span_count",
    "text_span_count_by_alpha",
    "text_non_whitespace_character_count_by_alpha",
    "has_any_extractable_text_layer",
    "substantive_extractable_text_layer",
    "substantive_nonzero_alpha_text_layer",
    "substantive_zero_alpha_text_layer",
    "displayed_image_count",
    "has_displayed_image",
    "maximum_displayed_image_coverage_ppm",
    "has_dominant_displayed_raster",
    "maximum_coverage_image_pixel_width",
    "maximum_coverage_image_pixel_height",
    "dominant_image_effective_dpi_x_milli",
    "dominant_image_effective_dpi_y_milli",
    "dominant_image_effective_dpi_mean_milli",
    "dominant_image_effective_dpi_band",
    "no_extracted_text_or_displayed_image",
    "drawing_path_count",
    "stroked_drawing_path_count",
    "filled_drawing_path_count",
    "drawing_item_count",
    "horizontal_line_item_count",
    "vertical_line_item_count",
    "other_line_item_count",
    "rectangle_item_count",
    "curve_item_count",
    "quadrilateral_item_count",
    "other_drawing_item_count",
)


def _page_feature_fingerprint_sha256(features: dict[str, Any], feature_contract_sha256: str) -> str:
    if _SHA256.fullmatch(feature_contract_sha256) is None:
        raise WaveOnePreOCRStructureError("pre-OCR feature contract hash is invalid")
    missing = set(_PAGE_FEATURE_FINGERPRINT_FIELDS) - set(features)
    if missing:
        raise WaveOnePreOCRStructureError("pre-OCR page fingerprint features are incomplete")
    projection = {
        "format_version": "BANK_PRE_OCR_PAGE_FEATURE_FINGERPRINT_V1",
        "feature_contract_sha256": feature_contract_sha256,
        "features": {field: features[field] for field in _PAGE_FEATURE_FINGERPRINT_FIELDS},
    }
    return sha256_bytes(_canonical_json_bytes(projection))


_DOCUMENT_FEATURE_SUMMARY_FIELDS = (
    "page_count",
    "orientation_page_counts",
    "rotation_page_counts",
    "geometry_family_page_counts",
    "cropbox_difference_page_count",
    "orientation_transition_count",
    "rotation_transition_count",
    "source_route_quadrant_transition_count",
    "dominant_raster_page_count",
    "effective_dpi_band_page_counts",
    "substantive_extractable_text_page_count",
    "substantive_nonzero_alpha_text_page_count",
    "substantive_zero_alpha_text_page_count",
    "vector_drawing_page_count",
    "vector_drawing_path_count",
)


def _document_feature_fingerprint_sha256(
    *,
    summary: dict[str, Any],
    page_feature_fingerprints: list[str],
    orientation_runs: list[dict[str, Any]],
    rotation_runs: list[dict[str, Any]],
    geometry_family_runs: list[dict[str, Any]],
    source_route_quadrant_runs: list[dict[str, Any]],
    feature_contract_sha256: str,
) -> str:
    missing = set(_DOCUMENT_FEATURE_SUMMARY_FIELDS) - set(summary)
    if (
        missing
        or _SHA256.fullmatch(feature_contract_sha256) is None
        or any(_SHA256.fullmatch(value) is None for value in page_feature_fingerprints)
    ):
        raise WaveOnePreOCRStructureError("pre-OCR document fingerprint features are incomplete")
    projection = {
        "format_version": "BANK_PRE_OCR_DOCUMENT_FEATURE_FINGERPRINT_V1",
        "feature_contract_sha256": feature_contract_sha256,
        "summary": {field: summary[field] for field in _DOCUMENT_FEATURE_SUMMARY_FIELDS},
        "page_feature_fingerprint_sequence": page_feature_fingerprints,
        "orientation_run_lengths": _feature_run_lengths(orientation_runs),
        "rotation_run_lengths": _feature_run_lengths(rotation_runs),
        "geometry_family_run_lengths": _feature_run_lengths(geometry_family_runs),
        "source_route_quadrant_run_lengths": _feature_run_lengths(source_route_quadrant_runs),
    }
    return sha256_bytes(_canonical_json_bytes(projection))


def _effective_dpi_band(average_dpi_milli: int, step: int) -> str:
    step_milli = step * 1_000
    band = ((average_dpi_milli + step_milli // 2) // step_milli) * step
    return str(band)


def _classify_source_route(
    *,
    page_count: int,
    substantive_extracted_text_pages: int,
    substantive_nonzero_alpha_text_pages: int,
    displayed_image_pages: int,
    dominant_raster_pages: int,
) -> str:
    if (
        page_count <= 0
        or substantive_extracted_text_pages < 0
        or substantive_extracted_text_pages > page_count
        or substantive_nonzero_alpha_text_pages < 0
        or substantive_nonzero_alpha_text_pages > substantive_extracted_text_pages
        or displayed_image_pages < 0
        or displayed_image_pages > page_count
        or dominant_raster_pages < 0
        or dominant_raster_pages > displayed_image_pages
    ):
        raise WaveOnePreOCRStructureError("PDF page-evidence counts are invalid")
    if substantive_extracted_text_pages == page_count and dominant_raster_pages == page_count:
        return "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION"
    if substantive_nonzero_alpha_text_pages == page_count:
        return "NATIVE_SEARCHABLE_ROUTE"
    if substantive_nonzero_alpha_text_pages == 0 and dominant_raster_pages == page_count:
        return "SCAN_ROUTE"
    if substantive_nonzero_alpha_text_pages == 0:
        return "UNRESOLVED_SOURCE_ROUTE"
    return "MIXED_PAGE_HYBRID_ROUTE"


def build_wave_one_pre_ocr_structure_features(
    project_root: Path, policy_path: Path
) -> dict[str, Any]:
    import fitz

    project_root = project_root.resolve()
    policy = load_wave_one_pre_ocr_structure_policy(policy_path, project_root)
    upstream_binding = policy["upstream_binding"]
    if (
        upstream_binding["mode"] != "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY"
        or upstream_binding["artifacts_rebuilt_by_this_run"] is not False
    ):
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR upstream binding mode drifted")
    inventory, inventory_ledger = _load_bound_published_json(
        project_root,
        upstream_binding["inventory"],
        label="published corpus inventory",
        kind="PUBLISHED_BANK_CORPUS_INVENTORY_V1",
    )
    source_profile, source_profile_ledger = _load_bound_published_json(
        project_root,
        upstream_binding["source_profile"],
        label="published Wave 1 source profile",
        kind="PUBLISHED_BANK_CORPUS_WAVE_1_SOURCE_PROFILE_V1",
    )
    selection_receipt = upstream_binding["selection_receipt_sha256"]
    if (
        _SHA256.fullmatch(selection_receipt) is None
        or inventory.get("wave_1", {}).get("selection_receipt_sha256") != selection_receipt
        or source_profile.get("selection_receipt_sha256") != selection_receipt
    ):
        raise WaveOnePreOCRStructureError("published Wave 1 selection receipt drifted")

    selected_documents = inventory.get("wave_1", {}).get("selected_documents")
    source_profiles = source_profile.get("profiles")
    if not isinstance(selected_documents, list) or not isinstance(source_profiles, list):
        raise WaveOnePreOCRStructureError("published Wave 1 document inventory is malformed")
    selection_projection = [
        {
            key: record.get(key)
            for key in ("bank", "document_id", "sha256", "size_bytes", "relative_path")
        }
        for record in selected_documents
    ]
    if sha256_bytes(_canonical_json_bytes(selection_projection)) != selection_receipt:
        raise WaveOnePreOCRStructureError("published inventory selection projection drifted")
    source_profile_projection = [
        {
            key: record.get(key)
            for key in ("bank", "document_id", "sha256", "size_bytes", "relative_path")
        }
        for record in source_profiles
    ]
    if source_profile_projection != selection_projection:
        raise WaveOnePreOCRStructureError("published source-profile selection drifted")
    if len({record["bank"] for record in selection_projection}) != len(selection_projection) or len(
        {record["document_id"] for record in selection_projection}
    ) != len(selection_projection):
        raise WaveOnePreOCRStructureError("published Wave 1 selection is not one document per bank")

    contract = policy["feature_extraction"]
    feature_contract_sha256 = sha256_bytes(_canonical_json_bytes(contract))
    threshold = contract["text_layer"]["substantive_min_non_whitespace_chars"]
    form_code_pattern = re.compile(
        contract["text_layer"]["exact_nonzero_alpha_form_code_pattern"],
        re.IGNORECASE,
    )
    raster_threshold_ppm = contract["raster"]["dominant_raster_min_page_coverage_ppm"]
    dpi_step = contract["raster"]["effective_dpi_band_step"]
    family_references = contract["geometry"]["family_references"]
    family_maximum = contract["geometry"]["family_max_normalized_distance_ppm"]
    square_tolerance = contract["geometry"]["orientation_square_tolerance_mpt"]
    drawing_tolerance = contract["vector_geometry"]["orthogonal_line_tolerance_mpt"]

    documents: list[dict[str, Any]] = []
    source_pdf_ledger: list[dict[str, Any]] = []
    corpus_orientation: Counter[str] = Counter()
    corpus_rotation: Counter[str] = Counter()
    corpus_geometry_family_pages: Counter[str] = Counter()
    corpus_geometry_family_documents: Counter[str] = Counter()
    corpus_dpi_bands: Counter[str] = Counter()
    corpus_route_candidates: Counter[str] = Counter()
    corpus_route_quadrants: Counter[str] = Counter()
    total_pages = 0
    orientation_transitions = 0
    rotation_transitions = 0
    route_quadrant_transitions = 0
    cropbox_differences = 0
    displayed_image_pages = 0
    dominant_raster_pages = 0
    any_text_pages = 0
    substantive_text_pages = 0
    nonzero_alpha_pages = 0
    zero_alpha_pages = 0
    no_text_or_image_pages = 0
    form_code_pages = 0
    form_code_documents = 0
    form_code_token_occurrences = 0
    drawing_pages = 0
    drawing_paths = 0

    for selected_record, upstream_document in zip(selected_documents, source_profiles, strict=True):
        source_path = _resolve_under_root(
            project_root, selected_record["relative_path"], "Wave 1 source PDF"
        )
        if source_path.is_symlink() or not source_path.is_file():
            raise WaveOnePreOCRStructureError(
                f"Wave 1 source PDF is not a regular local file: {selected_record['relative_path']}"
            )
        source_bytes = _read_stable_bytes(source_path, "Wave 1 source PDF")
        if (
            len(source_bytes) != selected_record["size_bytes"]
            or sha256_bytes(source_bytes) != selected_record["sha256"]
        ):
            raise WaveOnePreOCRStructureError(
                f"Wave 1 source PDF identity drifted: {selected_record['relative_path']}"
            )
        try:
            document = fitz.open(stream=source_bytes, filetype="pdf")
        except Exception as error:
            raise WaveOnePreOCRStructureError(
                f"Wave 1 source PDF cannot be opened: {selected_record['relative_path']}"
            ) from error
        try:
            if (
                not document.is_pdf
                or document.needs_pass
                or document.page_count <= 0
                or document.page_count != upstream_document.get("page_count")
            ):
                raise WaveOnePreOCRStructureError(
                    f"Wave 1 source PDF page identity drifted: {selected_record['relative_path']}"
                )
            upstream_pages = upstream_document.get("page_evidence")
            if not isinstance(upstream_pages, list) or len(upstream_pages) != document.page_count:
                raise WaveOnePreOCRStructureError(
                    "published source-profile page accounting drifted"
                )
            upstream_route_fingerprint = upstream_document.get("source_route_fingerprint_sha256")
            if (
                not isinstance(upstream_route_fingerprint, str)
                or _SHA256.fullmatch(upstream_route_fingerprint) is None
            ):
                raise WaveOnePreOCRStructureError("published source-route fingerprint is malformed")

            pages: list[dict[str, Any]] = []
            orientations: list[str] = []
            rotations: list[int] = []
            geometry_families: list[str] = []
            route_quadrants: list[str] = []
            document_dpi_bands: Counter[str] = Counter()
            document_form_code_pages: list[dict[str, Any]] = []
            document_drawing_paths = 0
            document_displayed_image_pages = 0

            for page_index, upstream_page in enumerate(upstream_pages):
                page = document.load_page(page_index)
                raw_text = page.get_text("rawdict")
                text_features, page_form_codes = _text_layer_features(
                    raw_text,
                    threshold=threshold,
                    form_code_pattern=form_code_pattern,
                )
                image_info = page.get_image_info()
                page_area = page.rect.width * page.rect.height
                maximum_coverage = 0.0
                maximum_coverage_image: dict[str, Any] | None = None
                maximum_coverage_bbox: Any | None = None
                for image in image_info:
                    image_bbox = fitz.Rect(image["bbox"])
                    clipped_bbox = image_bbox & page.rect
                    bbox_area = max(0.0, clipped_bbox.width) * max(0.0, clipped_bbox.height)
                    coverage = bbox_area / page_area if page_area else 0.0
                    if maximum_coverage_image is None or coverage > maximum_coverage:
                        maximum_coverage = coverage
                        maximum_coverage_image = image
                        maximum_coverage_bbox = image_bbox
                coverage_ppm = int(round(maximum_coverage * 1_000_000))
                has_dominant_raster = coverage_ppm >= raster_threshold_ppm
                image_pixel_width: int | None = None
                image_pixel_height: int | None = None
                dpi_x_milli: int | None = None
                dpi_y_milli: int | None = None
                dpi_mean_milli: int | None = None
                dpi_band: str | None = None
                if maximum_coverage_image is not None:
                    image_pixel_width = int(maximum_coverage_image["width"])
                    image_pixel_height = int(maximum_coverage_image["height"])
                if has_dominant_raster and maximum_coverage_bbox is not None:
                    if (
                        maximum_coverage_bbox.width == 0
                        or maximum_coverage_bbox.height == 0
                        or image_pixel_width is None
                        or image_pixel_height is None
                    ):
                        raise WaveOnePreOCRStructureError(
                            "dominant raster has invalid display extent"
                        )
                    dpi_x_milli = int(
                        round(image_pixel_width * 72 / abs(maximum_coverage_bbox.width) * 1_000)
                    )
                    dpi_y_milli = int(
                        round(image_pixel_height * 72 / abs(maximum_coverage_bbox.height) * 1_000)
                    )
                    dpi_mean_milli = (dpi_x_milli + dpi_y_milli + 1) // 2
                    dpi_band = _effective_dpi_band(dpi_mean_milli, dpi_step)
                    document_dpi_bands[dpi_band] += 1

                effective_rect = _rect_millipoints(page.rect)
                effective_width = _integer_millipoint(page.rect.width)
                effective_height = _integer_millipoint(page.rect.height)
                if abs(effective_width - effective_height) <= square_tolerance:
                    orientation = "SQUARE"
                elif effective_width > effective_height:
                    orientation = "LANDSCAPE"
                else:
                    orientation = "PORTRAIT"
                rotation = int(page.rotation)
                if rotation not in {0, 90, 180, 270}:
                    raise WaveOnePreOCRStructureError(
                        "PDF page rotation is outside the pre-OCR contract"
                    )
                geometry_family, family_distance = _geometry_family(
                    effective_width,
                    effective_height,
                    references=family_references,
                    maximum_distance_ppm=family_maximum,
                )
                media_box = _rect_millipoints(page.mediabox)
                crop_box = _rect_millipoints(page.cropbox)
                cropbox_differs = media_box != crop_box
                drawing_features = _drawing_features(page.get_drawings(), drawing_tolerance)
                substantive_text = text_features["substantive_extractable_text_layer"]
                route_quadrant = (
                    "TEXT_LAYER_AND_DOMINANT_RASTER"
                    if substantive_text and has_dominant_raster
                    else "TEXT_LAYER_AND_NONDOMINANT_RASTER"
                    if substantive_text
                    else "NO_TEXT_LAYER_AND_DOMINANT_RASTER"
                    if has_dominant_raster
                    else "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER"
                )
                no_text_or_image = (
                    text_features["extractable_non_whitespace_character_count"] == 0
                    and not image_info
                )
                features = {
                    "media_box_mpt": media_box,
                    "crop_box_mpt": crop_box,
                    "effective_rect_mpt": effective_rect,
                    "effective_width_mpt": effective_width,
                    "effective_height_mpt": effective_height,
                    "pdf_rotation_degrees": rotation,
                    "effective_orientation": orientation,
                    "geometry_family_candidate": geometry_family,
                    "geometry_family_distance_ppm": family_distance,
                    "cropbox_differs_from_mediabox": cropbox_differs,
                    "source_route_quadrant": route_quadrant,
                    **text_features,
                    "displayed_image_count": len(image_info),
                    "has_displayed_image": bool(image_info),
                    "maximum_displayed_image_coverage_ppm": coverage_ppm,
                    "has_dominant_displayed_raster": has_dominant_raster,
                    "maximum_coverage_image_pixel_width": image_pixel_width,
                    "maximum_coverage_image_pixel_height": image_pixel_height,
                    "dominant_image_effective_dpi_x_milli": dpi_x_milli,
                    "dominant_image_effective_dpi_y_milli": dpi_y_milli,
                    "dominant_image_effective_dpi_mean_milli": dpi_mean_milli,
                    "dominant_image_effective_dpi_band": dpi_band,
                    "no_extracted_text_or_displayed_image": no_text_or_image,
                    **drawing_features,
                }
                pages.append(
                    {
                        "page_number": page_index + 1,
                        "features": features,
                        "nonzero_alpha_text_layer_form_code_candidates": page_form_codes,
                        "form_code_candidate_status": ("PROXY_UNVALIDATED_RENDER_VISIBILITY"),
                        "form_code_candidates_are_statement_classification": False,
                        "geometry_family_candidate_is_diagnostic_only": True,
                        "render_visibility_validation_status": "NOT_RUN",
                        "ocr_status": "NOT_RUN",
                        "statement_type_status": "UNRESOLVED_PRE_OCR",
                        "table_status": "UNRESOLVED_PRE_OCR",
                        "period_axis_status": "UNRESOLVED_PRE_OCR",
                        "unit_axis_status": "UNRESOLVED_PRE_OCR",
                        "feature_fingerprint_sha256": (
                            _page_feature_fingerprint_sha256(features, feature_contract_sha256)
                        ),
                        "feature_fingerprint_is_canonical_accounting_identity": False,
                        "feature_fingerprint_is_canonical_mapping_authority": False,
                    }
                )
                if page_form_codes:
                    document_form_code_pages.append(
                        {
                            "page_number": page_index + 1,
                            "candidates": page_form_codes,
                            "status": "PROXY_UNVALIDATED_RENDER_VISIBILITY",
                        }
                    )

                expected_upstream_page = {
                    "extractable_text_layer_non_whitespace_char_count": (
                        text_features["extractable_non_whitespace_character_count"]
                    ),
                    "has_any_extractable_text_layer": text_features[
                        "has_any_extractable_text_layer"
                    ],
                    "substantive_extractable_text_layer": substantive_text,
                    "substantive_nonzero_alpha_text_layer": text_features[
                        "substantive_nonzero_alpha_text_layer"
                    ],
                    "substantive_zero_alpha_text_layer": text_features[
                        "substantive_zero_alpha_text_layer"
                    ],
                    "text_layer_span_count_by_alpha": text_features["text_span_count_by_alpha"],
                    "text_layer_character_count_by_alpha": text_features[
                        "text_non_whitespace_character_count_by_alpha"
                    ],
                    "displayed_image_count": len(image_info),
                    "has_displayed_image": bool(image_info),
                    "maximum_displayed_image_page_coverage": round(maximum_coverage, 8),
                    "has_dominant_displayed_raster": has_dominant_raster,
                    "source_route_quadrant": route_quadrant,
                    "no_extracted_text_or_displayed_image": no_text_or_image,
                    "page_number": page_index + 1,
                }
                if upstream_page != expected_upstream_page:
                    raise WaveOnePreOCRStructureError(
                        "published source-profile page evidence does not replay exactly"
                    )
                orientations.append(orientation)
                rotations.append(rotation)
                geometry_families.append(geometry_family)
                route_quadrants.append(route_quadrant)
                document_drawing_paths += drawing_features["drawing_path_count"]
                document_displayed_image_pages += bool(image_info)

            orientation_runs = _run_length_records(orientations)
            rotation_runs = _run_length_records(rotations)
            geometry_family_runs = _run_length_records(geometry_families)
            route_quadrant_runs = _run_length_records(route_quadrants)
            document_summary = {
                "page_count": len(pages),
                "orientation_page_counts": {
                    value: orientations.count(value)
                    for value in ("PORTRAIT", "LANDSCAPE", "SQUARE")
                },
                "rotation_page_counts": {
                    str(value): rotations.count(value) for value in (0, 90, 180, 270)
                },
                "geometry_family_page_counts": {
                    value: geometry_families.count(value)
                    for value in (
                        "A4_GEOMETRY_LIKE",
                        "LETTER_GEOMETRY_LIKE",
                        "OTHER_GEOMETRY",
                    )
                },
                "cropbox_difference_page_count": sum(
                    page_record["features"]["cropbox_differs_from_mediabox"]
                    for page_record in pages
                ),
                "orientation_transition_count": max(0, len(orientation_runs) - 1),
                "rotation_transition_count": max(0, len(rotation_runs) - 1),
                "source_route_quadrant_transition_count": max(0, len(route_quadrant_runs) - 1),
                "dominant_raster_page_count": sum(
                    page_record["features"]["has_dominant_displayed_raster"]
                    for page_record in pages
                ),
                "effective_dpi_band_page_counts": dict(sorted(document_dpi_bands.items())),
                "substantive_extractable_text_page_count": sum(
                    page_record["features"]["substantive_extractable_text_layer"]
                    for page_record in pages
                ),
                "substantive_nonzero_alpha_text_page_count": sum(
                    page_record["features"]["substantive_nonzero_alpha_text_layer"]
                    for page_record in pages
                ),
                "substantive_zero_alpha_text_page_count": sum(
                    page_record["features"]["substantive_zero_alpha_text_layer"]
                    for page_record in pages
                ),
                "nonzero_alpha_text_layer_form_code_candidate_page_count": len(
                    document_form_code_pages
                ),
                "nonzero_alpha_text_layer_form_code_unique_normalized_token_occurrence_count": sum(
                    len(record["candidates"]) for record in document_form_code_pages
                ),
                "vector_drawing_page_count": sum(
                    page_record["features"]["drawing_path_count"] > 0 for page_record in pages
                ),
                "vector_drawing_path_count": document_drawing_paths,
            }
            source_route_candidate = _classify_source_route(
                page_count=len(pages),
                substantive_extracted_text_pages=document_summary[
                    "substantive_extractable_text_page_count"
                ],
                substantive_nonzero_alpha_text_pages=document_summary[
                    "substantive_nonzero_alpha_text_page_count"
                ],
                displayed_image_pages=document_displayed_image_pages,
                dominant_raster_pages=document_summary["dominant_raster_page_count"],
            )
            upstream_reconciliation = {
                "page_count": len(pages),
                "any_extractable_text_layer_page_count": sum(
                    page_record["features"]["has_any_extractable_text_layer"]
                    for page_record in pages
                ),
                "substantive_extractable_text_layer_page_count": document_summary[
                    "substantive_extractable_text_page_count"
                ],
                "substantive_nonzero_alpha_text_layer_page_count": document_summary[
                    "substantive_nonzero_alpha_text_page_count"
                ],
                "substantive_zero_alpha_text_layer_page_count": document_summary[
                    "substantive_zero_alpha_text_page_count"
                ],
                "displayed_image_page_count": document_displayed_image_pages,
                "dominant_displayed_raster_page_count": document_summary[
                    "dominant_raster_page_count"
                ],
                "no_extracted_text_or_displayed_image_page_count": sum(
                    page_record["features"]["no_extracted_text_or_displayed_image"]
                    for page_record in pages
                ),
                "source_route_recommendation": source_route_candidate,
            }
            if any(
                upstream_document.get(key) != value
                for key, value in upstream_reconciliation.items()
            ):
                raise WaveOnePreOCRStructureError(
                    "published source-profile document accounting does not reconcile"
                )

            document_fingerprint = _document_feature_fingerprint_sha256(
                summary=document_summary,
                page_feature_fingerprints=[
                    page_record["feature_fingerprint_sha256"] for page_record in pages
                ],
                orientation_runs=orientation_runs,
                rotation_runs=rotation_runs,
                geometry_family_runs=geometry_family_runs,
                source_route_quadrant_runs=route_quadrant_runs,
                feature_contract_sha256=feature_contract_sha256,
            )
            documents.append(
                {
                    "bank": selected_record["bank"],
                    "document_id": selected_record["document_id"],
                    "relative_path": selected_record["relative_path"],
                    "sha256": selected_record["sha256"],
                    "size_bytes": selected_record["size_bytes"],
                    "page_count": len(pages),
                    "source_route_candidate": source_route_candidate,
                    "source_route_candidate_status": ("UPSTREAM_CANDIDATE_EXACTLY_REPLAYED"),
                    "upstream_source_route_fingerprint_sha256": (upstream_route_fingerprint),
                    "pdf_open_status": {
                        "is_pdf": bool(document.is_pdf),
                        "needs_password": bool(document.needs_pass),
                        "was_repaired": bool(document.is_repaired),
                    },
                    "feature_summary": document_summary,
                    "orientation_runs": orientation_runs,
                    "rotation_runs": rotation_runs,
                    "geometry_family_runs": geometry_family_runs,
                    "source_route_quadrant_feature_runs": route_quadrant_runs,
                    "nonzero_alpha_text_layer_form_code_candidate_pages": (
                        document_form_code_pages
                    ),
                    "form_code_candidate_status": ("PROXY_UNVALIDATED_RENDER_VISIBILITY"),
                    "form_code_candidate_counting_basis": contract["text_layer"][
                        "form_code_candidate_counting_basis"
                    ],
                    "statement_sequence_status": "UNRESOLVED_PRE_OCR",
                    "statement_block_status": "UNRESOLVED_PRE_OCR",
                    "table_topology_status": "UNRESOLVED_PRE_OCR",
                    "period_axis_status": "UNRESOLVED_PRE_OCR",
                    "unit_axis_status": "UNRESOLVED_PRE_OCR",
                    "scope_status": "UNRESOLVED_PRE_OCR",
                    "cash_flow_method_status": "UNRESOLVED_PRE_OCR",
                    "notes_boundary_status": "UNRESOLVED_PRE_OCR",
                    "source_row_sequence_status": "UNRESOLVED_PRE_OCR",
                    "hierarchy_signature_status": "UNRESOLVED_PRE_OCR",
                    "render_visibility_validation_status": "NOT_RUN",
                    "ocr_status": "NOT_RUN",
                    "pages": pages,
                    "document_feature_fingerprint_sha256": document_fingerprint,
                    "document_feature_fingerprint_is_canonical_accounting_identity": False,
                    "document_feature_fingerprint_is_canonical_mapping_authority": False,
                    "fingerprint_retention_boundary": contract["fingerprint"],
                }
            )
            source_pdf_ledger.append(
                {
                    "bank": selected_record["bank"],
                    "document_id": selected_record["document_id"],
                    "relative_path": selected_record["relative_path"],
                    "sha256": selected_record["sha256"],
                    "size_bytes": selected_record["size_bytes"],
                    "page_count": len(pages),
                    "hash_and_size_revalidation_status": "MATCH",
                    "upstream_source_route_fingerprint_sha256": (upstream_route_fingerprint),
                    "upstream_source_route_candidate": source_route_candidate,
                    "source_profile_reconciliation_status": "EXACT_PAGE_AND_DOCUMENT_REPLAY",
                }
            )
        finally:
            document.close()

        summary = documents[-1]["feature_summary"]
        total_pages += summary["page_count"]
        corpus_orientation.update(summary["orientation_page_counts"])
        corpus_rotation.update(summary["rotation_page_counts"])
        corpus_geometry_family_pages.update(summary["geometry_family_page_counts"])
        for family, count in summary["geometry_family_page_counts"].items():
            if count:
                corpus_geometry_family_documents[family] += 1
        corpus_dpi_bands.update(summary["effective_dpi_band_page_counts"])
        corpus_route_candidates[documents[-1]["source_route_candidate"]] += 1
        corpus_route_quadrants.update(
            page_record["features"]["source_route_quadrant"]
            for page_record in documents[-1]["pages"]
        )
        orientation_transitions += summary["orientation_transition_count"]
        rotation_transitions += summary["rotation_transition_count"]
        route_quadrant_transitions += summary["source_route_quadrant_transition_count"]
        cropbox_differences += summary["cropbox_difference_page_count"]
        displayed_image_pages += sum(
            page_record["features"]["has_displayed_image"] for page_record in documents[-1]["pages"]
        )
        dominant_raster_pages += summary["dominant_raster_page_count"]
        any_text_pages += sum(
            page_record["features"]["has_any_extractable_text_layer"]
            for page_record in documents[-1]["pages"]
        )
        substantive_text_pages += summary["substantive_extractable_text_page_count"]
        nonzero_alpha_pages += summary["substantive_nonzero_alpha_text_page_count"]
        zero_alpha_pages += summary["substantive_zero_alpha_text_page_count"]
        no_text_or_image_pages += sum(
            page_record["features"]["no_extracted_text_or_displayed_image"]
            for page_record in documents[-1]["pages"]
        )
        form_code_pages += summary["nonzero_alpha_text_layer_form_code_candidate_page_count"]
        form_code_documents += (
            summary["nonzero_alpha_text_layer_form_code_candidate_page_count"] > 0
        )
        form_code_token_occurrences += summary[
            "nonzero_alpha_text_layer_form_code_unique_normalized_token_occurrence_count"
        ]
        drawing_pages += summary["vector_drawing_page_count"]
        drawing_paths += summary["vector_drawing_path_count"]

    accounting = {
        "selected_document_count": len(documents),
        "pdf_hash_and_size_revalidated_document_count": len(documents),
        "source_profile_exactly_reconciled_document_count": len(documents),
        "pre_ocr_feature_profiled_document_count": len(documents),
        "total_pdf_page_count": total_pages,
        "page_geometry_accounted_count": total_pages,
        "page_source_route_quadrant_feature_accounted_count": total_pages,
        "text_layer_traversed_page_count": total_pages,
        "orientation_page_counts": {
            value: corpus_orientation[value] for value in ("PORTRAIT", "LANDSCAPE", "SQUARE")
        },
        "rotation_page_counts": {
            str(value): corpus_rotation[str(value)] for value in (0, 90, 180, 270)
        },
        "orientation_transition_count": orientation_transitions,
        "rotation_transition_count": rotation_transitions,
        "source_route_quadrant_transition_count": route_quadrant_transitions,
        "portrait_only_document_count": sum(
            document_record["feature_summary"]["orientation_page_counts"]["PORTRAIT"]
            == document_record["page_count"]
            for document_record in documents
        ),
        "mixed_orientation_document_count": sum(
            document_record["feature_summary"]["orientation_page_counts"]["LANDSCAPE"] > 0
            and document_record["feature_summary"]["orientation_page_counts"]["PORTRAIT"] > 0
            for document_record in documents
        ),
        "geometry_family_page_counts": {
            value: corpus_geometry_family_pages[value]
            for value in (
                "A4_GEOMETRY_LIKE",
                "LETTER_GEOMETRY_LIKE",
                "OTHER_GEOMETRY",
            )
        },
        "geometry_family_document_counts": {
            value: corpus_geometry_family_documents[value]
            for value in (
                "A4_GEOMETRY_LIKE",
                "LETTER_GEOMETRY_LIKE",
                "OTHER_GEOMETRY",
            )
        },
        "cropbox_difference_page_count": cropbox_differences,
        "displayed_image_page_count": displayed_image_pages,
        "dominant_raster_page_count": dominant_raster_pages,
        "effective_dpi_band_page_counts": dict(sorted(corpus_dpi_bands.items())),
        "any_extractable_text_layer_page_count": any_text_pages,
        "substantive_extractable_text_page_count": substantive_text_pages,
        "substantive_nonzero_alpha_text_page_count": nonzero_alpha_pages,
        "substantive_zero_alpha_text_page_count": zero_alpha_pages,
        "no_extracted_text_or_displayed_image_page_count": no_text_or_image_pages,
        "source_route_candidate_counts": {
            value: corpus_route_candidates[value] for value in _ROUTE_VOCABULARY
        },
        "source_route_quadrant_page_counts": {
            value: corpus_route_quadrants[value] for value in _ROUTE_QUADRANT_VOCABULARY
        },
        "nonzero_alpha_text_layer_form_code_candidate_page_count": form_code_pages,
        "nonzero_alpha_text_layer_form_code_candidate_document_count": (form_code_documents),
        "nonzero_alpha_text_layer_form_code_unique_normalized_token_occurrence_count": form_code_token_occurrences,
        "form_code_candidate_statement_classification_count": 0,
        "vector_drawing_page_count": drawing_pages,
        "vector_drawing_path_count": drawing_paths,
        "structurally_surveyed_document_count": 0,
        "statement_sequence_classified_document_count": 0,
        "source_accounted_statement_block_count": 0,
        "source_accounted_statement_page_count": 0,
        "statement_type_classified_page_count": 0,
        "accepted_title_candidate_count": 0,
        "accepted_table_count": 0,
        "source_accounted_table_count": 0,
        "source_accounted_logical_row_count": 0,
        "source_accounted_visible_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "source_accounted_period_axis_count": 0,
        "source_accounted_unit_axis_count": 0,
        "source_accounted_scope_count": 0,
        "source_accounted_hierarchy_relationship_count": 0,
        "render_visibility_validated_page_count": 0,
        "ocr_processed_page_count": 0,
        "financial_value_semantically_extracted_count": 0,
        "verbatim_financial_value_retained_count": 0,
        "absence_declaration_count": 0,
        "unresolved_statement_sequence_document_count": len(documents),
        "unresolved_statement_block_document_count": len(documents),
        "unresolved_table_topology_document_count": len(documents),
        "unresolved_period_axis_document_count": len(documents),
        "unresolved_unit_axis_document_count": len(documents),
        "unresolved_scope_document_count": len(documents),
        "unresolved_cash_flow_method_document_count": len(documents),
        "unresolved_notes_boundary_document_count": len(documents),
        "schema_used": False,
        "canonical_mapping_attempted": False,
        "role_a_used": False,
        "historical_values_used": False,
        "bank_specific_routing_used": False,
        "absence_claims_allowed": False,
    }
    expected_accounting = policy["expected_accounting"]
    replayed_expected = {key: accounting.get(key) for key in expected_accounting}
    if replayed_expected != expected_accounting:
        raise WaveOnePreOCRStructureError(
            "pre-OCR corpus accounting drifted from the locked Wave 1 inputs: "
            f"expected={expected_accounting!r} observed={replayed_expected!r}"
        )

    policy_path_resolved = project_root / POLICY_RELATIVE_PATH
    implementation_path = project_root / IMPLEMENTATION_RELATIVE_PATH
    inventory_ledger["selected_document_count"] = len(selected_documents)
    inventory_ledger["selected_pdf_page_count"] = total_pages
    inventory_ledger["selection_receipt_sha256"] = selection_receipt
    source_profile_ledger["profiled_document_count"] = len(source_profiles)
    source_profile_ledger["profiled_pdf_page_count"] = total_pages
    source_profile_ledger["selection_receipt_sha256"] = selection_receipt
    output_contract = policy["output"]
    return {
        "format_version": output_contract["format"],
        "policy": policy["policy"],
        "claim_boundary": policy["claim_boundary"],
        "status": output_contract["status"],
        "authority": {
            "kind": "FIXED_WAVE_1_PRE_OCR_STRUCTURE_POLICY_V1",
            "path": POLICY_RELATIVE_PATH.as_posix(),
            "sha256": sha256_file(policy_path_resolved),
            "size_bytes": policy_path_resolved.stat().st_size,
            "policy": policy["policy"],
            "claim_boundary": policy["claim_boundary"],
        },
        "selection_receipt_sha256": selection_receipt,
        "upstream_artifacts_rebuilt_by_this_run": False,
        "inputs": [inventory_ledger, source_profile_ledger],
        "source_pdf_ledger": source_pdf_ledger,
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "sha256": sha256_file(implementation_path),
            "pymupdf_binding_version": fitz.VersionBind,
            "pymupdf_runtime_versions": list(fitz.version),
        },
        "safety": policy["safety"],
        "feature_contract": contract,
        "feature_contract_sha256": feature_contract_sha256,
        "feature_fingerprints_are_canonical_accounting_identity": False,
        "feature_fingerprints_are_canonical_mapping_authority": False,
        "form_code_candidate_counting_basis": contract["text_layer"][
            "form_code_candidate_counting_basis"
        ],
        "accounting": accounting,
        "documents": documents,
    }


def publish_wave_one_pre_ocr_structure_features(
    project_root: Path,
    *,
    policy_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[Path, str, int]:
    project_root = project_root.resolve()
    policy_path = (policy_path or project_root / POLICY_RELATIVE_PATH).resolve()
    output_path = (output_path or project_root / OUTPUT_RELATIVE_PATH).resolve()
    expected_output = (project_root / OUTPUT_RELATIVE_PATH).resolve()
    if output_path != expected_output or not output_path.is_relative_to(project_root):
        raise WaveOnePreOCRStructureError("Wave 1 pre-OCR structure output location is invalid")
    payload = build_wave_one_pre_ocr_structure_features(project_root, policy_path)
    encoded = _canonical_json_bytes(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(output_path, flags, 0o644)
    except FileExistsError as error:
        raise WaveOnePreOCRStructureError(
            "Wave 1 pre-OCR structure output already exists"
        ) from error
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
        identity = os.fstat(descriptor)
        if not stat.S_ISREG(identity.st_mode) or identity.st_size != len(encoded):
            raise WaveOnePreOCRStructureError(
                "Wave 1 pre-OCR structure publication identity drifted"
            )
    except Exception:
        os.close(descriptor)
        output_path.unlink(missing_ok=True)
        raise
    os.close(descriptor)
    return output_path, sha256_bytes(encoded), len(encoded)
