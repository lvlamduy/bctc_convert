from __future__ import annotations

import copy
import datetime as datetime_module
import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from openpyxl import load_workbook

from bctc_ai.evaluation import e0041_post_mapping_export as export_module
from bctc_ai.evaluation.e0041_post_mapping_export import (
    E0041PostMappingExportError,
    _load_template,
    _publish_pair,
    _stable_read,
    _validate_mapping_challenger,
    assemble_post_mapping_projection,
    build_development_workbook,
)
from bctc_ai.mapping.e0040_calibration_challenger import (
    align_e0040_calibration_challenger,
    load_e0040_policy,
    projection_from_sealed_mapping_payload,
    source_rows_from_sealed_mapping_payload,
)
from bctc_ai.mapping.ordered_subgraph_v2 import load_ordered_subgraph_v2_policy

_CONTROL = Path("config/experiments/e0041-mbb-cdkt-post-mapping-development-excel.yaml")
_POSTJOIN = Path("docs/experiments/E-0037-mbb-cdkt-sealed-evidence-mapping.json")
_E0037_MAPPING = Path("output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json")
_E0038_MAPPING = Path("output/calibration/e0038-mbb-cdkt-exact-mapping/mapping_only.json")
_E0040_POLICY = Path("config/mapping/e0040-cdkt-semantic-normalization.yaml")
_MAPPER_POLICY = Path("config/mapping/ordered-subgraph-v2-exact-e0038.yaml")
_TEMPLATE = Path("template/Bank_CDKT_ReportNormId.xlsx")


@pytest.fixture(scope="module")
def e0040_result(project_root: Path):
    sealed = json.loads((project_root / _E0037_MAPPING).read_text(encoding="utf-8"))
    return align_e0040_calibration_challenger(
        source_rows_from_sealed_mapping_payload(sealed),
        projection_from_sealed_mapping_payload(sealed),
        policy=load_e0040_policy(project_root / _E0040_POLICY),
        mapper_policy=load_ordered_subgraph_v2_policy(project_root / _MAPPER_POLICY),
    )


@pytest.fixture(scope="module")
def template_material(project_root: Path):
    payload = (project_root / _TEMPLATE).read_bytes()
    workbook, rows, snapshot = _load_template(
        payload,
        sheet_name="Sheet1",
        schema_row_count=77,
    )
    workbook.close()
    return payload, rows, snapshot


@pytest.fixture
def assembly_factory(
    tmp_path: Path,
    project_root: Path,
    template_material,
):
    counter = 0

    def assemble(mapping_authority, *, hostile_source_label: bool = False):
        nonlocal counter
        counter += 1
        run_root = tmp_path / f"run-{counter}"
        registry_directory = run_root / "registry"
        registry_directory.mkdir(parents=True)
        crop_payload = b"synthetic-crop-for-e0041-mechanism-test"
        source_payload = b"synthetic-registered-render-and-ocr-source"
        crop_path = registry_directory / "crop.bin"
        source_path = run_root / "registered-source.bin"
        crop_path.write_bytes(crop_payload)
        source_path.write_bytes(source_payload)
        crop_sha256 = hashlib.sha256(crop_payload).hexdigest()
        source_sha256 = hashlib.sha256(source_payload).hexdigest()

        postjoin = json.loads((project_root / _POSTJOIN).read_text(encoding="utf-8"))
        # These superseded fields are hostile on purpose. E0041 must never read
        # them to make or populate a mapping.
        for index, row in enumerate(postjoin["rows"]):
            row["mapping"] = {"selected_report_norm_id": 900000 + index}
            if hostile_source_label and index == 0:
                row["semantic_proposals"]["ppocrv6_source"] = "=1+1"
        for index, cell in enumerate(postjoin["cells"]):
            cell["selected_report_norm_id"] = 800000 + index
            cell["candidate_report_norm_ids"] = [800000 + index]
            cell["output_status"] = "VALUE"
            cell["selected_raw_value"] = "999999"
            cell["selected_normalized_value"] = "999999"
            cell["displayed_unit_value"] = "999999"
            cell["canonical_unit_value"] = 999999
            cell["numeric_evidence"]["crop_sha256"] = crop_sha256

        relative_source = source_path.relative_to(run_root).as_posix()
        geometry_cells = [
            {
                "cell_id": cell["cell_id"],
                "page": cell["page"],
                "row_ordinal": cell["row_ordinal"],
                "axis_ordinal": cell["axis_ordinal"],
                "crop_bbox": [1, 2, 101, 42],
                "crop_path": "crop.bin",
                "crop_sha256": crop_sha256,
                "crop_size_bytes": len(crop_payload),
                "source_row_ids": [f"registered-source:{cell['row_id']}"],
                "source_render_path": relative_source,
                "source_render_sha256": source_sha256,
                "source_ocr_path": relative_source,
                "source_ocr_sha256": source_sha256,
                "value_line_indices": [],
            }
            for cell in postjoin["cells"]
        ]
        geometry = {
            "format_version": 2,
            "policy": "FIXED_GRID_NUMERIC_CELL_CROPS_V2",
            "geometry_authority": "E0033_PP_OCRV6_FIXED_GRID",
            "reference_isolation": {
                "accounting_validation_invoked": False,
                "historical_or_mongodb_values_loaded": False,
                "human_review_loaded": False,
                "schema_mapping_invoked": False,
                "template_labels_or_report_norm_ids_loaded": False,
            },
            "cells": geometry_cells,
        }
        geometry_before = copy.deepcopy(geometry)
        control = yaml.safe_load((project_root / _CONTROL).read_text(encoding="utf-8"))
        synthetic_record = {"path": "synthetic", "sha256": "0" * 64, "size_bytes": 1}
        projection = assemble_post_mapping_projection(
            postjoin_payload=postjoin,
            mapping_payload=mapping_authority,
            geometry_registry=geometry,
            geometry_registry_path=registry_directory / "crop_registry.json",
            template_rows=template_material[1],
            project_root=run_root,
            input_records={
                "e0037_postjoin": synthetic_record,
                "mapping_challenger": synthetic_record,
                "geometry_registry": synthetic_record,
            },
            validation_config=control["accounting_validation"],
        )
        return projection, geometry == geometry_before

    return assemble


def _expected_sets(e0040_result) -> tuple[set[str], set[int]]:
    rows = {item.row_id for item in e0040_result.final_result.row_mappings}
    schema = {item.report_norm_id for item in e0040_result.final_result.schema_dispositions}
    return rows, schema


def test_control_freezes_physical_equations_and_does_not_overclaim_atomic_publication(
    project_root: Path,
):
    control = yaml.safe_load((project_root / _CONTROL).read_text(encoding="utf-8"))
    equations = control["accounting_validation"]["strict_physical_visible_row_equations"]

    assert equations["authority"] == "NEWLY_FROZEN_CALIBRATION_MECHANISM_ASSERTION"
    assert equations["mapping_independent_physical_row_ids"] is True
    assert equations["expected_family_count"] == 18
    assert equations["expected_finding_count"] == 36
    assert len(equations["equations"]) == 18
    assert all(
        not any("report_norm_id" in key.casefold() for key in equation)
        for equation in equations["equations"]
    )
    assert control["outputs"]["publication"] == (
        "FD_RELATIVE_EXCLUSIVE_NO_OVERWRITE_PAIR_WITH_HELD_DIRFD_ROLLBACK_"
        "AND_FRESH_CANONICAL_CHAIN_REVALIDATION"
    )
    assert control["outputs"]["publication_path_safety"] == {
        "trusted_project_root_dirfd": "O_DIRECTORY_NOFOLLOW",
        "output_chain_traversal": "COMPONENT_BY_COMPONENT_DIRFD_RELATIVE_NOFOLLOW",
        "writes_and_rollback": "HELD_OUTPUT_DIRFD_RELATIVE",
        "success_gate": "FRESH_CANONICAL_CHAIN_PARENT_AND_FILE_INODE_REVALIDATION",
    }
    assert control["state"] == ("MECHANISM_READY_FORMAL_CAPTURE_BLOCKED_PENDING_E0040_SEAL")
    assert control["formal_capture_gate"] == {
        "status": "BLOCKED_PENDING_AUTHENTICATED_E0040_ARTIFACT_AND_SEAL",
        "required_mapping_authority": "E0040_GENERIC_CALIBRATION_CHALLENGER",
        "authenticated_e0040_artifact_bound": False,
        "authenticated_e0040_seal_bound": False,
        "e0038_may_be_used_as_formal_mapping_authority": False,
    }
    assert control["outputs"]["formal_publication_allowed_before_e0040_seal"] is False
    assert "atomic_pair_publication" not in control["outputs"]
    assert control["workbook"]["deterministic_core_properties"] == {
        "creator": "bctc-ai/E-0041",
        "last_modified_by": "bctc-ai/E-0041",
        "created_utc": "2000-01-01T00:00:00Z",
        "modified_utc": "2000-01-01T00:00:00Z",
        "version": "1",
        "revision": "1",
        "optional_free_text_fields_cleared": True,
        "canonical_core_xml_sha256": (
            "a025959e8b178cfc6c6aae8f2d49d86fa305d3e36e165c8cbbc16923068668e4"
        ),
    }
    for name in ("e0037_postjoin", "cdkt_template"):
        record = control["inputs"][name]
        payload = (project_root / record["path"]).read_bytes()
        assert (record["sha256"], record["size_bytes"]) == (
            hashlib.sha256(payload).hexdigest(),
            len(payload),
        )


def test_e0040_direct_result_adapter_rejects_detached_and_forged_envelopes(e0040_result):
    expected_rows, expected_schema = _expected_sets(e0040_result)
    rows, _dispositions, aliases, authority = _validate_mapping_challenger(
        e0040_result,
        expected_row_ids=expected_rows,
        expected_schema_ids=expected_schema,
    )

    assert Counter(item["status"] for item in rows.values()) == {
        "RESOLVED_ANCHOR": 43,
        "RESOLVED_PATH": 18,
        "SOURCE_ONLY_STRUCTURAL_ROW": 3,
    }
    assert aliases == set()
    assert authority["final_selected_pair_count"] == 61
    assert authority["source_only_row_count"] == 3

    # A fully coordinated JSON envelope is still detached raw data, not direct
    # call provenance from the approved challenger implementation.
    coordinated_forgery = e0040_result.to_dict()
    coordinated_forgery["normalization"]["id_scoped_alias_invocation_count"] = 0
    coordinated_forgery["collision_audit"]["new_collision_pairs"] = ()
    with pytest.raises(E0041PostMappingExportError, match="direct-call authority"):
        _validate_mapping_challenger(
            coordinated_forgery,
            expected_row_ids=expected_rows,
            expected_schema_ids=expected_schema,
        )

    alias_forgery = replace(
        e0040_result,
        normalization=replace(
            e0040_result.normalization,
            id_scoped_alias_invocation_count=1,
        ),
    )
    with pytest.raises(E0041PostMappingExportError, match="authority is unsafe"):
        _validate_mapping_challenger(
            alias_forgery,
            expected_row_ids=expected_rows,
            expected_schema_ids=expected_schema,
        )

    forged_search = replace(e0040_result.final_result.search, pruned_states=1)
    pruning_forgery = replace(
        e0040_result,
        final_result=replace(e0040_result.final_result, search=forged_search),
    )
    with pytest.raises(E0041PostMappingExportError, match="was pruned"):
        _validate_mapping_challenger(
            pruning_forgery,
            expected_row_ids=expected_rows,
            expected_schema_ids=expected_schema,
        )


def test_projection_retains_128_physical_cells_and_matches_strict_oracle(
    assembly_factory,
    e0040_result,
):
    projection, geometry_unchanged = assembly_factory(e0040_result)
    metrics = projection["metrics"]

    assert geometry_unchanged is True
    assert metrics["source_row_count"] == 64
    assert metrics["physical_cell_count"] == 128
    assert metrics["selected_target_cell_count"] == 122
    assert metrics["exported_numeric_cell_count"] == 111
    assert metrics["physical_cell_status_counts"] == {
        "BLANK": 5,
        "DASH": 5,
        "UNRESOLVED": 7,
        "VALUE": 111,
    }
    cells = projection["physical_cells"]
    assert len({cell["cell_id"] for cell in cells}) == 128
    assert all(
        cell["exported_canonical_value"] is None for cell in cells if cell["status"] == "DASH"
    )
    assert all(cell["visible_raw_value"] == "-" for cell in cells if cell["status"] == "DASH")
    assert all(
        cell["exported_canonical_value"] is None
        for cell in cells
        if cell["status"] in {"BLANK", "AMBIGUOUS", "UNRESOLVED"}
    )

    source_only = [cell for cell in cells if cell["source_only"]]
    assert len(source_only) == 6
    assert all(cell["report_norm_id"] is None for cell in source_only)
    source_only_total = [
        cell for cell in source_only if cell["row_id"] == "page-0004-row-023-label"
    ]
    assert len(source_only_total) == 2
    assert all(cell["source_numeric_status"] == "VALUE" for cell in source_only_total)
    assert all(cell["evidence_canonical_value"] is not None for cell in source_only_total)
    assert all(cell["exported_canonical_value"] is None for cell in source_only_total)
    assert all(
        any(ref.startswith("P4_R023_VISIBLE_CHILDREN_ONLY") for ref in cell["validation_refs"])
        for cell in source_only_total
    )

    validation = projection["validation"]
    assert (
        validation["pre_validation_value_status_sha256"]
        == (validation["post_validation_value_status_sha256"])
    )
    assert validation["finding_counts"] == {"NOT_TESTABLE": 6, "PASS": 30}
    assert len(validation["findings"]) == 36
    assert validation["secondary_schema_hierarchy"] == {
        "enabled": False,
        "separate_denominator": True,
        "finding_count": 0,
        "findings": [],
        "finding_counts": {},
    }
    assert {
        finding["finding_id"]
        for finding in validation["findings"]
        if finding["result"] == "NOT_TESTABLE"
    } == {
        "P3_R018_CURRENT",
        "P3_R018_COMPARATIVE",
        "P3_R038_TOTAL_CURRENT",
        "P3_R038_TOTAL_COMPARATIVE",
        "P4_R007_CURRENT",
        "P4_R007_COMPARATIVE",
    }
    assert not any(finding["result"] == "FAIL" for finding in validation["findings"])


def test_physical_equation_injection_is_rejected(
    project_root: Path,
    assembly_factory,
    e0040_result,
):
    projection, _ = assembly_factory(e0040_result)
    control = yaml.safe_load((project_root / _CONTROL).read_text(encoding="utf-8"))
    forged = copy.deepcopy(control["accounting_validation"])
    forged["strict_physical_visible_row_equations"]["equations"][0]["rhs_row_ids"] = [
        "page-0003-row-007-label"
    ]

    with pytest.raises(E0041PostMappingExportError, match="does not contain 18 families"):
        export_module._diagnose_physical_visible_equations(
            projection["physical_cells"],
            forged,
        )


def test_e0038_alias_and_six_unselected_rows_fail_closed_without_changing_arithmetic(
    project_root: Path,
    assembly_factory,
    e0040_result,
):
    e0038 = json.loads((project_root / _E0038_MAPPING).read_text(encoding="utf-8"))
    e0038_projection, _ = assembly_factory(e0038)
    e0040_projection, _ = assembly_factory(e0040_result)
    exact = e0038["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]
    alias_rows = {
        row["row_id"]
        for row in exact["row_mappings"]
        if row["selected_report_norm_id"] in {4375, 5699}
    }
    unselected_rows = {
        row["row_id"] for row in exact["row_mappings"] if row["selected_report_norm_id"] is None
    }

    assert len(alias_rows) == 2
    assert len(unselected_rows) == 6
    by_row: dict[str, list[dict[str, object]]] = {}
    for cell in e0038_projection["physical_cells"]:
        by_row.setdefault(cell["row_id"], []).append(cell)
    assert all(
        cell["status"] == "AMBIGUOUS"
        and cell["report_norm_id"] is None
        and cell["exported_canonical_value"] is None
        for row_id in alias_rows
        for cell in by_row[row_id]
    )
    assert all(
        cell["status"] in {"AMBIGUOUS", "UNRESOLVED"}
        and cell["report_norm_id"] is None
        and cell["exported_canonical_value"] is None
        for row_id in unselected_rows
        for cell in by_row[row_id]
    )
    assert e0038_projection["metrics"]["selected_target_cell_count"] == 112
    assert (
        e0038_projection["validation"]["findings"] == (e0040_projection["validation"]["findings"])
    )


def test_duplicate_selected_target_is_rejected(project_root: Path):
    payload = json.loads((project_root / _E0038_MAPPING).read_text(encoding="utf-8"))
    result = payload["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]
    selected = [row for row in result["row_mappings"] if row["selected_report_norm_id"]]
    selected[1]["selected_report_norm_id"] = selected[0]["selected_report_norm_id"]
    selected[1]["candidate_report_norm_ids"] = [selected[0]["selected_report_norm_id"]]

    with pytest.raises(E0041PostMappingExportError, match="duplicate selected ReportNormId"):
        _validate_mapping_challenger(
            payload,
            expected_row_ids={row["row_id"] for row in result["row_mappings"]},
            expected_schema_ids={row["report_norm_id"] for row in result["schema_dispositions"]},
        )


def test_workbook_clones_template_and_writes_hostile_ocr_as_literal_text(
    assembly_factory,
    e0040_result,
    template_material,
    monkeypatch: pytest.MonkeyPatch,
):
    projection, _ = assembly_factory(e0040_result, hostile_source_label=True)
    from openpyxl.writer import excel as excel_writer

    clock = [datetime_module.datetime(2030, 1, 2, 3, 4, 5)]

    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            value = clock[0]
            return value.replace(tzinfo=tz) if tz is not None else value

    monkeypatch.setattr(
        excel_writer,
        "datetime",
        SimpleNamespace(datetime=FakeDateTime, timezone=datetime_module.timezone),
    )
    workbook_bytes, receipt = build_development_workbook(
        template_bytes=template_material[0],
        projection=projection,
    )
    clock[0] = datetime_module.datetime(2040, 6, 7, 8, 9, 10)
    repeated_bytes, repeated_receipt = build_development_workbook(
        template_bytes=template_material[0],
        projection=projection,
    )

    assert workbook_bytes == repeated_bytes
    assert receipt == repeated_receipt
    assert receipt["exact_template_identity_value_style_fidelity"] is True
    assert receipt["deterministic_core_properties_sha256"] == (
        "a025959e8b178cfc6c6aae8f2d49d86fa305d3e36e165c8cbbc16923068668e4"
    )
    with zipfile.ZipFile(BytesIO(workbook_bytes)) as archive:
        core = archive.read("docProps/core.xml")
    assert hashlib.sha256(core).hexdigest() == (
        "a025959e8b178cfc6c6aae8f2d49d86fa305d3e36e165c8cbbc16923068668e4"
    )
    assert core == export_module._DETERMINISTIC_CORE_PROPERTIES_XML
    workbook = load_workbook(BytesIO(workbook_bytes), data_only=False)
    try:
        assert workbook.sheetnames == [
            "Sheet1",
            "PROVENANCE",
            "VALIDATION_DIAGNOSTICS",
            "RUN_METADATA",
        ]
        assert workbook.properties.created == datetime_module.datetime(2000, 1, 1)
        assert workbook.properties.modified == datetime_module.datetime(2000, 1, 1)
        assert workbook.properties.creator == "bctc-ai/E-0041"
        assert workbook.properties.lastModifiedBy == "bctc-ai/E-0041"
        assert workbook.properties.version == "1"
        assert workbook.properties.revision == "1"
        assert not any(
            cell.data_type == "f"
            for sheet in workbook.worksheets
            for row in sheet.iter_rows()
            for cell in row
        )
        provenance = workbook["PROVENANCE"]
        headers = {cell.value: cell.column for cell in provenance[1]}
        hostile = provenance.cell(2, headers["SourceLabel"])
        assert hostile.value == "=1+1"
        assert hostile.data_type == "s"
        dash_cells = [
            provenance.cell(row, headers["VisibleRawValue"])
            for row in range(2, provenance.max_row + 1)
            if provenance.cell(row, headers["Status"]).value == "DASH"
        ]
        assert len(dash_cells) == 5
        assert all(cell.value == "-" and cell.data_type == "s" for cell in dash_cells)

        source = workbook["Sheet1"]
        dash_schema_rows = [
            row
            for row in range(2, source.max_row + 1)
            if source.cell(row, 6).value == "DASH" or source.cell(row, 7).value == "DASH"
        ]
        assert dash_schema_rows
        for row in dash_schema_rows:
            if source.cell(row, 6).value == "DASH":
                assert source.cell(row, 4).value is None
            if source.cell(row, 7).value == "DASH":
                assert source.cell(row, 5).value is None
    finally:
        workbook.close()


def test_stable_read_rejects_parent_swap_to_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    parent = tmp_path / "input"
    detached = tmp_path / "detached-input"
    replacement = tmp_path / "replacement"
    parent.mkdir()
    replacement.mkdir()
    target = parent / "payload.bin"
    target.write_bytes(b"same-bytes")
    (replacement / "payload.bin").write_bytes(b"same-bytes")
    original_read = export_module.os.read
    raced = False

    def racing_read(descriptor: int, size: int):
        nonlocal raced
        payload = original_read(descriptor, size)
        if payload and not raced:
            raced = True
            parent.rename(detached)
            parent.symlink_to(replacement.name, target_is_directory=True)
        return payload

    monkeypatch.setattr(export_module.os, "read", racing_read)
    with pytest.raises(E0041PostMappingExportError, match="trusted directory chain"):
        _stable_read(tmp_path, target, maximum_size=1024, name="race fixture")
    assert (detached / "payload.bin").read_bytes() == b"same-bytes"


def test_pair_publication_is_exclusive_and_never_overwrites(tmp_path: Path):
    output = tmp_path / "output"
    workbook, provenance = _publish_pair(
        tmp_path,
        output,
        "development.xlsx",
        "provenance.json",
        b"workbook-v1",
        b"provenance-v1",
    )
    with pytest.raises(E0041PostMappingExportError, match="refusing to overwrite"):
        _publish_pair(
            tmp_path,
            output,
            "development.xlsx",
            "provenance.json",
            b"workbook-v2",
            b"provenance-v2",
        )

    assert workbook.read_bytes() == b"workbook-v1"
    assert provenance.read_bytes() == b"provenance-v1"
    assert (
        export_module._sha256_bytes(provenance.read_bytes())
        == hashlib.sha256(b"provenance-v1").hexdigest()
    )


def test_pair_publication_rolls_back_both_files_after_output_directory_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output = tmp_path / "output"
    detached = tmp_path / "detached-output"
    original_write = export_module._write_exclusive_at

    def racing_write(parent_descriptor: int, filename: str, payload: bytes):
        identity = original_write(parent_descriptor, filename, payload)
        if filename == "provenance.json":
            output.rename(detached)
            output.mkdir()
        return identity

    monkeypatch.setattr(export_module, "_write_exclusive_at", racing_write)
    with pytest.raises(E0041PostMappingExportError, match="detached from canonical path"):
        _publish_pair(
            tmp_path,
            output,
            "development.xlsx",
            "provenance.json",
            b"workbook",
            b"provenance",
        )

    assert list(output.iterdir()) == []
    assert list(detached.iterdir()) == []
    assert not list(tmp_path.rglob("*.xlsx"))
    assert not list(tmp_path.rglob("*.json"))


def test_second_pair_write_failure_rolls_back_detached_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output = tmp_path / "output"
    detached = tmp_path / "detached-output"
    original_write = export_module._write_exclusive_at

    def failing_second_write(parent_descriptor: int, filename: str, payload: bytes):
        if filename == "development.xlsx":
            raise OSError("injected second-write failure")
        identity = original_write(parent_descriptor, filename, payload)
        output.rename(detached)
        output.mkdir()
        return identity

    monkeypatch.setattr(export_module, "_write_exclusive_at", failing_second_write)
    with pytest.raises(OSError, match="injected second-write failure"):
        _publish_pair(
            tmp_path,
            output,
            "development.xlsx",
            "provenance.json",
            b"workbook",
            b"provenance",
        )

    assert list(output.iterdir()) == []
    assert list(detached.iterdir()) == []
    assert not list(tmp_path.rglob("*.xlsx"))
    assert not list(tmp_path.rglob("*.json"))


def test_formal_capture_blocks_before_any_read_or_legacy_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("formal capture touched input or publication code")

    monkeypatch.setattr(export_module, "_load_control", forbidden)
    monkeypatch.setattr(export_module, "_clean_git_commit", forbidden)
    monkeypatch.setattr(export_module, "_read_verified_artifact", forbidden)
    monkeypatch.setattr(export_module, "_publish_pair", forbidden)

    with pytest.raises(
        E0041PostMappingExportError,
        match="blocked pending an authenticated E-0040 artifact and seal",
    ):
        export_module.capture_e0041_post_mapping_development_excel(tmp_path)
    assert list(tmp_path.iterdir()) == []
