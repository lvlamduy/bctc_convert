"""F37 comparative year through the public path: SSB parent Q1 2025 (FULL271 doc 178), exact original page JSONs.

The KQKD comparative lane prints "Lũy kế từ đầu năm đến cuối quý này / Năm trước" under "Quý I năm 2025"; note 6
movements print "Kỳ ba tháng kết thúc ngày 31/03/2025 | 31/03/2024". The comparative year 2024 must come from the
PRIMARY lane's own label + title (recorded derivation), never from the detail's date: the same detail moved to
31/03/2023, 31/03/2025, a wrong end/quarter or a shifted range must withhold permission although every amount
still closes.
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
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/source_structure/f37-ssb178-comparative-year-20261028-v1"
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
    document = {"document_id": "gfpstorev1:document:" + "5" * 64, "document_ordinal": 1,
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


def _with_comparative_detail_header(pages, header):
    pages = copy.deepcopy(pages)
    page = next(page for _version_id, physical_page, page in pages if physical_page == 32)
    changed = 0
    for section in page["sections"]:
        for table in section["tables"]:
            for column in table["columns"]:
                path = column.get("header_path_exact") or []
                if path and path[0] == "Kỳ ba tháng kết thúc ngày 31/03/2024":
                    path[0] = header
                    changed += 1
    assert changed == 2  # general and specific movement, comparative column only
    return pages


def test_ssb178_comparative_2024_is_ready_with_the_printed_values():
    trial = _run(_pages())
    assert trial["status"] == READY, trial["reasons"]
    values = {m["role"]: [v.get("source_text") for v in m["values"]] for m in trial["mappings"]}
    assert values["CUSTOMER_GENERAL"] == ["48.928", "3.877"]
    assert values["CUSTOMER_SPECIFIC"] == ["385.903", "235.152"]
    assert values["FAMILY_ROOT_TOTAL"] == ["(434.831)", "(239.029)"]


@pytest.mark.parametrize("header", [
    "Kỳ ba tháng kết thúc ngày 31/03/2023",    # wrong year
    "Kỳ ba tháng kết thúc ngày 31/03/2025",    # the current year
    "Kỳ ba tháng kết thúc ngày 30/06/2024",    # same year and month count, wrong end
    "Từ ngày 01/02/2024 đến ngày 30/04/2024",  # shifted three-month range
    "Quý II năm 2024",                          # same year, wrong quarter
])
def test_wrong_comparative_detail_window_withholds_permission(header):
    trial = _run(_with_comparative_detail_header(_pages(), header))
    assert trial["status"] != READY
