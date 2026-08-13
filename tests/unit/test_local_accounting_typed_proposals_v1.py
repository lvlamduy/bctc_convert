from __future__ import annotations

import copy
import gc
import weakref
from copy import deepcopy
from hashlib import sha256

import pytest
from test_source_structure_evidence_projection_v2 import (
    _synthetic_native_pair,
    _synthetic_ocr_pair,
)

from bctc_ai.source_structure import local_accounting_typed_proposals_v1 as typed
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    FamilySpecV1,
    RowRoleSpecV1,
)

_SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)


_CUSTOMER_DEPOSIT_TYPE_SPEC = FamilySpecV1(
    family_id="CUSTOMER_DEPOSIT_TYPE_BREAKDOWN",
    owner_aliases=("tien gui cua khach hang",),
    branch_aliases=("phan tich theo loai tien gui",),
    ordered_children=(
        RowRoleSpecV1("DEMAND", ("tien gui khong ky han",)),
        RowRoleSpecV1("TERM", ("tien gui co ky han",)),
    ),
    optional_children=(),
    total_aliases=("tong cong",),
    closure_child_roles=("DEMAND", "TERM"),
)


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _compact_projection(lines: list[str]) -> dict:
    atoms = [
        {
            "source_local_id": f"ssv1:line:{_digest(f'{index}:{text}')}",
            "kind": "LINE",
            "authority": "AUTHENTICATED_PRIMARY",
            "raw_text": text,
            "canonical_bbox_mpt": [
                1_000,
                1_000 + index * 1_000,
                1_000 + max(2_000, len(text) * 400),
                1_700 + index * 1_000,
            ],
        }
        for index, text in enumerate(lines)
    ]
    neutral = {"atoms": atoms}
    return {
        "source_local_page_id": f"ssv2:page:{_digest('typed-proposal-page')}",
        "neutral_page_v1_sha256": canonical_json_sha256_v1(neutral),
        "route": "DOMINANT_RASTER_OCR",
        "terminal": False,
        "neutral_page_v1": neutral,
    }


def _install_compact_source_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        typed,
        "validate_source_evidence_projection_v2",
        lambda value: deepcopy(value),
    )


def _quality_lines(*, branch: str = "Phân tích chất lượng nợ cho vay") -> list[str]:
    return [
        "Cho vay khách hàng",
        branch,
        "31/12/2025",
        "31/12/2024",
        "Đơn vị: triệu VND",
        "Nợ đủ tiêu chuẩn",
        "100",
        "90",
        "Nợ cần chú ý",
        "20",
        "15",
        "Nợ dưới tiêu chuẩn",
        "10",
        "8",
        "Nợ nghi ngờ",
        "5",
        "4",
        "Nợ có khả năng mất vốn",
        "3",
        "2",
        "Tổng cộng",
        "138",
        "119",
    ]


def _maturity_lines() -> list[str]:
    return [
        "Cho vay khách hàng",
        "Phân tích theo thời hạn",
        "31/12/2025",
        "31/12/2024",
        "Đơn vị: triệu VND",
        "Ngắn hạn",
        "100",
        "90",
        "Trung hạn",
        "20",
        "15",
        "Dài hạn",
        "10",
        "8",
        "Tổng cộng",
        "130",
        "113",
    ]


def test_exact_ocr_and_native_v2_sources_build_and_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ocr_record, ocr_result = _synthetic_ocr_pair()
    native_record, native_result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    projections = [
        project_authenticated_page_v2(page_record=ocr_record, page_result=ocr_result),
        project_authenticated_page_v2(page_record=native_record, page_result=native_result),
    ]

    for projection in projections:
        artifact = typed.build_local_accounting_typed_proposal_set_v1(
            projection,
            _SPECS,
        )
        replayed = typed.validate_local_accounting_typed_proposal_set_v1(
            artifact,
            source_projection_v2=projection,
            family_specs=_SPECS,
        )
        assert replayed == artifact
        assert artifact["source_binding"]["source_route"] == projection["route"]
        assert artifact["metrics"]["source_line_scan_passes"] == 1
        assert (
            len(artifact["line_dispositions"]) == artifact["metrics"]["eligible_primary_line_count"]
        )


def test_two_families_share_one_scan_and_ordered_topology_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(_quality_lines() + _maturity_lines())

    artifact = typed.build_local_accounting_typed_proposal_set_v1(projection, _SPECS)
    exact = [
        item
        for item in artifact["topology_candidates"]
        if item["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    ]

    assert {item["family_id"] for item in exact} == {
        "LOAN_QUALITY_CLASSIFICATION",
        "LOAN_MATURITY_BUCKETS",
    }
    assert artifact["metrics"]["source_line_scan_passes"] == 1
    assert artifact["metrics"]["eligible_primary_line_visit_count"] == len(
        projection["neutral_page_v1"]["atoms"]
    )
    assert artifact["metrics"]["registry_compile_passes_on_page"] == 0
    assert artifact["metrics"]["family_line_cartesian_evaluation_count"] == 0
    assert artifact["metrics"]["topology_event_visit_count"] < (
        len(projection["neutral_page_v1"]["atoms"]) * artifact["metrics"]["compiled_family_count"]
    )
    assert len(artifact["topology_dispositions"]) == len(artifact["topology_candidates"])


@pytest.mark.parametrize(
    "mutation",
    ("line_deletion", "topology_deletion", "raw_tamper", "generator_tamper", "foreign_key"),
)
def test_replay_rejects_deletion_tamper_and_forbidden_metadata(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(_quality_lines())
    artifact = typed.build_local_accounting_typed_proposal_set_v1(projection, _SPECS)
    forged = deepcopy(artifact)
    if mutation == "line_deletion":
        forged["line_dispositions"].pop()
    elif mutation == "topology_deletion":
        forged["topology_dispositions"].pop()
    elif mutation == "raw_tamper":
        forged["semantic_line_proposals"][0]["raw_span"]["raw_text"] = "forged"
    elif mutation == "generator_tamper":
        forged["generator_binding"]["generator_identity"]["revision"] = "FORGED"
        forged["generator_binding"]["generator_identity_sha256"] = canonical_json_sha256_v1(
            forged["generator_binding"]["generator_identity"]
        )
    else:
        forged["bank_identity"] = "FORBIDDEN_ROUTING_METADATA"

    with pytest.raises(
        typed.LocalAccountingTypedProposalContractError,
        match="deterministic replay",
    ):
        typed.validate_local_accounting_typed_proposal_set_v1(
            forged,
            source_projection_v2=projection,
            family_specs=_SPECS,
        )


def test_replay_binds_exact_spec_config_and_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(_quality_lines())
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        projection,
        (LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
    )

    with pytest.raises(typed.LocalAccountingTypedProposalContractError):
        typed.validate_local_accounting_typed_proposal_set_v1(
            artifact,
            source_projection_v2=projection,
            family_specs=(LOAN_MATURITY_BUCKETS_SPEC_V1,),
        )
    with pytest.raises(typed.LocalAccountingTypedProposalContractError):
        typed.validate_local_accounting_typed_proposal_set_v1(
            artifact,
            source_projection_v2=projection,
            family_specs=(LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
            generator_config=typed.LocalAccountingTypedProposalConfigV1(maximum_edit_distance=1),
        )
    changed_projection = deepcopy(projection)
    changed_projection["neutral_page_v1"]["atoms"][0]["raw_text"] = "Chứng khoán"
    changed_projection["neutral_page_v1_sha256"] = canonical_json_sha256_v1(
        changed_projection["neutral_page_v1"]
    )
    with pytest.raises(typed.LocalAccountingTypedProposalContractError):
        typed.validate_local_accounting_typed_proposal_set_v1(
            artifact,
            source_projection_v2=changed_projection,
            family_specs=(LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
        )


def test_repair_ties_and_runner_up_are_retained_without_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(["Cho vay khách hàngg", "Cho vay gan han"])
    artifact = typed.build_local_accounting_typed_proposal_set_v1(projection, _SPECS)
    tied, runner = artifact["semantic_line_proposals"]

    assert tied["proposal_status"] == "UNRESOLVED_AMBIGUOUS_REPAIR_CANDIDATE"
    assert tied["proposed_text"] is None
    assert {
        (item["family_id"], item["role"], item["edit_distance"])
        for item in tied["candidate_matches"]
    } == {
        ("LOAN_QUALITY_CLASSIFICATION", "OWNER", 1),
        ("LOAN_MATURITY_BUCKETS", "OWNER", 1),
    }
    assert runner["proposal_status"] == "UNRESOLVED_UNIQUE_REPAIR_CANDIDATE"
    assert [item["edit_distance"] for item in runner["candidate_matches"]] == [1, 2]
    assert [item["role"] for item in runner["candidate_matches"]] == [
        "SHORT_TERM",
        "LONG_TERM",
    ]
    assert all(
        item["disposition"] == "RETAINED_UNRESOLVED_REPAIR_CANDIDATE"
        for item in artifact["line_dispositions"]
    )
    assert artifact["safety"]["bounded_repair_used_for_acceptance"] is False


def test_numeric_period_and_unit_lines_are_protected_before_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(["31/12/2025", "Đơn vị: triệu VND", "1.234", "-5"])
    artifact = typed.build_local_accounting_typed_proposal_set_v1(projection, _SPECS)

    assert artifact["semantic_line_proposals"] == []
    assert [item["disposition"] for item in artifact["line_dispositions"]] == [
        "PROTECTED_PERIOD_CONTEXT",
        "PROTECTED_UNIT_CONTEXT",
        "PROTECTED_NUMERIC_CONTEXT",
        "PROTECTED_NUMERIC_CONTEXT",
    ]


def test_line_gap_and_span_use_primary_line_axis_not_interleaved_word_atoms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(_quality_lines())
    interleaved = []
    for line in projection["neutral_page_v1"]["atoms"]:
        interleaved.extend(
            (
                line,
                {
                    **deepcopy(line),
                    "source_local_id": f"ssv1:word:{_digest(line['source_local_id'])}",
                    "kind": "WORD",
                },
            )
        )
    projection["neutral_page_v1"]["atoms"] = interleaved
    projection["neutral_page_v1_sha256"] = canonical_json_sha256_v1(projection["neutral_page_v1"])

    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        projection,
        (LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
    )
    candidate = artifact["topology_candidates"][0]

    assert artifact["metrics"]["eligible_primary_line_count"] == len(_quality_lines())
    assert candidate["source_ordinal_range"] == [0, 20]
    assert candidate["maximum_span_exceeded"] is False


def test_exported_generator_and_safety_constants_are_immutable() -> None:
    with pytest.raises(TypeError):
        typed.LOCAL_ACCOUNTING_TYPED_PROPOSAL_GENERATOR_IDENTITY_V1[  # type: ignore[index]
            "revision"
        ] = "FORGED"
    with pytest.raises(TypeError):
        typed.LOCAL_ACCOUNTING_TYPED_PROPOSAL_SAFETY_V1[  # type: ignore[index]
            "role_a_used"
        ] = True


def test_typo_in_complete_family_stays_unresolved_and_never_invokes_lag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(_quality_lines(branch="Phân tích chất lượng nợ cho vayx"))
    artifact = typed.build_local_accounting_typed_proposal_set_v1(projection, _SPECS)
    quality = next(
        item
        for item in artifact["topology_candidates"]
        if item["family_id"] == "LOAN_QUALITY_CLASSIFICATION"
    )

    assert quality["candidate_status"] == "UNRESOLVED_REPAIR_TOPOLOGY_CANDIDATE"
    assert quality["contains_repair_candidates"] is True
    assert artifact["topology_dispositions"] == [
        {
            "topology_candidate_id": quality["topology_candidate_id"],
            "disposition": "RETAINED_UNRESOLVED",
            "reason_code": "REPAIR_CANDIDATE_CANNOT_ACCEPT_STRUCTURE",
        }
    ]
    assert artifact["safety"]["lag_core_invoked"] is False
    assert artifact["safety"]["lag_observation_assembled"] is False
    assert artifact["safety"]["semantic_acceptance_claimed"] is False


def test_artifact_persists_no_forbidden_routing_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(_quality_lines()),
        _SPECS,
    )

    # The generator identity explicitly lists forbidden inputs as values; the
    # artifact must not persist any of them as data-bearing fields.
    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {key for item in value.values() for key in keys(item)}
        if isinstance(value, list):
            return {key for item in value for key in keys(item)}
        return set()

    persisted_keys = keys(artifact)

    for forbidden in (
        "bank_identity",
        "filename_identity",
        "physical_page",
        "note_number",
        "role_a_reference",
        "schema_identity",
    ):
        assert forbidden not in persisted_keys


def test_third_declarative_family_compiles_into_versioned_collision_registry() -> None:
    specs = (*_SPECS, _CUSTOMER_DEPOSIT_TYPE_SPEC)

    payload = typed.local_accounting_family_registry_payload_v1(specs)
    compiled = typed.compile_local_accounting_typed_proposal_registry_v1(specs)

    assert payload["format_version"] == "LOCAL_ACCOUNTING_FAMILY_REGISTRY_V1"
    assert [item["family_id"] for item in payload["family_specs"]] == [
        "CUSTOMER_DEPOSIT_TYPE_BREAKDOWN",
        "LOAN_MATURITY_BUCKETS",
        "LOAN_QUALITY_CLASSIFICATION",
    ]
    assert compiled.family_specs == (
        _CUSTOMER_DEPOSIT_TYPE_SPEC,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    total_collision = next(
        item
        for item in payload["collision_receipt"]["collisions"]
        if item["normalized_alias"] == "tong cong"
    )
    assert {
        (claim["family_id"], claim["role_kind"], claim["role"])
        for claim in total_collision["claims"]
    } == {
        ("CUSTOMER_DEPOSIT_TYPE_BREAKDOWN", "TOTAL", "TOTAL"),
        ("LOAN_MATURITY_BUCKETS", "TOTAL", "TOTAL"),
        ("LOAN_QUALITY_CLASSIFICATION", "TOTAL", "TOTAL"),
    }
    assert payload["collision_receipt"]["collision_count"] >= 1
    assert compiled.registry_sha256 == canonical_json_sha256_v1(payload)


def test_one_compiled_registry_is_reused_across_pages_without_recompilation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    first = _compact_projection(_quality_lines())
    second = _compact_projection(_maturity_lines())
    second["source_local_page_id"] = f"ssv2:page:{_digest('typed-proposal-page-2')}"
    expected = [
        typed.build_local_accounting_typed_proposal_set_v1(page, _SPECS) for page in (first, second)
    ]
    compiled = typed.compile_local_accounting_typed_proposal_registry_v1(_SPECS)

    def forbidden_recompile(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("multi-page registry path recompiled family vocabulary")

    monkeypatch.setattr(
        typed,
        "compile_local_accounting_typed_proposal_registry_v1",
        forbidden_recompile,
    )
    actual = [
        typed.build_local_accounting_typed_proposal_set_from_registry_v1(
            page,
            compiled,
        )
        for page in (first, second)
    ]

    assert actual == expected
    for page, artifact in zip((first, second), actual, strict=True):
        assert (
            typed.validate_local_accounting_typed_proposal_set_from_registry_v1(
                artifact,
                source_projection_v2=page,
                compiled_registry=compiled,
            )
            == artifact
        )
        assert artifact["metrics"]["source_line_scan_passes"] == 1
        assert artifact["metrics"]["registry_compile_passes_on_page"] == 0


def test_compiled_handle_receipt_tamper_cannot_change_inference_or_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(_quality_lines())
    compiled = typed.compile_local_accounting_typed_proposal_registry_v1(_SPECS)
    baseline = typed.build_local_accounting_typed_proposal_set_from_registry_v1(
        projection, compiled
    )

    copied = copy.copy(compiled)
    with pytest.raises(typed.LocalAccountingTypedProposalContractError):
        typed.build_local_accounting_typed_proposal_set_from_registry_v1(projection, copied)

    object.__setattr__(compiled, "registry_sha256", "0" * 64)
    object.__setattr__(compiled, "alias_entries", ())
    object.__setattr__(
        compiled.family_specs[1],
        "ordered_children",
        compiled.family_specs[1].ordered_children + (RowRoleSpecV1("FORGED", ("forged",)),),
    )
    object.__setattr__(compiled.config, "maximum_edit_distance", 0)
    assert (
        typed.build_local_accounting_typed_proposal_set_from_registry_v1(projection, compiled)
        == baseline
    )


def test_caller_config_mutation_after_compile_cannot_change_registry() -> None:
    config = typed.LocalAccountingTypedProposalConfigV1()
    compiled = typed.compile_local_accounting_typed_proposal_registry_v1(_SPECS, config)
    object.__setattr__(config, "maximum_edit_distance", 0)
    assert compiled.config.maximum_edit_distance == 2


def test_family_specs_reject_mutable_sequence_fields() -> None:
    mutable = FamilySpecV1(
        family_id="MUTABLE_SPEC",
        owner_aliases=["owner"],  # type: ignore[arg-type]
        branch_aliases=("branch",),
        ordered_children=(RowRoleSpecV1("ITEM", ("item",)),),
        optional_children=(),
        total_aliases=("total",),
        closure_child_roles=("ITEM",),
    )
    with pytest.raises(typed.LocalAccountingTypedProposalContractError):
        typed.compile_local_accounting_typed_proposal_registry_v1((mutable,))


def test_thousand_similar_aliases_overflow_before_any_edit_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    base = "a" * 24
    # Four replacement letters yield well over 1,000 unique, same-length
    # surfaces within two edits of the raw line while retaining a bounded
    # q-gram necessary-condition fanout.
    similar_aliases = tuple(
        alias
        for replacement in "bcde"
        for alias in (
            f"{base[:left]}{replacement}{base[left + 1 : right]}{replacement}{base[right + 1 :]}"
            for left in range(len(base))
            for right in range(left + 1, len(base))
        )
    )[:1_000]
    assert len(similar_aliases) == len(set(similar_aliases)) == 1_000
    assert {len(item) for item in similar_aliases} == {len(base)}
    stress_spec = FamilySpecV1(
        family_id="ALIAS_FANOUT_STRESS",
        owner_aliases=similar_aliases,
        branch_aliases=("fanout branch",),
        ordered_children=(RowRoleSpecV1("ITEM", ("fanout item",)),),
        optional_children=(),
        total_aliases=("fanout total",),
        closure_child_roles=("ITEM",),
    )
    config = typed.LocalAccountingTypedProposalConfigV1(maximum_fuzzy_alias_candidate_fanout=64)

    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection([base]),
        (stress_spec,),
        config,
    )

    assert artifact["semantic_line_proposals"] == []
    assert artifact["line_dispositions"][0]["disposition"] == ("RETAINED_UNRESOLVED_FUZZY_FANOUT")
    assert artifact["metrics"]["fuzzy_alias_fanout_overflow_line_count"] == 1
    assert artifact["metrics"]["maximum_fuzzy_alias_candidate_fanout"] == 1_000
    assert artifact["metrics"]["bounded_edit_distance_evaluation_count"] == 0
    assert artifact["metrics"]["bounded_edit_distance_evaluation_count"] <= (
        config.maximum_fuzzy_alias_candidate_fanout
    )


def test_thousand_shared_exact_total_aliases_fail_closed_at_bounded_fanout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"EXACT_TOTAL_FANOUT_{index:04d}",
            owner_aliases=(f"owner {index}",),
            branch_aliases=(f"branch {index}",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"item {index}",)),),
            optional_children=(),
            total_aliases=("tong cong",),
            closure_child_roles=("ITEM",),
        )
        for index in range(1_000)
    )
    config = typed.LocalAccountingTypedProposalConfigV1(
        maximum_exact_alias_candidate_fanout=64,
    )

    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["Tổng cộng"]),
        family_specs,
        config,
    )

    assert len(artifact["semantic_line_proposals"]) == 1
    assert artifact["semantic_line_proposals"][0]["candidate_matches"] == []
    assert artifact["semantic_line_proposals"][0]["proposal_status"] == (
        "DEFERRED_EXACT_ALIAS_COLLISION"
    )
    assert len(artifact["line_dispositions"]) == 1
    assert artifact["line_dispositions"][0]["semantic_proposal_id"] is not None
    assert artifact["line_dispositions"][0]["disposition"] == (
        "RETAINED_UNRESOLVED_EXACT_ALIAS_FANOUT"
    )
    assert artifact["line_dispositions"][0]["reason_code"] == (
        "DEFERRED_TO_LOCAL_BRANCH_SHORTLIST_RESOLUTION"
    )
    assert artifact["metrics"]["exact_alias_fanout_overflow_line_count"] == 1
    assert artifact["metrics"]["maximum_exact_alias_candidate_fanout"] == 1_000
    assert artifact["metrics"]["total_exact_alias_candidate_fanout"] == 1_000
    assert artifact["metrics"]["semantic_match_claim_count"] == 0
    assert artifact["metrics"]["family_line_cartesian_evaluation_count"] == 0
    assert artifact["topology_candidates"] == []


def test_common_total_resolves_only_for_local_branch_shortlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"CONTEXTUAL_TOTAL_{index:04d}",
            owner_aliases=(f"owner {index}",),
            branch_aliases=(f"branch {index}",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"item {index}",)),),
            optional_children=(),
            total_aliases=("tong cong",),
            closure_child_roles=("ITEM",),
        )
        for index in range(100)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["owner 0", "branch 0", "item 0", "tong cong"]),
        family_specs,
        typed.LocalAccountingTypedProposalConfigV1(maximum_exact_alias_candidate_fanout=64),
    )

    contextual = artifact["contextual_exact_resolution_proposals"]
    assert len(contextual) == 1
    assert {item["family_id"] for item in contextual[0]["candidate_matches"]} == {
        "CONTEXTUAL_TOTAL_0000"
    }
    assert len(artifact["topology_candidates"]) == 1
    assert artifact["topology_candidates"][0]["candidate_status"] == (
        "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    )
    assert artifact["topology_candidates"][0]["missing_required_roles"] == []
    assert artifact["metrics"]["semantic_match_claim_count"] == 4


def test_many_local_family_blocks_resolve_shared_labels_linearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_count = 100
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"LOCAL_BLOCK_{index:04d}",
            owner_aliases=(f"owner {index}",),
            branch_aliases=(f"branch {index}",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"item {index}",)),),
            optional_children=(),
            total_aliases=("tong cong",),
            closure_child_roles=("ITEM",),
        )
        for index in range(family_count)
    )
    lines = [
        line
        for index in range(family_count)
        for line in (f"owner {index}", f"branch {index}", f"item {index}", "tong cong")
    ]
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(lines), family_specs
    )

    assert len(artifact["topology_candidates"]) == family_count
    assert all(
        item["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
        for item in artifact["topology_candidates"]
    )
    assert len(artifact["contextual_exact_resolution_proposals"]) == family_count
    assert artifact["metrics"]["contextual_exact_resolution_lookup_count"] == (family_count)
    assert artifact["metrics"]["semantic_match_claim_count"] == 4 * family_count
    assert artifact["metrics"]["topology_event_visit_count"] <= 6 * family_count


def test_shared_branch_bootstraps_from_unique_owner_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"SHARED_BRANCH_{index:04d}",
            owner_aliases=(f"unique owner {index}",),
            branch_aliases=("common breakdown",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"unique item {index}",)),),
            optional_children=(),
            total_aliases=("total",),
            closure_child_roles=("ITEM",),
        )
        for index in range(100)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["unique owner 0", "common breakdown", "unique item 0", "total"]),
        family_specs,
    )

    assert len(artifact["topology_candidates"]) == 1
    assert artifact["topology_candidates"][0]["candidate_status"] == (
        "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    )
    assert artifact["metrics"]["contextual_exact_resolution_lookup_count"] == 2


def test_prior_common_total_cannot_poison_new_owner_branch_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"RESET_SAFE_{index:04d}",
            owner_aliases=(f"owner {index}",),
            branch_aliases=(f"branch {index}",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"item {index}",)),),
            optional_children=(),
            total_aliases=("total",),
            closure_child_roles=("ITEM",),
        )
        for index in range(100)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["total", "owner 0", "branch 0", "item 0", "total"]),
        family_specs,
    )

    assert len(artifact["topology_candidates"]) == 1
    candidate = artifact["topology_candidates"][0]
    assert candidate["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    assert candidate["missing_required_roles"] == []
    assert candidate["source_ordinal_range"] == [1, 4]


def test_owner_text_alone_does_not_reset_active_family_before_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    target = FamilySpecV1(
        family_id="ACTIVE_TARGET",
        owner_aliases=("target owner",),
        branch_aliases=("target branch",),
        ordered_children=(RowRoleSpecV1("ITEM", ("target item",)),),
        optional_children=(),
        total_aliases=("total",),
        closure_child_roles=("ITEM",),
    )
    neighbor = FamilySpecV1(
        family_id="NESTED_OWNER_CONTROL",
        owner_aliases=("neighbor owner",),
        branch_aliases=("neighbor branch",),
        ordered_children=(RowRoleSpecV1("ITEM", ("neighbor item",)),),
        optional_children=(),
        total_aliases=("total",),
        closure_child_roles=("ITEM",),
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(
            ["target owner", "target branch", "target item", "neighbor owner", "total"]
        ),
        (target, neighbor),
    )

    accepted = [
        item
        for item in artifact["topology_candidates"]
        if item["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    ]
    assert [item["family_id"] for item in accepted] == ["ACTIVE_TARGET"]


def test_active_frontier_filters_shared_owner_total_surface_to_total_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    target = FamilySpecV1(
        family_id="SHARED_SURFACE_TARGET",
        owner_aliases=("shared",),
        branch_aliases=("target branch",),
        ordered_children=(RowRoleSpecV1("ITEM", ("target item",)),),
        optional_children=(),
        total_aliases=("shared",),
        closure_child_roles=("ITEM",),
    )
    controls = tuple(
        FamilySpecV1(
            family_id=f"SHARED_SURFACE_CONTROL_{index:04d}",
            owner_aliases=(f"control owner {index}",),
            branch_aliases=(f"control branch {index}",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"control item {index}",)),),
            optional_children=(),
            total_aliases=("shared",),
            closure_child_roles=("ITEM",),
        )
        for index in range(100)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["shared", "target branch", "target item", "shared"]),
        (target, *controls),
    )

    assert len(artifact["topology_candidates"]) == 1
    candidate = artifact["topology_candidates"][0]
    assert candidate["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    assert candidate["missing_required_roles"] == []


def test_owner_plus_deferred_branch_resets_incomplete_prior_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"DEFERRED_RESET_{index:04d}",
            owner_aliases=(f"owner {index}",),
            branch_aliases=("common branch",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"item {index}",)),),
            optional_children=(),
            total_aliases=("total",),
            closure_child_roles=("ITEM",),
        )
        for index in range(100)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(
            [
                "owner 0",
                "common branch",
                "item 0",
                "owner 1",
                "common branch",
                "item 1",
                "total",
            ]
        ),
        family_specs,
    )

    exact = [
        item
        for item in artifact["topology_candidates"]
        if item["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    ]
    assert [(item["family_id"], item["source_ordinal_range"]) for item in exact] == [
        ("DEFERRED_RESET_0001", [3, 6])
    ]
    prior = next(
        item
        for item in artifact["topology_candidates"]
        if item["family_id"] == "DEFERRED_RESET_0000"
    )
    assert prior["candidate_status"] != "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    assert prior["missing_required_roles"] == ["TOTAL"]


def test_new_branch_wins_cross_phase_surface_over_old_total_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    old = FamilySpecV1(
        family_id="CROSS_PHASE_OLD",
        owner_aliases=("old owner",),
        branch_aliases=("old branch",),
        ordered_children=(RowRoleSpecV1("ITEM", ("old item",)),),
        optional_children=(),
        total_aliases=("shared",),
        closure_child_roles=("ITEM",),
    )
    new = FamilySpecV1(
        family_id="CROSS_PHASE_NEW",
        owner_aliases=("new owner",),
        branch_aliases=("shared",),
        ordered_children=(RowRoleSpecV1("ITEM", ("new item",)),),
        optional_children=(),
        total_aliases=("new total",),
        closure_child_roles=("ITEM",),
    )
    controls = tuple(
        FamilySpecV1(
            family_id=f"CROSS_PHASE_CONTROL_{index:04d}",
            owner_aliases=(f"control owner {index}",),
            branch_aliases=("shared",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"control item {index}",)),),
            optional_children=(),
            total_aliases=("shared",),
            closure_child_roles=("ITEM",),
        )
        for index in range(100)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(
            [
                "old owner",
                "old branch",
                "old item",
                "new owner",
                "shared",
                "new item",
                "new total",
            ]
        ),
        (old, new, *controls),
    )

    exact = [
        item
        for item in artifact["topology_candidates"]
        if item["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    ]
    assert [(item["family_id"], item["source_ordinal_range"]) for item in exact] == [
        ("CROSS_PHASE_NEW", [3, 6])
    ]


def test_contextual_budget_is_single_across_pending_and_active_phases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    active = tuple(
        FamilySpecV1(
            family_id=f"BUDGET_ACTIVE_{index:04d}",
            owner_aliases=(f"active owner {index}",),
            branch_aliases=("active branch",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"active item {index}",)),),
            optional_children=(),
            total_aliases=("collision",),
            closure_child_roles=("ITEM",),
        )
        for index in range(64)
    )
    pending = tuple(
        FamilySpecV1(
            family_id=f"BUDGET_PENDING_{index:04d}",
            owner_aliases=("pending owner",),
            branch_aliases=("collision",),
            ordered_children=(RowRoleSpecV1("ITEM", (f"pending item {index}",)),),
            optional_children=(),
            total_aliases=(f"pending total {index}",),
            closure_child_roles=("ITEM",),
        )
        for index in range(64)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["active branch", "pending owner", "collision"]),
        (*active, *pending),
    )

    assert artifact["metrics"]["contextual_exact_resolution_lookup_count"] <= 64
    assert artifact["metrics"]["contextual_exact_resolution_proposal_count"] <= 64


def test_contextual_budget_counts_alias_claims_within_one_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    roles = tuple(RowRoleSpecV1(f"ITEM_{index:04d}", ("common child",)) for index in range(100))
    spec = FamilySpecV1(
        family_id="WITHIN_FAMILY_ALIAS_FANOUT",
        owner_aliases=("owner",),
        branch_aliases=("branch",),
        ordered_children=roles,
        optional_children=(),
        total_aliases=("total",),
        closure_child_roles=tuple(item.role for item in roles),
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["owner", "branch", "common child"]),
        (spec,),
    )

    assert artifact["metrics"]["contextual_exact_resolution_overflow_line_count"] == 1
    assert artifact["contextual_exact_resolution_proposals"] == []
    assert artifact["metrics"]["semantic_match_claim_count"] <= 2


def test_contextual_budget_is_cumulative_across_family_alias_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    family_specs = tuple(
        FamilySpecV1(
            family_id=f"CUMULATIVE_CLAIMS_{family:04d}",
            owner_aliases=(f"owner {family}",),
            branch_aliases=("shared branch",),
            ordered_children=tuple(
                RowRoleSpecV1(f"ITEM_{role:04d}", ("common child",)) for role in range(64)
            ),
            optional_children=(),
            total_aliases=(f"total {family}",),
            closure_child_roles=tuple(f"ITEM_{role:04d}" for role in range(64)),
        )
        for family in range(64)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["shared branch", "common child"]), family_specs
    )

    assert artifact["metrics"]["contextual_exact_resolution_overflow_line_count"] == 1
    assert (
        sum(
            len(item["candidate_matches"])
            for item in artifact["contextual_exact_resolution_proposals"]
        )
        <= 64
    )


def test_identical_cross_family_topology_remains_ambiguous_not_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    specs = tuple(
        FamilySpecV1(
            family_id=f"IDENTICAL_CONTROL_{index}",
            owner_aliases=("owner",),
            branch_aliases=("branch",),
            ordered_children=(RowRoleSpecV1("ITEM", ("item",)),),
            optional_children=(),
            total_aliases=("total",),
            closure_child_roles=("ITEM",),
        )
        for index in range(2)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["owner", "branch", "item", "total"]), specs
    )

    assert len(artifact["topology_candidates"]) == 2
    assert artifact["metrics"]["exact_ordered_topology_candidate_count"] == 0
    assert all(
        item["contains_ambiguous_role_candidates"] is True
        and item["candidate_status"] == "UNRESOLVED_INCOMPLETE_OR_AMBIGUOUS_TOPOLOGY_CANDIDATE"
        for item in artifact["topology_candidates"]
    )


def test_internal_role_names_cannot_disambiguate_identical_visible_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    specs = tuple(
        FamilySpecV1(
            family_id=f"ROLE_NAME_CONTROL_{index}",
            owner_aliases=("owner",),
            branch_aliases=("branch",),
            ordered_children=(
                RowRoleSpecV1("MEANING_A" if index == 0 else "MEANING_B", ("item",)),
            ),
            optional_children=(),
            total_aliases=("total",),
            closure_child_roles=("MEANING_A" if index == 0 else "MEANING_B",),
        )
        for index in range(2)
    )
    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(["owner", "branch", "item", "total"]), specs
    )

    assert artifact["metrics"]["exact_ordered_topology_candidate_count"] == 0
    assert all(
        item["candidate_status"] == "UNRESOLVED_INCOMPLETE_OR_AMBIGUOUS_TOPOLOGY_CANDIDATE"
        for item in artifact["topology_candidates"]
    )


def test_compiled_registry_private_state_is_evicted_with_handle() -> None:
    compiled = typed.compile_local_accounting_typed_proposal_registry_v1(_SPECS)
    handle_id = id(compiled)
    handle_ref = weakref.ref(compiled)

    assert handle_id in typed._COMPILED_REGISTRY_STATE_BY_HANDLE_ID

    del compiled
    gc.collect()

    assert handle_ref() is None
    assert handle_id not in typed._COMPILED_REGISTRY_STATE_BY_HANDLE_ID


def test_complete_quality_fingerprint_without_branch_is_explicit_residual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    lines = _quality_lines()
    lines.remove("Phân tích chất lượng nợ cho vay")

    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        _compact_projection(lines),
        (LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
    )

    assert len(artifact["topology_candidates"]) == 1
    residual = artifact["topology_candidates"][0]
    assert residual["candidate_status"] == "UNRESOLVED_MISSING_BRANCH_FINGERPRINT"
    assert residual["missing_required_roles"] == ["BRANCH"]
    assert residual["orphan_branch"] is True
    assert artifact["topology_dispositions"] == [
        {
            "topology_candidate_id": residual["topology_candidate_id"],
            "disposition": "RETAINED_UNRESOLVED",
            "reason_code": ("COMPLETE_CHILD_FINGERPRINT_WITHOUT_LOCAL_BRANCH_ANCHOR"),
        }
    ]
    assert artifact["metrics"]["exact_ordered_topology_candidate_count"] == 0
    assert artifact["metrics"]["unresolved_topology_candidate_count"] == 1


def test_dash_percentage_and_not_applicable_tokens_are_protected_before_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_compact_source_contract(monkeypatch)
    projection = _compact_projection(
        [
            "-",
            "–",
            "—",
            "−",
            "12,5%",
            "12,5 %",
            "(8.0%)",
            "(8.0 %)",
            "100,000.00 %",
            "%",
            "Đơn vị: %",
            "Phần trăm",
            "Đơn vị: phần trăm",
            "N/A",
            "NA",
            "Không áp dụng",
        ]
    )

    artifact = typed.build_local_accounting_typed_proposal_set_v1(projection, _SPECS)

    assert artifact["semantic_line_proposals"] == []
    assert [item["disposition"] for item in artifact["line_dispositions"]] == [
        "PROTECTED_DASH_VALUE_CONTEXT",
        "PROTECTED_DASH_VALUE_CONTEXT",
        "PROTECTED_DASH_VALUE_CONTEXT",
        "PROTECTED_DASH_VALUE_CONTEXT",
        "PROTECTED_PERCENTAGE_VALUE_CONTEXT",
        "PROTECTED_PERCENTAGE_VALUE_CONTEXT",
        "PROTECTED_PERCENTAGE_VALUE_CONTEXT",
        "PROTECTED_PERCENTAGE_VALUE_CONTEXT",
        "PROTECTED_PERCENTAGE_VALUE_CONTEXT",
        "PROTECTED_PERCENTAGE_UNIT_CONTEXT",
        "PROTECTED_PERCENTAGE_UNIT_CONTEXT",
        "PROTECTED_PERCENTAGE_UNIT_CONTEXT",
        "PROTECTED_PERCENTAGE_UNIT_CONTEXT",
        "PROTECTED_NOT_APPLICABLE_VALUE_CONTEXT",
        "PROTECTED_NOT_APPLICABLE_VALUE_CONTEXT",
        "PROTECTED_NOT_APPLICABLE_VALUE_CONTEXT",
    ]
    assert all(
        item["reason_code"] == "SOURCE_VISIBLE_VALUE_OR_UNIT_CONTEXT_EXCLUDED_FROM_REPAIR"
        for item in artifact["line_dispositions"]
    )
    assert artifact["metrics"]["bounded_edit_distance_evaluation_count"] == 0
