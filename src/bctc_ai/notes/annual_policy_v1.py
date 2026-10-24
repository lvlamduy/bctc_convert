"""Document-owned annual accounting-period policy evidence (Codex 0250/0254; prototype, never by amount).

A bank's notes print its accounting year once, in the accounting-policy narratives (LPB FULL69 p12
/sections/0/narratives_exact/5: "Kỳ kế toán năm của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc vào ngày 31
tháng 12."). A note lane headed exactly "Năm kết thúc ngày 31/12/2025" prints a YEAR grain and an end but no start;
with that printed recurring calendar-year policy the start is printed too, so the lane is DURATION:YEAR:2025.

Evidence (from AUTHENTICATED ORIGINAL narratives only). Every narrative is split into sentences (newline, ". ",
"; "). A sentence naming the accounting year (năm tài chính / kỳ kế toán năm / niên độ kế toán / năm kế toán) together
with "bắt đầu" is a policy CANDIDATE, and so is any sentence naming a first / changed accounting year. Each candidate
is kept whole with its pointer, raw sentence, section hash and source binding, and is classified:
  * DEFINITION only when the WHOLE folded sentence is the finite grammar
    "<subject> [<owner>] bắt đầu từ/vào [ngày] D tháng M | D/M [năm Y | /Y] [,] và kết thúc [vào|tại] [ngày] D tháng M |
    D/M [năm Y | /Y] [hàng năm]" with ASCII digits; printed years are retained (an absolute interval is not a
    recurrence);
  * UNSUPPORTED_WORDING for any other candidate (extra wording is never accepted as a regex prefix);
  * QUALIFIER for a first / short / long / changed-year sentence.
Owner is one of the exact designations "của Ngân hàng" (BANK), "của Tập đoàn" / "của Ngân hàng và các công ty con"
(GROUP), absent (UNKNOWN) or anything else (OTHER: e.g. "của Ngân hàng Nhà nước", "của công ty con của Ngân hàng").

``resolve_annual_policy_v1(assertions, binding)`` is CALENDAR_YEAR only when there is at least one DEFINITION, no
UNSUPPORTED_WORDING / QUALIFIER candidate anywhere in the document, every DEFINITION is 01-01..12-31 with no printed
year, and every owner is the designation of the document's authenticated scope (SEPARATE -> BANK, CONSOLIDATED ->
GROUP). ``verify_annual_policy_v1(policy, binding)`` re-derives every assertion from its stored raw sentence and its
binding before any use: a status tag alone, a tampered field or another document's policy never grants.
"""

from __future__ import annotations

import re
from typing import Any

from bctc_ai.primary_statements.text_v1 import fold_vietnamese
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

CALENDAR_YEAR = "CALENDAR_YEAR"
_SUBJECT = r"(?:nam tai chinh|ky ke toan nam|nien do ke toan|nam ke toan)"
_DAY_MONTH = r"(?:ngay )?(\d{1,2})(?: thang |/)(\d{1,2})(?: nam (\d{4})|/(\d{4}))?"
_DEFINITION = re.compile(
    r"(?P<subject>" + _SUBJECT + r")(?: (?P<owner>cua [^,]+?))? bat dau (?:tu|vao) " + _DAY_MONTH
    + r",? va ket thuc (?:(?:vao|tai) )?" + _DAY_MONTH + r"(?P<tail> hang nam)?")
_CANDIDATE = re.compile(_SUBJECT + r".*\bbat dau\b")
_QUALIFIER = re.compile(r"\b" + _SUBJECT + r" dau tien\b|\bthay doi " + _SUBJECT + r"|\bchuyen doi " + _SUBJECT
                        + r"|\b" + _SUBJECT + r"[^.;]*\b(?:ngan hon|dai hon)\b")
_OWNERS = {"cua ngan hang": "BANK", "cua tap doan": "GROUP", "cua ngan hang va cac cong ty con": "GROUP"}
_SCOPE_OWNER = {"SEPARATE": "BANK", "CONSOLIDATED": "GROUP"}
BINDING_KEYS = ("document_ordinal", "source_logical_name", "source_sha256", "scope")


def _sentences(narrative: str) -> list[str]:
    return [s for s in re.split(r"\n+|(?<=[.;])\s+", narrative) if s.strip()]


def classify_sentence_v1(sentence: str) -> dict[str, Any] | None:
    """The candidate classification of one raw sentence, or None when it is not a policy candidate."""

    folded = re.sub(r"\s+", " ", fold_vietnamese(sentence)).strip().rstrip(".;").strip()
    qualifier = bool(_QUALIFIER.search(folded))
    if not qualifier and not _CANDIDATE.search(folded):
        return None
    record: dict[str, Any] = {"folded": folded, "ascii_digits": not any(ch.isdigit() and not ch.isascii() for ch in sentence)}
    match = _DEFINITION.fullmatch(folded)
    if qualifier:
        record.update(kind="QUALIFIER")
    elif match is None or not record["ascii_digits"]:
        record.update(kind="UNSUPPORTED_WORDING")
    else:
        owner = (match.group("owner") or "").strip()
        record.update(kind="DEFINITION",
                      window={"start": f"{int(match.group(4)):02d}-{int(match.group(3)):02d}",
                              "end": f"{int(match.group(8)):02d}-{int(match.group(7)):02d}"},
                      printed_years=[y for y in (match.group(5), match.group(6), match.group(9), match.group(10)) if y],
                      owner=_OWNERS.get(owner, "UNKNOWN" if not owner else "OTHER"), owner_text=owner)
    return record


def policy_sentences_v1(narrative: str) -> list[str]:
    """The raw sentences of one narrative that are policy candidates or qualifiers (the frontier test)."""

    return [sentence for sentence in _sentences(narrative) if classify_sentence_v1(sentence) is not None]


def policy_assertions_v1(page_json: dict[str, Any], provenance: dict[str, Any]) -> list[dict[str, Any]]:
    """Every policy candidate sentence in the ORIGINAL page's section narratives, kept whole with its binding."""

    found = []
    for s, section in enumerate(page_json.get("sections") or []):
        narratives = section.get("narratives_exact") if type(section) is dict else None
        if type(narratives) is not list:
            continue
        for i, narrative in enumerate(narratives):
            if type(narrative) is not str:
                continue
            for sentence in _sentences(narrative):
                record = classify_sentence_v1(sentence)
                if record is not None:
                    found.append({**provenance, "pointer": f"/sections/{s}/narratives_exact/{i}", "section_index": s,
                                  "narrative_index": i, "narrative_exact": narrative, "sentence_exact": sentence,
                                  "section_sha256": canonical_json_sha256_v1(section), **record})
    return found


def resolve_annual_policy_v1(assertions: list[dict[str, Any]], binding: dict[str, Any]) -> dict[str, Any]:
    """CALENDAR_YEAR only for scope-matched, unqualified, year-free 01-01..12-31 definitions and no other candidate."""

    definitions = [a for a in assertions if a["kind"] == "DEFINITION"]
    reasons = []
    if not definitions:
        reasons.append("NO_PRINTED_ANNUAL_POLICY")
    if any(a["kind"] == "UNSUPPORTED_WORDING" for a in assertions):
        reasons.append("UNSUPPORTED_POLICY_WORDING")
    if any(a["kind"] == "QUALIFIER" for a in assertions):
        reasons.append("POLICY_QUALIFIED_FIRST_SHORT_LONG_OR_CHANGED_YEAR")
    if any(a["printed_years"] for a in definitions):
        reasons.append("POLICY_ABSOLUTE_INTERVAL_NOT_A_RECURRENCE")
    expected_owner = _SCOPE_OWNER.get(binding.get("scope"))
    if any(a["owner"] != expected_owner for a in definitions) or (definitions and expected_owner is None):
        reasons.append("POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY")
    windows = {(a["window"]["start"], a["window"]["end"]) for a in definitions}
    if len(windows) > 1:
        reasons.append("POLICY_WINDOWS_CONFLICT")
    elif windows and windows != {("01-01", "12-31")}:
        reasons.append("POLICY_NOT_A_CALENDAR_YEAR")
    return {"status": "UNRESOLVED" if reasons else CALENDAR_YEAR, "reasons": reasons,
            "binding": {k: binding.get(k) for k in BINDING_KEYS},
            "pointers": [{k: a.get(k) for k in ("page_json_version_id", "physical_page", "pointer")} for a in definitions],
            "assertions": assertions}


def verify_annual_policy_v1(policy: Any, binding: dict[str, Any]) -> tuple[bool, str]:
    """Re-derive the policy from its stored raw sentences and binding; never trust a status tag (Codex 0254)."""

    if type(policy) is not dict or type(policy.get("assertions")) is not list:
        return False, "POLICY_NOT_A_RECORD"
    expected = {k: binding.get(k) for k in BINDING_KEYS}
    if policy.get("binding") != expected:
        return False, "POLICY_BINDING_IS_ANOTHER_DOCUMENT_OR_SCOPE"
    for assertion in policy["assertions"]:
        if type(assertion) is not dict or any(assertion.get(k) != expected[k] for k in BINDING_KEYS if k != "scope") \
                or type(assertion.get("page_json_version_id")) is not str or type(assertion.get("pointer")) is not str \
                or type(assertion.get("sentence_exact")) is not str or type(assertion.get("narrative_exact")) is not str \
                or assertion["sentence_exact"] not in assertion["narrative_exact"] \
                or not re.fullmatch(r"[0-9a-f]{64}", str(assertion.get("section_sha256"))):
            return False, "POLICY_ASSERTION_SOURCE_BINDING_INVALID"
        derived = classify_sentence_v1(assertion["sentence_exact"])
        if derived is None or any(assertion.get(k) != v for k, v in derived.items()):
            return False, "POLICY_ASSERTION_DOES_NOT_REDERIVE_FROM_ITS_SENTENCE"
    recomputed = resolve_annual_policy_v1(policy["assertions"], binding)
    if recomputed["status"] != policy.get("status") or recomputed["reasons"] != policy.get("reasons"):
        return False, "POLICY_STATUS_DOES_NOT_REDERIVE"
    return recomputed["status"] == CALENDAR_YEAR, "VERIFIED" if recomputed["status"] == CALENDAR_YEAR else "DOCUMENT_ANNUAL_POLICY_UNRESOLVED"
