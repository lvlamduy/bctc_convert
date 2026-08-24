from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/registered/family_first_accounting_checkpoints_v1.json"
COMPLETED = ROOT / "docs/experiments/COMPLETED_TM_FAMILIES.md"
LEDGER = ROOT / "docs/experiments/UNRESOLVED_MAPPING_LEDGER.md"
INTERBANK_EVIDENCE = (
    ROOT
    / "output/calibration/family-first-accounting-evidence-sweeps-v1"
    / "interbank-deposits-and-loans.json"
)
INTERBANK_MAPPING = (
    ROOT
    / "output/calibration/family-first-accounting-schema-mappings-v1"
    / "interbank-deposits-and-loans.json"
)

INTERBANK_UNRESOLVED_TRIALS = {
    1,
    3,
    5,
    6,
    11,
    12,
    17,
    18,
    25,
    26,
    27,
    28,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    62,
    64,
    65,
    75,
    86,
    87,
    88,
    89,
    90,
    92,
    93,
    94,
    95,
    96,
    99,
    100,
    101,
    102,
    139,
    140,
}

INTERBANK_PRIMARY_CAUSE_COUNTS = {
    "ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE": 16,
    "MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES": 15,
    "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM": 6,
    "TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM": 4,
    "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN": 1,
}


def _trading_metrics() -> dict[str, int]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    checkpoint = next(
        item for item in registry["checkpoints"] if item["family_id"] == "TRADING_SECURITIES"
    )
    return checkpoint["metrics"]


def test_current_trading_summary_and_open_ledger_share_one_denominator() -> None:
    metrics = _trading_metrics()
    completed = COMPLETED.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- TRADING_SECURITIES_OPEN_FILINGS_BEGIN -->")
    stop = ledger.index("<!-- TRADING_SECURITIES_OPEN_FILINGS_END -->")
    current = ledger[start:stop]

    assert f"{metrics['verified_document_count']}/140 filing" in completed
    assert f"{metrics['verified_mapping_count']} mapping" in completed
    assert f"{metrics['not_observed_proposal_count']} filing" in completed
    if metrics["unresolved_document_count"] == 0:
        assert "Không còn filing nào; số unresolved là 0" in completed
        assert "0 `UNRESOLVED`" in current
    else:
        assert f"{metrics['unresolved_document_count']} filing" in completed
    assert current.count("\n| TS-") == metrics["unresolved_document_count"]
    assert (
        len(set(re.findall(r"\| (TS-[0-9]{3}) \|", current)))
        == metrics["unresolved_document_count"]
    )


def test_every_current_trading_open_row_names_one_exact_filing_scope_and_review_status() -> None:
    metrics = _trading_metrics()
    ledger = LEDGER.read_text(encoding="utf-8")
    current = ledger[
        ledger.index("<!-- TRADING_SECURITIES_OPEN_FILINGS_BEGIN -->") : ledger.index(
            "<!-- TRADING_SECURITIES_OPEN_FILINGS_END -->"
        )
    ]
    rows = [line for line in current.splitlines() if line.startswith("| TS-")]
    assert len(rows) == metrics["unresolved_document_count"]
    if not rows:
        assert metrics["unresolved_document_count"] == 0
        return
    assert all(re.search(r"\| (?:Năm [0-9]{4}|(?:H1|Q[1-4])/[0-9]{4}) — ", row) for row in rows)
    assert all(" — hợp nhất — " in row or " — công ty mẹ/riêng lẻ — " in row for row in rows)
    assert all(
        " — kiểm toán |" in row or " — soát xét |" in row or " — không kiểm toán |" in row
        for row in rows
    )
    assert all(
        re.search(r"\| p[0-9]+(?:–[0-9]+)?(?:, p[0-9]+(?:–[0-9]+)?)* \|", row) for row in rows
    )
    assert "annual/H1/Q1" not in current


def test_historical_trading_section_cannot_be_mistaken_for_current_queue() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")
    historical = ledger[ledger.index("## Trading securities (`TRADING_SECURITIES`)") :]
    assert "Historical fixed-eight checkpoint only" in historical
    assert "authoritative current queue" in historical


def _interbank_unresolved_rows() -> list[list[str]]:
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- INTERBANK_575_UNRESOLVED_FILINGS_BEGIN -->")
    stop = ledger.index("<!-- INTERBANK_575_UNRESOLVED_FILINGS_END -->")
    block = ledger[start:stop]
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in block.splitlines()
        if line.startswith("| IDL-575-")
    ]


def _interbank_pdf_review_rows() -> list[list[str]]:
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- INTERBANK_575_PDF_REVIEW_BEGIN -->")
    stop = ledger.index("<!-- INTERBANK_575_PDF_REVIEW_END -->")
    block = ledger[start:stop]
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in block.splitlines()
        if line.startswith("| IDL-575-")
    ]


def _open_family_index_rows() -> list[list[str]]:
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- OPEN_FAMILY_INDEX_BEGIN -->")
    stop = ledger.index("<!-- OPEN_FAMILY_INDEX_END -->")
    block = ledger[start:stop]
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in block.splitlines()
        if re.match(r"^\| .+ \| [0-9]+ \|", line)
    ]


def _rendered_physical_page_count(page_locator: str) -> int:
    physical = page_locator.removeprefix("PDF ").split(";", 1)[0]
    count = 0
    for part in physical.split(", "):
        match = re.fullmatch(r"p([0-9]+)(?:–([0-9]+))?", part)
        assert match is not None
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        count += end - start + 1
    return count


def test_interbank_575_human_review_queue_has_41_fixable_and_one_unresolved() -> None:
    rows = _interbank_pdf_review_rows()

    assert len(rows) == 42
    assert len({row[0] for row in rows}) == 42
    assert {int(row[1]) for row in rows} == INTERBANK_UNRESOLVED_TRIALS
    assert Counter(row[2] for row in rows) == {
        "ACB": 10,
        "MBB": 2,
        "VPB": 4,
        "HDB": 10,
        "CTG": 3,
        "BID": 1,
        "VIB": 12,
    }
    assert all(row[6] == "PDF_VIEWED" for row in rows)
    assert sum(_rendered_physical_page_count(row[5]) for row in rows) == 58
    assert sum("OPEN — RESOLVABLE_PENDING_GENERIC_FIX" in row[7] for row in rows) == 41
    assert sum("OPEN — UNRESOLVED_AFTER_PDF_REVIEW" in row[7] for row in rows) == 1

    actual_unresolved = next(row for row in rows if "UNRESOLVED_AFTER_PDF_REVIEW" in row[7])
    assert actual_unresolved[:7] == [
        "IDL-575-008",
        "18",
        "MBB",
        "Q1 2025",
        "BCTC công ty mẹ/riêng lẻ",
        "PDF p26; trang in: p18",
        "PDF_VIEWED",
    ]
    assert "72.305.188" in actual_unresolved[7]
    assert "72.305.186" in actual_unresolved[7]
    assert "sáu dòng" in actual_unresolved[7]
    assert "31/12/2024" in actual_unresolved[7]
    assert "lệch 2 triệu đồng" in actual_unresolved[7]
    assert "không backsolve/sửa 2 triệu" in actual_unresolved[8]


def test_interbank_575_human_table_stays_human_readable() -> None:
    for row in _interbank_pdf_review_rows():
        cause = row[7]
        next_fix = row[8]
        assert cause and next_fix
        assert "sha256:" not in " ".join(row)
        assert "COLUMN_CONTEXT:" not in cause
        assert "HIERARCHICAL_CLOSURE:" not in cause
        assert "CANDIDATE_" not in cause
        assert "Hàng và cột kỳ nhìn thấy rõ" not in cause
        assert "Có hai vùng cùng family" not in cause
        assert "Subtotal in rõ" not in cause
        assert "Dòng kết quả cuối vùng nhìn thấy" not in cause
        assert re.search(r"`|p[0-9]+|[0-9]+\.[0-9]+", cause)


def test_interbank_575_human_causes_retain_pdf_specific_visual_findings() -> None:
    rows = {int(row[1]): row[7] for row in _interbank_pdf_review_rows()}

    assert "149.990.681 / 117.882.259" in rows[1]
    assert "125.447.269 / 117.882.259" in rows[3]
    assert all("%/năm" in rows[trial] for trial in (25, 26, 27, 28))
    assert all("Không áp dụng" in rows[trial] for trial in (25, 26, 27, 28))
    assert all("Chiết khấu, tái chiết khấu" in rows[trial] for trial in (37, 38))
    assert all("footer" in rows[trial] for trial in (39, 40))
    assert all("sibling" in rows[trial] for trial in (41, 42, 43, 44, 45, 46))
    assert "lặp lại ngay" in rows[62]
    assert "p21 chỉ là prose chính sách" in rows[64]
    assert "sibling/contra cấp family" in rows[65]
    assert "392.598.164" in rows[75]
    assert all("Thuyết minh" in rows[trial] for trial in (86, 87, 88, 89, 92, 93, 94, 96, 139))
    assert "family kế tiếp" in rows[140]


def test_interbank_575_open_ledger_has_one_auditable_row_per_trial() -> None:
    rows = _interbank_unresolved_rows()

    assert len(rows) == 42
    assert len({row[0] for row in rows}) == 42
    assert {int(row[1]) for row in rows} == INTERBANK_UNRESOLVED_TRIALS
    assert Counter(row[2].split(" / ", 1)[0] for row in rows) == {
        "ACB": 10,
        "MBB": 2,
        "VPB": 4,
        "HDB": 10,
        "CTG": 3,
        "BID": 1,
        "VIB": 12,
    }
    assert Counter(row[5].strip("`") for row in rows) == (INTERBANK_PRIMARY_CAUSE_COUNTS)


def test_every_interbank_575_open_row_keeps_source_region_and_machine_reason() -> None:
    rows = _interbank_unresolved_rows()

    for row in rows:
        bank_period_scope = row[2]
        pdf_identity = row[3]
        selected_region = row[4]
        exact_reasons = row[6]

        assert re.fullmatch(
            r"(?:ACB|MBB|VPB|HDB|CTG|BID|VIB) / "
            r"(?:Năm|H1|Q[1-4]) 20(?:25|26) / "
            r"(?:hợp nhất|công ty mẹ/riêng lẻ)",
            bank_period_scope,
        )
        assert re.search(r"`vietstock_bctc/.+\.pdf`<br>", pdf_identity)
        assert re.search(r"`sha256:[0-9a-f]{64}`$", pdf_identity)
        assert re.search(r"(?:^|<br>)(?:candidate [12]: )?p[0-9]+", selected_region)
        assert re.search(r"doc-line [0-9]+–[0-9]+", selected_region)
        assert exact_reasons.startswith("`") and exact_reasons.endswith("`")
        assert any(
            token in exact_reasons
            for token in (
                "VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE",
                "NOT_EXACT_COMPONENT_SUM",
                "NOT_ONE_EXACT_COMPONENT_SUM",
                "INHERITANCE_NOT_PROVEN",
            )
        )


def _primary_interbank_cause(trial: dict[str, object]) -> str:
    topology = trial["topology_scan"]
    assert isinstance(topology, dict)
    regions = topology["regions"]
    reasons = trial["unresolved_reasons"]
    assert isinstance(regions, list)
    assert isinstance(reasons, list)

    if len(regions) > 1:
        return "MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES"
    if reasons == ["COLUMN_CONTEXT:CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN"]:
        return "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN"
    if any("TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM" in reason for reason in reasons):
        return "TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM"
    if any("VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM" in reason for reason in reasons):
        return "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM"
    assert any("VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE" in reason for reason in reasons)
    return "ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE"


@pytest.mark.skipif(
    not INTERBANK_EVIDENCE.exists() or not INTERBANK_MAPPING.exists(),
    reason="ignored family-first artifacts are not restored in this checkout",
)
def test_interbank_575_ledger_rows_exact_match_both_replayed_artifacts() -> None:
    evidence = json.loads(INTERBANK_EVIDENCE.read_text(encoding="utf-8"))
    mapping = json.loads(INTERBANK_MAPPING.read_text(encoding="utf-8"))
    ledger = LEDGER.read_text(encoding="utf-8")
    evidence_trials = {
        trial["document_ordinal"]: trial
        for trial in evidence["trials"]
        if trial["evidence_status"] == "UNRESOLVED_EVIDENCE_GATES"
    }
    mapping_trials = {
        trial["document_ordinal"]: trial
        for trial in mapping["trials"]
        if trial["mapping_status"] == "UNRESOLVED"
    }
    rows = _interbank_unresolved_rows()
    review_rows = {int(row[1]): row for row in _interbank_pdf_review_rows()}

    assert f"`{hashlib.sha256(INTERBANK_EVIDENCE.read_bytes()).hexdigest()}`" in ledger
    assert f"`{hashlib.sha256(INTERBANK_MAPPING.read_bytes()).hexdigest()}`" in ledger
    assert len(rows) == len(evidence_trials) == len(mapping_trials) == 42
    assert set(evidence_trials) == set(mapping_trials) == {int(row[1]) for row in rows}
    assert set(review_rows) == set(evidence_trials)
    for row in rows:
        trial = evidence_trials[int(row[1])]
        mapping_trial = mapping_trials[int(row[1])]
        provenance = trial["private_provenance"]
        source = trial["source_pdf_ref"]
        regions = trial["topology_scan"]["regions"]

        assert source == mapping_trial["source_pdf_ref"]
        assert provenance == mapping_trial["private_provenance"]
        assert trial["unresolved_reasons"] == mapping_trial["unresolved_reasons"]

        period = "Năm" if provenance["period"] == "ANNUAL" else provenance["period"]
        scope = "hợp nhất" if provenance["scope"] == "CONSOLIDATED" else "công ty mẹ/riêng lẻ"
        assert row[2] == (f"{provenance['bank']} / {period} {provenance['year']} / {scope}")
        assert row[3] == (f"`{source['path']}`<br>`sha256:{source['sha256']}`")

        expected_regions = []
        for candidate_ordinal, region in enumerate(regions, start=1):
            page_start = region["page_sequence"]
            page_end = region["cluster_end_page_sequence_inclusive"]
            pages = f"p{page_start}" if page_start == page_end else f"p{page_start}–{page_end}"
            candidate = f"candidate {candidate_ordinal}: " if len(regions) > 1 else ""
            expected_regions.append(
                f"{candidate}{pages}, doc-line "
                f"{region['cluster_start_document_line_ordinal']}–"
                f"{region['cluster_end_document_line_ordinal_exclusive'] - 1}"
            )
        assert row[4] == "<br>".join(expected_regions)
        assert row[5] == f"`{_primary_interbank_cause(trial)}`"
        assert row[6] == "<br>".join(f"`{reason}`" for reason in trial["unresolved_reasons"])

        review_row = review_rows[int(row[1])]
        assert review_row[2] == provenance["bank"]
        assert review_row[3] == f"{period} {provenance['year']}"
        assert review_row[4] == (
            "BCTC hợp nhất" if provenance["scope"] == "CONSOLIDATED" else "BCTC công ty mẹ/riêng lẻ"
        )
        physical_pages = []
        for region in regions:
            page_start = region["page_sequence"]
            page_end = region["cluster_end_page_sequence_inclusive"]
            page = f"p{page_start}" if page_start == page_end else f"p{page_start}–{page_end}"
            if page not in physical_pages:
                physical_pages.append(page)
        printed_page = "p18" if int(row[1]) == 18 else "—"
        assert review_row[5] == (f"PDF {', '.join(physical_pages)}; trang in: {printed_page}")


def test_family_completion_rule_and_interbank_summary_are_in_both_status_docs() -> None:
    completed = COMPLETED.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "cập nhật cả" in completed
    assert "UNRESOLVED_MAPPING_LEDGER.md" in completed
    assert "every family checkpoint must update both" in ledger
    assert "COMPLETED_TM_FAMILIES.md" in ledger
    assert "UNRESOLVED_MAPPING_LEDGER.md#family-3-rnid-575-unresolved" in completed
    assert "UNRESOLVED_MAPPING_LEDGER.md#open-family3-rnid575" in completed
    assert "Family chưa hoàn tất" in completed
    assert "`PDF_VIEWED = 42`" in completed
    assert "`17 + 12 + 29 = 58`" in completed
    assert "41 filing\n  `OPEN — RESOLVABLE_PENDING_GENERIC_FIX`" in completed
    assert "Unresolved thực sự sau PDF review" in completed
    assert "MBB Q1/2025 công ty mẹ, PDF p26 / trang in p18" in completed
    assert "`2 triệu đồng`" in completed
    assert "41 Family 3 `RESOLVABLE_PENDING_GENERIC_FIX`" in ledger
    assert "1 Family 3\n`UNRESOLVED_AFTER_PDF_REVIEW`" in ledger
    assert "none of the 41 pending generic fixes is counted as closed" in ledger
    assert "Technical/pre-review provenance appendix" in ledger


def test_open_family_index_reconciles_143_items_and_links_every_open_heading() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")
    lines = ledger.splitlines()
    start = ledger.index("<!-- OPEN_FAMILY_INDEX_BEGIN -->")
    stop = ledger.index("<!-- OPEN_FAMILY_INDEX_END -->")
    index = ledger[start:stop]
    index_rows = _open_family_index_rows()
    indexed_targets = set(re.findall(r"\]\(#([a-z0-9-]+)\)", index))
    heading_targets = set()

    for line_index, line in enumerate(lines):
        if not line.startswith("## ") or "OPEN" not in line:
            continue
        if line == "## Danh mục OPEN cần xử lý":
            continue
        previous = line_index - 1
        while previous >= 0 and not lines[previous].strip():
            previous -= 1
        anchor = re.fullmatch(r'<a id="([a-z0-9-]+)"></a>', lines[previous])
        assert anchor is not None, line
        heading_targets.add(anchor.group(1))

    counts = {row[0]: int(row[1]) for row in index_rows}
    assert counts == {
        "Family 3 — Tiền gửi tại/cho vay TCTD khác — tài sản (575)": 42,
        "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra": 13,
        "Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý": 2,
        "Rủi ro tiền tệ": 7,
        "Rủi ro lãi suất": 1,
        "Chi phí thuế thu nhập doanh nghiệp": 7,
        "Chi phí quản lý chung": 14,
        "Thu nhập từ góp vốn, mua cổ phần và cổ tức": 1,
        "Thu nhập, chi phí và lãi thuần dịch vụ": 2,
        "Vốn và các quỹ": 9,
        "Phát hành giấy tờ có giá": 8,
        "Tiền gửi của khách hàng": 2,
        "Tài sản Có khác": 35,
    }
    assert counts["Family 3 — Tiền gửi tại/cho vay TCTD khác — tài sản (575)"] == len(
        _interbank_pdf_review_rows()
    )
    assert sum(counts.values()) == 143
    assert sum(counts.values()) - 42 == 101
    assert heading_targets <= indexed_targets
    assert len(heading_targets) == 13
    assert {
        "open-equity-funds-legacy-current",
        "open-issued-valuable-papers-legacy-current",
    } <= indexed_targets
    for target in indexed_targets:
        assert f'<a id="{target}"></a>' in ledger
    assert stop < ledger.index("## CLOSED — family-first 140-filing")


def test_family11_zero_unresolved_is_recorded_in_both_status_docs() -> None:
    completed = COMPLETED.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "## 11. Phân tích dư nợ cho vay theo khu vực địa lý" in completed
    assert "Không còn trial unresolved trong denominator này" in completed
    assert (
        "## CLOSED — family-first 140-filing "
        "`Phân tích dư nợ cho vay theo khu vực địa lý`" in ledger
    )
    assert "**0 filing `UNRESOLVED`**" in ledger
    assert "E-0175-family-first-loan-geography-140-filing-schema-sweep-seal-v1.json" in ledger
