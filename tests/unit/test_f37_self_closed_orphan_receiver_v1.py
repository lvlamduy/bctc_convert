"""F37 doc 17: a self-closed orphan movement receiver must not veto one closed normal population.

Real shape (exact original page JSONs, see the fixture provenance): BVB separate audited 2025 (COMMON204 doc 17).
p40 prints the complete expense table "Chi phí dự phòng rủi ro tín dụng trong năm bao gồm:" (continuation NONE,
purchased debt / customer / VAMC "Số trích lập" rows, total 680.216 / 611.837 = the p11 primary root). p41 prints the
prior-year customer movement "Ngày 1 tháng 1 năm 2024" -> "Ngày 31 tháng 12 năm 2024" under the heading
"11.1 ... (tiếp theo)" and is marked CONTINUES_FROM_PREVIOUS_PAGE, but nothing on p40 continues. At 6ec4b26f the doc
was held F37_SOURCE_CONTINUATION_NOT_CLOSED.
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
FIXTURES = ROOT / "tests/fixtures/source_structure/f37-common17-orphan-receiver-20261029-v1"
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


def _run(pages, *, selected_ordinals=None):
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


def _page(pages, physical_page):
    return next(page for _version_id, number, page in pages if number == physical_page)


def test_bvb017_closed_expense_table_is_ready_beside_the_self_closed_orphan_receiver():
    pages = _pages()
    assert _page(pages, 41)["sections"][0]["tables"][0]["continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE"
    trial = _run(pages)
    assert trial["status"] == READY, trial["reasons"]
    assert _values(trial) == {
        "CUSTOMER_PROVISION": ["476.404", "398.827"],
        "PURCHASED_DEBT_PROVISION": ["4.271", "-"],
        "VAMC_PROVISION": ["199.541", "213.010"],
        "FAMILY_ROOT_TOTAL": ["680.216", "611.837"],
    }


@pytest.mark.parametrize("mutation", [
    "previous_page_table_continues_on_next",
    "previous_page_table_both",
    "previous_page_table_unknown",
    "receiver_marker_both",
    "closing_year_differs",
    "closing_row_not_total",
    "opening_row_removed",
    "opening_not_year_start",
    "closing_not_year_end",
])
def test_open_or_unbounded_receivers_still_veto(mutation):
    pages = copy.deepcopy(_pages())
    p40, receiver = _page(pages, 40), _page(pages, 41)["sections"][0]["tables"][0]
    rows = receiver["rows"]
    if mutation == "previous_page_table_continues_on_next":
        p40["sections"][1]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    elif mutation == "previous_page_table_both":
        p40["sections"][1]["tables"][0]["continuation"] = "BOTH"
    elif mutation == "previous_page_table_unknown":
        p40["sections"][1]["tables"][0]["continuation"] = "UNKNOWN"
    elif mutation == "receiver_marker_both":
        receiver["continuation"] = "BOTH"
    elif mutation == "closing_year_differs":
        rows[-1]["label_exact"] = "Ngày 31 tháng 12 năm 2025"
        rows[-1]["hierarchy_path_exact"] = ["Ngày 31 tháng 12 năm 2025"]
    elif mutation == "closing_row_not_total":
        rows[-1]["row_kind"] = "ITEM"
    elif mutation == "opening_row_removed":
        del rows[0]
    elif mutation == "opening_not_year_start":
        rows[0]["label_exact"] = "Ngày 1 tháng 7 năm 2024"
        rows[0]["hierarchy_path_exact"] = ["Ngày 1 tháng 7 năm 2024"]
    else:
        rows[-1]["label_exact"] = "Ngày 30 tháng 6 năm 2024"
        rows[-1]["hierarchy_path_exact"] = ["Ngày 30 tháng 6 năm 2024"]
    trial = _run(pages)
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    assert "F37_SOURCE_CONTINUATION_NOT_CLOSED" in trial["reasons"]


def test_receiver_without_its_previous_physical_page_still_vetoes():
    pages = [item for item in copy.deepcopy(_pages()) if item[1] != 40]
    p39 = _page(pages, 39)
    p39["sections"].append(copy.deepcopy(_page(_pages(), 40)["sections"][0]))  # keep one closed normal population
    trial = _run(pages)
    assert trial["status"] == UNRESOLVED
    assert "F37_SOURCE_CONTINUATION_NOT_CLOSED" in trial["reasons"]
