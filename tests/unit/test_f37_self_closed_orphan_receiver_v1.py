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


def _run_batch(documents_pages):
    """One batch over several documents; selected_page_ordinal restarts at 1 per document, as in the runner."""
    compiled = _compiled()
    documents, selected, clusters, page_json_by_document = [], [], [], {}
    for document_ordinal, pages in enumerate(documents_pages, 1):
        document = {"document_id": "gfpstorev1:document:" + "%x" % (document_ordinal + 13) * 64,
                    "document_ordinal": document_ordinal, "source_logical_name": PROVENANCE["source_logical_name"],
                    "source_sha256": PROVENANCE["source_sha256"]}
        records, by_version = [], {}
        for ordinal, (version_id, physical_page, page) in enumerate(pages, 1):
            record = {**document, "page_json": page, "page_json_version_id": version_id,
                      "physical_page": physical_page, "selected_page_ordinal": ordinal}
            records.append(record)
            selected.append({key: value for key, value in record.items() if key != "page_json"})
            by_version[version_id] = page
        documents.append(document)
        clusters.append(coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=records, compiled_specs=compiled))
        page_json_by_document[document_ordinal] = by_version
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=documents, selected_page_axis=selected, document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]))
    indexed = build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base, page_json_by_document=page_json_by_document, compiled_specs=compiled)
    trials = build_gemini_json_credit_risk_provision_expense_trials_v1(
        indexed_query_evidence=indexed, page_json_by_document=page_json_by_document, compiled_specs=compiled)
    validate_gemini_json_credit_risk_provision_expense_replay_v1(
        base_indexed_query_evidence=base, indexed_query_evidence=indexed, trials=trials,
        page_json_by_document=page_json_by_document, compiled_specs=compiled)
    return trials


def _run(pages):
    return _run_batch([pages])[0]


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
    "receiver_marker_continues_on_next",
    "opening_row_kind_total",
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
    elif mutation == "closing_not_year_end":
        rows[-1]["label_exact"] = "Ngày 30 tháng 6 năm 2024"
        rows[-1]["hierarchy_path_exact"] = ["Ngày 30 tháng 6 năm 2024"]
    elif mutation == "receiver_marker_continues_on_next":
        receiver["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    else:
        rows[0]["row_kind"] = "TOTAL"
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


def _renamed(pages, salt):
    """The same page bytes under other version ids (a second document of the batch)."""
    return [("gfpstorev1:json:" + hashlib.sha256((salt + version_id).encode()).hexdigest(), physical_page,
             copy.deepcopy(page)) for version_id, physical_page, page in pages]


def test_receiver_previous_page_lookup_is_scoped_to_its_own_document():
    # Real batches cover many documents whose selected ordinals all restart at 1 (review finding F1).
    pages = _pages()
    for trials in (_run_batch([_renamed(pages, "other"), pages]), _run_batch([pages, _renamed(pages, "other")])):
        for trial in trials:
            assert trial["status"] == READY, trial["reasons"]
            assert _values(trial)["FAMILY_ROOT_TOTAL"] == ["680.216", "611.837"]


def test_conflicting_self_closed_prior_year_movement_does_not_authorize_customer_child_roles():
    pages = copy.deepcopy(_pages())
    charge = _page(pages, 41)["sections"][0]["tables"][0]["rows"][1]
    assert charge["values_exact"] == ["323.849", "74.978", "398.827"]
    charge["values_exact"][0], charge["values_exact"][2] = "323.850", "398.828"  # still adds up; only differs from p40
    trial = _run(pages)
    assert trial["status"] == READY, trial["reasons"]
    assert _values(trial)["CUSTOMER_PROVISION"] == ["476.404", "398.827"]  # the direct p40 cells only
    assert not {"CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"} & set(_values(trial))
