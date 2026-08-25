from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as subject
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.accounting_family_coextensive_parent_total_v1 import (
    project_accounting_family_coextensive_parent_total_region_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _spec() -> dict:
    return {
        "children": [
            {
                "matchers": [{"aliases": ["Tiền gửi TCTD khác"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [{"aliases": ["Cho vay TCTD khác"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "LOAN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [{"aliases": ["Bằng VND"], "within_role": "LOAN_GROUP"}],
                "presence": "OPTIONAL",
                "role": "LOAN_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [
                    {
                        "aliases": [
                            "Tiền gửi và cho vay TCTD khác",
                            "Tổng tiền gửi và cho vay TCTD khác",
                        ],
                        "within_role": None,
                    }
                ],
                "presence": "OPTIONAL",
                "role": "FAMILY_TOTAL",
                "role_kind": "TOTAL",
            },
        ],
        "family_id": "INTERBANK_ASSET",
        "format_version": topology_v1.SPEC_FORMAT_VERSION_V3,
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 0,
            "max_label_line_span": 1,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK_ASSET",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": [],
    }


def _line(index: int, text: str) -> dict:
    return {
        "bbox": [50, 80 + index * 34, 650, 104 + index * 34],
        "source_line_index": index,
        "source_text": None,
        "vietocr_text": text,
    }


def _pages(*, detail_first: bool = False) -> list[dict]:
    summary = [
        "Tiền gửi và cho vay TCTD khác",
        "Tiền gửi TCTD khác",
        "Cho vay TCTD khác",
    ]
    detail = [
        "Tiền gửi và cho vay TCTD khác",
        "Tiền gửi TCTD khác",
        "Cho vay TCTD khác",
        "Bằng VND",
    ]
    labels = [*detail, *summary] if detail_first else [*summary, *detail]
    return [
        {
            "lines": [_line(index, text) for index, text in enumerate(labels)],
            "page_sequence": 1,
        }
    ]


def test_prepruning_axis_retains_summary_and_detail_while_v1_stays_sealed() -> None:
    topology_path = _PROJECT_ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py"
    payload = topology_path.read_bytes()
    assert len(payload) == 75_614
    assert hashlib.sha256(payload).hexdigest() == (
        "5ef1890af46826e6ac7cfd10b88e136878fbb4ad569abdb78452ad8fde60da7e"
    )
    legacy = topology_v1.build_accounting_family_topology_scan_v1(_pages(), _spec())
    result = subject.build_accounting_family_topology_candidates_v2(_pages(), _spec())

    assert [region["observed_roles"] for region in legacy["regions"]] == [
        ["DEPOSIT_GROUP", "LOAN_GROUP", "LOAN_VND"]
    ]
    assert [region["observed_roles"] for region in result["regions"]] == [
        ["DEPOSIT_GROUP", "LOAN_GROUP"],
        ["DEPOSIT_GROUP", "LOAN_GROUP", "LOAN_VND"],
    ]
    assert result["metrics"]["legacy_pruned_complete_region_count"] == 1
    assert result["input_binding"]["legacy_topology_scan_id"] == legacy["scan_id"]
    assert result["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"


def test_provider_candidate_order_is_source_deterministic_not_role_richness_order() -> None:
    result = subject.build_accounting_family_topology_candidates_v2(
        _pages(detail_first=True),
        _spec(),
    )

    assert [region["cluster_start_document_line_ordinal"] for region in result["regions"]] == [0, 4]
    assert result == subject.build_accounting_family_topology_candidates_v2(
        _pages(detail_first=True),
        _spec(),
    )
    assert (
        subject.validate_accounting_family_topology_candidates_replay_v2(
            result,
            _pages(detail_first=True),
            _spec(),
        )
        == result
    )


def test_bound_candidate_replays_occurrences_and_projects_exact_owner_total() -> None:
    pages = _pages()
    spec = _spec()
    result = subject.build_accounting_family_topology_candidates_v2(pages, spec)
    summary, detail = result["regions"]

    bound = subject.bind_accounting_family_topology_candidate_v2(
        pages,
        spec,
        result,
        summary,
    )

    assert [item["role"] for item in bound["role_occurrences"]] == [
        "DEPOSIT_GROUP",
        "LOAN_GROUP",
    ]
    projected = bound["effective_topology_region"]
    parent = projected["parent_match"]
    owner_total = next(
        item for item in projected["child_matches"] if item["role"] == "FAMILY_TOTAL"
    )
    assert (
        owner_total["document_line_ordinal"],
        owner_total["end_document_line_ordinal"],
        owner_total["source_line_index"],
        owner_total["end_source_line_index"],
    ) == (
        parent["document_line_ordinal"],
        parent["end_document_line_ordinal"],
        parent["source_line_index"],
        parent["end_source_line_index"],
    )

    legacy = topology_v1.build_accounting_family_topology_scan_v1(pages, spec)
    assert subject.project_accounting_family_coextensive_parent_total_candidate_v2(
        pages,
        spec,
        result,
        detail,
    ) == project_accounting_family_coextensive_parent_total_region_v1(
        spec,
        legacy,
        legacy["regions"][0],
    )


def test_caller_region_and_coherently_rehashed_result_are_not_authority() -> None:
    pages = _pages()
    spec = _spec()
    result = subject.build_accounting_family_topology_candidates_v2(pages, spec)
    invented_region = copy.deepcopy(result["regions"][0])
    invented_region["observed_roles"].append("INVENTED")

    with pytest.raises(
        subject.AccountingFamilyTopologyCandidatesV2Error,
        match="not one exact replayed complete candidate",
    ):
        subject.bind_accounting_family_topology_candidate_v2(
            pages,
            spec,
            result,
            invented_region,
        )

    tampered = copy.deepcopy(result)
    tampered["regions"][0]["observed_roles"].append("INVENTED")
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = "aftcv2:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.AccountingFamilyTopologyCandidatesV2Error,
        match="does not replay exactly",
    ):
        subject.validate_accounting_family_topology_candidates_replay_v2(
            tampered,
            pages,
            spec,
        )


def test_full_page_or_family_spec_drift_fails_exact_replay() -> None:
    pages = _pages()
    spec = _spec()
    result = subject.build_accounting_family_topology_candidates_v2(pages, spec)
    changed_pages = copy.deepcopy(pages)
    changed_pages[0]["lines"][1]["vietocr_text"] = "Tiền gửi bị đổi"
    changed_spec = copy.deepcopy(spec)
    changed_spec["limits"]["max_cluster_span_lines"] = 19

    for replay_pages, replay_spec in ((changed_pages, spec), (pages, changed_spec)):
        with pytest.raises(
            subject.AccountingFamilyTopologyCandidatesV2Error,
            match="does not replay exactly",
        ):
            subject.validate_accounting_family_topology_candidates_replay_v2(
                result,
                replay_pages,
                replay_spec,
            )


def test_dependency_content_drift_fails_before_candidate_construction(monkeypatch) -> None:
    expected = copy.deepcopy(subject._DEPENDENCIES["topology_v1"])
    expected["sha256"] = "0" * 64
    monkeypatch.setitem(subject._DEPENDENCIES, "topology_v1", expected)

    with pytest.raises(
        subject.AccountingFamilyTopologyCandidatesV2Error,
        match="dependency content reference drifted",
    ):
        subject.build_accounting_family_topology_candidates_v2(_pages(), _spec())


def test_prepared_authority_scans_hits_once_and_matches_public_replay(monkeypatch) -> None:
    pages = _pages()
    spec = _spec()
    expected_scan = topology_v1.build_accounting_family_topology_scan_v1(pages, spec)
    expected_candidates = subject.build_accounting_family_topology_candidates_v2(pages, spec)
    expected_bindings = [
        subject.bind_accounting_family_topology_candidate_v2(
            pages,
            spec,
            expected_candidates,
            region,
        )
        for region in expected_candidates["regions"]
    ]
    original_document_hits = topology_v1._document_hits
    calls = 0

    def counted_document_hits(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_document_hits(*args, **kwargs)

    monkeypatch.setattr(topology_v1, "_document_hits", counted_document_hits)
    prepared = subject._prepare_accounting_family_topology_candidates_v2(pages, spec)
    scan, candidates, bindings = subject._prepared_accounting_family_topology_authority_v2(prepared)

    assert calls == 1
    assert scan == expected_scan
    assert candidates == expected_candidates
    assert [
        subject._validate_prepared_accounting_family_topology_candidate_binding_v2(
            binding,
            document_pages=pages,
            family_spec=spec,
            topology_candidates=candidates,
            topology_region=region,
        )
        for binding, region in zip(bindings, candidates["regions"], strict=True)
    ] == expected_bindings

    forged = replace(bindings[0], prepared_binding_sha256="0" * 64)
    with pytest.raises(
        subject.AccountingFamilyTopologyCandidatesV2Error,
        match="binding content drifted",
    ):
        subject._validate_prepared_accounting_family_topology_candidate_binding_v2(
            forged,
            document_pages=pages,
            family_spec=spec,
            topology_candidates=candidates,
            topology_region=candidates["regions"][0],
        )

    changed_pages = copy.deepcopy(pages)
    changed_pages[0]["lines"][0]["vietocr_text"] = "MUTATED CURRENT PAGE"
    with pytest.raises(
        subject.AccountingFamilyTopologyCandidatesV2Error,
        match="source binding drifted",
    ):
        subject._validate_prepared_accounting_family_topology_candidate_binding_v2(
            bindings[0],
            document_pages=changed_pages,
            family_spec=spec,
            topology_candidates=candidates,
            topology_region=candidates["regions"][0],
        )
