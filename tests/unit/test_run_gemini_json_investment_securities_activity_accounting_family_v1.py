from __future__ import annotations

import copy
import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import fitz
import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT
    / "scripts/experiments/"
    "run_gemini_json_investment_securities_activity_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family33_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
FULL271_SPEC = (
    ROOT
    / "config/families/"
    "tm-investment-securities-activity-pdf-residual-audit-full271-v1.json"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _synthetic_disjoint_historical_inputs() -> dict:
    source_sha256 = "f" * 64
    return {
        "compiled_specs": {"topology": {"family_id": runner.FAMILY_ID}},
        "index": {
            "corpus_manifest_index_id": "gjfccmiv1:index:" + "e" * 64,
            "documents": [{"source_sha256": source_sha256}],
        },
        "indexed": {
            "accepted_clusters": [{"document_ordinal": 1}],
            "selected_document_axis": [
                {"document_ordinal": 1, "source_sha256": source_sha256}
            ],
        },
        "selected_ids": ["gfpstorev1:json:synthetic"],
        "trials": [
            {
                "candidate_count": 1,
                "document_ordinal": 1,
                "source_sha256": source_sha256,
            }
        ],
    }


def _synthetic_valid_audit() -> dict:
    axes = {"pdf_residuals": [], "trials": []}
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
        "observation_contract": {"violation_count": 0},
        "source_authentication_axis": [],
        "source_authentication_axis_sha256": canonical_json_sha256_v1([]),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
    }
    return {
        **material,
        "audit_id": "gjisaauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def test_runner_pins_shared_multitable_implementation() -> None:
    runner._assert_shared_pins_v1()


def test_shared_multitable_pin_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_sha256", lambda _path: "0" * 64)
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesActivityV1Error,
        match="shared implementation pin drifted",
    ):
        runner._assert_shared_pins_v1()


def test_empty_pdf_residual_spec_seals_zero_terminal_residuals() -> None:
    checked = runner._validate_pdf_residual_spec_v1(_json(FULL271_SPEC))
    assert checked["corpus_manifest_index_id"] == (
        "gjfccmiv1:index:"
        "8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a"
    )
    assert checked["residuals"] == []


def test_pdf_residual_review_contract_tampering_fails_closed() -> None:
    tampered = _json(FULL271_SPEC)
    tampered["review_contract"]["render_contract"]["matrix"] = [3, 3]
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesActivityV1Error,
        match="PDF residual audit spec is invalid",
    ):
        runner._validate_pdf_residual_spec_v1(tampered)


def test_current_corpus_scope_rejects_pre_2025_documents() -> None:
    runner._assert_current_corpus(
        {"documents": [{"relative_path": "vietstock_bctc/BANK/2025/report.pdf"}]}
    )
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesActivityV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus(
            {
                "documents": [
                    {"relative_path": "vietstock_bctc/BANK/2024/report.pdf"}
                ]
            }
        )


def test_source_repair_render_authentication_and_tamper_gate(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Family 33 visible source token: -")
    document.save(source_path)
    document.close()
    payload = source_path.read_bytes()
    source_sha256 = sha256(payload).hexdigest()
    with fitz.open(stream=payload, filetype="pdf") as pdf:
        pixmap = pdf[0].get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
        image = pixmap.tobytes("png")
    repair = {
        "page_image": {
            "height": pixmap.height,
            "media_type": "image/png",
            "render_dpi": 300,
            "sha256": sha256(image).hexdigest(),
            "size_bytes": len(image),
            "width": pixmap.width,
        },
        "page_json_version_id": "gfpstorev1:json:" + "a" * 64,
        "physical_page": 1,
        "repair_id": "gjisarv1:repair:" + "b" * 64,
        "source_logical_name": source_path.name,
        "source_sha256": source_sha256,
        "source_size_bytes": len(payload),
    }
    index = {
        "documents": [
            {
                "relative_path": source_path.name,
                "source_sha256": source_sha256,
                "source_size_bytes": len(payload),
            }
        ]
    }
    selected_page_axis = [
        {
            "page_json_version_id": repair["page_json_version_id"],
            "physical_page": 1,
            "source_sha256": source_sha256,
        }
    ]
    authenticated = runner._authenticate_source_repairs_v1(
        repairs=[repair],
        index=index,
        selected_page_axis=selected_page_axis,
        source_pdf_root=tmp_path,
    )
    assert [item["repair_id"] for item in authenticated] == [repair["repair_id"]]

    tampered = copy.deepcopy(repair)
    tampered["page_image"]["sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesActivityV1Error,
        match="source-repair PDF render drifted",
    ):
        runner._authenticate_source_repairs_v1(
            repairs=[tampered],
            index=index,
            selected_page_axis=selected_page_axis,
            source_pdf_root=tmp_path,
        )


def test_historical_policy_authenticates_disjoint_oracles() -> None:
    references, receipt = runner._historical_policy_receipt_v1(
        **_synthetic_disjoint_historical_inputs()
    )
    assert len(references) == 2
    assert receipt["policy"] == runner.DISJOINT_EXPANSION
    assert receipt["disposition"] == runner.NOT_APPLICABLE_DISJOINT_CORPUS
    assert receipt["oracle_authentication"]["source_count"] == 16
    assert receipt["corpus_relation"]["overlap_count"] == 0
    assert receipt["comparison_axis"] == []


def test_historical_policy_rejects_partial_oracle_overlap() -> None:
    arguments = _synthetic_disjoint_historical_inputs()
    first_oracle = runner.generic._historical_oracles(
        compiled_specs=arguments["compiled_specs"]
    )[0][1]
    source_sha256 = first_oracle["trials"][0]["source_pdf_sha256"]
    arguments["index"]["documents"][0]["source_sha256"] = source_sha256
    arguments["indexed"]["selected_document_axis"][0][
        "source_sha256"
    ] = source_sha256
    arguments["trials"][0]["source_sha256"] = source_sha256
    with pytest.raises(Exception, match="overlap only partially"):
        runner._historical_policy_receipt_v1(**arguments)


def test_audit_axis_or_identity_tampering_fails_closed() -> None:
    audit = _synthetic_valid_audit()
    assert runner._validate_audit_v1(audit) == audit

    tampered = copy.deepcopy(audit)
    tampered["axes"]["trials"].append({"status": runner.generic.READY})
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesActivityV1Error,
        match="audit content is invalid",
    ):
        runner._validate_audit_v1(tampered)

    resealed = copy.deepcopy(audit)
    resealed["state"] = "TAMPERED"
    resealed_material = {
        key: copy.deepcopy(value)
        for key, value in resealed.items()
        if key != "audit_id"
    }
    resealed["audit_id"] = (
        "gjisaauditv1:audit:" + canonical_json_sha256_v1(resealed_material)
    )
    with pytest.raises(
        runner.RunGeminiJsonInvestmentSecuritiesActivityV1Error,
        match="audit content is invalid",
    ):
        runner._validate_audit_v1(resealed)
