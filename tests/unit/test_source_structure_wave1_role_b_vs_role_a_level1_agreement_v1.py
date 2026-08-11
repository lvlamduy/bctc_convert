from __future__ import annotations

import ast
import copy
import hashlib
import stat
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.source_structure import (
    wave1_role_b_vs_role_a_level1_agreement_v1 as agreement_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _synthetic_inputs(
    *,
    source_sha: str = "a" * 64,
    bank: str = "PROVENANCE_ONLY",
    terminal_last: bool = True,
    candidate_count: int = 1,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    page_count = 8
    candidate_ids = [f"candidate-{index}" for index in range(1, candidate_count + 1)]
    families = ["OTHER", "CDKT", "CDKT", "KQKD", "LCTT", "TM", "TM", "TM"]
    page_hypotheses: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    source_pages: list[dict[str, Any]] = []
    for ordinal, family in enumerate(families, start=1):
        terminal = terminal_last and ordinal == page_count
        if terminal:
            family = "UPSTREAM_TERMINAL"
        page_id = f"page-hypothesis-{source_sha[:8]}-{ordinal}"
        projection_id = f"projection-{source_sha[:8]}-{ordinal}"
        projection_sha = _digest(projection_id)
        evidence = ["TITLE_SIGNAL_HYPOTHESIS"] if ordinal in range(2, 7) else []
        if ordinal == 3:
            evidence = ["OFF_BALANCE_SIGNAL_HYPOTHESIS", *evidence]
        supporting = ordinal in range(2, 7) and candidate_count > 0
        cited_candidates = list(candidate_ids) if supporting else []
        page_hypotheses.append(
            {
                "input_ordinal": ordinal,
                "page_hypothesis_id": page_id,
                "source_local_page_id": projection_id,
                "source_projection_sha256": projection_sha,
                "upstream_status": (
                    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY" if terminal else "OCR_WORD_BOX_READ_COMPLETE"
                ),
                "terminal": terminal,
                "family_hypothesis": family,
                "diagnostic_score": 0.0 if terminal else 1.0,
                "evidence_codes": sorted(evidence),
                "continuation_marker_hypothesis": False,
            }
        )
        bindings.append(
            {
                "input_ordinal": ordinal,
                "source_local_page_id": projection_id,
                "source_projection_sha256": projection_sha,
                "route": "DOMINANT_RASTER_OCR",
                "upstream_status": page_hypotheses[-1]["upstream_status"],
                "terminal": terminal,
            }
        )
        dispositions.append(
            {
                "input_ordinal": ordinal,
                "page_hypothesis_id": page_id,
                "source_local_page_id": projection_id,
                "primary_disposition": (
                    "UPSTREAM_TERMINAL_UNRESOLVED"
                    if terminal
                    else (
                        "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS"
                        if supporting
                        else "RETAINED_UNRESOLVED"
                    )
                ),
                "block_hypothesis_ids": cited_candidates,
            }
        )
        source_pages.append(
            {
                "document_id": f"sha256:{source_sha}",
                "physical_page": ordinal,
                "projection_identity": projection_id,
                "projection_sha256": projection_sha,
                "route": "DOMINANT_RASTER_OCR",
                "status": page_hypotheses[-1]["upstream_status"],
                "terminal": terminal,
            }
        )

    blocks: list[dict[str, Any]] = []
    member_ids = [f"page-hypothesis-{source_sha[:8]}-{ordinal}" for ordinal in range(2, 6)]
    sequence = ["CDKT", "CDKT", "KQKD", "LCTT"]
    family_evidence = [page_hypotheses[ordinal - 1]["evidence_codes"] for ordinal in range(2, 6)]
    for rank, candidate_id in enumerate(candidate_ids, start=1):
        blocks.append(
            {
                "block_hypothesis_id": candidate_id,
                "rank": rank,
                "diagnostic_score": float(10 - rank),
                "diagnostic_score_components": {
                    "average_family_confidence": 1.0,
                    "form_signal_page_count": 1,
                    "start_form_signal": True,
                },
                "start_input_ordinal": 2,
                "end_input_ordinal": 5,
                "family_sequence_hypothesis": list(sequence),
                "family_evidence_codes": copy.deepcopy(family_evidence),
                "member_page_hypothesis_ids": list(member_ids),
                "tm_boundary_hypothesis_id": f"page-hypothesis-{source_sha[:8]}-6",
            }
        )
    role_b_document = {
        "source_sha256": source_sha,
        "status": (
            "CANDIDATES_EMITTED" if candidate_count else "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS"
        ),
        "document_hypotheses_identity": f"document-{source_sha[:8]}",
        "page_hypotheses": page_hypotheses,
        "page_projection_bindings": bindings,
        "page_dispositions": dispositions,
        "block_hypotheses": blocks,
    }
    role_b = {
        "format_version": agreement_v1._ROLE_B_FORMAT,
        "status": agreement_v1._ROLE_B_STATUS,
        "claim_boundary": agreement_v1._ROLE_B_CLAIM,
        "documents": [role_b_document],
    }
    role_a = {
        "format_version": agreement_v1._ROLE_A_FORMAT,
        "status": agreement_v1._ROLE_A_STATUS,
        "claim_boundary": agreement_v1._ROLE_A_CLAIM,
        "documents": [
            {
                "bank": bank,
                "source": {
                    "sha256": source_sha,
                    "document_id": f"sha256:{source_sha}",
                    "page_count": page_count,
                },
                "reference_status": agreement_v1._ROLE_A_STATUS,
                "claim_boundary": agreement_v1._ROLE_A_CLAIM,
                "page_basis": "ONE_BASED_PHYSICAL_PDF_PAGE",
                "page_segments": [
                    {
                        "kind": "COVER",
                        "start_page": 1,
                        "end_page": 1,
                        "copy_id": "NONE",
                        "embedded_off_balance_pages": [],
                    },
                    {
                        "kind": "CDKT_MAIN",
                        "start_page": 2,
                        "end_page": 3,
                        "copy_id": "PRIMARY",
                        "embedded_off_balance_pages": [3],
                    },
                    {
                        "kind": "KQKD",
                        "start_page": 4,
                        "end_page": 4,
                        "copy_id": "PRIMARY",
                        "embedded_off_balance_pages": [],
                    },
                    {
                        "kind": "LCTT",
                        "start_page": 5,
                        "end_page": 5,
                        "copy_id": "PRIMARY",
                        "embedded_off_balance_pages": [],
                    },
                    {
                        "kind": "TM",
                        "start_page": 6,
                        "end_page": 8,
                        "copy_id": "PRIMARY",
                        "embedded_off_balance_pages": [],
                    },
                ],
                "statement_blocks": [
                    _reference_block("CDKT", "CDKT_MAIN", 2, 3),
                    _reference_block(
                        "OFF_BALANCE", "OFF_BALANCE", 3, 3, placement="EMBEDDED_BOTTOM_REGION"
                    ),
                    _reference_block("KQKD", "KQKD", 4, 4),
                    _reference_block("LCTT", "LCTT", 5, 5),
                    _reference_block("TM", "TM", 6, 8),
                ],
            }
        ],
    }
    source_inventory = {"pages": source_pages}
    return role_b, role_a, source_inventory


def _reference_block(
    block_id: str,
    block_type: str,
    start: int,
    end: int,
    *,
    placement: str = "PAGE_SEQUENCE",
) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "block_type": block_type,
        "copy_id": "PRIMARY",
        "start_page": start,
        "end_page": end,
        "placement": placement,
        "parent_block_id": "CDKT" if block_type == "OFF_BALANCE" else None,
        "visible_unit_override": None,
    }


def _synthetic_authority() -> dict[str, Any]:
    return {
        "document_join": {
            "key": "SOURCE_SHA256_ONLY",
            "bank_is_output_provenance_only": True,
            "document_name_is_not_read_or_used": True,
        },
        "role_b_hypothesis_artifact": {"sha256": _digest("role-b")},
        "role_a_level_1_artifact": {"sha256": _digest("role-a")},
    }


def _synthetic_producer() -> dict[str, Any]:
    return {"git": {"commit": "0" * 40, "dirty": False}, "implementation_ledger": {}}


def _build_synthetic(
    role_b: dict[str, Any], role_a: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    return agreement_v1._build_from_inputs(
        role_b,
        role_a,
        source,
        authority=_synthetic_authority(),
        producer=_synthetic_producer(),
        enforce_finalized_baseline=False,
    )


def _validate_synthetic(
    value: dict[str, Any],
    role_b: dict[str, Any],
    role_a: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    return agreement_v1._validate_from_inputs(
        value,
        project_root=PROJECT_ROOT,
        role_b_inventory=role_b,
        role_a_reference=role_a,
        source_inventory=source,
        authority=_synthetic_authority(),
        enforce_finalized_baseline=False,
        validate_producer=False,
    )


def _refresh_identity(value: dict[str, Any]) -> None:
    value["agreement_identity_sha256"] = canonical_json_sha256_v1(
        {key: item for key, item in value.items() if key != "agreement_identity_sha256"}
    )


def _typed_shape(value: Any) -> Any:
    if type(value) is dict:
        return {key: _typed_shape(item) for key, item in value.items()}
    if type(value) is list:
        return list
    return type(value)


def test_exact_range_tm_start_page_confusion_terminal_and_off_balance_receipts() -> None:
    role_b, role_a, source = _synthetic_inputs()
    artifact = _build_synthetic(role_b, role_a, source)
    assert _validate_synthetic(artifact, role_b, role_a, source) == artifact
    document = artifact["documents"][0]
    assert document["bank"] == "PROVENANCE_ONLY"
    assert [item["physical_page"] for item in document["page_comparisons"]] == list(range(1, 9))
    assert document["page_comparisons"][-1]["comparison_status"] == ("UPSTREAM_TERMINAL_SEPARATE")
    candidate = document["candidate_comparisons"][0]
    assert [item["family"] for item in candidate["derived_family_hypotheses"]] == [
        "CDKT",
        "KQKD",
        "LCTT",
        "TM",
    ]
    assert all(item["candidate_exact_match"] for item in candidate["derived_family_hypotheses"])
    assert "end_page" not in candidate["derived_family_hypotheses"][-1]
    assert candidate["derived_family_hypotheses"][-1]["comparison_kind"] == (
        "START_PAGE_ONLY_NO_END_OR_COVERAGE_CLAIM"
    )
    assert document["off_balance_signal_comparisons"] == [
        {
            "role_a_block_id": "OFF_BALANCE",
            "start_page": 3,
            "end_page": 3,
            "placement": "EMBEDDED_BOTTOM_REGION",
            "signal_page_hits": [3],
            "has_off_balance_signal_hypothesis": True,
            "diagnostic_only_no_block_inference": True,
        }
    ]
    assert artifact["corpus_metrics"]["complete_page_count"] == 7
    assert artifact["corpus_metrics"]["terminal_page_count"] == 1
    assert artifact["corpus_metrics"]["complete_family_agreement_count"] == 7
    assert artifact["corpus_metrics"]["top1"]["candidate_comparison_count"] == 4
    assert artifact["corpus_metrics"]["top1"]["unique_exact_reference_match_count"] == 4
    assert (
        artifact["corpus_metrics"]["top1"]["exact_candidate_precision_against_machine_reference"]
        == 1.0
    )


def test_range_overlap_and_iou_are_not_promoted_to_exact() -> None:
    role_b, role_a, source = _synthetic_inputs()
    cdkt = role_a["documents"][0]["statement_blocks"][0]
    cdkt["end_page"] = 2
    artifact = _build_synthetic(role_b, role_a, source)
    hypothesis = artifact["documents"][0]["candidate_comparisons"][0]["derived_family_hypotheses"][
        0
    ]
    assert hypothesis["candidate_exact_match"] is False
    assert hypothesis["candidate_overlap_match"] is True
    assert hypothesis["reference_comparisons"][0] == {
        "role_a_block_id": "CDKT",
        "exact_range": False,
        "overlap": True,
        "intersection_page_count": 1,
        "union_page_count": 2,
        "intersection_over_union": 0.5,
    }
    assert artifact["documents"][0]["failure_classes"] == ["TOP1_CDKT_OVERLAP_NOT_EXACT"]


def test_duplicate_copy_references_and_unit_overrides_are_not_collapsed() -> None:
    role_b, role_a, source = _synthetic_inputs()
    duplicate = _reference_block("CDKT_COPY_B", "CDKT_MAIN", 2, 3)
    duplicate["copy_id"] = "B"
    duplicate["visible_unit_override"] = "THOUSAND_VND_VISIBLE_COPY"
    role_a["documents"][0]["statement_blocks"].insert(1, duplicate)
    artifact = _build_synthetic(role_b, role_a, source)
    references = artifact["documents"][0]["role_a_reference_receipt"]["statement_blocks"]
    assert [item["block_id"] for item in references[:2]] == ["CDKT", "CDKT_COPY_B"]
    assert references[1]["visible_unit_override"] == "THOUSAND_VND_VISIBLE_COPY"
    assert artifact["corpus_metrics"]["role_a_main_reference_block_count"] == 5
    assert artifact["corpus_metrics"]["top1"]["candidate_comparison_count"] == 4
    assert artifact["corpus_metrics"]["top1"]["unique_exact_reference_match_count"] == 5


def test_oracle_retains_alternatives_but_unique_reference_matches_do_not_double_count() -> None:
    role_b, role_a, source = _synthetic_inputs(candidate_count=2)
    artifact = _build_synthetic(role_b, role_a, source)
    metrics = artifact["corpus_metrics"]
    assert metrics["top1"]["candidate_comparison_count"] == 4
    assert metrics["oracle_any"]["candidate_comparison_count"] == 8
    assert metrics["oracle_any"]["exact_candidate_match_count"] == 8
    assert metrics["oracle_any"]["unique_exact_reference_match_count"] == 4
    assert artifact["failure_class_rollups"]["multi_alternative_document_count"] == 1
    assert artifact["documents"][0]["failure_classes"] == ["MULTI_ALTERNATIVE_HYPOTHESES"]


@pytest.mark.parametrize(
    "terminal_last,expected_class",
    [
        (True, "ZERO_CANDIDATE_WITH_TERMINAL_BARRIER"),
        (False, "ZERO_CANDIDATE_WITHOUT_TERMINAL_BARRIER"),
    ],
)
def test_zero_candidate_failure_class_is_derived(terminal_last: bool, expected_class: str) -> None:
    role_b, role_a, source = _synthetic_inputs(terminal_last=terminal_last, candidate_count=0)
    artifact = _build_synthetic(role_b, role_a, source)
    assert artifact["documents"][0]["failure_classes"] == [expected_class]
    assert artifact["failure_class_rollups"]["zero_candidate_document_count"] == 1


def test_source_sha_is_only_join_key_and_bank_is_provenance_only() -> None:
    first = _synthetic_inputs(source_sha="a" * 64, bank="FIRST")
    second = _synthetic_inputs(source_sha="b" * 64, bank="SECOND")
    role_b = copy.deepcopy(first[0])
    role_b["documents"].extend(second[0]["documents"])
    role_a = copy.deepcopy(first[1])
    role_a["documents"] = [*second[1]["documents"], *first[1]["documents"]]
    source = {"pages": [*first[2]["pages"], *second[2]["pages"]]}
    artifact = _build_synthetic(role_b, role_a, source)
    assert [item["source_sha256"] for item in artifact["documents"]] == ["a" * 64, "b" * 64]
    assert [item["bank"] for item in artifact["documents"]] == ["FIRST", "SECOND"]
    changed = copy.deepcopy(role_a)
    changed["documents"][0]["bank"] = "CHANGED_PROVENANCE"
    changed_artifact = _build_synthetic(role_b, changed, source)
    assert changed_artifact["corpus_metrics"] == artifact["corpus_metrics"]
    assert (
        changed_artifact["documents"][1]["candidate_comparisons"]
        == artifact["documents"][1]["candidate_comparisons"]
    )


def test_compact_inventory_physical_axis_is_authenticated_not_assumed() -> None:
    role_b, role_a, source = _synthetic_inputs()
    source["pages"][0]["physical_page"], source["pages"][1]["physical_page"] = (
        source["pages"][1]["physical_page"],
        source["pages"][0]["physical_page"],
    )
    with pytest.raises(agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error, match="physical-page"):
        _build_synthetic(role_b, role_a, source)


def test_no_drop_rejects_missing_projection_and_duplicate_source_join() -> None:
    role_b, role_a, source = _synthetic_inputs()
    source["pages"].pop()
    with pytest.raises(agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error):
        _build_synthetic(role_b, role_a, source)
    role_b, role_a, source = _synthetic_inputs()
    role_a["documents"].append(copy.deepcopy(role_a["documents"][0]))
    with pytest.raises(agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error, match="duplicated"):
        _build_synthetic(role_b, role_a, source)


def test_replay_validator_rejects_self_refreshed_receipt_and_metric_tamper() -> None:
    role_b, role_a, source = _synthetic_inputs()
    artifact = _build_synthetic(role_b, role_a, source)
    artifact["documents"][0]["candidate_comparisons"][0]["diagnostic_score"] = 99.0
    artifact["corpus_metrics"]["top1"]["exact_candidate_match_count"] = 0
    _refresh_identity(artifact)
    with pytest.raises(
        agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error,
        match="exact input replay",
    ):
        _validate_synthetic(artifact, role_b, role_a, source)


def test_claim_boundary_and_finalized_expected_metrics_are_exact() -> None:
    role_b, role_a, source = _synthetic_inputs()
    assert _typed_shape(_build_synthetic(role_b, role_a, source)["corpus_metrics"]) == _typed_shape(
        agreement_v1._FINALIZED_METRIC_PROJECTION
    )
    assert agreement_v1._FINALIZED_METRIC_PROJECTION["role_a_reference_block_counts"] == {
        "CDKT_MAIN": 28,
        "OFF_BALANCE": 28,
        "KQKD": 28,
        "LCTT": 28,
        "TM": 27,
    }
    assert agreement_v1._FINALIZED_METRIC_PROJECTION["top1"]["candidate_comparison_count"] == 52
    assert (
        agreement_v1._FINALIZED_METRIC_PROJECTION["top1"]["unique_exact_reference_match_count"]
        == 40
    )
    assert (
        agreement_v1._FINALIZED_METRIC_PROJECTION["top1"]["unique_overlap_reference_match_count"]
        == 52
    )
    assert (
        agreement_v1._FINALIZED_METRIC_PROJECTION["top1"][
            "exact_candidate_precision_against_machine_reference"
        ]
        == 0.769230769231
    )
    assert (
        agreement_v1._FINALIZED_METRIC_PROJECTION["oracle_any"]["candidate_comparison_count"] == 96
    )
    assert agreement_v1._FINALIZED_METRIC_PROJECTION["complete_family_agreement_count"] == 983
    assert agreement_v1._FINALIZED_METRIC_PROJECTION["complete_family_disagreement_count"] == 407
    assert agreement_v1._FINALIZED_METRIC_PROJECTION["complete_page_count"] == 1_390
    assert (
        agreement_v1._FINALIZED_FAILURE_ROLLUPS["tm_reference_page_hypothesized_other_count"] == 347
    )
    assert agreement_v1._SAFETY["human_gold"] is False
    assert agreement_v1._SAFETY["accuracy_claimed"] is False
    assert agreement_v1._SAFETY["tm_coverage_claimed"] is False
    assert agreement_v1._SAFETY["bank_identity_used_for_join_or_routing"] is False


def test_exclusive_publisher_seals_mode_nlink_bytes_and_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Path("output/survey/agreement.json")
    (tmp_path / target.parent).mkdir(parents=True)
    monkeypatch.setattr(
        agreement_v1,
        "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1",
        target,
    )
    payload = canonical_json_bytes_v1({"sealed": True})
    path = agreement_v1._publish_canonical_exclusive(tmp_path, payload)
    identity = path.stat()
    assert path.read_bytes() == payload
    assert stat.S_IMODE(identity.st_mode) == 0o444
    assert identity.st_nlink == 1
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
    with pytest.raises(
        agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error, match="already exists"
    ):
        agreement_v1._publish_canonical_exclusive(tmp_path, payload)
    assert path.read_bytes() == payload


def test_publisher_cleans_owned_temp_on_prelink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Path("output/survey/agreement.json")
    (tmp_path / target.parent).mkdir(parents=True)
    monkeypatch.setattr(
        agreement_v1,
        "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1",
        target,
    )

    def fail_write(_descriptor: int, _payload: bytes) -> int:
        raise OSError("injected write failure")

    monkeypatch.setattr(agreement_v1.os, "write", fail_write)
    with pytest.raises(agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error):
        agreement_v1._publish_canonical_exclusive(
            tmp_path, canonical_json_bytes_v1({"sealed": True})
        )
    assert not (tmp_path / target).exists()
    assert not list((tmp_path / target.parent).glob(".*.tmp"))


def test_publisher_loses_hardlink_race_without_touching_rival(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Path("output/survey/agreement.json")
    (tmp_path / target.parent).mkdir(parents=True)
    monkeypatch.setattr(
        agreement_v1,
        "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1",
        target,
    )
    original_link = agreement_v1.os.link

    def install_rival_then_link(*args: Any, **kwargs: Any) -> None:
        (tmp_path / target).write_bytes(b"rival")
        original_link(*args, **kwargs)

    monkeypatch.setattr(agreement_v1.os, "link", install_rival_then_link)
    with pytest.raises(
        agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error, match="exclusive race"
    ):
        agreement_v1._publish_canonical_exclusive(
            tmp_path, canonical_json_bytes_v1({"sealed": True})
        )
    assert (tmp_path / target).read_bytes() == b"rival"
    assert not list((tmp_path / target.parent).glob(".*.tmp"))


def test_destination_absence_is_checked_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = Path("output/survey/agreement.json")
    (tmp_path / target.parent).mkdir(parents=True)
    (tmp_path / target).write_bytes(b"foreign")
    monkeypatch.setattr(
        agreement_v1,
        "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1",
        target,
    )
    called = False

    def forbidden_build(_project_root: Path) -> dict[str, Any]:
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr(
        agreement_v1,
        "build_wave1_role_b_vs_role_a_level1_agreement_v1",
        forbidden_build,
    )
    with pytest.raises(
        agreement_v1.Wave1RoleBVsRoleALevel1AgreementV1Error, match="already exists"
    ):
        agreement_v1.publish_wave1_role_b_vs_role_a_level1_agreement_v1(tmp_path)
    assert called is False
    assert (tmp_path / target).read_bytes() == b"foreign"


def test_import_closure_and_forbidden_authority_surface_are_exact() -> None:
    module_path = PROJECT_ROOT / agreement_v1._IMPLEMENTATION_RELATIVE_PATH
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    source = module_path.read_text(encoding="utf-8")
    assert "os.replace" not in source
    call_names = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert call_names.isdisjoint(
        {
            "open_finalized_v3_survey_stream_v1",
            "project_authenticated_page_v2",
            "generate_page_geometry_proposals_v1",
            "locate_statement_pages",
            "discover_statement_pages_v4",
            "render_composited_displayed_page",
            "read_causal_native_text_page",
        }
    )
    implementation_paths = set(agreement_v1._IMPLEMENTATION_PATHS)
    assert len(implementation_paths) == 37
    assert all((PROJECT_ROOT / path).is_file() for path in implementation_paths)

    package_root = Path("src/bctc_ai")

    def with_initializers(relative: Path) -> set[Path]:
        discovered = {relative}
        parent = relative.parent
        while parent == package_root or package_root in parent.parents:
            initializer = parent / "__init__.py"
            if (PROJECT_ROOT / initializer).is_file():
                discovered.add(initializer)
            if parent == package_root:
                break
            parent = parent.parent
        return discovered

    def local_module_path(module: str) -> Path | None:
        if not module.startswith("bctc_ai"):
            return None
        candidate = Path("src", *module.split(".")).with_suffix(".py")
        if (PROJECT_ROOT / candidate).is_file():
            return candidate
        initializer = Path("src", *module.split("."), "__init__.py")
        return initializer if (PROJECT_ROOT / initializer).is_file() else None

    closure = with_initializers(agreement_v1._IMPLEMENTATION_RELATIVE_PATH)
    pending = list(closure)
    while pending:
        relative = pending.pop()
        local_tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(local_tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [
                    node.module,
                    *(f"{node.module}.{alias.name}" for alias in node.names),
                ]
            for module in modules:
                candidate = local_module_path(module)
                if candidate is None:
                    continue
                for discovered in with_initializers(candidate) - closure:
                    closure.add(discovered)
                    pending.append(discovered)
    closure.update(with_initializers(Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py")))
    assert closure == implementation_paths
    assert agreement_v1._ROLE_B_SHA256 == (
        "9e4c849ec17d01cc683df223bc44c29f0949bf4d8b46c557144537056bcc15b8"
    )
    assert agreement_v1._ROLE_A_SHA256 == (
        "2be9843943114602ab6a1e901dbb475ca80642068cfe31b1ba7e0a6d550c3577"
    )
