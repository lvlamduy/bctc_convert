"""F37 P1: annual movement tables split over two consecutive sections, each owned by its own narrative.

Real shape (exact original page JSONs, see the fixture provenance): EIB parent annual 2025 (FULL271 doc 39), note 10 on
p32 prints "Biến động số dư dự phòng rủi ro cho vay khách hàng cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025
như sau:" above a transposed table (Dự phòng chung | Dự phòng cụ thể | Tổng cộng), then the same narrative for 2024
above the second table in an untitled section. At 7b9756c6 this was held F37_TRANSPOSED_PRESENTATION_NOT_UNIQUE.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1,
    build_gemini_json_credit_risk_provision_expense_trials_v1,
    compile_gemini_json_credit_risk_provision_expense_family_specs_v1,
    validate_gemini_json_credit_risk_provision_expense_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/source_structure/f37-annual-split-sections-20261028-v1"
PROVENANCE = json.loads((FIXTURES / "provenance.json").read_bytes())


def _compiled():
    def config(name):
        return json.loads((ROOT / "config/families" / name).read_bytes())

    return compile_gemini_json_credit_risk_provision_expense_family_specs_v1(
        config("tm-credit-risk-provision-expense-topology-v1.json"),
        config("tm-credit-risk-provision-expense-evaluation-v1.json"),
        config("tm-credit-risk-provision-expense-schema-binding-v1.json"),
        config("tm-credit-risk-provision-expense-source-repair-v1.json"),
    )


def _pages():
    pages = []
    for item in PROVENANCE["pages"]:
        raw = (FIXTURES / item["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["canonical_json_sha256"]  # stored canonical bytes
        pages.append((item["page_json_version_id"], item["physical_page"], json.loads(raw)))
    return pages


def _run(pages):
    compiled = _compiled()
    document = {"document_id": "gfpstorev1:document:" + "e" * 64, "document_ordinal": 1,
                "source_logical_name": PROVENANCE["source_logical_name"], "source_sha256": PROVENANCE["source_sha256"]}
    records, selected, by_version = [], [], {}
    for ordinal, (version_id, physical_page, page) in enumerate(pages, 1):
        record = {**document, "page_json": page, "page_json_version_id": version_id,
                  "physical_page": physical_page, "selected_page_ordinal": ordinal}
        records.append(record)
        selected.append({key: value for key, value in record.items() if key != "page_json"})
        by_version[version_id] = page
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document], selected_page_axis=selected, document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]))
    page_json_by_document = {1: by_version}
    indexed = build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base, page_json_by_document=page_json_by_document, compiled_specs=compiled)
    trials = build_gemini_json_credit_risk_provision_expense_trials_v1(
        indexed_query_evidence=indexed, page_json_by_document=page_json_by_document, compiled_specs=compiled)
    validate_gemini_json_credit_risk_provision_expense_replay_v1(
        base_indexed_query_evidence=base, indexed_query_evidence=indexed, trials=trials,
        page_json_by_document=page_json_by_document, compiled_specs=compiled)
    return trials[0]


def _values(trial):
    return {m["role"]: [v.get("source_text") for v in m["values"]] for m in trial["mappings"]}


def test_eib039_split_annual_sections_bind_current_and_comparative():
    trial = _run(_pages())
    assert trial["status"] == READY, trial["reasons"]
    values = _values(trial)
    assert values["CUSTOMER_GENERAL"] == ["142.325", "173.835"]
    assert values["CUSTOMER_SPECIFIC"] == ["1.310.402", "789.237"]


def _p032(pages):
    return next(page for _version_id, physical_page, page in pages if physical_page == 32)


@pytest.mark.parametrize("mutation", [
    "same_year_twice", "narrative_without_year", "swap_years", "extra_narrative",
    "owner_narrative_names_credit_institutions", "follower_narrative_names_purchased_debt",
    "owner_table_title_names_securities", "follower_table_title_names_tctd",
])
def test_split_sections_fail_closed_on_altered_owner_narratives(mutation):
    pages = copy.deepcopy(_pages())
    page = _p032(pages)
    first, second = page["sections"][0], page["sections"][1]
    if mutation == "same_year_twice":
        second["narratives_exact"] = list(first["narratives_exact"])
    elif mutation == "narrative_without_year":
        second["narratives_exact"] = [second["narratives_exact"][0].replace(" năm 2024", "")]
    elif mutation == "swap_years":
        first["narratives_exact"], second["narratives_exact"] = second["narratives_exact"], first["narratives_exact"]
    elif mutation == "extra_narrative":
        second["narratives_exact"] = [*second["narratives_exact"], "Thuyết minh bổ sung cho năm 2023 như sau:"]
    elif mutation == "owner_narrative_names_credit_institutions":
        first["narratives_exact"] = [first["narratives_exact"][0].replace(
            "cho vay khách hàng", "cho vay khách hàng và các tổ chức tín dụng khác")]
    elif mutation == "follower_narrative_names_purchased_debt":
        second["narratives_exact"] = [second["narratives_exact"][0].replace(
            "cho vay khách hàng", "cho vay khách hàng và các khoản mua nợ")]
    elif mutation == "owner_table_title_names_securities":
        first["tables"][0]["title_exact"] = "Dự phòng rủi ro chứng khoán đầu tư"
    else:
        second["tables"][0]["title_exact"] = "Dự phòng rủi ro cho vay các TCTD khác"
    trial = _run(pages)
    assert trial["status"] == UNRESOLVED
