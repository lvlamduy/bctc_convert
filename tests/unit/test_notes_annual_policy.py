"""Notes engine: document-owned annual-policy evidence for "Năm kết thúc ngày 31/12/Y" lanes (Codex 0250/0254)."""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_notes_income_tax import RECON, cells, context_of, document, kqkd, make_table
from test_notes_source_bridge import corpus

from bctc_ai.notes.annual_policy_v1 import policy_assertions_v1, resolve_annual_policy_v1, verify_annual_policy_v1
from bctc_ai.notes.concept_list_shape_v1 import evaluate_concept_table_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.kernel_v1 import NotesKernelError, NotesSource, resolve_duration_lanes_v1, year_ended_policy_v1
from bctc_ai.primary_statements.periods_v1 import statement_period_context_v1
from bctc_ai.storage import gemini_financial_page_store_v1 as shared

ROOT = Path(__file__).resolve().parents[2]
INTERIM_Q4 = ["Báo cáo kết quả hoạt động giữa niên độ cho giai đoạn từ ngày 01/1/2025 đến ngày 31/12/2025"]
# Actual LPB FULL69 p12 /sections/0/narratives_exact/5 wording (raw ORIGINAL discovery 6ff8b778...).
LPB = ("(c) Kỳ kế toán\nKỳ kế toán năm của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12. "
       "Báo cáo tài chính giữa niên độ quý IV năm 2025 của Ngân hàng được lập cho kỳ kết thúc ngày 31 tháng 12 năm 2025.")
CALENDAR = "Kỳ kế toán năm của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12."
YEAR_ENDED = [("Năm kết thúc ngày 31/12/2025 Triệu VND",), ("Năm kết thúc\nngày 31/12/2024\nTriệu VND",)]
# The test document of test_notes_income_tax.document(): ordinal 1, x.pdf, "0"*64, SEPARATE.
BINDING = {"document_ordinal": 1, "source_logical_name": "x.pdf", "source_sha256": "0" * 64, "scope": "SEPARATE"}
PROVENANCE = {"document_ordinal": 1, "source_logical_name": "x.pdf", "source_sha256": "0" * 64,
              "page_json_version_id": "v12", "physical_page": 12}


def policy_page(*narratives):
    return {"status": "FINANCIAL_NOTE_CONTENT",
            "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE", "title_exact": "2. Cơ sở trình bày",
                          "narratives_exact": list(narratives), "tables": []}],
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}


def resolved(*narratives, scope="SEPARATE"):
    return resolve_annual_policy_v1(policy_assertions_v1(policy_page(*narratives), PROVENANCE), {**BINDING, "scope": scope})


@pytest.fixture(scope="module")
def family():
    return load_notes_config_v1(ROOT).families["INCOME_TAX"]


def interim(policy, **override):
    return replace(document(quarter=4), income_context_texts=INTERIM_Q4, annual_policy=policy, **override)


# --------------------------------------------------------------------------- evidence, resolution, verification


def test_the_actual_lpb_clause_is_a_scope_bound_calendar_definition():
    eps = ("Theo hướng dẫn …, bao gồm những thay đổi xảy ra sau ngày kết thúc năm tài chính nhưng trước ngày phát hành "
           "báo cáo tài chính.")
    assertions = policy_assertions_v1(policy_page("(d) Tổng số nhân viên", LPB, eps), PROVENANCE)
    [assertion] = assertions  # the Q4 endpoint sentence and the EPS sentence are not policy candidates
    assert assertion["pointer"] == "/sections/0/narratives_exact/1" and assertion["narrative_exact"] == LPB
    assert assertion["sentence_exact"] == CALENDAR and assertion["kind"] == "DEFINITION" and assertion["owner"] == "BANK"
    assert assertion["window"] == {"start": "01-01", "end": "12-31"} and assertion["printed_years"] == []
    policy = resolve_annual_policy_v1(assertions, BINDING)
    assert policy["status"] == "CALENDAR_YEAR" and policy["binding"] == BINDING
    assert verify_annual_policy_v1(policy, BINDING) == (True, "VERIFIED")
    group = resolved("Năm tài chính của Tập đoàn bắt đầu từ ngày 01/01 và kết thúc vào ngày 31/12 hàng năm.", scope="CONSOLIDATED")
    assert group["status"] == "CALENDAR_YEAR"


@pytest.mark.parametrize("narratives,scope,reason", [
    ((), "SEPARATE", "NO_PRINTED_ANNUAL_POLICY"),
    (("Kỳ kế toán năm bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12.",), "SEPARATE", "POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY"),
    (("Năm tài chính của Tập đoàn bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12.",), "SEPARATE",
     "POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY"),
    ((CALENDAR,), "CONSOLIDATED", "POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY"),
    ((CALENDAR,), None, "POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY"),
    (("Năm tài chính của Ngân hàng Nhà nước bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12.",), "SEPARATE",
     "POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY"),
    (("Năm tài chính của công ty con của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12.",), "SEPARATE",
     "POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY"),
    (("Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 1 năm 2024 và kết thúc vào ngày 31 tháng 12 năm 2025.",), "SEPARATE",
     "POLICY_ABSOLUTE_INTERVAL_NOT_A_RECURRENCE"),
    (("Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12 theo quyết định của Hội đồng.",),
     "SEPARATE", "UNSUPPORTED_POLICY_WORDING"),
    ((CALENDAR, "Năm tài chính đầu tiên của Ngân hàng ngắn hơn 12 tháng."), "SEPARATE",
     "POLICY_QUALIFIED_FIRST_SHORT_LONG_OR_CHANGED_YEAR"),
    ((CALENDAR, "Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 4 và kết thúc vào ngày 31 tháng 3."), "SEPARATE",
     "POLICY_WINDOWS_CONFLICT"),
    ((CALENDAR, "KỲ KẾ TOÁN NĂM CỦA NGÂN HÀNG BẮT ĐẦU TỪ NGÀY 1 THÁNG 4 VÀ KẾT THÚC VÀO NGÀY 31 THÁNG 3."), "SEPARATE",
     "POLICY_WINDOWS_CONFLICT"),
    (("Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 7 và kết thúc vào ngày 30 tháng 6.",), "SEPARATE",
     "POLICY_NOT_A_CALENDAR_YEAR"),
])
def test_unknown_foreign_compound_scoped_absolute_unsupported_qualified_or_conflicting_policy_stays_unresolved(
        narratives, scope, reason):
    policy = resolved(*narratives, scope=scope)
    assert policy["status"] == "UNRESOLVED" and reason in policy["reasons"]
    assert verify_annual_policy_v1(policy, {**BINDING, "scope": scope}) == (False, "DOCUMENT_ANNUAL_POLICY_UNRESOLVED")


def test_a_status_tag_another_documents_policy_or_a_tampered_assertion_never_verifies():
    policy = resolved(CALENDAR)
    assert verify_annual_policy_v1({"status": "CALENDAR_YEAR"}, BINDING) == (False, "POLICY_NOT_A_RECORD")
    assert verify_annual_policy_v1(policy, {**BINDING, "source_sha256": "9" * 64})[1] == "POLICY_BINDING_IS_ANOTHER_DOCUMENT_OR_SCOPE"
    tampered = copy.deepcopy(policy)
    tampered["assertions"][0]["window"]["start"] = "04-01"
    assert verify_annual_policy_v1(tampered, BINDING)[1] == "POLICY_ASSERTION_DOES_NOT_REDERIVE_FROM_ITS_SENTENCE"
    unbound = copy.deepcopy(policy)
    unbound["assertions"][0]["sentence_exact"] = "Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12."
    assert verify_annual_policy_v1(unbound, BINDING)[1] == "POLICY_ASSERTION_SOURCE_BINDING_INVALID"
    relabelled = copy.deepcopy(resolved())
    relabelled.update(status="CALENDAR_YEAR", reasons=[])
    assert verify_annual_policy_v1(relabelled, BINDING)[1] == "POLICY_STATUS_DOES_NOT_REDERIVE"


# --------------------------------------------------------------------------- lanes


def test_year_ended_lanes_take_their_own_printed_year_under_a_verified_calendar_policy():
    table = make_table(RECON[:1], YEAR_ENDED)
    lanes = resolve_duration_lanes_v1(table, interim(resolved(CALENDAR)), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == ["DURATION:YEAR:2025", "DURATION:YEAR:2024"]  # 2024 printed, not minus one
    assert all(lane.period_basis == "PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:v12@p12/sections/0/narratives_exact/0"
               and lane.reasons == [] and lane.shadow_evidence == [] for lane in lanes)


@pytest.mark.parametrize("header,policy,why", [
    ("Năm kết thúc ngày 31/12/2025", None, "DOCUMENT_ANNUAL_POLICY_ABSENT"),
    ("Năm kết thúc ngày 31/12/2025", "unresolved", "DOCUMENT_ANNUAL_POLICY_UNRESOLVED"),
    ("Năm kết thúc ngày 31/12/2025", "status_only", "POLICY_NOT_A_RECORD"),
    ("Năm kết thúc ngày 31/12/2025", "foreign", "POLICY_BINDING_IS_ANOTHER_DOCUMENT_OR_SCOPE"),
    ("Năm kết thúc ngày 30/06/2025", "calendar", "YEAR_END_NOT_31_DECEMBER"),
])
def test_absent_unresolved_untrusted_foreign_or_non_december_policy_keeps_the_hold(header, policy, why):
    foreign = resolve_annual_policy_v1(policy_assertions_v1(policy_page(CALENDAR), {**PROVENANCE, "source_sha256": "9" * 64}),
                                       {**BINDING, "source_sha256": "9" * 64})
    policies = {None: None, "unresolved": resolved(), "status_only": {"status": "CALENDAR_YEAR"}, "foreign": foreign,
                "calendar": resolved(CALENDAR)}
    table = make_table(RECON[:1], [(header,)])
    [lane] = resolve_duration_lanes_v1(table, interim(policies[policy]), [], [table.table_title])
    assert lane.period_key is None
    assert lane.reasons[:2] == ["PERIOD_UNRESOLVED:PERIOD_END_WITHOUT_PRINTED_DURATION", "ANNUAL_POLICY_NOT_APPLIED:" + why]


def test_a_contradictory_own_six_month_caption_keeps_the_hold():
    own = "Chi phí thuế cho giai đoạn sáu tháng kết thúc ngày 30 tháng 6 năm 2025"
    table = make_table(RECON[:1], YEAR_ENDED[:1], title=own)
    [lane] = resolve_duration_lanes_v1(table, interim(resolved(CALENDAR)), [], [table.table_title])
    assert lane.period_key is None and not lane.period_basis.startswith("PRINTED_YEAR_ENDED") and lane.reasons
    doc = interim(resolved(CALENDAR))
    assert year_ended_policy_v1("Năm kết thúc ngày 31/12/2025", doc, statement_period_context_v1([own])) == (
        None, "OWN_CAPTION_WINDOW_CONFLICT")
    assert year_ended_policy_v1("Năm kết thúc ngày 31/12/2025", doc, statement_period_context_v1([])) == (
        ("DURATION:YEAR:2025", "PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:v12@p12/sections/0/narratives_exact/0"), None)


def test_other_headers_resolve_exactly_as_without_the_policy():
    # Codex 0254: the interim fixture prints an explicit 01/01..31/12 range, so e.g. "Kỳ này" already resolves by its
    # independent route; the policy must change nothing for any header that is not a YEAR_ENDED 31/12 lane.
    headers = [("31/12/2025",), ("Kỳ này",), ("Quý 4/2025",), ("Lũy kế 31/12/2025",),
               ("Năm kết thúc ngày 31/12/2025 (trình bày lại)",), ("Năm kết thúc ngày 31/12/2025 và 31/12/2024",)]
    table = make_table(RECON[:1], headers)
    with_policy = resolve_duration_lanes_v1(table, interim(resolved(CALENDAR)), [], [table.table_title])
    without = resolve_duration_lanes_v1(table, interim(None), [], [table.table_title])
    assert [(lane.period_key, lane.period_basis) for lane in with_policy] == [(lane.period_key, lane.period_basis) for lane in without]
    assert not any(lane.period_basis.startswith("PRINTED_YEAR_ENDED") for lane in with_policy)
    assert with_policy[2].period_key == "DURATION:QUARTER:4:2025"


def test_primary_amounts_never_change_the_policy_period(family):
    keys = []
    for primary in ({}, kqkd({"DURATION:YEAR:2025": {"CURRENT": "87808"}}), kqkd({"DURATION:YEAR:2025": {"CURRENT": "1"}})):
        table = make_table(RECON, YEAR_ENDED)
        result = cells(evaluate_concept_table_v1(table, family, interim(resolved(CALENDAR), primary_cells=primary),
                                                 context_of(table), []))
        keys.append(sorted({key[1] for key in result}))
    assert keys[0] == keys[1] == keys[2] == ["DURATION:YEAR:2024", "DURATION:YEAR:2025"]


# --------------------------------------------------------------------------- authenticated ORIGINAL collection


def _store(tmp_path, *pages):
    db = tmp_path / "source.sqlite3"
    shared.initialize_gemini_financial_page_store_v1(db)
    vids = [_ingest(db, page_json=page, physical_page=number, image_sha256=f"{number:x}" * 64)["page_json_version_id"]
            for number, page in enumerate(pages, 1)]
    return db, vids


def test_the_complete_frontier_is_read_from_authenticated_selected_original_pages(tmp_path):
    db, (one, two, three) = _store(tmp_path, policy_page("Thuyết minh chung."), policy_page("Ghi chú. " + CALENDAR),
                                   policy_page("KỲ KẾ TOÁN NĂM CỦA NGÂN HÀNG BẮT ĐẦU TỪ NGÀY 1 THÁNG 4 VÀ KẾT THÚC VÀO NGÀY 31 THÁNG 3."))
    binding = {"document_ordinal": 1, "source_logical_name": "report.pdf", "source_sha256": "b" * 64, "scope": "SEPARATE"}
    single = NotesSource(corpus(db, [(1, one), (2, two)])).annual_policies_v1({1: "SEPARATE"})[1]
    assert single["status"] == "CALENDAR_YEAR" and single["binding"] == binding
    assert single["pointers"] == [{"page_json_version_id": two, "physical_page": 2, "pointer": "/sections/0/narratives_exact/0"}]
    assert single["assertions"][0]["original_blob_sha256"] and single["assertions"][0]["replay_receipt_id"]
    assert verify_annual_policy_v1(single, binding) == (True, "VERIFIED")
    # An uppercase competing definition on another selected page is part of the frontier and vetoes the grant.
    complete = NotesSource(corpus(db, [(1, one), (2, two), (3, three)])).annual_policies_v1({1: "SEPARATE"})[1]
    assert complete["status"] == "UNRESOLVED" and "POLICY_WINDOWS_CONFLICT" in complete["reasons"]
    # A policy printed on a page the corpus did not select is not this document's evidence.
    assert NotesSource(corpus(db, [(1, one)])).annual_policies_v1({1: "SEPARATE"})[1]["reasons"] == ["NO_PRINTED_ANNUAL_POLICY"]
    # Unrequested documents are not read; a loader provenance that is not the selected page fails the invocation.
    assert NotesSource(corpus(db, [(1, one), (2, two)])).annual_policies_v1({}) == {}
    with pytest.raises(NotesKernelError):
        NotesSource(corpus(db, [(1, one), (2, two)], relative_path="other.pdf")).annual_policies_v1({1: "SEPARATE"})
