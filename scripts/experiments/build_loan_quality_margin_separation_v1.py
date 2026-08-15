"""Normalize margin/advance lending outside the five loan-quality grades."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0067B-loan-quality-margin-separation-project-owner-v1.json")
QUALITY_RESULT_PATH = Path(
    "docs/experiments/E-0052-loan-quality-8bank-codex-verified-mapping-v1.json"
)
QUALITY_RESULT_SHA256 = "6e4c8ef7855bf8f053a0d95c54f7d6e026817eb73a54e671508d5bfd63ce7b2c"
QUALITY_RESULT_ID = (
    "lq8bcv1:result:111361a394cf8fc1224b0c6e4f43e47ee68d2f831c7cc6a74a7a251908101377"
)
CONTEXT_PATH = Path("config/schemas/loan-quality-margin-context-v1.json")
SCHEMA_APPEND_PATH = Path("data/registered/schema_append_1944.json")
SCHEMA_APPEND_SHA256 = "db7bd13e4dbc9cbda28eadadc381bbb0b3d7085eb913eed171a2e512a3334ca6"

FORMAT_VERSION = "LOAN_QUALITY_MARGIN_SEPARATION_PROJECT_OWNER_V1"
CLAIM_BOUNDARY = (
    "BOUNDED_EIGHT_REPORT_LOAN_QUALITY_NORMALIZATION_REUSES_REGISTERED_1944_"
    "UNDER_746_SEPARATES_STANDALONE_OR_747_INCLUDED_MARGIN_WITH_EXACT_"
    "ACCOUNTING_NO_OTHER_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_BANK_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_CORE_IDS = (747, 748, 749, 750, 751)
_CORE_NAMES = {
    747: "+ Nhóm 1: Nợ đủ tiêu chuẩn",
    748: "+ Nhóm 2: Nợ cần chú ý",
    749: "+ Nhóm 3: Nợ dưới tiêu chuẩn",
    750: "+ Nhóm 4: Nợ nghi ngờ",
    751: "+ Nhóm 5: Nợ có khả năng mất vốn",
}
_STANDALONE_ID = 1944
_STANDALONE_NAME = "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
_INCLUDED_ID = 5746
_INCLUDED_NAME = "Trong đó: Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
_AUTHORITY = {
    "bank_page_or_filename_used_as_mapping_rule": False,
    "bounded_schema_context_overlay_authority": True,
    "canonical_or_export_authority": False,
    "double_count_permitted": False,
    "numeric_authority_requires_prior_pixel_and_accounting_replay": True,
    "persisted_artifact_self_authenticating": False,
    "project_owner_margin_separation_authority": True,
    "public_exact_replay_required": True,
    "raw_text_similarity_mapping_authority": False,
}


class LoanQualityMarginSeparationV1Error(ValueError):
    """A pinned input, bounded context, or accounting normalization drifted."""


def _error(message: str) -> LoanQualityMarginSeparationV1Error:
    return LoanQualityMarginSeparationV1Error(message)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise _error(f"non-finite JSON constant in {label}: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"invalid UTF-8 JSON: {label}") from exc
    if type(value) is not dict:
        raise _error(f"JSON root must be one object: {label}")
    return value


def _stable_bytes(relative: Path) -> bytes:
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("fixed loan-quality input path escaped project root")
    path = PROJECT_ROOT / relative
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise _error(f"fixed input is not one single-link regular file: {relative}")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or after.st_nlink != 1:
        raise _error(f"fixed input changed during read: {relative}")
    return b"".join(chunks)


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise _error(f"{label} must be one nonempty string")
    return value


def _accentless(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return " ".join(
        "".join(char for char in decomposed if unicodedata.category(char) != "Mn").split()
    )


def _is_margin_surface(value: Any) -> bool:
    normalized = _accentless(_text(value, "margin source label"))
    return (
        "cho vay" in normalized
        and ("ky quy" in normalized or "margin" in normalized)
        and "ung truoc" in normalized
    )


def _integer(value: Any, label: str) -> int:
    raw = _text(value, label).strip()
    if raw in {"-", "–", "—"}:
        return 0
    normalized = raw.replace(".", "").replace(",", "")
    if not normalized.isdigit():
        raise _error(f"{label} is not one visible grouped integer")
    return int(normalized)


def _mapping_values(mapping: dict[str, Any]) -> tuple[list[int], list[dict[str, Any]]]:
    values = mapping.get("values")
    if type(values) is not list or len(values) != 2:
        raise _error("quality mapping does not contain exactly two period values")
    parsed: list[int] = []
    evidence: list[dict[str, Any]] = []
    for axis_index, raw in enumerate(values):
        if type(raw) is not dict or raw.get("axis_index") != axis_index:
            raise _error("quality mapping axis order drifted")
        transcription = _text(
            raw.get("independent_pixel_transcription"), "quality pixel transcription"
        )
        parsed.append(_integer(transcription, "quality pixel transcription"))
        evidence.append(
            {
                "axis_index": axis_index,
                "independent_pixel_transcription": transcription,
                "source_line_index": raw.get("source_line_index"),
            }
        )
    return parsed, evidence


def _outside_values(row: dict[str, Any]) -> tuple[list[int], list[dict[str, Any]]]:
    values = row.get("independent_pixel_values")
    if type(values) is not list or len(values) != 2:
        raise _error("standalone margin row does not contain two pixel values")
    parsed = [_integer(value, "standalone margin pixel value") for value in values]
    return parsed, [
        {
            "axis_index": axis_index,
            "independent_pixel_transcription": value,
            "source_line_index": None,
        }
        for axis_index, value in enumerate(values)
    ]


def _load_context() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable_bytes(CONTEXT_PATH)
    value = _strict_json(payload, CONTEXT_PATH.as_posix())
    expected_fields = {
        "authority",
        "context_id",
        "family",
        "format_version",
        "included_source_disclosure",
        "normalization_policy",
        "standalone_item",
        "state",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise _error("loan-quality margin context fields drifted")
    if (
        value["format_version"] != "LOAN_QUALITY_MARGIN_CONTEXT_V1"
        or value["state"] != "PROJECT_OWNER_ADJUDICATED_BOUNDED_SCHEMA_CONTEXT"
        or not same_typed_json_v1(
            value["family"],
            {"canonical_name": "Phân tích chất lượng nợ cho vay", "report_norm_id": 746},
        )
        or value["standalone_item"].get("report_norm_id") != _STANDALONE_ID
        or value["standalone_item"].get("canonical_name") != _STANDALONE_NAME
        or value["standalone_item"].get("parent_report_norm_id") != 746
        or value["standalone_item"].get("hierarchy_level") != 2
        or value["standalone_item"].get("mapping_eligible_in_this_bounded_context") is not True
        or value["standalone_item"].get("template_identity_reused") is not True
        or value["included_source_disclosure"].get("report_norm_id") != _INCLUDED_ID
        or value["included_source_disclosure"].get("canonical_name") != _INCLUDED_NAME
        or value["included_source_disclosure"].get("parent_report_norm_id") != 747
        or value["included_source_disclosure"].get("mapping_output_authority") is not False
        or not same_typed_json_v1(
            value["normalization_policy"],
            {
                "double_count_permitted": False,
                "included_in_747": "SUBTRACT_EXACT_5746_VALUE_FROM_747_AND_EMIT_1944",
                "standalone_after_five_grades": "KEEP_747_UNCHANGED_AND_EMIT_1944",
                "unobserved": "DO_NOT_SYNTHESIZE_1944",
            },
        )
    ):
        raise _error("loan-quality margin context semantics drifted")
    material = canonical_clone_v1(value)
    context_id = material.pop("context_id")
    if context_id != "lqmc:v1:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality margin context identity drifted")
    return value, {
        "context_id": context_id,
        "path": CONTEXT_PATH.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    quality_payload = _stable_bytes(QUALITY_RESULT_PATH)
    if hashlib.sha256(quality_payload).hexdigest() != QUALITY_RESULT_SHA256:
        raise _error("pinned E-0052 result bytes drifted")
    quality = _strict_json(quality_payload, QUALITY_RESULT_PATH.as_posix())
    if quality.get("result_id") != QUALITY_RESULT_ID:
        raise _error("pinned E-0052 result identity drifted")

    append_payload = _stable_bytes(SCHEMA_APPEND_PATH)
    if hashlib.sha256(append_payload).hexdigest() != SCHEMA_APPEND_SHA256:
        raise _error("registered ReportNormId 1944 append bytes drifted")
    append = _strict_json(append_payload, SCHEMA_APPEND_PATH.as_posix())
    item = append.get("appended_item")
    preservation = append.get("preservation")
    if (
        append.get("status") != "APPLIED_AND_VERIFIED"
        or type(item) is not dict
        or item.get("schema_id") != _STANDALONE_ID
        or item.get("canonical_name") != _STANDALONE_NAME
        or item.get("statement_type") != "TM"
        or type(preservation) is not dict
        or preservation.get("hierarchy_parent_status") != "NOT_INFERRED_WITHOUT_SOURCE_AUTHORITY"
    ):
        raise _error("registered ReportNormId 1944 identity drifted")
    return (
        quality,
        {
            "path": QUALITY_RESULT_PATH.as_posix(),
            "result_id": QUALITY_RESULT_ID,
            "sha256": QUALITY_RESULT_SHA256,
            "size_bytes": len(quality_payload),
        },
        {
            "path": SCHEMA_APPEND_PATH.as_posix(),
            "sha256": SCHEMA_APPEND_SHA256,
            "size_bytes": len(append_payload),
        },
    )


def _one_mapping(trial: dict[str, Any], report_norm_id: int) -> dict[str, Any]:
    mappings = trial.get("verified_mappings")
    if type(mappings) is not list:
        raise _error("E-0052 verified mapping list drifted")
    matches = [mapping for mapping in mappings if mapping.get("report_norm_id") == report_norm_id]
    if len(matches) != 1:
        raise _error(f"E-0052 does not contain one mapping for {report_norm_id}")
    return matches[0]


def _normalized_mapping(
    mapping: dict[str, Any], *, adjustment: list[int] | None = None
) -> tuple[dict[str, Any], list[int]]:
    report_norm_id = mapping.get("report_norm_id")
    if (
        report_norm_id not in _CORE_IDS
        or mapping.get("canonical_name") != _CORE_NAMES[report_norm_id]
    ):
        raise _error("E-0052 core quality schema binding drifted")
    values, evidence = _mapping_values(mapping)
    adjustments = [0, 0] if adjustment is None else adjustment
    normalized = [value - adjustments[index] for index, value in enumerate(values)]
    if any(value < 0 for value in normalized):
        raise _error("margin separation made the standard-grade value negative")
    return {
        "canonical_name": mapping["canonical_name"],
        "report_norm_id": report_norm_id,
        "source_status": mapping.get("status"),
        "status": "VERIFIED_BY_CODEX_NORMALIZED",
        "values": [
            {
                **evidence[index],
                "normalization_adjustment": -adjustments[index],
                "normalized_value": normalized[index],
                "source_reported_value": values[index],
            }
            for index in range(2)
        ],
    }, normalized


def _standalone_mapping(
    *, label: str, values: list[int], evidence: list[dict[str, Any]], source_role: str
) -> dict[str, Any]:
    return {
        "canonical_name": _STANDALONE_NAME,
        "independent_pixel_label": label,
        "parent_report_norm_id": 746,
        "report_norm_id": _STANDALONE_ID,
        "source_role": source_role,
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
        "values": [
            {
                **evidence[index],
                "normalized_value": values[index],
                "source_reported_value": values[index],
            }
            for index in range(2)
        ],
    }


def _trial(trial: dict[str, Any]) -> dict[str, Any]:
    if trial.get("status") != "VERIFIED_BY_CODEX":
        raise _error("E-0052 trial is no longer verified")
    code = _text(trial.get("bank_provenance"), "bank provenance")
    core_source = [_one_mapping(trial, report_norm_id) for report_norm_id in _CORE_IDS]
    source_totals = trial.get("source_only_total", {}).get("values")
    if type(source_totals) is not list or len(source_totals) != 2:
        raise _error("E-0052 source total denominator drifted")
    total_values = [
        _integer(value.get("independent_pixel_transcription"), "quality source total")
        for value in source_totals
    ]

    outside_rows = trial.get("accounting_scope_populations")
    if type(outside_rows) is not list:
        raise _error("E-0052 outside-core population list drifted")
    outside_margin = [
        row for row in outside_rows if _is_margin_surface(row.get("independent_pixel_label"))
    ]
    included = [
        mapping
        for mapping in trial["verified_mappings"]
        if mapping.get("report_norm_id") == _INCLUDED_ID
    ]
    if len(outside_margin) > 1 or len(included) > 1 or (outside_margin and included):
        raise _error("loan-quality margin presentation is ambiguous")

    margin_mapping: dict[str, Any] | None = None
    source_bridge: dict[str, Any] | None = None
    adjustment = [0, 0]
    if outside_margin:
        row = outside_margin[0]
        margin_values, margin_evidence = _outside_values(row)
        mode = "STANDALONE_AFTER_FIVE_GRADES"
        margin_mapping = _standalone_mapping(
            label=_text(row.get("independent_pixel_label"), "standalone margin label"),
            values=margin_values,
            evidence=margin_evidence,
            source_role="STANDALONE_SOURCE_ROW",
        )
    elif included:
        disclosure = included[0]
        if (
            disclosure.get("canonical_name") != _INCLUDED_NAME
            or disclosure.get("role") != "STANDARD_INCLUDED_DISCLOSURE"
        ):
            raise _error("included 5746 source disclosure semantics drifted")
        margin_values, margin_evidence = _mapping_values(disclosure)
        adjustment = margin_values
        mode = "INCLUDED_IN_747_VIA_5746"
        label = _text(disclosure.get("independent_pixel_label"), "included margin label")
        margin_mapping = _standalone_mapping(
            label=label,
            values=margin_values,
            evidence=margin_evidence,
            source_role="RECLASSIFIED_FROM_NONADDITIVE_5746_DISCLOSURE",
        )
        source_bridge = {
            "canonical_name": _INCLUDED_NAME,
            "mapping_output_authority": False,
            "parent_report_norm_id": 747,
            "report_norm_id": _INCLUDED_ID,
            "status": "VERIFIED_SOURCE_PRESENTATION_BRIDGE_NOT_AN_ADDITIONAL_OUTPUT",
            "values": margin_values,
        }
    else:
        margin_values = [0, 0]
        mode = "NOT_OBSERVED_DO_NOT_SYNTHESIZE"

    normalized_mappings: list[dict[str, Any]] = []
    normalized_core_values: list[list[int]] = []
    for mapping in core_source:
        normalized, values = _normalized_mapping(
            mapping,
            adjustment=adjustment if mapping.get("report_norm_id") == 747 else None,
        )
        normalized_mappings.append(normalized)
        normalized_core_values.append(values)
    if margin_mapping is not None:
        normalized_mappings.append(margin_mapping)

    equations: list[dict[str, Any]] = []
    for axis_index in range(2):
        addends = [values[axis_index] for values in normalized_core_values]
        if margin_mapping is not None:
            addends.append(margin_values[axis_index])
        if sum(addends) != total_values[axis_index]:
            raise _error("normalized quality rows do not close to the source family total")
        equations.append(
            {
                "addend_report_norm_ids": [
                    *_CORE_IDS,
                    *([] if margin_mapping is None else [_STANDALONE_ID]),
                ],
                "addends": addends,
                "axis_index": axis_index,
                "computed_total": sum(addends),
                "equation_role": "NORMALIZED_QUALITY_ROWS_EQUAL_SOURCE_TOTAL",
                "source_total": total_values[axis_index],
                "status": "CORROBORATED",
            }
        )
        if source_bridge is not None:
            original_standard, _ = _mapping_values(core_source[0])
            adjusted_standard = normalized_core_values[0][axis_index]
            if adjusted_standard + margin_values[axis_index] != original_standard[axis_index]:
                raise _error("adjusted 747 plus standalone margin does not equal reported 747")
            equations.append(
                {
                    "adjusted_747": adjusted_standard,
                    "axis_index": axis_index,
                    "equation_role": "ADJUSTED_747_PLUS_1944_EQUALS_SOURCE_747",
                    "margin_1944": margin_values[axis_index],
                    "source_747": original_standard[axis_index],
                    "status": "CORROBORATED",
                }
            )

    return {
        "bank_provenance": code,
        "normalization_equations": equations,
        "normalized_mappings": normalized_mappings,
        "physical_page": trial.get("physical_page"),
        "presentation_mode": mode,
        "source_5746_bridge": source_bridge,
        "source_family_total": total_values,
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
    }


def build_live_loan_quality_margin_separation_v1() -> dict[str, Any]:
    """Rebuild the bounded normalized quality view without bank-specific routing."""

    quality, quality_ref, append_ref = _load_inputs()
    context, context_ref = _load_context()
    trials = quality.get("trials")
    if type(trials) is not list or [trial.get("bank_provenance") for trial in trials] != list(
        _BANK_ORDER
    ):
        raise _error("E-0052 eight-bank denominator or order drifted")
    normalized_trials = [_trial(trial) for trial in trials]
    modes = [trial["presentation_mode"] for trial in normalized_trials]
    if modes.count("STANDALONE_AFTER_FIVE_GRADES") != 2:
        raise _error("standalone margin presentation denominator drifted")
    if modes.count("INCLUDED_IN_747_VIA_5746") != 1:
        raise _error("included-in-standard margin presentation denominator drifted")
    if modes.count("NOT_OBSERVED_DO_NOT_SYNTHESIZE") != 5:
        raise _error("unobserved margin presentation denominator drifted")

    equation_count = sum(len(trial["normalization_equations"]) for trial in normalized_trials)
    mapping_count = sum(len(trial["normalized_mappings"]) for trial in normalized_trials)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "loan_quality_result": quality_ref,
            "registered_schema_append_1944": append_ref,
            "schema_context": context_ref,
        },
        "metrics": {
            "accounting_equation_count": equation_count,
            "adjusted_standard_grade_bank_count": modes.count("INCLUDED_IN_747_VIA_5746"),
            "document_count": len(normalized_trials),
            "double_count_count": 0,
            "normalized_mapping_count": mapping_count,
            "source_5746_bridge_count": modes.count("INCLUDED_IN_747_VIA_5746"),
            "standalone_margin_mapping_count": sum(
                any(
                    mapping["report_norm_id"] == _STANDALONE_ID
                    for mapping in trial["normalized_mappings"]
                )
                for trial in normalized_trials
            ),
            "unobserved_margin_bank_count": modes.count("NOT_OBSERVED_DO_NOT_SYNTHESIZE"),
            "visible_normalized_period_cell_count": mapping_count * 2,
        },
        "schema_context": canonical_clone_v1(context),
        "state": "LOAN_QUALITY_MARGIN_SEPARATION_VERIFIED",
        "trials": normalized_trials,
    }
    return _validate(
        {**material, "result_id": "e0067b:result:" + canonical_json_sha256_v1(material)}
    )


def _validate(value: Any) -> dict[str, Any]:
    expected_fields = {
        "authority",
        "claim_boundary",
        "format_version",
        "input_refs",
        "metrics",
        "result_id",
        "schema_context",
        "state",
        "trials",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise _error("loan-quality margin result fields drifted")
    expected_metrics = {
        "accounting_equation_count": 18,
        "adjusted_standard_grade_bank_count": 1,
        "document_count": 8,
        "double_count_count": 0,
        "normalized_mapping_count": 43,
        "source_5746_bridge_count": 1,
        "standalone_margin_mapping_count": 3,
        "unobserved_margin_bank_count": 5,
        "visible_normalized_period_cell_count": 86,
    }
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "LOAN_QUALITY_MARGIN_SEPARATION_VERIFIED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or not same_typed_json_v1(value["metrics"], expected_metrics)
        or type(value["trials"]) is not list
        or [trial.get("bank_provenance") for trial in value["trials"]] != list(_BANK_ORDER)
    ):
        raise _error("loan-quality margin result identity or metrics drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "e0067b:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality margin result content identity drifted")
    return canonical_clone_v1(value)


def validate_loan_quality_margin_separation_replay_v1(value: Any) -> dict[str, Any]:
    """Exact-rebuild a persisted normalized result from registered inputs."""

    persisted = _validate(value)
    rebuilt = build_live_loan_quality_margin_separation_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-quality margin result does not exact-replay")
    return rebuilt


def main() -> None:
    result = build_live_loan_quality_margin_separation_v1()
    OUTPUT_PATH.write_bytes(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
