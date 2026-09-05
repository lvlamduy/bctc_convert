from __future__ import annotations

import copy
import importlib.util
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz
import pytest

from bctc_ai.evaluation.gemini_json_capital_contribution_dividend_income_family_v1 import (
    FAMILY_ID,
    SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
    SOURCE_REPAIR_POLICY,
    GeminiJsonCapitalContributionDividendIncomeFamilyV1Error,
    _apply_repairs_to_pages,
    _compile_source_repair_artifact,
    _standalone_long_term_leaf_evidence,
    build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1,
    coalesce_gemini_json_capital_contribution_dividend_income_document_v1,
    evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / (
    "scripts/experiments/"
    "run_gemini_json_capital_contribution_dividend_income_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family35_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64


def _adapter_page(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm 2025"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2024"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "29. Thu nhập từ góp vốn, mua cổ phần",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _adapter_record(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _adapter_evaluate(page: dict[str, Any]) -> dict[str, Any]:
    _topology, _evaluation, _schema, compiled = runner._compile_specs_v1()
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=[_adapter_record(page)], compiled_specs=compiled
    )
    assert cluster["status"].startswith("READY")
    receipt = (
        build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        )
    )
    return evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )


def _reseal_repair_artifact(value: dict[str, Any]) -> None:
    for repair in value["repairs"]:
        material = {key: item for key, item in repair.items() if key != "repair_id"}
        repair["repair_id"] = "gjccdifav1:repair:" + canonical_json_sha256_v1(
            material
        )
    value["repairs"].sort(
        key=lambda item: (
            item["source_binding"]["source_logical_name"],
            item["source_binding"]["physical_page"],
            item["repair_id"],
        )
    )
    material = {
        "family_id": value["family_id"],
        "format_version": value["format_version"],
        "repairs": value["repairs"],
        "review_policy": value["review_policy"],
    }
    value["overlay_id"] = "gjccdifav1:overlay:" + canonical_json_sha256_v1(
        material
    )


def test_standalone_ambiguous_long_term_leaf_retries_only_after_exact_closure() -> None:
    page = _adapter_page(
        [
            {
                "hierarchy_path_exact": [
                    "Cổ tức nhận được trong năm từ góp vốn, mua cổ phần"
                ],
                "label_exact": "Cổ tức nhận được trong năm từ góp vốn, mua cổ phần",
                "row_kind": "ITEM",
                "values_exact": ["10", "8"],
            },
            {
                "hierarchy_path_exact": ["Thu từ lợi nhuận công ty con chuyển về"],
                "label_exact": "Thu từ lợi nhuận công ty con chuyển về",
                "row_kind": "ITEM",
                "values_exact": ["3", "2"],
            },
            {
                "hierarchy_path_exact": ["Thu nhập góp vốn, mua cổ phần"],
                "label_exact": "Thu nhập góp vốn, mua cổ phần",
                "row_kind": "ITEM",
                "values_exact": ["7", "6"],
            },
            {
                "hierarchy_path_exact": ["Tổng cộng"],
                "label_exact": "Tổng cộng",
                "row_kind": "TOTAL",
                "values_exact": ["10", "8"],
            },
        ]
    )

    candidate = _adapter_evaluate(page)

    assert candidate["status"].startswith("READY")
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [
        cell["coefficient"]
        for cell in by_role["LONG_TERM_CAPITAL_DIVIDEND"]["values"]
    ] == [10, 8]
    assert {
        source_ref["label_exact"]
        for source_ref in by_role["LONG_TERM_CAPITAL_DIVIDEND"]["source_refs"]
    } == {
        "Thu từ lợi nhuận công ty con chuyển về",
        "Thu nhập góp vốn, mua cổ phần",
    }
    retry = candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ]["standalone_long_term_leaf_retry_receipt"]
    assert retry["status"] == "EXACT_SHARED_CLOSURE_RETRY_ACCEPTED"
    assert retry["evidence"]["row_kind"] == "ITEM"
    assert retry["evidence"]["source_values_exact"] == ["7", "6"]


def test_structural_carrier_with_same_label_is_never_retried_as_leaf() -> None:
    carrier = "Thu nhập góp vốn, mua cổ phần"
    page = _adapter_page(
        [
            {
                "hierarchy_path_exact": [carrier],
                "label_exact": carrier,
                "row_kind": "SUBTOTAL",
                "values_exact": ["10", "8"],
            },
            {
                "hierarchy_path_exact": [carrier, "+ Thu từ chứng khoán đầu tư"],
                "label_exact": "+ Thu từ chứng khoán đầu tư",
                "row_kind": "ITEM",
                "values_exact": ["7", "6"],
            },
            {
                "hierarchy_path_exact": [
                    carrier,
                    "+ Từ góp vốn, đầu tư dài hạn khác",
                ],
                "label_exact": "+ Từ góp vốn, đầu tư dài hạn khác",
                "row_kind": "ITEM",
                "values_exact": ["3", "2"],
            },
            {
                "hierarchy_path_exact": [carrier],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["10", "8"],
            },
        ]
    )

    candidate = _adapter_evaluate(page)

    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [
        cell["coefficient"]
        for cell in by_role["LONG_TERM_CAPITAL_DIVIDEND"]["values"]
    ] == [3, 2]
    adapter = candidate["closure_receipt"].get(
        "capital_contribution_dividend_income_adapter_receipt"
    )
    assert adapter is None or adapter["standalone_long_term_leaf_retry_receipt"] is None


def test_standalone_retry_rejects_descendant_duplicate_and_missing_exact_owner() -> None:
    base_rows = [
        {
            "hierarchy_path_exact": [
                "Cổ tức nhận được trong năm từ góp vốn, mua cổ phần"
            ],
            "label_exact": "Cổ tức nhận được trong năm từ góp vốn, mua cổ phần",
            "row_kind": "ITEM",
            "values_exact": ["10", "8"],
        },
        {
            "hierarchy_path_exact": ["Thu nhập góp vốn, mua cổ phần"],
            "label_exact": "Thu nhập góp vốn, mua cổ phần",
            "row_kind": "ITEM",
            "values_exact": ["10", "8"],
        },
        {
            "hierarchy_path_exact": ["Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["10", "8"],
        },
    ]
    _topology, _evaluation, _schema, compiled = runner._compile_specs_v1()

    descendant = _adapter_page(copy.deepcopy(base_rows))
    descendant["sections"][0]["tables"][0]["rows"].append(
        {
            "hierarchy_path_exact": [
                "Thu nhập góp vốn, mua cổ phần",
                "Một dòng con",
            ],
            "label_exact": "Một dòng con",
            "row_kind": "ITEM",
            "values_exact": ["1", "1"],
        }
    )
    duplicate = _adapter_page(copy.deepcopy(base_rows))
    duplicate["sections"][0]["tables"][0]["rows"].insert(
        2, copy.deepcopy(base_rows[1])
    )
    no_owner = _adapter_page(copy.deepcopy(base_rows))
    no_owner["sections"][0]["title_exact"] = "Một thuyết minh khác"
    region = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "section_id": "s1",
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }
    for page in (descendant, duplicate, no_owner):
        assert (
            _standalone_long_term_leaf_evidence(
                pages={VERSION_ID: page},
                regions=[region],
                compiled_specs=compiled,
            )
            is None
        )


def _fixture_page() -> dict[str, Any]:
    return {
        "sections": [
            {
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm 2025"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2024"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Thu nhập khác"],
                                "label_exact": "Thu nhập khác",
                                "row_kind": "ITEM",
                                "values_exact": [None, None],
                            }
                        ],
                    }
                ]
            }
        ]
    }


def _fixture_repair_artifact(*, cell_count: int = 2) -> dict[str, Any]:
    base_page = _fixture_page()
    effective_page = copy.deepcopy(base_page)
    for column_index in range(cell_count):
        effective_page["sections"][0]["tables"][0]["rows"][0][
            "values_exact"
        ][column_index] = "-"
    base_table = base_page["sections"][0]["tables"][0]
    effective_table = effective_page["sections"][0]["tables"][0]
    logical_name = "bank/2025/fixture.pdf"
    source_sha256 = "a" * 64
    source_size_bytes = 123
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(
        {
            "source_logical_name": logical_name,
            "source_sha256": source_sha256,
            "source_size_bytes": source_size_bytes,
        }
    )
    image_sha256 = "b" * 64
    source_binding = {
        "document_id": document_id,
        "image_sha256": image_sha256,
        "image_size_bytes": 456,
        "media_type": "image/png",
        "page_id": "",
        "physical_page": 1,
        "pixel_height": 100,
        "pixel_width": 100,
        "render_dpi": 300,
        "source_logical_name": logical_name,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
    }
    source_binding["page_id"] = "gfpstorev1:page:" + canonical_json_sha256_v1(
        {
            "document_id": document_id,
            "image_sha256": image_sha256,
            "image_size_bytes": 456,
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": 100,
            "pixel_width": 100,
            "render_dpi": 300,
        }
    )
    stored_sha256 = "c" * 64
    extraction_run_id = "gfpstorev1:run:" + "d" * 64
    version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
        {
            "canonical_json_sha256": stored_sha256,
            "extraction_run_id": extraction_run_id,
            "page_id": source_binding["page_id"],
        }
    )
    cells = []
    for column_index in range(cell_count):
        cells.append(
            {
                "after_exact": "-",
                "before_exact": None,
                "cell_id": f"r1:c{column_index + 1}",
                "column_header_path_exact": [
                    "Năm 2025" if column_index == 0 else "Năm 2024"
                ],
                "crop_bbox_pixels_xyxy": [
                    20 + column_index * 20,
                    20,
                    35 + column_index * 20,
                    35,
                ],
                "crop_rgb_sha256": str(column_index + 1) * 64,
                "row_hierarchy_path_exact": ["Thu nhập khác"],
                "row_label_exact": "Thu nhập khác",
                "visual_state": "PDF_RENDER_VISIBLE_LITERAL",
            }
        )
    repair = {
        "base_page_json_sha256": canonical_json_sha256_v1(base_page),
        "base_page_json_version_id": version_id,
        "cell_repairs": cells,
        "effective_page_json_sha256": canonical_json_sha256_v1(effective_page),
        "extraction_run_id": extraction_run_id,
        "repair_id": "",
        "repair_reason": "VISIBLE_PDF_TRANSCRIPTION_MISMATCH",
        "row_repairs": [],
        "source_binding": source_binding,
        "stored_canonical_json_sha256": stored_sha256,
        "table_ref": {
            "base_table_sha256": canonical_json_sha256_v1(base_table),
            "effective_table_sha256": canonical_json_sha256_v1(effective_table),
            "section_id": "s1",
            "table_id": "t1",
        },
        "visual_evidence": {
            "evidence_kind": "PDF_RENDER_VISIBLE_LITERAL",
            "render_mode": "PYMUPDF_RGB_300_DPI_ALPHA_FALSE",
            "reviewed_utc_date": "2026-09-04",
            "table_crop_bbox_pixels_xyxy": [10, 10, 90, 90],
            "table_crop_rgb_sha256": "e" * 64,
        },
    }
    value = {
        "family_id": FAMILY_ID,
        "format_version": SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION,
        "overlay_id": "",
        "repairs": [repair],
        "review_policy": SOURCE_REPAIR_POLICY,
    }
    _reseal_repair_artifact(value)
    return value


def _fixture_source_axis(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    repair = artifact["repairs"][0]
    source = repair["source_binding"]
    return {
        repair["base_page_json_version_id"]: {
            "document_id": source["document_id"],
            "physical_page": source["physical_page"],
            "source_logical_name": source["source_logical_name"],
            "source_sha256": source["source_sha256"],
        }
    }


def _fixture_pdf_repair(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    relative = Path("bank/2025/fixture.pdf")
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    document = fitz.open()
    page = document.new_page(width=72, height=72)
    page.insert_text((25, 36), "-")
    document.save(source)
    document.close()
    payload = source.read_bytes()
    with fitz.open(stream=payload, filetype="pdf") as opened:
        pixmap = opened[0].get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
    image = pixmap.tobytes("png")
    table_bbox = [0, 0, pixmap.width, pixmap.height]
    cell_bbox = [0, 0, max(1, pixmap.width // 2), max(1, pixmap.height // 2)]
    repair = {
        "cell_repairs": [
            {
                "crop_bbox_pixels_xyxy": cell_bbox,
                "crop_rgb_sha256": runner._crop_rgb_sha256(pixmap, cell_bbox),
            }
        ],
        "row_repairs": [],
        "source_binding": {
            "image_sha256": sha256(image).hexdigest(),
            "image_size_bytes": len(image),
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": pixmap.height,
            "pixel_width": pixmap.width,
            "render_dpi": 300,
            "source_logical_name": relative.as_posix(),
            "source_sha256": sha256(payload).hexdigest(),
            "source_size_bytes": len(payload),
        },
        "visual_evidence": {
            "table_crop_bbox_pixels_xyxy": table_bbox,
            "table_crop_rgb_sha256": runner._crop_rgb_sha256(pixmap, table_bbox),
        },
    }
    return source, repair


def _reseal_audit(value: dict[str, Any]) -> None:
    material = {key: item for key, item in value.items() if key != "audit_id"}
    value["audit_id"] = "gjccdifav1:audit:" + canonical_json_sha256_v1(material)


def _audit_fixture(*, strict: bool = False) -> dict[str, Any]:
    comparator = []
    additions = []
    legacy = []
    policy = runner.STRICT_RELEASE if strict else runner.DISJOINT_EXPANSION
    metrics = runner.PINNED_OLD140_METRICS if strict else runner.PINNED_FULL271_METRICS
    if strict:
        comparator = [
            {"disposition": "EXACT", "source_sha256": f"{index:064x}"}
            for index in range(
                runner.PINNED_STRICT_HISTORICAL_COMPARATOR_RECORD_COUNT
            )
        ]
        for index in range(runner.PINNED_STRICT_VISIBLE_PRIMARY_ROOT_ADDITION_COUNT):
            comparator[index]["disposition"] = (
                "EVIDENCE_SAFE_VISIBLE_PRIMARY_INCOME_STATEMENT_ROOT_ADDITION"
            )
            additions.append({"source_sha256": comparator[index]["source_sha256"]})
        legacy = [{"source_sha256": "f" * 64}]
    axes = {"historical_comparator": comparator}
    material = {
        "axes": axes,
        "axis_counts": {"historical_comparator": len(comparator)},
        "axis_sha256": {
            "historical_comparator": canonical_json_sha256_v1(comparator)
        },
        "family_id": FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": {"policy": policy},
        "implementation_refs": [],
        "legacy_blank_zero_comparator_projections": legacy,
        "metrics": copy.deepcopy(metrics),
        "repair_application": {"status": "PASS"},
        "repair_authentication_axis_sha256": "0" * 64,
        "repair_authentication_count": runner.REGISTERED_SOURCE_REPAIR_COUNT,
        "source_observation_contract": {"status": "PASS"},
        "spec_refs": {},
        "sweep_id": "fixture",
        "visible_primary_income_statement_root_additions": additions,
    }
    value = {**material, "audit_id": ""}
    _reseal_audit(value)
    return value


def test_shared_implementation_hash_pins_and_registered_repair_denominators() -> None:
    runner._assert_shared_pins_v1()
    _topology, _evaluation, _schema, compiled = runner._compile_specs_v1()
    overlay = compiled[
        "capital_contribution_dividend_income_source_repair_overlay"
    ]
    assert len(overlay["repairs"]) == runner.REGISTERED_SOURCE_REPAIR_COUNT
    assert sum(len(item["cell_repairs"]) for item in overlay["repairs"]) == (
        runner.REGISTERED_SOURCE_REPAIR_CELL_COUNT
    )
    assert {
        (cell["before_exact"], cell["after_exact"])
        for repair in overlay["repairs"]
        for cell in repair["cell_repairs"]
    } <= {
        (None, "-"),
        ("null", "-"),
        ("-ktCap", "-"),
        ("-ktCap-", "-"),
        ("‐", "-"),
        ("- roll: -", "-"),
        ("-带有横线-", "-"),
        ("-壮-", "-"),
        ("-壮-「-」? -", "-"),
    }


def test_corpus_policy_is_explicit_and_rejects_pre_2025_expansion() -> None:
    expansion = {
        "corpus_manifest_index_id": runner.PINNED_FULL271_INDEX_ID,
        "documents": [{"relative_path": "bank/2025/report.pdf"}],
    }
    runner._assert_corpus_policy_v1(expansion, policy=runner.DISJOINT_EXPANSION)
    historical = {
        "corpus_manifest_index_id": runner.PINNED_OLD140_INDEX_ID,
        "documents": [{"relative_path": "bank/2024/report.pdf"}],
    }
    runner._assert_corpus_policy_v1(historical, policy=runner.STRICT_RELEASE)

    expansion["documents"][0]["relative_path"] = "bank/2024/report.pdf"
    with pytest.raises(runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error):
        runner._assert_corpus_policy_v1(
            expansion, policy=runner.DISJOINT_EXPANSION
        )
    with pytest.raises(runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error):
        runner._assert_corpus_policy_v1(historical, policy="AUTO")


def test_source_repair_compiler_allows_only_literal_dash_and_bounded_crop() -> None:
    artifact = _fixture_repair_artifact(cell_count=1)
    assert _compile_source_repair_artifact(artifact)["overlay_id"] == artifact[
        "overlay_id"
    ]

    numeric = copy.deepcopy(artifact)
    numeric["repairs"][0]["cell_repairs"][0]["after_exact"] = "0"
    _reseal_repair_artifact(numeric)
    with pytest.raises(GeminiJsonCapitalContributionDividendIncomeFamilyV1Error):
        _compile_source_repair_artifact(numeric)

    outside = copy.deepcopy(artifact)
    outside["repairs"][0]["cell_repairs"][0]["crop_bbox_pixels_xyxy"] = [
        0,
        0,
        5,
        5,
    ]
    _reseal_repair_artifact(outside)
    with pytest.raises(
        GeminiJsonCapitalContributionDividendIncomeFamilyV1Error,
        match="outside its table crop",
    ):
        _compile_source_repair_artifact(outside)


def test_source_repair_duplicate_missing_extra_and_before_image_tamper_fail() -> None:
    artifact = _fixture_repair_artifact(cell_count=2)
    compiled_overlay = _compile_source_repair_artifact(artifact)
    version_id = artifact["repairs"][0]["base_page_json_version_id"]
    specs = {
        "capital_contribution_dividend_income_source_repair_overlay": (
            compiled_overlay
        )
    }
    pages, receipts = _apply_repairs_to_pages(
        page_json_by_version={version_id: _fixture_page()},
        source_by_version=_fixture_source_axis(artifact),
        compiled_specs=specs,
    )
    assert pages[version_id]["sections"][0]["tables"][0]["rows"][0][
        "values_exact"
    ] == ["-", "-"]
    assert len(receipts) == 1

    duplicate = copy.deepcopy(artifact)
    duplicate["repairs"][0]["cell_repairs"].append(
        copy.deepcopy(duplicate["repairs"][0]["cell_repairs"][0])
    )
    _reseal_repair_artifact(duplicate)
    with pytest.raises(GeminiJsonCapitalContributionDividendIncomeFamilyV1Error):
        _compile_source_repair_artifact(duplicate)

    missing = copy.deepcopy(artifact)
    missing["repairs"][0]["cell_repairs"].pop()
    _reseal_repair_artifact(missing)
    missing_overlay = _compile_source_repair_artifact(missing)
    with pytest.raises(
        GeminiJsonCapitalContributionDividendIncomeFamilyV1Error,
        match="effective table drifted",
    ):
        _apply_repairs_to_pages(
            page_json_by_version={version_id: _fixture_page()},
            source_by_version=_fixture_source_axis(missing),
            compiled_specs={
                "capital_contribution_dividend_income_source_repair_overlay": (
                    missing_overlay
                )
            },
        )

    one = _fixture_repair_artifact(cell_count=1)
    extra = copy.deepcopy(one)
    extra["repairs"][0]["cell_repairs"].append(
        copy.deepcopy(artifact["repairs"][0]["cell_repairs"][1])
    )
    _reseal_repair_artifact(extra)
    extra_overlay = _compile_source_repair_artifact(extra)
    with pytest.raises(
        GeminiJsonCapitalContributionDividendIncomeFamilyV1Error,
        match="effective table drifted",
    ):
        _apply_repairs_to_pages(
            page_json_by_version={version_id: _fixture_page()},
            source_by_version=_fixture_source_axis(extra),
            compiled_specs={
                "capital_contribution_dividend_income_source_repair_overlay": (
                    extra_overlay
                )
            },
        )

    drifted_page = _fixture_page()
    drifted_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "0"
    with pytest.raises(
        GeminiJsonCapitalContributionDividendIncomeFamilyV1Error,
        match="base page drifted",
    ):
        _apply_repairs_to_pages(
            page_json_by_version={version_id: drifted_page},
            source_by_version=_fixture_source_axis(artifact),
            compiled_specs=specs,
        )


def test_pdf_render_full_image_table_and_cell_crops_are_authenticated(
    tmp_path: Path,
) -> None:
    _source, repair = _fixture_pdf_repair(tmp_path)
    assert runner.authenticate_capital_contribution_dividend_income_source_repairs_v1(
        repairs=[repair], source_pdf_root=tmp_path
    ) == [repair]

    cases = [
        ("source_binding", "image_sha256", "page render drifted"),
        ("visual_evidence", "table_crop_rgb_sha256", "table crop drifted"),
    ]
    for owner, key, message in cases:
        tampered = copy.deepcopy(repair)
        tampered[owner][key] = "0" * 64
        with pytest.raises(
            runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
            match=message,
        ):
            runner.authenticate_capital_contribution_dividend_income_source_repairs_v1(
                repairs=[tampered], source_pdf_root=tmp_path
            )
    tampered = copy.deepcopy(repair)
    tampered["cell_repairs"][0]["crop_rgb_sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="cell crop drifted",
    ):
        runner.authenticate_capital_contribution_dividend_income_source_repairs_v1(
            repairs=[tampered], source_pdf_root=tmp_path
        )


def test_pdf_source_missing_traversal_and_byte_tamper_fail_closed(
    tmp_path: Path,
) -> None:
    source, repair = _fixture_pdf_repair(tmp_path)
    missing = copy.deepcopy(repair)
    missing["source_binding"]["source_logical_name"] = "missing.pdf"
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="path is unavailable",
    ):
        runner.authenticate_capital_contribution_dividend_income_source_repairs_v1(
            repairs=[missing], source_pdf_root=tmp_path
        )

    outside = tmp_path.parent / "outside.pdf"
    outside.write_bytes(source.read_bytes())
    traversal = copy.deepcopy(repair)
    traversal["source_binding"]["source_logical_name"] = "../outside.pdf"
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="path is unavailable",
    ):
        runner.authenticate_capital_contribution_dividend_income_source_repairs_v1(
            repairs=[traversal], source_pdf_root=tmp_path
        )

    bytes_tamper = copy.deepcopy(repair)
    bytes_tamper["source_binding"]["source_sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="PDF bytes drifted",
    ):
        runner.authenticate_capital_contribution_dividend_income_source_repairs_v1(
            repairs=[bytes_tamper], source_pdf_root=tmp_path
        )


def test_repair_application_requires_exact_unique_registered_axis() -> None:
    repair_id = "gjccdifav1:repair:" + "1" * 64
    source_sha256 = "2" * 64
    compiled = {
        "capital_contribution_dividend_income_source_repair_overlay": {
            "overlay_id": "gjccdifav1:overlay:" + "3" * 64,
            "repairs": [
                {
                    "repair_id": repair_id,
                    "source_binding": {"source_sha256": source_sha256},
                }
            ],
        }
    }

    def sweep(applied: list[str]) -> dict[str, Any]:
        return {
            "trials": [
                {
                    "candidates": [
                        {
                            "closure_receipt": {
                                "capital_contribution_dividend_income_adapter_receipt": {
                                    "source_repair_receipts": [
                                        {"repair_id": item} for item in applied
                                    ]
                                }
                            }
                        }
                    ],
                    "source_sha256": source_sha256,
                }
            ]
        }

    assert runner._repair_application_receipt_v1(
        sweep=sweep([repair_id]), compiled_specs=compiled
    )["status"] == "PASS"
    for applied in ([], [repair_id, repair_id], [repair_id, "unexpected"]):
        with pytest.raises(
            runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
            match="not exhaustive and unique",
        ):
            runner._repair_application_receipt_v1(
                sweep=sweep(applied), compiled_specs=compiled
            )


def test_audit_axis_identity_and_policy_specific_denominators_fail_closed() -> None:
    expansion = _audit_fixture()
    assert runner.validate_capital_contribution_dividend_income_audit_v1(
        expansion
    ) == expansion
    unsealed = copy.deepcopy(expansion)
    unsealed["axes"]["historical_comparator"].append({"disposition": "EXACT"})
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="axis seals drifted",
    ):
        runner.validate_capital_contribution_dividend_income_audit_v1(unsealed)

    invented = copy.deepcopy(expansion)
    invented["visible_primary_income_statement_root_additions"] = [
        {"source_sha256": "f" * 64}
    ]
    _reseal_audit(invented)
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="expansion audit comparator gates drifted",
    ):
        runner.validate_capital_contribution_dividend_income_audit_v1(invented)

    strict = _audit_fixture(strict=True)
    assert runner.validate_capital_contribution_dividend_income_audit_v1(
        strict
    ) == strict
    strict["visible_primary_income_statement_root_additions"].pop()
    _reseal_audit(strict)
    with pytest.raises(
        runner.RunGeminiJsonCapitalContributionDividendIncomeV1Error,
        match="strict audit comparator gates drifted",
    ):
        runner.validate_capital_contribution_dividend_income_audit_v1(strict)


def test_oracle_coefficients_preserve_current_comparative_order_and_types() -> None:
    assert runner._oracle_integer_coefficients_v1(
        {
            "values": [
                {"normalized_value": 2, "period_role": "COMPARATIVE"},
                {"normalized_value": 3, "period_role": "CURRENT"},
            ]
        }
    ) == [3, 2]
    assert runner._oracle_integer_coefficients_v1(
        {"values": [{"normalized_value": 3.0, "period_role": "CURRENT"}]}
    ) is None
