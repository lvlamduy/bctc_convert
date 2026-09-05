from __future__ import annotations

import argparse
import copy
import importlib.util
from hashlib import sha256
from pathlib import Path

import fitz
import pytest
from PIL import Image

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
    _checked_source_replay_adapter_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT
    / "scripts/experiments/"
    "run_gemini_json_cash_equivalents_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family40_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
FULL271_SPEC = (
    ROOT
    / "config/families/tm-cash-equivalents-pdf-residual-audit-full271-v1.json"
)
COMMON204_SPEC = (
    ROOT
    / "config/families/tm-cash-equivalents-pdf-residual-audit-common204-v1.json"
)


def _seal_residual(residual: dict) -> dict:
    material = {
        key: copy.deepcopy(value)
        for key, value in residual.items()
        if key != "residual_audit_id"
    }
    residual["residual_audit_id"] = (
        "gjcepdfv1:residual:" + canonical_json_sha256_v1(material)
    )
    return residual


def _residual_spec(residuals: list[dict]) -> dict:
    return {
        "corpus_manifest_index_id": "fixture-index",
        "family_id": runner.FAMILY_ID,
        "format_version": runner.PDF_RESIDUAL_FORMAT_VERSION,
        "residual_axis_sha256": canonical_json_sha256_v1(residuals),
        "residuals": residuals,
        "review_contract": copy.deepcopy(runner._PDF_REVIEW_CONTRACT),
    }


def _not_observed_residual(*, render_sha256: str = "1" * 64) -> dict:
    return _seal_residual(
        {
            "disposition": runner._NOT_OBSERVED_DISPOSITION,
            "document_ordinal": 1,
            "pdf_page_count": 1,
            "pdf_target_text_hit_axis": [],
            "reasons": [],
            "review_page_axis": [
                {
                    "page_json_version_id": "gfpstorev1:json:" + "2" * 64,
                    "pdf_page_render_sha256": render_sha256,
                    "physical_page": 1,
                }
            ],
            "selected_json_target_page_axis": [
                {
                    "page_json_version_id": "gfpstorev1:json:" + "2" * 64,
                    "physical_page": 1,
                }
            ],
            "source_logical_name": "bank/2025/report.pdf",
            "source_sha256": "3" * 64,
            "source_size_bytes": 100,
            "status": runner.generic.NOT_OBSERVED,
        }
    )


def test_runner_pins_shared_multitable_implementation() -> None:
    runner._assert_shared_pins_v1()


def test_shared_multitable_pin_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_sha256", lambda _path: "0" * 64)
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="shared implementation pin drifted",
    ):
        runner._assert_shared_pins_v1()


def test_family_compiler_binds_all_four_registered_inputs() -> None:
    topology = runner.generic._json(runner.TOPOLOGY_SPEC_PATH)
    evaluation = runner.generic._json(runner.EVALUATION_SPEC_PATH)
    schema = runner.generic._json(runner.SCHEMA_BINDING_SPEC_PATH)
    repairs = runner.generic._json(runner.SOURCE_REPAIR_PATH)
    compiled = runner.compile_gemini_json_cash_equivalents_family_specs_v1(
        topology, evaluation, schema, repairs
    )
    generic_compiled = runner.compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, schema
    )
    assert compiled["topology"]["family_id"] == runner.FAMILY_ID
    assert compiled["cash_equivalents_source_repairs"] == repairs["repairs"]
    assert len(compiled["cash_equivalents_source_repairs"]) == 9
    assert "cash_equivalents_source_repairs" not in generic_compiled


@pytest.mark.parametrize(
    ("path", "count", "not_observed_count", "unresolved_count"),
    [
        (FULL271_SPEC, 71, 65, 6),
        (COMMON204_SPEC, 54, 50, 4),
    ],
)
def test_registered_pdf_residual_specs_are_sealed_and_complete(
    path: Path,
    count: int,
    not_observed_count: int,
    unresolved_count: int,
) -> None:
    checked = runner._validate_pdf_residual_spec_v1(runner.generic._json(path))
    assert len(checked["residuals"]) == count
    assert sum(
        residual["status"] == runner.generic.NOT_OBSERVED
        for residual in checked["residuals"]
    ) == not_observed_count
    assert sum(
        residual["status"] == runner.generic.UNRESOLVED
        for residual in checked["residuals"]
    ) == unresolved_count


def test_pdf_residual_schema_and_identity_fail_closed() -> None:
    residual = _not_observed_residual()
    spec = _residual_spec([residual])
    assert runner._validate_pdf_residual_spec_v1(spec) == spec

    render_tamper = copy.deepcopy(spec)
    render_tamper["residuals"][0]["review_page_axis"][0][
        "pdf_page_render_sha256"
    ] = "0" * 64
    render_tamper["residual_axis_sha256"] = canonical_json_sha256_v1(
        render_tamper["residuals"]
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="record identity drifted",
    ):
        runner._validate_pdf_residual_spec_v1(render_tamper)

    disposition_tamper = copy.deepcopy(spec)
    disposition_tamper["residuals"][0]["disposition"] = (
        runner._UNRESOLVED_DISPOSITION
    )
    _seal_residual(disposition_tamper["residuals"][0])
    disposition_tamper["residual_axis_sha256"] = canonical_json_sha256_v1(
        disposition_tamper["residuals"]
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="status/disposition pairing is invalid",
    ):
        runner._validate_pdf_residual_spec_v1(disposition_tamper)

    hit_axis_tamper = copy.deepcopy(spec)
    hit_axis_tamper["residuals"][0]["pdf_target_text_hit_axis"] = [1]
    _seal_residual(hit_axis_tamper["residuals"][0])
    hit_axis_tamper["residual_axis_sha256"] = canonical_json_sha256_v1(
        hit_axis_tamper["residuals"]
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="record is invalid",
    ):
        runner._validate_pdf_residual_spec_v1(hit_axis_tamper)


def test_pdf_target_text_scan_normalizes_case_and_returns_physical_pages() -> None:
    pdf = fitz.open()
    first = pdf.new_page(width=300, height=200)
    first.insert_text((25, 50), "CASH   AND CASH EQUIVALENTS")
    second = pdf.new_page(width=300, height=200)
    second.insert_text((25, 50), "Unrelated accounting policy")
    try:
        assert runner._pdf_target_text_hit_axis_v1(pdf) == [1]
    finally:
        pdf.close()


def test_selected_json_target_scan_covers_every_declared_surface_kind() -> None:
    page_ids = [
        "gfpstorev1:json:" + digit * 64 for digit in ("a", "b", "c", "d", "e")
    ]
    pages = {
        page_ids[0]: {
            "sections": [{"title_exact": "Cash and cash equivalents"}]
        },
        page_ids[1]: {
            "sections": [{"narratives_exact": ["TIỀN VÀ TƯƠNG ĐƯƠNG TIỀN"]}]
        },
        page_ids[2]: {
            "sections": [
                {"tables": [{"title_exact": "Tiền và các khoản tương đương tiền"}]}
            ]
        },
        page_ids[3]: {
            "sections": [
                {
                    "tables": [
                        {
                            "rows": [
                                {
                                    "label_exact": (
                                        "Các khoản tương đương tiền cuối kỳ bao gồm"
                                    )
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        page_ids[4]: {"sections": [{"title_exact": "Unrelated policy"}]},
    }
    selected_axis = [
        {
            "document_ordinal": 8,
            "page_json_version_id": page_id,
            "physical_page": physical_page,
            "source_sha256": "f" * 64,
        }
        for physical_page, page_id in enumerate(page_ids, start=1)
    ]
    assert runner._selected_json_target_page_axis_v1(
        page_json_by_version=pages,
        selected_page_axis=selected_axis,
        document_ordinal=8,
        source_sha256="f" * 64,
    ) == [
        {"page_json_version_id": page_id, "physical_page": physical_page}
        for physical_page, page_id in enumerate(page_ids[:4], start=1)
    ]


def test_pdf_residual_authentication_allows_selected_frontier_pdf_count_difference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logical_name = "bank/2025/report.pdf"
    source_path = tmp_path / logical_name
    source_path.parent.mkdir(parents=True)
    pdf = fitz.open()
    page = pdf.new_page(width=200, height=200)
    page.insert_text((25, 50), "cash policy only")
    page = pdf.new_page(width=200, height=200)
    page.insert_text((25, 50), "unrelated policy")
    pdf.save(source_path)
    pdf.close()
    source_bytes = source_path.read_bytes()
    source_sha256 = sha256(source_bytes).hexdigest()
    with fitz.open(source_path) as opened:
        pixmap = opened[0].get_pixmap(
            matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False
        )
        render_sha256 = sha256(pixmap.tobytes("png")).hexdigest()
    page_id = "gfpstorev1:json:" + "4" * 64
    page_id_2 = "gfpstorev1:json:" + "6" * 64
    residual = _not_observed_residual(render_sha256=render_sha256)
    residual["pdf_page_count"] = 2
    residual["source_logical_name"] = logical_name
    residual["source_sha256"] = source_sha256
    residual["source_size_bytes"] = len(source_bytes)
    residual["review_page_axis"][0]["page_json_version_id"] = page_id
    residual["selected_json_target_page_axis"][0]["page_json_version_id"] = page_id
    _seal_residual(residual)
    spec = _residual_spec([residual])
    index = {
        "corpus_manifest_index_id": "fixture-index",
        "documents": [
            {
                # Composite PDFs can expose a smaller selected-JSON frontier than
                # their authenticated physical PDF page axis.
                "page_count": 7,
                "relative_path": logical_name,
                "source_ordinal": 1,
                "source_sha256": source_sha256,
                "source_size_bytes": len(source_bytes),
            }
        ],
    }
    selected_axis = [
        {
            "document_ordinal": 1,
            "page_json_version_id": page_id,
            "physical_page": 1,
            "source_sha256": source_sha256,
        },
        {
            "document_ordinal": 1,
            "page_json_version_id": page_id_2,
            "physical_page": 2,
            "source_sha256": source_sha256,
        },
    ]
    pages = {
        1: {
            page_id: {
                "sections": [{"title_exact": "Cash and cash equivalents"}]
            },
            page_id_2: {"sections": [{"title_exact": "Unrelated policy"}]},
        }
    }
    trials = [
        {
            "document_ordinal": 1,
            "reasons": [],
            "source_logical_name": logical_name,
            "source_sha256": source_sha256,
            "status": runner.generic.NOT_OBSERVED,
        }
    ]
    authenticated = runner._authenticate_pdf_residuals_v1(
        spec=spec,
        index=index,
        selected_page_axis=selected_axis,
        page_json_by_document=pages,
        trials=trials,
        source_pdf_root=tmp_path,
    )
    assert authenticated == [residual]

    registered_extra = copy.deepcopy(spec)
    registered_extra["residuals"][0]["selected_json_target_page_axis"].append(
        {"page_json_version_id": page_id_2, "physical_page": 2}
    )
    _seal_residual(registered_extra["residuals"][0])
    registered_extra["residual_axis_sha256"] = canonical_json_sha256_v1(
        registered_extra["residuals"]
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="selected JSON target page axis drifted",
    ):
        runner._authenticate_pdf_residuals_v1(
            spec=registered_extra,
            index=index,
            selected_page_axis=selected_axis,
            page_json_by_document=pages,
            trials=trials,
            source_pdf_root=tmp_path,
        )

    source_extra = copy.deepcopy(pages)
    source_extra[1][page_id_2]["sections"][0]["title_exact"] = (
        "Tiền và các khoản tương đương tiền"
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="selected JSON target page axis drifted",
    ):
        runner._authenticate_pdf_residuals_v1(
            spec=spec,
            index=index,
            selected_page_axis=selected_axis,
            page_json_by_document=source_extra,
            trials=trials,
            source_pdf_root=tmp_path,
        )

    drifted_trials = copy.deepcopy(trials)
    drifted_trials[0]["status"] = runner.generic.UNRESOLVED
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="source/trial binding drifted",
    ):
        runner._authenticate_pdf_residuals_v1(
            spec=spec,
            index=index,
            selected_page_axis=selected_axis,
            page_json_by_document=pages,
            trials=drifted_trials,
            source_pdf_root=tmp_path,
        )

    monkeypatch.setattr(runner, "_pdf_target_text_hit_axis_v1", lambda _pdf: [1])
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="target-text hit axis drifted",
    ):
        runner._authenticate_pdf_residuals_v1(
            spec=spec,
            index=index,
            selected_page_axis=selected_axis,
            page_json_by_document=pages,
            trials=trials,
            source_pdf_root=tmp_path,
        )


def test_source_repair_authentication_replays_full_page_and_rgb_crop(
    tmp_path: Path,
) -> None:
    logical_name = "bank/2025/repair.pdf"
    source_path = tmp_path / logical_name
    source_path.parent.mkdir(parents=True)
    pdf = fitz.open()
    page = pdf.new_page(width=200, height=200)
    page.insert_text((100, 100), "-")
    pdf.save(source_path)
    pdf.close()
    source_bytes = source_path.read_bytes()
    source_sha256 = sha256(source_bytes).hexdigest()
    with fitz.open(stream=source_bytes, filetype="pdf") as opened:
        rendered = runner.render_full_pdf_page_v1(
            opened[0], physical_page=1, dpi=300, source_sha256=source_sha256
        )
    with Image.open(runner.BytesIO(rendered.image)) as image:
        rgb = image.convert("RGB")
        bbox = [400, 380, 440, 430]
        crop = rgb.crop(tuple(bbox))
        render = {
            "image_sha256": sha256(rendered.image).hexdigest(),
            "image_size_bytes": len(rendered.image),
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": rgb.height,
            "pixel_width": rgb.width,
            "render_dpi": 300,
            "render_receipt_sha256": canonical_json_sha256_v1(rendered.receipt),
        }
        crop_evidence = {
            "bbox_pixels_xyxy": bbox,
            "pixel_height": crop.height,
            "pixel_width": crop.width,
            "rgb_sha256": sha256(crop.tobytes()).hexdigest(),
        }
    page_id = "gfpstorev1:json:" + "5" * 64
    repair = {
        "before_exact": None,
        "crop_evidence": crop_evidence,
        "locator": {
            "column_ordinal": 1,
            "page_json_version_id": page_id,
            "physical_page": 1,
            "row_ordinal": 1,
            "section_id": "s1",
            "table_id": "t1",
        },
        "render": render,
        "source": {
            "source_logical_name": logical_name,
            "source_sha256": source_sha256,
            "source_size_bytes": len(source_bytes),
        },
    }
    index = {
        "documents": [
            {
                "relative_path": logical_name,
                "source_ordinal": 1,
                "source_sha256": source_sha256,
                "source_size_bytes": len(source_bytes),
            }
        ]
    }
    selected_axis = [
        {
            "document_ordinal": 1,
            "page_json_version_id": page_id,
            "physical_page": 1,
            "source_sha256": source_sha256,
        }
    ]
    pages = {
        1: {
            page_id: {
                "sections": [{"tables": [{"rows": [{"values_exact": [None]}]}]}]
            }
        }
    }
    assert runner._authenticate_source_repairs_v1(
        repairs=[repair],
        index=index,
        selected_page_axis=selected_axis,
        page_json_by_document=pages,
        source_pdf_root=tmp_path,
    ) == [repair]

    tampered = copy.deepcopy(repair)
    tampered["crop_evidence"]["rgb_sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="render or crop evidence drifted",
    ):
        runner._authenticate_source_repairs_v1(
            repairs=[tampered],
            index=index,
            selected_page_axis=selected_axis,
            page_json_by_document=pages,
            source_pdf_root=tmp_path,
        )


def test_source_replay_loads_complete_frontier_before_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page_ids = tuple("gfpstorev1:json:" + value * 64 for value in ("6", "7"))
    selected_axis = [
        {
            "document_ordinal": 1,
            "page_json_version_id": page_id,
            "physical_page": ordinal,
            "source_sha256": "8" * 64,
        }
        for ordinal, page_id in enumerate(page_ids, start=1)
    ]
    raw = {"selected_page_axis": selected_axis}
    pages = {1: {page_id: {"sections": []} for page_id in page_ids}}
    expected_indexed = {"sealed": True}
    expected_trials = [{"trial": "sealed"}]
    observed: dict[str, object] = {}

    monkeypatch.setattr(runner.generic, "_json", lambda _path: {"repairs": []})
    monkeypatch.setattr(
        runner,
        "bind_gemini_json_cash_equivalents_source_repairs_v1",
        lambda compiled, _repairs: {**compiled, "bound": True},
    )
    monkeypatch.setattr(
        runner,
        "query_selected_multitable_hierarchical_family_regions_v1",
        lambda _database, **kwargs: raw,
    )

    def load_pages(_database: Path, *, selected_ids: list[str], **_kwargs: object):
        observed["selected_ids"] = selected_ids
        return pages

    monkeypatch.setattr(runner.generic, "_load_selected_pages_by_document", load_pages)

    def adapt(value: dict, *, page_json_by_document: dict, **_kwargs: object):
        assert value is raw
        assert page_json_by_document is pages
        assert list(page_json_by_document[1]) == list(page_ids)
        observed["adapted"] = True
        return expected_indexed, []

    monkeypatch.setattr(
        runner,
        "adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1",
        adapt,
    )
    monkeypatch.setattr(
        runner,
        "_build_trials_v1",
        lambda **kwargs: expected_trials,
    )
    actual = runner.replay_cash_equivalents_trials_from_source_v1(
        source_page_database=Path("fixture.sqlite3"),
        selected_page_json_version_ids=page_ids,
        compiled_specs={"generic": True},
        indexed_query_evidence=expected_indexed,
    )
    assert actual == expected_trials
    assert observed == {"adapted": True, "selected_ids": list(page_ids)}


def test_trial_builder_evaluates_and_replays_every_accepted_cluster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexed = {
        "accepted_clusters": [
            {"component_regions": [{"region": 1}], "document_ordinal": 1},
            {"component_regions": [{"region": 2}], "document_ordinal": 2},
        ]
    }
    pages = {1: {"page-1": {}}, 2: {"page-2": {}}}
    evaluated: list[int] = []
    replayed: list[int] = []

    monkeypatch.setattr(
        runner,
        "build_gemini_json_cash_equivalents_region_query_receipt_v1",
        lambda regions: {"region": regions[0]["region"]},
    )

    def evaluate(*, regions: list[dict], **_kwargs: object) -> dict:
        ordinal = regions[0]["region"]
        evaluated.append(ordinal)
        return {"candidate": ordinal}

    def replay(value: dict, *, regions: list[dict], **_kwargs: object) -> dict:
        ordinal = regions[0]["region"]
        assert value == {"candidate": ordinal}
        replayed.append(ordinal)
        return value

    monkeypatch.setattr(
        runner, "evaluate_gemini_json_cash_equivalents_family_cluster_v1", evaluate
    )
    monkeypatch.setattr(
        runner,
        "validate_gemini_json_cash_equivalents_family_candidate_replay_v1",
        replay,
    )
    monkeypatch.setattr(
        runner.generic,
        "_trials",
        lambda *, indexed, candidates_by_ordinal: [
            indexed,
            candidates_by_ordinal,
        ],
    )
    result = runner._build_trials_v1(
        indexed=indexed, pages=pages, compiled_specs={"compiled": True}
    )
    assert evaluated == replayed == [1, 2]
    assert result[1] == {1: {"candidate": 1}, 2: {"candidate": 2}}


def test_source_replay_rejects_different_adapted_query_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page_id = "gfpstorev1:json:" + "9" * 64
    raw = {
        "selected_page_axis": [
            {
                "document_ordinal": 1,
                "page_json_version_id": page_id,
                "physical_page": 1,
                "source_sha256": "a" * 64,
            }
        ]
    }
    monkeypatch.setattr(runner.generic, "_json", lambda _path: {"repairs": []})
    monkeypatch.setattr(
        runner,
        "bind_gemini_json_cash_equivalents_source_repairs_v1",
        lambda compiled, _repairs: compiled,
    )
    monkeypatch.setattr(
        runner,
        "query_selected_multitable_hierarchical_family_regions_v1",
        lambda *_args, **_kwargs: raw,
    )
    monkeypatch.setattr(
        runner.generic,
        "_load_selected_pages_by_document",
        lambda *_args, **_kwargs: {1: {page_id: {}}},
    )
    monkeypatch.setattr(
        runner,
        "adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1",
        lambda *_args, **_kwargs: ({"sealed": "different"}, []),
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="rebuilt different query evidence",
    ):
        runner.replay_cash_equivalents_trials_from_source_v1(
            source_page_database=Path("fixture.sqlite3"),
            selected_page_json_version_ids=(page_id,),
            compiled_specs={},
            indexed_query_evidence={"sealed": True},
        )


def test_source_replay_callback_is_bound_to_exact_runner_bytes() -> None:
    reference = runner.generic._file_ref(RUNNER_PATH, root=ROOT)
    checked, checked_ref = _checked_source_replay_adapter_v1(
        runner.replay_cash_equivalents_trials_from_source_v1,
        adapter_ref=reference,
        implementation_refs=[reference],
    )
    assert checked is runner.replay_cash_equivalents_trials_from_source_v1
    assert checked_ref == reference

    tampered = {**reference, "sha256": "0" * 64}
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="content reference does not authenticate",
    ):
        _checked_source_replay_adapter_v1(
            runner.replay_cash_equivalents_trials_from_source_v1,
            adapter_ref=tampered,
            implementation_refs=[tampered],
        )


def test_audit_validation_rejects_source_observation_violation() -> None:
    axes = {
        "pdf_residuals": [],
        "trials": [],
    }
    material = {
        "axes": axes,
        "axis_counts": {name: len(axis) for name, axis in axes.items()},
        "axis_sha256": {
            name: canonical_json_sha256_v1(axis) for name, axis in axes.items()
        },
        "family_id": runner.FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": {
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        "source_authentication_axis": [],
        "source_authentication_axis_sha256": canonical_json_sha256_v1([]),
        "source_observation_contract": {"status": "PASS", "violation_count": 0},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
    }
    audit = {
        **material,
        "audit_id": "gjceauditv1:audit:" + canonical_json_sha256_v1(material),
    }
    assert same_typed_json_v1(runner._validate_audit_v1(audit), audit)
    audit["source_observation_contract"]["status"] = "FAILED"
    audit["source_observation_contract"]["violation_count"] = 1
    audit_material = {key: value for key, value in audit.items() if key != "audit_id"}
    audit["audit_id"] = (
        "gjceauditv1:audit:" + canonical_json_sha256_v1(audit_material)
    )
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="audit content is invalid",
    ):
        runner._validate_audit_v1(audit)


def test_run_requires_disjoint_expansion() -> None:
    with pytest.raises(
        runner.RunGeminiJsonCashEquivalentsV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_implementation_refs_cover_family_and_frozen_shared_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.generic,
        "_file_ref",
        lambda path, root=None: {
            "path": str(path.relative_to(root)) if root is not None else str(path)
        },
    )
    paths = [
        item["path"] for item in runner._implementation_refs(runner.PDF_RESIDUAL_AUDIT_SPEC_PATH)
    ]
    assert paths == [
        "scripts/experiments/run_gemini_json_cash_equivalents_accounting_family_v1.py",
        "src/bctc_ai/evaluation/gemini_json_cash_equivalents_family_v1.py",
        "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py",
        "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py",
        "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py",
        "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        "config/families/tm-cash-equivalents-topology-v1.json",
        "config/families/tm-cash-equivalents-evaluation-v1.json",
        "config/families/tm-cash-equivalents-schema-binding-v1.json",
        "data/registered/gemini_json_cash_equivalents_source_repairs_v1.json",
        "config/families/tm-cash-equivalents-pdf-residual-audit-full271-v1.json",
    ]
