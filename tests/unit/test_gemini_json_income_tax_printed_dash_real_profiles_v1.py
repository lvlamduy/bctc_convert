"""Pinned approved metadata/page bytes; no PDF/DB job or financial seal is asserted."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled
from test_gemini_json_income_tax_source_label_discrepancy_v1 import _reseal, _reseal_candidate

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation import gemini_json_income_tax_source_label_discrepancy_v1 as negative
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

METADATA_PATH = (Path(__file__).resolve().parents[1] / "fixtures/source_structure/"
                 "f39-t7a-approved-identity-20261027-v1.json")
METADATA_SHA256 = "503423bd2990ad8ab496e5008275a2cf732bfc3fc9a46174b805c14d1733c1bb"
REGISTRY_SHA256 = "612e04c5f666febd06026d2a7be81e35440cd24c661b812f6513008789030ab3"
APPROVAL = {
    "name": "0468-claude-to-codex-t7a-source-metadata-and-test-window.md",
    "sha256": "a1e113b687887f1f237c36106931606cea9b6ae8ec90ecc6e9d36199fe1a6215",
    "size_bytes": 2765,
}
EXPECTED = {
    "171:7:s1:t1:r19": {
        "source": {
            "document_id": "gfpstorev1:document:a5bff06e7e40624395b3ac616c632af5553bde99ad6a56cc5bd88a6333897792",
            "source_logical_name": "vietstock_bctc/SHB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf",
            "source_sha256": "46c3f6c73df7a5480989bdf1aa46dce12c7ce7c8cbba17a39b3ce95e1fe815e6",
            "source_size_bytes": 4257289,
        },
        "vid": "gfpstorev1:json:ffc7669eaba5e84d80ed82a9b9798f0d84e5d3d207d7bb5421823fb2140a9b99",
        "page": 7, "section": "s1", "row": 19, "money_axis": [4, 5], "dash_columns": [4, 5],
        "role": "DEFERRED_TAX_NET", "kind": "PRIMARY_STATEMENT", "statement": "INCOME_STATEMENT",
        "page_status": "PRIMARY_FINANCIAL_STATEMENT",
        "before": {"hierarchy_path_exact": ["8 Chi phí thuế TNDN hoãn lại"],
                   "label_exact": "8 Chi phí thuế TNDN hoãn lại", "row_kind": "ITEM",
                   "values_exact": [None, "9.923", "(11.920)", "0", "0"]},
        "observation_sha256": "8ac4134c0d270abd77b30afb5da2bce33fb5551f9c5af831f83894af253ecbf4",
        "stored_page_sha256": "99a6e03894bba8674dc9a4ff6d310eb0b25dfe5937727f055a675191f0c15743",
        "decoded_page_sha256": "885cc9f654dee23001249e14c4ef80d05d538febfd1ebc34ffa3573a66a430f0",
        "png_sha256": "74398c3867b9f249e8c0e6add34962ebbf7cafa23530c27440258a4361aa64c4",
        "png_size": 740599, "width": 826, "height": 1175,
    },
    "176:7:s1:t1:r19": {
        "source": {
            "document_id": "gfpstorev1:document:6a2feb8242684dc39c7f4c15a173c5ec316a822acc1800ae304b1ea3a1673be3",
            "source_logical_name": "vietstock_bctc/SHB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf",
            "source_sha256": "3a66122194e4dd2e0ca18d584beeacb81279cf71e276eface59d17e72813dcfd",
            "source_size_bytes": 6465872,
        },
        "vid": "gfpstorev1:json:7423fe253e4e0bb9a0f866fb3a707de3201964c2e34c43eff7ee051180b79a1d",
        "page": 7, "section": "s1", "row": 19, "money_axis": [4, 5], "dash_columns": [4],
        "role": "DEFERRED_TAX_NET", "kind": "PRIMARY_STATEMENT", "statement": "INCOME_STATEMENT",
        "page_status": "PRIMARY_FINANCIAL_STATEMENT",
        "before": {"hierarchy_path_exact": ["8 Chi phí thuế TNDN hoãn lại"],
                   "label_exact": "8 Chi phí thuế TNDN hoãn lại", "row_kind": "ITEM",
                   "values_exact": [None, "4.683", "(9.923)", "0", "(9.923)"]},
        "observation_sha256": "be9defe9cfdc5378881b4c492d0cf9d487d5ccdb51a475df214491044c9d9698",
        "stored_page_sha256": "313226c6a4067ac10f89d82a47cc16bd281764a0b1e8ee779cd9e7d9315972b5",
        "decoded_page_sha256": "79f49dddac63a30fa14e2123a4623e476369ed324c6ebe851161f76ee8a521ed",
        "png_sha256": "d508bae8c6f93312b9383c16fbcb02f9e80d0546ccb50c173cfb1297c07a646c",
        "png_size": 526167, "width": 830, "height": 1176,
    },
    "232:63:s2:t1:r4": {
        "source": {
            "document_id": "gfpstorev1:document:6eb5c21cde836a115db7ee2886b76b3791e6718e654e0d47dfac69955c9d6c28",
            "source_logical_name": "vietstock_bctc/TPB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf",
            "source_sha256": "742dbc45b1f5f7612100fd6e078977e206f700693a1f132e3373b81386934b8c",
            "source_size_bytes": 8825841,
        },
        "vid": "gfpstorev1:json:a2b2d9f05ef87d4d1389c9ee9328be17cdc3794649109fb161f46cdd8265ff02",
        "page": 63, "section": "s2", "row": 4, "money_axis": [1, 2], "dash_columns": [2],
        "role": "NON_TAXABLE_AGGREGATE", "kind": "FINANCIAL_NOTE", "statement": "NOT_APPLICABLE",
        "page_status": "FINANCIAL_NOTE_CONTENT",
        "before": {"hierarchy_path_exact": ["Điều chỉnh:", "Thu nhập không chịu thuế"],
                   "label_exact": "Thu nhập không chịu thuế", "row_kind": "ITEM", "values_exact": ["(60)", "0"]},
        "observation_sha256": "9e7fae906a9ea23bae038db89ca3a227158976e6de57b0996698d6b961be8210",
        "stored_page_sha256": "aacbb3cacb93cf0655bae20006a316a441c06a4962a0b6c05e6367931b097f58",
        "decoded_page_sha256": "de574f67ab9030f78fbab88642404a53d29642acbd86a1788f3f5ec2c3da50b3",
        "png_sha256": "f01ba48ff58ec0a5d840029c7cb3dd65fd92061963d6ed6e79f1e29bf91fcb20",
        "png_size": 424138, "width": 828, "height": 1170,
    },
}


@pytest.fixture(scope="module")
def approved_metadata():
    raw = METADATA_PATH.read_bytes()
    assert len(raw) == 52757 and sha256(raw).hexdigest() == METADATA_SHA256
    metadata = json.loads(raw)
    assert [item["case"] for item in metadata["cases"]] == list(EXPECTED)
    return {item["case"]: item for item in metadata["cases"]}


def _source_record(profile):
    """Decode the approved bounded receipt; never open its historical DB/PDF paths."""
    locator = profile["citing_mappings"][0]["source_ref"]["locator"]
    return {**{key: deepcopy(locator[key]) for key in negative._LOCATOR_KEYS},
            "page_json": json.loads(bytes.fromhex(profile["page_json_version"]["canonical_json_bytes"]))}


def _candidate_and_context(profile):
    record, compiled = _source_record(profile), _adapter_compiled()
    cited = deepcopy(profile["citing_mappings"][0])
    cited["source_refs"] = [cited.pop("source_ref")]
    candidate = {"status": READY, "reasons": [], "closure_receipt": {}, "mappings": [cited]}
    _reseal_candidate(candidate)
    context = family._source_context_receipt(
        compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=[record],
    )
    return candidate, context, [record], compiled


def test_registry_adds_three_profiles_and_preserves_the_original_t5_observation():
    assert negative.REGISTRY_SHA256 == REGISTRY_SHA256
    assert sha256(negative.REGISTRY_PATH.read_bytes()).hexdigest() == REGISTRY_SHA256
    registry = negative.load_registered_negative_source_label_observations_v1()
    assert registry["registry_id"] == "gjitflabelv1:registry:b17291ea3366ccff528d74c5bce9627fdac8a57f3a5728a0f3ca1123f6664bf1"
    assert len(registry["observations"]) == 4
    legacy = registry["observations"][0]
    assert legacy["observation_id"] == "gjitflabelv1:observation:6c8df1d00fc761adeca20b96ed415f104b4e1f244ff2de114751ff91c157ced2"
    assert canonical_json_sha256_v1({key: value for key, value in legacy.items() if key != "observation_id"}) == (
        "6c8df1d00fc761adeca20b96ed415f104b4e1f244ff2de114751ff91c157ced2"
    )
    assert [item["classification"] for item in registry["observations"]] == [
        "SOURCE_LABEL_SUBSTITUTION_NOT_EXTRA_ROW", *[negative.PRINTED_DASH_CLASSIFICATION] * 3,
    ]


@pytest.mark.parametrize("case", EXPECTED)
def test_registered_profile_matches_exact_approved_source_raw_row_axis_and_pixels(approved_metadata, case):
    expected, profile = EXPECTED[case], approved_metadata[case]
    records = [_source_record(profile)]
    observations = negative.registered_negative_source_label_observation_axis_v1(records)
    assert len(observations) == 1
    observed = observations[0]
    registration = observed["registered_negative_observation"]
    assert registration["observation_id"] == "gjitflabelv1:observation:" + expected["observation_sha256"]
    assert registration["source"] == expected["source"]
    assert registration["locator"] == {
        "page_json_version_id": expected["vid"], "physical_page": expected["page"],
        "section_id": expected["section"], "table_id": "t1", "row_ordinal": expected["row"],
        "row_id": f"r{expected['row']}", "money_column_ordinals": expected["money_axis"],
    }
    assert registration["expected_role"] == expected["role"]
    assert registration["source_section_kind"] == expected["kind"]
    assert registration["source_statement_type"] == expected["statement"]
    assert registration["source_page_status"] == expected["page_status"]
    assert registration["before_reference"] == observed["original_source_row_exact"] == expected["before"]
    assert registration["printed_dash_money_column_ordinals"] == expected["dash_columns"]
    assert all(type(expected["before"]["values_exact"][column - 1]) is str
               and expected["before"]["values_exact"][column - 1] == "0" for column in expected["dash_columns"])
    assert observed["money_column_ordinals"] == expected["money_axis"]
    assert registration["review"]["approval_message"] == APPROVAL
    assert registration["review"]["source_identity_ref"] == {
        "name": "t7a-identity.json", "sha256": METADATA_SHA256, "size_bytes": 52757,
    }
    assert registration["review"]["source_identity_case"] == case
    assert registration["review"]["printed_glyph_by_money_column"] == {
        str(column): "-" for column in expected["dash_columns"]
    }
    assert registration["review"]["page_render"] == {
        "renderer": "pdftoppm", "resolution_dpi": 100, "format": "PNG", "alpha": False, "colorspace": "RGB",
        "sha256": expected["png_sha256"], "size_bytes": expected["png_size"],
        "width_pixels": expected["width"], "height_pixels": expected["height"],
    }
    stored_page = bytes.fromhex(profile["page_json_version"]["canonical_json_bytes"])
    # Preserve the original BLOB's two LF bytes; evaluator canonical JSON uses one LF.
    assert stored_page.endswith(b"\n\n")
    assert sha256(stored_page).hexdigest() == profile["page_json_version"]["canonical_json_sha256"] == expected["stored_page_sha256"]
    assert canonical_json_sha256_v1(records[0]["page_json"]) == observed["original_page_json_sha256"] == expected["decoded_page_sha256"]


@pytest.mark.parametrize("case", EXPECTED)
@pytest.mark.parametrize("runtime_ordinal", [1, 17, 204])
def test_real_profile_routing_uses_source_identity_when_document_ordinals_move(approved_metadata, case, runtime_ordinal):
    record = _source_record(approved_metadata[case])
    record["document_ordinal"] = runtime_ordinal
    before = deepcopy(record)
    observations = negative.registered_negative_source_label_observation_axis_v1([record])
    assert len(observations) == 1
    assert observations[0]["source_locator"]["document_ordinal"] == runtime_ordinal
    assert observations[0]["registered_negative_observation"]["source"] == EXPECTED[case]["source"]
    assert record == before


@pytest.mark.parametrize("case", EXPECTED)
def test_real_page_profile_withholds_whole_document_without_changing_any_lane(approved_metadata, case):
    candidate, context, records, compiled = _candidate_and_context(approved_metadata[case])
    before = deepcopy((candidate, context, records))
    result = family._seal_income_tax_source_controls(
        candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
    )
    assert result["status"] == UNRESOLVED and result["mappings"] == []
    assert result["reasons"] == ["SOURCE_PRINTED_DASH_VS_JSON_NUMERIC_DISCREPANCY"]
    assert (candidate, context, records) == before
    assert result["candidate_id"] == "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in result.items() if key != "candidate_id"}
    )


@pytest.mark.parametrize("case", EXPECTED)
@pytest.mark.parametrize("drift", ["typed_zero", "selected_vid", "pdf_identity"])
def test_real_profile_cannot_authorize_retyped_cells_or_another_source_version(approved_metadata, case, drift):
    expected, record = EXPECTED[case], _source_record(approved_metadata[case])
    if drift == "typed_zero":
        section = record["page_json"]["sections"][int(expected["section"][1:]) - 1]
        row = section["tables"][0]["rows"][expected["row"] - 1]
        row["values_exact"][expected["dash_columns"][0] - 1] = 0
    elif drift == "selected_vid":
        record["page_json_version_id"] = "gfpstorev1:json:" + "f" * 64
    else:
        record["source_logical_name"] = "synthetic/different-pdf.pdf"
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error):
        negative.registered_negative_source_label_observation_axis_v1([record])


def test_real_note_profile_replays_its_own_complete_population(approved_metadata):
    candidate, context, records, compiled = _candidate_and_context(approved_metadata["232:63:s2:t1:r4"])
    observed = context["registered_source_label_discrepancy_observations"][0]
    own = [item for item in context["tax_population_inventory"] if item["locator"] == observed["source_locator"]]
    assert len(own) == 1 and own[0]["locator"]["section_id"] == "s2"
    assert own[0]["lane_axis"]["money_column_ordinals"] == [1, 2]
    assert own[0]["source_table_rows_exact"][3] == EXPECTED["232:63:s2:t1:r4"]["before"]
    context["tax_population_inventory"].remove(own[0])
    _reseal(context, "receipt_id", "gjitfav1:source-context:")
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="NOTE population replay"):
        family._registered_negative_source_label_conflicts_v1(
            candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
        )
