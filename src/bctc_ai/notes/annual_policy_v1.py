"""Document-owned annual accounting-period policy evidence (Codex 0250/0254/0258; prototype, never by amount).

A bank's notes print its accounting year once, in the accounting-policy narratives (LPB FULL69 p12
/sections/0/narratives_exact/5: "(c) Kỳ kế toán\\nKỳ kế toán năm của Ngân hàng bắt đầu từ ngày 1 tháng 1 và kết thúc
vào ngày 31 tháng 12. …"). A note lane headed exactly "Năm kết thúc ngày 31/12/2025" prints a YEAR grain and an end
but no start; with that printed recurring calendar-year policy the start is printed too: DURATION:YEAR:2025.

Capture (the only authority). ``PolicyCapture`` is an immutable record built by the collector from AUTHENTICATED
ORIGINAL pages: the document binding (ordinal, source name, source SHA-256, scope), the frontier (every selected page
of the document with its candidate count read from the stored narratives) and, for every page with candidates,
EVERY narrative of the page with its exact pointer, a hash over all of them, and the page's ORIGINAL BLOB SHA /
replay receipt. ``verify_annual_policy_v1`` re-derives the COMPLETE assertion axis from the captured raw narratives
(never from a caller-supplied status or assertion list), checks every page hash and that every frontier page with a
candidate is captured with exactly that many candidates, and grants only a CALENDAR_YEAR resolution.

Sentences split at ". " / "; " only; a physical line wrap is part of its sentence (a wrapped subject and start phrase
are one candidate). Only the finite generic heading line reviewed in LPB, an enumerator followed by exactly "Kỳ kế
toán" ("(c) Kỳ kế toán"), is set aside before the whole-sentence grammar (Codex 0260); any other heading (an
exception, an owner qualification, anything unknown) stays in the sentence and makes it UNSUPPORTED_WORDING.
A sentence is a CANDIDATE when its folded text names the accounting year (năm tài chính / kỳ kế toán năm / niên độ
kế toán / năm kế toán) with "bắt đầu", or a first / changed / shorter / longer accounting year (QUALIFIER). A
candidate whose raw text has a combining mark or a non-ASCII digit, or whose whole folded text is not the finite grammar, is UNSUPPORTED_WORDING; only a whole-sentence match is a DEFINITION
(printed years retained: an absolute interval is not a recurrence). Owners are the exact designations "của Ngân hàng"
(BANK) and "của Tập đoàn" / "của Ngân hàng và các công ty con" (GROUP); absent is UNKNOWN, anything else OTHER.
CALENDAR_YEAR needs at least one DEFINITION, no UNSUPPORTED_WORDING or QUALIFIER anywhere in the frontier, every
DEFINITION 01-01..12-31 without printed year, and every owner the designation of the authenticated scope
(SEPARATE -> BANK, CONSOLIDATED -> GROUP).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
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
_HEADING = re.compile(r"\(?[a-z0-9]{1,4}[.)] ?ky ke toan")
_OWNERS = {"cua ngan hang": "BANK", "cua tap doan": "GROUP", "cua ngan hang va cac cong ty con": "GROUP"}
_SCOPE_OWNER = {"SEPARATE": "BANK", "CONSOLIDATED": "GROUP"}


@dataclass(frozen=True)
class PolicyPage:
    page_json_version_id: str
    physical_page: int
    original_blob_sha256: str
    replay_receipt_id: str
    narratives: tuple[tuple[str, str], ...]   # (exact pointer, raw narrative) for EVERY narrative of the page
    narratives_sha256: str


@dataclass(frozen=True)
class PolicyCapture:
    binding: tuple[Any, ...]                  # (document_ordinal, source_logical_name, source_sha256, scope)
    frontier: tuple[tuple[str, int], ...]     # every selected page of the document: (VID, stored candidate count)
    pages: tuple[PolicyPage, ...]             # every frontier page with candidates, from its ORIGINAL object


def raw_marks_ok_v1(raw: str) -> bool:
    """The kernel's raw guard: no combining mark after NFC and only ASCII decimal digits (checked before folding)."""

    text = unicodedata.normalize("NFC", raw)
    return not any(unicodedata.category(c) == "Mn" for c in text) and all(
        c in "0123456789" for c in text if unicodedata.category(c) == "Nd")


def _folded(text: str) -> str:
    return fold_vietnamese(text).rstrip(".;").strip()


def classify_sentence_v1(sentence: str) -> dict[str, Any] | None:
    """The candidate classification of one raw sentence (physical wraps included), or None when not a candidate."""

    whole = _folded(sentence)
    qualifier = bool(_QUALIFIER.search(whole))
    if not qualifier and not _CANDIDATE.search(whole):
        return None
    lines = [line for line in sentence.split("\n") if line.strip()]
    body = sentence
    if len(lines) > 1:
        head = _folded(lines[0])
        if _HEADING.fullmatch(head):
            body = "\n".join(lines[1:])
    folded = _folded(body)
    record: dict[str, Any] = {"folded": folded, "raw_ok": raw_marks_ok_v1(body)}
    match = _DEFINITION.fullmatch(folded)
    if qualifier:
        record.update(kind="QUALIFIER")
    elif match is None or not record["raw_ok"]:
        record.update(kind="UNSUPPORTED_WORDING")
    else:
        owner = (match.group("owner") or "").strip()
        record.update(kind="DEFINITION",
                      window={"start": f"{int(match.group(4)):02d}-{int(match.group(3)):02d}",
                              "end": f"{int(match.group(8)):02d}-{int(match.group(7)):02d}"},
                      printed_years=[y for y in (match.group(5), match.group(6), match.group(9), match.group(10)) if y],
                      owner=_OWNERS.get(owner, "UNKNOWN" if not owner else "OTHER"), owner_text=owner)
    return record


def _sentences(narrative: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;])\s+", narrative) if s.strip()]


def policy_sentences_v1(narrative: str) -> list[str]:
    """The raw sentences of one narrative that are policy candidates or qualifiers (the frontier test)."""

    return [sentence for sentence in _sentences(narrative) if classify_sentence_v1(sentence) is not None]


def page_narratives_v1(page_json: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Every string narrative of an ORIGINAL page with its exact pointer, in page order."""

    found = []
    for s, section in enumerate(page_json.get("sections") or []):
        narratives = section.get("narratives_exact") if type(section) is dict else None
        for i, narrative in enumerate(narratives if type(narratives) is list else []):
            if type(narrative) is str:
                found.append((f"/sections/{s}/narratives_exact/{i}", narrative))
    return tuple(found)


def policy_page_v1(page_json: dict[str, Any], *, page_json_version_id: str, physical_page: int,
                   original_blob_sha256: str, replay_receipt_id: str) -> PolicyPage:
    narratives = page_narratives_v1(page_json)
    return PolicyPage(page_json_version_id, physical_page, original_blob_sha256, replay_receipt_id, narratives,
                      canonical_json_sha256_v1([list(n) for n in narratives]))


def assertions_v1(capture: PolicyCapture) -> list[dict[str, Any]]:
    """The COMPLETE assertion axis re-derived from every captured raw narrative."""

    found = []
    for page in capture.pages:
        for pointer, narrative in page.narratives:
            for sentence in _sentences(narrative):
                record = classify_sentence_v1(sentence)
                if record is not None:
                    found.append({"page_json_version_id": page.page_json_version_id, "physical_page": page.physical_page,
                                  "pointer": pointer, "sentence_exact": sentence, **record})
    return found


def resolve_annual_policy_v1(assertions: list[dict[str, Any]], scope: str | None) -> dict[str, Any]:
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
    expected_owner = _SCOPE_OWNER.get(scope)
    if definitions and (expected_owner is None or any(a["owner"] != expected_owner for a in definitions)):
        reasons.append("POLICY_OWNER_NOT_THE_DOCUMENT_SCOPE_ENTITY")
    windows = {(a["window"]["start"], a["window"]["end"]) for a in definitions}
    if len(windows) > 1:
        reasons.append("POLICY_WINDOWS_CONFLICT")
    elif windows and windows != {("01-01", "12-31")}:
        reasons.append("POLICY_NOT_A_CALENDAR_YEAR")
    return {"status": "UNRESOLVED" if reasons else CALENDAR_YEAR, "reasons": reasons,
            "pointers": [{k: a[k] for k in ("page_json_version_id", "physical_page", "pointer")} for a in definitions],
            "assertions": assertions}


def verify_annual_policy_v1(capture: Any, binding: tuple[Any, ...]) -> tuple[bool, str, dict[str, Any] | None]:
    """(granted, why, resolution) re-derived from the immutable capture alone (Codex 0258/0261).

    Scope: this checks the CONSISTENCY of a capture inside the authenticated collector -> runner -> kernel path
    (``NotesSource.annual_policies_v1`` builds it from loader-authenticated ORIGINAL pages and ``run_v1`` hands it
    straight to the kernel; no capture is ever reloaded or deserialized). It does not independently authenticate an
    object constructed elsewhere: source binding and the complete narrative / frontier checks are what it enforces.
    """

    if type(capture) is not PolicyCapture or any(type(page) is not PolicyPage for page in capture.pages):
        return False, "POLICY_NOT_A_CAPTURE", None
    if capture.binding != tuple(binding):
        return False, "POLICY_BINDING_IS_ANOTHER_DOCUMENT_OR_SCOPE", None
    frontier = dict(capture.frontier)
    if len(frontier) != len(capture.frontier) or len({p.page_json_version_id for p in capture.pages}) != len(capture.pages):
        return False, "POLICY_FRONTIER_OR_PAGES_REPEATED", None
    for page in capture.pages:
        if canonical_json_sha256_v1([list(n) for n in page.narratives]) != page.narratives_sha256:
            return False, "POLICY_PAGE_NARRATIVES_HASH_MISMATCH", None
        if not re.fullmatch(r"[0-9a-f]{64}", str(page.original_blob_sha256)) or page.page_json_version_id not in frontier:
            return False, "POLICY_PAGE_NOT_BOUND_TO_FRONTIER", None
    counts = {p.page_json_version_id: sum(len(policy_sentences_v1(n)) for _ptr, n in p.narratives) for p in capture.pages}
    for version_id, count in frontier.items():
        if counts.get(version_id, 0) != count:
            return False, "POLICY_FRONTIER_CANDIDATES_NOT_CAPTURED", None
    resolution = resolve_annual_policy_v1(assertions_v1(capture), capture.binding[3])
    granted = resolution["status"] == CALENDAR_YEAR
    return granted, "VERIFIED" if granted else "DOCUMENT_ANNUAL_POLICY_UNRESOLVED", resolution
