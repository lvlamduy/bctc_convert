from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_issued_valuable_papers_family_v1 import (
    GeminiJsonIssuedValuablePapersFamilyV1Error,
    _bind_printed_total_from_closed_net_frontier_v1,
    _enforce_source_local_mapping_lanes_v1,
    compile_gemini_json_issued_valuable_papers_family_specs_v1,
    evaluate_gemini_json_issued_valuable_papers_family_cluster_v1,
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION = "gfpstorev1:json:" + "2" * 64
FIXTURES = ROOT / "tests/fixtures/source_structure/f25-source-total-lanes-20261027-v1"
FIXTURE_MANIFEST_SHA256 = "627e64289e583b007763a6d4fc9a79e4238d5c85449cde03a7310dba801a325e"


def _decode_beforeimage(evidence: dict) -> dict | list:
    payload = evidence["canonical_json"].encode("utf-8")
    assert len(payload) == evidence["size_bytes"]
    assert sha256(payload).hexdigest() == evidence["sha256"]
    value = json.loads(payload)
    assert canonical_json_bytes_v1(value) == payload
    return value


def _compiled(*, registered_repairs: bool = False) -> dict:
    def config(kind: str) -> dict:
        path = ROOT / f"config/families/tm-issued-valuable-papers-{kind}-v1.json"
        return json.loads(path.read_bytes())

    repairs = (
        json.loads(
            (ROOT / "data/registered/gemini_json_issued_valuable_papers_source_repairs_v1.json")
            .read_bytes()
        )
        if registered_repairs
        else {
            "family_id": "ISSUED_VALUABLE_PAPERS",
            "format_version": (
                "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
            ),
            "policy": (
                "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_MISSING_AS_NULL_NO_BLANK_ZERO_INFERENCE"
            ),
            "render_contract": {
                "alpha": False,
                "colorspace": "RGB",
                "format": "PNG",
                "render_dpi": 300,
                "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
            },
            "repair_axis_sha256": canonical_json_sha256_v1([]),
            "repairs": [],
        }
    )
    return compile_gemini_json_issued_valuable_papers_family_specs_v1(
        config("topology"),
        config("evaluation"),
        config("schema-binding"),
        repairs,
    )


def _row(label: str | None, values: list[str | None], kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(columns: list[list[str]], rows: list[dict], title: str | None = None) -> dict:
    return {
        "columns": [
            {"header_path_exact": header, "value_kind": "MONEY"}
            for header in columns
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _page(tables: list[dict]) -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables,
                "title_exact": "10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate(page: dict) -> tuple[dict, dict]:
    compiled = _compiled()
    record = {
        "document_id": "gfpstorev1:document:" + "1" * 64,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "synthetic-source-local-lanes.pdf",
        "source_sha256": "3" * 64,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY, cluster["reasons"]
    context = {
        "regions": cluster["component_regions"],
        "page_json_by_version": {VERSION: page},
        "compiled_specs": compiled,
        "query_receipt": (
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                cluster["component_regions"]
            )
        ),
    }
    return evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context), context


def _summary() -> dict:
    return _table(
        [["31/12/2025", "Triệu đồng"], ["31/12/2024", "Triệu đồng"]],
        [
            _row("Chứng chỉ tiền gửi", ["100", "80"]),
            _row("Trái phiếu", ["40", "30"]),
            _row("Tổng cộng", ["140", "110"], "TOTAL"),
        ],
    )


def test_two_period_source_summary_remains_source_local_and_replayable() -> None:
    page = _page([_summary()])
    before = copy.deepcopy(page)
    candidate, context = _evaluate(page)
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [140, 110]
    assert validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate, **context
    ) == candidate
    assert page == before


def test_one_period_maturity_cannot_acquire_summary_comparative() -> None:
    detail = _table(
        [
            ["31/12/2025", "Chứng chỉ tiền gửi", "Triệu đồng"],
            ["31/12/2025", "Trái phiếu", "Triệu đồng"],
            ["31/12/2025", "Tổng cộng", "Triệu đồng"],
        ],
        [
            _row("Dưới 12 tháng", ["40", "-", "40"]),
            _row("Từ 12 tháng đến 5 năm", ["60", "40", "100"]),
            _row("Số dư cuối năm", ["100", "40", "140"], "TOTAL"),
        ],
        "31/12/2025",
    )
    page = _page([_summary(), detail])
    before = copy.deepcopy(page)
    candidate, context = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    receipt = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"][
        "original_source_mapping_lane_receipt"
    ]
    assert receipt["failures"]
    assert any(table["status"] == "HOLD" for table in receipt["source_lane_inventory"]["tables"])
    assert receipt["withheld_or_rebound_mappings"]
    assert validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate, **context
    ) == candidate
    assert page == before

    tampered = copy.deepcopy(candidate)
    binding = tampered["closure_receipt"]["issued_valuable_papers_adapter_receipt"][
        "original_source_mapping_lane_receipt"
    ]
    binding["withheld_or_rebound_mappings"]["sha256"] = "0" * 64
    with pytest.raises(
        GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"
    ):
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            tampered, **context
        )


def _source_ref(table: int, row: int, columns: list[int]) -> dict:
    return {
        "locator": {
            "page_json_version_id": VERSION,
            "section_id": "s1",
            "table_id": f"t{table}",
        },
        "money_column_ordinals": columns,
        "row_ordinal": row,
    }


def _lane_candidate(refs: list[dict]) -> dict:
    return {
        "closure_receipt": {"structural_root_receipt": {"emitted_mapping": True}},
        "mappings": [
            {
                "item_mapping_id": "synthetic-item",
                "role": "BOND",
                "source_refs": refs,
                "values": [
                    {"coefficient": 40, "source_text": "40", "state": "RAW_SIGNED_INTEGER"},
                    {"coefficient": 30, "source_text": "30", "state": "RAW_SIGNED_INTEGER"},
                ],
            }
        ],
        "reasons": [],
        "status": READY,
    }


@pytest.mark.parametrize("equal_current_and_comparative", [False, True])
def test_one_current_net_column_never_borrows_comparative_even_if_values_equal(
    equal_current_and_comparative: bool,
) -> None:
    detail = _table(
        [["30/06/2025", "Mệnh giá"], ["30/06/2025", "Giá trị thuần"]],
        [_row("Trái phiếu", ["40", "40"])],
        "30/06/2025",
    )
    candidate = _lane_candidate([_source_ref(1, 2, [1, 2]), _source_ref(2, 1, [2])])
    if equal_current_and_comparative:
        candidate["mappings"][0]["values"][1] = copy.deepcopy(
            candidate["mappings"][0]["values"][0]
        )
    page = _page([_summary(), detail])
    before = copy.deepcopy(page)
    receipt = _enforce_source_local_mapping_lanes_v1(candidate, pages={VERSION: page})
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert receipt is not None and receipt["withheld_mappings"]
    assert page == before


@pytest.mark.parametrize("reverse_sources", [False, True])
def test_separately_dated_one_column_sources_need_economic_population_proof(
    reverse_sources: bool,
) -> None:
    page = _page(
        [
            _table([["31/12/2025"]], [_row("Trái phiếu", ["40"])], "31/12/2025"),
            _table([["31/12/2024"]], [_row("Trái phiếu", ["30"])], "31/12/2024"),
        ]
    )
    refs = [_source_ref(1, 1, [1]), _source_ref(2, 1, [1])]
    candidate = _lane_candidate(list(reversed(refs)) if reverse_sources else refs)
    receipt = _enforce_source_local_mapping_lanes_v1(candidate, pages={VERSION: page})
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert receipt is not None
    assert all(check["status"] == "HOLD" for check in receipt["checks"])


def test_genuine_single_source_current_lane_remains_one_lane() -> None:
    page = _page([_table([["31/12/2025"]], [_row("Trái phiếu", ["40"])])])
    candidate = _lane_candidate([_source_ref(1, 1, [1])])
    candidate["mappings"][0]["values"] = candidate["mappings"][0]["values"][:1]
    before = copy.deepcopy(candidate)
    assert _enforce_source_local_mapping_lanes_v1(candidate, pages={VERSION: page}) is None
    assert candidate == before


@pytest.mark.parametrize(
    "drift",
    ["missing_date", "duplicate_date", "wrong_lane_text", "different_population"],
)
def test_separate_source_lane_proof_fails_closed_on_source_drift(drift: str) -> None:
    page = _page(
        [
            _table([["31/12/2025"]], [_row("Trái phiếu", ["40"])]),
            _table([["31/12/2024"]], [_row("Trái phiếu", ["30"])]),
        ]
    )
    second = page["sections"][0]["tables"][1]
    if drift == "missing_date":
        second["columns"][0]["header_path_exact"] = ["Triệu đồng"]
    elif drift == "duplicate_date":
        second["columns"][0]["header_path_exact"] = ["31/12/2025"]
    elif drift == "wrong_lane_text":
        second["rows"][0]["values_exact"] = ["40"]
    else:
        second["title_exact"] = "Trái phiếu có kỳ hạn còn lại dưới 12 tháng"
    candidate = _lane_candidate([_source_ref(1, 1, [1]), _source_ref(2, 1, [1])])
    receipt = _enforce_source_local_mapping_lanes_v1(candidate, pages={VERSION: page})
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert receipt is not None


def _packet_context(case_id: str) -> tuple[dict, dict]:
    payload = (FIXTURES / "manifest.json").read_bytes()
    assert sha256(payload).hexdigest() == FIXTURE_MANIFEST_SHA256
    manifest = json.loads(payload)
    case = next(item for item in manifest["cases"] if item["case_id"] == case_id)
    original = case["stored_candidate"]
    assert canonical_json_sha256_v1(original) == case["stored_candidate_sha256"]
    pages = {}
    for source in case["pages"]:
        raw = (FIXTURES / source["file"]).read_bytes()
        assert len(raw) == source["size_bytes"]
        assert sha256(raw).hexdigest() == source["sha256"]
        pages[source["page_json_version_id"]] = json.loads(raw)
    # These authorities are copied from persisted candidate bytes. No query or
    # cluster receipt is regenerated to fit a changed result in these fixtures.
    context = {
        "regions": copy.deepcopy(original["component_regions"]),
        "page_json_by_version": pages,
        "compiled_specs": _compiled(registered_repairs=True),
        "query_receipt": copy.deepcopy(original["closure_receipt"]["query_receipt"]),
    }
    return case, context


def test_authenticated_lpb_printed_total_binds_raw_result_without_discount_double_count() -> None:
    case, context = _packet_context("f25-lpb-doc069")
    before = copy.deepcopy(context["page_json_by_version"])
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY, candidate["reasons"]
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [64_097_013, 55_458_916]
    assert [cell["source_text"] for cell in root["values"]] == ["64.097.013", "55.458.916"]
    assert root["row_id"] == "r11"
    assert len(root["source_refs"]) == 1
    assert root["source_refs"][0]["row_kind"] == "TOTAL"
    assert root["source_refs"][0]["money_column_ordinals"] == [1, 2]
    original = case["stored_candidate"]
    assert [item for item in candidate["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"] == [
        item for item in original["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"
    ]
    old_kind = "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
    original_equations = original["closure_receipt"]["equations"]
    retired = [item for item in original_equations if item["equation_kind"] == old_kind]
    assert len(retired) == 1
    assert candidate["closure_receipt"]["equations"] == [
        item for item in original_equations if item["equation_kind"] != old_kind
    ]
    adapter = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    binding = adapter["printed_net_frontier_total_receipt"]
    assert binding["failures"] == []
    assert binding["superseded_global_equations"] == retired
    assert binding["superseded_root_permissions"] == original["closure_receipt"][
        "root_component_sum_receipts"
    ]
    assert _decode_beforeimage(binding["superseded_derived_root"]) == next(
        item for item in original["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"
    )
    active = {key: value for key, value in candidate["closure_receipt"].items()
              if key != "issued_valuable_papers_adapter_receipt"}
    assert retired[0]["equation_id"] not in json.dumps(active, ensure_ascii=False)
    equation_ids = {item["equation_id"] for item in active["equations"]}
    assert all(item["source_equation_id"] in equation_ids for item in active["root_component_sum_receipts"])
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate, **context
    ) == candidate
    assert context["page_json_by_version"] == before


@pytest.mark.parametrize("drift", ["root_source_ref", "printed_receipt", "beforeimage_envelope"])
def test_authenticated_printed_root_and_superseded_receipt_tamper_fail_replay(drift: str) -> None:
    _, context = _packet_context("f25-lpb-doc069")
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == READY
    if drift == "root_source_ref":
        root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
        root["source_refs"][0]["row_ordinal"] = 10
    elif drift == "printed_receipt":
        candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"][
            "printed_net_frontier_total_receipt"
        ]["superseded_root_permissions"] = []
    else:
        candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"][
            "printed_net_frontier_total_receipt"
        ]["superseded_derived_root"]["canonical_json"] = "["
    with pytest.raises(GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            candidate, **context
        )


@pytest.mark.parametrize("case_id", ["f25-msb-doc076", "f25-vab-doc241"])
def test_authenticated_single_period_detail_cannot_borrow_summary_comparative(case_id: str) -> None:
    _, context = _packet_context(case_id)
    if case_id == "f25-msb-doc076":
        # The immutable original now has independent current-only permission.
        # Remove both printed period surfaces only in this counterfactual copy.
        page = next(iter(context["page_json_by_version"].values()))
        section = page["sections"][1]
        section["narratives_exact"] = []
        total = section["tables"][1]["rows"][-1]
        total["label_exact"] = None
        total["hierarchy_path_exact"] = [None]
        _counterfactual_candidate, context = _evaluate(page)
    before = copy.deepcopy(context["page_json_by_version"])
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**context)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    key = "original_source_mapping_lane_receipt" if case_id == "f25-msb-doc076" else "source_local_lane_binding_receipt"
    withheld_key = "withheld_or_rebound_mappings" if case_id == "f25-msb-doc076" else "withheld_mappings"
    binding = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"][key]
    assert binding[withheld_key]
    assert _decode_beforeimage(binding[withheld_key])
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"]) == 0
    if case_id == "f25-msb-doc076":
        assert "TRANSPOSED_ORIGINAL_SOURCE_PERIOD_OWNER_UNPROVEN" in binding["failures"]
        assert any(table["status"] == "HOLD" for table in binding["source_lane_inventory"]["tables"])
    else:
        assert any(check["mapping_lane_count"] == 2 and any(
            len(source["source_ref"]["money_column_ordinals"]) == 1
            for source in check["source_axis"]
        ) for check in binding["checks"])
    assert validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate, **context
    ) == candidate
    tampered = copy.deepcopy(candidate)
    tampered["closure_receipt"]["issued_valuable_papers_adapter_receipt"][key][withheld_key] = []
    with pytest.raises(GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            tampered, **context
        )
    assert context["page_json_by_version"] == before


@pytest.mark.parametrize(
    "drift",
    [
        "duplicate_total", "ambiguous_equation", "wrong_unit", "wrong_lane",
        "wrong_owner", "raw_row_drift", "blank_total", "partial_proof", "validation_child_component",
    ],
)
def test_printed_net_total_requires_exact_source_population_and_complete_proof(drift: str) -> None:
    _, context = _packet_context("f25-lpb-doc069")
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(**context)
    assert candidate["status"] == READY
    original_mappings = copy.deepcopy(candidate["mappings"])
    table = next(iter(context["page_json_by_version"].values()))["sections"][0]["tables"][0]
    equation = next(item for item in candidate["closure_receipt"]["equations"] if
                    item["equation_kind"] == "EXACT_CLOSED_STRUCTURAL_GROUP_SUBTOTALS_EQUAL_TERMINAL_TOTAL")
    if drift == "duplicate_total":
        table["rows"].append(copy.deepcopy(table["rows"][-1]))
    elif drift == "ambiguous_equation":
        candidate["closure_receipt"]["equations"].append(copy.deepcopy(equation))
    elif drift == "wrong_unit":
        table["unit_exact"] = "Nghìn VND"
    elif drift == "wrong_lane":
        table["columns"][1]["header_path_exact"][0] = "31/12/2025"
    elif drift == "wrong_owner":
        next(iter(context["page_json_by_version"].values()))["sections"][0]["title_exact"] = (
            "20. Các khoản nợ khác"
        )
    elif drift == "raw_row_drift":
        table["rows"][-1]["label_exact"] = "Một dân số khác"
    elif drift == "blank_total":
        table["rows"][-1]["values_exact"][0] = None
    elif drift == "partial_proof":
        equation["component_source_refs"] = equation["component_source_refs"][:1]
        equation["component_roles"] = equation["component_roles"][:1]
        equation["multipliers"] = [1]
    else:
        child = copy.deepcopy(equation["component_source_refs"][0][0])
        child.update({key: copy.deepcopy(table["rows"][3][key]) for key in (
            "hierarchy_path_exact", "label_exact", "row_kind",
        )})
        child.update({"row_id": "r4", "row_ordinal": 4})
        equation["component_source_refs"].append([child])
        equation["component_roles"].append("SOURCE_ROW")
        equation["multipliers"].append(1)
    if drift in {"partial_proof", "validation_child_component"}:
        # Deliberately resealed adversarial proof: a hash alone must not grant
        # the missing population/typed-source-row authority.
        material = {key: value for key, value in equation.items() if key != "equation_id"}
        equation["equation_id"] = "gjfoltiev1:equation:" + canonical_json_sha256_v1(material)
    receipt = _bind_printed_total_from_closed_net_frontier_v1(
        candidate, pages=context["page_json_by_version"], compiled_specs=context["compiled_specs"]
    )
    assert receipt is not None and receipt["failures"]
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert _decode_beforeimage(receipt["withheld_mappings"]) == original_mappings
    assert candidate["closure_receipt"]["root_component_sum_receipts"] == []
    assert not any(
        item["equation_kind"] == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
        for item in candidate["closure_receipt"]["equations"]
    )
