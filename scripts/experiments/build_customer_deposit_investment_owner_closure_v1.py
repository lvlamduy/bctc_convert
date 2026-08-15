"""Close four project-owner-adjudicated customer-deposit/investment gaps.

This overlay does not rewrite the byte-frozen E-0058 or E-0067 results.  It
exact-replays them, binds the current live TM schema, and records only the four
owner decisions that close CD-001/CD-002 and IS-001/IS-002.  Bank/page fields
are fixed evidence locators; no bank, filename, page, or note number is a
matching rule.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json")
DEPOSIT_RESULT_PATH = Path(
    "docs/experiments/E-0058-customer-deposit-8bank-codex-verified-mapping-v1.json"
)
DEPOSIT_RESULT_SHA256 = "f758a8d181d3f1cfa1e324978727472bef8a29a3971cf7d888faaafea83d21ec"
DEPOSIT_RESULT_ID = (
    "cd8bcv1:result:09592cf9317192b61070bc1d88316a3b996adbb60810cb87683d736582651183"
)
INVESTMENT_RESULT_PATH = Path(
    "docs/experiments/E-0067-investment-securities-8bank-codex-verified-mapping-v1.json"
)
INVESTMENT_RESULT_SHA256 = "eb2f29bb66c15f1c593bd36c586c614332d78226fd7a51663fb6307c7b99a24b"
INVESTMENT_RESULT_ID = (
    "e0067:result:5433c63914c9463b8eaffc10e3929ed6907facde731cccc6457874141c31abcd"
)
SEMANTIC_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
SCHEMA_PROJECTION_SHA256 = "4384238aa0e02035ab2f78e7671460fc03b2d2f25433d0eb9e327e8b7c545229"

FORMAT_VERSION = "CUSTOMER_DEPOSIT_INVESTMENT_PROJECT_OWNER_CLOSURE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_BOUND_REPORT_PROJECT_OWNER_CLOSURE_OF_CD_001_CD_002_IS_001_"
    "IS_002_EXACT_BASE_REPLAY_LIVE_TM_SCHEMA_VISIBLE_PDF_PIXEL_PPOCRV6_"
    "NUMERIC_CHALLENGER_DOCUMENT_UNIT_AND_ACCOUNTING_ONLY_NO_BROAD_CORPUS_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "base_artifacts_rewritten_or_relabelled": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_requires_visible_pixel": True,
    "document_unit_inheritance_requires_explicit_pdf_text": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "persisted_result_self_authenticating": False,
    "project_owner_adjudication_authority": True,
    "public_exact_replay_required": True,
    "source_locator_fields_are_evidence_only": True,
    "text_similarity_alone_used_for_mapping": False,
    "upstream_ppocrv6_used_only_as_numeric_challenger": True,
}
_BID_RENDER_13 = "ad37ee06b7c7a00958eadac79a64704ade85a42594f52daa96b1bde8e11d096c"
_BID_RENDER_23 = "698a0edeef1117abd73f42b074a4292c137f75fede743cbfc6904d2554990bc4"
_VIB_RENDER_36 = "5409b12a869a9775994e9192119a83823a08c27ca2a8e9d692d0f147b718be66"
_BID_FOREIGN_DEBT_COMPARATIVE_DASH = [1446, 1204, 1464, 1218]
_HEX = set("0123456789abcdef")


class CustomerDepositInvestmentOwnerClosureV1Error(ValueError):
    """A pinned input, schema binding, pixel, or accounting decision drifted."""


def _error(message: str) -> CustomerDepositInvestmentOwnerClosureV1Error:
    return CustomerDepositInvestmentOwnerClosureV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load exact-replay dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


deposit = _load_module(
    "customer_deposit_base_for_owner_closure_v1",
    "build_customer_deposit_8bank_codex_verified_mapping_v1.py",
)
investment = _load_module(
    "investment_securities_base_for_owner_closure_v1",
    "build_investment_securities_8bank_codex_verified_mapping_v1.py",
)


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
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise _error(f"fixed path escaped project root: {relative}")
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in relative.parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _error(f"fixed input is not one single-link regular file: {relative}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1 << 20):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    ):
        raise _error(f"fixed input changed during read: {relative}")
    return b"".join(chunks)


def _fixed_json(relative: Path, expected_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable_bytes(relative)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise _error(f"pinned JSON bytes drifted: {relative}")
    return _strict_json(payload, relative.as_posix()), {
        "path": relative.as_posix(),
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _schema_binding(
    item: Any, report_norm_id: int, name: str, parent: int, order: int
) -> dict[str, Any]:
    if (
        item.schema_id != report_norm_id
        or item.canonical_name != name
        or item.parent_id != parent
        or item.display_order != order
    ):
        raise _error(f"live TM schema item {report_norm_id} drifted")
    return {
        "canonical_name": name,
        "display_order": order,
        "parent_report_norm_id": parent,
        "report_norm_id": report_norm_id,
    }


def _one_trial(trials: Any, code: str, key: str) -> dict[str, Any]:
    if type(trials) is not list:
        raise _error("base result trial denominator drifted")
    matches = [trial for trial in trials if trial.get(key) == code]
    if len(matches) != 1:
        raise _error(f"base result does not contain one {code} trial")
    return matches[0]


def _customer_deposit_decision(
    base: Mapping[str, Any], schema_770: Mapping[str, Any]
) -> dict[str, Any]:
    mappings = []
    for code, page, expected_value in (("VPB", 55, 64165), ("VIB", 42, 174)):
        trial = _one_trial(base["trials"], code, "document_provenance")
        unresolved = trial.get("unresolved_items")
        if type(unresolved) is not list or len(unresolved) != 1:
            raise _error(f"{code} customer-deposit unresolved denominator drifted")
        item = unresolved[0]
        binding = item.get("source_value_binding")
        if (
            item.get("physical_page") != page
            or item.get("source_label")
            != "Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50%"
            or type(binding) is not dict
            or binding.get("normalized_value") != expected_value
            or binding.get("source_numeric_challenger_status")
            != "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        ):
            raise _error(f"{code} customer-deposit source item drifted")
        equations = trial.get("verified_accounting_equations")
        expected_equation = (
            "CUSTOMER_TYPE_TOTAL_INCLUDING_UNMAPPED_SOURCE_ROW"
            if code == "VPB"
            else "TCKT_DETAIL_TOTAL_INCLUDING_UNMAPPED_SOURCE_ROW"
        )
        if type(equations) is not list or not any(
            equation.get("name") == expected_equation
            and equation.get("status") == "CORROBORATED_EXACT"
            and equation.get("computed_total") == equation.get("printed_total")
            for equation in equations
        ):
            raise _error(f"{code} customer-deposit accounting closure drifted")
        mappings.append(
            {
                "bank_provenance": code,
                **canonical_clone_v1(schema_770),
                "physical_page": page,
                "source_label": item["source_label"],
                "source_value": canonical_clone_v1(binding),
                "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
            }
        )
    return {
        "base_metrics": canonical_clone_v1(base["metrics"]),
        "closed_ledger_ids": ["CD-001", "CD-002"],
        "family_id": "CUSTOMER_DEPOSIT_CLASSIFICATION",
        "post_adjudication_metrics": {
            "accounting_equation_verified_count": 43,
            "mapping_verified_count": 120,
            "unresolved_source_item_count": 0,
        },
        "resolved_mappings": mappings,
        "schema_binding": canonical_clone_v1(schema_770),
        "status": "PROJECT_OWNER_SCHEMA_770_CLOSURE_VERIFIED",
    }


def _evidence_context(
    semantic_index: Mapping[str, Any], crop_manifest: Mapping[str, Any], code: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        investment.support._document(semantic_index["documents"], code, "semantic index"),
        investment.support._document(crop_manifest["documents"], code, "crop manifest"),
    )


def _label(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    page: int,
    line: int,
    pixel: str,
    render_sha256: str,
) -> dict[str, Any]:
    return investment.support._label_evidence(
        semantic_document,
        manifest_document,
        page,
        investment._line(line, pixel),
        render_sha256,
    )


def _provider_lines(
    manifest_document: Mapping[str, Any], page: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_page = investment.support._page(manifest_document, page, "crop manifest")
    result_ref = manifest_page.get("result_ref")
    if type(result_ref) is not dict:
        raise _error("source page result reference drifted")
    path = result_ref.get("path")
    if type(path) is not str:
        raise _error("source page result path drifted")
    payload = _stable_bytes(Path(path))
    if hashlib.sha256(payload).hexdigest() != result_ref.get("sha256") or len(
        payload
    ) != result_ref.get("size_bytes"):
        raise _error("source page result content identity drifted")
    result = _strict_json(payload, path)
    lines = result.get("lines")
    if type(lines) is not list or len(lines) != manifest_page.get("primary_line_count"):
        raise _error("source page result line denominator drifted")
    return lines, canonical_clone_v1(result_ref)


def _money(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    provider_lines: Sequence[Mapping[str, Any]],
    page: int,
    spec: Mapping[str, Any],
    render_sha256: str,
) -> dict[str, Any]:
    value = investment.support._money_evidence(
        semantic_document, manifest_document, page, spec, render_sha256
    )
    line_index = value["source_line_index"]
    if line_index is None:
        return {
            **value,
            "upstream_ppocrv6_numeric_challenger": None,
            "upstream_ppocrv6_numeric_challenger_status": "NOT_AVAILABLE_PIXEL_ONLY_DASH",
        }
    provider = provider_lines[line_index]
    raw = provider.get("raw_text")
    if (
        type(raw) is not str
        or provider.get("raw_pixel_bbox") != value["source_bbox_raw_pixels"]
        or investment.support.support._money(raw) != value["normalized_value"]
    ):
        raise _error("upstream PP-OCRv6 numeric challenger disagrees with visible pixel")
    return {
        **value,
        "upstream_ppocrv6_numeric_challenger": raw,
        "upstream_ppocrv6_numeric_challenger_status": "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
    }


def _verify_visible_dash(render_ref: Mapping[str, Any], bbox: Sequence[int]) -> None:
    path = render_ref.get("path")
    if type(path) is not str:
        raise _error("DASH render path drifted")
    payload = _stable_bytes(Path(path))
    if hashlib.sha256(payload).hexdigest() != render_ref.get("sha256"):
        raise _error("DASH render content identity drifted")
    with Image.open(io.BytesIO(payload)) as image:
        grayscale = image.convert("L")
        if not (0 <= bbox[0] < bbox[2] <= image.width and 0 <= bbox[1] < bbox[3] <= image.height):
            raise _error("DASH bbox escaped the authenticated render")
        dark = [
            (x, y)
            for y in range(bbox[1], bbox[3])
            for x in range(bbox[0], bbox[2])
            if grayscale.getpixel((x, y)) < 100
        ]
    if not dark:
        raise _error("visible DASH review bbox contains no dark glyph")
    xs = [item[0] for item in dark]
    ys = [item[1] for item in dark]
    if max(xs) - min(xs) + 1 < 5 or max(ys) - min(ys) + 1 > 3:
        raise _error("visible DASH review bbox is not one short horizontal glyph")


def _bid_row(
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    provider_lines: Sequence[Mapping[str, Any]],
    schema_binding: Mapping[str, Any],
    role: str,
    label_specs: Sequence[tuple[int, str]],
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
) -> dict[str, Any]:
    values = []
    for period_role, spec in (("CURRENT", current), ("COMPARATIVE", comparative)):
        values.append(
            {
                "period_role": period_role,
                **_money(
                    semantic_document,
                    manifest_document,
                    provider_lines,
                    23,
                    spec,
                    _BID_RENDER_23,
                ),
            }
        )
    return {
        **canonical_clone_v1(schema_binding),
        "role": role,
        "source_label": [
            _label(
                semantic_document,
                manifest_document,
                23,
                line,
                pixel,
                _BID_RENDER_23,
            )
            for line, pixel in label_specs
        ],
        "source_values": values,
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
    }


def _bid_equation(
    role: str,
    semantic_document: Mapping[str, Any],
    manifest_document: Mapping[str, Any],
    provider_lines: Sequence[Mapping[str, Any]],
    addends: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
) -> dict[str, Any]:
    source_addends = [
        _money(
            semantic_document,
            manifest_document,
            provider_lines,
            23,
            spec,
            _BID_RENDER_23,
        )
        for spec in addends
    ]
    source_total = _money(
        semantic_document,
        manifest_document,
        provider_lines,
        23,
        total,
        _BID_RENDER_23,
    )
    return {
        **investment._equation(
            role,
            [item["normalized_value"] for item in source_addends],
            source_total["normalized_value"],
        ),
        "source_addends": source_addends,
        "source_total": source_total,
    }


def _bid_decision(
    base_trial: Mapping[str, Any],
    scan_trial: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    schemas: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        base_trial.get("status") != "UNRESOLVED_MAPPING"
        or base_trial.get("unresolved_items")
        != [
            {
                "page_sequence": 23,
                "reason": "LOCAL_OR_REPLAY_BOUND_DOCUMENT_UNIT_NOT_ADMITTED",
                "source_label": "CHỨNG KHOÁN ĐẦU TƯ",
            }
        ]
        or scan_trial.get("matcher_result", {}).get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    ):
        raise _error("BID investment base trial or unique structure drifted")
    semantic_document, manifest_document = _evidence_context(semantic_index, crop_manifest, "BID")
    provider_lines, result_ref = _provider_lines(manifest_document, 23)
    render_ref = investment.support._render(manifest_document, 23, _BID_RENDER_23)
    dash = investment._dash(_BID_FOREIGN_DEBT_COMPARATIVE_DASH)
    _verify_visible_dash(render_ref, _BID_FOREIGN_DEBT_COMPARATIVE_DASH)
    rows = [
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[806],
            "AFS_DEBT",
            [(42, "Chứng khoán Nợ")],
            investment._line(43, "173,963,871"),
            investment._line(44, "171,829,517"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[807],
            "AFS_GOVERNMENT",
            [(45, "Chứng khoán chính phủ")],
            investment._line(46, "30,611,982"),
            investment._line(47, "26,481,588"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[808],
            "AFS_TCTD",
            [(48, "Chứng khoán Nợ do các TCTD khác trong nước phát hành")],
            investment._line(49, "143,226,706"),
            investment._line(50, "145,347,929"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[810],
            "AFS_FOREIGN_ORGANIZATION_BY_EXHAUSTIVE_DEBT_TOPOLOGY",
            [(51, "Chứng khoán Nợ nước ngoài")],
            investment._line(52, "125,183"),
            dash,
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[812],
            "AFS_EQUITY",
            [(53, "Chứng khoán Vốn")],
            investment._line(54, "47,428"),
            investment._line(55, "52,919"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[814],
            "AFS_EQUITY_TCTD",
            [(56, "Chứng khoán Vốn do các TCTD khác trong nước phát"), (59, "hành")],
            investment._line(57, "17,721"),
            investment._line(58, "23,064"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[815],
            "AFS_EQUITY_DOMESTIC_TCKT",
            [(60, "Chứng khoán vốn do các TCKT trong nước phát hành")],
            investment._line(61, "23,487"),
            investment._line(62, "23,491"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[816],
            "AFS_EQUITY_FOREIGN_ORGANIZATION",
            [(63, "Chứng khoán Vốn nước ngoài")],
            investment._line(64, "6,220"),
            investment._line(65, "6,364"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[825],
            "AFS_PROVISION",
            [(66, "Dự phòng rủi ro trái phiếu sẵn sàng để bán")],
            investment._line(67, "(22,961)"),
            investment._line(68, "(22,832)"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[848],
            "HTM_GROSS",
            [(73, "Giá trị chứng khoán")],
            investment._line(74, "100,956,425"),
            investment._line(75, "113,629,492"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[831],
            "HTM_GOVERNMENT",
            [(76, "Chứng khoán chính phủ")],
            investment._line(77, "84,781,142"),
            investment._line(78, "98,925,286"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[832],
            "HTM_TCTD",
            [(79, "Chứng khoán Nợ do các TCTD khác trong nước phát hành")],
            investment._line(80, "11,182,283"),
            investment._line(81, "11,238,206"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[833],
            "HTM_DOMESTIC_TCKT",
            [(82, "Chứng khoán Nợ do các TCKT trong nước phát hành")],
            investment._line(83, "4,993,000"),
            investment._line(84, "3,466,000"),
        ),
        _bid_row(
            semantic_document,
            manifest_document,
            provider_lines,
            schemas[849],
            "HTM_PROVISION",
            [(85, "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo"), (88, "hạn")],
            investment._line(86, "(37,448)"),
            investment._line(87, "(25,995)"),
        ),
    ]
    equations = [
        _bid_equation(
            "BID_CURRENT_AFS_DEBT",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(46, "30,611,982"),
                investment._line(49, "143,226,706"),
                investment._line(52, "125,183"),
            ],
            investment._line(43, "173,963,871"),
        ),
        _bid_equation(
            "BID_COMPARATIVE_AFS_DEBT",
            semantic_document,
            manifest_document,
            provider_lines,
            [investment._line(47, "26,481,588"), investment._line(50, "145,347,929"), dash],
            investment._line(44, "171,829,517"),
        ),
        _bid_equation(
            "BID_CURRENT_AFS_EQUITY",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(57, "17,721"),
                investment._line(61, "23,487"),
                investment._line(64, "6,220"),
            ],
            investment._line(54, "47,428"),
        ),
        _bid_equation(
            "BID_COMPARATIVE_AFS_EQUITY",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(58, "23,064"),
                investment._line(62, "23,491"),
                investment._line(65, "6,364"),
            ],
            investment._line(55, "52,919"),
        ),
        _bid_equation(
            "BID_CURRENT_AFS_NET",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(43, "173,963,871"),
                investment._line(54, "47,428"),
                investment._line(67, "(22,961)"),
            ],
            investment._line(69, "173,988,338"),
        ),
        _bid_equation(
            "BID_COMPARATIVE_AFS_NET",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(44, "171,829,517"),
                investment._line(55, "52,919"),
                investment._line(68, "(22,832)"),
            ],
            investment._line(70, "171,859,604"),
        ),
        _bid_equation(
            "BID_CURRENT_HTM_GROSS",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(77, "84,781,142"),
                investment._line(80, "11,182,283"),
                investment._line(83, "4,993,000"),
            ],
            investment._line(74, "100,956,425"),
        ),
        _bid_equation(
            "BID_COMPARATIVE_HTM_GROSS",
            semantic_document,
            manifest_document,
            provider_lines,
            [
                investment._line(78, "98,925,286"),
                investment._line(81, "11,238,206"),
                investment._line(84, "3,466,000"),
            ],
            investment._line(75, "113,629,492"),
        ),
        _bid_equation(
            "BID_CURRENT_HTM_NET",
            semantic_document,
            manifest_document,
            provider_lines,
            [investment._line(74, "100,956,425"), investment._line(86, "(37,448)")],
            investment._line(89, "100,918,977"),
        ),
        _bid_equation(
            "BID_COMPARATIVE_HTM_NET",
            semantic_document,
            manifest_document,
            provider_lines,
            [investment._line(75, "113,629,492"), investment._line(87, "(25,995)")],
            investment._line(90, "113,603,497"),
        ),
    ]
    unit = _label(
        semantic_document,
        manifest_document,
        13,
        49,
        "cáo tài chính hợp nhất này, các số liệu được làm tròn đến hàng triệu và trình bày theo đơn vị triệu VND. Việc trình",
        _BID_RENDER_13,
    )
    return {
        "bank_provenance": "BID",
        "document_unit_evidence": {
            "evidence": unit,
            "scope": "DOCUMENT_LEVEL_MILLION_VND_PROJECT_OWNER_CONFIRMED",
            "unit": "Triệu VND",
        },
        "family_boundary": canonical_clone_v1(base_trial["family_boundary"]),
        "layout": "AFS_AND_HTM_TWO_DATE_COLUMNS_WITH_DOCUMENT_LEVEL_MILLION_VND",
        "page_evidence": {
            "page_sequence": 23,
            "period_axes": [
                _label(semantic_document, manifest_document, 23, 39, "30/06/2026", _BID_RENDER_23),
                _label(semantic_document, manifest_document, 23, 40, "31/12/2025", _BID_RENDER_23),
            ],
            "render_ref": render_ref,
            "result_ref": result_ref,
            "source_projection": canonical_clone_v1(
                investment.support._page(semantic_document, 23, "semantic index")[
                    "source_projection"
                ]
            ),
        },
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
        "structural_scan_result_id": scan_trial["matcher_result"]["result_id"],
        "verified_accounting_equations": equations,
        "verified_mappings": rows,
        "visible_dash_normalized_zero_count": 1,
    }


def _vib_decision(
    base_trial: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    schema_808: Mapping[str, Any],
) -> dict[str, Any]:
    if base_trial.get("unresolved_items") != [
        {
            "page_sequence": 36,
            "reason": "TWO_SOURCE_COMPONENTS_REQUIRE_EXPLICIT_AGGREGATION_INTO_REPORT_NORM_ID_808",
            "source_label": "Trái phiếu và chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
        }
    ]:
        raise _error("VIB investment aggregation denominator drifted")
    semantic_document, manifest_document = _evidence_context(semantic_index, crop_manifest, "VIB")
    provider_lines, result_ref = _provider_lines(manifest_document, 36)
    periods = []
    equations = []
    for period_role, first, second in (
        ("CURRENT", investment._line(17, "5.894.320"), investment._line(20, "32.879.230")),
        (
            "COMPARATIVE",
            investment._line(18, "12.104.102"),
            investment._line(21, "28.252.422"),
        ),
    ):
        components = [
            _money(
                semantic_document,
                manifest_document,
                provider_lines,
                36,
                spec,
                _VIB_RENDER_36,
            )
            for spec in (first, second)
        ]
        total = sum(component["normalized_value"] for component in components)
        periods.append(
            {
                "component_source_values": components,
                "normalized_value": total,
                "period_role": period_role,
                "source_cell_status": "AGGREGATED_TWO_VISIBLE_VALUES",
            }
        )
        equations.append(
            {
                "addends": [component["normalized_value"] for component in components],
                "computed_total": total,
                "period_role": period_role,
                "role": "VIB_TCTD_BOND_PLUS_CERTIFICATE_EQUALS_REPORT_NORM_ID_808",
                "status": "CORROBORATED_EXACT",
            }
        )
    return {
        "bank_provenance": "VIB",
        **canonical_clone_v1(schema_808),
        "aggregation": "SUM_OF_TWO_VISIBLE_TCTD_DEBT_COMPONENTS_PER_PERIOD",
        "component_labels": [
            _label(
                semantic_document,
                manifest_document,
                36,
                15,
                "Trái phiếu do các TCTD khác trong nước phát hành",
                _VIB_RENDER_36,
            ),
            _label(
                semantic_document,
                manifest_document,
                36,
                19,
                "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
                _VIB_RENDER_36,
            ),
        ],
        "equations": equations,
        "result_ref": result_ref,
        "source_values": periods,
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
    }


def _investment_decision(
    base: Mapping[str, Any],
    structure_scan: Mapping[str, Any],
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    schemas: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    bid_base = _one_trial(base["trials"], "BID", "bank_provenance")
    vib_base = _one_trial(base["trials"], "VIB", "bank_provenance")
    bid_scan = _one_trial(structure_scan["trials"], "BID", "document_provenance")
    bid = _bid_decision(bid_base, bid_scan, semantic_index, crop_manifest, schemas)
    vib = _vib_decision(vib_base, semantic_index, crop_manifest, schemas[808])
    return {
        "base_metrics": canonical_clone_v1(base["metrics"]),
        "bid_verified_trial": bid,
        "closed_ledger_ids": ["IS-001", "IS-002"],
        "family_id": "INVESTMENT_SECURITIES",
        "post_adjudication_metrics": {
            "accounting_equation_verified_count": 39,
            "dash_cell_verified_as_zero_count": 16,
            "document_unresolved_count": 0,
            "document_verified_count": 8,
            "mapped_value_cell_count": 198,
            "mapping_verified_count": 99,
            "unresolved_mapping_count": 0,
        },
        "status": "PROJECT_OWNER_UNIT_AND_AGGREGATION_CLOSURE_VERIFIED",
        "vib_808_aggregate_mapping": vib,
    }


def build_live_customer_deposit_investment_owner_closure_v1() -> dict[str, Any]:
    """Exact-rebuild the four owner-adjudicated closures from live inputs."""

    deposit_base, deposit_ref = _fixed_json(DEPOSIT_RESULT_PATH, DEPOSIT_RESULT_SHA256)
    if deposit_base.get("result_id") != DEPOSIT_RESULT_ID:
        raise _error("pinned customer-deposit result identity drifted")
    deposit.validate_customer_deposit_8bank_codex_verified_mapping_replay_v1(deposit_base)

    investment_base, investment_ref = _fixed_json(INVESTMENT_RESULT_PATH, INVESTMENT_RESULT_SHA256)
    if investment_base.get("result_id") != INVESTMENT_RESULT_ID:
        raise _error("pinned investment result identity drifted")
    (
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        manifest_sha,
        review_sha,
    ) = investment._live_inputs()
    rebuilt_investment = investment.build_investment_securities_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=manifest_sha,
        review_sha256=review_sha,
    )
    if not same_typed_json_v1(investment_base, rebuilt_investment):
        raise _error("pinned investment result does not exact-replay")
    if (
        schema_authority.get("tm_schema_projection_sha256") != SCHEMA_PROJECTION_SHA256
        or manifest_sha != CROP_MANIFEST_SHA256
    ):
        raise _error("live TM schema or crop-manifest identity drifted")
    schema_specs = {
        806: ("Chứng khoán nợ", 805, 268),
        807: ("+ Do Chính phủ phát hành (NHNN, Kho bạc)", 805, 269),
        808: ("+ Do các TCTD khác phát hành", 805, 271),
        810: ("+ Do các tổ chức kinh tế nước ngoài phát hành", 805, 273),
        812: ("Chứng khoán vốn", 805, 275),
        814: ("+ Do các TCTD khác phát hành", 805, 277),
        815: ("+ Do các tổ chức kinh tế trong nước phát hành", 805, 278),
        816: ("+ Do các tổ chức kinh tế nước ngoài phát hành", 805, 279),
        825: ("Dự phòng giảm giá chứng khoán sẵn sàng để bán", 805, 288),
        831: ("+ Do Chính phủ phát hành (NHNN, Kho bạc)", 829, 294),
        832: ("+ Do các TCTD khác phát hành", 829, 295),
        833: ("+ Do các tổ chức kinh tế trong nước phát hành", 829, 296),
        848: ("Tổng chứng khoán đầu tư giữ đến ngày đáo hạn", 829, 311),
        849: ("Dự phòng giảm giá đầu tư giữ đến ngày đáo hạn", 829, 312),
    }
    schemas = {
        report_norm_id: _schema_binding(
            schema_by_id[report_norm_id], report_norm_id, name, parent, order
        )
        for report_norm_id, (name, parent, order) in schema_specs.items()
    }
    schema_770 = _schema_binding(
        schema_by_id[770],
        770,
        "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
        766,
        224,
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "customer_deposit": _customer_deposit_decision(deposit_base, schema_770),
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "customer_deposit_result": {
                **deposit_ref,
                "result_id": DEPOSIT_RESULT_ID,
            },
            "investment_result": {
                **investment_ref,
                "result_id": INVESTMENT_RESULT_ID,
            },
            "semantic_index_sha256": SEMANTIC_INDEX_SHA256,
            "tm_schema_projection_sha256": SCHEMA_PROJECTION_SHA256,
        },
        "investment_securities": _investment_decision(
            investment_base, structure_scan, semantic_index, crop_manifest, schemas
        ),
        "metrics": {
            "closed_ledger_entry_count": 4,
            "customer_deposit_added_mapping_count": 2,
            "investment_added_accounting_equation_count": 12,
            "investment_added_mapping_count": 15,
            "investment_added_mapped_value_cell_count": 30,
            "remaining_targeted_unresolved_count": 0,
        },
        "state": "PROJECT_OWNER_CUSTOMER_DEPOSIT_INVESTMENT_CLOSURE_VERIFIED",
    }
    return _validate(
        {**material, "result_id": "e0067c:result:" + canonical_json_sha256_v1(material)}
    )


def _validate(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "customer_deposit",
        "format_version",
        "input_refs",
        "investment_securities",
        "metrics",
        "result_id",
        "state",
    }
    metrics = {
        "closed_ledger_entry_count": 4,
        "customer_deposit_added_mapping_count": 2,
        "investment_added_accounting_equation_count": 12,
        "investment_added_mapping_count": 15,
        "investment_added_mapped_value_cell_count": 30,
        "remaining_targeted_unresolved_count": 0,
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "PROJECT_OWNER_CUSTOMER_DEPOSIT_INVESTMENT_CLOSURE_VERIFIED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or not same_typed_json_v1(value["metrics"], metrics)
    ):
        raise _error("owner closure result shape, authority, or metrics drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "e0067c:result:" + canonical_json_sha256_v1(material):
        raise _error("owner closure content identity drifted")
    return canonical_clone_v1(value)


def validate_customer_deposit_investment_owner_closure_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted closure from all pinned live inputs."""

    persisted = _validate(value)
    rebuilt = build_live_customer_deposit_investment_owner_closure_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("owner closure does not exact-replay")
    return rebuilt


def main() -> None:
    OUTPUT_PATH.write_bytes(
        canonical_json_bytes_v1(build_live_customer_deposit_investment_owner_closure_v1())
    )


if __name__ == "__main__":
    main()
