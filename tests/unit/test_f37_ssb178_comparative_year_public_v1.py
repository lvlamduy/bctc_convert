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
    _family37_document_plan_v1,
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
    return _run_full(pages)["trial"]


def _run_full(pages):
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
    return {"base": base, "compiled": compiled, "indexed": indexed, "page_json_by_document": page_json_by_document,
            "trial": trials[0], "trials": trials}


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
    "Kỳ ba tháng từ ngày 01/02/2024 đến ngày 31/03/2024",  # matching end, contradicting printed start
])
def test_wrong_comparative_detail_window_withholds_permission(header):
    trial = _run(_with_comparative_detail_header(_pages(), header))
    assert trial["status"] != READY


def test_comparative_root_without_any_printed_year_withholds_permission():
    # Codex 0570: the same KQKD with the title year removed ("Quý I"), detail still 31/03/2024.
    pages = copy.deepcopy(_pages())
    page = next(page for _version_id, physical_page, page in pages if physical_page == 6)
    section = next(item for item in page["sections"] if item.get("statement_type") == "INCOME_STATEMENT")
    assert section["title_exact"] == "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025"
    section["title_exact"] = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I"
    trial = _run(pages)
    assert trial["status"] != READY


def _with_primary_lane_labels(pages, *, current, comparative):
    """The KQKD title without its year and every Năm nay / Năm trước column label replaced."""
    pages = copy.deepcopy(pages)
    page = next(page for _version_id, physical_page, page in pages if physical_page == 6)
    section = next(item for item in page["sections"] if item.get("statement_type") == "INCOME_STATEMENT")
    section["title_exact"] = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I"
    replaced = {"Năm nay": current, "Năm trước": comparative}
    changed = 0
    for table in section["tables"]:
        for column in table["columns"]:
            path = column.get("header_path_exact") or []
            if path and path[-1] in replaced:
                path[-1] = replaced[path[-1]]
                changed += 1
    assert changed == 4  # Quý I and Lũy kế groups, both lanes
    return pages


def _with_current_detail_header(pages, header):
    pages = copy.deepcopy(pages)
    page = next(page for _version_id, physical_page, page in pages if physical_page == 32)
    changed = 0
    for section in page["sections"]:
        for table in section["tables"]:
            for column in table["columns"]:
                path = column.get("header_path_exact") or []
                if path and path[0] == "Kỳ ba tháng kết thúc ngày 31/03/2025":
                    path[0] = header
                    changed += 1
    assert changed == 2
    return pages


def test_explicit_current_2025_and_comparative_2024_primary_labels_are_ready():
    trial = _run(_with_primary_lane_labels(_pages(), current="Năm 2025", comparative="Năm 2024"))
    assert trial["status"] == READY, trial["reasons"]
    values = {m["role"]: [v.get("source_text") for v in m["values"]] for m in trial["mappings"]}
    assert values["CUSTOMER_GENERAL"] == ["48.928", "3.877"]
    assert values["FAMILY_ROOT_TOTAL"] == ["(434.831)", "(239.029)"]


@pytest.mark.parametrize("current_detail", [
    "Kỳ ba tháng kết thúc ngày 31/03/2025",   # the printed detail year, still no PRIMARY current year
    "Kỳ ba tháng kết thúc ngày 31/03/2023",
])
def test_unknown_current_primary_year_withholds_although_comparative_is_explicit(current_detail):
    # Codex 0575: CURRENT "Năm nay" under "Quý I" proves no year; the explicit comparative 2024 must not fill it.
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    if current_detail != "Kỳ ba tháng kết thúc ngày 31/03/2025":
        pages = _with_current_detail_header(pages, current_detail)
    trial = _run(pages)
    assert trial["status"] != READY


# Codex 0584 N1 / N2: the root-less (note-only) route.

CURRENT_HEADER = "Kỳ ba tháng kết thúc ngày 31/03/2025"
COMPARATIVE_HEADER = "Kỳ ba tháng kết thúc ngày 31/03/2024"


def _note_only(pages):
    """Genuinely absent PRIMARY: only the note page p32 is selected."""
    return [item for item in copy.deepcopy(pages) if item[1] == 32]


def _with_note_headers(pages, by_header):
    pages = copy.deepcopy(pages)
    page = next(page for _version_id, physical_page, page in pages if physical_page == 32)
    changed = 0
    for section in page["sections"]:
        for table in section["tables"]:
            for column in table["columns"]:
                path = column.get("header_path_exact") or []
                if path and path[0] in by_header:
                    column["header_path_exact"] = [*by_header[path[0]], *path[1:]]
                    changed += 1
    assert changed == 4  # both movement tables, both money columns
    return pages


def _mapped_values(trial):
    return {m["role"]: [v.get("source_text") for v in m["values"]] for m in trial["mappings"]}


def test_note_only_with_printed_roles_is_ready_without_a_primary_root_total():
    pages = _with_note_headers(_note_only(_pages()), {
        CURRENT_HEADER: ["Kỳ này", CURRENT_HEADER],
        COMPARATIVE_HEADER: ["Kỳ trước", COMPARATIVE_HEADER],
    })
    trial = _run(pages)
    assert trial["status"] == READY, trial["reasons"]
    values = _mapped_values(trial)
    assert values["CUSTOMER_GENERAL"] == ["48.928", "3.877"]
    assert values["CUSTOMER_SPECIFIC"] == ["385.903", "235.152"]
    assert "FAMILY_ROOT_TOTAL" not in values  # only note facts are admitted


def test_note_only_date_only_headers_are_not_a_printed_role():
    trial = _run(_note_only(_pages()))
    assert trial["status"] != READY
    assert "F37_ROOTLESS_LANE_ROLE_NOT_PRINTED" in trial["reasons"]


def test_note_only_inverted_date_only_pair_is_withheld():
    pages = _with_note_headers(_note_only(_pages()), {
        CURRENT_HEADER: ["Kỳ ba tháng kết thúc ngày 31/03/2023"],
        COMPARATIVE_HEADER: [COMPARATIVE_HEADER],
    })
    trial = _run(pages)
    assert trial["status"] != READY
    assert "F37_ROOTLESS_LANE_ROLE_NOT_PRINTED" in trial["reasons"]


def test_note_only_printed_roles_against_the_date_order_are_withheld():
    pages = _with_note_headers(_note_only(_pages()), {
        CURRENT_HEADER: ["Kỳ này", "Kỳ ba tháng kết thúc ngày 31/03/2023"],
        COMPARATIVE_HEADER: ["Kỳ trước", COMPARATIVE_HEADER],
    })
    trial = _run(pages)
    assert trial["status"] != READY


@pytest.mark.parametrize("current_detail", [CURRENT_HEADER, "Kỳ ba tháng kết thúc ngày 31/03/2023"])
def test_present_but_period_unresolved_primary_carrier_closes_the_note_only_route(current_detail):
    # The KQKD root row is printed, but its lanes ("Năm nay | Năm 2024") do not resolve: not absence.
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    pages = _with_note_headers(pages, {
        CURRENT_HEADER: ["Kỳ này", current_detail],
        COMPARATIVE_HEADER: ["Kỳ trước", COMPARATIVE_HEADER],
    })
    trial = _run(pages)
    assert trial["status"] != READY
    assert "F37_PRIMARY_ROOT_CARRIER_PERIOD_UNRESOLVED" in trial["reasons"]


def test_unresolved_primary_carrier_is_retained_in_the_source_authority():
    # Codex 0588: the carrier and its exact lane-axis reason survive in the final source authority receipt.
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    document = {"document_id": "gfpstorev1:document:" + "5" * 64, "document_ordinal": 1,
                "source_logical_name": PROVENANCE["source_logical_name"], "source_sha256": PROVENANCE["source_sha256"]}
    axis = [{**document, "page_json_version_id": version_id, "physical_page": physical_page,
             "selected_page_ordinal": ordinal}
            for ordinal, (version_id, physical_page, _page) in enumerate(pages, 1)]
    plan = _family37_document_plan_v1(document=document, selected_page_axis=axis,
                                      source_pages={version_id: page for version_id, _number, page in pages},
                                      compiled_specs=_compiled())
    carriers = plan["adapter_receipt"]["source_authority_receipt"]["unresolved_primary_root_carrier_axis"]
    assert [item["locator"]["physical_page"] for item in carriers] == [6]
    assert carriers[0]["lane_axis_reasons"] == ["DURATION_PERIOD_PRECISION_DIFFERS_ACROSS_MONEY_COLUMNS"]
    assert "F37_PRIMARY_ROOT_CARRIER_PERIOD_UNRESOLVED" in plan["blocking_reasons"]


def _carrier_axis(indexed):
    (disposition,) = indexed["candidate_dispositions"]
    receipt = disposition["cluster"]["credit_risk_provision_expense_query_adapter_receipt"]
    return receipt["source_authority_receipt"]["unresolved_primary_root_carrier_axis"]


def test_unresolved_carrier_survives_indexed_trial_and_fresh_replay_with_no_mapping():
    # Codex 0589: indexed -> trial -> fresh replay keep the explicit reason, the exact PRIMARY locator and lane
    # rejection reasons, and admit no mapping.
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    run = _run_full(pages)  # _run_full already replays indexed evidence and trials from the page JSON
    assert run["trial"]["status"] != READY
    assert "F37_PRIMARY_ROOT_CARRIER_PERIOD_UNRESOLVED" in run["trial"]["reasons"]
    assert run["trial"]["mappings"] == []
    (carrier,) = _carrier_axis(run["indexed"])
    assert carrier["locator"]["physical_page"] == 6
    assert carrier["locator"]["page_json_version_id"] == PROVENANCE["pages"][0]["page_json_version_id"]
    assert carrier["lane_axis_reasons"] == ["DURATION_PERIOD_PRECISION_DIFFERS_ACROSS_MONEY_COLUMNS"]
    assert carrier["lane_axis_complete"] is False


def test_tampered_carrier_axis_fails_the_fresh_replay():
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    run = _run_full(pages)
    tampered = copy.deepcopy(run["indexed"])
    _carrier_axis(tampered).clear()
    with pytest.raises(Exception, match="replay drifted"):
        validate_gemini_json_credit_risk_provision_expense_replay_v1(
            base_indexed_query_evidence=run["base"], indexed_query_evidence=tampered, trials=run["trials"],
            page_json_by_document=run["page_json_by_document"], compiled_specs=run["compiled"])


def _assert_carrier_unresolved(run):
    assert run["trial"]["status"] == UNRESOLVED
    assert "F37_PRIMARY_ROOT_CARRIER_PERIOD_UNRESOLVED" in run["trial"]["reasons"]
    assert run["trial"]["mappings"] == []
    (carrier,) = _carrier_axis(run["indexed"])
    assert carrier["locator"]["physical_page"] == 6
    assert carrier["lane_axis_reasons"] == ["DURATION_PERIOD_PRECISION_DIFFERS_ACROSS_MONEY_COLUMNS"]


def test_unresolved_carrier_without_any_note_page_is_unresolved_not_absent():
    # Codex 0597: the printed family root row is direct family evidence even when no note observation exists.
    pages = [item for item in _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
             if item[1] == 6]
    _assert_carrier_unresolved(_run_full(pages))


def test_unresolved_carrier_with_contradictory_note_lanes_keeps_the_carrier():
    # The note prints "Kỳ này" on its 31/03/2023 column: the shared lane axis drops the note table, the carrier stays.
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    pages = _with_note_headers(pages, {
        CURRENT_HEADER: ["Kỳ này", "Kỳ ba tháng kết thúc ngày 31/03/2023"],
        COMPARATIVE_HEADER: ["Kỳ trước", COMPARATIVE_HEADER],
    })
    _assert_carrier_unresolved(_run_full(pages))


def test_unresolved_carrier_with_consistent_note_roles_of_other_years_is_unresolved():
    # Printed roles agree with the note's own dates (2024 current, 2023 comparative) but the PRIMARY lanes are
    # unresolved: no report-period authority, N1 reason, no mapping.
    pages = _with_primary_lane_labels(_pages(), current="Năm nay", comparative="Năm 2024")
    pages = _with_note_headers(pages, {
        CURRENT_HEADER: ["Kỳ này", COMPARATIVE_HEADER],
        COMPARATIVE_HEADER: ["Kỳ trước", "Kỳ ba tháng kết thúc ngày 31/03/2023"],
    })
    _assert_carrier_unresolved(_run_full(pages))
