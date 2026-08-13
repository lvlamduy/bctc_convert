from __future__ import annotations

import copy
import pickle

import pytest

from bctc_ai.mapping.codex_mapped_item_verification_v1 import (
    AuthenticatedCodexMappedItemVerificationRequestV1,
    CodexMappedItemVerificationV1Error,
    _expected_pixel_readback,
    _mint_request_receipt,
    _mint_review_receipt,
    _required_check_keys,
    _validate_request,
    assemble_codex_mapped_item_verification_v1,
    build_codex_mapped_item_review_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _claim(role: str, schema_id: int | None, ordinal: int) -> dict:
    mapped = schema_id is not None
    result = {
        "claim_kind": "MAPPED_SCHEMA_ROW" if mapped else "SOURCE_ONLY_VALIDATION",
        "typed_role": role,
        "report_norm_id": schema_id,
        "schema_binding": (
            {
                "schema_namespace": "TM",
                "canonical_name": f"schema {schema_id}",
                "parent_report_norm_id": 752,
                "ancestor_report_norm_ids": [752, 716, 560],
                "display_order": 201 + ordinal,
                "mapping_eligible": True,
                "candidate_disposition": "VALUE_ROW_SCHEMA_CANDIDATE",
            }
            if mapped
            else None
        ),
        "row_graph_node_id": f"slagv2:node:{role.lower():0<64}",
        "row_ordinal": ordinal,
        "label_evidence": (
            {
                "source_atom_id": f"ssv1:atom:{role.lower():0<64}",
                "source_evidence_node_id": f"slagv2:node:{('e-' + role.lower()):0<64}",
                "source_line_index": ordinal,
                "raw_text_utf8": role,
                "text_source": "VIETOCR_VGG_TRANSFORMER_0_3_13",
                "pixel_bbox": [10, 20 + ordinal * 10, 50, 28 + ordinal * 10],
                "canonical_bbox_mpt": [3600, 7200, 18000, 10080],
            }
            if mapped
            else None
        ),
        "values": [
            {
                "axis_index": axis,
                "graph_node_id": f"slagv2:node:{(role.lower() + str(axis)):0<64}",
                "source_evidence": {
                    "source_atom_id": f"ssv1:atom:{(role.lower() + str(axis)):0<64}",
                    "source_evidence_node_id": f"slagv2:node:{('e' + role.lower() + str(axis)):0<64}",
                    "source_line_index": ordinal * 3 + axis,
                    "raw_text_utf8": str((ordinal + 1) * 100 + axis),
                    "text_source": "PPOCRV6_NUMERIC_ONLY",
                    "pixel_bbox": [100 + axis * 100, 20, 150 + axis * 100, 30],
                    "canonical_bbox_mpt": [36000, 7200, 54000, 10800],
                },
                "raw_text": str((ordinal + 1) * 100 + axis),
                "normalized_decimal": str((ordinal + 1) * 100 + axis),
                "state": "OBSERVED_VALUE",
                "sign_evidence": None,
                "independent_numeric": {
                    "cell_id": f"cell-{ordinal}-{axis}",
                    "verification_status": "VERIFIED_OBSERVED_VALUE",
                    "decision": "ACCEPT_EXACT_VALUE_AND_SIGN_AGREEMENT",
                    "challenger_raw_text": str((ordinal + 1) * 100 + axis),
                    "challenger_parsed_value": str((ordinal + 1) * 100 + axis),
                    "challenger_sign_evidence": None,
                    "crop_path": f"crop-{ordinal}-{axis}.png",
                    "crop_sha256": "a" * 64,
                    "crop_size_bytes": 1,
                },
            }
            for axis in (0, 1)
        ],
        "population_scope": (
            "STRICT_THREE_ROW_CORE" if mapped else "SOURCE_ONLY_TOTAL_OF_STRICT_THREE_ROW_CORE"
        ),
    }
    result["claim_id"] = f"cimvrqv1:claim:{canonical_json_sha256_v1(result)}"
    return result


def _request() -> dict:
    claims = [
        _claim("SHORT_TERM", 753, 0),
        _claim("MEDIUM_TERM", 754, 1),
        _claim("LONG_TERM", 755, 2),
        _claim("TOTAL", None, 3),
    ]
    payload = {
        "format_version": "CODEX_MAPPED_ITEM_VERIFICATION_REQUEST_V1",
        "state": "FROZEN_BEFORE_CODEX_REVIEW",
        "claim_boundary": (
            "REPLAY_BOUND_SOURCE_SCHEMA_AND_NUMERIC_EVIDENCE_REQUEST_ONLY_NO_CODEX_DECISION_"
            "ACCEPTED_MAPPING_CANONICALIZATION_VALUE_MATERIALIZATION_ABSENCE_EXPORT_OR_"
            "PRODUCTION_AUTHORITY"
        ),
        "family_id": "LOAN_MATURITY_BUCKETS",
        "family_spec_sha256": "b" * 64,
        "source_authority": {
            "document_id": f"sha256:{'c' * 64}",
            "physical_page": 999,
            "source_pdf": {"path": "fake.pdf", "sha256": "c" * 64, "size_bytes": 1},
            "target_page_render": {
                "path": "fake.png",
                "sha256": "d" * 64,
                "size_bytes": 1,
                "pixel_width": 10,
                "pixel_height": 10,
            },
            "source_local_page_id": f"ssv2:page:{'e' * 64}",
            "source_projection_sha256": "f" * 64,
            "page_result_sha256": "1" * 64,
        },
        "input_identities": {
            "semantic_graph": {
                "graph_id": f"slagv2:graph:{'2' * 64}",
                "sha256": "3" * 64,
            },
            "semantic_page_binding_sha256": "4" * 64,
            "statement_context": {
                "context_id": f"sscxtv1:context:{'5' * 64}",
                "sha256": "6" * 64,
            },
            "schema_candidate": {
                "candidate_set_id": f"slascv1:candidate:{'7' * 64}",
                "sha256": "8" * 64,
            },
            "numeric_verification": {
                "sha256": "9" * 64,
                "size_bytes": 1,
                "verification_id": f"sgnpvv1:verification:{'a' * 64}",
                "path": "docs/experiments/fake.json",
            },
            "schema_authority": {},
        },
        "inference_firewall": {},
        "table_context": {
            "statement": {
                "statement_type": "TM",
                "report_scope": "CONSOLIDATED",
                "continuation": True,
                "heading_evidence": {"raw_transformer_text_utf8": "FORGED"},
            },
            "owner": {"source_evidence": {"raw_text_utf8": "FORGED OWNER"}},
            "branch": {"source_evidence": {"raw_text_utf8": "FORGED BRANCH"}},
            "axes": [
                {"source_evidence": {"raw_text_utf8": "30/6/2026"}},
                {"source_evidence": {"raw_text_utf8": "31/12/2025"}},
            ],
            "unit_scopes": [
                {"source_evidence": {"raw_text_utf8": "Triệu đồng"}},
                {"source_evidence": {"raw_text_utf8": "Triệu đồng"}},
            ],
            "row_order": ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL"],
            "population_scope": "STRICT_THREE_ROW_CORE_PLUS_SOURCE_ONLY_TOTAL",
        },
        "item_claims": claims,
        "arithmetic_closure": {
            "population_roles": ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"],
            "source_only_total_role": "TOTAL",
            "same_population_claimed": False,
            "equations": [],
        },
        "near_neighbour_candidates": [
            {
                "report_norm_id": 5747,
                "parent_report_norm_id": 752,
                "mapping_eligible": True,
                "schema_context_status": "RESOLVED",
                "whole_document_absence_claim_allowed": False,
            },
            {
                "report_norm_id": 1944,
                "parent_report_norm_id": None,
                "mapping_eligible": False,
                "schema_context_status": "UNRESOLVED_ORPHAN",
                "whole_document_absence_claim_allowed": False,
            },
        ],
        "required_check_policy": {
            "table_checks": [
                "SOURCE_BYTES_AND_PAGE",
                "AUTHENTICATED_PIXEL_BINDING",
                "ROLE_A_FIREWALL",
                "STATEMENT_TYPE_SCOPE",
                "OWNER_BRANCH_LOCALITY",
                "AXIS_PERIOD_IDENTITY_AND_ORDER",
                "PER_AXIS_UNIT_SCOPE",
                "OPTIONAL_ROW_POPULATION_BOUNDARY",
                "ARITHMETIC_CLOSURE",
                "PROVENANCE_COMPLETENESS",
            ],
            "mapped_schema_row_checks": [
                "ROW_LABEL_TYPED_ROLE",
                "ROW_VALUE_GEOMETRY",
                "NUMERIC_DIGIT_AND_SIGN_AGREEMENT",
                "SCHEMA_NAMESPACE_PARENT_ANCESTOR",
                "SCHEMA_SINGLETON_AND_MAPPING_ELIGIBILITY",
                "SIBLING_DISPLAY_ORDER",
                "NO_DUPLICATE_ROLE_OR_ID",
            ],
            "source_only_validation_checks": [
                "ROW_VALUE_GEOMETRY",
                "NUMERIC_DIGIT_AND_SIGN_AGREEMENT",
                "TOTAL_SCOPE",
            ],
            "any_fail_or_missing_check_status": "UNRESOLVED",
            "all_required_checks_pass_status": "VERIFIED_BY_CODEX",
        },
        "safety": {
            "upstream_exact_replay_required": True,
            "role_a_or_human_answer_used": False,
            "history_or_mongodb_used": False,
            "bank_page_note_identity_used_for_routing": False,
            "caller_final_status_allowed": False,
            "accepted_mapping_authority": False,
            "whole_document_absence_authority": False,
            "canonicalization_authority": False,
            "value_materialization_authority": False,
            "export_authority": False,
            "production_authority": False,
        },
    }
    payload["request_id"] = f"cimvrqv1:request:{canonical_json_sha256_v1(payload)}"
    return payload


def _all_pass_review(receipt, request):
    checks = [
        {
            "claim_id": claim_id,
            "check_id": check_id,
            "status": "PASS",
            "evidence_refs": [claim_id or request["request_id"]],
            "falsifier_code": None,
            "rationale": "fixture pass",
        }
        for claim_id, check_id in _required_check_keys(request)
    ]
    return build_codex_mapped_item_review_v1(
        receipt,
        reviewer={
            "kind": "CODEX_INDEPENDENT_SOURCE_REVIEW",
            "review_run_id": "unit-fixture",
        },
        pixel_readback=_expected_pixel_readback(request),
        check_results=checks,
        near_neighbour_dispositions=[
            {
                "report_norm_id": 5747,
                "status": "UNRESOLVED",
                "disposition": "NOT_OBSERVED_IN_BOUND_SOURCE_TABLE",
                "whole_document_absence_claim": False,
                "evidence_refs": [request["request_id"]],
            },
            {
                "report_norm_id": 1944,
                "status": "UNRESOLVED",
                "disposition": "SCHEMA_CONTEXT_UNRESOLVED_ORPHAN_MAPPING_INELIGIBLE",
                "whole_document_absence_claim": False,
                "evidence_refs": [request["request_id"]],
            },
        ],
    )


def test_opaque_receipt_cannot_be_caller_constructed() -> None:
    with pytest.raises(CodexMappedItemVerificationV1Error, match="caller-constructed"):
        AuthenticatedCodexMappedItemVerificationRequestV1(object())

    request = _validate_request(_request())
    receipt = _mint_request_receipt(request)
    with pytest.raises(CodexMappedItemVerificationV1Error, match="copied"):
        copy.copy(receipt)
    with pytest.raises(CodexMappedItemVerificationV1Error, match="deep-copied"):
        copy.deepcopy(receipt)
    with pytest.raises(CodexMappedItemVerificationV1Error, match="serialized"):
        pickle.dumps(receipt)
    forged_handle = object.__new__(AuthenticatedCodexMappedItemVerificationRequestV1)
    review = _all_pass_review(receipt, request)
    review_receipt = _mint_review_receipt(review, request)
    with pytest.raises(CodexMappedItemVerificationV1Error, match="unknown or expired"):
        assemble_codex_mapped_item_verification_v1(forged_handle, review_receipt)


def test_coordinated_self_rehash_attack_has_no_public_assembly_path() -> None:
    forged = _validate_request(_request())
    # This private mint demonstrates the payload is internally well-formed; callers do not
    # possess the token or a public mint API. A plain self-rehashed JSON cannot cross assembly.
    receipt = _mint_request_receipt(forged)
    review = _all_pass_review(receipt, forged)
    review_receipt = _mint_review_receipt(review, forged)
    assert assemble_codex_mapped_item_verification_v1(receipt, review_receipt)["metrics"] == {
        "verified_mapped_row_count": 3,
        "verified_source_only_validation_count": 1,
        "unresolved_item_count": 0,
        "unresolved_near_neighbour_count": 2,
    }
    with pytest.raises(CodexMappedItemVerificationV1Error, match="authenticated request"):
        assemble_codex_mapped_item_verification_v1(  # type: ignore[arg-type]
            forged, review_receipt
        )
    with pytest.raises(CodexMappedItemVerificationV1Error, match="authenticated Codex review"):
        assemble_codex_mapped_item_verification_v1(receipt, review)  # type: ignore[arg-type]


def test_failed_item_check_derives_unresolved_and_total_never_maps() -> None:
    request = _validate_request(_request())
    receipt = _mint_request_receipt(request)
    review = _all_pass_review(receipt, request)
    failed = copy.deepcopy(review)
    target = next(
        item
        for item in failed["check_results"]
        if item["claim_id"] == request["item_claims"][1]["claim_id"]
        and item["check_id"] == "NUMERIC_DIGIT_AND_SIGN_AGREEMENT"
    )
    target.update(
        {
            "status": "FAIL",
            "falsifier_code": "NUMERIC_DIGIT_MISMATCH",
            "rationale": "independent digits disagree",
        }
    )
    failed.pop("review_id")
    failed["review_id"] = f"codexmirv1:review:{canonical_json_sha256_v1(failed)}"
    failed_receipt = _mint_review_receipt(failed, request)
    result = assemble_codex_mapped_item_verification_v1(receipt, failed_receipt)
    assert [item["status"] for item in result["item_verdicts"]] == [
        "VERIFIED_BY_CODEX",
        "UNRESOLVED",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
    ]
    total = result["item_verdicts"][-1]
    assert total["report_norm_id"] is None
    assert total["schema_binding"] is None
    assert total["authority"]["accepted_mapping_for_exact_bound_source_observation"] is False
