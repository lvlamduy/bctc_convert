"""Document-owned annual accounting-period policy evidence (Codex 0250; prototype, opt-in by data, never by amount).

A bank's notes print its accounting year once, in the accounting-policy narratives ("Năm tài chính của Ngân hàng
bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31 tháng 12"). A note lane headed exactly "Năm kết thúc ngày
31/12/2025" prints a YEAR grain and an end date but no start; with that printed calendar-year policy the start is
printed too, so the lane is DURATION:YEAR:2025 by the document's own words.

This module only collects and resolves the policy evidence, from the AUTHENTICATED ORIGINAL page objects (never
the validator projection), keeping every assertion with its exact pointer, entire narrative, section/BLOB hashes,
owner and qualifiers. ``resolve_annual_policy_v1`` yields CALENDAR_YEAR only when every assertion is the
document entity's own 01/01-31/12 year with no qualifier (first / short / long / changed year); anything else,
including no assertion, an unknown or foreign owner, a qualifier or two different windows, stays UNRESOLVED with
its reasons. The kernel applies it only to a held "Năm kết thúc ngày 31/12/Y" lane (``year_ended_policy_v1``).
"""

from __future__ import annotations

import re
from typing import Any

from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

CALENDAR_YEAR = "CALENDAR_YEAR"
_DAY_MONTH = r"(?:ngay\s+)?(\d{1,2})(?:\s+thang\s+|\s*/\s*)(\d{1,2})"
_POLICY = re.compile(
    r"(?P<subject>nam tai chinh|ky ke toan nam)(?P<owner>[^.;:]{0,80}?)\s+bat dau\s+(?:tu|vao)\s+" + _DAY_MONTH
    + r"(?:\s+nam\s+\d{4})?\s*(?:,\s*)?va\s+ket thuc\s+(?:vao|tai)?\s*" + _DAY_MONTH)
_ENTITY = re.compile(r"\bcua\s+(?:ngan hang|tap doan)\b")
_FOREIGN = re.compile(r"\bcua\s+(?:cac\s+)?(?:cong ty|chi nhanh|don vi)\b")
_QUALIFIERS = {"FIRST_YEAR": r"\bnam tai chinh dau tien\b|\bky ke toan nam dau tien\b",
               "SHORT_OR_LONG_YEAR": r"\bngan hon\b|\bdai hon\b|\b(?:15|muoi lam) thang\b",
               "CHANGED_YEAR": r"\bthay doi (?:nam tai chinh|ky ke toan)\b|\bchuyen doi (?:nam tai chinh|ky ke toan)\b"}


def policy_assertions_v1(page_json: dict[str, Any], provenance: dict[str, Any]) -> list[dict[str, Any]]:
    """Every annual-period definition printed in the ORIGINAL page's section narratives, with its source binding."""

    found = []
    for s, section in enumerate(page_json.get("sections") or []):
        narratives = section.get("narratives_exact") if type(section) is dict else None
        if type(narratives) is not list:
            continue
        for i, narrative in enumerate(narratives):
            if type(narrative) is not str:
                continue
            folded = re.sub(r"\s+", " ", fold_vietnamese(narrative))
            for match in _POLICY.finditer(folded):
                owner_text = match.group("owner")
                owner = ("DOCUMENT_ENTITY" if _ENTITY.search(owner_text) else
                         "FOREIGN" if _FOREIGN.search(owner_text) else "UNKNOWN")
                found.append({
                    **provenance,
                    "pointer": f"/sections/{s}/narratives_exact/{i}", "section_index": s, "narrative_index": i,
                    "narrative_exact": narrative, "match_folded": match.group(0),
                    "section_sha256": canonical_json_sha256_v1(section),
                    "window": {"start": f"{int(match.group(4)):02d}-{int(match.group(3)):02d}",
                               "end": f"{int(match.group(6)):02d}-{int(match.group(5)):02d}"},
                    "owner": owner,
                    "qualifiers": sorted(name for name, pattern in _QUALIFIERS.items() if re.search(pattern, folded)),
                })
    return found


def resolve_annual_policy_v1(assertions: list[dict[str, Any]]) -> dict[str, Any]:
    """CALENDAR_YEAR only when every assertion is the document entity's own unqualified 01-01..12-31 year."""

    reasons = []
    if not assertions:
        reasons.append("NO_PRINTED_ANNUAL_POLICY")
    if any(a["owner"] != "DOCUMENT_ENTITY" for a in assertions):
        reasons.append("POLICY_OWNER_UNKNOWN_OR_FOREIGN")
    if any(a["qualifiers"] for a in assertions):
        reasons.append("POLICY_QUALIFIED_FIRST_SHORT_LONG_OR_CHANGED_YEAR")
    windows = {(a["window"]["start"], a["window"]["end"]) for a in assertions}
    if len(windows) > 1:
        reasons.append("POLICY_WINDOWS_CONFLICT")
    elif windows and windows != {("01-01", "12-31")}:
        reasons.append("POLICY_NOT_A_CALENDAR_YEAR")
    return {"status": "UNRESOLVED" if reasons else CALENDAR_YEAR, "reasons": reasons,
            "pointers": [{k: a.get(k) for k in ("page_json_version_id", "physical_page", "pointer")} for a in assertions],
            "assertions": assertions}
