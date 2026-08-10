from __future__ import annotations

from copy import deepcopy

import pytest
from test_source_structure_evidence_projection_v1 import (
    _line_supplement,
    _native_complete,
    _native_nonmonotonic_visual_order_complete,
    _ocr_complete,
    _ocr_terminal,
    _refresh_result_ref,
)

from bctc_ai.source_structure.contracts_v1 import (
    ATOM_DISPOSITION_FORMAT_VERSION,
    TOPOLOGY_FEATURE_FORMAT_VERSION,
    VALUE_SEMANTICS_FORMAT_VERSION,
    PrimaryDisposition,
    SourceStructureContractError,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    make_empty_page_proposal_set_v1,
    make_page_proposal_set_v1,
    make_source_object_id_v1,
    make_topology_fingerprint_v1,
    same_typed_json_v1,
    validate_neutral_page_envelope_v1,
    validate_value_semantics_v1,
)
from bctc_ai.source_structure.evidence_projection_v1 import project_authenticated_page_v1


def _ocr_envelope():
    record, result = _ocr_complete()
    return project_authenticated_page_v1(page_record=record, page_result=result)


def _ocr_value_envelope(raw_text: str):
    record, result = _ocr_complete()
    result["lines"][0]["raw_text"] = raw_text
    result["lines"][0]["words"][0]["raw_text"] = raw_text
    result["words"][0]["raw_text"] = raw_text
    _refresh_result_ref(record, result)
    return project_authenticated_page_v1(page_record=record, page_result=result)


def _word_atom(envelope: dict):
    return next(atom for atom in envelope["atoms"] if atom["kind"] == "WORD")


def _terminal_envelope():
    record, result = _ocr_terminal()
    supplement, supplement_ref = _line_supplement(record, result)
    return project_authenticated_page_v1(
        page_record=record,
        page_result=result,
        line_only_supplement=supplement,
        line_only_supplement_ref=supplement_ref,
    )


def _owned_proposal_inputs(envelope: dict, atom_ids: list[str], bbox: list[int]):
    basis = {
        "source_local_page_id": envelope["source_local_page_id"],
        "request_sha256": envelope["source_locator"]["request_sha256"],
        "kind": "SOURCE_BLOCK_CANDIDATE",
        "canonical_bbox_mpt": bbox,
        "primary_atom_ids": atom_ids,
        "supporting_atom_ids": [],
        "evidence_codes": ["LOCAL_GEOMETRY"],
    }
    proposal_id = make_source_object_id_v1("source_object", basis)
    proposal = {
        "source_local_id": proposal_id,
        "kind": basis["kind"],
        "canonical_bbox_mpt": bbox,
        "primary_atom_ids": atom_ids,
        "supporting_atom_ids": [],
        "evidence_codes": basis["evidence_codes"],
    }
    dispositions = make_empty_page_proposal_set_v1(envelope)["dispositions"]
    for disposition in dispositions:
        if disposition["source_atom_id"] in atom_ids:
            disposition.update(
                {
                    "primary_disposition": PrimaryDisposition.OWNED_BY_SOURCE_OBJECT.value,
                    "source_object_id": proposal_id,
                    "reason_code": "PRIMARY_LOCAL_GEOMETRY_OWNERSHIP",
                }
            )
    return proposal, dispositions


def test_canonical_json_is_typed_closed_and_byte_exact() -> None:
    integer = {"value": 1}
    floating = {"value": 1.0}
    assert canonical_json_sha256_v1(integer) != canonical_json_sha256_v1(floating)
    assert canonical_json_sha256_v1({"value": -0.0}) != canonical_json_sha256_v1({"value": 0.0})
    assert not same_typed_json_v1(-0.0, 0.0)
    assert not same_typed_json_v1(True, 1)
    assert not same_typed_json_v1(1, 1.0)
    assert decode_canonical_json_bytes_v1(canonical_json_bytes_v1(integer)) == integer
    with pytest.raises(SourceStructureContractError, match="canonical V1"):
        decode_canonical_json_bytes_v1(b'{"value": 1}\n')
    with pytest.raises(SourceStructureContractError, match="duplicate"):
        decode_canonical_json_bytes_v1(b'{"value":1,"value":2}\n')
    with pytest.raises(SourceStructureContractError, match="non-finite"):
        canonical_json_bytes_v1({"value": float("nan")})


def test_provenance_ids_do_not_collide_but_topology_fingerprint_is_identity_free() -> None:
    first_record, first_result = _ocr_complete(source_sha="a" * 64, page=1)
    second_record, second_result = _ocr_complete(source_sha="9" * 64, page=8)
    first = project_authenticated_page_v1(
        page_record=first_record,
        page_result=first_result,
    )
    second = project_authenticated_page_v1(
        page_record=second_record,
        page_result=second_result,
    )
    assert first["source_local_page_id"] != second["source_local_page_id"]
    assert first["atoms"][0]["source_local_id"] != second["atoms"][0]["source_local_id"]

    features = {
        "format_version": TOPOLOGY_FEATURE_FORMAT_VERSION,
        "evidence_mode": "OCR_PRIMARY",
        "page_orientation": "PORTRAIT",
        "primary_line_count_bucket": "ONE",
        "primary_word_count_bucket": "ONE",
        "supplemental_line_count_bucket": "ZERO",
        "quarantine_count_bucket": "ZERO",
        "source_object_kind_sequence": ["SOURCE_BLOCK_CANDIDATE"],
        "relation_code_sequence": ["VERTICAL_SUCCESSOR"],
    }
    assert make_topology_fingerprint_v1(features) == make_topology_fingerprint_v1(
        deepcopy(features)
    )
    assert make_topology_fingerprint_v1(features) != make_topology_fingerprint_v1(
        {**features, "primary_line_count_bucket": "TWO_TO_FOUR"}
    )
    for key, value in (
        ("document_id", "doc"),
        ("doc_digest", "0" * 64),
        ("request_sha256", "0" * 64),
        ("path", "/tmp/input.pdf"),
        ("physical_page", 1),
        ("page_number", 1),
        ("absolute_bbox_mpt", [1, 2, 3, 4]),
    ):
        with pytest.raises(SourceStructureContractError, match="identity/reference|fields drifted"):
            make_topology_fingerprint_v1({**features, key: value})

    forbidden_value = deepcopy(features)
    forbidden_value["evidence_mode"] = "ROLE_A_SCHEMA_REPORTNORMID_BANK_ACB"
    with pytest.raises(SourceStructureContractError, match="identity/reference"):
        make_topology_fingerprint_v1(forbidden_value)

    unknown_relation = deepcopy(features)
    unknown_relation["relation_code_sequence"] = ["DOC_DIGEST_PAGE_NUMBER"]
    with pytest.raises(SourceStructureContractError, match="relation-code"):
        make_topology_fingerprint_v1(unknown_relation)


def test_no_drop_and_exactly_one_primary_disposition() -> None:
    envelope = _ocr_envelope()
    empty = make_empty_page_proposal_set_v1(envelope)
    assert len(empty["dispositions"]) == len(envelope["atoms"])
    assert {item["source_atom_id"] for item in empty["dispositions"]} == {
        atom["source_local_id"] for atom in envelope["atoms"]
    }

    missing = deepcopy(empty)
    missing["dispositions"].pop()
    with pytest.raises(SourceStructureContractError, match="every atom"):
        make_page_proposal_set_v1(
            envelope,
            proposals=missing["proposals"],
            dispositions=missing["dispositions"],
        )

    duplicated = deepcopy(empty)
    duplicated["dispositions"].append(deepcopy(duplicated["dispositions"][0]))
    with pytest.raises(SourceStructureContractError, match="duplicated"):
        make_page_proposal_set_v1(
            envelope,
            proposals=duplicated["proposals"],
            dispositions=duplicated["dispositions"],
        )


def test_proposal_evidence_and_disposition_reasons_use_closed_vocabularies() -> None:
    envelope = _ocr_envelope()
    empty = make_empty_page_proposal_set_v1(envelope)
    atom = envelope["atoms"][0]
    basis = {
        "source_local_page_id": envelope["source_local_page_id"],
        "request_sha256": envelope["source_locator"]["request_sha256"],
        "kind": "SOURCE_BLOCK_CANDIDATE",
        "canonical_bbox_mpt": atom["canonical_bbox_mpt"],
        "primary_atom_ids": [atom["source_local_id"]],
        "supporting_atom_ids": [],
        "evidence_codes": ["ROLE_A_SCHEMA_REPORTNORMID_BANK_ACB"],
    }
    forbidden_proposal = {
        "source_local_id": make_source_object_id_v1("source_object", basis),
        "kind": basis["kind"],
        "canonical_bbox_mpt": basis["canonical_bbox_mpt"],
        "primary_atom_ids": basis["primary_atom_ids"],
        "supporting_atom_ids": basis["supporting_atom_ids"],
        "evidence_codes": basis["evidence_codes"],
    }
    with pytest.raises(SourceStructureContractError, match="closed V1 vocabulary"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[forbidden_proposal],
            dispositions=empty["dispositions"],
        )

    forbidden_reason = deepcopy(empty["dispositions"])
    forbidden_reason[0]["reason_code"] = "HISTORY_PATH_ROLE_A_BANK_HINT"
    with pytest.raises(SourceStructureContractError, match="closed V1 vocabulary"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[],
            dispositions=forbidden_reason,
        )


def test_primary_source_object_ownership_is_bidirectionally_closed() -> None:
    envelope = _ocr_envelope()
    empty = make_empty_page_proposal_set_v1(envelope)
    atom = envelope["atoms"][0]
    proposal_basis = {
        "source_local_page_id": envelope["source_local_page_id"],
        "request_sha256": envelope["source_locator"]["request_sha256"],
        "kind": "SOURCE_BLOCK_CANDIDATE",
        "canonical_bbox_mpt": atom["canonical_bbox_mpt"],
        "primary_atom_ids": [atom["source_local_id"]],
        "supporting_atom_ids": [],
        "evidence_codes": ["LOCAL_GEOMETRY"],
    }
    proposal_id = make_source_object_id_v1("source_object", proposal_basis)
    proposal = {
        "source_local_id": proposal_id,
        "kind": proposal_basis["kind"],
        "canonical_bbox_mpt": proposal_basis["canonical_bbox_mpt"],
        "primary_atom_ids": proposal_basis["primary_atom_ids"],
        "supporting_atom_ids": [],
        "evidence_codes": proposal_basis["evidence_codes"],
    }
    dispositions = deepcopy(empty["dispositions"])
    owned = next(item for item in dispositions if item["source_atom_id"] == atom["source_local_id"])
    owned.update(
        {
            "format_version": ATOM_DISPOSITION_FORMAT_VERSION,
            "primary_disposition": PrimaryDisposition.OWNED_BY_SOURCE_OBJECT.value,
            "source_object_id": proposal_id,
            "reason_code": "PRIMARY_LOCAL_GEOMETRY_OWNERSHIP",
        }
    )
    accepted = make_page_proposal_set_v1(
        envelope,
        proposals=[proposal],
        dispositions=dispositions,
    )
    assert accepted["proposals"][0]["source_local_id"] == proposal_id

    bad = deepcopy(dispositions)
    owned_bad = next(item for item in bad if item["source_atom_id"] == atom["source_local_id"])
    owned_bad["primary_disposition"] = PrimaryDisposition.RETAINED_UNOWNED.value
    owned_bad["source_object_id"] = None
    owned_bad["reason_code"] = "NO_SOURCE_OBJECT_OWNERSHIP_PROPOSED"
    with pytest.raises(SourceStructureContractError, match="ownership accounting"):
        make_page_proposal_set_v1(envelope, proposals=[proposal], dispositions=bad)

    second_basis = {**proposal_basis, "kind": "TABULAR_GEOMETRY_CANDIDATE"}
    second = {
        **proposal,
        "source_local_id": make_source_object_id_v1("source_object", second_basis),
        "kind": second_basis["kind"],
    }
    with pytest.raises(SourceStructureContractError, match="multiple source objects"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[proposal, second],
            dispositions=dispositions,
        )


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_ocr_proposal_bbox_is_page_bounded_and_contains_every_primary(rotation: int) -> None:
    record, result = _ocr_complete(rotation)
    envelope = project_authenticated_page_v1(page_record=record, page_result=result)
    atom = envelope["atoms"][0]
    atom_bbox = atom["canonical_bbox_mpt"]
    proposal, dispositions = _owned_proposal_inputs(
        envelope,
        [atom["source_local_id"]],
        atom_bbox,
    )
    assert (
        make_page_proposal_set_v1(
            envelope,
            proposals=[proposal],
            dispositions=dispositions,
        )["proposals"][0]["canonical_bbox_mpt"]
        == atom_bbox
    )

    noncontained_bbox = [atom_bbox[0], atom_bbox[1], atom_bbox[2] - 1, atom_bbox[3]]
    noncontained, noncontained_dispositions = _owned_proposal_inputs(
        envelope,
        [atom["source_local_id"]],
        noncontained_bbox,
    )
    with pytest.raises(SourceStructureContractError, match="contain every primary"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[noncontained],
            dispositions=noncontained_dispositions,
        )

    page_width, page_height = envelope["coordinate_authority"]["unrotated_dimensions_mpt"]
    off_page, off_page_dispositions = _owned_proposal_inputs(
        envelope,
        [atom["source_local_id"]],
        [-1, 0, page_width, page_height],
    )
    with pytest.raises(SourceStructureContractError, match="page bounds"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[off_page],
            dispositions=off_page_dispositions,
        )


def test_native_proposal_bbox_is_exact_nonnegative_primary_union() -> None:
    record, result = _native_nonmonotonic_visual_order_complete()
    envelope = project_authenticated_page_v1(page_record=record, page_result=result)
    primary_atoms = [atom for atom in envelope["atoms"] if atom["kind"] == "WORD"]
    primary_ids = [atom["source_local_id"] for atom in primary_atoms]
    union = [
        min(atom["canonical_bbox_mpt"][0] for atom in primary_atoms),
        min(atom["canonical_bbox_mpt"][1] for atom in primary_atoms),
        max(atom["canonical_bbox_mpt"][2] for atom in primary_atoms),
        max(atom["canonical_bbox_mpt"][3] for atom in primary_atoms),
    ]
    proposal, dispositions = _owned_proposal_inputs(envelope, primary_ids, union)
    assert (
        make_page_proposal_set_v1(
            envelope,
            proposals=[proposal],
            dispositions=dispositions,
        )["proposals"][0]["canonical_bbox_mpt"]
        == union
    )

    expanded = [union[0] - 1, union[1], union[2], union[3]]
    expanded_proposal, expanded_dispositions = _owned_proposal_inputs(
        envelope,
        primary_ids,
        expanded,
    )
    with pytest.raises(SourceStructureContractError, match="primary-atom union"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[expanded_proposal],
            dispositions=expanded_dispositions,
        )


def test_terminal_and_supplement_atoms_cannot_receive_source_object_ownership() -> None:
    envelope = _terminal_envelope()
    empty = make_empty_page_proposal_set_v1(envelope)
    atom = envelope["atoms"][0]
    proposal_basis = {
        "source_local_page_id": envelope["source_local_page_id"],
        "request_sha256": envelope["source_locator"]["request_sha256"],
        "kind": "SOURCE_BLOCK_CANDIDATE",
        "canonical_bbox_mpt": atom["canonical_bbox_mpt"],
        "primary_atom_ids": [atom["source_local_id"]],
        "supporting_atom_ids": [],
        "evidence_codes": ["LOCAL_GEOMETRY"],
    }
    proposal = {
        "source_local_id": make_source_object_id_v1("source_object", proposal_basis),
        "kind": proposal_basis["kind"],
        "canonical_bbox_mpt": proposal_basis["canonical_bbox_mpt"],
        "primary_atom_ids": proposal_basis["primary_atom_ids"],
        "supporting_atom_ids": [],
        "evidence_codes": proposal_basis["evidence_codes"],
    }
    with pytest.raises(SourceStructureContractError, match="promoted"):
        make_page_proposal_set_v1(
            envelope,
            proposals=[proposal],
            dispositions=empty["dispositions"],
        )


def test_quarantine_summary_has_authenticated_deterministic_identity_and_disposition() -> None:
    record, result = _native_complete()
    span = {
        "page": 1,
        "text_sha256": "8" * 64,
        "nonwhitespace_character_count": 4,
        "bbox_mpt": [10, 20, 30, 40],
        "block_number": 1,
        "line_number": 2,
        "span_number": 3,
        "color": 0,
        "alpha": 0,
        "render_sequence": 4,
        "occluding_sequence": 5,
        "occluding_object_type": "fill_path",
        "reason": "FULLY_OCCLUDED",
    }
    result["quarantined_spans"] = [span]
    result["metrics"]["quarantined_span_count"] = 1
    record["quarantined_span_count"] = 1
    encoded = canonical_json_bytes_v1(result)
    record["result_ref"] = {
        "path": (
            f"objects/sha256/{canonical_json_sha256_v1(result)[:2]}/"
            f"{canonical_json_sha256_v1(result)}.json"
        ),
        "sha256": canonical_json_sha256_v1(result),
        "size_bytes": len(encoded),
    }
    envelope = project_authenticated_page_v1(page_record=record, page_result=result)
    quarantine = next(atom for atom in envelope["atoms"] if atom["kind"] == "QUARANTINED_SPAN")
    assert quarantine["raw_text"] is None
    assert quarantine["raw_text_sha256"] is None
    assert quarantine["quarantine_summary"]["excluded_text_sha256"] == "8" * 64
    assert len(quarantine["quarantine_payload_sha256"]) == 64
    dispositions = make_empty_page_proposal_set_v1(envelope)["dispositions"]
    disposition = next(
        item for item in dispositions if item["source_atom_id"] == quarantine["source_local_id"]
    )
    assert disposition["primary_disposition"] == "UPSTREAM_QUARANTINED"

    tampered = deepcopy(envelope)
    quarantine_tampered = next(
        atom for atom in tampered["atoms"] if atom["kind"] == "QUARANTINED_SPAN"
    )
    quarantine_tampered["quarantine_summary"]["alpha"] = 1
    with pytest.raises(SourceStructureContractError, match="payload identity"):
        validate_neutral_page_envelope_v1(tampered)


def _value_record(
    *,
    status: str,
    raw_token,
    normalized_value,
    region_id,
    bbox,
    zero: bool = False,
    dash: bool = False,
    blank: bool = False,
    reason=None,
    pixel_ref=None,
):
    return {
        "format_version": VALUE_SEMANTICS_FORMAT_VERSION,
        "status": status,
        "raw_token": raw_token,
        "normalized_value": normalized_value,
        "source_region_id": region_id,
        "bounded_region_bbox_mpt": bbox,
        "visible_numeric_zero_verified": zero,
        "visible_dash_verified": dash,
        "pixel_blank_verified": blank,
        "pixel_evidence_ref": pixel_ref,
        "unresolved_reason": reason,
    }


def _bound_value_record(
    *,
    raw_token: str,
    status: str,
    normalized_value,
    zero: bool = False,
    dash: bool = False,
):
    envelope = _ocr_value_envelope(raw_token)
    atom = _word_atom(envelope)
    return (
        envelope,
        atom,
        _value_record(
            status=status,
            raw_token=raw_token,
            normalized_value=normalized_value,
            region_id=atom["source_local_id"],
            bbox=deepcopy(atom["canonical_bbox_mpt"]),
            zero=zero,
            dash=dash,
        ),
    )


def test_observed_values_exactly_bind_one_nonterminal_primary_text_atom() -> None:
    zero_envelope, zero_atom, zero = _bound_value_record(
        raw_token="0",
        status="OBSERVED_ZERO",
        normalized_value="0",
        zero=True,
    )
    assert validate_value_semantics_v1(zero, envelope=zero_envelope)["status"] == "OBSERVED_ZERO"

    value_envelope, _, observed = _bound_value_record(
        raw_token="1.234,50",
        status="OBSERVED_VALUE",
        normalized_value="1234.5",
    )
    assert (
        validate_value_semantics_v1(observed, envelope=value_envelope)["normalized_value"]
        == "1234.5"
    )

    dash_envelope, _, dash = _bound_value_record(
        raw_token="-",
        status="DASH",
        normalized_value=None,
        dash=True,
    )
    assert validate_value_semantics_v1(dash, envelope=dash_envelope)["status"] == "DASH"

    decimal_envelope, _, decimal_zero = _bound_value_record(
        raw_token="0.0",
        status="OBSERVED_ZERO",
        normalized_value="0",
        zero=True,
    )
    assert (
        validate_value_semantics_v1(decimal_zero, envelope=decimal_envelope)["status"]
        == "OBSERVED_ZERO"
    )

    forged_value = deepcopy(zero)
    forged_value.update({"status": "OBSERVED_VALUE", "raw_token": "999", "normalized_value": "999"})
    with pytest.raises(SourceStructureContractError, match="exactly bound"):
        validate_value_semantics_v1(forged_value, envelope=zero_envelope)

    forged_dash = deepcopy(zero)
    forged_dash.update(
        {
            "status": "DASH",
            "raw_token": "-",
            "normalized_value": None,
            "visible_numeric_zero_verified": False,
            "visible_dash_verified": True,
        }
    )
    with pytest.raises(SourceStructureContractError, match="exactly bound"):
        validate_value_semantics_v1(forged_dash, envelope=zero_envelope)

    sub_bbox = deepcopy(zero)
    sub_bbox["bounded_region_bbox_mpt"][2] -= 1
    with pytest.raises(SourceStructureContractError, match="exactly bound"):
        validate_value_semantics_v1(sub_bbox, envelope=zero_envelope)

    outside_bbox = deepcopy(zero)
    outside_bbox["bounded_region_bbox_mpt"][0] -= 1
    with pytest.raises(SourceStructureContractError, match="outside its authenticated source atom"):
        validate_value_semantics_v1(outside_bbox, envelope=zero_envelope)

    typed_bbox = deepcopy(zero)
    typed_bbox["bounded_region_bbox_mpt"][0] = float(typed_bbox["bounded_region_bbox_mpt"][0])
    with pytest.raises(SourceStructureContractError, match="four integer"):
        validate_value_semantics_v1(typed_bbox, envelope=zero_envelope)

    typed_region = deepcopy(zero)
    typed_region["source_region_id"] = True
    with pytest.raises(SourceStructureContractError, match="source-local identity"):
        validate_value_semantics_v1(typed_region, envelope=zero_envelope)

    foreign_record, foreign_result = _ocr_complete(source_sha="7" * 64, page=7)
    foreign_envelope = project_authenticated_page_v1(
        page_record=foreign_record,
        page_result=foreign_result,
    )
    foreign_atom = _word_atom(foreign_envelope)
    self_consistent_foreign = deepcopy(zero)
    self_consistent_foreign.update(
        {
            "source_region_id": foreign_atom["source_local_id"],
            "bounded_region_bbox_mpt": foreign_atom["canonical_bbox_mpt"],
        }
    )
    with pytest.raises(SourceStructureContractError, match="not an atom"):
        validate_value_semantics_v1(self_consistent_foreign, envelope=zero_envelope)

    tokenless = deepcopy(zero)
    tokenless["raw_token"] = None
    with pytest.raises(SourceStructureContractError, match="exactly bound"):
        validate_value_semantics_v1(tokenless, envelope=zero_envelope)

    assert zero_atom["raw_text"] == "0"


def test_blank_pixel_refs_and_nonprimary_atoms_cannot_promote_value_claims() -> None:
    envelope = _ocr_value_envelope("0")
    atom = _word_atom(envelope)
    bbox = deepcopy(atom["canonical_bbox_mpt"])
    arbitrary_crop = {
        "kind": "BOUNDED_SOURCE_PIXEL_CROP",
        "sha256": "8" * 64,
        "size_bytes": 101,
        "media_type": "image/png",
        "source_local_page_id": envelope["source_local_page_id"],
        "source_region_id": atom["source_local_id"],
        "bounded_region_bbox_mpt": bbox,
        "coordinate_authority_sha256": canonical_json_sha256_v1(envelope["coordinate_authority"]),
    }
    blank = _value_record(
        status="BLANK",
        raw_token=None,
        normalized_value=None,
        region_id=atom["source_local_id"],
        bbox=bbox,
        blank=True,
        pixel_ref=arbitrary_crop,
    )
    with pytest.raises(SourceStructureContractError, match="BLANK is unsupported"):
        validate_value_semantics_v1(blank, envelope=envelope)
    no_crop = deepcopy(blank)
    no_crop["pixel_evidence_ref"] = None
    with pytest.raises(SourceStructureContractError, match="BLANK is unsupported"):
        validate_value_semantics_v1(no_crop, envelope=envelope)

    arbitrary_ref_on_zero = _value_record(
        status="OBSERVED_ZERO",
        raw_token="0",
        normalized_value="0",
        region_id=atom["source_local_id"],
        bbox=bbox,
        zero=True,
        pixel_ref=arbitrary_crop,
    )
    with pytest.raises(SourceStructureContractError, match="pixel evidence references"):
        validate_value_semantics_v1(arbitrary_ref_on_zero, envelope=envelope)

    terminal = _terminal_envelope()
    supplemental = next(atom for atom in terminal["atoms"] if atom["kind"] == "LINE")
    supplemental_value = _value_record(
        status="OBSERVED_ZERO",
        raw_token=supplemental["raw_text"],
        normalized_value="0",
        region_id=supplemental["source_local_id"],
        bbox=deepcopy(supplemental["canonical_bbox_mpt"]),
        zero=True,
    )
    with pytest.raises(SourceStructureContractError, match="nonterminal primary"):
        validate_value_semantics_v1(supplemental_value, envelope=terminal)

    unresolved_supplement = deepcopy(supplemental_value)
    unresolved_supplement.update(
        {
            "status": "UNRESOLVED",
            "normalized_value": None,
            "visible_numeric_zero_verified": False,
            "unresolved_reason": "CONFLICTING_NUMERIC_READER_EVIDENCE",
        }
    )
    assert (
        validate_value_semantics_v1(unresolved_supplement, envelope=terminal)["status"]
        == "UNRESOLVED"
    )

    quarantine_record, quarantine_result = _native_complete()
    quarantine_result["quarantined_spans"] = [
        {
            "page": 1,
            "text_sha256": "a" * 64,
            "nonwhitespace_character_count": 1,
            "bbox_mpt": [200_000, 200_000, 210_000, 210_000],
            "block_number": 1,
            "line_number": 0,
            "span_number": 0,
            "color": 0,
            "alpha": 255,
            "render_sequence": 1,
            "occluding_sequence": 2,
            "occluding_object_type": "image",
            "reason": "OCCLUDED_TEXT_SPAN",
        }
    ]
    quarantine_result["metrics"]["quarantined_span_count"] = 1
    quarantine_record["quarantined_span_count"] = 1
    _refresh_result_ref(quarantine_record, quarantine_result)
    quarantine_envelope = project_authenticated_page_v1(
        page_record=quarantine_record,
        page_result=quarantine_result,
    )
    quarantine_atom = next(
        item for item in quarantine_envelope["atoms"] if item["kind"] == "QUARANTINED_SPAN"
    )
    quarantine_value = _value_record(
        status="OBSERVED_VALUE",
        raw_token="999",
        normalized_value="999",
        region_id=quarantine_atom["source_local_id"],
        bbox=deepcopy(quarantine_atom["canonical_bbox_mpt"]),
    )
    with pytest.raises(SourceStructureContractError, match="nonterminal primary"):
        validate_value_semantics_v1(quarantine_value, envelope=quarantine_envelope)

    empty_record, empty_result = _ocr_complete()
    empty_result["lines"][0]["raw_text"] = ""
    empty_result["lines"][0]["words"][0]["raw_text"] = ""
    empty_result["words"][0]["raw_text"] = ""
    _refresh_result_ref(empty_record, empty_result)
    empty_envelope = project_authenticated_page_v1(
        page_record=empty_record,
        page_result=empty_result,
    )
    excluded_atom = next(
        item for item in empty_envelope["atoms"] if item["kind"] == "EXCLUDED_EMPTY_WORD"
    )
    excluded_value = _value_record(
        status="OBSERVED_ZERO",
        raw_token="0",
        normalized_value="0",
        region_id=excluded_atom["source_local_id"],
        bbox=deepcopy(excluded_atom["canonical_bbox_mpt"]),
        zero=True,
    )
    with pytest.raises(SourceStructureContractError, match="nonterminal primary"):
        validate_value_semantics_v1(excluded_value, envelope=empty_envelope)


def test_unresolved_values_are_nonpromotional_but_visible_tokens_exact_bind() -> None:
    envelope = _ocr_value_envelope("ambiguous")
    atom = _word_atom(envelope)
    missing = _value_record(
        status="UNRESOLVED",
        raw_token=None,
        normalized_value=None,
        region_id=None,
        bbox=None,
        reason="TOKEN_NOT_OBSERVED",
    )
    assert validate_value_semantics_v1(missing, envelope=envelope)["status"] == "UNRESOLVED"

    bounded_missing = deepcopy(missing)
    bounded_missing.update(
        {
            "source_region_id": atom["source_local_id"],
            "bounded_region_bbox_mpt": deepcopy(atom["canonical_bbox_mpt"]),
            "unresolved_reason": "OCR_TOKEN_MISSING_IN_BOUNDED_REGION",
        }
    )
    assert validate_value_semantics_v1(bounded_missing, envelope=envelope)["status"] == "UNRESOLVED"

    visible = deepcopy(bounded_missing)
    visible.update(
        {
            "raw_token": "ambiguous",
            "unresolved_reason": "AMBIGUOUS_VISIBLE_TOKEN",
        }
    )
    assert validate_value_semantics_v1(visible, envelope=envelope)["status"] == "UNRESOLVED"

    mismatched_text = deepcopy(visible)
    mismatched_text["raw_token"] = "forged"
    with pytest.raises(SourceStructureContractError, match="exactly bound"):
        validate_value_semantics_v1(mismatched_text, envelope=envelope)

    sub_bbox = deepcopy(visible)
    sub_bbox["bounded_region_bbox_mpt"][2] -= 1
    with pytest.raises(SourceStructureContractError, match="exactly bound"):
        validate_value_semantics_v1(sub_bbox, envelope=envelope)

    unbounded = deepcopy(missing)
    unbounded.update(
        {
            "raw_token": "ambiguous",
            "unresolved_reason": "AMBIGUOUS_VISIBLE_TOKEN",
        }
    )
    with pytest.raises(SourceStructureContractError, match="source-region authority"):
        validate_value_semantics_v1(unbounded, envelope=envelope)

    unknown_reason = deepcopy(missing)
    unknown_reason["unresolved_reason"] = "HISTORY_PATH_ROLE_A_BANK_HINT"
    with pytest.raises(SourceStructureContractError, match="unresolved value"):
        validate_value_semantics_v1(unknown_reason, envelope=envelope)

    empty_token = deepcopy(missing)
    empty_token["raw_token"] = ""
    with pytest.raises(SourceStructureContractError, match="raw token"):
        validate_value_semantics_v1(empty_token, envelope=envelope)


def test_financial_token_normalization_is_exact_and_locale_ambiguous_tokens_fail_closed() -> None:
    invalid_envelope, _, forged_normalization = _bound_value_record(
        raw_token="not a number",
        status="OBSERVED_VALUE",
        normalized_value="123",
    )
    with pytest.raises(SourceStructureContractError, match="numeric grammar"):
        validate_value_semantics_v1(forged_normalization, envelope=invalid_envelope)

    value_envelope, _, mismatched_normalization = _bound_value_record(
        raw_token="1.234,50",
        status="OBSERVED_VALUE",
        normalized_value="123",
    )
    with pytest.raises(SourceStructureContractError, match="exact parsed raw token"):
        validate_value_semantics_v1(mismatched_normalization, envelope=value_envelope)

    for ambiguous_raw in ("0,123", "1.234", "-0,123", "(1.234)"):
        ambiguous_envelope, ambiguous_atom, ambiguous = _bound_value_record(
            raw_token=ambiguous_raw,
            status="OBSERVED_VALUE",
            normalized_value="123",
        )
        with pytest.raises(SourceStructureContractError, match="locale-ambiguous"):
            validate_value_semantics_v1(ambiguous, envelope=ambiguous_envelope)

        unresolved_ambiguous = _value_record(
            status="UNRESOLVED",
            raw_token=ambiguous_raw,
            normalized_value=None,
            region_id=ambiguous_atom["source_local_id"],
            bbox=deepcopy(ambiguous_atom["canonical_bbox_mpt"]),
            reason="AMBIGUOUS_VISIBLE_TOKEN",
        )
        assert (
            validate_value_semantics_v1(
                unresolved_ambiguous,
                envelope=ambiguous_envelope,
            )["status"]
            == "UNRESOLVED"
        )

    ambiguous_zero_envelope, _, ambiguous_zero = _bound_value_record(
        raw_token="0,000",
        status="OBSERVED_ZERO",
        normalized_value="0",
        zero=True,
    )
    with pytest.raises(SourceStructureContractError, match="exact numeric evidence"):
        validate_value_semantics_v1(ambiguous_zero, envelope=ambiguous_zero_envelope)

    typed_envelope, _, normalized_type_drift = _bound_value_record(
        raw_token="1.234,50",
        status="OBSERVED_VALUE",
        normalized_value=1234.5,
    )
    with pytest.raises(SourceStructureContractError, match="visible raw/numeric evidence"):
        validate_value_semantics_v1(normalized_type_drift, envelope=typed_envelope)

    false_dash_envelope, _, false_dash = _bound_value_record(
        raw_token="0",
        status="DASH",
        normalized_value=None,
        dash=True,
    )
    with pytest.raises(SourceStructureContractError, match="visible dash"):
        validate_value_semantics_v1(false_dash, envelope=false_dash_envelope)
