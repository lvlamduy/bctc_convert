from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

import bctc_ai.export.tm_consolidated_production as production
from bctc_ai.export.tm_consolidated_development import (
    TM_CONSOLIDATED_SCHEMA_PROJECTION_SHA256,
    TM_CONSOLIDATED_TEMPLATE_SHA256,
    TMConsolidatedDevelopmentArtifacts,
    TMConsolidatedDevelopmentExportResult,
    build_tm_consolidated_development_artifacts,
)


@dataclass(frozen=True)
class _ActualRun:
    run_directory: Path
    assembly: production.TMConsolidatedProductionAssembly
    first: TMConsolidatedDevelopmentArtifacts
    second: TMConsolidatedDevelopmentArtifacts
    provenance: dict[str, object]


@dataclass(frozen=True)
class _DashEvidence:
    source_image_path: str
    crop_box: tuple[int, int, int, int]
    component_box: tuple[int, int, int, int]
    observation: str = "DASH"


@dataclass(frozen=True)
class _DashRow:
    visual_cell_evidence: tuple[_DashEvidence | None, ...]


@dataclass(frozen=True)
class _DashParsed:
    rows: tuple[_DashRow, ...]


@dataclass(frozen=True)
class _DashResult:
    dash_pixel_evidence_sha256: str


@pytest.fixture(scope="module")
def actual_production_run(
    project_root: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> _ActualRun:
    run_directory = tmp_path_factory.mktemp("tm-consolidated-production")
    assembly = production.assemble_mbb_tm_consolidated_production_results(
        project_root=project_root,
        run_directory=run_directory,
    )
    kwargs = {
        "template_path": assembly.schema_workbook_path,
        "workbook_name": production.TM_PRODUCTION_WORKBOOK_NAME,
        "schema": assembly.schema,
        "owner_inputs": assembly.owner_inputs,
        "policy": assembly.policy,
        "run_metadata": {
            "input_manifest_sha256": assembly.input_manifest_sha256,
            "render_manifest_sha256": assembly.render_manifest_sha256,
            "run_id": "pytest-no-write",
        },
    }
    first = build_tm_consolidated_development_artifacts(**kwargs)
    second = build_tm_consolidated_development_artifacts(**kwargs)
    return _ActualRun(
        run_directory=run_directory,
        assembly=assembly,
        first=first,
        second=second,
        provenance=json.loads(first.provenance_bytes),
    )


def test_production_contract_audit_pins_exact_27_actual_owner_apis(project_root: Path) -> None:
    contracts = production.audit_tm_consolidated_production_contracts(project_root)

    assert tuple(contracts) == production.TM_PRODUCTION_OWNER_KEYS
    assert len(contracts) == 27
    assert len(production.TM_PRODUCTION_PAGE_OWNER_KEYS) == 26
    assert production.TM_PRODUCTION_RENDER_PAGES == (*range(31, 55), 57, 58, 60, 61)
    assert all(not module.startswith("tests.") for module in contracts.values())


def test_actual_all_27_assembly_and_in_memory_export_are_exact_and_deterministic(
    actual_production_run: _ActualRun,
) -> None:
    run = actual_production_run
    assembly = run.assembly

    assert tuple(item.owner_key for item in assembly.owner_inputs) == (
        production.TM_PRODUCTION_OWNER_KEYS
    )
    assert len({id(item.result) for item in assembly.owner_inputs}) == 27
    assert assembly.policy.schema_workbook_sha256 == TM_CONSOLIDATED_TEMPLATE_SHA256
    assert assembly.policy.schema_projection_sha256 == TM_CONSOLIDATED_SCHEMA_PROJECTION_SHA256
    assert (
        assembly.input_sha256s[production.TM_PRODUCTION_SOURCE_PDF_RELATIVE_PATH.as_posix()]
        == production.TM_PRODUCTION_SOURCE_PDF_SHA256
    )
    assert (
        assembly.input_sha256s[production.TM_PRODUCTION_SCHEMA_WORKBOOK_RELATIVE_PATH.as_posix()]
        == TM_CONSOLIDATED_TEMPLATE_SHA256
    )

    assert run.first.schema_item_count == 1_712
    assert run.first.status_counts == {
        "MAPPED": 890,
        "NA": 23,
        "NOT_OBSERVED": 799,
    }
    assert run.first.observation_count == run.first.provenance_count == 1_250
    assert run.provenance["summary"]["value_status_counts"] == {
        "BLANK": 20,
        "DASH": 169,
        "VALUE": 1_061,
    }
    assert run.provenance["summary"]["validation_record_count"] == 850
    assert run.provenance["summary"]["validation_status_counts"] == {
        "NOT_TESTABLE_DASH_IS_NOT_ZERO": 170,
        "NOT_TESTABLE_TARGET_NOT_OBSERVED": 2,
        "PASS": 677,
        "PASS_ROUNDED_TO_NEAREST_MILLION": 1,
    }
    assert run.provenance["schema_identity"] == assembly.policy.schema_identity
    assert run.provenance["document_coverage"] == {
        "accounted_schema_item_count": 1_712,
        "accounted_source_row_count": 553,
        "ambiguous_schema_item_count": 0,
        "ambiguous_source_row_count": 0,
        "latest_schema_batch_item_count": 2,
        "mapped_latest_schema_batch_item_count": 0,
        "mapped_mixed_source_row_count": 38,
        "mapped_new_schema_item_count": 307,
        "mapped_new_source_row_count": 155,
        "mapped_reused_schema_item_count": 583,
        "mapped_reused_source_row_count": 300,
        "mapped_schema_item_count": 890,
        "mapped_source_row_count": 493,
        "new_schema_item_count": 327,
        "not_applicable_schema_item_count": 23,
        "not_observed_latest_schema_batch_item_count": 2,
        "not_observed_new_schema_item_count": 20,
        "not_observed_schema_item_count": 799,
        "observed_output_cell_count": 1_250,
        "source_category_counts": {"MAPPED": 493, "SOURCE_ONLY_VALIDATION": 60},
        "source_only_validation_row_count": 60,
        "source_status_counts": {
            "MAPPED_AUTOMATIC_SCOPED": 457,
            "MAPPED_STRUCTURAL_SCOPED": 9,
            "PARTIALLY_MAPPED_AUTOMATIC_SCOPED": 6,
            "PARTIAL_CELL_MAPPING": 2,
            "PARTIAL_TOTAL_COLUMN_MAPPING": 19,
            "SOURCE_ONLY_CONTEXT": 9,
            "SOURCE_ONLY_EXTERNAL_VALIDATION": 1,
            "SOURCE_ONLY_SUBTOTAL": 5,
            "SOURCE_ONLY_VALIDATION": 45,
        },
        "unaccounted_source_row_count": 0,
        "unresolved_or_review_source_row_count": 0,
        "unresolved_schema_item_count": 0,
        "narrative_evidence_counts": {
            "mapped_narrative_record_count": 1,
            "narrative_fact_count": 5,
            "narrative_mapped_assignment_count": 7,
            "narrative_quantity_count": 8,
            "narrative_record_count": 13,
            "narrative_value_count": 7,
        },
        "visible_source_cell_count": 1_659,
        "visible_source_row_count": 553,
        "visible_source_value_status_slot_count": 1_659,
        "visible_value_status_slots_by_owner": {
            owner_key: {
                "basis": (
                    "PAGE30_MAPPED_VALUE_COUNT_PLUS_VISIBLE_STRUCTURAL_BLANK_ROW_COUNT"
                    if owner_key == "page-0030"
                    else (
                        "PAGE31_EXTRACTED_VALUE_COUNT"
                        if owner_key == "page-0031"
                        else "MAPPER_DECLARED_FINANCIAL_SLOT_COUNT"
                    )
                ),
                "count": count,
            }
            for owner_key, count in {
                "page-0030": 40,
                "page-0031": 56,
                "pages-0032-0033": 176,
                "page-0034": 99,
                "page-0035": 26,
                "page-0036": 26,
                "pages-0037-0038": 145,
                "pages-0039-0040": 96,
                "page-0041": 57,
                "page-0042": 48,
                "page-0043": 50,
                "page-0044": 60,
                "page-0045": 24,
                "page-0046": 62,
                "page-0047": 42,
                "page-0048": 20,
                "page-0049": 28,
                "page-0050": 38,
                "page-0051": 18,
                "page-0052": 12,
                "page-0053": 72,
                "page-0054": 72,
                "page-0057": 160,
                "page-0058": 72,
                "page-0060": 140,
                "page-0061": 20,
            }.items()
        },
    }
    derived_1170 = [
        observation
        for observation in run.provenance["observations"]
        if observation["observation_origin"] == "DERIVED" and observation["report_norm_id"] == 1170
    ]
    assert len(derived_1170) == 2
    assert all(
        observation["derivation_component_report_norm_ids"] == [6024, 6025]
        and observation["derivation_method"] == "DERIVED_SUM_OF_EXPLICIT_PRINTED_CHILDREN_6024_6025"
        and observation["derivation_source_ids"]
        == ["page-0046:net_service:row-0015", "page-0046:net_service:row-0018"]
        for observation in derived_1170
    )
    direct_children = [
        observation
        for observation in run.provenance["observations"]
        if observation["report_norm_id"] in {6024, 6025}
    ]
    assert len(direct_children) == 4
    assert all(observation["observation_origin"] == "DIRECT" for observation in direct_children)
    assert not any(
        str(record["status"]).startswith("FAIL") for record in run.provenance["validation"]
    )
    assert run.first.workbook_bytes == run.second.workbook_bytes
    assert run.first.provenance_bytes == run.second.provenance_bytes


def test_verified_render_cache_is_reused_without_rendering(
    monkeypatch: pytest.MonkeyPatch,
    actual_production_run: _ActualRun,
) -> None:
    assembly = actual_production_run.assembly

    def forbidden_render(*_args, **_kwargs):
        raise AssertionError("verified render cache should have been reused")

    monkeypatch.setattr(production, "render_pages", forbidden_render)
    paths, manifest_sha256 = production._verified_cached_renders(
        source_pdf_path=assembly.source_pdf_path,
        source_pdf_sha256=production.TM_PRODUCTION_SOURCE_PDF_SHA256,
        render_directory=actual_production_run.run_directory / "renders-300dpi",
        pages=production.TM_PRODUCTION_RENDER_PAGES,
        dpi=production.TM_PRODUCTION_RENDER_DPI,
    )

    assert tuple(paths) == production.TM_PRODUCTION_RENDER_PAGES
    assert manifest_sha256 == assembly.render_manifest_sha256


def test_render_manifest_digest_is_run_directory_independent(
    actual_production_run: _ActualRun,
) -> None:
    manifest_path = actual_production_run.run_directory / "renders-300dpi" / "manifest.json"
    original = json.loads(manifest_path.read_bytes())
    relocated = json.loads(manifest_path.read_bytes())
    for record in relocated["pages"]:
        record["path"] = (Path("/different/verified/cache") / Path(record["path"]).name).as_posix()

    assert production._canonical_render_manifest_sha256(original) == (
        actual_production_run.assembly.render_manifest_sha256
    )
    assert production._canonical_render_manifest_sha256(relocated) == (
        actual_production_run.assembly.render_manifest_sha256
    )


def test_dash_evidence_normalization_removes_only_path_and_fails_closed() -> None:
    first = _DashParsed(
        rows=(
            _DashRow(
                visual_cell_evidence=(
                    _DashEvidence(
                        source_image_path="/first/cache/page-0048.png",
                        crop_box=(10, 20, 30, 40),
                        component_box=(15, 25, 28, 35),
                    ),
                )
            ),
        )
    )
    relocated = replace(
        first,
        rows=(
            replace(
                first.rows[0],
                visual_cell_evidence=(
                    replace(
                        first.rows[0].visual_cell_evidence[0],
                        source_image_path="/second/cache/page-0048.png",
                    ),
                ),
            ),
        ),
    )

    def normalize(parsed: _DashParsed) -> _DashResult:
        raw = production._raw_dash_pixel_evidence_sha256("page-0048", parsed)
        return production._canonicalize_dash_pixel_evidence("page-0048", parsed, _DashResult(raw))

    assert normalize(first) == normalize(relocated)
    changed_box = replace(
        first,
        rows=(
            replace(
                first.rows[0],
                visual_cell_evidence=(
                    replace(first.rows[0].visual_cell_evidence[0], crop_box=(11, 20, 30, 40)),
                ),
            ),
        ),
    )
    assert normalize(first) != normalize(changed_box)
    with pytest.raises(production.TMConsolidatedProductionError, match="hash drifted"):
        production._canonicalize_dash_pixel_evidence("page-0048", first, _DashResult("0" * 64))


def test_actual_artifacts_are_identical_across_verified_cache_directories(
    project_root: Path,
    tmp_path: Path,
    actual_production_run: _ActualRun,
) -> None:
    source_cache = actual_production_run.run_directory / "renders-300dpi"
    relocated_run = tmp_path / "relocated-run"
    relocated_cache = relocated_run / "renders-300dpi"
    relocated_cache.mkdir(parents=True)
    manifest = json.loads((source_cache / "manifest.json").read_bytes())
    for record in manifest["pages"]:
        source = Path(record["path"])
        destination = relocated_cache / source.name
        destination.hardlink_to(source)
        record["path"] = destination.as_posix()
    (relocated_cache / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    relocated = production.assemble_mbb_tm_consolidated_production_results(
        project_root=project_root,
        run_directory=relocated_run,
    )
    artifact = build_tm_consolidated_development_artifacts(
        template_path=relocated.schema_workbook_path,
        workbook_name=production.TM_PRODUCTION_WORKBOOK_NAME,
        schema=relocated.schema,
        owner_inputs=relocated.owner_inputs,
        policy=relocated.policy,
        run_metadata={
            "input_manifest_sha256": relocated.input_manifest_sha256,
            "render_manifest_sha256": relocated.render_manifest_sha256,
            "run_id": "pytest-no-write",
        },
    )

    assert relocated.render_manifest_sha256 == actual_production_run.assembly.render_manifest_sha256
    assert artifact.workbook_sha256 == actual_production_run.first.workbook_sha256
    assert artifact.provenance_sha256 == actual_production_run.first.provenance_sha256
    assert artifact.workbook_bytes == actual_production_run.first.workbook_bytes
    assert artifact.provenance_bytes == actual_production_run.first.provenance_bytes


def test_cli_requires_explicit_output_and_calls_production_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        production.build_cli_parser().parse_args([])

    captured = {}

    def fake_export(**kwargs):
        captured.update(kwargs)
        return TMConsolidatedDevelopmentExportResult(
            workbook_path=(Path(kwargs["output_directory"]) / "tm.xlsx").as_posix(),
            provenance_path=(Path(kwargs["output_directory"]) / "tm.json").as_posix(),
            workbook_sha256="a" * 64,
            provenance_sha256="b" * 64,
            workbook_size_bytes=1,
            provenance_size_bytes=1,
            schema_item_count=1_712,
            observation_count=1_250,
            provenance_count=1_250,
            status_counts={"MAPPED": 890},
        )

    monkeypatch.setattr(production, "export_mbb_tm_consolidated_production", fake_export)
    output_directory = tmp_path / "explicit-output"
    run_directory = tmp_path / "explicit-run"
    assert (
        production.main(
            (
                "--project-root",
                str(tmp_path),
                "--output-dir",
                str(output_directory),
                "--run-dir",
                str(run_directory),
                "--run-id",
                "test-run",
            )
        )
        == 0
    )

    assert captured["output_directory"] == output_directory.resolve()
    assert captured["run_directory"] == run_directory.resolve()
    assert captured["run_id"] == "test-run"
    assert "TM_SCHEMA_ITEMS=1712" in capsys.readouterr().out
