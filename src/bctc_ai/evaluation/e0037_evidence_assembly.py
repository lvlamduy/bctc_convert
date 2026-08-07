from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import stat
import unicodedata
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError


class E0037SourceStructureError(RuntimeError):
    """Raised when the source-only E-0037 structure cannot be assembled safely."""


SOURCE_STRUCTURE_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/source_structure.json"
)
SOURCE_STRUCTURE_STATE = "SOURCE_ONLY_STRUCTURE_SEALED_BEFORE_SCHEMA_ACCESS"
E0035_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0035-mbb-cdkt-logical-row-label-crops.json")
SOURCE_STRUCTURE_CANONICALIZATION = "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_V1"
# Updated only when the frozen inputs or deterministic source-only contract change.
SOURCE_STRUCTURE_CANONICAL_SHA256 = (
    "ef098a659f8b557ac3a801edccfc7c0848be9a512b47ba7c9278cd3873f70728"
)
SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES = 136042

_E0035_SEAL_SHA256 = "a1bb81e895b45d003910aba523ba121461f15079b9452dde8d508600c5dcc3e3"
_E0035_SEAL_SIZE = 5131
_E0035_MANIFEST_PATH = PurePosixPath(
    "output/calibration/e0035-mbb-cdkt-logical-row-label-crops/"
    "a177792e8b98f340f562/crop_manifest.json"
)
_E0035_MANIFEST_SHA256 = "3b12da05e19467e85bfc6d828b73a3e35598c53d7c57cfb932b76763bec57eac"
_E0035_MANIFEST_SIZE = 70663
_CROP_ROOT = _E0035_MANIFEST_PATH.parent / "crops"
_EXPECTED_ROWS_BY_PAGE = {3: 39, 4: 25}
_EXPECTED_ROW_COUNT = 64
_EXPECTED_SEAL_STATUS = "PASS_REFERENCE_BLIND_ALL_LOGICAL_ROW_LABEL_CROPS_FROZEN"

_SOURCE_ONLY_CONTRACT = {
    "permitted_input_kinds": [
        "E0035_SEAL",
        "E0035_CROP_MANIFEST",
        "REGISTERED_LABEL_CROP_PNG",
    ],
    "forbidden_input_kinds": [
        "SCHEMA_OR_WORKBOOK",
        "E0030_MAPPING",
        "E0033_ROW_CONTRACT",
        "E0034_NUMERIC_VERIFICATION",
        "E0036_READER_REVIEW_OR_HISTORY",
        "HUMAN_REVIEW",
        "HISTORICAL_OR_MONGODB_DATA",
        "NUMERIC_CELL_TEXT_VALUE_OR_STATUS",
    ],
    "geometry_authority": "E0035_CROP_MANIFEST",
    "typography_authority": {
        "font_weight_and_slant": "REGISTERED_SOURCE_PIXELS",
        "case_role": "E0035_FROZEN_PPOCR_TEXT_PROVENANCE_ONLY",
    },
    "lexical_row_role_authority": "E0035_FROZEN_PPOCR_TEXT_PROVENANCE_ONLY",
    "x_indentation_used": False,
    "note_reference_used_as_schema_numbering": False,
    "child_set_completion_policy": "UNKNOWN_UNLESS_PIXELS_PROVE_COMPLETE",
    "derivation_binding": "EXACT_CANONICAL_PAYLOAD_IDENTITY_REQUIRED_BEFORE_SCHEMA_ACCESS",
}

_AUTHORITY = {
    "source_pixels_are_font_weight_and_slant_authority": True,
    "e0035_manifest_is_geometry_and_raw_label_provenance": True,
    "e0035_frozen_raw_label_is_case_and_lexical_role_authority": True,
    "schema_loaded": False,
    "workbook_or_template_loaded": False,
    "e0030_loaded": False,
    "e0033_loaded": False,
    "e0034_loaded": False,
    "e0036_review_or_history_loaded": False,
    "human_review_loaded": False,
    "historical_or_mongodb_data_loaded": False,
    "numeric_cell_evidence_loaded": False,
    "period_unit_scope_answer_loaded": False,
    "schema_mapping_invoked": False,
    "accounting_validation_invoked": False,
}

_GATES = {
    "exact_e0035_seal_hash_and_size": True,
    "exact_e0035_manifest_hash_and_size": True,
    "page_render_identities_bound_transitively_without_opening_pixels": True,
    "all_64_registered_crop_hashes_verified": True,
    "all_paths_canonical_and_inside_exact_allowlist": True,
    "all_reads_regular_nofollow_and_identity_stable": True,
    "font_weight_and_slant_derived_from_registered_pixels": True,
    "casing_and_lexical_roles_derived_from_e0035_frozen_raw_labels": True,
    "x_indentation_not_used": True,
    "note_references_not_used_as_schema_numbering": True,
    "schema_review_history_numeric_inputs_not_opened": True,
    "all_child_sets_fail_closed_unknown": True,
    "canonical_payload_identity_matches_precommitted_source_only_identity": True,
}

SOURCE_STRUCTURE_CLAIM_BOUNDARY = (
    "Seal A records deterministic source-only font-weight and slant evidence derived from "
    "registered crop pixels; casing and lexical row-role evidence derived from frozen E-0035 "
    "PP-OCR raw-label provenance; row-role proposals; and physical parent/section edges for "
    "the 64 E-0035 rows. Its exact canonical payload SHA-256 and size must be bound before "
    "schema access because payload-only validation cannot independently prove pixel or manifest "
    "derivation. It does not establish schema identity, mapping, period, unit, scope, numeric "
    "truth, accounting validity, Excel correctness, holdout accuracy, or production readiness; "
    "unsupported structure remains UNKNOWN."
)

_SAMPLE_KEYS = {
    "category",
    "crop_height",
    "crop_path",
    "crop_sha256",
    "crop_width",
    "label_line_indices",
    "label_union_bbox",
    "note_right_edge",
    "page",
    "ppocr_boxes",
    "ppocr_scores",
    "ppocr_text",
    "row_ordinal",
    "sample_id",
    "source_crop_bbox",
    "source_row_ids",
}
_ROW_ROLES = {"SECTION", "TOTAL", "GROUP", "DETAIL", "UNKNOWN"}
_TYPOGRAPHY_ROLES = {
    "BOLD_UPRIGHT",
    "BOLD_ITALIC",
    "REGULAR_UPRIGHT",
    "REGULAR_ITALIC",
}
_ROW_KEYS = {
    "row_id",
    "source_order",
    "page",
    "row_ordinal",
    "raw_label",
    "label_provenance",
    "crop",
    "page_render",
    "geometry",
    "typography",
    "typography_role",
    "row_role",
    "row_role_candidates",
    "structural_evidence",
    "physical_parent_row_id",
    "section_row_id",
    "child_set_complete",
}
_TYPOGRAPHY_METRIC_KEYS = {
    "analysis_left_trim_pixels",
    "otsu_threshold",
    "ink_pixel_count",
    "eroded_ink_pixel_count",
    "erosion_survival_ppm",
    "upright_projection_energy",
    "best_italic_projection_energy",
    "italic_gain_ppm",
    "uppercase_ratio_ppm",
}
_FORBIDDEN_PAYLOAD_KEYS = {
    "reportnormid",
    "report_norm_id",
    "schema_id",
    "schema_candidates",
    "raw_numeric_text",
    "normalized_numeric_value",
    "normalized_value",
    "period",
    "period_role",
    "unit",
    "scope",
    "review_answer",
    "historical_value",
}


@dataclass(frozen=True)
class _StableBytes:
    data: bytes
    sha256: str
    size_bytes: int


def canonical_payload_identity(payload: dict[str, Any]) -> dict[str, str | int]:
    """Return the canonical content identity that must be sealed before schema access.

    Payload-only validation can check deterministic internal derivations, but it cannot
    reopen pixels or the E-0035 manifest. A later phase must compare this identity with
    the precommitted constants (or an independently published pre-schema seal).
    """

    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise E0037SourceStructureError("Seal A payload is not canonical finite JSON") from error
    return {
        "canonicalization": SOURCE_STRUCTURE_CANONICALIZATION,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "size_bytes": len(encoded),
    }


def _same_json_type_and_value(value: Any, expected: Any) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(
            _same_json_type_and_value(value[key], child) for key, child in expected.items()
        )
    if isinstance(expected, list):
        return len(value) == len(expected) and all(
            _same_json_type_and_value(item, expected_item)
            for item, expected_item in zip(value, expected, strict=True)
        )
    return value == expected


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_relative(
    value: str | Path, *, expected: PurePosixPath | None = None
) -> PurePosixPath:
    text = value.as_posix() if isinstance(value, Path) else value
    if not isinstance(text, str) or not text or "\\" in text:
        raise E0037SourceStructureError(f"invalid project-relative path: {value!r}")
    relative = PurePosixPath(text)
    if relative.is_absolute() or "." in relative.parts or ".." in relative.parts:
        raise E0037SourceStructureError(f"unsafe project-relative path: {value!r}")
    if relative.as_posix() != text:
        raise E0037SourceStructureError(f"non-canonical project-relative path: {value!r}")
    if expected is not None and relative != expected:
        raise E0037SourceStructureError(
            f"path is outside the sealed source-only contract: {relative.as_posix()}"
        )
    return relative


def _project_root(project_root: Path) -> Path:
    raw = Path(project_root)
    if raw.is_symlink():
        raise E0037SourceStructureError("project root must not be a symlink")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as error:
        raise E0037SourceStructureError("project root is unavailable") from error
    if not resolved.is_dir():
        raise E0037SourceStructureError("project root must be a directory")
    return resolved


def _reject_symlink_components(root: Path, relative: PurePosixPath) -> Path:
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise E0037SourceStructureError(
                f"required source-only input is absent: {relative}"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise E0037SourceStructureError(f"symlink component is forbidden: {relative}")
    return root.joinpath(*relative.parts)


def _same_identity(before: os.stat_result, after: os.stat_result) -> bool:
    return (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) == (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )


def _open_nofollow(root: Path, relative: PurePosixPath) -> int:
    directory_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    directory_flags |= getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    file_flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptor: int | None = None
    try:
        directory_descriptor = os.open(root, directory_flags)
        for component in relative.parts[:-1]:
            next_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        return os.open(relative.parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as error:
        raise E0037SourceStructureError(
            f"cannot open sealed input without symlinks: {relative}"
        ) from error
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _stable_read(
    root: Path,
    relative: PurePosixPath,
    *,
    expected_sha256: str | None,
    expected_size: int | None,
    maximum_size: int,
) -> _StableBytes:
    _reject_symlink_components(root, relative)
    descriptor = _open_nofollow(root, relative)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise E0037SourceStructureError(f"sealed input is not a regular file: {relative}")
        if before.st_size > maximum_size:
            raise E0037SourceStructureError(f"sealed input exceeds size bound: {relative}")
        if expected_size is not None and before.st_size != expected_size:
            raise E0037SourceStructureError(f"sealed input size drifted: {relative}")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise E0037SourceStructureError(f"sealed input truncated during read: {relative}")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise E0037SourceStructureError(f"sealed input grew during read: {relative}")
        after = os.fstat(descriptor)
        if not _same_identity(before, after):
            raise E0037SourceStructureError(f"sealed input changed during read: {relative}")
    finally:
        os.close(descriptor)

    final_path = _reject_symlink_components(root, relative)
    final = os.lstat(final_path)
    if not _same_identity(before, final):
        raise E0037SourceStructureError(f"sealed input identity changed after read: {relative}")
    data = b"".join(chunks)
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise E0037SourceStructureError(f"sealed input SHA-256 drifted: {relative}")
    return _StableBytes(data=data, sha256=digest, size_bytes=len(data))


def _json_object(record: _StableBytes, name: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_nonfinite_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        payload = json.loads(
            record.data.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise E0037SourceStructureError(f"{name} is not canonical UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise E0037SourceStructureError(f"{name} must be a JSON object")
    return payload


def _png_array(
    record: _StableBytes, *, expected_width: int | None, expected_height: int | None
) -> np.ndarray:
    try:
        with Image.open(BytesIO(record.data)) as image:
            if image.format != "PNG":
                raise E0037SourceStructureError("registered source image must be PNG")
            image.load()
            if expected_width is not None and image.width != expected_width:
                raise E0037SourceStructureError("registered crop width drifted")
            if expected_height is not None and image.height != expected_height:
                raise E0037SourceStructureError("registered crop height drifted")
            return np.asarray(image.convert("L"), dtype=np.uint8).copy()
    except (OSError, UnidentifiedImageError) as error:
        raise E0037SourceStructureError("registered source image cannot be decoded") from error


def _otsu_threshold(gray: np.ndarray) -> int:
    histogram = np.bincount(gray.reshape(-1), minlength=256)
    total = int(gray.size)
    total_sum = sum(index * int(count) for index, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0
    best_numerator = -1
    best_denominator = 1
    best_threshold = 0
    for threshold, raw_count in enumerate(histogram):
        count = int(raw_count)
        background_weight += count
        background_sum += threshold * count
        foreground_weight = total - background_weight
        if background_weight == 0:
            continue
        if foreground_weight == 0:
            break
        difference = total_sum * background_weight - background_sum * total
        numerator = difference * difference
        denominator = background_weight * foreground_weight
        if numerator * best_denominator > best_numerator * denominator:
            best_numerator = numerator
            best_denominator = denominator
            best_threshold = threshold
    return best_threshold


def _erosion_count(mask: np.ndarray) -> int:
    if mask.shape[0] < 3 or mask.shape[1] < 3:
        return 0
    eroded = mask[1:-1, 1:-1].copy()
    for delta_y in (-1, 0, 1):
        for delta_x in (-1, 0, 1):
            eroded &= mask[
                1 + delta_y : mask.shape[0] - 1 + delta_y,
                1 + delta_x : mask.shape[1] - 1 + delta_x,
            ]
    return int(np.count_nonzero(eroded))


def _projection_energy(y_coordinates: np.ndarray, x_coordinates: np.ndarray, numerator: int) -> int:
    denominator = 25
    shifts = (y_coordinates * numerator + denominator // 2) // denominator
    projected = x_coordinates + shifts
    counts = np.bincount(projected, minlength=int(projected.max()) + 1).astype(np.int64)
    return int(counts @ counts)


def _case_ratio(text: str) -> int:
    cased = [character for character in text if character.isalpha()]
    if not cased:
        return 0
    return sum(character.isupper() for character in cased) * 1_000_000 // len(cased)


def _normalized_visible_label(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold().replace("đ", "d"))
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(
        "".join(character if character.isalnum() else " " for character in without_marks).split()
    )


def _typography(gray: np.ndarray, text: str, manifest: dict[str, Any]) -> dict[str, Any]:
    policy = manifest.get("crop_policy")
    if not isinstance(policy, dict):
        raise E0037SourceStructureError("E-0035 crop policy is missing")
    source_padding = policy.get("source_padding_left_top_right_bottom")
    white_border = policy.get("white_border_left_top_right_bottom")
    if source_padding != [8, 4, 8, 4] or white_border != [12, 8, 12, 8]:
        raise E0037SourceStructureError("E-0035 crop padding drifted")
    analysis_left_trim = int(source_padding[0]) + int(white_border[0]) + 4
    if gray.shape[1] <= analysis_left_trim + 8:
        raise E0037SourceStructureError("registered crop is too narrow for typography analysis")
    analysis = gray[:, analysis_left_trim:]
    threshold = _otsu_threshold(analysis)
    mask = analysis <= threshold
    ink_count = int(np.count_nonzero(mask))
    if ink_count < 20:
        raise E0037SourceStructureError("registered crop has insufficient visible ink")
    eroded_count = _erosion_count(mask)
    erosion_survival_ppm = eroded_count * 1_000_000 // ink_count
    y_coordinates, x_coordinates = np.where(mask)
    upright_energy = _projection_energy(y_coordinates, x_coordinates, 0)
    italic_energies = [
        _projection_energy(y_coordinates, x_coordinates, numerator) for numerator in (3, 4, 5, 6)
    ]
    best_italic_energy = max(italic_energies)
    italic_gain_ppm = best_italic_energy * 1_000_000 // upright_energy
    uppercase_ratio_ppm = _case_ratio(text)
    font_weight = "BOLD" if erosion_survival_ppm >= 480_000 else "REGULAR"
    font_slant = "ITALIC" if italic_gain_ppm >= 1_005_000 else "UPRIGHT"
    case_role = "UPPERCASE" if uppercase_ratio_ppm >= 800_000 else "MIXED"
    return {
        "font_weight": font_weight,
        "font_slant": font_slant,
        "case_role": case_role,
        "metrics": {
            "analysis_left_trim_pixels": analysis_left_trim,
            "otsu_threshold": threshold,
            "ink_pixel_count": ink_count,
            "eroded_ink_pixel_count": eroded_count,
            "erosion_survival_ppm": erosion_survival_ppm,
            "upright_projection_energy": upright_energy,
            "best_italic_projection_energy": best_italic_energy,
            "italic_gain_ppm": italic_gain_ppm,
            "uppercase_ratio_ppm": uppercase_ratio_ppm,
        },
    }


def _valid_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _bbox(value: Any, name: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(_valid_int(item) for item in value)
        or any(item < 0 for item in value)
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise E0037SourceStructureError(f"invalid {name}")
    return list(value)


def _classify_row_roles(rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(rows):
        next_row = rows[index + 1] if index + 1 < len(rows) else None
        if next_row is not None and next_row["page"] != row["page"]:
            next_row = None
        normalized = _normalized_visible_label(row["raw_label"])
        typography = row["typography"]
        is_uppercase = typography["case_role"] == "UPPERCASE"
        is_total = is_uppercase and (normalized == "tong" or normalized.startswith("tong "))
        if is_total:
            role = "TOTAL"
            candidates = ["TOTAL"]
            evidence = ["FROZEN_RAW_LABEL_UPPERCASE", "FROZEN_RAW_LABEL_TOTAL_LEXEME"]
        elif is_uppercase:
            if next_row is not None:
                next_normalized = _normalized_visible_label(next_row["raw_label"])
                next_is_total = next_row["typography"]["case_role"] == "UPPERCASE" and (
                    next_normalized == "tong" or next_normalized.startswith("tong ")
                )
            else:
                next_is_total = False
            if next_row is not None and not next_is_total:
                role = "SECTION"
                candidates = ["SECTION"]
                evidence = ["FROZEN_RAW_LABEL_UPPERCASE", "FOLLOWING_NON_TOTAL_ROW"]
            else:
                role = "UNKNOWN"
                candidates = ["SECTION", "DETAIL"]
                evidence = ["FROZEN_RAW_LABEL_UPPERCASE", "NO_PIXEL_PROVEN_CHILD"]
        else:
            current_bold = typography["font_weight"] == "BOLD"
            current_italic = typography["font_slant"] == "ITALIC"
            lower_style_follows = False
            if next_row is not None and next_row["typography"]["case_role"] != "UPPERCASE":
                following = next_row["typography"]
                if current_bold and not current_italic:
                    lower_style_follows = (
                        following["font_weight"] == "REGULAR" or following["font_slant"] == "ITALIC"
                    )
                elif current_italic:
                    lower_style_follows = (
                        following["font_weight"] == "REGULAR"
                        and following["font_slant"] == "UPRIGHT"
                    )
            if lower_style_follows:
                role = "GROUP"
                candidates = ["GROUP"]
                evidence = ["PIXEL_STYLE_EMPHASIS", "FOLLOWING_LOWER_TYPOGRAPHIC_LEVEL"]
            else:
                role = "DETAIL"
                candidates = ["DETAIL"]
                evidence = ["NO_PIXEL_PROVEN_CHILD"]
        row["row_role"] = role
        row["row_role_candidates"] = candidates
        row["structural_evidence"] = evidence


def _assign_source_only_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    active_section: str | None = None
    bold_group: str | None = None
    italic_group: str | None = None
    current_page: int | None = None
    for row in rows:
        if row["page"] != current_page:
            current_page = row["page"]
            active_section = None
            bold_group = None
            italic_group = None
        role = row["row_role"]
        typography = row["typography"]
        normalized = _normalized_visible_label(row["raw_label"])
        parent: str | None = None
        section: str | None = active_section
        if role == "SECTION":
            active_section = row["row_id"]
            section = None
            bold_group = None
            italic_group = None
        elif role == "TOTAL":
            if " va " in f" {normalized} ":
                section = None
            bold_group = None
            italic_group = None
        elif role == "UNKNOWN":
            bold_group = None
            italic_group = None
        elif role == "GROUP":
            if typography["font_slant"] == "ITALIC":
                parent = bold_group
                italic_group = row["row_id"]
            else:
                parent = None
                bold_group = row["row_id"]
                italic_group = None
        else:
            if typography["font_slant"] == "ITALIC":
                italic_group = None
                parent = None
            elif typography["font_weight"] == "BOLD":
                bold_group = None
                italic_group = None
            else:
                parent = italic_group or bold_group
        row["physical_parent_row_id"] = parent
        row["section_row_id"] = section
        row["child_set_complete"] = "UNKNOWN"
        if section is not None:
            edges.append(
                {
                    "parent_row_id": section,
                    "child_row_id": row["row_id"],
                    "relation_type": "SECTION_MEMBER",
                    "evidence": [
                        "CONTIGUOUS_SOURCE_ORDER",
                        "FROZEN_RAW_LABEL_SECTION_HEADING_CASE",
                        "NO_INTERVENING_CONFIRMED_SECTION",
                    ],
                }
            )
        if parent is not None:
            edges.append(
                {
                    "parent_row_id": parent,
                    "child_row_id": row["row_id"],
                    "relation_type": "PHYSICAL_PARENT",
                    "evidence": [
                        "CONTIGUOUS_SOURCE_ORDER",
                        "PARENT_GROUP_PIXEL_STYLE",
                        "CHILD_LOWER_OR_PEER_TYPOGRAPHIC_LEVEL",
                    ],
                }
            )
    return edges


def _page_record(page_sources: Any, page: int) -> dict[str, Any]:
    if not isinstance(page_sources, list):
        raise E0037SourceStructureError("E-0035 page sources are missing")
    matching = [
        item for item in page_sources if isinstance(item, dict) and item.get("page") == page
    ]
    if len(matching) != 1:
        raise E0037SourceStructureError(f"E-0035 page {page} render is not unique")
    render = matching[0].get("render")
    if not isinstance(render, dict):
        raise E0037SourceStructureError(f"E-0035 page {page} render identity is missing")
    return render


def _assemble_rows(
    root: Path,
    manifest: dict[str, Any],
    page_records: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    samples = manifest.get("samples")
    if not isinstance(samples, list) or len(samples) != _EXPECTED_ROW_COUNT:
        raise E0037SourceStructureError("E-0035 sample denominator drifted")
    rows: list[dict[str, Any]] = []
    page_ordinals: Counter[int] = Counter()
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for source_order, sample in enumerate(samples):
        if not isinstance(sample, dict) or set(sample) != _SAMPLE_KEYS:
            raise E0037SourceStructureError("E-0035 sample field set drifted")
        page = sample.get("page")
        row_ordinal = sample.get("row_ordinal")
        if page not in _EXPECTED_ROWS_BY_PAGE or not _valid_int(row_ordinal):
            raise E0037SourceStructureError("E-0035 sample page or ordinal is invalid")
        if row_ordinal != page_ordinals[page]:
            raise E0037SourceStructureError("E-0035 sample ordering is not contiguous")
        page_ordinals[page] += 1
        expected_id = f"page-{page:04d}-row-{row_ordinal:03d}-label"
        if sample.get("sample_id") != expected_id or expected_id in seen_ids:
            raise E0037SourceStructureError("E-0035 sample identity drifted")
        seen_ids.add(expected_id)
        crop_relative = _canonical_relative(str(sample.get("crop_path", "")))
        expected_crop = _CROP_ROOT / f"{expected_id}.png"
        if crop_relative != expected_crop:
            raise E0037SourceStructureError("E-0035 crop path escaped the registered crop set")
        crop_sha256 = sample.get("crop_sha256")
        if not isinstance(crop_sha256, str) or len(crop_sha256) != 64 or crop_sha256 in seen_hashes:
            raise E0037SourceStructureError("E-0035 crop SHA-256 set is invalid")
        seen_hashes.add(crop_sha256)
        crop_record = _stable_read(
            root,
            crop_relative,
            expected_sha256=crop_sha256,
            expected_size=None,
            maximum_size=2 * 1024 * 1024,
        )
        crop_width = sample.get("crop_width")
        crop_height = sample.get("crop_height")
        if not _valid_int(crop_width) or not _valid_int(crop_height):
            raise E0037SourceStructureError("E-0035 crop dimensions are invalid")
        gray = _png_array(
            crop_record,
            expected_width=crop_width,
            expected_height=crop_height,
        )
        raw_label = sample.get("ppocr_text")
        if not isinstance(raw_label, str) or not raw_label.strip():
            raise E0037SourceStructureError("E-0035 raw label provenance is invalid")
        typography = _typography(gray, raw_label, manifest)
        typography_role = f"{typography['font_weight']}_{typography['font_slant']}"
        if typography_role not in _TYPOGRAPHY_ROLES:
            raise E0037SourceStructureError("unexpected typography role")
        boxes = sample.get("ppocr_boxes")
        scores = sample.get("ppocr_scores")
        if (
            not isinstance(boxes, list)
            or not boxes
            or not isinstance(scores, list)
            or len(scores) != len(boxes)
            or any(
                not isinstance(score, (int, float)) or isinstance(score, bool) for score in scores
            )
        ):
            raise E0037SourceStructureError("E-0035 PP-OCR provenance is invalid")
        checked_boxes = [_bbox(box, "PP-OCR box") for box in boxes]
        source_row_ids = sample.get("source_row_ids")
        label_line_indices = sample.get("label_line_indices")
        if (
            not isinstance(source_row_ids, list)
            or not source_row_ids
            or not all(isinstance(value, str) and value for value in source_row_ids)
            or not isinstance(label_line_indices, list)
            or not label_line_indices
            or not all(_valid_int(value) for value in label_line_indices)
        ):
            raise E0037SourceStructureError("E-0035 source row provenance is invalid")
        page_record = page_records[page]
        rows.append(
            {
                "row_id": expected_id,
                "source_order": source_order,
                "page": page,
                "row_ordinal": row_ordinal,
                "raw_label": raw_label,
                "label_provenance": {
                    "reader": "E0035_FROZEN_PPOCR_TEXT_PROVENANCE_ONLY",
                    "source_row_ids": list(source_row_ids),
                    "label_line_indices": list(label_line_indices),
                    "ppocr_scores": list(scores),
                },
                "crop": {
                    "path": crop_relative.as_posix(),
                    "sha256": crop_record.sha256,
                    "size_bytes": crop_record.size_bytes,
                    "width": crop_width,
                    "height": crop_height,
                },
                "page_render": dict(page_record),
                "geometry": {
                    "label_union_bbox": _bbox(sample.get("label_union_bbox"), "label union bbox"),
                    "source_crop_bbox": _bbox(sample.get("source_crop_bbox"), "source crop bbox"),
                    "ppocr_boxes": checked_boxes,
                    "note_right_edge": sample.get("note_right_edge"),
                    "x_indentation_used": False,
                    "note_reference_used_as_schema_numbering": False,
                },
                "typography": typography,
                "typography_role": typography_role,
            }
        )
    if dict(page_ordinals) != _EXPECTED_ROWS_BY_PAGE:
        raise E0037SourceStructureError("E-0035 rows-by-page denominator drifted")
    _classify_row_roles(rows)
    return rows


def _recursive_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key).casefold())
            keys.extend(_recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_recursive_keys(child))
    return keys


def _validate_page_record(page_record: Any, expected_page: int) -> dict[str, Any]:
    if (
        not isinstance(page_record, dict)
        or set(page_record) != {"page", "row_count", "path", "sha256", "size_bytes", "verification"}
        or not _valid_int(page_record.get("page"))
        or page_record["page"] != expected_page
        or not _valid_int(page_record.get("row_count"))
        or page_record["row_count"] != _EXPECTED_ROWS_BY_PAGE[expected_page]
        or page_record.get("verification") != "TRANSITIVELY_HASH_BOUND_BY_E0035_MANIFEST_NOT_OPENED"
        or not _valid_sha256(page_record.get("sha256"))
        or not _valid_int(page_record.get("size_bytes"))
        or not 0 < page_record["size_bytes"] <= 64 * 1024 * 1024
    ):
        raise E0037SourceStructureError("Seal A page identity contract drifted")
    relative = _canonical_relative(page_record.get("path"))
    if relative.name != f"page-{expected_page:04d}.png":
        raise E0037SourceStructureError("Seal A page render path drifted")
    return {key: page_record[key] for key in ("path", "sha256", "size_bytes", "verification")}


def _validate_geometry(geometry: dict[str, Any]) -> int:
    label_bbox = _bbox(geometry.get("label_union_bbox"), "Seal A label union bbox")
    source_bbox = _bbox(geometry.get("source_crop_bbox"), "Seal A source crop bbox")
    raw_boxes = geometry.get("ppocr_boxes")
    if not isinstance(raw_boxes, list) or not raw_boxes:
        raise E0037SourceStructureError("Seal A PP-OCR boxes are invalid")
    boxes = [_bbox(box, "Seal A PP-OCR box") for box in raw_boxes]
    if not (
        source_bbox[0] <= label_bbox[0] < label_bbox[2] <= source_bbox[2]
        and source_bbox[1] <= label_bbox[1] < label_bbox[3] <= source_bbox[3]
        and all(
            label_bbox[0] <= box[0] < box[2] <= label_bbox[2]
            and label_bbox[1] <= box[1] < box[3] <= label_bbox[3]
            for box in boxes
        )
    ):
        raise E0037SourceStructureError("Seal A geometry containment drifted")
    note_right_edge = geometry.get("note_right_edge")
    if (
        type(note_right_edge) is not float
        or not math.isfinite(note_right_edge)
        or note_right_edge < label_bbox[2]
        or geometry.get("x_indentation_used") is not False
        or geometry.get("note_reference_used_as_schema_numbering") is not False
    ):
        raise E0037SourceStructureError("Seal A geometry authority drifted")
    return len(boxes)


def _validate_label_provenance(
    provenance: dict[str, Any], *, page: int, ppocr_box_count: int
) -> None:
    source_row_ids = provenance.get("source_row_ids")
    label_line_indices = provenance.get("label_line_indices")
    scores = provenance.get("ppocr_scores")
    if (
        provenance.get("reader") != "E0035_FROZEN_PPOCR_TEXT_PROVENANCE_ONLY"
        or not isinstance(source_row_ids, list)
        or not source_row_ids
        or not isinstance(label_line_indices, list)
        or not label_line_indices
        or not isinstance(scores, list)
        or len(scores) != ppocr_box_count
        or len(scores) != len(label_line_indices)
        or any(
            type(score) is not float or not math.isfinite(score) or not 0.0 <= score <= 1.0
            for score in scores
        )
        or any(not _valid_int(index) or index < 0 for index in label_line_indices)
        or label_line_indices != sorted(set(label_line_indices))
    ):
        raise E0037SourceStructureError("Seal A label provenance drifted")
    source_line_indices: list[int] = []
    for source_row_id in source_row_ids:
        prefix = f"page-{page:04d}:line-"
        if (
            not isinstance(source_row_id, str)
            or not source_row_id.startswith(prefix)
            or len(source_row_id) != len(prefix) + 4
            or not source_row_id[-4:].isdigit()
        ):
            raise E0037SourceStructureError("Seal A source-row provenance drifted")
        source_line_indices.append(int(source_row_id[-4:]))
    if source_line_indices != sorted(set(source_line_indices)) or not set(
        label_line_indices
    ).issubset(source_line_indices):
        raise E0037SourceStructureError("Seal A source-line provenance drifted")


def _validate_typography(
    typography: dict[str, Any], *, raw_label: str, crop: dict[str, Any]
) -> None:
    metrics = typography.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != _TYPOGRAPHY_METRIC_KEYS:
        raise E0037SourceStructureError("Seal A typography metric fields drifted")
    if not all(_valid_int(metrics.get(key)) for key in _TYPOGRAPHY_METRIC_KEYS):
        raise E0037SourceStructureError("Seal A typography metrics must be integers")
    trim = metrics["analysis_left_trim_pixels"]
    threshold = metrics["otsu_threshold"]
    ink = metrics["ink_pixel_count"]
    eroded = metrics["eroded_ink_pixel_count"]
    survival = metrics["erosion_survival_ppm"]
    upright = metrics["upright_projection_energy"]
    italic = metrics["best_italic_projection_energy"]
    italic_gain = metrics["italic_gain_ppm"]
    uppercase_ratio = metrics["uppercase_ratio_ppm"]
    maximum_ink = crop["height"] * (crop["width"] - trim)
    if (
        trim != 24
        or crop["width"] <= trim + 8
        or not 0 <= threshold <= 255
        or not 20 <= ink <= maximum_ink
        or not 0 <= eroded <= ink
        or survival != eroded * 1_000_000 // ink
        or not 0 < upright <= ink * ink
        or not 0 < italic <= ink * ink
        or italic_gain != italic * 1_000_000 // upright
        or uppercase_ratio != _case_ratio(raw_label)
        or not 0 <= uppercase_ratio <= 1_000_000
    ):
        raise E0037SourceStructureError("Seal A typography metric values drifted")
    expected_weight = "BOLD" if survival >= 480_000 else "REGULAR"
    expected_slant = "ITALIC" if italic_gain >= 1_005_000 else "UPRIGHT"
    expected_case = "UPPERCASE" if uppercase_ratio >= 800_000 else "MIXED"
    if (
        typography.get("font_weight") != expected_weight
        or typography.get("font_slant") != expected_slant
        or typography.get("case_role") != expected_case
    ):
        raise E0037SourceStructureError("Seal A derived typography roles drifted")


def validate_source_only_structure(payload: dict[str, Any]) -> None:
    """Validate Seal A without reopening inputs, then enforce its canonical identity.

    Internal checks can reproduce role and edge derivations from the recorded fields.
    Only the precommitted canonical SHA-256/size can prove those fields still represent
    the exact frozen manifest and crop pixels before a later phase opens schema data.
    """

    expected_keys = {
        "format_version",
        "experiment_id",
        "state",
        "source_only_contract",
        "inputs",
        "pages",
        "rows",
        "edges",
        "metrics",
        "gates",
        "authority",
        "claim_boundary",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise E0037SourceStructureError("Seal A top-level field set drifted")
    if (
        not _valid_int(payload.get("format_version"))
        or payload["format_version"] != 1
        or payload.get("experiment_id") != "E-0037"
        or payload.get("state") != SOURCE_STRUCTURE_STATE
        or not _same_json_type_and_value(payload.get("source_only_contract"), _SOURCE_ONLY_CONTRACT)
        or not _same_json_type_and_value(payload.get("authority"), _AUTHORITY)
    ):
        raise E0037SourceStructureError("Seal A identity or authority drifted")
    if payload.get("claim_boundary") != SOURCE_STRUCTURE_CLAIM_BOUNDARY:
        raise E0037SourceStructureError("Seal A claim boundary drifted")
    forbidden = _FORBIDDEN_PAYLOAD_KEYS.intersection(_recursive_keys(payload))
    if forbidden:
        raise E0037SourceStructureError(
            f"Seal A contains forbidden answer fields: {sorted(forbidden)}"
        )

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "e0035_seal",
        "e0035_crop_manifest",
        "crop_count",
        "crop_set_sha256",
    }:
        raise E0037SourceStructureError("Seal A input identity contract drifted")
    expected_seal_identity = {
        "path": E0035_SEAL_RELATIVE_PATH.as_posix(),
        "sha256": _E0035_SEAL_SHA256,
        "size_bytes": _E0035_SEAL_SIZE,
        "status": _EXPECTED_SEAL_STATUS,
    }
    expected_manifest_identity = {
        "path": _E0035_MANIFEST_PATH.as_posix(),
        "sha256": _E0035_MANIFEST_SHA256,
        "size_bytes": _E0035_MANIFEST_SIZE,
    }
    if (
        not _valid_int(inputs.get("crop_count"))
        or inputs["crop_count"] != _EXPECTED_ROW_COUNT
        or not _valid_sha256(inputs.get("crop_set_sha256"))
        or not _same_json_type_and_value(inputs.get("e0035_seal"), expected_seal_identity)
        or not _same_json_type_and_value(
            inputs.get("e0035_crop_manifest"), expected_manifest_identity
        )
    ):
        raise E0037SourceStructureError("Seal A frozen input identity drifted")

    pages = payload.get("pages")
    if not isinstance(pages, list) or len(pages) != len(_EXPECTED_ROWS_BY_PAGE):
        raise E0037SourceStructureError("Seal A page identity count drifted")
    page_identity_by_page = {
        page: _validate_page_record(page_record, page)
        for page, page_record in zip(sorted(_EXPECTED_ROWS_BY_PAGE), pages, strict=True)
    }

    rows = payload.get("rows")
    edges = payload.get("edges")
    if not isinstance(rows, list) or len(rows) != _EXPECTED_ROW_COUNT:
        raise E0037SourceStructureError("Seal A must contain exactly 64 rows")
    if not isinstance(edges, list):
        raise E0037SourceStructureError("Seal A edges are invalid")
    row_ids: set[str] = set()
    crop_hashes: set[str] = set()
    counts: Counter[int] = Counter()
    for source_order, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != _ROW_KEYS:
            raise E0037SourceStructureError("Seal A row must be an exact object")
        row_id = row.get("row_id")
        page = row.get("page")
        row_ordinal = row.get("row_ordinal")
        if (
            not isinstance(row_id, str)
            or row_id in row_ids
            or not _valid_int(row.get("source_order"))
            or row["source_order"] != source_order
            or not _valid_int(page)
            or page not in _EXPECTED_ROWS_BY_PAGE
            or not _valid_int(row_ordinal)
            or row_ordinal != counts[page]
            or row_id != f"page-{page:04d}-row-{row_ordinal:03d}-label"
        ):
            raise E0037SourceStructureError("Seal A row identity or order drifted")
        raw_label = row.get("raw_label")
        if (
            not isinstance(raw_label, str)
            or not raw_label
            or raw_label != raw_label.strip()
            or len(raw_label) > 4096
            or any(character in raw_label for character in ("\x00", "\r", "\n"))
            or row.get("row_role") not in _ROW_ROLES
            or row.get("typography_role") not in _TYPOGRAPHY_ROLES
            or row.get("child_set_complete") != "UNKNOWN"
            or not isinstance(row.get("row_role_candidates"), list)
            or not isinstance(row.get("structural_evidence"), list)
        ):
            raise E0037SourceStructureError("Seal A row enum or label contract drifted")
        label_provenance = row.get("label_provenance")
        crop = row.get("crop")
        page_render = row.get("page_render")
        geometry = row.get("geometry")
        typography = row.get("typography")
        if (
            not isinstance(label_provenance, dict)
            or set(label_provenance)
            != {"reader", "source_row_ids", "label_line_indices", "ppocr_scores"}
            or not isinstance(crop, dict)
            or set(crop) != {"path", "sha256", "size_bytes", "width", "height"}
            or not isinstance(page_render, dict)
            or set(page_render) != {"path", "sha256", "size_bytes", "verification"}
            or not isinstance(geometry, dict)
            or set(geometry)
            != {
                "label_union_bbox",
                "source_crop_bbox",
                "ppocr_boxes",
                "note_right_edge",
                "x_indentation_used",
                "note_reference_used_as_schema_numbering",
            }
            or not isinstance(typography, dict)
            or set(typography) != {"font_weight", "font_slant", "case_role", "metrics"}
        ):
            raise E0037SourceStructureError("Seal A nested row contract drifted")
        expected_crop_path = (_CROP_ROOT / f"{row_id}.png").as_posix()
        if (
            crop.get("path") != expected_crop_path
            or not _valid_sha256(crop.get("sha256"))
            or crop["sha256"] in crop_hashes
            or not _valid_int(crop.get("size_bytes"))
            or not 0 < crop["size_bytes"] <= 2 * 1024 * 1024
            or not _valid_int(crop.get("width"))
            or not 0 < crop["width"] <= 10_000
            or not _valid_int(crop.get("height"))
            or not 0 < crop["height"] <= 10_000
            or not _same_json_type_and_value(page_render, page_identity_by_page[page])
        ):
            raise E0037SourceStructureError("Seal A crop or page-render identity drifted")
        ppocr_box_count = _validate_geometry(geometry)
        _validate_label_provenance(
            label_provenance,
            page=page,
            ppocr_box_count=ppocr_box_count,
        )
        _validate_typography(typography, raw_label=raw_label, crop=crop)
        expected_typography_role = f"{typography['font_weight']}_{typography['font_slant']}"
        if row["typography_role"] != expected_typography_role:
            raise E0037SourceStructureError("Seal A composite typography role drifted")
        row_ids.add(row_id)
        crop_hashes.add(crop["sha256"])
        counts[page] += 1
    if dict(counts) != _EXPECTED_ROWS_BY_PAGE:
        raise E0037SourceStructureError("Seal A rows-by-page denominator drifted")

    crop_set_hash = hashlib.sha256()
    for row in rows:
        crop_set_hash.update(row["row_id"].encode("utf-8"))
        crop_set_hash.update(b"\0")
        crop_set_hash.update(row["crop"]["sha256"].encode("ascii"))
        crop_set_hash.update(b"\n")
    if inputs["crop_set_sha256"] != crop_set_hash.hexdigest():
        raise E0037SourceStructureError("Seal A crop-set aggregate SHA-256 drifted")

    derived_rows = copy.deepcopy(rows)
    _classify_row_roles(derived_rows)
    for row, derived in zip(rows, derived_rows, strict=True):
        for key in ("row_role", "row_role_candidates", "structural_evidence"):
            if not _same_json_type_and_value(row.get(key), derived[key]):
                raise E0037SourceStructureError("Seal A row-role derivation drifted")
    derived_edges = _assign_source_only_edges(derived_rows)
    for row, derived in zip(rows, derived_rows, strict=True):
        for key in ("physical_parent_row_id", "section_row_id", "child_set_complete"):
            if not _same_json_type_and_value(row.get(key), derived[key]):
                raise E0037SourceStructureError("Seal A structural-parent derivation drifted")
    if not _same_json_type_and_value(edges, derived_edges):
        raise E0037SourceStructureError("Seal A edge derivation or order drifted")

    role_counts = Counter(row["row_role"] for row in rows)
    typography_counts = Counter(row["typography_role"] for row in rows)
    expected_metrics = {
        "row_count": _EXPECTED_ROW_COUNT,
        "rows_by_page": {
            str(page): count for page, count in sorted(_EXPECTED_ROWS_BY_PAGE.items())
        },
        "row_role_counts": dict(sorted(role_counts.items())),
        "typography_role_counts": dict(sorted(typography_counts.items())),
        "physical_parent_edge_count": sum(
            edge["relation_type"] == "PHYSICAL_PARENT" for edge in derived_edges
        ),
        "section_member_edge_count": sum(
            edge["relation_type"] == "SECTION_MEMBER" for edge in derived_edges
        ),
        "unknown_child_set_count": _EXPECTED_ROW_COUNT,
    }
    if not _same_json_type_and_value(payload.get("metrics"), expected_metrics):
        raise E0037SourceStructureError("Seal A derived metrics drifted")
    if not _same_json_type_and_value(payload.get("gates"), _GATES):
        raise E0037SourceStructureError("Seal A exact gate contract drifted")

    # This final binding rejects internally consistent substitutions that cannot be
    # disproved without reopening the frozen E-0035 manifest and registered pixels.
    identity = canonical_payload_identity(payload)
    if (
        identity["sha256"] != SOURCE_STRUCTURE_CANONICAL_SHA256
        or identity["size_bytes"] != SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES
    ):
        raise E0037SourceStructureError("Seal A canonical payload identity drifted")


def assemble_source_only_structure(
    project_root: Path,
    *,
    e0035_seal_path: Path = E0035_SEAL_RELATIVE_PATH,
) -> dict[str, Any]:
    """Assemble E-0037 Seal A from E-0035 pixels and geometry only.

    The function has an exact-path input firewall. It never opens schema/workbook,
    review, historical, numeric, period/unit/scope, or prior mapping artifacts.
    """

    root = _project_root(project_root)
    seal_relative = _canonical_relative(
        e0035_seal_path,
        expected=PurePosixPath(E0035_SEAL_RELATIVE_PATH.as_posix()),
    )
    seal_record = _stable_read(
        root,
        seal_relative,
        expected_sha256=_E0035_SEAL_SHA256,
        expected_size=_E0035_SEAL_SIZE,
        maximum_size=128 * 1024,
    )
    seal = _json_object(seal_record, "E-0035 seal")
    manifest_identity = seal.get("crop_manifest")
    if (
        seal.get("experiment_id") != "E-0035"
        or seal.get("status") != _EXPECTED_SEAL_STATUS
        or seal.get("capture_git_dirty") is not False
        or not isinstance(manifest_identity, dict)
        or manifest_identity.get("path") != _E0035_MANIFEST_PATH.as_posix()
        or manifest_identity.get("sha256") != _E0035_MANIFEST_SHA256
        or manifest_identity.get("size_bytes") != _E0035_MANIFEST_SIZE
    ):
        raise E0037SourceStructureError("E-0035 seal identity or state drifted")
    manifest_record = _stable_read(
        root,
        _E0035_MANIFEST_PATH,
        expected_sha256=_E0035_MANIFEST_SHA256,
        expected_size=_E0035_MANIFEST_SIZE,
        maximum_size=512 * 1024,
    )
    manifest = _json_object(manifest_record, "E-0035 crop manifest")
    if (
        manifest.get("experiment_id") != "E-0035"
        or manifest.get("sample_count") != _EXPECTED_ROW_COUNT
        or manifest.get("reference_text_available_to_decoder") is not False
        or manifest.get("authority", {}).get("source_render_is_pixel_authority") is not True
        or manifest.get("authority", {}).get("template_or_history_is_available_to_crop_builder")
        is not False
    ):
        raise E0037SourceStructureError("E-0035 manifest authority drifted")

    page_records: dict[int, dict[str, Any]] = {}
    page_outputs: list[dict[str, Any]] = []
    for page in sorted(_EXPECTED_ROWS_BY_PAGE):
        registered = _page_record(manifest.get("page_sources"), page)
        render_relative = _canonical_relative(str(registered.get("path", "")))
        expected_sha256 = registered.get("sha256")
        expected_size = registered.get("size_bytes")
        if (
            not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or not _valid_int(expected_size)
        ):
            raise E0037SourceStructureError("E-0035 render identity is invalid")
        page_record = {
            "path": render_relative.as_posix(),
            "sha256": expected_sha256,
            "size_bytes": expected_size,
            "verification": "TRANSITIVELY_HASH_BOUND_BY_E0035_MANIFEST_NOT_OPENED",
        }
        page_records[page] = page_record
        page_outputs.append(
            {"page": page, "row_count": _EXPECTED_ROWS_BY_PAGE[page], **page_record}
        )

    rows = _assemble_rows(root, manifest, page_records)
    edges = _assign_source_only_edges(rows)
    role_counts = Counter(row["row_role"] for row in rows)
    typography_counts = Counter(row["typography_role"] for row in rows)
    crop_set_hash = hashlib.sha256()
    for row in rows:
        crop_set_hash.update(row["row_id"].encode("utf-8"))
        crop_set_hash.update(b"\0")
        crop_set_hash.update(row["crop"]["sha256"].encode("ascii"))
        crop_set_hash.update(b"\n")
    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0037",
        "state": SOURCE_STRUCTURE_STATE,
        "source_only_contract": copy.deepcopy(_SOURCE_ONLY_CONTRACT),
        "inputs": {
            "e0035_seal": {
                "path": seal_relative.as_posix(),
                "sha256": seal_record.sha256,
                "size_bytes": seal_record.size_bytes,
                "status": _EXPECTED_SEAL_STATUS,
            },
            "e0035_crop_manifest": {
                "path": _E0035_MANIFEST_PATH.as_posix(),
                "sha256": manifest_record.sha256,
                "size_bytes": manifest_record.size_bytes,
            },
            "crop_count": len(rows),
            "crop_set_sha256": crop_set_hash.hexdigest(),
        },
        "pages": page_outputs,
        "rows": rows,
        "edges": edges,
        "metrics": {
            "row_count": len(rows),
            "rows_by_page": {
                str(page): count for page, count in sorted(_EXPECTED_ROWS_BY_PAGE.items())
            },
            "row_role_counts": dict(sorted(role_counts.items())),
            "typography_role_counts": dict(sorted(typography_counts.items())),
            "physical_parent_edge_count": sum(
                edge["relation_type"] == "PHYSICAL_PARENT" for edge in edges
            ),
            "section_member_edge_count": sum(
                edge["relation_type"] == "SECTION_MEMBER" for edge in edges
            ),
            "unknown_child_set_count": sum(row["child_set_complete"] == "UNKNOWN" for row in rows),
        },
        "gates": dict(_GATES),
        "authority": dict(_AUTHORITY),
        "claim_boundary": SOURCE_STRUCTURE_CLAIM_BOUNDARY,
    }
    validate_source_only_structure(payload)
    return payload


def load_source_only_structure(
    project_root: Path,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
    path: Path = SOURCE_STRUCTURE_RELATIVE_PATH,
) -> dict[str, Any]:
    """Load a byte-bound Seal A through the no-symlink/stable-read boundary."""

    root = _project_root(project_root)
    if not _valid_sha256(expected_sha256) or not _valid_int(expected_size_bytes):
        raise E0037SourceStructureError("Seal A expected file identity is invalid")
    if not 0 < expected_size_bytes <= 4 * 1024 * 1024:
        raise E0037SourceStructureError("Seal A expected file size is invalid")
    relative = _canonical_relative(
        path,
        expected=PurePosixPath(SOURCE_STRUCTURE_RELATIVE_PATH.as_posix()),
    )
    record = _stable_read(
        root,
        relative,
        expected_sha256=expected_sha256,
        expected_size=expected_size_bytes,
        maximum_size=4 * 1024 * 1024,
    )
    payload = _json_object(record, "E-0037 source-only structure")
    validate_source_only_structure(payload)
    return payload


# Explicit integration alias: capture/orchestration code may use the experiment name.
assemble_e0037_source_structure = assemble_source_only_structure
