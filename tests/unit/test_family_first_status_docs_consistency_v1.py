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
DIRECT_REVIEW_RECEIPT = (
    ROOT / "docs/experiments/E-0177-canonical-open-direct-pixel-review-receipt-v1.json"
)
DIRECT_REVIEW_RENDERER = (
    ROOT / "src/bctc_ai/evaluation/family_first_authenticated_page_region_v1.py"
)
STALE_SCHEMA_PIN_EXPERIMENTS = {
    "0073",
    "0076",
    "0078",
    "0088",
    "0091",
    "0097",
    "0098",
    "0099",
    "0127",
    "0129",
    "0131",
    "0133",
}
STALE_SCHEMA_FORMAL_ARTIFACT_COUNTS = {
    "docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json": 12,
    "docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json": 0,
    "docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json": 8,
    "docs/experiments/E-0088-operating-expense-8bank-codex-verified-mapping-v1.json": 4,
    "docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json": 1,
    "docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json": 0,
    "docs/experiments/E-0098-contingent-liabilities-8bank-codex-verified-mapping-v1.json": 13,
    "docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json": 0,
    "docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json": 29,
    "docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json": 0,
    "docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json": 2,
    "docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json": 7,
}
STALE_SCHEMA_LIVE_REFS = {
    "config/schemas/hierarchy_reference.yaml",
    "config/schemas/sources.yaml",
    "data/registered/hierarchy_registry.json",
    "data/registered/schema_coverage_registry.json",
    "data/registered/schema_registry.json",
    "reference/schemas/schema_graph.jsonl",
    "template/Bank_TM_ReportNormId.v2.xlsx",
}
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


def _canonical_open_source_rows() -> list[list[str]]:
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- CANONICAL_OPEN_SOURCE_ROWS_BEGIN -->")
    stop = ledger.index("<!-- CANONICAL_OPEN_SOURCE_ROWS_END -->")
    block = ledger[start:stop]
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in block.splitlines()
        if line.startswith("| F3-") or line.startswith("| E0")
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
    canonical_family3 = [row for row in _canonical_open_source_rows() if row[0].startswith("F3-")]
    assert sum(row[7] == "RESOLVABLE_PENDING_GENERIC_FIX" for row in canonical_family3) == 41
    assert sum(row[7] == "KEEP_UNRESOLVED_SOURCE_CONFLICT" for row in canonical_family3) == 1
    assert "Technical/pre-review provenance appendix" in ledger


def test_open_family_index_reconciles_247_items_and_links_every_open_heading() -> None:
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
        "Tài sản/GTCG đem thế chấp, cầm cố, chiết khấu": 3,
        "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra": 26,
        "Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý": 5,
        "Rủi ro tiền tệ": 10,
        "Rủi ro lãi suất": 1,
        "Rủi ro thanh khoản": 4,
        "Tỷ giá ngoại tệ": 34,
        "Chi phí thuế thu nhập doanh nghiệp": 8,
        "Chi phí quản lý chung": 18,
        "Thu nhập từ góp vốn, mua cổ phần và cổ tức": 1,
        "Thu nhập, chi phí và lãi thuần dịch vụ": 2,
        "Vốn và các quỹ": 17,
        "Phát hành giấy tờ có giá": 8,
        "Tiền gửi của khách hàng": 2,
        "Tài sản Có khác": 47,
        "Tiền gửi/vay TCTD khác — nguồn vốn": 2,
        "Báo cáo bộ phận hợp nhất": 17,
    }
    assert counts["Family 3 — Tiền gửi tại/cho vay TCTD khác — tài sản (575)"] == len(
        _interbank_pdf_review_rows()
    )
    assert sum(counts.values()) == 247
    assert sum(counts.values()) - 42 == 205
    assert heading_targets <= indexed_targets
    assert len(heading_targets) == 14
    assert {
        "open-equity-funds-legacy-current",
        "open-issued-valuable-papers-legacy-current",
    } <= indexed_targets
    for target in indexed_targets:
        assert f'<a id="{target}"></a>' in ledger
    assert stop < ledger.index("## CLOSED — family-first 140-filing")


def test_canonical_open_queue_covers_every_source_row_with_human_and_pixel_evidence() -> None:
    rows = _canonical_open_source_rows()
    ids = [row[0] for row in rows]

    assert len(rows) == 247
    assert all(len(row) == 10 for row in rows)
    assert len(set(ids)) == 247
    assert sum(item.startswith("F3-IDL-575-") for item in ids) == 42
    assert sum(item.startswith("E") for item in ids) == 205
    assert "PM-001" not in " ".join(ids)
    assert not any(re.fullmatch(r"(?:CL|FI)-[0-9]+", item) for item in ids)

    experiment_counts = Counter(
        match.group(1) for item in ids if (match := re.match(r"^E([0-9]{4})-", item))
    )
    assert experiment_counts == {
        "0073": 12,
        "0076": 3,
        "0078": 10,
        "0088": 4,
        "0091": 1,
        "0097": 3,
        "0098": 13,
        "0099": 3,
        "0101": 3,
        "0103": 4,
        "0104": 15,
        "0127": 35,
        "0129": 2,
        "0131": 5,
        "0133": 7,
        "0137": 2,
        "0142": 1,
        "0143": 14,
        "0146": 7,
        "0153": 13,
        "0154": 2,
        "0155": 7,
        "0156": 1,
        "0158": 19,
        "0159": 2,
        "0161": 17,
    }
    annual_experiments = {
        "0127",
        "0129",
        "0131",
        "0133",
        "0137",
        "0142",
        "0143",
        "0146",
        "0153",
        "0154",
        "0155",
        "0156",
        "0158",
        "0159",
        "0161",
    }
    assert sum(experiment_counts[key] for key in annual_experiments) == 134
    assert (
        sum(count for key, count in experiment_counts.items() if key not in annual_experiments)
        == 71
    )

    allowed_statuses = {
        "RESOLVABLE_PENDING_GENERIC_FIX",
        "KEEP_UNRESOLVED_SCHEMA_GAP",
        "KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY",
        "KEEP_UNRESOLVED_SEMANTIC_GAP",
        "KEEP_UNRESOLVED_SOURCE_SCOPE",
        "KEEP_UNRESOLVED_SOURCE_CONFLICT",
        "KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE",
    }
    assert Counter(row[7] for row in rows) == {
        "KEEP_UNRESOLVED_SCHEMA_GAP": 80,
        "KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY": 76,
        "RESOLVABLE_PENDING_GENERIC_FIX": 51,
        "KEEP_UNRESOLVED_SEMANTIC_GAP": 17,
        "KEEP_UNRESOLVED_SOURCE_SCOPE": 11,
        "KEEP_UNRESOLVED_SOURCE_CONFLICT": 7,
        "KEEP_UNRESOLVED_SOURCE_VALUE_UNAVAILABLE": 5,
    }
    for row in rows:
        assert row[0] and row[1] and "source " in row[1]
        assert row[2]
        assert re.fullmatch(
            r"(?:ACB|MBB|VPB|HDB|VCB|CTG|BID|VIB) / "
            r"(?:Năm|H1|Q[1-4]) 20[0-9]{2} / "
            r"BCTC (?:hợp nhất|công ty mẹ/riêng lẻ) / "
            r"(?:kiểm toán|soát xét|không kiểm toán)",
            row[3],
        )
        assert re.search(r"[.]pdf<br>sha256:[0-9a-f]{64}$", row[4])
        assert row[5].startswith("physical p")
        assert "printed" in row[5] or "trang in" in row[5]
        assert row[6].startswith("DIRECT_PIXEL_REVIEW_2026-08-24") or row[6].startswith(
            "PERSISTED_"
        )
        assert row[7] in allowed_statuses
        assert len(row[8]) >= 45
        assert not re.fullmatch(r"[A-Z0-9_:; ./-]+", row[8])
        assert "formal:" in row[9]

    direct_rows = {row[0]: row for row in rows if row[6].startswith("DIRECT_")}
    assert set(direct_rows) == {
        "E0078-CAF-009",
        "E0078-CAF-010",
        "E0161-ASEG-005",
        "E0161-ASEG-014",
    }
    assert direct_rows["E0078-CAF-009"][5] == "physical p27–28; printed p24–25"
    assert direct_rows["E0078-CAF-010"][5] == "physical p44–45; printed p42–43"
    assert direct_rows["E0161-ASEG-005"][5] == "physical p83; printed p79"
    assert direct_rows["E0161-ASEG-014"][5] == "physical p82; printed p80"

    ledger = LEDGER.read_text(encoding="utf-8")
    assert (
        "NEEDS_DIRECT_PIXEL_REVIEW"
        not in ledger[
            ledger.index("<!-- CANONICAL_OPEN_SOURCE_ROWS_BEGIN -->") : ledger.index(
                "<!-- CANONICAL_OPEN_SOURCE_ROWS_END -->"
            )
        ]
    )
    for stale in ("143 work item", "101 item", "441 / 143 OPEN"):
        assert stale not in ledger
    assert "545 entries = 247 OPEN + 298 closed/history" in ledger
    assert "CLOSED_STALE_PERIOD_GAP" in ledger


def test_direct_pixel_review_receipt_is_complete_and_linked_from_every_direct_row() -> None:
    receipt = json.loads(DIRECT_REVIEW_RECEIPT.read_text(encoding="utf-8"))
    renderer = receipt["renderers"]
    reviews = receipt["reviews"]

    assert receipt["experiment_id"] == "E-0177"
    assert renderer["dpi"] == 200
    assert renderer["implementation"].endswith(
        "family_first_authenticated_page_region_v1.py::_render_page"
    )
    assert (
        renderer["implementation_sha256"]
        == hashlib.sha256(DIRECT_REVIEW_RENDERER.read_bytes()).hexdigest()
    )
    assert renderer["direct_review_observed"] == {
        "interpreter": "system python3 with PYTHONPATH=src",
        "pymupdf_VersionBind": "1.26.3",
        "pymupdf_VersionFitz": "1.26.3",
    }
    assert renderer["canonical_replay"] == {
        "interpreter": ".venv/bin/python",
        "pymupdf_VersionBind": "1.28.0",
        "pymupdf_VersionFitz": "1.29.0",
    }
    assert {review["review_key"] for review in reviews} == {
        "E0078-CAF-009:p27",
        "E0078-CAF-009:p28",
        "E0078-CAF-010:p44",
        "E0078-CAF-010:p45",
        "E0161-ASEG-005:p83",
        "E0161-ASEG-014:p82",
    }
    assert all(review["source_pdf"]["sha256"] for review in reviews)
    assert all(review["physical_page"] > 0 for review in reviews)
    assert all(review["review_observed_render"]["sha256"] for review in reviews)
    assert all(review["canonical_replay_render"]["sha256"] for review in reviews)

    differing = [
        review
        for review in reviews
        if review["review_observed_render"] != review["canonical_replay_render"]
    ]
    assert [review["review_key"] for review in differing] == ["E0161-ASEG-014:p82"]
    assert differing[0]["review_observed_render"] == {
        "format": "PNG",
        "sha256": "f3fb0c18b88ff2137ed0f03351bbf019adbb29c6c66eca96c16ca1880cec9e79",
        "size_bytes": 1438284,
    }
    assert differing[0]["canonical_replay_render"] == {
        "format": "PNG",
        "sha256": "01c83ad86684b837c60c1a94dbcd47eea0fe7d870a1352688518e8a541b3438d",
        "size_bytes": 1438261,
    }

    direct_rows = {
        row[0]: row for row in _canonical_open_source_rows() if row[6].startswith("DIRECT_")
    }
    assert set(direct_rows) == {
        "E0078-CAF-009",
        "E0078-CAF-010",
        "E0161-ASEG-005",
        "E0161-ASEG-014",
    }
    assert all(
        "[receipt E-0177](E-0177-canonical-open-direct-pixel-review-receipt-v1.json)" in row[6]
        for row in direct_rows.values()
    )
    assert (
        "f3fb0c18b88ff2137ed0f03351bbf019adbb29c6c66eca96c16ca1880cec9e79"
        in (direct_rows["E0161-ASEG-014"][6])
    )
    assert (
        "01c83ad86684b837c60c1a94dbcd47eea0fe7d870a1352688518e8a541b3438d"
        in (direct_rows["E0161-ASEG-014"][6])
    )


@pytest.mark.skipif(
    not DIRECT_REVIEW_RECEIPT.exists()
    or any(
        not (ROOT / review["source_pdf"]["path"]).exists()
        for review in json.loads(DIRECT_REVIEW_RECEIPT.read_text(encoding="utf-8"))["reviews"]
    ),
    reason="the four private source PDFs are not restored in this checkout",
)
def test_direct_pixel_review_receipt_replays_all_six_pages_without_temp_files() -> None:
    import fitz

    from bctc_ai.evaluation.family_first_authenticated_page_region_v1 import _render_page

    receipt = json.loads(DIRECT_REVIEW_RECEIPT.read_text(encoding="utf-8"))
    renderer = receipt["renderers"]

    assert fitz.VersionBind == renderer["canonical_replay"]["pymupdf_VersionBind"]
    assert fitz.VersionFitz == renderer["canonical_replay"]["pymupdf_VersionFitz"]
    for review in receipt["reviews"]:
        source = (ROOT / review["source_pdf"]["path"]).read_bytes()
        assert hashlib.sha256(source).hexdigest() == review["source_pdf"]["sha256"]
        assert len(source) == review["source_pdf"]["size_bytes"]

        render = _render_page(
            source,
            physical_page=review["physical_page"],
            dpi=renderer["dpi"],
        )
        assert hashlib.sha256(render).hexdigest() == review["canonical_replay_render"]["sha256"]
        assert len(render) == review["canonical_replay_render"]["size_bytes"]


def test_stale_schema_pins_fail_closed_only_for_the_76_affected_schema_gap_rows() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")
    note = ledger[
        ledger.index("<!-- STALE_SCHEMA_PIN_LIVE_REPLAY_BEGIN -->") : ledger.index(
            "<!-- STALE_SCHEMA_PIN_LIVE_REPLAY_END -->"
        )
    ]
    rows = _canonical_open_source_rows()

    assert "84 cặp hash/kích thước không còn khớp" in note
    assert "không phải exact replay của schema hiện hành" in note
    assert "KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY" in note
    assert all(f"`{path}`" in note for path in STALE_SCHEMA_FORMAL_ARTIFACT_COUNTS)
    assert all(f"`{path}`" in note for path in STALE_SCHEMA_LIVE_REFS)

    replay_rows = [
        row for row in rows if row[7] == "KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY"
    ]
    assert len(replay_rows) == 76
    counts = Counter(row[9].rsplit("<br>formal: ", 1)[1] for row in replay_rows)
    assert counts == Counter(
        {path: count for path, count in STALE_SCHEMA_FORMAL_ARTIFACT_COUNTS.items() if count}
    )
    for row in rows:
        match = re.match(r"^E([0-9]{4})-", row[0])
        if match is None:
            continue
        belongs_to_stale_artifact = match.group(1) in STALE_SCHEMA_PIN_EXPERIMENTS
        if belongs_to_stale_artifact and "SCHEMA_GAP" in row[7]:
            assert row[7] == "KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY"
        if row[7] == "KEEP_UNRESOLVED_SCHEMA_GAP_REQUIRES_LIVE_SCHEMA_REPLAY":
            assert belongs_to_stale_artifact


def test_corrected_open_human_reasons_name_the_exact_axis_or_margin_population() -> None:
    rows = {row[0]: row for row in _canonical_open_source_rows()}

    for row_id, currency in {
        "E0155-A2025-CRISK-001": "AUD",
        "E0155-A2025-CRISK-002": "CAD",
        "E0155-A2025-CRISK-004": "JPY",
    }.items():
        assert f"Trục {currency}" in rows[row_id][8]
        assert "năm ô nguồn" in rows[row_id][8]
        assert "nhánh vàng" not in rows[row_id][8]

    for experiment in ("E0098", "E0153"):
        for row_id in ("003", "007"):
            assert "nhóm L/C" in rows[f"{experiment}-CL-{row_id}"][8]
            assert "parent L/C" in rows[f"{experiment}-CL-{row_id}"][8]
        for row_id in ("005", "009"):
            assert "nhóm bảo lãnh" in rows[f"{experiment}-CL-{row_id}"][8]
            assert "parent bảo lãnh" in rows[f"{experiment}-CL-{row_id}"][8]

    keep_e0161 = {f"E0161-ASEG-{ordinal:03d}" for ordinal in range(1, 18) if ordinal not in {5, 14}}
    assert all(
        "không đồng nhất schema hoặc là blank thật" not in rows[row_id][8] for row_id in keep_e0161
    )
    assert "blank thật, không phải dấu gạch và không phải 0" in rows["E0161-ASEG-017"][8]


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
