"""Notes engine: document-owned annual-policy capture for "Năm kết thúc ngày 31/12/Y" lanes (Codex 0250/0254/0258)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_notes_income_tax import RECON, cells, context_of, document, kqkd, make_table
from test_notes_source_bridge import corpus

from bctc_ai.notes.annual_policy_v1 import (
    PolicyCapture,
    assertions_v1,
    policy_page_v1,
    policy_sentences_v1,
    verify_annual_policy_v1,
)
from bctc_ai.notes.concept_list_shape_v1 import evaluate_concept_table_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.kernel_v1 import (
    NotesKernelError,
    NotesSource,
    resolve_duration_lanes_v1,
    year_ended_policy_v1,
)
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
BINDING = (1, "x.pdf", "0" * 64, "SEPARATE")


def policy_page(*narratives):
    return {"status": "FINANCIAL_NOTE_CONTENT",
            "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE", "title_exact": "2. Cơ sở trình bày",
                          "narratives_exact": list(narratives), "tables": []}],
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}


def page_of(narratives, number=12):
    return policy_page_v1(policy_page(*narratives), page_json_version_id=f"v{number}", physical_page=number,
                          original_blob_sha256="a" * 64, replay_receipt_id=f"receipt-{number}")


def capture(*narratives, scope="SEPARATE", pages=None):
    """A collector-shaped capture: one page (or the given narrative lists as pages) with its full frontier."""

    built = [page_of(list(p), 12 + i) for i, p in enumerate(pages or [narratives])]
    frontier = tuple((p.page_json_version_id, sum(len(policy_sentences_v1(n)) for _ptr, n in p.narratives)) for p in built)
    return PolicyCapture((*BINDING[:3], scope), frontier, tuple(p for p, (_v, count) in zip(built, frontier, strict=False) if count))


@pytest.fixture(scope="module")
def family():
    return load_notes_config_v1(ROOT).families["INCOME_TAX"]


def interim(policy, **override):
    return replace(document(quarter=4), income_context_texts=INTERIM_Q4, annual_policy=policy, **override)


# --------------------------------------------------------------------------- capture, resolution, verification


def test_the_actual_lpb_clause_is_a_scope_bound_calendar_definition():
    eps = ("Theo hướng dẫn …, bao gồm những thay đổi xảy ra sau ngày kết thúc năm tài chính nhưng trước ngày phát hành "
           "báo cáo tài chính.")
    lpb = capture("(d) Tổng số nhân viên", LPB, eps)
    [assertion] = assertions_v1(lpb)  # the Q4 endpoint sentence and the EPS sentence are not policy candidates
    assert assertion["pointer"] == "/sections/0/narratives_exact/1" and assertion["kind"] == "DEFINITION"
    assert assertion["sentence_exact"] == "(c) Kỳ kế toán\n" + CALENDAR  # the cue-free heading line is set aside
    assert assertion["owner"] == "BANK" and assertion["window"] == {"start": "01-01", "end": "12-31"}
    granted, why, resolution = verify_annual_policy_v1(lpb, BINDING)
    assert (granted, why) == (True, "VERIFIED") and resolution["pointers"] == [
        {"page_json_version_id": "v12", "physical_page": 12, "pointer": "/sections/0/narratives_exact/1"}]
    group = capture("Năm tài chính của Tập đoàn bắt đầu từ ngày 01/01 và kết thúc vào ngày 31/12 hàng năm.", scope="CONSOLIDATED")
    assert verify_annual_policy_v1(group, (*BINDING[:3], "CONSOLIDATED"))[:2] == (True, "VERIFIED")


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
    # Codex 0258: physically wrapped competitors and qualifiers stay in the frontier; raw marks fail before folding.
    ((CALENDAR, "Năm tài chính\ncủa Ngân hàng bắt đầu từ ngày 1 tháng 7 và kết thúc vào ngày 30 tháng 6."), "SEPARATE",
     "POLICY_WINDOWS_CONFLICT"),
    ((CALENDAR, "Năm tài chính đầu tiên\ncủa Ngân hàng ngắn hơn 12 tháng."), "SEPARATE",
     "POLICY_QUALIFIED_FIRST_SHORT_LONG_OR_CHANGED_YEAR"),
    (("Kỳ kế toán năm của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12\u0301.",), "SEPARATE",
     "UNSUPPORTED_POLICY_WORDING"),
    # Codex 0260: only the reviewed generic heading "(c) Kỳ kế toán" is set aside; an exception or owner heading is not.
    (("(c) Ngoại lệ cho năm đầu tiên\n" + CALENDAR,), "SEPARATE", "UNSUPPORTED_POLICY_WORDING"),
    (("(c) Riêng công ty con\n" + CALENDAR,), "SEPARATE", "UNSUPPORTED_POLICY_WORDING"),
])
def test_unknown_foreign_scoped_absolute_unsupported_qualified_wrapped_marked_or_conflicting_policy_never_grants(
        narratives, scope, reason):
    granted, why, resolution = verify_annual_policy_v1(capture(*narratives, scope=scope), (*BINDING[:3], scope))
    assert (granted, why) == (False, "DOCUMENT_ANNUAL_POLICY_UNRESOLVED") and reason in resolution["reasons"]


def test_status_tags_other_documents_and_dropped_resealed_or_moved_evidence_never_verify():
    qualified = capture(CALENDAR + " Năm tài chính đầu tiên của Ngân hàng ngắn hơn 12 tháng.")
    page = qualified.pages[0]
    assert verify_annual_policy_v1({"status": "CALENDAR_YEAR"}, BINDING)[1] == "POLICY_NOT_A_CAPTURE"
    assert verify_annual_policy_v1(capture(CALENDAR), (1, "x.pdf", "9" * 64, "SEPARATE"))[1] == "POLICY_BINDING_IS_ANOTHER_DOCUMENT_OR_SCOPE"
    # Dropping the qualifier sentence from the captured narrative without resealing the page hash.
    edited = replace(page, narratives=(("/sections/0/narratives_exact/0", CALENDAR),))
    assert verify_annual_policy_v1(replace(qualified, pages=(edited,)), BINDING)[1] == "POLICY_PAGE_NARRATIVES_HASH_MISMATCH"
    # Resealed: the page hash recomputed, but the frontier still records two stored candidates on that page.
    resealed = page_of([CALENDAR])
    assert verify_annual_policy_v1(replace(qualified, pages=(resealed,)), BINDING)[1] == "POLICY_FRONTIER_CANDIDATES_NOT_CAPTURED"
    # A whole competing page removed: its frontier count stays and the grant cannot come from the remaining page.
    two = capture(pages=[[CALENDAR], ["Năm tài chính của Ngân hàng bắt đầu từ ngày 1 tháng 4 và kết thúc vào ngày 31 tháng 3."]])
    assert verify_annual_policy_v1(replace(two, pages=two.pages[:1]), BINDING)[1] == "POLICY_FRONTIER_CANDIDATES_NOT_CAPTURED"
    # A moved pointer changes the sealed page; a page outside the frontier is not this document's evidence.
    moved = replace(page, narratives=(("/sections/0/narratives_exact/7", page.narratives[0][1]),))
    assert verify_annual_policy_v1(replace(qualified, pages=(moved,)), BINDING)[1] == "POLICY_PAGE_NARRATIVES_HASH_MISMATCH"
    stray = page_of([CALENDAR], number=99)
    assert verify_annual_policy_v1(replace(capture(CALENDAR), pages=(stray,)), BINDING)[1] == "POLICY_PAGE_NOT_BOUND_TO_FRONTIER"


# --------------------------------------------------------------------------- lanes


def test_year_ended_lanes_take_their_own_printed_year_under_a_verified_calendar_policy():
    table = make_table(RECON[:1], YEAR_ENDED)
    lanes = resolve_duration_lanes_v1(table, interim(capture(CALENDAR)), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == ["DURATION:YEAR:2025", "DURATION:YEAR:2024"]  # 2024 printed, not minus one
    assert all(lane.period_basis == "PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:v12@p12/sections/0/narratives_exact/0"
               and lane.reasons == [] and lane.shadow_evidence == [] for lane in lanes)


@pytest.mark.parametrize("header,policy,why", [
    ("Năm kết thúc ngày 31/12/2025", None, "DOCUMENT_ANNUAL_POLICY_ABSENT"),
    ("Năm kết thúc ngày 31/12/2025", "unresolved", "DOCUMENT_ANNUAL_POLICY_UNRESOLVED"),
    ("Năm kết thúc ngày 31/12/2025", "status_only", "POLICY_NOT_A_CAPTURE"),
    ("Năm kết thúc ngày 31/12/2025", "foreign", "POLICY_BINDING_IS_ANOTHER_DOCUMENT_OR_SCOPE"),
    ("Năm kết thúc ngày 30/06/2025", "calendar", "YEAR_END_NOT_31_DECEMBER"),
])
def test_absent_unresolved_untrusted_foreign_or_non_december_policy_keeps_the_hold(header, policy, why, monkeypatch):
    policies = {None: None, "unresolved": capture(), "status_only": {"status": "CALENDAR_YEAR"},
                "foreign": replace(capture(CALENDAR), binding=(1, "x.pdf", "9" * 64, "SEPARATE")), "calendar": capture(CALENDAR)}
    table = make_table(RECON[:1], [(header,)])
    if policy is None:
        # Codex 0272/0273: without a capture the policy is never consulted and the lane is exactly the pre-policy
        # kernel's (one reason, nothing granted); only a direct caller of the helper is told the policy is absent.
        from bctc_ai.notes import kernel_v1

        assert year_ended_policy_v1(header, interim(None), statement_period_context_v1([])) == (None, why)

        def consulted(*_args):
            raise AssertionError("annual policy consulted without a capture")

        monkeypatch.setattr(kernel_v1, "year_ended_policy_v1", consulted)
        [lane] = resolve_duration_lanes_v1(table, interim(None), [], [table.table_title])
        assert (lane.period_key, lane.period_basis, lane.candidates, lane.reasons) == (
            None, "UNRESOLVED", [], ["PERIOD_UNRESOLVED:PERIOD_END_WITHOUT_PRINTED_DURATION"])
        assert [e["candidate"] for e in lane.shadow_evidence] == ["DURATION:YEAR_ENDED:2025-12-31"]
        return
    [lane] = resolve_duration_lanes_v1(table, interim(policies[policy]), [], [table.table_title])
    assert lane.period_key is None
    assert lane.reasons[:2] == ["PERIOD_UNRESOLVED:PERIOD_END_WITHOUT_PRINTED_DURATION", "ANNUAL_POLICY_NOT_APPLIED:" + why]


def test_a_contradictory_own_six_month_caption_keeps_the_hold():
    own = "Chi phí thuế cho giai đoạn sáu tháng kết thúc ngày 30 tháng 6 năm 2025"
    table = make_table(RECON[:1], YEAR_ENDED[:1], title=own)
    [lane] = resolve_duration_lanes_v1(table, interim(capture(CALENDAR)), [], [table.table_title])
    assert lane.period_key is None and not lane.period_basis.startswith("PRINTED_YEAR_ENDED") and lane.reasons
    doc = interim(capture(CALENDAR))
    assert year_ended_policy_v1("Năm kết thúc ngày 31/12/2025", doc, statement_period_context_v1([own])) == (
        None, "OWN_CAPTION_WINDOW_CONFLICT")
    assert year_ended_policy_v1("Năm kết thúc ngày 31/12/2025", doc, statement_period_context_v1([])) == (
        ("DURATION:YEAR:2025", "PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:v12@p12/sections/0/narratives_exact/0"), None)


def test_other_headers_resolve_exactly_as_without_the_policy():
    # The interim fixture prints an explicit 01/01..31/12 range, so e.g. "Kỳ này" already resolves by its independent
    # route; the policy must change nothing for any header that is not a YEAR_ENDED 31/12 lane.
    headers = [("31/12/2025",), ("Kỳ này",), ("Quý 4/2025",), ("Lũy kế 31/12/2025",),
               ("Năm kết thúc ngày 31/12/2025 (trình bày lại)",), ("Năm kết thúc ngày 31/12/2025 và 31/12/2024",)]
    table = make_table(RECON[:1], headers)
    with_policy = resolve_duration_lanes_v1(table, interim(capture(CALENDAR)), [], [table.table_title])
    without = resolve_duration_lanes_v1(table, interim(None), [], [table.table_title])
    assert [(lane.period_key, lane.period_basis) for lane in with_policy] == [(lane.period_key, lane.period_basis) for lane in without]
    assert not any(lane.period_basis.startswith("PRINTED_YEAR_ENDED") for lane in with_policy)
    assert with_policy[2].period_key == "DURATION:QUARTER:4:2025"


def test_primary_amounts_never_change_the_policy_period(family):
    keys = []
    for primary in ({}, kqkd({"DURATION:YEAR:2025": {"CURRENT": "87808"}}), kqkd({"DURATION:YEAR:2025": {"CURRENT": "1"}})):
        table = make_table(RECON, YEAR_ENDED)
        result = cells(evaluate_concept_table_v1(table, family, interim(capture(CALENDAR), primary_cells=primary),
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


def test_the_complete_frontier_is_captured_from_authenticated_selected_original_pages(tmp_path):
    wrapped = "Kỳ kế toán năm\ncủa Ngân hàng bắt đầu từ ngày 1 tháng 4 và kết thúc vào ngày 31 tháng 3."
    db, (one, two, three) = _store(tmp_path, policy_page("Thuyết minh chung."), policy_page("Ghi chú. " + CALENDAR),
                                   policy_page(wrapped))
    binding = (1, "report.pdf", "b" * 64, "SEPARATE")
    single = NotesSource(corpus(db, [(1, one), (2, two)])).annual_policies_v1({1: "SEPARATE"})[1]
    assert single.binding == binding and single.frontier == ((one, 0), (two, 1))
    assert [p.page_json_version_id for p in single.pages] == [two] and single.pages[0].replay_receipt_id
    granted, why, resolution = verify_annual_policy_v1(single, binding)
    assert (granted, why) == (True, "VERIFIED")
    assert resolution["pointers"] == [{"page_json_version_id": two, "physical_page": 2, "pointer": "/sections/0/narratives_exact/0"}]
    # A wrapped competing definition on another selected page is part of the frontier and vetoes the grant.
    complete = NotesSource(corpus(db, [(1, one), (2, two), (3, three)])).annual_policies_v1({1: "SEPARATE"})[1]
    granted, _why, resolution = verify_annual_policy_v1(complete, binding)
    assert not granted and "POLICY_WINDOWS_CONFLICT" in resolution["reasons"]
    # A policy printed on a page the corpus did not select is not this document's evidence.
    unselected = NotesSource(corpus(db, [(1, one)])).annual_policies_v1({1: "SEPARATE"})[1]
    assert verify_annual_policy_v1(unselected, binding)[2]["reasons"] == ["NO_PRINTED_ANNUAL_POLICY"]
    # Unrequested documents are not read; a loader provenance that is not the selected page fails the invocation.
    assert NotesSource(corpus(db, [(1, one), (2, two)])).annual_policies_v1({}) == {}
    with pytest.raises(NotesKernelError):
        NotesSource(corpus(db, [(1, one), (2, two)], relative_path="other.pdf")).annual_policies_v1({1: "SEPARATE"})
