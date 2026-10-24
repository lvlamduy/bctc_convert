"""Notes engine: document-owned annual-policy evidence for "Năm kết thúc ngày 31/12/Y" lanes (Codex 0250)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_notes_income_tax import RECON, cells, context_of, document, kqkd, make_table
from test_notes_source_bridge import corpus

from bctc_ai.notes.annual_policy_v1 import policy_assertions_v1, resolve_annual_policy_v1
from bctc_ai.notes.concept_list_shape_v1 import evaluate_concept_table_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.kernel_v1 import NotesKernelError, NotesSource, resolve_duration_lanes_v1, year_ended_policy_v1
from bctc_ai.primary_statements.periods_v1 import statement_period_context_v1
from bctc_ai.storage import gemini_financial_page_store_v1 as shared

ROOT = Path(__file__).resolve().parents[2]
INTERIM_Q4 = ["Báo cáo kết quả hoạt động giữa niên độ cho giai đoạn từ ngày 01/1/2025 đến ngày 31/12/2025"]
CALENDAR = "Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12."
YEAR_ENDED = [("Năm kết thúc ngày 31/12/2025 Triệu VND",), ("Năm kết thúc\nngày 31/12/2024\nTriệu VND",)]
PROVENANCE = {"page_json_version_id": "v12", "physical_page": 12, "document_ordinal": 1}


def policy_page(*narratives):
    return {"status": "FINANCIAL_NOTE_CONTENT",
            "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE", "title_exact": "2. Cơ sở trình bày",
                          "narratives_exact": list(narratives), "tables": []}],
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}


def resolved(*narratives):
    return resolve_annual_policy_v1(policy_assertions_v1(policy_page(*narratives), PROVENANCE))


@pytest.fixture(scope="module")
def family():
    return load_notes_config_v1(ROOT).families["INCOME_TAX"]


def interim(policy, **override):
    return replace(document(quarter=4), income_context_texts=INTERIM_Q4, annual_policy=policy, **override)


# --------------------------------------------------------------------------- evidence and resolution


def test_policy_assertions_keep_pointer_entire_clause_hashes_owner_and_window():
    narrative = "(c) Kỳ kế toán năm. " + CALENDAR + " Báo cáo này lập cho Quý IV năm 2025 kết thúc ngày 31 tháng 12 năm 2025."
    [assertion] = policy_assertions_v1(policy_page("Không liên quan.", narrative), PROVENANCE)
    assert assertion["pointer"] == "/sections/0/narratives_exact/1" and assertion["narrative_exact"] == narrative
    assert assertion["window"] == {"start": "01-01", "end": "12-31"} and assertion["owner"] == "DOCUMENT_ENTITY"
    assert assertion["qualifiers"] == [] and len(assertion["section_sha256"]) == 64 and assertion["physical_page"] == 12
    policy = resolve_annual_policy_v1([assertion])
    assert policy["status"] == "CALENDAR_YEAR" and policy["pointers"] == [
        {"page_json_version_id": "v12", "physical_page": 12, "pointer": "/sections/0/narratives_exact/1"}]
    worded = resolved("Kỳ kế toán năm của Tập đoàn bắt đầu từ ngày 01/01 và kết thúc vào ngày 31/12 hàng năm.")
    assert worded["status"] == "CALENDAR_YEAR"


@pytest.mark.parametrize("narratives,reason", [
    ((), "NO_PRINTED_ANNUAL_POLICY"),
    (("Năm tài chính bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12.",), "POLICY_OWNER_UNKNOWN_OR_FOREIGN"),
    (("Năm tài chính của công ty con bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12.",), "POLICY_OWNER_UNKNOWN_OR_FOREIGN"),
    ((CALENDAR + " Năm tài chính đầu tiên ngắn hơn 12 tháng.",), "POLICY_QUALIFIED_FIRST_SHORT_LONG_OR_CHANGED_YEAR"),
    ((CALENDAR, "Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 4 và kết thúc vào ngày 31 tháng 3."), "POLICY_WINDOWS_CONFLICT"),
    (("Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 7 và kết thúc vào ngày 30 tháng 6.",), "POLICY_NOT_A_CALENDAR_YEAR"),
])
def test_unknown_foreign_qualified_conflicting_or_non_calendar_policy_stays_unresolved(narratives, reason):
    policy = resolved(*narratives)
    assert policy["status"] == "UNRESOLVED" and reason in policy["reasons"]
    assert len(policy["assertions"]) == len([n for n in narratives if "bắt đầu" in n])  # every occurrence is kept


# --------------------------------------------------------------------------- lanes


def test_year_ended_lanes_take_their_own_printed_year_under_a_calendar_policy():
    table = make_table(RECON[:1], YEAR_ENDED)
    lanes = resolve_duration_lanes_v1(table, interim(resolved(CALENDAR)), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == ["DURATION:YEAR:2025", "DURATION:YEAR:2024"]  # 2024 printed, not minus one
    assert all(lane.period_basis == "PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:v12@p12/sections/0/narratives_exact/0"
               and lane.reasons == [] and lane.shadow_evidence == [] for lane in lanes)


@pytest.mark.parametrize("header,policy,why", [
    ("Năm kết thúc ngày 31/12/2025", None, "DOCUMENT_ANNUAL_POLICY_ABSENT"),
    ("Năm kết thúc ngày 31/12/2025", "unresolved", "DOCUMENT_ANNUAL_POLICY_UNRESOLVED"),
    ("Năm kết thúc ngày 30/06/2025", "calendar", "YEAR_END_NOT_31_DECEMBER"),
])
def test_absent_unresolved_or_non_december_policy_keeps_the_hold(header, policy, why):
    policies = {None: None, "unresolved": resolved(), "calendar": resolved(CALENDAR)}
    table = make_table(RECON[:1], [(header,)])
    [lane] = resolve_duration_lanes_v1(table, interim(policies[policy]), [], [table.table_title])
    assert lane.period_key is None
    assert lane.reasons[:2] == ["PERIOD_UNRESOLVED:PERIOD_END_WITHOUT_PRINTED_DURATION", "ANNUAL_POLICY_NOT_APPLIED:" + why]


def test_a_contradictory_own_six_month_caption_keeps_the_hold():
    # A report-level Q4 frame does not veto; a table's OWN six-month caption does (Codex 0250). The kernel already
    # holds such a lane earlier (own vs report window); the policy rule refuses it on its own as well.
    own = "Chi phí thuế cho giai đoạn sáu tháng kết thúc ngày 30 tháng 6 năm 2025"
    table = make_table(RECON[:1], YEAR_ENDED[:1], title=own)
    [lane] = resolve_duration_lanes_v1(table, interim(resolved(CALENDAR)), [], [table.table_title])
    assert lane.period_key is None and not lane.period_basis.startswith("PRINTED_YEAR_ENDED") and lane.reasons
    granted, why = year_ended_policy_v1("Năm kết thúc ngày 31/12/2025", resolved(CALENDAR), statement_period_context_v1([own]))
    assert granted is None and why == "OWN_CAPTION_WINDOW_CONFLICT"
    granted, why = year_ended_policy_v1("Năm kết thúc ngày 31/12/2025", resolved(CALENDAR), statement_period_context_v1([]))
    assert granted == ("DURATION:YEAR:2025",
                       "PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:v12@p12/sections/0/narratives_exact/0") and why is None


def test_bare_dates_relative_quarter_ytd_and_annotated_headers_gain_nothing():
    headers = [("31/12/2025",), ("Kỳ này",), ("Quý 4/2025",), ("Lũy kế 31/12/2025",),
               ("Năm kết thúc ngày 31/12/2025 (trình bày lại)",), ("Năm kết thúc ngày 31/12/2025 và 31/12/2024",)]
    table = make_table(RECON[:1], headers)
    lanes = resolve_duration_lanes_v1(table, interim(resolved(CALENDAR)), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == [None, None, "DURATION:QUARTER:4:2025", None, None, None]
    assert not any(lane.period_basis.startswith("PRINTED_YEAR_ENDED") for lane in lanes)


def test_primary_amounts_never_change_the_policy_period(family):
    # The same note under agreeing, differing or absent PRIMARY lines gets the same printed-policy period keys.
    keys = []
    for primary in ({}, kqkd({"DURATION:YEAR:2025": {"CURRENT": "87808"}}), kqkd({"DURATION:YEAR:2025": {"CURRENT": "1"}})):
        table = make_table(RECON, YEAR_ENDED)
        result = cells(evaluate_concept_table_v1(table, family, interim(resolved(CALENDAR), primary_cells=primary),
                                                 context_of(table), []))
        keys.append(sorted({key[1] for key in result}))
    assert keys[0] == keys[1] == keys[2] == ["DURATION:YEAR:2024", "DURATION:YEAR:2025"]


# --------------------------------------------------------------------------- authenticated ORIGINAL collection


def _two_page_store(tmp_path, first, second):
    db = tmp_path / "source.sqlite3"
    shared.initialize_gemini_financial_page_store_v1(db)
    one = _ingest(db, page_json=first, physical_page=1, image_sha256="c" * 64)["page_json_version_id"]
    two = _ingest(db, page_json=second, physical_page=2, image_sha256="f" * 64)["page_json_version_id"]
    return db, one, two


def test_policies_are_read_from_authenticated_selected_original_pages_only(tmp_path):
    db, one, two = _two_page_store(tmp_path, policy_page("Thuyết minh chung."), policy_page("Ghi chú. " + CALENDAR))
    policies = NotesSource(corpus(db, [(1, one), (2, two)])).annual_policies_v1([1])
    assert policies[1]["status"] == "CALENDAR_YEAR"
    [pointer] = policies[1]["pointers"]
    assert pointer == {"page_json_version_id": two, "physical_page": 2, "pointer": "/sections/0/narratives_exact/0"}
    assertion = policies[1]["assertions"][0]
    assert assertion["source_logical_name"] == "report.pdf" and assertion["original_blob_sha256"] and assertion["replay_receipt_id"]
    # A policy printed on a page the corpus did not select is not this document's evidence.
    unselected = NotesSource(corpus(db, [(1, one)])).annual_policies_v1([1])
    assert unselected[1]["status"] == "UNRESOLVED" and unselected[1]["reasons"] == ["NO_PRINTED_ANNUAL_POLICY"]
    # A loader provenance that is not the selected document's page fails the invocation.
    with pytest.raises(NotesKernelError):
        NotesSource(corpus(db, [(1, one), (2, two)], relative_path="other.pdf")).annual_policies_v1([1])
