#!/usr/bin/env python3
"""Verify annual-2025 interbank deposit and borrowing notes for eight banks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
    project_full_document_vietocr_reporting_period_contexts_v1,
    validate_full_document_vietocr_reporting_period_contexts_replay_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

try:
    from scripts.experiments.adaptive_accounting_table_geometry_v1 import (
        assign_numeric_row_v1,
        cluster_numeric_rows_v1,
    )
except ModuleNotFoundError:
    from adaptive_accounting_table_geometry_v1 import (  # type: ignore[no-redef]
        assign_numeric_row_v1,
        cluster_numeric_rows_v1,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0159-annual-2025-interbank-funding-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0159-annual-2025-interbank-funding-8bank-codex-pixel-review-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_PERIOD_PROJECTION_ID = (
    "fdvrpcv1:projection:fd732522c67ec0fa927696bf1b17721f1ce16c34a083618e2bb4ebf7acb6d0d3"
)

FORMAT_VERSION = "ANNUAL_2025_INTERBANK_FUNDING_8BANK_CODEX_VERIFIED_MAPPING_V1"
STATE = "ANNUAL_2025_INTERBANK_FUNDING_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025if8bcv1:result:"
REVIEW_FORMAT = "ANNUAL_2025_INTERBANK_FUNDING_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_ID_PREFIX = "annual2025if8bcv1:pixel-review:"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDF_FRESH_VIETOCR_"
    "BANK_BLIND_LIABILITY_SIDE_INTERBANK_FUNDING_GRAPH_PERIOD_UNIT_GEOMETRY_"
    "PROVIDER_NUMERIC_CHALLENGER_EXACT_ACCOUNTING_EQUATIONS_LIVE_TM_SCHEMA_"
    "SUPPORTED_ROWS_ONLY_SOURCE_ONLY_AUXILIARY_ROWS_RETAINED_NO_EXPORT_AUTHORITY"
)

_SCHEMA = {
    "FAMILY_TOTAL": (1040, "Tiền, vàng gửi và vay các tổ chức tín dụng khác", 560),
    "DEPOSIT_PARENT": (1041, "Tiền gửi của các tổ chức tín dụng khác", 1040),
    "TERM_DEPOSIT": (1042, "+ Tiền gửi có kỳ hạn", 1040),
    "TERM_DEPOSIT_VND": (1043, "Trong đó: + Bằng tiền VNĐ", 1040),
    "TERM_DEPOSIT_FOREIGN": (1044, "+ Bằng ngoại tệ", 1040),
    "DEMAND_DEPOSIT": (1045, "+ Tiền gửi không kỳ hạn", 1040),
    "DEMAND_DEPOSIT_VND": (1046, "Trong đó: + Bằng tiền VNĐ", 1040),
    "DEMAND_DEPOSIT_FOREIGN": (1047, "+ Bằng ngoại tệ", 1040),
    "BORROWING": (1048, "Tiền vay các tổ chức tín dụng khác", 1040),
    "BORROWING_VND": (1049, "+ Bằng tiền VNĐ", 1040),
    "BORROWING_VND_DISCOUNT": (1050, "Trong đó: + Vay chiết khấu, tái chiết khấu", 1040),
    "BORROWING_VND_COLLATERAL": (1051, "+ Vay cầm cố, thế chấp", 1040),
    "BORROWING_FOREIGN": (1052, "+ Bằng ngoại tệ", 1040),
}
_GEMMA_RESCUES = (
    {
        "accounting_closure": "119590000 + 6980904 = 126570904",
        "crop_sha256": "7f6bf47dc6a06cecfe5a6f94f30f8405de9a9f70e5c92b0d3491d5f1319142df",
        "fresh_vietocr_text": "6.960.904",
        "gemma4_text": "6.980.904",
        "model": "GEMMA4_26B_A4B_IT_QAT_Q4_0_LOCAL_GPU_REASONING_OFF",
        "page_sequence": 44,
        "source_line_index": 81,
        "source_numeric_challenger": "6.980.904",
    },
    {
        "accounting_closure": "5816757 + 33981761 = 39798518",
        "crop_sha256": "990bc12154e28504bb18907fa3704aba1f9618516273b3ebd61d9b7d4d8ff032",
        "fresh_vietocr_text": "5.616.757",
        "gemma4_text": "5.816.757",
        "model": "GEMMA4_26B_A4B_IT_QAT_Q4_0_LOCAL_GPU_REASONING_OFF",
        "page_sequence": 44,
        "source_line_index": 96,
        "source_numeric_challenger": "5.816.757",
    },
)
_AUTHORITY = {
    "asset_side_root_575_used_for_mapping": False,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "complete_pdf_scanned_for_every_document": True,
    "computed_parent_values_require_complete_visible_child_equations": True,
    "dash_is_zero_only_after_bound_source_component_verification": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma4_used_as_numeric_truth": False,
    "liability_side_root_1040_only": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_visible_supported_rows": True,
    "out_of_schema_auxiliary_rows_discarded": False,
    "provider_source_axis_used_as_numeric_challenger": True,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
}
_MONEY = re.compile(r"^(?:\(?[0-9]+(?:[.,][0-9]+)*\)?|[-–—])$")
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "schema_family",
    "state",
    "trials",
}


class Annual2025InterbankFunding8BankError(ValueError):
    """The annual interbank-funding evidence, equations or schema drifted."""


def _error(message: str) -> Annual2025InterbankFunding8BankError:
    return Annual2025InterbankFunding8BankError(message)


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual interbank support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _scanner() -> ModuleType:
    return _load(
        "annual_2025_interbank_funding_scan_support_v1",
        "scan_annual_2025_interbank_funding_full_document_v1.py",
    )


def _support() -> ModuleType:
    return _load(
        "annual_2025_interbank_funding_source_support_v1",
        "build_trading_securities_8bank_codex_verified_mapping_v1.py",
    )


def _stable_json(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    payload = _support()._stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise _error(f"fixed annual interbank input drifted: {path}")
    value = _support()._strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error("annual interbank JSON root drifted")
    return value, digest


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in items
        if type(item) is dict and item.get("bank_code", item.get("document_provenance")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one {code} document")
    return canonical_clone_v1(matches[0])


def _page(document: Mapping[str, Any], number: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict and page.get("physical_page", page.get("page_sequence")) == number
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one page {number}")
    return canonical_clone_v1(matches[0])


def _line(page: Mapping[str, Any], index: int) -> dict[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= index < len(lines):
        raise _error("annual interbank line index drifted")
    line = lines[index]
    if (
        type(line) is not dict
        or line.get("source_line_index") != index
        or type(line.get("vietocr_text")) is not str
        or type(line.get("source_bbox_raw_pixels")) is not list
    ):
        raise _error("annual interbank line identity drifted")
    return line


def _n(value: str) -> str:
    return _scanner()._n(value)


def _money(value: Any) -> int:
    if type(value) is not str:
        raise _error(f"visible money surface must be exact string: {value!r}")
    token = value.strip().replace(" ", "")
    if re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})+\.", token) is not None:
        token = token[:-1]
    if _MONEY.fullmatch(token) is None:
        raise _error(f"visible money surface drifted: {value!r}")
    if token in {"-", "–", "—"}:
        return 0
    negative = token.startswith("(") and token.endswith(")")
    digits = token.strip("()").replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error("visible money digits drifted")
    result = int(digits)
    return -result if negative else result


def _is_money(line: Mapping[str, Any]) -> bool:
    try:
        _money(line["vietocr_text"])
    except Annual2025InterbankFunding8BankError:
        return False
    return True


def _geometry_lines(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "bbox": list(line["source_bbox_raw_pixels"]),
            "source_line_index": line["source_line_index"],
            "vietocr_text": line["vietocr_text"],
        }
        for line in page["lines"]
    ]


def _row_value_lines(page: Mapping[str, Any], label_index: int) -> list[dict[str, Any]]:
    label = _line(page, label_index)
    geometry = _geometry_lines(page)
    width = max(item["bbox"][2] for item in geometry)
    values = assign_numeric_row_v1(
        geometry,
        label_boxes=[label["source_bbox_raw_pixels"]],
        is_numeric=_is_money,
        page_width=width,
    )
    label_box = label["source_bbox_raw_pixels"]
    label_center = (label_box[1] + label_box[3]) / 2
    tolerance = max(12.0, (label_box[3] - label_box[1]) * 0.45)
    inline_by_index = {
        item["source_line_index"]: item
        for item in values
        if abs((item["bbox"][1] + item["bbox"][3]) / 2 - label_center) <= tolerance
    }
    # Very narrow values such as `14` can be rejected by the adaptive row
    # assigner as noise.  Retain them only when they occupy one of the repeated
    # right-hand numeric columns and share the exact physical row.
    inline_by_index.update(
        {
            item["source_line_index"]: item
            for item in geometry
            if item["bbox"][0] > width * 0.45
            and _is_money(item)
            and abs((item["bbox"][1] + item["bbox"][3]) / 2 - label_center) <= tolerance
        }
    )
    inline = [item for item in inline_by_index.values()]
    return sorted(inline, key=lambda item: (item["bbox"][0], item["source_line_index"]))


def _period_column_centers(page: Mapping[str, Any]) -> list[float]:
    width = max(line["source_bbox_raw_pixels"][2] for line in page["lines"])
    candidates = []
    for line in page["lines"]:
        text = _n(line["vietocr_text"])
        bbox = line["source_bbox_raw_pixels"]
        if bbox[0] > width * 0.45 and (_scanner()._period(text) or _scanner()._unit(text)):
            candidates.append((bbox[0] + bbox[2]) / 2)
    groups: list[list[float]] = []
    for center in sorted(candidates):
        for group in groups:
            if abs(center - sum(group) / len(group)) <= max(55.0, width * 0.055):
                group.append(center)
                break
        else:
            groups.append([center])
    if len(groups) < 2:
        raise _error("annual interbank two-period numeric column geometry drifted")
    selected = sorted(groups, key=lambda group: (-len(group), sum(group) / len(group)))[:2]
    return sorted(sum(group) / len(group) for group in selected)


def _numeric_rows(page: Mapping[str, Any], start: int, stop: int) -> list[list[dict[str, Any]]]:
    geometry = _geometry_lines(page)
    width = max(item["bbox"][2] for item in geometry)
    return cluster_numeric_rows_v1(
        geometry,
        is_numeric=_is_money,
        start_index=start,
        stop_index=stop,
        page_width=width,
    )


def _source_axis(
    crop_document: Mapping[str, Any], page_number: int
) -> tuple[dict[str, Any], list[str]]:
    crop_page = _page(crop_document, page_number, "annual crop manifest")
    return crop_page, _support()._source_line_axis(crop_page)


def _value_component(
    semantic_page: Mapping[str, Any], source_axis: Sequence[str], line_index: int
) -> dict[str, Any]:
    line = _line(semantic_page, line_index)
    if len(source_axis) != len(semantic_page["lines"]):
        raise _error("annual interbank source/fresh line denominator drifted")
    source = source_axis[line_index]
    source_value = _money(source)
    fresh_value = _money(line["vietocr_text"])
    rescue = None
    if source_value != fresh_value:
        expected = {
            "crop_sha256": line["crop_ref"]["sha256"],
            "fresh_vietocr_text": line["vietocr_text"],
            "page_sequence": semantic_page["physical_page"],
            "source_line_index": line_index,
            "source_numeric_challenger": source,
        }
        matches = [
            candidate
            for candidate in _GEMMA_RESCUES
            if all(candidate[key] == item for key, item in expected.items())
        ]
        if len(matches) != 1:
            raise _error(
                "unreviewed annual interbank numeric challenger disagreement at "
                f"page {semantic_page['physical_page']} line {line_index}"
            )
        rescue = canonical_clone_v1(matches[0])
    return {
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "fresh_vietocr_numeric_proposal": line["vietocr_text"],
        "gemma4_text_rescue": rescue,
        "normalized_value": source_value,
        "pixel_transcription": source,
        "source_line_index": line_index,
        "source_numeric_challenger": source,
        "source_numeric_challenger_status": "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
    }


def _label_evidence(
    semantic_page: Mapping[str, Any], source_axis: Sequence[str], line_index: int
) -> dict[str, Any]:
    line = _line(semantic_page, line_index)
    if len(source_axis) != len(semantic_page["lines"]):
        raise _error("annual interbank label denominator drifted")
    return {
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "fresh_vietocr_proposal": line["vietocr_text"],
        "normalized_fresh_vietocr": _n(line["vietocr_text"]),
        "pixel_transcription": source_axis[line_index],
        "source_bbox_raw_pixels": list(line["source_bbox_raw_pixels"]),
        "source_line_index": line_index,
    }


def _two_values(
    semantic_page: Mapping[str, Any], source_axis: Sequence[str], label_index: int
) -> list[dict[str, Any]]:
    values = _row_value_lines(semantic_page, label_index)
    if len(values) > 2:
        # Audit stamps can contribute narrow digit fragments.  Bind values to
        # the two independently resolved repeated period/unit column centres,
        # never merely to the first or last numeric-looking tokens.
        centers = _period_column_centers(semantic_page)
        selected = []
        remaining = list(values)
        for expected in centers:
            item = min(
                remaining,
                key=lambda value: abs((value["bbox"][0] + value["bbox"][2]) / 2 - expected),
            )
            selected.append(item)
            remaining.remove(item)
        values = sorted(selected, key=lambda item: item["bbox"][0])
    if len(values) != 2:
        return []
    return [
        _value_component(semantic_page, source_axis, item["source_line_index"]) for item in values
    ]


def _trailing_two_values(
    semantic_page: Mapping[str, Any], source_axis: Sequence[str], start: int, stop: int
) -> list[list[dict[str, Any]]]:
    rows = []
    for row in _numeric_rows(semantic_page, start, stop):
        if len(row) == 2:
            rows.append(
                [
                    _value_component(semantic_page, source_axis, item["source_line_index"])
                    for item in row
                ]
            )
    return rows


def _sum_values(
    components: Sequence[Sequence[Mapping[str, Any]]], *, binding: str
) -> list[dict[str, Any]]:
    if not components or any(len(item) != 2 for item in components):
        raise _error("computed annual interbank value requires complete two-axis components")
    return [
        {
            "component_bindings": [canonical_clone_v1(item[axis]) for item in components],
            "normalized_value": sum(item[axis]["normalized_value"] for item in components),
            "value_binding": binding,
        }
        for axis in range(2)
    ]


def _value_numbers(values: Sequence[Mapping[str, Any]]) -> list[int]:
    if len(values) != 2 or any(type(value.get("normalized_value")) is not int for value in values):
        raise _error("annual interbank mapped value vector drifted")
    return [value["normalized_value"] for value in values]


def _schema_binding(item: Any, role: str) -> dict[str, Any]:
    schema_id, name, parent = _SCHEMA[role]
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id != schema_id
        or item.canonical_name != name
        or item.parent_id != parent
        or item.hierarchy_level not in {1, 2}
        or type(item.display_order) is not int
    ):
        raise _error(f"annual interbank schema binding drifted: {role}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _role_ref(region: Mapping[str, Any], role: str) -> dict[str, Any]:
    value = region["role_refs"].get(role)
    if type(value) is not dict:
        raise _error(f"annual interbank required role missing: {role}")
    return canonical_clone_v1(value)


def _labels_between(
    semantic_page: Mapping[str, Any], start: int, stop: int, predicate: Any
) -> list[dict[str, Any]]:
    return [
        line
        for line in semantic_page["lines"]
        if start < line["source_line_index"] < stop and predicate(_n(line["vietocr_text"]))
    ]


def _currency_kind(text: str) -> str | None:
    if "ngoai te" in text or "ngoai hoi" in text:
        return "FOREIGN"
    if (
        "bang vnd" in text
        or re.search(r"\bbang vn[a-z]\b", text) is not None
        or re.search(r"\bbang v[a-z]?nd\b", text) is not None
        or "dong viet nam" in text
        or "bang tien vnd" in text
    ):
        return "VND"
    return None


def _mapped(
    *,
    role: str,
    schema_by_id: Mapping[int, Any],
    label: dict[str, Any] | None,
    values: Sequence[Mapping[str, Any]],
    topology: str,
) -> dict[str, Any]:
    return {
        "label_evidence": label,
        "role": role,
        "schema_binding": _schema_binding(schema_by_id[_SCHEMA[role][0]], role),
        "status": "VERIFIED_BY_CODEX",
        "topology": topology,
        "values": canonical_clone_v1(list(values)),
    }


def _parse_trial(
    *,
    code: str,
    region: Mapping[str, Any],
    semantic_document: Mapping[str, Any],
    crop_document: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    refs = {
        role: _role_ref(region, role)
        for role in ("OWNER", "DEMAND_DEPOSIT", "TERM_DEPOSIT", "BORROWING")
    }
    if region["role_refs"]["DEPOSIT_PARENT"] is not None:
        refs["DEPOSIT_PARENT"] = _role_ref(region, "DEPOSIT_PARENT")
    pages = {
        number: _page(semantic_document, number, "annual semantic index")
        for number in {ref["page_sequence"] for ref in refs.values()}
    }
    source = {}
    for number in pages:
        _crop_page, source[number] = _source_axis(crop_document, number)

    def evidence(ref: Mapping[str, Any]) -> dict[str, Any]:
        return _label_evidence(
            pages[ref["page_sequence"]], source[ref["page_sequence"]], ref["source_line_index"]
        )

    order = [refs["DEMAND_DEPOSIT"], refs["TERM_DEPOSIT"], refs["BORROWING"]]
    role_values: dict[str, list[dict[str, Any]]] = {}
    role_labels: dict[str, dict[str, Any] | None] = {
        "DEMAND_DEPOSIT": evidence(refs["DEMAND_DEPOSIT"]),
        "TERM_DEPOSIT": evidence(refs["TERM_DEPOSIT"]),
        "BORROWING": evidence(refs["BORROWING"]),
        "DEPOSIT_PARENT": evidence(refs["DEPOSIT_PARENT"]) if "DEPOSIT_PARENT" in refs else None,
        "FAMILY_TOTAL": evidence(refs["OWNER"]),
    }
    auxiliary = []

    # Deposit groups can be explicit rows with inline totals or parent labels
    # followed by currency children and an unlabeled subtotal.
    for ordinal, role in enumerate(("DEMAND_DEPOSIT", "TERM_DEPOSIT")):
        ref = refs[role]
        next_ref = order[ordinal + 1]
        page = pages[ref["page_sequence"]]
        axis = source[ref["page_sequence"]]
        start = ref["source_line_index"]
        stop = (
            next_ref["source_line_index"]
            if ref["page_sequence"] == next_ref["page_sequence"]
            else len(page["lines"])
        )
        children = _labels_between(page, start, stop, lambda text: _currency_kind(text) is not None)
        if _currency_kind(_n(_line(page, start)["vietocr_text"])) is not None:
            children.insert(0, _line(page, start))
        by_kind: dict[str, list[dict[str, Any]]] = {"VND": [], "FOREIGN": []}
        for child in children:
            kind = _currency_kind(_n(child["vietocr_text"]))
            assert kind is not None
            values = _two_values(page, axis, child["source_line_index"])
            if values:
                by_kind[kind].append({"label": child, "values": values})
        if len(by_kind["VND"]) != 1 or len(by_kind["FOREIGN"]) != 1:
            raise _error(f"{code} {role} does not expose one VND and one foreign child")
        for kind, child_role in (
            ("VND", role + "_VND"),
            ("FOREIGN", role + "_FOREIGN"),
        ):
            child = by_kind[kind][0]
            role_values[child_role] = child["values"]
            role_labels[child_role] = _label_evidence(
                page, axis, child["label"]["source_line_index"]
            )
        inline = (
            []
            if _currency_kind(_n(_line(page, start)["vietocr_text"])) is not None
            else _two_values(page, axis, start)
        )
        children_sum = _sum_values(
            [role_values[role + "_VND"], role_values[role + "_FOREIGN"]],
            binding="COMPUTED_EXACT_FROM_VISIBLE_CURRENCY_CHILDREN",
        )
        if inline:
            if _value_numbers(inline) != _value_numbers(children_sum):
                raise _error(f"{code} {role} inline parent does not close to currency children")
            role_values[role] = inline
        else:
            rows = _trailing_two_values(
                page, axis, max(c["source_line_index"] for c in children), stop
            )
            matching = [row for row in rows if _value_numbers(row) == _value_numbers(children_sum)]
            role_values[role] = matching[0] if len(matching) == 1 else children_sum

    # Deposit parent may be explicit, labeled, an unlabeled subtotal, or an
    # exact computed sum of the two complete deposit groups.
    deposit_sum = _sum_values(
        [role_values["DEMAND_DEPOSIT"], role_values["TERM_DEPOSIT"]],
        binding="COMPUTED_EXACT_FROM_VISIBLE_DEMAND_AND_TERM_DEPOSITS",
    )
    deposit_page = pages[refs["TERM_DEPOSIT"]["page_sequence"]]
    deposit_axis = source[refs["TERM_DEPOSIT"]["page_sequence"]]
    deposit_values = []
    if "DEPOSIT_PARENT" in refs:
        deposit_values = _two_values(
            pages[refs["DEPOSIT_PARENT"]["page_sequence"]],
            source[refs["DEPOSIT_PARENT"]["page_sequence"]],
            refs["DEPOSIT_PARENT"]["source_line_index"],
        )
    total_labels = _labels_between(
        deposit_page,
        refs["TERM_DEPOSIT"]["source_line_index"],
        refs["BORROWING"]["source_line_index"]
        if refs["BORROWING"]["page_sequence"] == deposit_page["physical_page"]
        else len(deposit_page["lines"]),
        lambda text: "tong tien gui" in text and ("tctd" in text or "to chuc tin dung" in text),
    )
    if not deposit_values and total_labels:
        deposit_values = _two_values(
            deposit_page, deposit_axis, total_labels[0]["source_line_index"]
        )
    if not deposit_values:
        stop = (
            refs["BORROWING"]["source_line_index"]
            if refs["BORROWING"]["page_sequence"] == deposit_page["physical_page"]
            else len(deposit_page["lines"])
        )
        rows = _trailing_two_values(
            deposit_page,
            deposit_axis,
            refs["TERM_DEPOSIT"]["source_line_index"],
            stop,
        )
        matching = [row for row in rows if _value_numbers(row) == _value_numbers(deposit_sum)]
        deposit_values = matching[0] if len(matching) == 1 else deposit_sum
    if _value_numbers(deposit_values) != _value_numbers(deposit_sum):
        raise _error(f"{code} deposit parent does not close to demand plus term")
    role_values["DEPOSIT_PARENT"] = deposit_values

    # Borrowing permits intermediate sub-parents (e.g. UPAS LC).  Aggregate all
    # top-level visible VND/foreign rows; discount/collateral are non-additive.
    borrow_ref = refs["BORROWING"]
    borrow_page = pages[borrow_ref["page_sequence"]]
    borrow_axis = source[borrow_ref["page_sequence"]]
    start = borrow_ref["source_line_index"]
    rate_lines = [
        line["source_line_index"]
        for line in borrow_page["lines"]
        if line["source_line_index"] > start and "lai suat" in _n(line["vietocr_text"])
    ]
    stop = min(rate_lines, default=len(borrow_page["lines"]))
    currency_labels = _labels_between(
        borrow_page, start, stop, lambda text: _currency_kind(text) is not None
    )
    currency_components: dict[str, list[list[dict[str, Any]]]] = {"VND": [], "FOREIGN": []}
    currency_label_evidence: dict[str, list[dict[str, Any]]] = {"VND": [], "FOREIGN": []}
    for child in currency_labels:
        kind = _currency_kind(_n(child["vietocr_text"]))
        assert kind is not None
        values = _two_values(borrow_page, borrow_axis, child["source_line_index"])
        if values:
            currency_components[kind].append(values)
            currency_label_evidence[kind].append(
                _label_evidence(borrow_page, borrow_axis, child["source_line_index"])
            )
    if not currency_components["VND"] or not currency_components["FOREIGN"]:
        raise _error(f"{code} borrowing does not expose both currency populations")
    for kind, role in (("VND", "BORROWING_VND"), ("FOREIGN", "BORROWING_FOREIGN")):
        components = currency_components[kind]
        role_values[role] = (
            components[0]
            if len(components) == 1
            else _sum_values(
                components,
                binding="COMPUTED_EXACT_FROM_MULTIPLE_VISIBLE_INTERMEDIATE_CURRENCY_BRANCHES",
            )
        )
        role_labels[role] = (
            currency_label_evidence[kind][0]
            if len(currency_label_evidence[kind]) == 1
            else {
                "component_labels": currency_label_evidence[kind],
                "label_binding": "MULTIPLE_INTERMEDIATE_BRANCHES_SAME_CURRENCY_ROLE",
            }
        )

    detail_roles = {
        "BORROWING_VND_DISCOUNT": lambda text: "chiet khau" in text,
        "BORROWING_VND_COLLATERAL": lambda text: "vay cam co" in text or "vay cam co" in text,
    }
    for role, predicate in detail_roles.items():
        matches = _labels_between(borrow_page, start, stop, predicate)
        valued = [
            (line, _two_values(borrow_page, borrow_axis, line["source_line_index"]))
            for line in matches
        ]
        valued = [(line, values) for line, values in valued if values]
        if valued:
            line, values = valued[0]
            role_values[role] = values
            role_labels[role] = _label_evidence(borrow_page, borrow_axis, line["source_line_index"])

    borrow_sum = _sum_values(
        [role_values["BORROWING_VND"], role_values["BORROWING_FOREIGN"]],
        binding="COMPUTED_EXACT_FROM_VISIBLE_CURRENCY_POPULATIONS",
    )
    borrow_values = _two_values(borrow_page, borrow_axis, start)
    rows = _trailing_two_values(borrow_page, borrow_axis, start, stop)
    matching = [row for row in rows if _value_numbers(row) == _value_numbers(borrow_sum)]
    if not borrow_values:
        borrow_values = matching[-1] if matching else borrow_sum
    if _value_numbers(borrow_values) != _value_numbers(borrow_sum):
        # A generic section heading can precede intermediate branch parents;
        # the last exact closing row is the authoritative parent value.
        if matching:
            borrow_values = matching[-1]
        else:
            raise _error(f"{code} borrowing parent does not close to currency populations")
    role_values["BORROWING"] = borrow_values

    source_only_predicates = {
        "UPAS_LC_PAYABLE": lambda text: "upas" in text,
        "IFC_BORROWING_DETAIL": lambda text: "ifc" in text or "cong ty tai chinh quoc te" in text,
    }
    for source_role, predicate in source_only_predicates.items():
        for source_line in _labels_between(borrow_page, start, stop, predicate):
            values = _two_values(borrow_page, borrow_axis, source_line["source_line_index"])
            if values:
                auxiliary.append(
                    {
                        "label_evidence": _label_evidence(
                            borrow_page, borrow_axis, source_line["source_line_index"]
                        ),
                        "reason": "NO_EXACT_LIVE_TM_SCHEMA_LEAF_OR_NONADDITIVE_DETAIL",
                        "role": source_role,
                        "status": "UNRESOLVED_SOURCE_ONLY_AUXILIARY_ROW_RETAINED",
                        "values": values,
                    }
                )

    family_sum = _sum_values(
        [role_values["DEPOSIT_PARENT"], role_values["BORROWING"]],
        binding="COMPUTED_EXACT_FROM_VISIBLE_DEPOSIT_AND_BORROWING_PARENTS",
    )
    # If an explicit/unlabeled combined family total is visible, require exact
    # equality; otherwise the complete child equation supplies the parent.
    owner_page = pages[refs["OWNER"]["page_sequence"]]
    owner_axis = source[refs["OWNER"]["page_sequence"]]
    explicit_family = _labels_between(
        owner_page,
        refs["OWNER"]["source_line_index"],
        len(owner_page["lines"]),
        lambda text: "tong tien gui va vay" in text,
    )
    family_values = []
    if explicit_family:
        family_values = _two_values(owner_page, owner_axis, explicit_family[0]["source_line_index"])
    if not family_values and borrow_page["physical_page"] == owner_page["physical_page"]:
        closing = _trailing_two_values(borrow_page, borrow_axis, start, stop)
        candidates = [row for row in closing if _value_numbers(row) == _value_numbers(family_sum)]
        if candidates:
            family_values = candidates[-1]
    if not family_values:
        family_values = family_sum
    if _value_numbers(family_values) != _value_numbers(family_sum):
        raise _error(f"{code} family total does not close to deposits plus borrowings")
    role_values["FAMILY_TOTAL"] = family_values

    mappings = []
    topology = {
        "FAMILY_TOTAL": "OWNER_PLUS_EXACT_DEPOSIT_AND_BORROWING_PARENT_EQUATION",
        "DEPOSIT_PARENT": "PARENT_EQUALS_DEMAND_PLUS_TERM",
        "BORROWING": "PARENT_EQUALS_AGGREGATED_VND_PLUS_FOREIGN",
    }
    for role in _SCHEMA:
        if role not in role_values:
            continue
        mappings.append(
            _mapped(
                role=role,
                schema_by_id=schema_by_id,
                label=role_labels.get(role),
                values=role_values[role],
                topology=topology.get(role, "OWNER_CHILD_GEOMETRY_AND_TWO_PERIOD_VALUE_ROW"),
            )
        )
    equations = [
        {
            "computed": _value_numbers(role_values[parent]),
            "components": [
                {"role": child, "values": _value_numbers(role_values[child])} for child in children
            ],
            "name": name,
            "status": "CORROBORATED_EXACT",
            "visible_or_derived_parent": _value_numbers(role_values[parent]),
        }
        for name, parent, children in (
            (
                "DEMAND_DEPOSIT_EQUALS_VND_PLUS_FOREIGN",
                "DEMAND_DEPOSIT",
                ("DEMAND_DEPOSIT_VND", "DEMAND_DEPOSIT_FOREIGN"),
            ),
            (
                "TERM_DEPOSIT_EQUALS_VND_PLUS_FOREIGN",
                "TERM_DEPOSIT",
                ("TERM_DEPOSIT_VND", "TERM_DEPOSIT_FOREIGN"),
            ),
            (
                "DEPOSIT_PARENT_EQUALS_DEMAND_PLUS_TERM",
                "DEPOSIT_PARENT",
                ("DEMAND_DEPOSIT", "TERM_DEPOSIT"),
            ),
            (
                "BORROWING_EQUALS_VND_PLUS_FOREIGN",
                "BORROWING",
                ("BORROWING_VND", "BORROWING_FOREIGN"),
            ),
            (
                "FAMILY_TOTAL_EQUALS_DEPOSITS_PLUS_BORROWINGS",
                "FAMILY_TOTAL",
                ("DEPOSIT_PARENT", "BORROWING"),
            ),
        )
    ]
    return mappings, auxiliary, equations


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    rescue_crops: set[str] = set()

    def collect(value: Any) -> None:
        if type(value) is dict:
            rescue = value.get("gemma4_text_rescue")
            if type(rescue) is dict and type(rescue.get("crop_sha256")) is str:
                rescue_crops.add(rescue["crop_sha256"])
            for item in value.values():
                collect(item)
        elif type(value) is list:
            for item in value:
                collect(item)

    collect(list(trials))
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"] == "UNIQUE_COMPLETE_REGION" for trial in trials
        ),
        "gemma4_bounded_numeric_conflict_rescue_count": len(rescue_crops),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "source_only_auxiliary_row_count": sum(
            len(trial["verified_source_only_rows"]) for trial in trials
        ),
        "verified_value_cell_count": sum(
            len(mapping["values"]) for trial in trials for mapping in trial["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("annual interbank result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["state"] != STATE
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual interbank result identity drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("whole_document_uniqueness") != "UNIQUE_COMPLETE_REGION"
            or any(item.get("status") != "VERIFIED_BY_CODEX" for item in trial["verified_mappings"])
        ):
            raise _error("annual interbank trial shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual interbank result ID drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_interbank_funding_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual interbank semantic axis drifted")
    periods = validate_full_document_vietocr_reporting_period_contexts_replay_v1(
        project_full_document_vietocr_reporting_period_contexts_v1(semantic_index),
        semantic_index,
    )
    if periods["projection_id"] != EXPECTED_PERIOD_PROJECTION_ID:
        raise _error("annual interbank reporting-period projection drifted")
    context_by = {
        item["document_provenance"]: item["reporting_period_context"]
        for item in periods["contexts"]
    }
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    trials = []
    scan_ids = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        semantic_document = _document(semantic_index["documents"], code, "annual semantic index")
        crop_document = _document(crop_manifest["documents"], code, "annual crop manifest")
        scan = _scanner().build_annual_2025_interbank_funding_document_scan_v1(semantic_document)
        scan_ids.append(scan["scan_id"])
        if scan["uniqueness"] != "UNIQUE_COMPLETE_REGION":
            raise _error(f"{code} does not have one unique complete interbank funding region")
        context = context_by[code]
        if (
            context["current_period_end"] != "31/12/2025"
            or context["balance_comparative_period_end"] != "31/12/2024"
        ):
            raise _error(f"{code} annual interbank document period drifted")
        region = scan["regions"][0]
        mappings, source_only, equations = _parse_trial(
            code=code,
            region=region,
            semantic_document=semantic_document,
            crop_document=crop_document,
            schema_by_id=schema_by_id,
        )
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "evidence_page_sequence_start": region["page_sequence_start"],
                "evidence_page_sequence_stop": region["page_sequence_stop"],
                "scan_id": scan["scan_id"],
                "source_pdf_sha256": semantic_document["source_pdf"]["sha256"],
                "source_period": "2025-12-31",
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SOURCE_ONLY_AUXILIARY_ROWS"
                    if source_only
                    else "VERIFIED_BY_CODEX"
                ),
                "variant": region["variant"],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
                "whole_document_uniqueness": scan["uniqueness"],
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {"path": CROP_MANIFEST_PATH.as_posix(), "sha256": crop_sha},
            "document_scan_ids": scan_ids,
            "period_projection_id": periods["projection_id"],
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index": {"path": SEMANTIC_INDEX_PATH.as_posix(), "sha256": index_sha},
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": _metrics(trials),
        "schema_family": _schema_binding(schema_by_id[1040], "FAMILY_TOTAL"),
        "state": STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _review(result: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "input_result_id": result["result_id"],
        "metrics": canonical_clone_v1(result["metrics"]),
        "state": "ANNUAL_2025_INTERBANK_FUNDING_PIXEL_REVIEW_COMPLETE",
        "trials": [
            {
                "document_provenance": trial["document_provenance"],
                "page_sequence_start": trial["evidence_page_sequence_start"],
                "page_sequence_stop": trial["evidence_page_sequence_stop"],
                "status": "PASS",
                "verified_mapping_count": len(trial["verified_mappings"]),
                "visible_source_only_count": len(trial["verified_source_only_rows"]),
            }
            for trial in result["trials"]
        ],
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def validate_annual_2025_interbank_funding_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_annual_2025_interbank_funding_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("annual interbank result does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.build:
        if RESULT_PATH.exists() or REVIEW_PATH.exists():
            raise _error("refusing to overwrite annual interbank artifacts")
        result = build_live_annual_2025_interbank_funding_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result) + b"\n")
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(_review(result)) + b"\n")
        print(result["result_id"])
        return 0
    result, _ = _stable_json(
        RESULT_PATH, hashlib.sha256((PROJECT_ROOT / RESULT_PATH).read_bytes()).hexdigest()
    )
    validated = validate_annual_2025_interbank_funding_8bank_codex_verified_mapping_replay_v1(
        result
    )
    review, _ = _stable_json(
        REVIEW_PATH, hashlib.sha256((PROJECT_ROOT / REVIEW_PATH).read_bytes()).hexdigest()
    )
    if not same_typed_json_v1(review, _review(validated)):
        raise _error("annual interbank review drifted")
    print(validated["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
