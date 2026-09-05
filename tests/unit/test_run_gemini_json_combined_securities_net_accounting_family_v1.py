from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import pytest

from scripts.experiments import (
    run_gemini_json_combined_securities_net_accounting_family_v1 as runner,
)

ROOT = Path(__file__).resolve().parents[2]
FULL271_SPEC = (
    ROOT
    / "config/families/tm-combined-securities-net-pdf-residual-audit-full271-v1.json"
)
COMMON204_SPEC = (
    ROOT
    / "config/families/tm-combined-securities-net-pdf-residual-audit-common204-v1.json"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def test_runner_pins_shared_multitable_implementation() -> None:
    runner._assert_shared_pins_v1()


def test_shared_pin_drift_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_sha256", lambda _path: "0" * 64)
    with pytest.raises(
        runner.RunGeminiJsonCombinedSecuritiesNetV1Error,
        match="shared implementation pin drifted",
    ):
        runner._assert_shared_pins_v1()


def test_current_corpus_and_historical_policy_fail_closed() -> None:
    with pytest.raises(
        runner.RunGeminiJsonCombinedSecuritiesNetV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus_v1(
            {"documents": [{"relative_path": "bank/2024/report.pdf"}]}
        )
    with pytest.raises(
        runner.RunGeminiJsonCombinedSecuritiesNetV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


@pytest.mark.parametrize(
    ("path", "document_count", "page_count", "image_only_count"),
    [
        (FULL271_SPEC, 271, 306, 121),
        (COMMON204_SPEC, 204, 230, 86),
    ],
)
def test_pdf_residual_specs_exhaust_every_reviewed_source(
    path: Path,
    document_count: int,
    page_count: int,
    image_only_count: int,
) -> None:
    checked = runner._validate_pdf_residual_spec_v1(_json(path))
    assert len(checked["residuals"]) == document_count
    assert sum(len(item["review_page_axis"]) for item in checked["residuals"]) == page_count
    assert (
        sum(item["extractable_text_page_count"] == 0 for item in checked["residuals"])
        == image_only_count
    )
    assert all(item["pdf_text_target_hit_pages"] == [] for item in checked["residuals"])


def test_pdf_residual_tamper_and_arithmetic_disposition_fail_closed() -> None:
    render_tamper = _json(FULL271_SPEC)
    render_tamper["residuals"][0]["review_page_axis"][0][
        "pdf_page_render_sha256"
    ] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonCombinedSecuritiesNetV1Error,
        match="identity drifted",
    ):
        runner._validate_pdf_residual_spec_v1(render_tamper)

    invented = _json(FULL271_SPEC)
    invented["residuals"][0]["disposition"] = "SUM_FAMILY32_AND_FAMILY33"
    with pytest.raises(
        runner.RunGeminiJsonCombinedSecuritiesNetV1Error,
        match="invalid or unordered",
    ):
        runner._validate_pdf_residual_spec_v1(invented)


def test_pdf_candidate_pattern_is_direct_presentation_sensitive() -> None:
    exact = runner._normalize_pdf_text_v1(
        "Lãi/(Lỗ) thuần từ chứng khoán kinh doanh và chứng khoán đầu tư"
    )
    separate = runner._normalize_pdf_text_v1(
        "Lãi thuần từ mua bán chứng khoán kinh doanh\n"
        "Lãi thuần từ mua bán chứng khoán đầu tư"
    )
    assert any(pattern.search(exact) for pattern in runner._PDF_TARGET_PATTERNS)
    # A whole-page text scan deliberately treats nearby separate lines as a
    # candidate that requires pixel review; it never promotes them to a sum.
    assert any(pattern.search(separate) for pattern in runner._PDF_TARGET_PATTERNS)


def test_audit_requires_disjoint_history_zero_observation_violations() -> None:
    sweep = {
        "metrics": {
            "document_count": 2,
            "mapping_count": 0,
            "not_observed_count": 2,
            "ready_count": 0,
            "unresolved_count": 0,
        },
        "sweep_id": "gjfafsv1:sweep:" + "1" * 64,
    }
    indexed = {"query_receipt": {"selected_document_count": 2}}
    trials = [
        {"candidate_count": 0, "candidates": [], "status": runner.generic.NOT_OBSERVED},
        {"candidate_count": 0, "candidates": [], "status": runner.generic.NOT_OBSERVED},
    ]
    receipt = {
        "corpus_relation": {"overlap_count": 0},
        "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
        "policy": runner.DISJOINT_EXPANSION,
    }
    audit = runner.build_combined_securities_net_experimental_audit_v1(
        sweep=sweep,
        output=Path("family34.json"),
        indexed=indexed,
        trials=trials,
        pdf_residuals=[{"ordinal": 1}, {"ordinal": 2}],
        historical_receipt=receipt,
        observation_contract={"status": "PASS", "violation_count": 0},
        spec_refs={},
    )
    assert runner.validate_combined_securities_net_experimental_audit_v1(audit)

    violated = copy.deepcopy(audit)
    violated["source_observation_contract"]["violation_count"] = 1
    with pytest.raises(
        runner.RunGeminiJsonCombinedSecuritiesNetV1Error,
        match="audit content is invalid",
    ):
        runner.validate_combined_securities_net_experimental_audit_v1(violated)
