from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import fitz
import pytest
import yaml

import bctc_ai.rows.native_statement as native
from bctc_ai.axes.header_binding import HeaderBinding
from bctc_ai.cli.main import build_parser
from bctc_ai.core.contracts import BoundingBox, RowType
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import parse_financial_number
from bctc_ai.ocr.pdf_text import PDFTextPage
from bctc_ai.rows.pdf_statement import GeometryCell, StatementRow
from bctc_ai.tables.geometry import ColumnAxis, ColumnRole, PageGeometry, TextRun

_CLEAN_GIT = {"commit": "a" * 40, "dirty": False}
_ROLE_DIRECTORIES = {
    "LOGIC_DEVELOPMENT": "output/development",
    "CALIBRATION": "output/calibration",
    "VALIDATION": "output/validation",
    "PRODUCTION_INPUT": "output/production",
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )


def _identity_paths(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value["path"]
        for child in value.values():
            yield from _identity_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _identity_paths(child)


def _copy(path: str | Path, source_root: Path, destination_root: Path) -> None:
    relative = Path(path)
    destination = destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / relative, destination)


def _page_contract(
    page: int,
    statement_type: str,
    scope: str,
    mapping_eligible: bool,
) -> dict[str, Any]:
    return {
        "page": page,
        "statement_type": statement_type,
        "scope": scope,
        "mapping_eligible": mapping_eligible,
        "continuation_from_page": None,
        "continuation_to_page": None,
        "locally_accepted": True,
        "inferred_from_page": None,
        "inference_direction": None,
        "inference_checks": [],
        "score": 10.0,
        "independent_signal_groups": ["FORM", "TITLE", "PERIOD"],
    }


def _accepted_discovery(
    source: Path,
    root: Path,
    *,
    role: str,
) -> dict[str, Any]:
    digest = sha256_file(source)
    relative = source.relative_to(root).as_posix()
    contracts = [
        _page_contract(1, "CDKT", "MAIN_STATEMENT", True),
        _page_contract(2, "CDKT", "OFF_BALANCE_SHEET", False),
        _page_contract(3, "KQKD", "MAIN_STATEMENT", True),
        _page_contract(4, "LCTT", "MAIN_STATEMENT", True),
    ]
    return {
        "format_version": "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_RESULT_V1",
        "policy": "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1",
        "claim_boundary": "STATEMENT_PAGE_DISCOVERY_ONLY",
        "status": "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY",
        "run_id": "synthetic-discovery-v1",
        "source": {
            "document_id": f"sha256:{digest}",
            "relative_path": relative,
            "sha256": digest,
            "size_bytes": source.stat().st_size,
            "bank": "UNIT",
            "year": 2026,
            "dataset_role": role,
            "registry_state": "REGISTERED",
            "hash_verified_stable": True,
            "immutable_role_assignment": True,
        },
        "code": {"commit": "b" * 40, "dirty": False, "implementation": []},
        "authority": {
            "geometry": "PYMUPDF_NATIVE_TEXT_WORDS",
            "base_scoring_engine": "MULTISIGNAL_STATEMENT_DISCOVERY_V4",
            "base_geometry_authority": "PP_OCRV6_WORD_BOXES",
            "evidence_source": "PYMUPDF_NATIVE_TEXT_GEOMETRY",
            "override_scope": "GEOMETRY_SOURCE_ONLY",
            "semantic_reader": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "role_a_outputs_loaded": False,
            "bank_identity_used_for_scoring": False,
            "filename_identity_used_for_scoring": False,
            "page_number_rules_used_for_scoring": False,
            "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
        },
        "inputs": {"runtime_read_ledger": [], "runtime_read_ledger_sha256": "0" * 64},
        "native_text": {
            "page_count": 6,
            "usable_page_count": 6,
            "ocr_required_pages": [],
            "all_pages_usable": True,
            "pages": [{"page": page, "text_quality": "USABLE_TEXT_LAYER"} for page in range(1, 7)],
        },
        "discovery": {
            "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
            "algorithm_revision": 4,
            "policy": "NATIVE_TEXT_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V1",
            "geometry_authority": "PYMUPDF_NATIVE_TEXT_WORDS",
            "semantic_reader_authority": None,
            "observed_pages": list(range(1, 7)),
            "block": {
                "start_page": 1,
                "end_page": 4,
                "notes_boundary_page": 6,
                "score": 60.0,
                "recognized_pages_by_statement_type": {
                    "CDKT": [1, 2],
                    "KQKD": [3],
                    "LCTT": [4],
                },
                "mapping_eligible_pages_by_statement_type": {
                    "CDKT": [1],
                    "KQKD": [3],
                    "LCTT": [4],
                },
                "mapping_eligible_pages": [1, 3, 4],
                "off_balance_excluded_pages": [2],
                "page_contracts": contracts,
            },
            "cash_flow": {
                "method": "DIRECT",
                "schema_branch_assignment_permitted": False,
            },
            "errors": [],
        },
    }


def _make_project(
    tmp_path: Path,
    canonical_root: Path,
    *,
    role: str = "CALIBRATION",
) -> tuple[Path, Path, Path, Path]:
    root = (tmp_path / "project").resolve()
    root.mkdir(parents=True)
    canonical_policy = canonical_root / native.POLICY_RELATIVE_PATH
    raw_policy = yaml.safe_load(canonical_policy.read_text(encoding="utf-8"))
    files: set[str | Path] = {
        native.POLICY_RELATIVE_PATH,
        *getattr(native, "_IMPLEMENTATION_PATHS", ()),
    }
    files.update(_identity_paths(raw_policy))
    for relative in files:
        _copy(relative, canonical_root, root)

    source = root / "data/incoming/unit-bank-2026.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as document:
        for page_number in range(1, 7):
            page = document.new_page(width=600, height=800)
            page.insert_text((36, 54), f"SYNTHETIC SOURCE PAGE {page_number}")
        document.save(source)
    digest = sha256_file(source)
    relative = source.relative_to(root).as_posix()
    _write_jsonl(
        root / "data/registered/source_registry.jsonl",
        [
            {
                "bank": "UNIT",
                "document_id": f"sha256:{digest}",
                "hash_verified_stable": True,
                "immutable_copy": None,
                "kind": "PDF",
                "registered_at": "2026-08-08T00:00:00+00:00",
                "relative_path": relative,
                "sha256": digest,
                "size_bytes": source.stat().st_size,
                "source_mtime_ns": source.stat().st_mtime_ns,
                "state": "REGISTERED",
                "year": 2026,
            }
        ],
    )
    _write_jsonl(
        root / "data/registered/dataset_roles.jsonl",
        [
            {
                "assigned_at": "2026-08-08T00:00:00+00:00",
                "dataset_role": role,
                "document_id": f"sha256:{digest}",
                "immutable": True,
                "source_path": relative,
            }
        ],
    )
    discovery = root / _ROLE_DIRECTORIES.get(role, "output/development") / "discovery.json"
    _write_json(discovery, _accepted_discovery(source, root, role=role))
    return root, source, discovery, root / native.POLICY_RELATIVE_PATH


def _native_pages(*, unusable: set[int] | None = None) -> list[PDFTextPage]:
    unusable = unusable or set()
    return [
        PDFTextPage(
            page=page,
            width_points=600,
            height_points=800,
            rotation=0,
            words=[],
            text_quality=(
                "OCR_REQUIRED_CORRUPT_TEXT_LAYER" if page in unusable else "USABLE_TEXT_LAYER"
            ),
            corruption_markers=(),
        )
        for page in range(1, 7)
    ]


def _geometry(page: int) -> PageGeometry:
    runs = (
        TextRun(
            run_id="section-label",
            raw_text="TÀI SẢN",
            normalized_text="TÀI SẢN",
            bbox=BoundingBox(40.25, 140.5, 120.75, 151.25),
            word_indices=(0,),
            block_number=1,
            line_number=0,
        ),
        TextRun(
            run_id="data-label",
            raw_text="Khoản mục nguồn",
            normalized_text="Khoản mục nguồn",
            bbox=BoundingBox(40, 170, 180, 181),
            word_indices=(1,),
            block_number=2,
            line_number=0,
        ),
        TextRun(
            run_id="note-reference",
            raw_text="12.1",
            normalized_text="12.1",
            bbox=BoundingBox(335, 170, 350, 181),
            word_indices=(2,),
            block_number=3,
            line_number=0,
        ),
    )
    return PageGeometry(
        page=page,
        width_points=600,
        height_points=800,
        data_start_y=130,
        data_end_y=752,
        label_right_boundary=350,
        edge_tolerance=7.2,
        runs=runs,
        axes=(
            ColumnAxis("value-1", ColumnRole.VALUE, 450, 410, 3, "synthetic"),
            ColumnAxis("value-2", ColumnRole.VALUE, 550, 510, 3, "synthetic"),
        ),
        unit_run_ids=(),
        warnings=("synthetic geometry warning",),
    )


def _rows(page: int, table_id: str | None = None) -> list[StatementRow]:
    prefix = table_id or f"page-{page}"
    return [
        StatementRow(
            row_id=f"{prefix}:row-0001",
            page=page,
            row_type=RowType.SECTION_HEADER,
            label="TÀI SẢN",
            label_boxes=(BoundingBox(40.25, 140.5, 120.75, 151.25),),
            note_reference=None,
            note_bbox=None,
            cells=(),
            y0=140.5,
            y1=151.25,
            indentation=40.25,
            warnings=("label-only row retained for ordered context",),
        ),
        StatementRow(
            row_id=f"{prefix}:row-0002",
            page=page,
            row_type=RowType.DATA_ROW,
            label="Khoản mục nguồn",
            label_boxes=(BoundingBox(40, 170, 180, 181),),
            note_reference="12.1",
            note_bbox=BoundingBox(335, 170, 350, 181),
            cells=(
                GeometryCell(
                    axis_id="value-1",
                    raw_text="(1.234)",
                    parsed=parse_financial_number("(1.234)"),
                    bbox=BoundingBox(410, 170, 450, 181),
                    run_id="b2:l0:s1",
                    axis_distance=0.125,
                ),
                GeometryCell(
                    axis_id="value-2",
                    raw_text="-",
                    parsed=parse_financial_number("-"),
                    bbox=BoundingBox(545, 170, 550, 181),
                    run_id="b3:l0:s1",
                    axis_distance=0.0,
                ),
            ),
            y0=170,
            y1=181,
            indentation=40,
            warnings=(),
        ),
        StatementRow(
            row_id=f"{prefix}:row-0003",
            page=page,
            row_type=RowType.DATA_ROW,
            label="",
            label_boxes=(),
            note_reference=None,
            note_bbox=None,
            cells=(
                GeometryCell(
                    axis_id="value-1",
                    raw_text="25",
                    parsed=parse_financial_number("25"),
                    bbox=BoundingBox(435, 195, 450, 206),
                    run_id="b4:l0:s1",
                    axis_distance=0.0,
                ),
            ),
            y0=195,
            y1=206,
            indentation=0,
            warnings=("numeric row has no attached label",),
        ),
    ]


def _headers() -> list[HeaderBinding]:
    return [
        HeaderBinding(
            axis_id="value-1",
            raw_header="Ngày 31 tháng 3 năm 2026 Triệu đồng",
            header_bbox=BoundingBox(390, 80, 455, 120),
            unit="VND_MILLION",
            unit_multiplier=1_000_000,
            unit_bbox=BoundingBox(405, 110, 450, 120),
            period_start=date(2026, 3, 31),
            period_end=date(2026, 3, 31),
            period_type="SNAPSHOT",
            duration_months=None,
            current_or_comparative="CURRENT",
            restated=False,
            confidence=1.0,
            evidence=("period end parsed from axis-local header",),
        ),
        HeaderBinding(
            axis_id="value-2",
            raw_header="Ngày 31 tháng 12 năm 2025 Triệu đồng",
            header_bbox=BoundingBox(490, 80, 555, 120),
            unit="VND_MILLION",
            unit_multiplier=1_000_000,
            unit_bbox=BoundingBox(505, 110, 550, 120),
            period_start=date(2025, 12, 31),
            period_end=date(2025, 12, 31),
            period_type="SNAPSHOT",
            duration_months=None,
            current_or_comparative="COMPARATIVE",
            restated=False,
            confidence=0.95,
            evidence=("period end parsed from axis-local header",),
        ),
    ]


def _patch_source_processing(
    monkeypatch: pytest.MonkeyPatch,
    *,
    unusable: set[int] | None = None,
) -> None:
    monkeypatch.setattr(
        native,
        "extract_pdf_text_v2",
        lambda source, *, config, page_numbers=None: [
            page
            for page in _native_pages(unusable=unusable)
            if page_numbers is None or page.page in page_numbers
        ],
    )
    monkeypatch.setattr(native, "analyze_page_geometry", lambda page, config: _geometry(page.page))
    monkeypatch.setattr(
        native,
        "reconstruct_statement_rows",
        lambda geometry, config, table_id=None: _rows(geometry.page, table_id),
    )
    monkeypatch.setattr(native, "financial_table_span", lambda rows: rows)
    monkeypatch.setattr(native, "bind_value_headers", lambda geometry, config: _headers())


def _patch_commit_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    def current_identity(root: Path, commit: str, raw_path: str) -> dict[str, Any]:
        del commit
        path = root / raw_path
        return {
            "path": raw_path,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    monkeypatch.setattr(native, "_file_identity_at_commit", current_identity)


def _build(
    root: Path,
    source: Path,
    discovery: Path,
    policy: Path,
) -> dict[str, Any]:
    return native.build_registered_native_statement_rows(
        project_root=root,
        source_pdf=source,
        discovery_path=discovery,
        discovery_sha256=sha256_file(discovery),
        policy_path=policy,
        run_id="synthetic-native-rows-v1",
        git_state=dict(_CLEAN_GIT),
    )


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _strings(child)


def _keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        yield from value
        for child in value.values():
            yield from _keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _keys(child)


def test_policy_and_build_bind_exact_source_discovery_role_and_selected_pages(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)

    policy = native.load_native_statement_rows_policy(policy_path, root)
    payload = _build(root, source, discovery, policy_path)

    assert policy["claim_boundary"] == "UNMAPPED_SOURCE_ROWS_AND_CELLS_ONLY"
    assert payload["status"] == "ACCEPTED_NATIVE_STATEMENT_ROWS"
    assert payload["source"]["sha256"] == sha256_file(source)
    assert payload["source"]["dataset_role"] == "CALIBRATION"
    assert payload["statement_discovery"]["path"] == discovery.relative_to(root).as_posix()
    assert payload["statement_discovery"]["sha256"] == sha256_file(discovery)
    assert payload["authority"]["geometry"] == "PYMUPDF_NATIVE_TEXT_WORDS"
    assert payload["authority"]["schema_mapper"] is None
    assert [page["page"] for page in payload["pages"]] == [1, 2, 3, 4]
    assert [page["statement_type"] for page in payload["pages"]] == [
        "CDKT",
        "CDKT",
        "KQKD",
        "LCTT",
    ]
    assert payload["pages"][1]["scope"] == "OFF_BALANCE_SHEET"
    assert payload["pages"][1]["discovery_contract"]["mapping_eligible"] is False
    assert payload["selection"]["notes_pages_selected"] == 0
    assert payload["selection"]["selected_pages"] == [1, 2, 3, 4]
    ledger = payload["inputs"]["runtime_read_ledger"]
    assert {record["kind"] for record in ledger} == {
        "SOURCE_PDF",
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "ACCEPTED_STATEMENT_DISCOVERY",
        "THIS_POLICY",
        "NATIVE_TEXT_QUALITY_CONFIG",
        "GEOMETRY_CONFIG",
    }
    assert all(set(record) == {"kind", "path", "sha256", "size_bytes"} for record in ledger)


def test_rows_headers_decimals_dates_dash_bboxes_and_warnings_are_json_explicit(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)

    first = _build(root, source, discovery, policy_path)
    second = _build(root, source, discovery, policy_path)

    assert first == second
    page = first["pages"][0]
    assert page["headers"][0]["period_start"] == "2026-03-31"
    assert page["headers"][0]["period_end"] == "2026-03-31"
    assert page["headers"][0]["header_bbox"] == {
        "x0": 390,
        "y0": 80,
        "x1": 455,
        "y1": 120,
    }
    assert page["headers"][0]["unit_bbox"] == {
        "x0": 405,
        "y0": 110,
        "x1": 450,
        "y1": 120,
    }
    assert page["rows"][0]["row_type"] == "SECTION_HEADER"
    assert page["rows"][0]["raw_label"] == "TÀI SẢN"
    assert page["rows"][0]["normalized_label"] == "TÀI SẢN"
    assert page["rows"][0]["cells"] == []
    value, dash = page["rows"][1]["cells"]
    assert value["raw_text"] == "(1.234)"
    assert value["normalized_text"] == "-1234"
    assert value["value"] == "-1234"
    assert value["observation"] == "VALUE"
    assert value["sign_evidence"] == "parentheses"
    assert value["bbox"] == {"x0": 410, "y0": 170, "x1": 450, "y1": 181}
    expected_table_prefix = f"native-{sha256_file(source)[:16]}-cdkt-main-statement-page-0001"
    assert page["rows"][1]["row_id"].startswith(expected_table_prefix)
    assert value["provenance"]["table_id"] == expected_table_prefix
    assert value["provenance"]["document_sha256"] == sha256_file(source)
    assert dash["raw_text"] == "-"
    assert dash["value"] is None
    assert dash["observation"] == "DASH"
    assert page["rows"][2]["normalized_label"] == ""
    assert page["rows"][2]["warnings"] == ["numeric row has no attached label"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda item: item.update(status="UNRESOLVED_NATIVE_TEXT_STATEMENT_DISCOVERY"),
            "acceptance contract",
        ),
        (
            lambda item: item["authority"].update(geometry="PP_OCRV6_WORD_BOXES"),
            "authority|geometry|native",
        ),
        (
            lambda item: item["discovery"].update(status="UNRESOLVED"),
            "acceptance contract",
        ),
        (
            lambda item: item["discovery"].update(geometry_authority="PP_OCRV6_WORD_BOXES"),
            "acceptance contract|authority|geometry|native",
        ),
        (lambda item: item["source"].update(sha256="f" * 64), "source|hash|identity"),
        (
            lambda item: item["source"].update(dataset_role="VALIDATION"),
            "role|identity",
        ),
    ],
)
def test_discovery_must_be_accepted_native_and_match_exact_source_and_role(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation,
    message: str,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    payload = json.loads(discovery.read_text(encoding="utf-8"))
    mutation(payload)
    _write_json(discovery, payload)

    with pytest.raises(native.NativeStatementRowsError, match=message):
        _build(root, source, discovery, policy_path)


def test_registry_source_hash_and_role_identity_are_rechecked(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    registry = root / "data/registered/source_registry.jsonl"
    record = json.loads(registry.read_text(encoding="utf-8"))
    record["sha256"] = "0" * 64
    record["document_id"] = "sha256:" + record["sha256"]
    _write_jsonl(registry, [record])

    with pytest.raises(native.NativeStatementRowsError, match="source|registry|hash|sha256"):
        _build(root, source, discovery, policy_path)


def test_ineligible_page_contract_cannot_widen_row_selection(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    payload = json.loads(discovery.read_text(encoding="utf-8"))
    payload["discovery"]["block"]["page_contracts"].append(
        _page_contract(5, "KQKD", "NOT_APPLICABLE", False)
    )
    _write_json(discovery, payload)

    with pytest.raises(native.NativeStatementRowsError, match="unsupported page contract"):
        _build(root, source, discovery, policy_path)


def test_off_balance_mapping_flag_and_notes_boundary_are_strictly_separate(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    payload = json.loads(discovery.read_text(encoding="utf-8"))
    payload["discovery"]["block"]["page_contracts"][1]["mapping_eligible"] = True
    _write_json(discovery, payload)
    with pytest.raises(native.NativeStatementRowsError, match="unsupported page contract"):
        _build(root, source, discovery, policy_path)

    payload = _accepted_discovery(source, root, role="CALIBRATION")
    payload["discovery"]["block"]["notes_boundary_page"] = 4
    _write_json(discovery, payload)
    with pytest.raises(native.NativeStatementRowsError, match="notes boundary"):
        _build(root, source, discovery, policy_path)

    payload = _accepted_discovery(source, root, role="CALIBRATION")
    payload["discovery"]["block"]["page_contracts"].append(
        _page_contract(6, "TM", "MAIN_STATEMENT", True)
    )
    _write_json(discovery, payload)
    with pytest.raises(native.NativeStatementRowsError, match="unsupported page contract"):
        _build(root, source, discovery, policy_path)


def test_bounded_inferred_page_contract_requires_complete_visible_checks(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    payload = json.loads(discovery.read_text(encoding="utf-8"))
    block = payload["discovery"]["block"]
    block["page_contracts"].append(_page_contract(5, "LCTT", "MAIN_STATEMENT", True))
    block["recognized_pages_by_statement_type"]["LCTT"] = [4, 5]
    block["mapping_eligible_pages_by_statement_type"]["LCTT"] = [4, 5]
    block["mapping_eligible_pages"] = [1, 3, 4, 5]
    block["end_page"] = 5
    inferred = block["page_contracts"][3]
    inferred.update(
        locally_accepted=False,
        inferred_from_page=5,
        inference_direction="BACKWARD_FROM_NEXT",
        inference_checks=[
            "ACCOUNTING_ROWS",
            "NUMERIC_GEOMETRY",
            "SHARED_NUMERIC_AXES",
            "TABLE_EDGE_CONTINUITY",
        ],
    )
    _write_json(discovery, payload)

    accepted = _build(root, source, discovery, policy_path)
    assert accepted["pages"][3]["discovery_contract"]["locally_accepted"] is False
    assert accepted["pages"][3]["discovery_contract"]["inferred_from_page"] == 5

    inferred["inference_checks"] = []
    _write_json(discovery, payload)
    with pytest.raises(
        native.NativeStatementRowsError,
        match="neither locally accepted nor boundedly inferred",
    ):
        _build(root, source, discovery, policy_path)


def test_rows_outside_financial_span_remain_in_explicit_audit_channel(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    monkeypatch.setattr(native, "financial_table_span", lambda rows: rows[:2])

    payload = _build(root, source, discovery, policy_path)

    page = payload["pages"][0]
    assert page["financial_table_span_row_count"] == 2
    assert page["outside_financial_table_span_row_count"] == 1
    outside = page["outside_financial_table_span_rows"][0]
    assert outside["within_financial_table_span"] is False
    assert outside["normalized_label"] == ""
    assert outside["warnings"] == ["numeric row has no attached label"]
    assert outside["cells"][0]["source_status"] == "OBSERVED_VALUE"
    assert payload["summary"]["cell_count"] == 8
    all_source_cells = sum(
        len(row["cells"])
        for record in payload["pages"]
        for bucket in ("rows", "outside_financial_table_span_rows")
        for row in record[bucket]
    )
    assert all_source_cells == 12


def test_dirty_git_and_holdout_are_rejected(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path / "dirty", project_root)
    _patch_source_processing(monkeypatch)
    with pytest.raises(native.NativeStatementRowsError, match="dirty|clean Git"):
        native.build_registered_native_statement_rows(
            root,
            source,
            discovery,
            sha256_file(discovery),
            policy_path,
            "synthetic-native-rows-v1",
            {"commit": "a" * 40, "dirty": True},
        )

    holdout_root, holdout_source, holdout_discovery, holdout_policy = _make_project(
        tmp_path / "forbidden_role", project_root, role="UNTOUCHED_HOLDOUT"
    )
    with pytest.raises(native.NativeStatementRowsError, match="holdout|UNTOUCHED_HOLDOUT"):
        _build(holdout_root, holdout_source, holdout_discovery, holdout_policy)


def test_nonusable_selected_page_requires_ocr_and_fails_closed(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch, unusable={3})

    with pytest.raises(native.NativeStatementRowsError, match="page 3|OCR|required|usable"):
        _build(root, source, discovery, policy_path)


def test_runtime_input_drift_is_detected_after_extraction(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    original = native._runtime_input_ledger
    calls = 0

    def drifting(project_root: Path, inputs):
        nonlocal calls
        calls += 1
        records = original(project_root, inputs)
        if calls > 1:
            records = copy.deepcopy(records)
            records[0]["sha256"] = "e" * 64
        return records

    monkeypatch.setattr(native, "_runtime_input_ledger", drifting)
    with pytest.raises(native.NativeStatementRowsError, match="changed|drift|runtime input"):
        _build(root, source, discovery, policy_path)


def test_payload_contains_no_schema_mapping_or_absolute_project_paths(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)

    payload = _build(root, source, discovery, policy_path)

    assert str(root) not in "\n".join(_strings(payload))
    forbidden = ("reportnorm", "schema_id", "canonical_name", "mapping_candidate")
    lowered_keys = {key.casefold() for key in _keys(payload)}
    assert not any(fragment in key for key in lowered_keys for fragment in forbidden)
    assert payload["isolation"]["historical_values_loaded"] is False
    assert payload["isolation"]["role_a_outputs_loaded"] is False


def test_publication_is_exclusive_and_role_directory_bound(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    monkeypatch.setattr(native, "_current_git_state", lambda root: dict(_CLEAN_GIT))
    output = root / "output/calibration/native-rows/result.json"

    publication = native.publish_registered_native_statement_rows(
        root,
        source,
        discovery,
        sha256_file(discovery),
        policy_path,
        "synthetic-native-rows-v1",
        output,
    )

    assert publication.path == output
    assert publication.sha256 == sha256_file(output)
    assert publication.size_bytes == output.stat().st_size
    with pytest.raises(native.NativeStatementRowsError, match="overwrite|exists"):
        native.publish_registered_native_statement_rows(
            root,
            source,
            discovery,
            sha256_file(discovery),
            policy_path,
            "synthetic-native-rows-v1",
            output,
        )
    with pytest.raises(native.NativeStatementRowsError, match="calibration|role|output"):
        native.publish_registered_native_statement_rows(
            root,
            source,
            discovery,
            sha256_file(discovery),
            policy_path,
            "synthetic-native-rows-v2",
            root / "output/development/native-rows/result.json",
        )


def test_strict_loader_roundtrips_canonical_publication_and_rejects_tamper(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    monkeypatch.setattr(native, "_current_git_state", lambda root: dict(_CLEAN_GIT))
    _patch_commit_identity(monkeypatch)
    output = root / "output/calibration/native-rows/loadable.json"
    publication = native.publish_registered_native_statement_rows(
        root,
        source,
        discovery,
        sha256_file(discovery),
        policy_path,
        "synthetic-native-rows-loadable-v1",
        output,
    )

    loaded = native.load_registered_native_statement_rows(
        output,
        project_root=root,
        expected_sha256=publication.sha256,
    )
    assert loaded == publication.payload

    tampered = copy.deepcopy(loaded)
    cell = tampered["pages"][0]["rows"][1]["cells"][0]
    cell["observation"] = "DASH"
    _write_json(output, tampered)
    with pytest.raises(native.NativeStatementRowsError, match="trusted.*SHA-256"):
        native.load_registered_native_statement_rows(
            output,
            project_root=root,
            expected_sha256=publication.sha256,
        )


def test_strict_loader_rejects_coherent_structural_tampering(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    _patch_commit_identity(monkeypatch)
    monkeypatch.setattr(native, "_current_git_state", lambda root: dict(_CLEAN_GIT))
    output = root / "output/calibration/native-rows/strict.json"
    publication = native.publish_registered_native_statement_rows(
        root,
        source,
        discovery,
        sha256_file(discovery),
        policy_path,
        "synthetic-native-rows-strict-v1",
        output,
    )

    cases = (
        "code_implementation",
        "authority",
        "isolation",
        "runtime_ledger",
        "selection",
        "discovery_contract",
        "statement_type",
        "scope",
        "geometry",
        "axis",
        "header",
        "native_word_digest",
        "row_type",
        "row_id",
        "bbox",
        "table_provenance",
    )
    for case in cases:
        tampered = copy.deepcopy(publication.payload)
        page = tampered["pages"][0]
        row = page["rows"][1]
        if case == "code_implementation":
            tampered["code"]["implementation"][0]["sha256"] = "f" * 64
        elif case == "authority":
            tampered["authority"]["schema_mapper"] = "FORBIDDEN"
        elif case == "isolation":
            tampered["isolation"]["historical_values_loaded"] = True
        elif case == "runtime_ledger":
            tampered["inputs"]["runtime_read_ledger"][0]["sha256"] = "f" * 64
            tampered["inputs"]["runtime_read_ledger_sha256"] = native.stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True)
                for record in tampered["inputs"]["runtime_read_ledger"]
            )
        elif case == "selection":
            tampered["selection"]["policy"] = "WIDENED"
        elif case == "discovery_contract":
            page["discovery_contract"]["score"] = 999.0
        elif case == "statement_type":
            page["statement_type"] = "TM"
        elif case == "scope":
            page["scope"] = "NOT_APPLICABLE"
        elif case == "geometry":
            page["geometry"]["authority"] = "PP_OCRV6_WORD_BOXES"
        elif case == "axis":
            page["geometry"]["axes"][0]["sample_count"] = 0
        elif case == "header":
            page["headers"][0]["axis_id"] = "unknown-axis"
        elif case == "native_word_digest":
            page["native_words_sha256"] = "not-a-digest"
        elif case == "row_type":
            row["row_type"] = "UNKNOWN_ROW_TYPE"
        elif case == "row_id":
            row["row_id"] = row["row_id"].replace("native-", "foreign-", 1)
            row["provenance"]["row_id"] = row["row_id"]
            for cell in row["cells"]:
                cell["provenance"]["row_id"] = row["row_id"]
        elif case == "bbox":
            row["cells"][0]["bbox"]["x1"] = -1
            row["cells"][0]["provenance"]["value_bbox"]["x1"] = -1
        elif case == "table_provenance":
            row["provenance"]["table_id"] = "foreign-table"
        if case in {
            "discovery_contract",
            "statement_type",
            "scope",
            "geometry",
            "axis",
            "header",
            "native_word_digest",
            "row_type",
            "row_id",
            "bbox",
            "table_provenance",
        }:
            tampered["summary"]["pages_sha256"] = native.stable_records_hash(
                json.dumps(item, ensure_ascii=False, sort_keys=True) for item in tampered["pages"]
            )
        _write_json(output, tampered)
        with pytest.raises(native.NativeStatementRowsError):
            native.load_registered_native_statement_rows(
                output,
                project_root=root,
                expected_sha256=sha256_file(output),
            )


def test_trusted_discovery_digest_and_post_link_rollback_are_fail_closed(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy_path = _make_project(tmp_path, project_root)
    _patch_source_processing(monkeypatch)
    trusted_discovery_sha256 = sha256_file(discovery)
    discovery.write_bytes(discovery.read_bytes() + b" ")
    with pytest.raises(native.NativeStatementRowsError, match="trusted SHA-256"):
        native.build_registered_native_statement_rows(
            root,
            source,
            discovery,
            trusted_discovery_sha256,
            policy_path,
            "trusted-discovery-v1",
            dict(_CLEAN_GIT),
        )

    target = tmp_path / "exclusive" / "rows.json"
    real_fsync = native.os.fsync
    calls = 0

    def fail_after_link(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated post-link directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(native.os, "fsync", fail_after_link)
    with pytest.raises(OSError, match="post-link"):
        native._write_exclusive(target, b"{}\n")
    assert not target.exists()


def test_cli_has_stable_defaults_and_prints_project_relative_artifact(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    root, source, discovery, _ = _make_project(tmp_path, project_root)
    output = root / "output/calibration/run/result.json"
    parser = build_parser()
    parsed = parser.parse_args(
        [
            "--project-root",
            str(root),
            "extract-native-rows",
            "--pdf",
            source.relative_to(root).as_posix(),
            "--discovery",
            discovery.relative_to(root).as_posix(),
            "--discovery-sha256",
            sha256_file(discovery),
            "--output",
            output.relative_to(root).as_posix(),
        ]
    )
    assert parsed.policy == native.POLICY_RELATIVE_PATH.as_posix()
    assert parsed.run_id == "registered-native-statement-rows-v1"
    fake_payload = {"status": "ACCEPTED_NATIVE_STATEMENT_ROWS"}
    fake = native.NativeStatementRowsPublication(
        path=output,
        sha256="d" * 64,
        size_bytes=123,
        payload=fake_payload,
    )
    monkeypatch.setattr(native, "publish_registered_native_statement_rows", lambda *args: fake)

    assert parsed.handler(parsed) == 0
    stdout = capsys.readouterr().out
    assert "NATIVE_STATEMENT_ROWS_STATUS=ACCEPTED_NATIVE_STATEMENT_ROWS" in stdout
    assert "NATIVE_STATEMENT_ROWS_ARTIFACT=output/calibration/run/result.json" in stdout
    assert str(root) not in stdout
