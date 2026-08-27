from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_flat_accounting_family_v1 import _specs

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (
    GeminiFamilyEffectivePageFrontierV1Error,
    apply_gemini_family_effective_page_frontier_v1,
    build_gemini_family_effective_page_frontier_v1,
)


def _ref(name: str, digit: str) -> dict:
    return {"path": name, "sha256": digit * 64, "size_bytes": 123}


def _replacement(base: str, selected: str) -> dict:
    return {
        "base_page_json_version_id": base,
        "candidate_id": "gjfafcv1:candidate:" + "3" * 64,
        "document_ordinal": 4,
        "physical_page": 37,
        "repair_id": "gjfrrv1:repair:" + "4" * 64,
        "repair_job_id": "gjfrrqv1:job:" + "5" * 64,
        "repair_receipt_sha256": "6" * 64,
        "selected_page_json_version_id": selected,
    }


def test_effective_page_frontier_replaces_only_exact_selected_versions() -> None:
    base = ["gfpstorev1:json:" + digit * 64 for digit in "12"]
    selected = "gfpstorev1:json:" + "7" * 64
    value = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        base_page_json_version_ids=base,
        database_ref=_ref("store.sqlite3", "9"),
        family_id="TRADING_SECURITIES",
        job_status_counts={"ABSTAINED": 0, "RESOLVED": 1},
        repair_source_family_run_id="gjfafstorev1:run:" + "a" * 64,
        replacements=[_replacement(base[0], selected)],
        results_database_ref=_ref("families.sqlite3", "b"),
    )
    checked, effective = apply_gemini_family_effective_page_frontier_v1(
        value, base_page_json_version_ids=base
    )
    assert checked == value
    assert effective == [selected, base[1]]

    tampered = deepcopy(value)
    tampered["replacements"][0]["physical_page"] = 38
    with pytest.raises(GeminiFamilyEffectivePageFrontierV1Error, match="does not replay"):
        apply_gemini_family_effective_page_frontier_v1(tampered, base_page_json_version_ids=base)


def test_effective_page_frontier_preserves_identity_repair_observation() -> None:
    base = ["gfpstorev1:json:" + "1" * 64]
    value = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        base_page_json_version_ids=base,
        database_ref=_ref("store.sqlite3", "9"),
        family_id="TRADING_SECURITIES",
        job_status_counts={"ABSTAINED": 0, "RESOLVED": 1},
        repair_source_family_run_id="gjfafstorev1:run:" + "a" * 64,
        replacements=[_replacement(base[0], base[0])],
        results_database_ref=_ref("families.sqlite3", "b"),
    )
    assert (
        apply_gemini_family_effective_page_frontier_v1(value, base_page_json_version_ids=base)[1]
        == base
    )

    topology, evaluation, schema = _specs()
    family_frontier = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        base_page_json_version_ids=base,
        database_ref=_ref("store.sqlite3", "9"),
        family_id=topology["family_id"],
        job_status_counts={"ABSTAINED": 0, "RESOLVED": 1},
        repair_source_family_run_id="gjfafstorev1:run:" + "a" * 64,
        replacements=[_replacement(base[0], base[0])],
        results_database_ref=_ref("families.sqlite3", "b"),
    )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[{"document_ordinal": 1, "mappings": [], "status": UNRESOLVED}],
        effective_page_frontier=family_frontier,
    )
    assert sweep["effective_page_frontier"] == family_frontier
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
