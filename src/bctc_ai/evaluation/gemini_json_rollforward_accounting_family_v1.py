"""Generic two-period accounting roll-forward over selected Gemini JSON.

The primitive is deliberately layout-neutral.  It normalizes three equivalent
presentations into one ``period -> lane -> movement`` graph:

* one table containing two ordered period blocks;
* two period tables whose columns are accounting lanes; and
* two lane tables whose columns are periods.

Only exact Gemini JSON strings, one content-addressed same-document region
receipt, and declarative specifications are consumed.  There is no PDF
geometry, OCR fallback, bank/file/page route, or numeric backsolve across
unrelated rows.  A blank is an unknown, not zero.  A one-blank full-rank lane
solution may corroborate equation closure, but it is never emitted as a schema
mapping; two blanks always remain unresolved and identify a bounded row/table
repair frontier.  Both periods must close their equations and every comparative
closing endpoint must equal the current opening endpoint in the same lane and
unit.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1"
EVALUATION_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1"
LAYOUT_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_LAYOUT_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_ROLLFORWARD_SCHEMA_BINDING_SPEC_V1"
QUERY_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_REGION_QUERY_RECEIPT_V1"
QUERY_RECEIPT_AUTHENTICATION_KIND = (
    "CONTENT_ADDRESSED_EXACT_DOCUMENT_SOURCE_VERSION_ORDERED_REGION_BINDING"
)
SOURCE_REPAIR_OVERLAY_FORMAT_VERSION = (
    "GEMINI_JSON_ROLLFORWARD_AUTHENTICATED_SOURCE_REPAIR_OVERLAY_V1"
)
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_WITH_OPTIONAL_EXTERNALLY_PINNED_CONTENT_ADDRESSED_"
    "SOURCE_IMAGE_ACCOUNTING_DASH_REPAIR_ONLY_DOCUMENT_SOURCE_VERSION_"
    "ORDERED_REGION_RECEIPT_DECLARATIVE_OWNER_EXPLICIT_DIRECTIONAL_CONTINUATION_"
    "FULL_SECTION_TABLE_ROW_RESET_POPULATION_TWO_PERIOD_LANE_MOVEMENT_TRANSPOSE_"
    "ENDPOINT_CONTINUITY_EXACT_"
    "SIGNED_ROLLFORWARD_SOURCE_OBSERVED_SCHEMA_MAPPING_EQUATION_CORROBORATION_ONLY_NO_"
    "GEOMETRY_PPOCR_VIETOCR_BANK_FILE_PAGE_NOTE_ROUTING_MULTI_UNKNOWN_ZERO_"
    "COERCION_OR_EXPORT_AUTHORITY_CANONICAL_SQLITE_SELECTED_QUERY_AND_CANDIDATE_"
    "REPLAY_REQUIRED_FOR_PERSISTENCE"
)

_ORIENTATIONS = {
    "LANE_TABLES_PERIOD_COLUMNS",
    "PERIOD_TABLES_LANE_COLUMNS",
    "STACKED_PERIOD_BLOCKS",
}
_MOVEMENT_KINDS = {
    "CLOSING",
    "DECREASE",
    "FOREIGN_EXCHANGE",
    "OPENING",
    "OTHER",
    "PROVISION_OR_REVERSAL",
    "USE",
}
_DATE_DMY = re.compile(
    r"(?<!\d)([0-3]?\d)(?:[./-]|\s+(?:thang\s+)?)"
    r"([01]?\d)(?:[./-]|\s+(?:nam\s+)?)((?:19|20)\d{2})(?!\d)"
)
_DATE_WORDS = re.compile(
    r"(?:tai\s+)?(?:ngay\s+)?([0-3]?\d)\s+thang\s+([01]?\d)\s+nam\s+"
    r"((?:19|20)\d{2})"
)
_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_QUARTER_YEAR = re.compile(
    r"\b(?:quy\s*(?P<vn>[1-4]|iv|iii|ii|i)|q\s*(?P<q>[1-4])|"
    r"(?P<en>first|second|third|fourth)\s+quarter)"
    r"(?:\s+(?:nam|of|in))?\s+(?P<year>(?:19|20)\d{2})\b"
)
_CUMULATIVE_MONTH_YEAR = re.compile(
    r"\b(?P<months>3|6|9|ba|sau|chin)\s+thang\s+dau\s+nam\s+"
    r"(?P<year>(?:19|20)\d{2})\b"
)
_DIGITS = re.compile(r"^\d+$")
_GROUPED = re.compile(r"^\d{1,3}(?:[., ]\d{3})+$")
_DASHES = {"-", "–", "—", "_"}
_SOURCE_OBSERVED_MAPPING_STATES = frozenset(
    {
        "AGGREGATED_EXACT_SOURCE_ROWS",
        "DASH_ZERO",
        "NORMALIZED_DIRECTIONAL_DEDUCTION",
        "RAW_SIGNED_INTEGER",
    }
)
_PAGE_JSON_VERSION_ID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_EXTRACTION_RUN_ID = re.compile(r"gfpstorev1:run:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_PAGE_ID = re.compile(r"gfpstorev1:page:[0-9a-f]{64}\Z")
_SOURCE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_REPAIR_ID = re.compile(r"gjfrasrv1:repair:[0-9a-f]{64}\Z")
_SOURCE_REPAIR_OVERLAY_ID = re.compile(r"gjfrasrv1:overlay:[0-9a-f]{64}\Z")
_CONTINUATION_NEGATION_TOKENS = frozenset(
    {
        "chang",
        "chua",
        "isn",
        "isnt",
        "khong",
        "neither",
        "never",
        "no",
        "nor",
        "not",
        "without",
    }
)


def _is_source_observed_mapping_cell_v1(value: Any) -> bool:
    """Return whether a role cell has exact source support for mapping output."""

    return (
        type(value) is dict
        and type(value.get("coefficient")) is int
        and type(value.get("source_text")) is str
        and value.get("state") in _SOURCE_OBSERVED_MAPPING_STATES
    )


_ENGLISH_CONTINUATION_DETERMINERS = frozenset({"a", "an", "the"})
_ENGLISH_CONTINUATION_MODIFIERS = frozenset({"directly", "immediately", "just"})
_ENGLISH_PREVIOUS_TOKENS = frozenset({"preceding", "previous", "prior"})
_ENGLISH_OUTGOING_PREPOSITIONS = frozenset({"on", "onto", "to"})
_ENGLISH_NEXT_TOKENS = frozenset({"following", "next", "subsequent"})
_CONTINUES_FROM_PREVIOUS = {"BOTH", "CONTINUES_FROM_PREVIOUS_PAGE"}
_CONTINUATION_KINDS = {
    "BOTH",
    "CONTINUES_FROM_PREVIOUS_PAGE",
    "CONTINUES_ON_NEXT_PAGE",
    "NONE",
    "UNKNOWN",
}
_CONTINUATION_FROM_PREVIOUS = "FROM_PREVIOUS_PAGE"
_CONTINUATION_TO_NEXT = "TO_NEXT_PAGE"
_CONTINUATION_NEGATED = "NEGATED"
_CONTINUATION_AMBIGUOUS = "AMBIGUOUS"
_CONTINUATION_CONFLICT = "CONFLICT"
_CONTINUATION_NONE = "NONE"


class GeminiJsonRollforwardAccountingFamilyV1Error(ValueError):
    """The roll-forward spec, source region, or exact arithmetic drifted."""


def _error(message: str) -> GeminiJsonRollforwardAccountingFamilyV1Error:
    return GeminiJsonRollforwardAccountingFamilyV1Error(message)


def _normalized(value: Any) -> str:
    if type(value) is not str:
        return ""
    # A small number of otherwise valid provider records contain the two
    # literal characters ``\\n`` where a visual line break occurred.  Treat
    # that transport spelling exactly like whitespace; it must not create a
    # new bank/file alias merely because a label wrapped in the PDF.
    value = re.sub(r"\\[nr]", " ", value)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", normalize_vietnamese_anchor_v1(value)).split())


def _normalized_aliases(values: Any, *, label: str) -> list[str]:
    if (
        type(values) is not list
        or not values
        or any(type(value) is not str or not value.strip() for value in values)
    ):
        raise _error(f"roll-forward {label} aliases are invalid")
    aliases = [_normalized(value) for value in values]
    if any(not value for value in aliases) or len(aliases) != len(set(aliases)):
        raise _error(f"roll-forward {label} aliases collide")
    return aliases


def _source_repair_bbox_v1(
    value: Any,
    *,
    pixel_width: int,
    pixel_height: int,
    label: str,
) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or not (0 <= value[0] < value[2] <= pixel_width)
        or not (0 <= value[1] < value[3] <= pixel_height)
    ):
        raise _error(f"roll-forward authenticated source-repair {label} is invalid")
    return list(value)


def _compile_authenticated_source_repair_overlay_v1(
    value: Any,
    *,
    family_id: str,
) -> dict[str, Any]:
    """Compile an externally pinned, content-addressed visual dash overlay.

    The overlay is intentionally narrower than a general OCR correction path:
    it may only replace an exact JSON null with one visibly observed accounting
    dash.  The selected JSON version is replayed through its extraction-run,
    page-image and immutable source identities, and every cell is bound to an
    exact table/row/column plus an RGB crop hash.  Reading the referenced image
    artifact remains the responsibility of the caller that pins the evaluation
    spec; candidate replay independently proves that no other source cell moved.
    """

    fields = {"family_id", "format_version", "overlay_id", "repairs"}
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != SOURCE_REPAIR_OVERLAY_FORMAT_VERSION
        or value.get("family_id") != family_id
        or type(value.get("repairs")) is not list
        or not value["repairs"]
    ):
        raise _error("roll-forward authenticated source-repair overlay is invalid")
    checked_repairs = []
    seen_versions: set[str] = set()
    repair_fields = {
        "base_page_json_sha256",
        "base_page_json_version_id",
        "cell_repairs",
        "effective_page_json_sha256",
        "extraction_run_id",
        "repair_id",
        "repair_reason",
        "source_binding",
        "stored_canonical_json_sha256",
        "table_ref",
        "visual_evidence",
    }
    source_fields = {
        "document_id",
        "image_sha256",
        "image_size_bytes",
        "media_type",
        "page_id",
        "physical_page",
        "pixel_height",
        "pixel_width",
        "render_dpi",
        "source_logical_name",
        "source_sha256",
        "source_size_bytes",
    }
    table_fields = {
        "base_table_sha256",
        "effective_table_sha256",
        "section_id",
        "table_id",
    }
    visual_fields = {
        "artifact_ref",
        "crop_bbox_pixels_xyxy",
        "crop_rgb_sha256",
        "evidence_kind",
    }
    artifact_fields = {"path", "sha256", "size_bytes"}
    cell_fields = {
        "after_exact",
        "before_exact",
        "cell_id",
        "column_header_path_exact",
        "crop_bbox_pixels_xyxy",
        "crop_rgb_sha256",
        "row_hierarchy_path_exact",
        "row_label_exact",
        "visual_state",
    }
    for raw in value["repairs"]:
        if type(raw) is not dict or set(raw) != repair_fields:
            raise _error("roll-forward authenticated source-repair fields drifted")
        repair = canonical_clone_v1(raw)
        source = repair["source_binding"]
        if type(source) is not dict or set(source) != source_fields:
            raise _error("roll-forward authenticated source-repair source binding drifted")
        if (
            type(source["source_logical_name"]) is not str
            or not source["source_logical_name"].strip()
            or type(source["source_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(source["source_sha256"]) is None
            or type(source["source_size_bytes"]) is not int
            or source["source_size_bytes"] <= 0
            or type(source["document_id"]) is not str
            or _DOCUMENT_ID.fullmatch(source["document_id"]) is None
            or type(source["physical_page"]) is not int
            or source["physical_page"] <= 0
            or type(source["image_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(source["image_sha256"]) is None
            or type(source["image_size_bytes"]) is not int
            or source["image_size_bytes"] <= 0
            or type(source["pixel_width"]) is not int
            or source["pixel_width"] <= 0
            or type(source["pixel_height"]) is not int
            or source["pixel_height"] <= 0
            or source["render_dpi"] not in {200, 300}
            or source["media_type"] != "image/png"
            or type(source["page_id"]) is not str
            or _PAGE_ID.fullmatch(source["page_id"]) is None
        ):
            raise _error("roll-forward authenticated source-repair source binding is invalid")
        document_material = {
            "source_logical_name": source["source_logical_name"],
            "source_sha256": source["source_sha256"],
            "source_size_bytes": source["source_size_bytes"],
        }
        expected_document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(
            document_material
        )
        page_material = {
            "document_id": expected_document_id,
            "physical_page": source["physical_page"],
            "image_sha256": source["image_sha256"],
            "image_size_bytes": source["image_size_bytes"],
            "pixel_width": source["pixel_width"],
            "pixel_height": source["pixel_height"],
            "render_dpi": source["render_dpi"],
            "media_type": source["media_type"],
        }
        expected_page_id = "gfpstorev1:page:" + canonical_json_sha256_v1(page_material)
        if source["document_id"] != expected_document_id or source["page_id"] != expected_page_id:
            raise _error("roll-forward authenticated source-repair source identity does not replay")
        if (
            type(repair["base_page_json_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(repair["base_page_json_sha256"]) is None
            or type(repair["effective_page_json_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(repair["effective_page_json_sha256"]) is None
            or type(repair["stored_canonical_json_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(repair["stored_canonical_json_sha256"]) is None
            or type(repair["extraction_run_id"]) is not str
            or _EXTRACTION_RUN_ID.fullmatch(repair["extraction_run_id"]) is None
            or type(repair["base_page_json_version_id"]) is not str
            or _PAGE_JSON_VERSION_ID.fullmatch(repair["base_page_json_version_id"]) is None
        ):
            raise _error("roll-forward authenticated source-repair page version is invalid")
        expected_version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
            {
                "canonical_json_sha256": repair["stored_canonical_json_sha256"],
                "extraction_run_id": repair["extraction_run_id"],
                "page_id": source["page_id"],
            }
        )
        if repair["base_page_json_version_id"] != expected_version_id:
            raise _error("roll-forward authenticated source-repair page version does not replay")
        if repair["base_page_json_version_id"] in seen_versions:
            raise _error("roll-forward authenticated source-repair page version is duplicated")
        seen_versions.add(repair["base_page_json_version_id"])

        table_ref = repair["table_ref"]
        if (
            type(table_ref) is not dict
            or set(table_ref) != table_fields
            or type(table_ref["section_id"]) is not str
            or re.fullmatch(r"s[1-9][0-9]*", table_ref["section_id"]) is None
            or type(table_ref["table_id"]) is not str
            or re.fullmatch(r"t[1-9][0-9]*", table_ref["table_id"]) is None
            or type(table_ref["base_table_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(table_ref["base_table_sha256"]) is None
            or type(table_ref["effective_table_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(table_ref["effective_table_sha256"]) is None
        ):
            raise _error("roll-forward authenticated source-repair table binding is invalid")
        visual = repair["visual_evidence"]
        if type(visual) is not dict or set(visual) != visual_fields:
            raise _error("roll-forward authenticated source-repair visual evidence drifted")
        artifact = visual["artifact_ref"]
        if (
            type(artifact) is not dict
            or set(artifact) != artifact_fields
            or type(artifact["path"]) is not str
            or not artifact["path"]
            or artifact["path"].startswith("/")
            or ".." in artifact["path"].split("/")
            or type(artifact["sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(artifact["sha256"]) is None
            or type(artifact["size_bytes"]) is not int
            or artifact["size_bytes"] <= 0
            or visual["evidence_kind"]
            != "AUTHENTICATED_MANUAL_VISUAL_ACCOUNTING_DASH_TRANSCRIPTION"
            or type(visual["crop_rgb_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(visual["crop_rgb_sha256"]) is None
        ):
            raise _error("roll-forward authenticated source-repair artifact reference is invalid")
        table_bbox = _source_repair_bbox_v1(
            visual["crop_bbox_pixels_xyxy"],
            pixel_width=source["pixel_width"],
            pixel_height=source["pixel_height"],
            label="table crop",
        )
        cells = repair["cell_repairs"]
        if type(cells) is not list or not cells:
            raise _error("roll-forward authenticated source-repair cell axis is empty")
        checked_cells = []
        seen_cells = set()
        for raw_cell in cells:
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("roll-forward authenticated source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell["cell_id"])
            if (
                match is None
                or cell["cell_id"] in seen_cells
                or cell["before_exact"] is not None
                or cell["after_exact"] not in _DASHES
                or cell["visual_state"] != "DASH"
                or type(cell["row_label_exact"]) is not str
                or not cell["row_label_exact"].strip()
                or type(cell["row_hierarchy_path_exact"]) is not list
                or not cell["row_hierarchy_path_exact"]
                or any(type(item) is not str or not item for item in cell["row_hierarchy_path_exact"])
                or type(cell["column_header_path_exact"]) is not list
                or not cell["column_header_path_exact"]
                or any(type(item) is not str or not item for item in cell["column_header_path_exact"])
                or type(cell["crop_rgb_sha256"]) is not str
                or _SOURCE_SHA256.fullmatch(cell["crop_rgb_sha256"]) is None
            ):
                raise _error("roll-forward authenticated source-repair cell is invalid")
            seen_cells.add(cell["cell_id"])
            cell_bbox = _source_repair_bbox_v1(
                cell["crop_bbox_pixels_xyxy"],
                pixel_width=source["pixel_width"],
                pixel_height=source["pixel_height"],
                label="cell crop",
            )
            if not (
                table_bbox[0] <= cell_bbox[0] < cell_bbox[2] <= table_bbox[2]
                and table_bbox[1] <= cell_bbox[1] < cell_bbox[3] <= table_bbox[3]
            ):
                raise _error("roll-forward authenticated source-repair cell leaves table crop")
            checked_cells.append(cell)
        checked_cells.sort(
            key=lambda item: tuple(
                int(part[1:]) for part in item["cell_id"].split(":")
            )
        )
        if cells != checked_cells:
            raise _error("roll-forward authenticated source-repair cell axis is unordered")
        if repair["repair_reason"] != "VISIBLE_ACCOUNTING_DASH_OMITTED_FROM_SELECTED_JSON":
            raise _error("roll-forward authenticated source-repair reason is invalid")
        material = {key: repair[key] for key in repair if key != "repair_id"}
        expected_repair_id = "gjfrasrv1:repair:" + canonical_json_sha256_v1(material)
        if (
            type(repair["repair_id"]) is not str
            or _SOURCE_REPAIR_ID.fullmatch(repair["repair_id"]) is None
            or repair["repair_id"] != expected_repair_id
        ):
            raise _error("roll-forward authenticated source-repair identity does not replay")
        checked_repairs.append(repair)
    checked_repairs.sort(
        key=lambda item: (
            item["source_binding"]["source_logical_name"],
            item["source_binding"]["physical_page"],
            int(item["table_ref"]["section_id"][1:]),
            int(item["table_ref"]["table_id"][1:]),
            item["repair_id"],
        )
    )
    if value["repairs"] != checked_repairs:
        raise _error("roll-forward authenticated source-repair axis is unordered")
    material = {
        "family_id": family_id,
        "format_version": SOURCE_REPAIR_OVERLAY_FORMAT_VERSION,
        "repairs": checked_repairs,
    }
    expected_overlay_id = "gjfrasrv1:overlay:" + canonical_json_sha256_v1(material)
    if (
        type(value["overlay_id"]) is not str
        or _SOURCE_REPAIR_OVERLAY_ID.fullmatch(value["overlay_id"]) is None
        or value["overlay_id"] != expected_overlay_id
    ):
        raise _error("roll-forward authenticated source-repair overlay identity does not replay")
    return {**material, "overlay_id": expected_overlay_id}


def _authenticated_source_repair_receipt_v1(
    *,
    overlay: Mapping[str, Any],
    repair: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "overlay_id": overlay["overlay_id"],
        "repair": canonical_clone_v1(repair),
        "rule": (
            "EXACT_CONTENT_ADDRESSED_SELECTED_PAGE_TABLE_CELL_AND_VISUAL_EVIDENCE_"
            "NULL_TO_VISIBLE_ACCOUNTING_DASH_ONLY"
        ),
        "status": "AUTHENTICATED_VISIBLE_ACCOUNTING_DASH_TRANSCRIBED",
    }


def _apply_authenticated_source_repair_overlay_v1(
    *,
    region_axis: Sequence[Mapping[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Apply only exact, pinned null-to-visible-dash source repairs.

    A repair is relevant only when its exact selected page/table locator occurs
    in the authenticated candidate region.  Every source identity, base object,
    row, column and post-repair object is replayed before the cloned page is
    exposed to classification.  Unrelated candidates retain their original
    page objects byte-for-byte.
    """

    overlay = compiled_specs.get("source_repair_overlay")
    if overlay is None:
        return dict(page_json_by_version), []
    if type(overlay) is not dict:
        raise _error("roll-forward compiled source-repair overlay is invalid")
    effective_pages = dict(page_json_by_version)
    receipts = []
    for repair in overlay["repairs"]:
        source = repair["source_binding"]
        table_ref = repair["table_ref"]
        matches = [
            locator
            for locator in region_axis
            if locator.get("page_json_version_id") == repair["base_page_json_version_id"]
            and locator.get("section_id") == table_ref["section_id"]
            and locator.get("table_id") == table_ref["table_id"]
        ]
        if not matches:
            continue
        if len(matches) != 1:
            raise _error("roll-forward authenticated source-repair locator is duplicated")
        locator = matches[0]
        if any(
            locator.get(field) != source[field]
            for field in (
                "document_id",
                "physical_page",
                "source_logical_name",
                "source_sha256",
            )
        ):
            raise _error("roll-forward authenticated source-repair region binding drifted")
        base_page = page_json_by_version.get(repair["base_page_json_version_id"])
        if type(base_page) is not dict:
            raise _error("roll-forward authenticated source-repair base page is absent")
        if canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]:
            raise _error("roll-forward authenticated source-repair base page drifted")
        _section, base_table = _source_table(
            base_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        if canonical_json_sha256_v1(base_table) != table_ref["base_table_sha256"]:
            raise _error("roll-forward authenticated source-repair base table drifted")
        effective_page = canonical_clone_v1(base_page)
        _effective_section, effective_table = _source_table(
            effective_page,
            section_id=table_ref["section_id"],
            table_id=table_ref["table_id"],
        )
        rows = effective_table.get("rows")
        columns = effective_table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("roll-forward authenticated source-repair table axes are invalid")
        for cell_repair in repair["cell_repairs"]:
            match = re.fullmatch(r"r([1-9][0-9]*):c([1-9][0-9]*)", cell_repair["cell_id"])
            if match is None:
                raise _error("roll-forward authenticated source-repair cell identity drifted")
            row_index = int(match.group(1)) - 1
            column_index = int(match.group(2)) - 1
            if not (0 <= row_index < len(rows) and 0 <= column_index < len(columns)):
                raise _error("roll-forward authenticated source-repair cell is out of bounds")
            row = rows[row_index]
            column = columns[column_index]
            values = row.get("values_exact") if isinstance(row, Mapping) else None
            if (
                type(values) is not list
                or len(values) != len(columns)
                or row.get("label_exact") != cell_repair["row_label_exact"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"),
                    cell_repair["row_hierarchy_path_exact"],
                )
                or not same_typed_json_v1(
                    column.get("header_path_exact"),
                    cell_repair["column_header_path_exact"],
                )
                or not same_typed_json_v1(values[column_index], cell_repair["before_exact"])
            ):
                raise _error("roll-forward authenticated source-repair cell binding drifted")
            values[column_index] = cell_repair["after_exact"]
        if canonical_json_sha256_v1(effective_table) != table_ref["effective_table_sha256"]:
            raise _error("roll-forward authenticated source-repair effective table drifted")
        if canonical_json_sha256_v1(effective_page) != repair["effective_page_json_sha256"]:
            raise _error("roll-forward authenticated source-repair effective page drifted")
        effective_pages[repair["base_page_json_version_id"]] = effective_page
        receipts.append(
            _authenticated_source_repair_receipt_v1(overlay=overlay, repair=repair)
        )
    return effective_pages, receipts


def _aliases_by_role(topology: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        child["role"]: sorted(
            {_normalized(alias) for matcher in child["matchers"] for alias in matcher["aliases"]}
        )
        for child in topology["children"]
    }


def _compile_layout(value: Any, *, family_id: str, topology_roles: set[str]) -> dict[str, Any]:
    fields = {
        "aggregate_population_aliases",
        "allowed_orientations",
        "family_id",
        "format_version",
        "lane_roles",
        "max_component_tables",
        "max_page_span",
        "minimum_required_lanes",
        "movement_roles",
        "period_movement_context_aliases",
        "population_policy",
        "unit_aliases",
        "unit_bindings",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != LAYOUT_FORMAT_VERSION
        or value["family_id"] != family_id
        or type(value["allowed_orientations"]) is not list
        or set(value["allowed_orientations"]) != _ORIENTATIONS
        or value["max_component_tables"] != 2
        or value["max_page_span"] != 1
        or value["minimum_required_lanes"] != 2
    ):
        raise _error("roll-forward layout identity is invalid")

    lane_roles = []
    lane_names: set[str] = set()
    for raw in value["lane_roles"]:
        if (
            type(raw) is not dict
            or set(raw) != {"aliases", "optional", "role"}
            or type(raw["role"]) is not str
            or raw["role"] not in topology_roles
            or raw["role"] in lane_names
            or type(raw["optional"]) is not bool
        ):
            raise _error("roll-forward lane declaration is invalid")
        lane_names.add(raw["role"])
        lane_roles.append(
            {
                **raw,
                "aliases": _normalized_aliases(raw["aliases"], label=raw["role"]),
            }
        )
    if len(lane_roles) < 2 or sum(not role["optional"] for role in lane_roles) != 2:
        raise _error("roll-forward requires exactly two non-optional lanes")

    movement_roles = []
    movement_names: set[str] = set()
    kinds: set[str] = set()
    for raw in value["movement_roles"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "allow_one_unknown_inference",
                "equation_coefficient",
                "kind",
                "required",
                "role",
            }
            or type(raw["role"]) is not str
            or raw["role"] not in topology_roles
            or raw["role"] in movement_names
            or raw["kind"] not in _MOVEMENT_KINDS
            or raw["kind"] in kinds
            or type(raw["required"]) is not bool
            or type(raw["allow_one_unknown_inference"]) is not bool
            or raw["equation_coefficient"] not in {-1, 1}
        ):
            raise _error("roll-forward movement declaration is invalid")
        movement_names.add(raw["role"])
        kinds.add(raw["kind"])
        movement_roles.append(canonical_clone_v1(raw))
    if not {"OPENING", "PROVISION_OR_REVERSAL", "CLOSING"} <= kinds:
        raise _error("roll-forward endpoint/provision movement roles are incomplete")
    required_kinds = {item["kind"] for item in movement_roles if item["required"]}
    if required_kinds != {"OPENING", "PROVISION_OR_REVERSAL", "CLOSING"}:
        raise _error("roll-forward required movement roles drifted")
    coefficient_by_kind = {item["kind"]: item["equation_coefficient"] for item in movement_roles}
    if coefficient_by_kind["OPENING"] != 1 or coefficient_by_kind["CLOSING"] != -1:
        raise _error("roll-forward endpoint coefficients drifted")

    population = value["population_policy"]
    if (
        type(population) is not dict
        or set(population)
        != {
            "hard_negative_aliases",
            "owner_aliases",
            "owner_page_radius",
            "reset_aliases",
        }
        or population["owner_page_radius"] != 2
    ):
        raise _error("roll-forward population policy is invalid")
    checked_population = {
        "hard_negative_aliases": _normalized_aliases(
            population["hard_negative_aliases"], label="hard-negative"
        ),
        "owner_aliases": _normalized_aliases(population["owner_aliases"], label="owner"),
        "owner_page_radius": 2,
        "reset_aliases": _normalized_aliases(population["reset_aliases"], label="reset"),
    }
    if type(value["unit_bindings"]) is not list or not value["unit_bindings"]:
        raise _error("roll-forward money-unit bindings are invalid")
    unit_bindings = []
    canonical_units: set[str] = set()
    for raw in value["unit_bindings"]:
        if (
            type(raw) is not dict
            or set(raw)
            != {
                "aliases",
                "canonical_unit",
                "currency",
                "document_consensus_eligible",
                "magnitude_power10",
            }
            or type(raw["canonical_unit"]) is not str
            or not raw["canonical_unit"]
            or raw["canonical_unit"] in canonical_units
            or raw["currency"] != "VND"
            or type(raw["document_consensus_eligible"]) is not bool
            or raw["magnitude_power10"] not in {0, 3, 6, 9}
            or raw["document_consensus_eligible"] != (raw["magnitude_power10"] > 0)
        ):
            raise _error("roll-forward money-unit binding is invalid")
        canonical_units.add(raw["canonical_unit"])
        unit_bindings.append(
            {
                **canonical_clone_v1(raw),
                "aliases": _normalized_aliases(
                    raw["aliases"], label=f"unit-{raw['canonical_unit']}"
                ),
            }
        )
    return {
        "aggregate_population_aliases": _normalized_aliases(
            value["aggregate_population_aliases"], label="aggregate-population"
        ),
        "allowed_orientations": list(value["allowed_orientations"]),
        "lane_roles": lane_roles,
        "max_component_tables": 2,
        "max_page_span": 1,
        "minimum_required_lanes": 2,
        "movement_roles": movement_roles,
        "period_movement_context_aliases": _normalized_aliases(
            value["period_movement_context_aliases"], label="period-movement-context"
        ),
        "population_policy": checked_population,
        "unit_aliases": _normalized_aliases(value["unit_aliases"], label="unit"),
        "unit_bindings": unit_bindings,
    }


def _compile_schema(
    value: Any,
    *,
    family_id: str,
    lane_roles: set[str],
    movement_roles: set[str],
) -> dict[str, Any]:
    fields = {
        "context_only_report_norm_ids",
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "mapping_bindings",
        "schema_period_role",
        "unknown_inference_policy",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != SCHEMA_FORMAT_VERSION
        or value["family_id"] != family_id
        or type(value["family_root_report_norm_id"]) is not int
        or value["family_root_report_norm_id"] <= 0
        or value["schema_period_role"] != "CURRENT_PERIOD"
        or value["unknown_inference_policy"] != "ONE_UNKNOWN_ONE_FULL_RANK_LANE_EQUATION_ONLY"
        or type(value["context_only_report_norm_ids"]) is not list
        or value["family_root_report_norm_id"] not in value["context_only_report_norm_ids"]
        or any(
            type(identity) is not int or identity <= 0
            for identity in value["context_only_report_norm_ids"]
        )
        or len(value["context_only_report_norm_ids"])
        != len(set(value["context_only_report_norm_ids"]))
    ):
        raise _error("roll-forward schema identity is invalid")
    bindings: dict[tuple[str, str], int] = {}
    identities = set(value["context_only_report_norm_ids"])
    for raw in value["mapping_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"lane_role", "movement_role", "report_norm_id"}
            or raw["lane_role"] not in lane_roles
            or raw["movement_role"] not in movement_roles
            or type(raw["report_norm_id"]) is not int
            or raw["report_norm_id"] <= 0
            or (raw["lane_role"], raw["movement_role"]) in bindings
            or raw["report_norm_id"] in identities
        ):
            raise _error("roll-forward schema binding is invalid or duplicate")
        bindings[(raw["lane_role"], raw["movement_role"])] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    return {
        "bindings": bindings,
        "context_only_report_norm_ids": list(value["context_only_report_norm_ids"]),
        "family_root_report_norm_id": value["family_root_report_norm_id"],
        "schema_period_role": "CURRENT_PERIOD",
        "unknown_inference_policy": value["unknown_inference_policy"],
    }


def compile_gemini_json_rollforward_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile one bank-blind lane/movement roll-forward contract."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("roll-forward topology spec is invalid") from exc
    evaluation_fields = {
        "closure_policy",
        "family_id",
        "format_version",
        "layout_spec",
        "period_semantics",
    }
    if (
        type(evaluation_spec) is not dict
        or frozenset(evaluation_spec)
        not in {frozenset(evaluation_fields), frozenset({*evaluation_fields, "authenticated_source_repair_overlay"})}
        or evaluation_spec["format_version"] != EVALUATION_FORMAT_VERSION
        or evaluation_spec["family_id"] != topology["family_id"]
        or evaluation_spec["closure_policy"] != "EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK"
        or evaluation_spec["period_semantics"] != "CURRENT_AND_COMPARATIVE_MOVEMENT"
    ):
        raise _error("roll-forward evaluation spec is invalid")
    topology_roles = {topology["parent"]["role"], *(c["role"] for c in topology["children"])}
    layout = _compile_layout(
        evaluation_spec["layout_spec"],
        family_id=topology["family_id"],
        topology_roles=topology_roles,
    )
    schema = _compile_schema(
        schema_binding_spec,
        family_id=topology["family_id"],
        lane_roles={item["role"] for item in layout["lane_roles"]},
        movement_roles={item["role"] for item in layout["movement_roles"]},
    )
    source_repair_overlay = (
        _compile_authenticated_source_repair_overlay_v1(
            evaluation_spec["authenticated_source_repair_overlay"],
            family_id=topology["family_id"],
        )
        if "authenticated_source_repair_overlay" in evaluation_spec
        else None
    )
    aliases_by_role = _aliases_by_role(topology)
    return {
        "aliases_by_role": aliases_by_role,
        "anchor_alias_groups": [
            [
                aliases_by_role[
                    next(item["role"] for item in layout["movement_roles"] if item["kind"] == kind)
                ]
                for kind in ("OPENING", "PROVISION_OR_REVERSAL", "CLOSING")
            ]
        ],
        "claim_boundary": CLAIM_BOUNDARY,
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "layout": layout,
        "query_anchor_alias_groups": [
            [
                aliases_by_role[
                    next(item["role"] for item in layout["movement_roles"] if item["kind"] == kind)
                ]
                for kind in ("OPENING", "PROVISION_OR_REVERSAL", "CLOSING")
            ]
        ],
        "query_parent_aliases": canonical_clone_v1(topology_spec["parent"]["aliases"]),
        "rollforward_projection_policy": canonical_clone_v1(layout),
        "schema": schema,
        "source_repair_overlay": source_repair_overlay,
        "topology": topology,
    }


def _date_tokens(value: Any) -> list[tuple[date, str]]:
    folded = _normalized(value)
    if not folded:
        return []
    matches = [*_DATE_DMY.finditer(folded), *_DATE_WORDS.finditer(folded)]
    result = []
    for match in sorted(matches, key=lambda item: item.start()):
        try:
            token = (
                date(int(match.group(3)), int(match.group(2)), int(match.group(1))),
                match.group(0),
            )
        except ValueError:
            continue
        if token not in result:
            result.append(token)
    if result:
        return result
    years = set(_YEAR.findall(folded))
    if len(years) == 1:
        year = int(next(iter(years)))
        return [(date(year, 12, 31), str(year))]
    return []


def _date_token(value: Any) -> tuple[date, str] | None:
    tokens = _date_tokens(value)
    return tokens[-1] if tokens else None


def _full_date_token_spans_v1(value: Any) -> list[tuple[date, str, int, int]]:
    """Return non-overlapping exact full-date tokens in visual source order."""

    folded = _normalized(value)
    if not folded:
        return []
    candidates = []
    for pattern in (_DATE_WORDS, _DATE_DMY):
        for match in pattern.finditer(folded):
            try:
                parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                continue
            candidates.append((parsed, match.group(0), match.start(), match.end()))
    # ``ngay 31 thang 12 nam 2025`` is recognized by both date grammars.
    # Prefer the widest match and retain genuinely repeated dates at distinct
    # source positions.
    selected: list[tuple[date, str, int, int]] = []
    for item in sorted(candidates, key=lambda record: (record[2], -(record[3] - record[2]))):
        if any(not (item[3] <= other[2] or item[2] >= other[3]) for other in selected):
            continue
        selected.append(item)
    return sorted(selected, key=lambda record: record[2])


def _movement_period_end_token_v1(
    value: Any,
) -> tuple[tuple[date, str], str] | None:
    """Resolve only an exact source-visible reporting-period end grammar.

    A range binds to its explicit end date; quarter and cumulative-month
    labels bind to their conventional calendar reporting end.  A bare year is
    returned only as a fiscal-close candidate and still requires the separate
    authenticated document fiscal-close receipt at its call site.
    """

    folded = _normalized(value)
    if not folded:
        return None
    full_dates = _full_date_token_spans_v1(value)
    unique_full_dates = {item[0] for item in full_dates}
    if len(unique_full_dates) == 1:
        selected = full_dates[-1]
        return (selected[0], selected[1]), "EXACT_FULL_DATE"
    if len(full_dates) == 2 and len(unique_full_dates) == 2:
        first, last = full_dates
        prefix = folded[: first[2]]
        between = folded[first[3] : last[2]]
        exact_range_connectors = bool(
            re.search(r"\b(?:tu|from)\b", prefix)
            and re.search(r"\b(?:den|to|through)\b", between)
        )
        if exact_range_connectors and first[0] < last[0]:
            return (last[0], last[1]), "EXACT_DATE_RANGE_END_GRAMMAR"
        return None
    if full_dates:
        return None

    quarter_matches = list(_QUARTER_YEAR.finditer(folded))
    if len(quarter_matches) == 1:
        match = quarter_matches[0]
        quarter_token = match.group("vn") or match.group("q") or match.group("en")
        quarter = {
            "i": 1,
            "ii": 2,
            "iii": 3,
            "iv": 4,
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
        }.get(quarter_token, int(quarter_token) if quarter_token.isdigit() else 0)
        period_end = date(int(match.group("year")), quarter * 3, 31 if quarter in {1, 4} else 30)
        return (period_end, match.group(0)), "EXACT_QUARTER_END_GRAMMAR"

    month_matches = list(_CUMULATIVE_MONTH_YEAR.finditer(folded))
    if len(month_matches) == 1:
        match = month_matches[0]
        months = {"ba": 3, "sau": 6, "chin": 9}.get(
            match.group("months"), int(match.group("months")) if match.group("months").isdigit() else 0
        )
        period_end = date(int(match.group("year")), months, 31 if months == 3 else 30)
        return (period_end, match.group(0)), "EXACT_CUMULATIVE_MONTH_END_GRAMMAR"

    years = set(_YEAR.findall(folded))
    if len(years) == 1:
        year = int(next(iter(years)))
        return (date(year, 12, 31), str(year)), "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
    return None


def _money(value: Any) -> dict[str, Any]:
    if value is None:
        return {"coefficient": None, "source_text": None, "state": "UNKNOWN_BLANK"}
    if type(value) is not str or not value.strip():
        raise _error("roll-forward money cell is not one exact string/null")
    source = value
    token = value.strip()
    if all(character in _DASHES for character in token):
        return {"coefficient": 0, "source_text": source, "state": "DASH_ZERO"}
    negative = token.startswith("(") and token.endswith(")")
    body = token[1:-1].strip() if negative else token
    if body.startswith("-"):
        if negative:
            raise _error("roll-forward money sign is contradictory")
        negative = True
        body = body[1:].strip()
    if not (_DIGITS.fullmatch(body) or _GROUPED.fullmatch(body)):
        raise _error("roll-forward money grouping is invalid")
    coefficient = int(body.replace(".", "").replace(",", "").replace(" ", ""))
    return {
        "coefficient": -coefficient if negative else coefficient,
        "source_text": source,
        "state": "RAW_SIGNED_INTEGER",
    }


def solve_one_unknown_rollforward_lane_v1(
    cells_by_role: Mapping[str, Mapping[str, Any]],
    *,
    movement_specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Solve or corroborate one exact scalar lane equation.

    Roles absent from ``cells_by_role`` are not printed movement rows and do
    not enter the equation.  A present null cell is one unknown.  This
    distinction is what prevents two omitted values from silently becoming
    two zeros.
    """

    specs = {item["role"]: item for item in movement_specs}
    if not cells_by_role or any(role not in specs for role in cells_by_role):
        raise _error("roll-forward lane contains an undeclared movement role")
    unknown = [
        role
        for role, cell in cells_by_role.items()
        if cell.get("state") == "UNKNOWN_BLANK" and cell.get("coefficient") is None
    ]
    known_sum = sum(
        int(cell["coefficient"]) * int(specs[role]["equation_coefficient"])
        for role, cell in cells_by_role.items()
        if role not in unknown
    )
    if not unknown:
        return {
            "equation_rank": 1,
            "inferred_role": None,
            "residual": known_sum,
            "status": (
                "EXACT"
                if known_sum == 0
                else "EXACT_DISPLAY_UNIT_ROUNDING"
                if abs(known_sum) == 1
                else "MISMATCH"
            ),
        }
    if len(unknown) != 1:
        return {
            "equation_rank": 1,
            "inferred_role": None,
            "residual": None,
            "status": "RANK_DEFICIENT_MULTIPLE_UNKNOWNS",
            "unknown_roles": sorted(unknown),
        }
    role = unknown[0]
    spec = specs[role]
    if not spec["allow_one_unknown_inference"]:
        return {
            "equation_rank": 1,
            "inferred_role": None,
            "residual": None,
            "status": "UNKNOWN_ROLE_INFERENCE_FORBIDDEN",
            "unknown_roles": [role],
        }
    coefficient = int(spec["equation_coefficient"])
    inferred = -known_sum * coefficient
    return {
        "equation_rank": 1,
        "inferred_coefficient": inferred,
        "inferred_role": role,
        "residual": 0,
        "status": "EXACT_ONE_UNKNOWN_INFERRED",
        "unknown_roles": [role],
    }


def _rebuild_rollforward_equations_from_role_vectors_v1(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Replay the persisted equation axis from its canonical solved role vectors."""

    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    by_lane: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for vector in role_vectors:
        key = (vector.get("period_role"), vector.get("lane_role"))
        movement_role = vector.get("movement_role")
        if (
            key[0] not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
            or type(key[1]) is not str
            or type(movement_role) is not str
            or type(vector.get("cell")) is not dict
            or movement_role in by_lane.setdefault(key, {})
        ):
            raise _error("roll-forward role-vector equation axis is invalid")
        by_lane[key][movement_role] = canonical_clone_v1(vector["cell"])
    equations = []
    for period_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
        for lane_role in sorted(lane for period, lane in by_lane if period == period_role):
            cells = by_lane[(period_role, lane_role)]
            if not required_movements <= set(cells):
                continue
            inferred_roles = [
                role
                for role, cell in cells.items()
                if cell.get("state") == "INFERRED_ONE_UNKNOWN_FULL_RANK"
            ]
            if len(inferred_roles) > 1:
                raise _error("roll-forward role-vector inference axis is invalid")
            solver_cells = canonical_clone_v1(cells)
            if inferred_roles:
                inferred_role = inferred_roles[0]
                solver_cells[inferred_role] = {
                    **solver_cells[inferred_role],
                    "coefficient": None,
                    "state": "UNKNOWN_BLANK",
                }
            solution = solve_one_unknown_rollforward_lane_v1(
                solver_cells,
                movement_specs=movement_specs,
            )
            if inferred_roles and (
                solution["status"] != "EXACT_ONE_UNKNOWN_INFERRED"
                or solution["inferred_role"] != inferred_roles[0]
                or solution["inferred_coefficient"] != cells[inferred_roles[0]].get("coefficient")
            ):
                raise _error("roll-forward inferred role vector does not replay")
            equations.append(
                {
                    "equation_rank": 1,
                    "inferred_coefficient": solution.get("inferred_coefficient"),
                    "inferred_role": solution.get("inferred_role"),
                    "lane_role": lane_role,
                    "period_role": period_role,
                    "role_coefficients": [
                        {
                            "coefficient": cells[item["role"]]["coefficient"],
                            "equation_coefficient": item["equation_coefficient"],
                            "role": item["role"],
                            "state": cells[item["role"]]["state"],
                        }
                        for item in movement_specs
                        if item["role"] in cells
                    ],
                    "status": solution["status"],
                }
            )
    return equations


def _rebuild_rollforward_potential_mappings_from_role_vectors_v1(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Replay the exact schema-bound current-period mapping projection."""

    bindings = compiled_specs["schema"]["bindings"]
    mappings = []
    for vector in role_vectors:
        if vector.get("period_role") != "CURRENT_PERIOD":
            continue
        report_norm_id = bindings.get((vector.get("lane_role"), vector.get("movement_role")))
        cell = vector.get("cell")
        if report_norm_id is None or not _is_source_observed_mapping_cell_v1(cell):
            continue
        material = {
            **canonical_clone_v1(vector),
            "mapping_kind": (
                "DECLARATIVE_EXACT_ADDITIVE_SOURCE_ROWS_ROLLFORWARD_PROPOSAL"
                if cell.get("state") == "AGGREGATED_EXACT_SOURCE_ROWS"
                else "DECLARATIVE_EXACT_DIRECTIONAL_DEDUCTION_ROLLFORWARD_PROPOSAL"
                if cell.get("state") == "NORMALIZED_DIRECTIONAL_DEDUCTION"
                else "DECLARATIVE_VISIBLE_ROLLFORWARD_CELL_PROPOSAL"
            ),
            "report_norm_id": report_norm_id,
        }
        mappings.append(
            {
                **material,
                "item_mapping_id": "gjfrfmv1:item:" + canonical_json_sha256_v1(material),
            }
        )
    return mappings


def _node(identifier: str, *, prefix: str, values: list[Any]) -> Any:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error("roll-forward source node identity is invalid")
    suffix = identifier.removeprefix(prefix)
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error("roll-forward source node identity is invalid")
    index = int(suffix) - 1
    if not 0 <= index < len(values):
        raise _error("roll-forward source node identity is out of range")
    return values[index]


def _source_table(
    page_json: Mapping[str, Any], *, section_id: str, table_id: str
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("roll-forward page section axis is invalid")
    section = _node(section_id, prefix="s", values=sections)
    tables = section.get("tables") if isinstance(section, Mapping) else None
    if type(tables) is not list:
        raise _error("roll-forward section table axis is invalid")
    table = _node(table_id, prefix="t", values=tables)
    if not isinstance(table, Mapping):
        raise _error("roll-forward table is invalid")
    return section, table


def _matches_alias(value: Any, aliases: Sequence[str]) -> bool:
    folded = _normalized(value)
    if not folded:
        return False
    forms = {folded, re.sub(r"^(?:\d+|[ivxlcdm]+)\s+", "", folded)}
    return any(
        form == alias or form.startswith(alias + " ") or f" {alias} " in f" {form} "
        for form in forms
        for alias in aliases
    )


def _role_for_row(row: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> str | None:
    movement_roles = {item["role"] for item in compiled_specs["layout"]["movement_roles"]}
    folded = _normalized(row.get("label_exact"))
    forms = {folded, re.sub(r"^(?:\d+|[ivxlcdm]+)\s+", "", folded)} if folded else set()
    exact = {
        role
        for role in movement_roles
        if any(form == alias for form in forms for alias in compiled_specs["aliases_by_role"][role])
    }
    matched = exact or {
        role
        for role in movement_roles
        if _matches_alias(row.get("label_exact"), compiled_specs["aliases_by_role"][role])
    }
    if len(matched) > 1:
        raise _error("roll-forward row matches multiple movement roles")
    if matched:
        return next(iter(matched))
    period = _date_token(row.get("label_exact"))
    if period is None or not (
        folded.startswith("tai ngay ")
        or folded.startswith("tai ")
        or folded.startswith("ngay ")
        or "so du" in folded
    ):
        return None
    kind = "OPENING" if (period[0].month, period[0].day) == (1, 1) else "CLOSING"
    return next(
        item["role"] for item in compiled_specs["layout"]["movement_roles"] if item["kind"] == kind
    )


def _lane_for_surface(value: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    matched = {
        item["role"]
        for item in compiled_specs["layout"]["lane_roles"]
        if _matches_alias(value, compiled_specs["aliases_by_role"][item["role"]])
    }
    if len(matched) > 1:
        raise _error("roll-forward surface matches multiple lane roles")
    return next(iter(matched)) if matched else None


def _lane_from_header(path: Any, *, compiled_specs: Mapping[str, Any]) -> str | None:
    if type(path) is not list or any(
        value is not None and type(value) is not str for value in path
    ):
        raise _error("roll-forward column header path is invalid")
    joined = " ".join(value for value in path if type(value) is str)
    if _matches_alias(
        joined,
        compiled_specs["layout"]["population_policy"]["hard_negative_aliases"],
    ):
        return None
    for value in reversed(path):
        if (role := _lane_for_surface(value, compiled_specs=compiled_specs)) is not None:
            return role
    return None


def _projected_lane_columns_v1(
    columns: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[str | None], dict[str, Any]]:
    """Select one declared aggregate population when lane columns repeat.

    Some schedules present geographic or branch sub-populations beside one
    aggregate block.  A repeated lane remains ambiguous unless exactly one
    candidate carries a declaratively named aggregate ancestor.  This does
    not merge, sum, or prefer columns by position.
    """

    lane_by_column = [
        _lane_from_header(column.get("header_path_exact"), compiled_specs=compiled_specs)
        for column in columns
    ]
    projected = list(lane_by_column)
    decisions = []
    unresolved = []
    aliases = compiled_specs["layout"]["aggregate_population_aliases"]

    def duplicate_source_cell_receipts(indexes: Sequence[int]) -> list[dict[str, Any]]:
        if rows is None:
            return []
        result = []
        for block_ordinal, block in enumerate(
            _row_blocks(list(rows), compiled_specs=compiled_specs),
            start=1,
        ):
            for entry in block:
                row_index = entry["row_index"]
                values = rows[row_index].get("values_exact")
                if type(values) is not list or len(values) != len(columns):
                    raise _error("roll-forward duplicate population row axis is invalid")
                result.append(
                    {
                        "block_ordinal": block_ordinal,
                        "candidate_cells": [_money(values[index]) for index in indexes],
                        "movement_role": entry["movement_role"],
                        "row_id": f"r{row_index + 1}",
                    }
                )
        return result

    for lane_role in sorted({role for role in lane_by_column if role is not None}):
        indexes = [index for index, role in enumerate(lane_by_column) if role == lane_role]
        if len(indexes) == 1:
            continue
        aggregate_matches_by_index = {
            index: [
                _normalized(surface)
                for surface in columns[index].get("header_path_exact", [])
                if _normalized(surface) in aliases
            ]
            for index in indexes
        }
        aggregate_indexes = [index for index in indexes if aggregate_matches_by_index[index]]
        if len(aggregate_indexes) != 1:
            unresolved.append(
                {
                    "aggregate_candidate_column_ordinals": [
                        index + 1 for index in aggregate_indexes
                    ],
                    "candidate_column_ordinals": [index + 1 for index in indexes],
                    "duplicate_source_cell_receipts": duplicate_source_cell_receipts(indexes),
                    "lane_role": lane_role,
                }
            )
            continue
        selected = aggregate_indexes[0]
        identities = aggregate_matches_by_index[selected]
        if len(set(identities)) != 1:
            unresolved.append(
                {
                    "aggregate_candidate_column_ordinals": [selected + 1],
                    "candidate_column_ordinals": [index + 1 for index in indexes],
                    "duplicate_source_cell_receipts": duplicate_source_cell_receipts(indexes),
                    "lane_role": lane_role,
                    "reason": "AGGREGATE_HEADER_IDENTITY_AMBIGUOUS",
                }
            )
            continue
        row_sum_receipts = []
        if rows is not None:
            for row_index, row in enumerate(rows):
                if _role_for_row(row, compiled_specs=compiled_specs) is None:
                    continue
                values = row.get("values_exact")
                if type(values) is not list or len(values) != len(columns):
                    raise _error("roll-forward aggregate population row axis is invalid")
                cells = [_money(values[index]) for index in indexes]
                if any(cell["coefficient"] is None for cell in cells):
                    row_sum_receipts.append(
                        {
                            "candidate_coefficients": [cell["coefficient"] for cell in cells],
                            "row_id": f"r{row_index + 1}",
                            "status": "UNKNOWN_SIBLING_OR_AGGREGATE_CELL",
                        }
                    )
                    continue
                selected_offset = indexes.index(selected)
                selected_coefficient = cells[selected_offset]["coefficient"]
                sibling_sum = sum(
                    cell["coefficient"]
                    for offset, cell in enumerate(cells)
                    if offset != selected_offset
                )
                row_sum_receipts.append(
                    {
                        "candidate_coefficients": [cell["coefficient"] for cell in cells],
                        "row_id": f"r{row_index + 1}",
                        "selected_coefficient": selected_coefficient,
                        "sibling_sum": sibling_sum,
                        "status": (
                            "EXACT_HORIZONTAL_AGGREGATE"
                            if selected_coefficient == sibling_sum
                            else "HORIZONTAL_AGGREGATE_MISMATCH"
                        ),
                    }
                )
        if rows is not None and (
            not any(item["status"] == "EXACT_HORIZONTAL_AGGREGATE" for item in row_sum_receipts)
            or any(item["status"] == "HORIZONTAL_AGGREGATE_MISMATCH" for item in row_sum_receipts)
        ):
            unresolved.append(
                {
                    "aggregate_candidate_column_ordinals": [selected + 1],
                    "candidate_column_ordinals": [index + 1 for index in indexes],
                    "duplicate_source_cell_receipts": duplicate_source_cell_receipts(indexes),
                    "lane_role": lane_role,
                    "reason": "AGGREGATE_ROW_SUM_NOT_EXACT",
                    "row_sum_receipts": row_sum_receipts,
                }
            )
            continue
        for index in indexes:
            if index != selected:
                projected[index] = None
        decisions.append(
            {
                "aggregate_header_path_exact": canonical_clone_v1(
                    columns[selected].get("header_path_exact")
                ),
                "aggregate_identity_normalized": identities[0],
                "candidate_column_ordinals": [index + 1 for index in indexes],
                "lane_role": lane_role,
                "row_sum_receipts": row_sum_receipts,
                "selected_column_ordinal": selected + 1,
            }
        )
    return projected, {
        "aggregate_population_aliases": list(aliases),
        "decisions": decisions,
        "raw_lane_roles_by_column": lane_by_column,
        "rule": (
            "REPEATED_LANE_REQUIRES_EXACTLY_ONE_DECLARED_AGGREGATE_ANCESTOR_"
            "OTHERWISE_REMAINS_AMBIGUOUS"
        ),
        "status": (
            "DUPLICATE_POPULATION_NOT_UNIQUELY_AGGREGATED"
            if unresolved
            else "UNIQUE_AGGREGATE_POPULATION_SELECTED"
            if decisions
            else "DIRECT_UNIQUE_LANE_COLUMNS"
        ),
        "unresolved_duplicate_lanes": unresolved,
    }


def _lane_from_table_context(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> str | None:
    return _lane_context_evidence(
        section,
        table,
        compiled_specs=compiled_specs,
    )["explicit_lane_role"]


def _lane_context_evidence(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Return candidate-local lane evidence without unioning nearby prose.

    A table title is the narrowest source, followed by the section title.  A
    single narrative role may bind directly.  Multiple narrative roles remain
    an ordered candidate axis for a later local one-to-one table assignment;
    they are never collapsed into an arbitrary set choice here.
    """

    narratives = section.get("narratives_exact", [])
    if type(narratives) is not list or any(
        value is not None and type(value) is not str for value in narratives
    ):
        raise _error("roll-forward section narrative axis is invalid")
    policy = compiled_specs["layout"]["population_policy"]
    structural_surfaces = [
        table.get("title_exact"),
        section.get("title_exact"),
        *narratives,
    ]
    hard_negative_visible = any(
        _matches_alias(surface, policy["hard_negative_aliases"])
        for surface in structural_surfaces
        if type(surface) is str
    )
    reset_visible = any(
        _matches_alias(surface, policy["reset_aliases"])
        for surface in narratives
        if type(surface) is str
    )
    title_role = _lane_for_surface(table.get("title_exact"), compiled_specs=compiled_specs)
    section_role = _lane_for_surface(section.get("title_exact"), compiled_specs=compiled_specs)
    narrative_evidence = [
        {"narrative_ordinal": ordinal, "role": role, "text_exact": value}
        for ordinal, value in enumerate(narratives, start=1)
        if type(value) is str
        and (role := _lane_for_surface(value, compiled_specs=compiled_specs)) is not None
    ]
    narrative_roles = [item["role"] for item in narrative_evidence]
    if len(narrative_roles) != len(set(narrative_roles)):
        raise _error("roll-forward narrative lane role repeats in one local section")
    explicit_role = title_role or section_role
    explicit_source = "TABLE_TITLE" if title_role is not None else "SECTION_TITLE"
    if title_role is not None and section_role is not None and title_role != section_role:
        raise _error("roll-forward table and section lane roles conflict")
    if explicit_role is None and len(narrative_roles) == 1:
        explicit_role = narrative_roles[0]
        explicit_source = "SINGLE_NARRATIVE"
    if hard_negative_visible:
        explicit_role = None
        explicit_source = None
    return {
        "explicit_lane_role": explicit_role,
        "explicit_source_kind": explicit_source if explicit_role is not None else None,
        "hard_negative_visible": hard_negative_visible,
        "narrative_lane_evidence": narrative_evidence,
        "narrative_lane_roles": narrative_roles,
        "reset_visible": reset_visible,
    }


def _sequence_positions(tokens: Sequence[str], sequence: Sequence[str]) -> list[int]:
    width = len(sequence)
    return [
        index
        for index in range(len(tokens) - width + 1)
        if tuple(tokens[index : index + width]) == tuple(sequence)
    ]


def _english_from_previous_page_grammar(tokens: Sequence[str]) -> bool:
    """Accept only bounded ``from`` + explicit prior-page token productions."""

    if not tokens or tokens[0] != "from":
        return False
    tail = list(tokens[1:8])
    if tail and tail[0] in _ENGLISH_CONTINUATION_DETERMINERS:
        tail.pop(0)
    if not tail:
        return False

    # adjective-first: ``from the immediately preceding page``
    adjective_first = list(tail)
    if adjective_first and adjective_first[0] in _ENGLISH_CONTINUATION_MODIFIERS:
        adjective_first.pop(0)
    if adjective_first and adjective_first[0] in _ENGLISH_PREVIOUS_TOKENS:
        adjective_first.pop(0)
        if adjective_first and adjective_first[0] in _ENGLISH_CONTINUATION_MODIFIERS:
            adjective_first.pop(0)
        if adjective_first and adjective_first[0] == "page":
            return True

    # noun-first: ``from the page immediately preceding this one``
    noun_first = list(tail)
    if not noun_first or noun_first.pop(0) != "page":
        return False
    if noun_first and noun_first[0] in _ENGLISH_CONTINUATION_MODIFIERS:
        noun_first.pop(0)
    if not noun_first or noun_first.pop(0) not in _ENGLISH_PREVIOUS_TOKENS:
        return False
    # The optional deictic tail is deliberately closed: an arbitrary noun such
    # as ``note`` or ``accounting period`` must not inherit the preceding-page
    # meaning merely because ``page`` and ``prior`` both appeared earlier.
    return tuple(noun_first) in {(), ("this", "one"), ("to", "this", "one")}


def _continuation_surface_direction(value: Any) -> str:
    """Parse one English/Vietnamese continuation marker fail-closed."""

    tokens = tuple(_normalized(value).split())
    if not tokens:
        return _CONTINUATION_NONE
    markers = [
        *(("ENGLISH", index) for index, token in enumerate(tokens) if token == "continued"),
        *(
            ("VIETNAMESE", index + 1)
            for sequence in (("con", "tiep"), ("tiep", "theo"), ("tiep", "tuc"))
            for index in _sequence_positions(tokens, sequence)
        ),
    ]
    if not markers:
        return _CONTINUATION_NONE
    if any(token in _CONTINUATION_NEGATION_TOKENS for token in tokens):
        return _CONTINUATION_NEGATED

    incoming = False
    outgoing = False
    for language, marker in markers:
        suffix = tokens[marker + 1 :]
        if language == "ENGLISH":
            incoming = incoming or _english_from_previous_page_grammar(suffix)
            outgoing = (
                outgoing
                or "overleaf" in suffix
                or any(
                    token in _ENGLISH_OUTGOING_PREPOSITIONS
                    and (
                        "page" in suffix[index + 1 : index + 5]
                        or any(
                            candidate in _ENGLISH_NEXT_TOKENS
                            for candidate in suffix[index + 1 : index + 4]
                        )
                    )
                    for index, token in enumerate(suffix)
                )
            )
            outgoing = outgoing or (
                "page" in suffix and any(token in _ENGLISH_NEXT_TOKENS for token in suffix)
            )
            continue

        page_positions = [index for index, token in enumerate(suffix) if token == "trang"]
        for page_index in page_positions:
            direction = suffix[page_index + 1 : page_index + 4]
            incoming = incoming or "truoc" in direction
            outgoing = outgoing or "sau" in direction
            outgoing = outgoing or (
                len(direction) >= 2 and direction[0] == "ke" and direction[1] == "tiep"
            )
            outgoing = outgoing or (
                len(direction) >= 2 and direction[0] == "tiep" and direction[1] == "theo"
            )
    if incoming and not outgoing:
        return _CONTINUATION_FROM_PREVIOUS
    if outgoing and not incoming:
        return _CONTINUATION_TO_NEXT
    if incoming and outgoing:
        return _CONTINUATION_CONFLICT
    return _CONTINUATION_AMBIGUOUS


def _explicit_continuation_evidence(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> list[dict[str, Any]]:
    continuation = table.get("continuation")
    if continuation not in _CONTINUATION_KINDS:
        raise _error("roll-forward table continuation kind is invalid")
    narratives = section.get("narratives_exact")
    if type(narratives) is not list:
        raise _error("roll-forward continuation narrative axis is invalid")
    surfaces = [
        ("TABLE_TITLE", table.get("title_exact")),
        ("SECTION_TITLE", section.get("title_exact")),
        *(("SECTION_NARRATIVE", value) for value in narratives),
    ]
    directional_surfaces = [
        {
            "direction": direction,
            "source_exact": value,
            "source_kind": source_kind,
        }
        for source_kind, value in surfaces
        if (direction := _continuation_surface_direction(value)) != _CONTINUATION_NONE
    ]
    # A forward-only marker belongs to the page that precedes a continuation;
    # it can never authenticate that this table continues from an owner above.
    if continuation == "CONTINUES_ON_NEXT_PAGE":
        return []
    contradictory = {
        _CONTINUATION_CONFLICT,
        _CONTINUATION_NEGATED,
        _CONTINUATION_TO_NEXT,
    }
    if continuation == "CONTINUES_FROM_PREVIOUS_PAGE" and any(
        item["direction"] in contradictory for item in directional_surfaces
    ):
        raise _error("roll-forward continuation directions conflict")
    if continuation == "BOTH" and any(
        item["direction"] in {_CONTINUATION_CONFLICT, _CONTINUATION_NEGATED}
        for item in directional_surfaces
    ):
        raise _error("roll-forward continuation directions conflict")
    evidence = (
        [
            {
                "source_exact": continuation,
                "source_kind": "TABLE_CONTINUATION_KIND",
            }
        ]
        if continuation in _CONTINUES_FROM_PREVIOUS
        else []
    )
    evidence.extend(
        {
            "source_exact": item["source_exact"],
            "source_kind": item["source_kind"],
        }
        for item in directional_surfaces
        if item["direction"] == _CONTINUATION_FROM_PREVIOUS
    )
    if continuation not in _CONTINUES_FROM_PREVIOUS and any(
        item["direction"] in contradictory for item in directional_surfaces
    ):
        return []
    return evidence


def _canonical_money_units_from_surface_v1(
    value: Any,
    *,
    compiled_specs: Mapping[str, Any],
    document_consensus_only: bool = False,
) -> set[str]:
    folded = _normalized(value)
    if not folded or "ty gia" in folded or "exchange rate" in folded:
        return set()
    matched = []
    for binding in compiled_specs["layout"]["unit_bindings"]:
        if document_consensus_only and not binding["document_consensus_eligible"]:
            continue
        alias_visible = False
        for alias in binding["aliases"]:
            normalized_alias = _normalized(alias)
            # Vietnamese ``đồng`` normalizes to the ordinary word ``dong``
            # (for example in ``hoạt động``).  A magnitude-qualified alias is
            # already unambiguous; the bare currency name is authority-bearing
            # only as a standalone/unit-labelled surface.
            if normalized_alias == "dong":
                alias_visible = bool(
                    folded == "dong"
                    or re.search(r"\b(?:don vi(?: tinh)?|unit|currency) dong\b", folded)
                )
            elif _matches_alias(value, [alias]):
                alias_visible = True
            if alias_visible:
                break
        if alias_visible:
            matched.append(binding)
    magnitude_matches = [item for item in matched if item["magnitude_power10"] > 0]
    selected = magnitude_matches or matched
    return {item["canonical_unit"] for item in selected}


def _bound_unit(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> str | None:
    table_units = _canonical_money_units_from_surface_v1(
        table.get("unit_exact"),
        compiled_specs=compiled_specs,
    )
    if len(table_units) > 1:
        return None
    money_column_units = []
    for column in table.get("columns", []):
        if column.get("value_kind") != "MONEY":
            continue
        column_units = {
            unit
            for surface in column.get("header_path_exact", [])
            for unit in _canonical_money_units_from_surface_v1(
                surface,
                compiled_specs=compiled_specs,
            )
        }
        money_column_units.append(column_units)
    if table_units:
        table_unit = next(iter(table_units))
        if any(len(units) > 1 or (units and units != {table_unit}) for units in money_column_units):
            return None
        return table_unit
    if not money_column_units or any(len(units) != 1 for units in money_column_units):
        return None
    uniform_units = {next(iter(units)) for units in money_column_units}
    return next(iter(uniform_units)) if len(uniform_units) == 1 else None


def _unit_visible(table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]) -> bool:
    return _bound_unit(table, compiled_specs=compiled_specs) is not None


def _checked_row_values(rows: Sequence[Mapping[str, Any]], *, column_count: int) -> None:
    if any(
        type(row.get("values_exact")) is not list or len(row["values_exact"]) != column_count
        for row in rows
    ):
        raise _error("roll-forward row value vector does not match the column axis")


def _period_from_surfaces(values: Sequence[Any]) -> tuple[date, str] | None:
    tokens = [
        resolved[0]
        for value in values
        if (resolved := _movement_period_end_token_v1(value)) is not None
    ]
    if not tokens:
        return None
    dates = {token[0] for token in tokens}
    if len(dates) == 1:
        return tokens[-1]
    years = {value.year for value in dates}
    if len(years) == 1:
        selected_date = max(dates)
        return next(token for token in reversed(tokens) if token[0] == selected_date)
    return None


def _period_semantics_evidence_v1(
    period: tuple[date, str] | None,
    *,
    source_kind: str | None,
    date_source_surfaces: Sequence[Any],
    local_context_surfaces: Sequence[Any],
    document_fiscal_close_year_binding_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if period is None or source_kind is None:
        return None
    date_source_exact_axis = []
    for value in date_source_surfaces:
        resolved = _movement_period_end_token_v1(value)
        document_year_bound = (
            document_fiscal_close_year_binding_receipt is not None
            and resolved is not None
            and resolved[1] == "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
            and resolved[0][0].year == period[0].year
        )
        unbound_year_candidate = (
            document_fiscal_close_year_binding_receipt is None
            and resolved is not None
            and resolved[1] == "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
            and resolved[0][0] == period[0]
        )
        if (
            type(value) is str
            and value
            and (
                resolved is not None
                and resolved[1] != "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
                and resolved[0][0] == period[0]
                or document_year_bound
                or unbound_year_candidate
            )
            and value not in date_source_exact_axis
        ):
            date_source_exact_axis.append(value)
    if not date_source_exact_axis:
        raise _error("roll-forward period evidence has no exact date source")
    local_context_exact_axis = []
    for value in local_context_surfaces:
        if type(value) is str and value and value not in local_context_exact_axis:
            local_context_exact_axis.append(value)
    return {
        "document_fiscal_close_year_binding_receipt": (
            canonical_clone_v1(document_fiscal_close_year_binding_receipt)
            if document_fiscal_close_year_binding_receipt is not None
            else None
        ),
        "date_source_exact_axis": date_source_exact_axis,
        "local_context_exact_axis": local_context_exact_axis,
        "period_date": period[0].isoformat(),
        "source_kind": source_kind,
    }


def classify_gemini_json_rollforward_table_v1(
    *,
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one decoded candidate table without granting numeric authority.

    The result is used by the selected-frontier storage query after indexed
    endpoint rows have reduced the search space.  Population qualifiers are
    evaluated per column so a customer-loan block can coexist with an LC block
    in the same table without admitting the LC columns.
    """

    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        raise _error("roll-forward candidate table axes are incomplete")
    try:
        blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    except GeminiJsonRollforwardAccountingFamilyV1Error:
        blocks = []
    movement_roles = [item["movement_role"] for block in blocks for item in block]
    core_roles = {
        item["role"] for item in compiled_specs["layout"]["movement_roles"] if item["required"]
    }
    lane_by_column, lane_population_assignment_receipt = _projected_lane_columns_v1(
        columns,
        compiled_specs=compiled_specs,
        rows=rows,
    )
    column_lanes = {role for role in lane_by_column if role is not None}
    context = _lane_context_evidence(
        section,
        table,
        compiled_specs=compiled_specs,
    )
    context_lane = context["explicit_lane_role"]
    if len(column_lanes) >= compiled_specs["layout"]["minimum_required_lanes"]:
        orientation = "LANE_COLUMNS"
    elif context_lane is not None or context["narrative_lane_roles"]:
        orientation = "PERIOD_COLUMNS"
    else:
        orientation = None
    structural_surfaces = [
        section.get("title_exact"),
        *section.get("narratives_exact", []),
        table.get("title_exact"),
    ]
    structural_text = " ".join(value for value in structural_surfaces if type(value) is str)
    accepted_header_text = " ".join(
        value
        for column, lane_role in zip(columns, lane_by_column, strict=True)
        if lane_role is not None
        for value in column.get("header_path_exact", [])
        if type(value) is str
    )
    population_policy = compiled_specs["layout"]["population_policy"]
    local_owner_visible = _matches_alias(
        " ".join((structural_text, accepted_header_text)),
        population_policy["owner_aliases"],
    )
    period_context_owner_visible = _matches_alias(
        " ".join(
            value
            for value in [section.get("title_exact"), *section.get("narratives_exact", [])]
            if type(value) is str
        ),
        population_policy["owner_aliases"],
    )
    structural_hard_negative_visible = context["hard_negative_visible"] or _matches_alias(
        structural_text, population_policy["hard_negative_aliases"]
    )
    reasons = []
    if not core_roles <= set(movement_roles):
        reasons.append("ROLLFORWARD_CORE_MOVEMENT_ROLES_INCOMPLETE")
    if orientation is None:
        reasons.append("ROLLFORWARD_LANE_OR_PERIOD_AXIS_NOT_CLASSIFIED")
    if structural_hard_negative_visible:
        reasons.append("ROLLFORWARD_STRUCTURAL_HARD_NEGATIVE_VISIBLE")
    return {
        "column_lane_roles": lane_by_column,
        "continuation_evidence": _explicit_continuation_evidence(section, table),
        "context_lane_assignment_source_kind": context["explicit_source_kind"],
        "context_lane_candidates_in_source_order": context["narrative_lane_roles"],
        "context_lane_evidence": context["narrative_lane_evidence"],
        "context_lane_role": context_lane,
        "context_reset_visible": context["reset_visible"],
        "local_owner_visible": local_owner_visible,
        "lane_population_assignment_receipt": lane_population_assignment_receipt,
        "movement_roles_in_source_order": movement_roles,
        "orientation": orientation,
        "period_context_owner_visible": period_context_owner_visible,
        "reasons": reasons,
        "structural_hard_negative_visible": structural_hard_negative_visible,
    }


def classify_gemini_json_rollforward_cluster_layout_v1(
    component_classifications: Sequence[Mapping[str, Any]],
) -> str | None:
    """Classify the selected component topology without using decoded values.

    This structural layout is shared with the indexed query.  In particular,
    one selected lane-column table remains a ``STACKED_PERIOD_BLOCKS`` layout
    even when only one period block can be decoded.  Period completeness is a
    separate accounting check and makes that candidate unresolved; it must not
    change the authenticated layout after query selection.
    """

    if (
        type(component_classifications) not in {list, tuple}
        or not component_classifications
        or any(not isinstance(item, Mapping) for item in component_classifications)
    ):
        raise _error("roll-forward component classification axis is invalid")
    orientations = {item.get("orientation") for item in component_classifications}
    component_count = len(component_classifications)
    if component_count == 1 and orientations == {"LANE_COLUMNS"}:
        return "STACKED_PERIOD_BLOCKS"
    if component_count == 2 and orientations == {"LANE_COLUMNS"}:
        return "PERIOD_TABLES_LANE_COLUMNS"
    if component_count == 2 and orientations == {"PERIOD_COLUMNS"}:
        return "LANE_TABLES_PERIOD_COLUMNS"
    return None


def build_gemini_json_rollforward_complementary_continuation_v1(
    *,
    owner_locator: Mapping[str, Any],
    owner_section: Mapping[str, Any],
    owner_table: Mapping[str, Any],
    continuation_locator: Mapping[str, Any],
    continuation_section: Mapping[str, Any],
    continuation_table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate and materialize one row-split, adjacent-page table.

    The incoming half must be explicitly marked by the provider.  The outgoing
    half may also be marked, or may be an immediately preceding owner-visible
    prefix whose missing closing endpoint proves it is not a complete table on
    its own.  Headers may be repeated exactly or omitted on the incoming page;
    conflicting headers, units, populations, document identity, direction, or
    page distance reject the merge.  The returned source-row locator axis
    keeps every value bound to the physical table where it was observed.
    """

    if any(
        not isinstance(value, Mapping)
        for value in (
            owner_locator,
            owner_section,
            owner_table,
            continuation_locator,
            continuation_section,
            continuation_table,
        )
    ):
        raise _error("roll-forward complementary continuation input is invalid")
    if (
        owner_locator.get("document_id") != continuation_locator.get("document_id")
        or owner_locator.get("source_logical_name")
        != continuation_locator.get("source_logical_name")
        or owner_locator.get("source_sha256") != continuation_locator.get("source_sha256")
        or type(owner_locator.get("physical_page")) is not int
        or type(continuation_locator.get("physical_page")) is not int
        or continuation_locator["physical_page"] - owner_locator["physical_page"] != 1
        or owner_table.get("continuation")
        not in {"NONE", "CONTINUES_ON_NEXT_PAGE", "BOTH"}
        or continuation_table.get("continuation")
        not in {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}
    ):
        return None
    owner_columns = owner_table.get("columns")
    continuation_columns = continuation_table.get("columns")
    owner_rows = owner_table.get("rows")
    continuation_rows = continuation_table.get("rows")
    if (
        type(owner_columns) is not list
        or not owner_columns
        or type(continuation_columns) is not list
        or len(owner_columns) != len(continuation_columns)
        or type(owner_rows) is not list
        or not owner_rows
        or type(continuation_rows) is not list
        or not continuation_rows
    ):
        return None

    def header_surface(column: Mapping[str, Any]) -> str | None:
        path = column.get("header_path_exact")
        if type(path) is not list or any(
            value is not None and type(value) is not str for value in path
        ):
            raise _error("roll-forward continuation column header is invalid")
        values = [value for value in path if type(value) is str and value.strip()]
        return " ".join(values) if values else None

    for owner_column, continuation_column in zip(
        owner_columns, continuation_columns, strict=True
    ):
        if not isinstance(owner_column, Mapping) or not isinstance(
            continuation_column, Mapping
        ):
            raise _error("roll-forward continuation column is invalid")
        owner_header = header_surface(owner_column)
        continuation_header = header_surface(continuation_column)
        if (
            owner_column.get("value_kind") != continuation_column.get("value_kind")
            or continuation_header is not None
            and _normalized(continuation_header) != _normalized(owner_header)
        ):
            return None
    try:
        owner_classification = classify_gemini_json_rollforward_table_v1(
            section=owner_section,
            table=owner_table,
            compiled_specs=compiled_specs,
        )
        continuation_classification = classify_gemini_json_rollforward_table_v1(
            section=continuation_section,
            table=continuation_table,
            compiled_specs=compiled_specs,
        )
    except GeminiJsonRollforwardAccountingFamilyV1Error:
        return None
    if (
        not owner_classification["local_owner_visible"]
        or owner_classification["orientation"] != "LANE_COLUMNS"
        or "ROLLFORWARD_CORE_MOVEMENT_ROLES_INCOMPLETE"
        not in owner_classification["reasons"]
        or owner_classification["context_reset_visible"]
        or owner_classification["structural_hard_negative_visible"]
        or continuation_classification["context_reset_visible"]
        or continuation_classification["structural_hard_negative_visible"]
    ):
        return None
    owner_unit = _bound_unit(owner_table, compiled_specs=compiled_specs)
    continuation_unit = _bound_unit(continuation_table, compiled_specs=compiled_specs)
    if owner_unit is not None and continuation_unit is not None and owner_unit != continuation_unit:
        return None
    combined_table = canonical_clone_v1(owner_table)
    combined_table["continuation"] = "NONE"
    combined_table["rows"] = [
        *canonical_clone_v1(owner_rows),
        *canonical_clone_v1(continuation_rows),
    ]
    if combined_table.get("unit_exact") is None:
        combined_table["unit_exact"] = continuation_table.get("unit_exact")
    combined_section = canonical_clone_v1(owner_section)
    try:
        logical_classification = classify_gemini_json_rollforward_table_v1(
            section=combined_section,
            table=combined_table,
            compiled_specs=compiled_specs,
        )
    except GeminiJsonRollforwardAccountingFamilyV1Error:
        return None
    if (
        logical_classification["orientation"] != "LANE_COLUMNS"
        or logical_classification["reasons"]
        or not logical_classification["local_owner_visible"]
        or logical_classification["context_reset_visible"]
        or logical_classification["structural_hard_negative_visible"]
    ):
        return None
    row_source_refs = []
    logical_row_ordinal = 0
    for locator, rows in (
        (owner_locator, owner_rows),
        (continuation_locator, continuation_rows),
    ):
        for source_row_ordinal, _row in enumerate(rows, start=1):
            logical_row_ordinal += 1
            row_source_refs.append(
                {
                    "logical_row_id": f"r{logical_row_ordinal}",
                    "source_locator": canonical_clone_v1(locator),
                    "source_row_id": f"r{source_row_ordinal}",
                }
            )
    receipt = {
        "combined_row_axis_sha256": canonical_json_sha256_v1(
            [
                {
                    **canonical_clone_v1(source_ref),
                    "row": canonical_clone_v1(row),
                }
                for source_ref, row in zip(
                    row_source_refs,
                    combined_table["rows"],
                    strict=True,
                )
            ]
        ),
        "continuation_column_axis_sha256": canonical_json_sha256_v1(
            continuation_columns
        ),
        "continuation_kind": continuation_table["continuation"],
        "continuation_locator": canonical_clone_v1(continuation_locator),
        "direction_authentication_kind": (
            "BIDIRECTIONAL_PROVIDER_CONTINUATION"
            if owner_table["continuation"] in {"CONTINUES_ON_NEXT_PAGE", "BOTH"}
            else (
                "EXPLICIT_INCOMING_WITH_IMMEDIATELY_PRECEDING_OWNER_PREFIX_"
                "MISSING_CLOSING_ENDPOINT"
            )
        ),
        "logical_classification": canonical_clone_v1(logical_classification),
        "logical_layout_kind": "STACKED_PERIOD_BLOCKS",
        "logical_orientation": "LANE_COLUMNS",
        "owner_column_axis_sha256": canonical_json_sha256_v1(owner_columns),
        "owner_continuation_kind": owner_table["continuation"],
        "owner_locator": canonical_clone_v1(owner_locator),
        "row_source_ref_axis": canonical_clone_v1(row_source_refs),
        "rule": (
            "SAME_DOCUMENT_ADJACENT_PAGE_AUTHENTICATED_INCOMING_CONTINUATION_"
            "OWNER_PREFIX_MISSING_CLOSING_ENDPOINT_COLUMNS_INHERITED_ONLY_WHEN_"
            "INCOMING_HEADERS_OMITTED_OR_EXACT_AND_COMBINED_ROWS_CLOSE_DECLARED_"
            "ROLLFORWARD"
        ),
        "status": "AUTHENTICATED_COMPLEMENTARY_ROW_CONTINUATION",
    }
    return {
        "combined_section": combined_section,
        "combined_table": combined_table,
        "receipt": receipt,
        "row_source_refs": row_source_refs,
    }


def build_gemini_json_rollforward_following_owner_backbinding_v1(
    *,
    preceding_locator: Mapping[str, Any],
    preceding_section: Mapping[str, Any],
    preceding_table: Mapping[str, Any],
    following_locator: Mapping[str, Any],
    following_section: Mapping[str, Any],
    following_table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate a complete component whose owner appears on the next page.

    Some disclosures put the current-period table at the bottom of a page
    carrying only the report header, then print the family title, ``tiếp
    theo`` marker and complete comparative table at the top of the next page.
    This binds only that immediately preceding complete table: both tables
    must have identical declared lane/movement topology, distinct ordered
    exact period contexts, compatible units and no reset/hard negative.
    """

    if any(
        not isinstance(value, Mapping)
        for value in (
            preceding_locator,
            preceding_section,
            preceding_table,
            following_locator,
            following_section,
            following_table,
        )
    ):
        raise _error("roll-forward following-owner backbinding input is invalid")
    if (
        preceding_locator.get("document_id") != following_locator.get("document_id")
        or preceding_locator.get("source_logical_name")
        != following_locator.get("source_logical_name")
        or preceding_locator.get("source_sha256") != following_locator.get("source_sha256")
        or type(preceding_locator.get("physical_page")) is not int
        or type(following_locator.get("physical_page")) is not int
        or following_locator["physical_page"] - preceding_locator["physical_page"] != 1
        or preceding_table.get("continuation")
        not in {"NONE", "CONTINUES_ON_NEXT_PAGE", "BOTH"}
        or following_table.get("continuation")
        not in {"CONTINUES_FROM_PREVIOUS_PAGE", "BOTH"}
    ):
        return None
    try:
        preceding_classification = classify_gemini_json_rollforward_table_v1(
            section=preceding_section,
            table=preceding_table,
            compiled_specs=compiled_specs,
        )
        following_classification = classify_gemini_json_rollforward_table_v1(
            section=following_section,
            table=following_table,
            compiled_specs=compiled_specs,
        )
    except GeminiJsonRollforwardAccountingFamilyV1Error:
        return None
    if (
        preceding_classification["reasons"]
        or following_classification["reasons"]
        or preceding_classification["orientation"] != "LANE_COLUMNS"
        or following_classification["orientation"] != "LANE_COLUMNS"
        or preceding_classification["local_owner_visible"]
        or not following_classification["local_owner_visible"]
        or preceding_classification["context_reset_visible"]
        or following_classification["context_reset_visible"]
        or preceding_classification["structural_hard_negative_visible"]
        or following_classification["structural_hard_negative_visible"]
        or preceding_classification["column_lane_roles"]
        != following_classification["column_lane_roles"]
        or preceding_classification["movement_roles_in_source_order"]
        != following_classification["movement_roles_in_source_order"]
    ):
        return None

    def exact_period_context(
        section: Mapping[str, Any], table: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        source_axis = []
        for source_kind, source_exact in (
            ("SECTION_TITLE", section.get("title_exact")),
            *(
                ("SECTION_NARRATIVE", value)
                for value in section.get("narratives_exact", [])
            ),
            ("TABLE_TITLE", table.get("title_exact")),
        ):
            resolved = _period_from_surfaces([source_exact])
            if resolved is not None:
                source_axis.append(
                    {
                        "date": resolved[0].isoformat(),
                        "source_exact": source_exact,
                        "source_kind": source_kind,
                    }
                )
        dates = {item["date"] for item in source_axis}
        if len(dates) != 1:
            return None
        return {
            "date": next(iter(dates)),
            "source_axis": source_axis,
            "source_axis_sha256": canonical_json_sha256_v1(source_axis),
        }

    preceding_period = exact_period_context(preceding_section, preceding_table)
    following_period = exact_period_context(following_section, following_table)
    if (
        preceding_period is None
        or following_period is None
        or preceding_period["date"] <= following_period["date"]
    ):
        return None
    preceding_unit = _bound_unit(preceding_table, compiled_specs=compiled_specs)
    following_unit = _bound_unit(following_table, compiled_specs=compiled_specs)
    if (
        preceding_unit is not None
        and following_unit is not None
        and preceding_unit != following_unit
    ):
        return None
    receipt = {
        "following_classification": canonical_clone_v1(following_classification),
        "following_column_axis_sha256": canonical_json_sha256_v1(
            following_table.get("columns")
        ),
        "following_continuation_kind": following_table["continuation"],
        "following_locator": canonical_clone_v1(following_locator),
        "following_period_context": following_period,
        "following_unit": following_unit,
        "preceding_classification": canonical_clone_v1(preceding_classification),
        "preceding_column_axis_sha256": canonical_json_sha256_v1(
            preceding_table.get("columns")
        ),
        "preceding_continuation_kind": preceding_table["continuation"],
        "preceding_locator": canonical_clone_v1(preceding_locator),
        "preceding_period_context": preceding_period,
        "preceding_unit": preceding_unit,
        "rule": (
            "SAME_DOCUMENT_IMMEDIATELY_FOLLOWING_LOCAL_OWNER_WITH_EXPLICIT_"
            "INCOMING_CONTINUATION_BACKBINDS_PRECEDING_COMPLETE_SAME_TOPOLOGY_"
            "DISTINCT_ORDERED_EXACT_PERIOD_CONTEXT_COMPONENT"
        ),
        "status": "AUTHENTICATED_FOLLOWING_OWNER_BACKBINDING",
    }
    return receipt


def classify_gemini_json_rollforward_period_role_surface_v1(value: Any) -> str | None:
    """Classify an explicit relative-period label, never a generic ``trong kỳ`` row."""

    current = {
        "current period",
        "current year",
        "ky hien tai",
        "ky nay",
        "nam nay",
        "so cuoi quy",
        "this period",
        "this year",
    }
    comparative = {
        "ky so sanh",
        "ky truoc",
        "nam truoc",
        "previous period",
        "previous year",
        "prior period",
        "prior year",
        "so dau nam",
    }
    # Gemini sometimes retains a period caption as the final physical line of
    # a table title (``<owner>\nSố cuối quý``).  Treat physical lines as exact
    # surfaces; do not substring-match prose or ordinary movement-row labels.
    folded_axis = {
        _normalized(surface)
        for surface in str(value).splitlines()
        if _normalized(surface)
    }
    roles = {
        role
        for role, aliases in (
            ("CURRENT_PERIOD", current),
            ("COMPARATIVE_PERIOD", comparative),
        )
        if folded_axis & aliases
    }
    if roles == {"CURRENT_PERIOD"}:
        return "CURRENT_PERIOD"
    if roles == {"COMPARATIVE_PERIOD"}:
        return "COMPARATIVE_PERIOD"
    return None


def project_gemini_json_rollforward_source_role_vectors_v1(
    source_role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Project raw sources to one role vector without hiding duplicates.

    Multiple *movement* rows in one exact component/block/column are an
    additive accounting presentation (for example two separately disclosed
    uses of specific provision).  They may be summed only when every source
    cell is an exact integer/dash or an explicitly unknown blank and all
    period, lane, unit, locator and block coordinates agree.  A group with a
    blank remains one unknown aggregate movement, which may only be solved by
    the ordinary one-unknown full-rank equation.  Repeated endpoints,
    cross-component repeats and conflicting scopes remain ambiguities.
    """

    if type(source_role_vectors) not in {list, tuple} or any(
        not isinstance(item, Mapping) for item in source_role_vectors
    ):
        raise _error("roll-forward source-role vector axis is invalid")
    kind_by_role = {
        item["role"]: item["kind"] for item in compiled_specs["layout"]["movement_roles"]
    }
    groups: dict[tuple[str, str, str], list[tuple[int, Mapping[str, Any]]]] = {}
    for ordinal, vector in enumerate(source_role_vectors, start=1):
        key = (
            vector.get("period_role"),
            vector.get("lane_role"),
            vector.get("movement_role"),
        )
        if (
            any(type(item) is not str or not item for item in key)
            or key[2] not in kind_by_role
        ):
            raise _error("roll-forward source-role vector key is invalid")
        groups.setdefault(key, []).append((ordinal, vector))

    projected = []
    duplicate_receipts = []
    reasons = []
    scope_fields = (
        "block_ordinal",
        "bound_unit",
        "column_ordinal",
        "endpoint_date",
        "locator",
        "period_date",
        "period_role",
        "period_semantics_evidence",
        "resolved_period",
    )
    for key, records in groups.items():
        first = records[0][1]
        if len(records) == 1:
            projected.append(canonical_clone_v1(first))
            continue
        cells = [record.get("cell") for _ordinal, record in records]
        exact_cells = all(
            type(cell) is dict
            and type(cell.get("coefficient")) is int
            and cell.get("state") in {"DASH_ZERO", "RAW_SIGNED_INTEGER"}
            and type(cell.get("source_text")) is str
            for cell in cells
        )
        exact_or_unknown_cells = all(
            type(cell) is dict
            and (
                (
                    type(cell.get("coefficient")) is int
                    and cell.get("state") in {"DASH_ZERO", "RAW_SIGNED_INTEGER"}
                    and type(cell.get("source_text")) is str
                )
                or (
                    cell.get("coefficient") is None
                    and cell.get("state") == "UNKNOWN_BLANK"
                    and cell.get("source_text") is None
                )
            )
            for cell in cells
        )
        one_scope = all(
            all(same_typed_json_v1(record.get(field), first.get(field)) for field in scope_fields)
            for _ordinal, record in records[1:]
        )
        source_coordinates = [
            (
                canonical_json_sha256_v1(record.get("locator")),
                record.get("block_ordinal"),
                record.get("column_ordinal"),
                record.get("row_id"),
            )
            for _ordinal, record in records
        ]
        additive_scope = (
            kind_by_role[key[2]] not in {"OPENING", "CLOSING"}
            and one_scope
            and len(source_coordinates) == len(set(source_coordinates))
        )
        if additive_scope and exact_or_unknown_cells:
            aggregate_cell = (
                {
                    "coefficient": sum(cell["coefficient"] for cell in cells),
                    "source_text": " + ".join(cell["source_text"] for cell in cells),
                    "state": "AGGREGATED_EXACT_SOURCE_ROWS",
                }
                if exact_cells
                else {
                    "coefficient": None,
                    "source_text": None,
                    "state": "UNKNOWN_BLANK",
                }
            )
            aggregate = canonical_clone_v1(first)
            aggregate["assignment_kind"] = (
                "EXACT_ADDITIVE_SAME_BLOCK_SOURCE_ROWS"
                if exact_cells
                else "ADDITIVE_SAME_BLOCK_SOURCE_ROWS_WITH_UNKNOWN"
            )
            aggregate["cell"] = aggregate_cell
            aggregate["row_label_exact"] = " + ".join(
                record["row_label_exact"] for _ordinal, record in records
            )
            projected.append(aggregate)
            duplicate_receipts.append(
                {
                    "aggregate_cell": canonical_clone_v1(aggregate_cell),
                    "corroborated_key": list(key),
                    "disposition": (
                        "EXACT_ADDITIVE_SAME_BLOCK_SOURCE_ROWS_PROJECTED"
                        if exact_cells
                        else "ADDITIVE_SAME_BLOCK_SOURCE_ROWS_WITH_UNKNOWN_PROJECTED"
                    ),
                    "rule": (
                        "SAME_PERIOD_LANE_COMPONENT_BLOCK_COLUMN_ADDITIVE_MOVEMENT_"
                        "ROWS_EXACT_OR_ONE_EQUATION_UNKNOWN_ONLY"
                    ),
                    "source_records": [
                        {
                            "cell": canonical_clone_v1(record["cell"]),
                            "column_ordinal": record["column_ordinal"],
                            "locator": canonical_clone_v1(record["locator"]),
                            "row_id": record["row_id"],
                            "row_label_exact": record["row_label_exact"],
                            "source_role_vector_ordinal": ordinal,
                        }
                        for ordinal, record in records
                    ],
                }
            )
            continue
        projected.append(canonical_clone_v1(first))
        reason = "ROLLFORWARD_DUPLICATE_ROLE_PERIOD_LANE_AMBIGUOUS:" + ":".join(key)
        reasons.append(reason)
        for _ordinal, vector in records[1:]:
            duplicate_receipts.append(
                {
                    "corroborated_key": list(key),
                    "disposition": (
                        "IDENTICAL_DUPLICATE_SOURCE_AMBIGUOUS"
                        if (
                            same_typed_json_v1(first.get("cell"), vector.get("cell"))
                            and first.get("resolved_period") == vector.get("resolved_period")
                            and first.get("bound_unit") == vector.get("bound_unit")
                        )
                        else "CONFLICTING_DUPLICATE_SOURCE_AMBIGUOUS"
                    ),
                    "first_column_ordinal": first.get("column_ordinal"),
                    "first_locator": canonical_clone_v1(first.get("locator")),
                    "second_column_ordinal": vector.get("column_ordinal"),
                    "second_locator": canonical_clone_v1(vector.get("locator")),
                }
            )
    return projected, duplicate_receipts, sorted(set(reasons))


def build_gemini_json_rollforward_duplicate_source_ambiguities_v1(
    source_role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Rebuild every duplicate-source disposition from the raw source axis."""

    return project_gemini_json_rollforward_source_role_vectors_v1(
        source_role_vectors,
        compiled_specs=compiled_specs,
    )[1]


def normalize_gemini_json_rollforward_directional_deductions_v1(
    projected_role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize one uniquely closing unsigned use/decrease source cell.

    Several audited disclosures print a use of provision as an unsigned
    number although its row semantics are deductive.  A positive source cell
    is negated only when (a) its already authenticated role is USE/DECREASE,
    (b) the unmodified lane is a mismatch, and (c) flipping exactly one such
    cell is the unique way to close the full equation exactly.  Literal source
    text remains unchanged and the transformation is persisted for replay.
    """

    result = [canonical_clone_v1(vector) for vector in projected_role_vectors]
    movement_specs = compiled_specs["layout"]["movement_roles"]
    kind_by_role = {item["role"]: item["kind"] for item in movement_specs}
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    grouped_indices: dict[tuple[str, str], list[int]] = {}
    for index, vector in enumerate(result):
        grouped_indices.setdefault(
            (vector.get("period_role"), vector.get("lane_role")), []
        ).append(index)
    receipts = []
    for (period_role, lane_role), indices in sorted(grouped_indices.items()):
        cells = {result[index]["movement_role"]: result[index]["cell"] for index in indices}
        if not required_movements <= set(cells):
            continue
        baseline = solve_one_unknown_rollforward_lane_v1(
            cells,
            movement_specs=movement_specs,
        )
        if baseline["status"] != "MISMATCH":
            continue
        exact_candidates = []
        for index in indices:
            vector = result[index]
            cell = vector["cell"]
            if (
                kind_by_role.get(vector["movement_role"]) not in {"USE", "DECREASE"}
                or cell.get("state") != "RAW_SIGNED_INTEGER"
                or type(cell.get("coefficient")) is not int
                or cell["coefficient"] <= 0
            ):
                continue
            trial_cells = canonical_clone_v1(cells)
            trial_cells[vector["movement_role"]] = {
                **canonical_clone_v1(cell),
                "coefficient": -cell["coefficient"],
                "state": "NORMALIZED_DIRECTIONAL_DEDUCTION",
            }
            solution = solve_one_unknown_rollforward_lane_v1(
                trial_cells,
                movement_specs=movement_specs,
            )
            if solution["status"] == "EXACT":
                exact_candidates.append((index, trial_cells[vector["movement_role"]], solution))
        if len(exact_candidates) != 1:
            continue
        index, normalized_cell, solution = exact_candidates[0]
        vector = result[index]
        source_cell = canonical_clone_v1(vector["cell"])
        vector["cell"] = normalized_cell
        receipts.append(
            {
                "lane_role": lane_role,
                "locator": canonical_clone_v1(vector["locator"]),
                "movement_role": vector["movement_role"],
                "normalized_cell": canonical_clone_v1(normalized_cell),
                "period_role": period_role,
                "row_id": vector["row_id"],
                "row_label_exact": vector["row_label_exact"],
                "rule": (
                    "UNSIGNED_POSITIVE_USE_OR_DECREASE_NEGATED_ONLY_BY_UNIQUE_"
                    "EXACT_FULL_LANE_EQUATION_CLOSURE"
                ),
                "source_cell": source_cell,
                "source_mismatch_residual": baseline["residual"],
                "status": "UNIQUE_EXACT_DIRECTIONAL_DEDUCTION_NORMALIZED",
                "target_residual": solution["residual"],
            }
        )
    return result, receipts


def _row_blocks(
    rows: list[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[list[dict[str, Any]]]:
    """Return explicit blocks plus a bounded shared-closing/opening block.

    A common accounting presentation prints ``O, movements, C(previous),
    movements, C(current)``.  The first closing is also the second period's
    opening even though its visible label remains ``closing``.  This is the
    only implicit endpoint admitted: it must follow one completed block and
    must itself terminate at the next visible closing.
    """

    role_specs = {item["role"]: item for item in compiled_specs["layout"]["movement_roles"]}
    opening = next(role for role, item in role_specs.items() if item["kind"] == "OPENING")
    closing = next(role for role, item in role_specs.items() if item["kind"] == "CLOSING")
    required = {role for role, item in role_specs.items() if item["required"]}
    blocks: list[list[dict[str, Any]]] = []
    active: list[dict[str, Any]] | None = None
    previous_closing: dict[str, Any] | None = None

    def source_entry(
        index: int,
        role: str,
        *,
        assignment_kind: str = "DECLARED_SURFACE_ROLE",
        source_movement_role: str | None = None,
        source_block_ordinal: int | None = None,
    ) -> dict[str, Any]:
        token = _date_token(rows[index].get("label_exact"))
        hierarchy_path_exact = rows[index].get("hierarchy_path_exact")
        if type(hierarchy_path_exact) is not list:
            raise _error("roll-forward source row hierarchy is invalid")
        return {
            "assignment_kind": assignment_kind,
            "endpoint_date": token[0].isoformat() if token is not None else None,
            "movement_role": role,
            "row_hierarchy_path_exact": canonical_clone_v1(hierarchy_path_exact),
            "row_index": index,
            "row_label_exact": rows[index].get("label_exact"),
            "source_block_ordinal": source_block_ordinal,
            "source_movement_role": source_movement_role or role,
        }

    def is_ordered_date_endpoint(index: int) -> bool:
        folded = _normalized(rows[index].get("label_exact"))
        return _date_token(rows[index].get("label_exact")) is not None and (
            folded.startswith("tai ngay ")
            or folded.startswith("tai ")
            or folded.startswith("ngay ")
            or folded.startswith("so du tai ngay ")
        )

    def close_active(entry: dict[str, Any]) -> None:
        nonlocal active, previous_closing
        if active is None:
            raise _error("roll-forward closing endpoint has no opening endpoint")
        active.append(entry)
        roles = [item["movement_role"] for item in active]
        if not required <= set(roles) or roles[0] != opening or roles[-1] != closing:
            raise _error("roll-forward period block has incomplete endpoint topology")
        opening_date = active[0]["endpoint_date"]
        closing_date = active[-1]["endpoint_date"]
        if (
            opening_date is not None and closing_date is not None and opening_date >= closing_date
        ) or (
            active[0]["assignment_kind"] == "ORDERED_DATE_ENDPOINT_AS_OPENING"
            and (opening_date is None or closing_date is None)
        ):
            raise _error("roll-forward ordered date endpoint continuity is invalid")
        blocks.append(active)
        previous_closing = active[-1]
        active = None

    for index, row in enumerate(rows):
        # Provider JSON may preserve visual period dividers such as ``Kỳ
        # này`` or ``Số dư đầu năm`` as GROUP rows with no values.  They are
        # hierarchy/context carriers, not accounting movements, even when the
        # divider text is also a valid opening-balance alias.
        if (
            row.get("row_kind") == "GROUP"
            and type(row.get("values_exact")) is list
            and all(value is None for value in row["values_exact"])
        ):
            continue
        role = _role_for_row(row, compiled_specs=compiled_specs)
        if role is None:
            folded = _normalized(row.get("label_exact"))
            endpoint_period = _date_token(row.get("label_exact"))
            if endpoint_period is not None and (
                folded.startswith("tai ngay ")
                or folded.startswith("tai ")
                or folded.startswith("ngay ")
                or "so du" in folded
            ):
                role = opening if active is None else closing
        if role is None:
            continue
        if role == opening:
            if active is not None:
                raise _error("roll-forward opening endpoint repeats before closing")
            active = [source_entry(index, role)]
            continue
        if role == closing:
            # A stacked disclosure may print two self-contained windows as
            # ``dated opening ... dated closing, dated opening ... dated
            # closing``.  Every source-visible dated endpoint that starts
            # while no block is active is therefore an opening, including
            # after a prior block has closed.  The later closing-date and
            # equation checks authenticate each window independently.
            if active is None and is_ordered_date_endpoint(index):
                active = [
                    source_entry(
                        index,
                        opening,
                        assignment_kind="ORDERED_DATE_ENDPOINT_AS_OPENING",
                        source_movement_role=closing,
                    )
                ]
                continue
            close_active(source_entry(index, role))
            continue
        if active is None:
            if previous_closing is None:
                raise _error("roll-forward movement row has no opening endpoint")
            active = [
                source_entry(
                    previous_closing["row_index"],
                    opening,
                    assignment_kind="SHARED_PREVIOUS_CLOSING_AS_OPENING",
                    source_movement_role=closing,
                    source_block_ordinal=len(blocks),
                )
            ]
        # Multiple additive movement rows are preserved here and projected by
        # ``project_gemini_json_rollforward_source_role_vectors_v1``.  Opening
        # and closing endpoints remain structurally unique above.
        active.append(source_entry(index, role))
    if active is not None:
        raise _error("roll-forward period block has no closing endpoint")
    return blocks


def _period_lane_cells_from_lane_columns(
    *,
    locator: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    row_source_refs: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        raise _error("roll-forward table row/column axis is incomplete")
    _checked_row_values(rows, column_count=len(columns))
    if row_source_refs is not None and (
        len(row_source_refs) != len(rows)
        or any(
            not isinstance(item, Mapping)
            or set(item) != {"logical_row_id", "source_locator", "source_row_id"}
            or type(item.get("logical_row_id")) is not str
            or type(item.get("source_locator")) is not dict
            or type(item.get("source_row_id")) is not str
            for item in row_source_refs
        )
    ):
        raise _error("roll-forward continuation row-source axis is invalid")
    lane_by_column, lane_population_assignment_receipt = _projected_lane_columns_v1(
        columns,
        compiled_specs=compiled_specs,
        rows=rows,
    )
    if len({role for role in lane_by_column if role is not None}) < 2:
        return []
    aggregate_aliases = set(compiled_specs["layout"]["aggregate_population_aliases"])
    total_column_indexes = [
        index
        for index, (column, lane_role) in enumerate(zip(columns, lane_by_column, strict=True))
        if lane_role is None
        and any(
            _normalized(surface) in aggregate_aliases
            for surface in column.get("header_path_exact", [])
        )
    ]
    horizontal_total_zero_by_coordinate: dict[tuple[int, int], dict[str, Any]] = {}
    selected_lane_indexes = [
        index for index, lane_role in enumerate(lane_by_column) if lane_role is not None
    ]
    if len(total_column_indexes) == 1:
        total_index = total_column_indexes[0]
        for row_index, row in enumerate(rows):
            values = row["values_exact"]
            lane_cells = [_money(values[index]) for index in selected_lane_indexes]
            total_cell = _money(values[total_index])
            unknown_offsets = [
                offset
                for offset, cell in enumerate(lane_cells)
                if cell["coefficient"] is None
            ]
            if (
                len(unknown_offsets) != 1
                or type(total_cell["coefficient"]) is not int
                or any(
                    type(cell["coefficient"]) is not int
                    for offset, cell in enumerate(lane_cells)
                    if offset not in unknown_offsets
                )
            ):
                continue
            unknown_offset = unknown_offsets[0]
            known_sum = sum(
                int(cell["coefficient"])
                for offset, cell in enumerate(lane_cells)
                if offset != unknown_offset
            )
            if total_cell["coefficient"] != known_sum:
                continue
            column_index = selected_lane_indexes[unknown_offset]
            horizontal_total_zero_by_coordinate[(row_index, column_index)] = {
                "aggregate_cell": canonical_clone_v1(total_cell),
                "aggregate_column_header_path_exact": canonical_clone_v1(
                    columns[total_index].get("header_path_exact")
                ),
                "aggregate_column_ordinal": total_index + 1,
                "blank_column_header_path_exact": canonical_clone_v1(
                    columns[column_index].get("header_path_exact")
                ),
                "blank_column_ordinal": column_index + 1,
                "lane_role": lane_by_column[column_index],
                "locator": canonical_clone_v1(locator),
                "recovered_cell": {
                    "coefficient": 0,
                    "source_text": None,
                    "state": "HORIZONTAL_TOTAL_PROVEN_ZERO",
                },
                "row_id": (
                    row_source_refs[row_index]["logical_row_id"]
                    if row_source_refs is not None
                    else f"r{row_index + 1}"
                ),
                "row_label_exact": row.get("label_exact"),
                "rule": (
                    "ONE_BLANK_DECLARED_LANE_EQUALS_ZERO_ONLY_WHEN_EXACT_VISIBLE_"
                    "TOTAL_EQUALS_SUM_OF_ALL_OTHER_DECLARED_LANES"
                ),
                "sibling_cells": [
                    {
                        "cell": canonical_clone_v1(cell),
                        "column_ordinal": selected_lane_indexes[offset] + 1,
                        "lane_role": lane_by_column[selected_lane_indexes[offset]],
                    }
                    for offset, cell in enumerate(lane_cells)
                    if offset != unknown_offset
                ],
                "status": "EXACT_HORIZONTAL_TOTAL_ZERO_RECOVERED",
            }
    blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    if len(blocks) not in {1, 2}:
        raise _error("roll-forward lane-column table must expose one or two endpoint blocks")

    def projected_cell(row_index: int, column_index: int) -> dict[str, Any]:
        recovery = horizontal_total_zero_by_coordinate.get((row_index, column_index))
        return canonical_clone_v1(
            recovery["recovered_cell"]
            if recovery is not None
            else _money(rows[row_index]["values_exact"][column_index])
        )

    result = []
    for block_ordinal, block in enumerate(blocks, start=1):
        block_rows = [rows[item["row_index"]] for item in block]
        period_role_sources = []
        if classify_gemini_json_rollforward_period_role_surface_v1(
            table.get("title_exact")
        ) is not None:
            period_role_sources.append(("TABLE_TITLE", table["title_exact"]))
        for entry in block:
            hierarchy = entry["row_hierarchy_path_exact"]
            for surface in hierarchy[:-1]:
                if (
                    classify_gemini_json_rollforward_period_role_surface_v1(surface)
                    is not None
                    and ("SHARED_ROW_HIERARCHY_PERIOD_LABEL", surface)
                    not in period_role_sources
                ):
                    period_role_sources.append(
                        ("SHARED_ROW_HIERARCHY_PERIOD_LABEL", surface)
                    )
        selected_column_period_sources = []
        selected_column_roles = []
        for column, lane_role in zip(columns, lane_by_column, strict=True):
            if lane_role is None:
                continue
            column_sources = [
                surface
                for surface in column.get("header_path_exact", [])
                if classify_gemini_json_rollforward_period_role_surface_v1(surface)
                is not None
            ]
            selected_column_roles.append(
                {
                    classify_gemini_json_rollforward_period_role_surface_v1(surface)
                    for surface in column_sources
                }
            )
            selected_column_period_sources.extend(column_sources)
        if (
            selected_column_roles
            and all(len(roles) == 1 for roles in selected_column_roles)
            and len(set.union(*selected_column_roles)) == 1
        ):
            period_role_sources.append(
                (
                    "SHARED_COLUMN_HEADER_PERIOD_LABEL",
                    selected_column_period_sources[0],
                )
            )
        hinted_roles = {
            classify_gemini_json_rollforward_period_role_surface_v1(surface)
            for _kind, surface in period_role_sources
        }
        hinted_roles.discard(None)
        period_role_hint = next(iter(hinted_roles)) if len(hinted_roles) == 1 else None
        period_role_hint_source = next(
            (
                (source_kind, surface)
                for source_kind, surface in period_role_sources
                if classify_gemini_json_rollforward_period_role_surface_v1(surface)
                == period_role_hint
            ),
            (None, None),
        )
        closing_row = block_rows[-1]
        closing_period = _period_from_surfaces([closing_row.get("label_exact")])
        table_period = _period_from_surfaces([table.get("title_exact")])
        block_hierarchy_period_surfaces = [
            surface
            for entry in block
            for surface in entry["row_hierarchy_path_exact"][:-1]
        ]
        block_hierarchy_period = _period_from_surfaces(block_hierarchy_period_surfaces)
        section_period = _period_from_surfaces(
            [*section.get("narratives_exact", []), section.get("title_exact")]
        )
        period = closing_period or table_period or block_hierarchy_period or section_period
        period_assignment_source_kind = (
            "CLOSING_ROW_LABEL"
            if closing_period is not None
            else "TABLE_TITLE"
            if table_period is not None
            else "SHARED_ROW_HIERARCHY_PERIOD_DATE"
            if block_hierarchy_period is not None
            else "SELECTED_SECTION_CONTEXT"
            if section_period is not None
            else None
        )
        section_period_surfaces = [
            *section.get("narratives_exact", []),
            section.get("title_exact"),
        ]
        period_date_source_surfaces = (
            [closing_row.get("label_exact")]
            if closing_period is not None
            else [table.get("title_exact")]
            if table_period is not None
            else block_hierarchy_period_surfaces
            if block_hierarchy_period is not None
            else section_period_surfaces
        )
        local_period_context_surfaces = [
            *section_period_surfaces,
            table.get("title_exact"),
            *(value for column in columns for value in column.get("header_path_exact", [])),
        ]
        result.append(
            {
                "block_ordinal": block_ordinal,
                "bound_unit": _bound_unit(table, compiled_specs=compiled_specs),
                "cells": [
                    {
                        "assignment_kind": entry["assignment_kind"],
                        "cell": projected_cell(entry["row_index"], column_index),
                        "column_ordinal": column_index + 1,
                        "endpoint_date": entry["endpoint_date"],
                        "lane_role": lane_role,
                        # The accounting fragment is one logical table owned
                        # by ``locator``.  Exact physical row provenance is
                        # retained separately in the authenticated
                        # ``row_source_ref_axis``; keeping this locator logical
                        # also lets additive rows on opposite page halves
                        # replay in one deterministic component scope.
                        "locator": canonical_clone_v1(locator),
                        "movement_role": entry["movement_role"],
                        "row_hierarchy_path_exact": entry["row_hierarchy_path_exact"],
                        "row_id": (
                            row_source_refs[entry["row_index"]]["logical_row_id"]
                            if row_source_refs is not None
                            else f"r{entry['row_index'] + 1}"
                        ),
                        "row_label_exact": entry["row_label_exact"],
                        "source_block_ordinal": entry["source_block_ordinal"],
                        "source_movement_role": entry["source_movement_role"],
                    }
                    for entry in block
                    for column_index, lane_role in enumerate(lane_by_column)
                    if lane_role is not None
                ],
                "locator": canonical_clone_v1(locator),
                "lane_population_assignment_receipt": canonical_clone_v1(
                    lane_population_assignment_receipt
                ),
                "horizontal_total_zero_recovery_receipts": [
                    canonical_clone_v1(receipt)
                    for (row_index, _column_index), receipt in sorted(
                        horizontal_total_zero_by_coordinate.items()
                    )
                    if any(entry["row_index"] == row_index for entry in block)
                ],
                "period": period,
                "period_assignment_source_kind": period_assignment_source_kind,
                "period_semantics_evidence": _period_semantics_evidence_v1(
                    period,
                    source_kind=period_assignment_source_kind,
                    date_source_surfaces=period_date_source_surfaces,
                    local_context_surfaces=local_period_context_surfaces,
                ),
                "period_role_hint": period_role_hint,
                "period_role_hint_source_exact": period_role_hint_source[1],
                "period_role_hint_source_kind": period_role_hint_source[0],
            }
        )
    return result


def _period_lane_cells_from_period_columns(
    *,
    locator: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    lane_role_override: str | None = None,
) -> list[dict[str, Any]]:
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or not columns or type(rows) is not list or not rows:
        raise _error("roll-forward lane table row/column axis is incomplete")
    _checked_row_values(rows, column_count=len(columns))
    lane_role = lane_role_override or _lane_from_table_context(
        section, table, compiled_specs=compiled_specs
    )
    if lane_role is None:
        return []
    period_surfaces = [column.get("header_path_exact", []) for column in columns]
    periods = [_period_from_surfaces(surfaces) for surfaces in period_surfaces]
    bare_year_columns = []
    for column_index, (surfaces, period) in enumerate(zip(period_surfaces, periods, strict=True)):
        if period is None:
            continue
        resolved_surfaces = [
            resolved
            for surface in surfaces
            if (resolved := _movement_period_end_token_v1(surface)) is not None
            and resolved[0][0] == period[0]
        ]
        if resolved_surfaces and all(
            resolved[1] == "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
            for resolved in resolved_surfaces
        ):
            bare_year_columns.append(column_index)
    if bare_year_columns:
        years = {periods[index][0].year for index in bare_year_columns if periods[index]}
        if len(bare_year_columns) != len(columns) or len(years) != 2:
            raise _error("roll-forward mixed bare-year/full-date period columns are ambiguous")
    if (
        any(period is None for period in periods)
        or len({period[0] for period in periods if period}) != 2
    ):
        raise _error("roll-forward lane table must expose exactly two period columns")
    blocks = _row_blocks(rows, compiled_specs=compiled_specs)
    if len(blocks) != 1:
        raise _error("roll-forward lane table must expose one endpoint block")
    block = blocks[0]
    result = []
    for column_index, period in enumerate(periods):
        local_period_context_surfaces = [
            section.get("title_exact"),
            *section.get("narratives_exact", []),
            table.get("title_exact"),
            *columns[column_index].get("header_path_exact", []),
        ]
        result.append(
            {
                "block_ordinal": column_index + 1,
                "bound_unit": _bound_unit(table, compiled_specs=compiled_specs),
                "cells": [
                    {
                        "assignment_kind": entry["assignment_kind"],
                        "cell": _money(rows[entry["row_index"]].get("values_exact")[column_index]),
                        "column_ordinal": column_index + 1,
                        "endpoint_date": entry["endpoint_date"],
                        "lane_role": lane_role,
                        "movement_role": entry["movement_role"],
                        "row_hierarchy_path_exact": entry["row_hierarchy_path_exact"],
                        "row_id": f"r{entry['row_index'] + 1}",
                        "row_label_exact": entry["row_label_exact"],
                        "source_block_ordinal": entry["source_block_ordinal"],
                        "source_movement_role": entry["source_movement_role"],
                    }
                    for entry in block
                ],
                "locator": canonical_clone_v1(locator),
                "lane_population_assignment_receipt": None,
                "period": period,
                "period_assignment_source_kind": "COLUMN_HEADER_PATH",
                "period_semantics_evidence": _period_semantics_evidence_v1(
                    period,
                    source_kind="COLUMN_HEADER_PATH",
                    date_source_surfaces=columns[column_index].get("header_path_exact", []),
                    local_context_surfaces=local_period_context_surfaces,
                ),
                "period_role_hint": None,
                "period_role_hint_source_exact": None,
                "period_role_hint_source_kind": None,
            }
        )
    return result


def _fragments_have_same_full_rank_topology_v1(
    fragments: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> bool:
    if len(fragments) != 2:
        return False
    lane_fingerprints = []
    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_lanes = {
        item["role"] for item in compiled_specs["layout"]["lane_roles"] if not item["optional"]
    }
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    kind_by_role = {item["role"]: item["kind"] for item in movement_specs}
    for fragment in fragments:
        source_cells_by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for item in fragment["cells"]:
            key = (item["lane_role"], item["movement_role"])
            source_cells_by_key.setdefault(key, []).append(item["cell"])
        cells_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
        for key, cells in source_cells_by_key.items():
            if len(cells) == 1:
                cells_by_key[key] = cells[0]
                continue
            if (
                kind_by_role[key[1]] in {"OPENING", "CLOSING"}
                or any(
                    type(cell.get("coefficient")) is not int
                    or cell.get("state") not in {"DASH_ZERO", "RAW_SIGNED_INTEGER"}
                    for cell in cells
                )
            ):
                return False
            cells_by_key[key] = {
                "coefficient": sum(cell["coefficient"] for cell in cells),
                "source_text": " + ".join(cell["source_text"] for cell in cells),
                "state": "AGGREGATED_EXACT_SOURCE_ROWS",
            }
        lanes = {lane for lane, _movement in cells_by_key}
        if not required_lanes <= lanes:
            return False
        for lane_role in lanes:
            if not required_movements <= {
                movement for lane, movement in cells_by_key if lane == lane_role
            }:
                return False
            solution = solve_one_unknown_rollforward_lane_v1(
                {
                    movement: cell
                    for (lane, movement), cell in cells_by_key.items()
                    if lane == lane_role
                },
                movement_specs=movement_specs,
            )
            if solution["status"] not in {"EXACT", "EXACT_ONE_UNKNOWN_INFERRED"}:
                return False
        # Optional movement rows legitimately differ between periods (for
        # example a current-period ``Dự phòng giảm khác`` with no comparator
        # row).  Period identity depends on the same lane population and a
        # closed required opening/provision/closing topology, not identical
        # optional disclosures.
        lane_fingerprints.append(sorted(lanes))
    return lane_fingerprints[0] == lane_fingerprints[1]


def _adjacent_distinct_component_tables_v1(fragments: Sequence[Mapping[str, Any]]) -> bool:
    if len(fragments) != 2:
        return False
    first, second = (item["locator"] for item in fragments)
    return (
        first["page_json_version_id"] == second["page_json_version_id"]
        and first["section_id"] == second["section_id"]
        and int(second["table_id"][1:]) == int(first["table_id"][1:]) + 1
        and first["table_id"] != second["table_id"]
    )


def _unique_ordered_endpoint_chain_period_receipt_v1(
    fragments: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate current/comparative order from one unique endpoint chain.

    Some PDFs visibly caption two adjacent roll-forwards as ``Kỳ này`` and
    ``Kỳ trước`` while the extracted JSON omits only those captions.  We do
    not manufacture them.  Instead, two otherwise undated components may be
    ordered when both are exact, have the same required lane population, and
    the first component's opening equals the second component's closing in
    every lane.  The inverse chain must not also hold.
    """

    if len(fragments) != 2 or not _adjacent_distinct_component_tables_v1(fragments):
        return None
    if any(
        fragment.get("period") is not None or fragment.get("period_role_hint") is not None
        for fragment in fragments
    ):
        return None
    if len({fragment.get("bound_unit") for fragment in fragments}) != 1:
        return None
    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_lanes = {
        item["role"] for item in compiled_specs["layout"]["lane_roles"] if not item["optional"]
    }
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    kind_by_role = {item["role"]: item["kind"] for item in movement_specs}
    lane_axes: list[dict[str, dict[str, Mapping[str, Any]]]] = []
    for fragment in fragments:
        grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for item in fragment.get("cells", []):
            grouped.setdefault((item["lane_role"], item["movement_role"]), []).append(
                item["cell"]
            )
        cells_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
        for key, cells in grouped.items():
            if len(cells) == 1:
                cells_by_key[key] = cells[0]
                continue
            if (
                kind_by_role.get(key[1]) in {"OPENING", "CLOSING"}
                or any(
                    type(cell.get("coefficient")) is not int
                    or cell.get("state") not in {"DASH_ZERO", "RAW_SIGNED_INTEGER"}
                    for cell in cells
                )
            ):
                return None
            cells_by_key[key] = {
                "coefficient": sum(int(cell["coefficient"]) for cell in cells),
                "source_text": " + ".join(str(cell["source_text"]) for cell in cells),
                "state": "AGGREGATED_EXACT_SOURCE_ROWS",
            }
        lanes = {lane for lane, _movement in cells_by_key}
        if not required_lanes <= lanes:
            return None
        lane_axis: dict[str, dict[str, Mapping[str, Any]]] = {}
        for lane_role in lanes:
            cells = {
                movement: cell
                for (lane, movement), cell in cells_by_key.items()
                if lane == lane_role
            }
            if not required_movements <= set(cells):
                return None
            solution = solve_one_unknown_rollforward_lane_v1(
                cells,
                movement_specs=movement_specs,
            )
            # Period ordering must not depend on an inferred or rounded value.
            if solution["status"] != "EXACT":
                return None
            lane_axis[lane_role] = cells
        lane_axes.append(lane_axis)
    if set(lane_axes[0]) != set(lane_axes[1]):
        return None
    opening_role = next(
        item["role"] for item in movement_specs if item["kind"] == "OPENING"
    )
    closing_role = next(
        item["role"] for item in movement_specs if item["kind"] == "CLOSING"
    )

    def chained(left: Mapping[str, Mapping[str, Any]], right: Mapping[str, Mapping[str, Any]]) -> bool:
        return all(
            left[lane][opening_role].get("coefficient")
            == right[lane][closing_role].get("coefficient")
            for lane in left
        )

    if not chained(lane_axes[0], lane_axes[1]) or chained(lane_axes[1], lane_axes[0]):
        return None
    assignments = [
        {
            "assignment_kind": "ORDERED_ENDPOINT_CHAIN_CURRENT_COMPONENT",
            "date": None,
            "document_fiscal_close_year_binding_receipt": None,
            "locator": canonical_clone_v1(fragments[0]["locator"]),
            "narrative_ordinal": None,
            "period_role": "CURRENT_PERIOD",
            "source_exact": None,
            "source_kind": "UNIQUE_ORDERED_ENDPOINT_CHAIN",
        },
        {
            "assignment_kind": "ORDERED_ENDPOINT_CHAIN_COMPARATIVE_COMPONENT",
            "date": None,
            "document_fiscal_close_year_binding_receipt": None,
            "locator": canonical_clone_v1(fragments[1]["locator"]),
            "narrative_ordinal": None,
            "period_role": "COMPARATIVE_PERIOD",
            "source_exact": None,
            "source_kind": "UNIQUE_ORDERED_ENDPOINT_CHAIN",
        },
    ]
    return {
        "assignments": assignments,
        "movement_context_evidence": [],
        "rule": (
            "ORDERED_DISTINCT_MOVEMENT_DATES_TO_ADJACENT_COMPONENTS_OR_"
            "ONE_CURRENT_DATE_PLUS_SYMBOLIC_COMPARATIVE"
        ),
        "status": "ORDERED_TWO_COMPONENT_UNIQUE_ENDPOINT_CHAIN_BOUND",
    }


def _page_local_reporting_date_evidence_v1(
    page_json: Mapping[str, Any],
    *,
    target_locator: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return independent exact reporting-date carriers on the target page.

    A one-block movement table cannot call its sole date ``current`` merely
    because it is the only date decoded.  The date must also occur in a
    reporting title or as the later member of an exact two-date money-column
    table elsewhere on the same immutable page.
    """

    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("roll-forward reporting-date page section axis is invalid")
    evidence = []

    def append_record(*, parsed: date, source_exact: str, source_kind: str) -> None:
        token = next(
            (token for token in reversed(_date_tokens(source_exact)) if token[0] == parsed),
            None,
        )
        if token is None:
            raise _error("roll-forward reporting-date token is absent")
        record = {
            "date": parsed.isoformat(),
            "date_token": token[1],
            "document_fiscal_close_year_binding_receipt": None,
            "narrative_ordinal": None,
            "source_exact": source_exact,
            "source_kind": source_kind,
            "status": "EXACT_PAGE_LOCAL_REPORTING_DATE",
            "year": parsed.year,
        }
        if record not in evidence:
            evidence.append(record)

    for section_ordinal, section in enumerate(sections, start=1):
        if not isinstance(section, Mapping):
            raise _error("roll-forward reporting-date section is invalid")
        title = section.get("title_exact")
        folded_title = _normalized(title)
        title_dates = (
            sorted({token[0] for token in _date_tokens(title)})
            if type(title) is str
            and (_DATE_DMY.search(folded_title) or _DATE_WORDS.search(folded_title))
            else []
        )
        reporting_title = bool(
            folded_title
            and any(
                marker in folded_title
                for marker in (
                    "bao cao tai chinh",
                    "financial statement",
                    "thuyet minh bao cao",
                )
            )
            and any(
                marker in folded_title
                for marker in (
                    "cho giai doan",
                    "ket thuc",
                    "tai ngay",
                    "as at",
                    "for the period",
                    "period ended",
                )
            )
        )
        if reporting_title and title_dates:
            append_record(
                parsed=max(title_dates),
                source_exact=title,
                source_kind="PAGE_REPORTING_SECTION_TITLE",
            )

        tables = section.get("tables")
        if type(tables) is not list:
            raise _error("roll-forward reporting-date table axis is invalid")
        for table_ordinal, table in enumerate(tables, start=1):
            if (
                section_ordinal == int(target_locator["section_id"][1:])
                and table_ordinal == int(target_locator["table_id"][1:])
            ):
                continue
            if not isinstance(table, Mapping):
                raise _error("roll-forward reporting-date table is invalid")
            columns = table.get("columns")
            if type(columns) is not list or len(columns) < 2:
                continue
            dated_columns = []
            for column_ordinal, column in enumerate(columns, start=1):
                if not isinstance(column, Mapping) or column.get("value_kind") != "MONEY":
                    continue
                header = column.get("header_path_exact")
                if type(header) is not list:
                    continue
                source_exact = "\n".join(item for item in header if type(item) is str)
                folded = _normalized(source_exact)
                if not folded or not (
                    _DATE_DMY.search(folded) or _DATE_WORDS.search(folded)
                ):
                    continue
                dates = sorted({token[0] for token in _date_tokens(source_exact)})
                if len(dates) == 1:
                    dated_columns.append((dates[0], column_ordinal, source_exact))
            distinct_dates = sorted({item[0] for item in dated_columns})
            if len(distinct_dates) != 2:
                continue
            previous, current = distinct_dates
            if not (
                previous < current
                and current.year <= previous.year + 1
                and (current - previous).days <= 366
            ):
                continue
            for parsed, _column_ordinal, source_exact in dated_columns:
                if parsed == current:
                    append_record(
                        parsed=parsed,
                        source_exact=source_exact,
                        source_kind="PAGE_TWO_DATE_MONEY_TABLE_CURRENT_COLUMN",
                    )
    return evidence


def _resolve_ordered_period_components_v1(
    fragments: Sequence[dict[str, Any]],
    *,
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    document_fiscal_close_context_evidence: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Bind two adjacent period tables from exact ordered local context.

    Two dated movement narratives form an order-preserving bijection.  With
    only one current date, the second table remains explicitly symbolic; no
    calendar date is fabricated.  That weaker assignment is admitted only
    when both adjacent tables expose the same independently closing topology.
    """

    result = [dict(fragment) for fragment in fragments]
    base_receipt = {
        "assignments": [],
        "movement_context_evidence": [],
        "rule": (
            "ORDERED_DISTINCT_MOVEMENT_DATES_TO_ADJACENT_COMPONENTS_OR_"
            "ONE_CURRENT_DATE_PLUS_SYMBOLIC_COMPARATIVE"
        ),
        "status": "NOT_APPLICABLE",
    }
    explicit_period_rule = "EXACT_COMPONENT_TITLE_OR_SHARED_ROW_HIERARCHY_PERIOD_ROLE"

    def explicit_period_record(fragment: Mapping[str, Any]) -> dict[str, Any] | None:
        source_exact = fragment.get("period_role_hint_source_exact")
        source_kind = fragment.get("period_role_hint_source_kind")
        if (
            type(source_exact) is not str
            or not source_exact
            or source_kind
            not in {
                "SHARED_COLUMN_HEADER_PERIOD_LABEL",
                "SHARED_ROW_HIERARCHY_PERIOD_LABEL",
                "TABLE_TITLE",
            }
            or classify_gemini_json_rollforward_period_role_surface_v1(source_exact)
            != fragment.get("period_role_hint")
        ):
            return None
        period = fragment.get("period")
        period_date = period[0] if period is not None else None
        return {
            "date": period_date.isoformat() if period_date is not None else None,
            "date_token": None,
            "document_fiscal_close_year_binding_receipt": None,
            "narrative_ordinal": None,
            "source_exact": source_exact,
            "source_kind": source_kind,
            "status": "EXACT_EXPLICIT_RELATIVE_PERIOD_ROLE",
            "year": period_date.year if period_date is not None else None,
        }

    explicit_role_axis = [fragment.get("period_role_hint") for fragment in result]
    if (
        len(result) == 2
        and explicit_role_axis == ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"]
        and all(fragment.get("period") is not None for fragment in result)
        and result[0]["period"][0] == result[1]["period"][0]
        and all(
            isinstance(fragment.get("period_semantics_evidence"), Mapping)
            for fragment in result
        )
        and same_typed_json_v1(
            {
                key: result[0].get("period_semantics_evidence", {}).get(key)
                for key in (
                    "date_source_exact_axis",
                    "document_fiscal_close_year_binding_receipt",
                    "period_date",
                    "source_kind",
                )
            },
            {
                key: result[1].get("period_semantics_evidence", {}).get(key)
                for key in (
                    "date_source_exact_axis",
                    "document_fiscal_close_year_binding_receipt",
                    "period_date",
                    "source_kind",
                )
            },
        )
    ):
        current_period = result[0]["period"]
        current_evidence = result[0].get("period_semantics_evidence")
        date_sources = (
            current_evidence.get("date_source_exact_axis")
            if isinstance(current_evidence, Mapping)
            else None
        )
        authenticated_current_period = bool(
            type(date_sources) is list
            and date_sources
            and any(
                (resolved := _movement_period_end_token_v1(source)) is not None
                and resolved[1] != "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
                and resolved[0][0] == current_period[0]
                for source in date_sources
            )
        )
        explicit_evidence = [explicit_period_record(fragment) for fragment in result]
        if authenticated_current_period and all(item is not None for item in explicit_evidence):
            current_evidence = canonical_clone_v1(current_evidence)
            current_role_surface = explicit_evidence[0]["source_exact"]
            if current_role_surface not in current_evidence["local_context_exact_axis"]:
                current_evidence["local_context_exact_axis"].append(current_role_surface)
            result[0]["period_semantics_evidence"] = current_evidence
            result[1]["period"] = None
            result[1]["period_semantics_evidence"] = None
            explicit_evidence[1]["date"] = None
            explicit_evidence[1]["year"] = None
            assignments = [
                {
                    "assignment_kind": "EXPLICIT_RELATIVE_PERIOD_ROLE_TO_COMPONENT",
                    "date": fragment["period"][0].isoformat()
                    if fragment["period"] is not None
                    else None,
                    "document_fiscal_close_year_binding_receipt": None,
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "narrative_ordinal": None,
                    "period_role": fragment["period_role_hint"],
                    "source_exact": evidence["source_exact"],
                    "source_kind": evidence["source_kind"],
                }
                for fragment, evidence in zip(result, explicit_evidence, strict=True)
            ]
            return result, {
                "assignments": assignments,
                "movement_context_evidence": explicit_evidence,
                "rule": explicit_period_rule,
                "status": "EXPLICIT_CURRENT_COMPARATIVE_COMPONENT_ROLES_BOUND",
            }

    if (
        len(result) == 2
        and explicit_role_axis == ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"]
        and all(fragment.get("period") is None for fragment in result)
    ):
        explicit_evidence = [explicit_period_record(fragment) for fragment in result]
        if all(item is not None for item in explicit_evidence):
            assignments = [
                {
                    "assignment_kind": "EXPLICIT_RELATIVE_PERIOD_ROLE_TO_COMPONENT",
                    "date": None,
                    "document_fiscal_close_year_binding_receipt": None,
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "narrative_ordinal": None,
                    "period_role": fragment["period_role_hint"],
                    "source_exact": evidence["source_exact"],
                    "source_kind": evidence["source_kind"],
                }
                for fragment, evidence in zip(result, explicit_evidence, strict=True)
            ]
            return result, {
                "assignments": assignments,
                "movement_context_evidence": explicit_evidence,
                "rule": explicit_period_rule,
                "status": "EXPLICIT_CURRENT_COMPARATIVE_COMPONENT_ROLES_BOUND",
            }
    if len(result) == 1:
        fragment = result[0]
        explicit_evidence = explicit_period_record(fragment)
        if fragment.get("period_role_hint") == "COMPARATIVE_PERIOD":
            return result, {
                "assignments": [],
                "movement_context_evidence": (
                    [explicit_evidence] if explicit_evidence is not None else []
                ),
                "rule": explicit_period_rule,
                "status": "SINGLE_CURRENT_EXPLICIT_COMPARATIVE_ONLY",
            }
        page_json = page_json_by_version.get(fragment["locator"]["page_json_version_id"])
        if not isinstance(page_json, Mapping):
            raise _error("roll-forward single-period context page is absent")
        reporting_evidence = _page_local_reporting_date_evidence_v1(
            page_json,
            target_locator=fragment["locator"],
        )
        receipt = {
            **base_receipt,
            "movement_context_evidence": reporting_evidence,
            "rule": "SINGLE_EXACT_PERIOD_MATCHING_INDEPENDENT_PAGE_LOCAL_REPORTING_DATE",
        }
        reporting_dates = {item["date"] for item in reporting_evidence}
        if not reporting_evidence:
            if (
                fragment.get("period_role_hint") == "CURRENT_PERIOD"
                and explicit_evidence is not None
            ):
                period_evidence = fragment.get("period_semantics_evidence")
                if isinstance(period_evidence, Mapping):
                    period_evidence = canonical_clone_v1(period_evidence)
                    if (
                        explicit_evidence["source_exact"]
                        not in period_evidence["local_context_exact_axis"]
                    ):
                        period_evidence["local_context_exact_axis"].append(
                            explicit_evidence["source_exact"]
                        )
                    fragment["period_semantics_evidence"] = period_evidence
                return result, {
                    "assignments": [
                        {
                            "assignment_kind": "EXPLICIT_RELATIVE_PERIOD_ROLE_TO_COMPONENT",
                            "date": explicit_evidence["date"],
                            "document_fiscal_close_year_binding_receipt": None,
                            "locator": canonical_clone_v1(fragment["locator"]),
                            "narrative_ordinal": None,
                            "period_role": "CURRENT_PERIOD",
                            "source_exact": explicit_evidence["source_exact"],
                            "source_kind": explicit_evidence["source_kind"],
                        }
                    ],
                    "movement_context_evidence": [explicit_evidence],
                    "rule": explicit_period_rule,
                    "status": "SINGLE_CURRENT_EXPLICIT_ROLE_BOUND",
                }
            return result, {**receipt, "status": "SINGLE_CURRENT_REPORTING_CONTEXT_ABSENT"}
        if len(reporting_dates) != 1:
            return result, {**receipt, "status": "SINGLE_CURRENT_REPORTING_CONTEXT_NOT_UNIQUE"}
        fragment_period = fragment.get("period")
        reporting_date = date.fromisoformat(next(iter(reporting_dates)))
        period_evidence = fragment.get("period_semantics_evidence")
        date_sources = (
            period_evidence.get("date_source_exact_axis")
            if isinstance(period_evidence, Mapping)
            else None
        )
        fragment_has_full_date = bool(
            type(date_sources) is list
            and any(
                type(source) is str
                and (_DATE_DMY.search(_normalized(source)) or _DATE_WORDS.search(_normalized(source)))
                for source in date_sources
            )
        )
        same_period = fragment_period is None or fragment_period[0] == reporting_date or (
            not fragment_has_full_date and fragment_period[0].year == reporting_date.year
        )
        if not same_period:
            return result, {**receipt, "status": "SINGLE_CURRENT_TABLE_PERIOD_CONFLICTING"}
        selected_evidence = reporting_evidence[0]
        fragment["period"] = (reporting_date, selected_evidence["date_token"])
        fragment["period_role_hint"] = "CURRENT_PERIOD"
        fragment["period_semantics_evidence"] = _period_semantics_evidence_v1(
            fragment["period"],
            source_kind=selected_evidence["source_kind"],
            date_source_surfaces=[item["source_exact"] for item in reporting_evidence],
            local_context_surfaces=[
                *(
                    period_evidence.get("local_context_exact_axis", [])
                    if isinstance(period_evidence, Mapping)
                    else []
                ),
                *(item["source_exact"] for item in reporting_evidence),
            ],
        )
        assignment = {
            "assignment_kind": "PAGE_LOCAL_REPORTING_DATE_TO_SINGLE_COMPONENT",
            "date": reporting_date.isoformat(),
            "document_fiscal_close_year_binding_receipt": None,
            "locator": canonical_clone_v1(fragment["locator"]),
            "narrative_ordinal": None,
            "period_role": "CURRENT_PERIOD",
            "source_exact": selected_evidence["source_exact"],
            "source_kind": selected_evidence["source_kind"],
        }
        return result, {
            **receipt,
            "assignments": [assignment],
            "status": "SINGLE_CURRENT_PERIOD_CONTEXT_BOUND",
        }
    if not _adjacent_distinct_component_tables_v1(result):
        return result, base_receipt
    locators = [fragment["locator"] for fragment in result]
    version_id = locators[0]["page_json_version_id"]
    page_json = page_json_by_version.get(version_id)
    if not isinstance(page_json, Mapping):
        raise _error("roll-forward period context page is absent")
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("roll-forward period context section axis is invalid")
    section_ordinal = int(locators[0]["section_id"][1:])
    section = sections[section_ordinal - 1]
    if not isinstance(section, Mapping):
        raise _error("roll-forward period context section is invalid")
    narratives = section.get("narratives_exact")
    if type(narratives) is not list:
        raise _error("roll-forward period context narrative axis is invalid")
    movement_aliases = compiled_specs["layout"]["period_movement_context_aliases"]
    owner_text = " ".join(
        value for value in [section.get("title_exact"), *narratives] if type(value) is str
    )
    if not _matches_alias(
        owner_text,
        compiled_specs["layout"]["population_policy"]["owner_aliases"],
    ):
        return result, {**base_receipt, "status": "LOCAL_OWNER_SCOPE_NOT_VISIBLE"}
    movement_evidence = []

    def period_context_record(
        *,
        source_exact: Any,
        source_kind: str,
        narrative_ordinal: int | None,
    ) -> dict[str, Any] | None:
        resolved = _movement_period_end_token_v1(source_exact)
        full_date_tokens = _full_date_token_spans_v1(source_exact)
        unique_dates = {token[0] for token in full_date_tokens}
        base = {
            "date": None,
            "date_token": None,
            "document_fiscal_close_year_binding_receipt": None,
            "narrative_ordinal": narrative_ordinal,
            "source_exact": source_exact,
            "source_kind": source_kind,
            "year": None,
        }
        if resolved is None:
            return (
                {
                    **base,
                    "status": "AMBIGUOUS_MULTIPLE_DATES",
                }
                if len(unique_dates) > 1
                else None
            )
        selected_token, derivation_kind = resolved
        selected_date = selected_token[0]
        if derivation_kind == "EXACT_FULL_DATE":
            return {
                **base,
                "date": selected_date.isoformat(),
                "date_token": selected_token[1],
                "status": "EXACT_ONE_DATE",
                "year": selected_date.year,
            }
        if derivation_kind in {
            "EXACT_CUMULATIVE_MONTH_END_GRAMMAR",
            "EXACT_DATE_RANGE_END_GRAMMAR",
            "EXACT_QUARTER_END_GRAMMAR",
        }:
            return {
                **base,
                "date": selected_date.isoformat(),
                "date_token": selected_token[1],
                "status": "EXACT_PERIOD_END_GRAMMAR",
                "year": selected_date.year,
            }
        binding = _document_fiscal_close_year_binding_receipt_v1(
            document_fiscal_close_context_evidence,
            year=selected_date.year,
        )
        if binding is None:
            return {
                **base,
                "date_token": selected_token[1],
                "status": "EXACT_ONE_YEAR_UNBOUND",
                "year": selected_date.year,
            }
        year_context = binding["year_context"]
        bound_date = date(selected_date.year, year_context["month"], year_context["day"])
        return {
            **base,
            "date": bound_date.isoformat(),
            "date_token": selected_token[1],
            "document_fiscal_close_year_binding_receipt": binding,
            "status": "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
            "year": selected_date.year,
        }

    for narrative_ordinal, source_exact in enumerate(narratives, start=1):
        if not (
            _matches_alias(source_exact, movement_aliases)
            or _matches_alias(
                source_exact,
                compiled_specs["layout"]["population_policy"]["owner_aliases"],
            )
        ):
            continue
        record = period_context_record(
            source_exact=source_exact,
            source_kind="SELECTED_SECTION_MOVEMENT_NARRATIVE",
            narrative_ordinal=narrative_ordinal,
        )
        if record is not None:
            movement_evidence.append(record)
    exact_statuses = {
        "EXACT_ONE_DATE",
        "EXACT_PAGE_LOCAL_REPORTING_DATE",
        "EXACT_PERIOD_END_GRAMMAR",
        "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
    }
    exact_movement = [item for item in movement_evidence if item["status"] in exact_statuses]
    if not exact_movement:
        context_surfaces = [("SELECTED_SECTION_TITLE", section.get("title_exact"))]
        if section_ordinal > 1:
            previous = sections[section_ordinal - 2]
            if isinstance(previous, Mapping):
                context_surfaces.insert(
                    0,
                    ("IMMEDIATELY_PRECEDING_SECTION_TITLE", previous.get("title_exact")),
                )
        for source_kind, source_exact in context_surfaces:
            record = period_context_record(
                source_exact=source_exact,
                source_kind=source_kind,
                narrative_ordinal=None,
            )
            if record is not None and record["status"] in exact_statuses:
                exact_movement.append(record)
                movement_evidence.append(record)
    # A selected roll-forward table can lose its visually adjacent caption in
    # Gemini JSON while a separate two-date money table on the same page still
    # authenticates the reporting endpoint.  Reuse that source-bound page
    # evidence for the current component; the comparative component remains
    # symbolic and is admitted only by the strict full-rank topology gate
    # below.  This is deliberately page-local and never filename-derived.
    if not exact_movement:
        page_reporting_evidence = _page_local_reporting_date_evidence_v1(
            page_json,
            target_locator=result[0]["locator"],
        )
        reporting_dates = {item["date"] for item in page_reporting_evidence}
        if len(reporting_dates) == 1:
            exact_movement.extend(page_reporting_evidence)
            movement_evidence.extend(page_reporting_evidence)
    receipt = {**base_receipt, "movement_context_evidence": movement_evidence}

    # Two adjacent movement tables commonly carry only ``trong nam YYYY`` in
    # their own titles.  That bare year is not itself a reporting date: bind
    # each year only when an independent exact page reporting date or the
    # authenticated document fiscal-close evidence proves the endpoint.  In
    # particular this keeps an interim current period (for example 30-Jun)
    # from being silently coerced to 31-Dec while still authenticating the
    # preceding fiscal-year comparison.
    def bare_year_fragment_source(
        fragment: Mapping[str, Any],
    ) -> tuple[int, str] | None:
        period = fragment.get("period")
        evidence = fragment.get("period_semantics_evidence")
        if period is None or not isinstance(evidence, Mapping):
            return None
        sources = evidence.get("date_source_exact_axis")
        if type(sources) is not list or not sources:
            return None
        resolved = [
            _movement_period_end_token_v1(source)
            for source in sources
            if type(source) is str
        ]
        if len(resolved) != len(sources) or any(
            item is None
            or item[1] != "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
            or item[0][0].year != period[0].year
            for item in resolved
        ):
            return None
        return period[0].year, sources[0]

    bare_sources = [bare_year_fragment_source(fragment) for fragment in result]
    if (
        len(result) == 2
        and all(item is not None for item in bare_sources)
        and bare_sources[0][0] == bare_sources[1][0] + 1
    ):
        page_reporting_evidence = _page_local_reporting_date_evidence_v1(
            page_json,
            target_locator=result[0]["locator"],
        )
        authorities_by_year: dict[int, list[dict[str, Any]]] = {}
        for record in [*exact_movement, *page_reporting_evidence]:
            if record.get("status") in exact_statuses | {"EXACT_PAGE_LOCAL_REPORTING_DATE"}:
                authorities_by_year.setdefault(record["year"], []).append(record)
        resolution_plans = []
        resolved_records = []
        for ordinal, (fragment, bare_source) in enumerate(
            zip(result, bare_sources, strict=True)
        ):
            year, source_exact = bare_source
            binding = _document_fiscal_close_year_binding_receipt_v1(
                document_fiscal_close_context_evidence,
                year=year,
            )
            candidates = list(authorities_by_year.get(year, []))
            if binding is not None:
                year_context = binding["year_context"]
                try:
                    bound_date = date(year, year_context["month"], year_context["day"])
                except (KeyError, TypeError, ValueError):
                    candidates = []
                else:
                    candidates.append(
                        {
                            "date": bound_date.isoformat(),
                            "date_token": str(year),
                            "document_fiscal_close_year_binding_receipt": binding,
                            "narrative_ordinal": None,
                            "source_exact": source_exact,
                            "source_kind": fragment["period_assignment_source_kind"],
                            "status": "EXACT_ONE_YEAR_BOUND_TO_DOCUMENT_FISCAL_CLOSE_CONTEXT",
                            "year": year,
                        }
                    )
            candidate_dates = {record["date"] for record in candidates}
            if not candidates or len(candidate_dates) != 1:
                break
            authority = candidates[0]
            period_date = date.fromisoformat(authority["date"])
            existing_evidence = fragment["period_semantics_evidence"]
            local_context = [
                *existing_evidence.get("local_context_exact_axis", []),
                *(record["source_exact"] for record in candidates),
            ]
            resolution_plans.append(
                (ordinal, fragment, authority, period_date, local_context)
            )
            resolved_records.append(authority)
        if len(resolution_plans) == 2:
            assignments = []
            for ordinal, fragment, authority, period_date, local_context in resolution_plans:
                fragment["period"] = (period_date, authority["date_token"])
                fragment["period_semantics_evidence"] = _period_semantics_evidence_v1(
                    fragment["period"],
                    source_kind=authority["source_kind"],
                    date_source_surfaces=[authority["source_exact"]],
                    local_context_surfaces=local_context,
                    document_fiscal_close_year_binding_receipt=authority[
                        "document_fiscal_close_year_binding_receipt"
                    ],
                )
                fragment["period_role_hint"] = (
                    "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
                )
                assignments.append(
                    {
                        "assignment_kind": "INDEPENDENT_DATE_AUTHORITY_TO_BARE_YEAR_COMPONENT",
                        "date": period_date.isoformat(),
                        "document_fiscal_close_year_binding_receipt": canonical_clone_v1(
                            authority["document_fiscal_close_year_binding_receipt"]
                        ),
                        "locator": canonical_clone_v1(fragment["locator"]),
                        "narrative_ordinal": authority["narrative_ordinal"],
                        "period_role": fragment["period_role_hint"],
                        "source_exact": authority["source_exact"],
                        "source_kind": authority["source_kind"],
                    }
                )
            dates = [fragment["period"][0] for fragment in result]
            if dates[0] > dates[1]:
                return result, {
                    **receipt,
                    "assignments": assignments,
                    "movement_context_evidence": resolved_records,
                    "status": "ORDERED_TWO_BARE_YEAR_COMPONENTS_CONTEXT_BOUND",
                }
    if len(exact_movement) == 2 and len(movement_evidence) == 2:
        dates = [date.fromisoformat(item["date"]) for item in exact_movement]
        if dates[0] <= dates[1] or len(set(dates)) != 2:
            return result, {**receipt, "status": "AMBIGUOUS_OR_REVERSED_CONTEXT_DATES"}
        assignments = []
        for ordinal, (fragment, period_date, evidence) in enumerate(
            zip(result, dates, exact_movement, strict=True)
        ):
            if fragment["period"] is not None and fragment["period"][0] != period_date:
                return result, {**receipt, "status": "CONFLICTING_TABLE_PERIOD_EVIDENCE"}
            fragment["period"] = (period_date, evidence["date_token"])
            fragment["period_semantics_evidence"] = _period_semantics_evidence_v1(
                fragment["period"],
                source_kind=evidence["source_kind"],
                date_source_surfaces=[evidence["source_exact"]],
                local_context_surfaces=[evidence["source_exact"]],
                document_fiscal_close_year_binding_receipt=evidence[
                    "document_fiscal_close_year_binding_receipt"
                ],
            )
            fragment["period_role_hint"] = (
                "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
            )
            assignments.append(
                {
                    "assignment_kind": "ORDERED_MOVEMENT_NARRATIVE_TO_COMPONENT",
                    "date": period_date.isoformat(),
                    "document_fiscal_close_year_binding_receipt": canonical_clone_v1(
                        evidence["document_fiscal_close_year_binding_receipt"]
                    ),
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "narrative_ordinal": evidence["narrative_ordinal"],
                    "period_role": fragment["period_role_hint"],
                    "source_exact": evidence["source_exact"],
                    "source_kind": evidence["source_kind"],
                }
            )
        return result, {
            **receipt,
            "assignments": assignments,
            "status": "ORDERED_TWO_DATE_CONTEXT_BOUND",
        }
    if not movement_evidence:
        endpoint_chain_receipt = _unique_ordered_endpoint_chain_period_receipt_v1(
            result,
            compiled_specs=compiled_specs,
        )
        if endpoint_chain_receipt is not None:
            result[0]["period"] = None
            result[0]["period_semantics_evidence"] = None
            result[0]["period_role_hint"] = "CURRENT_PERIOD"
            result[1]["period"] = None
            result[1]["period_semantics_evidence"] = None
            result[1]["period_role_hint"] = "COMPARATIVE_PERIOD"
            return result, endpoint_chain_receipt
    if len(exact_movement) != 1 or len(movement_evidence) > 1:
        return result, {**receipt, "status": "CONTEXT_DATE_AXIS_NOT_UNIQUE"}
    if (
        not _fragments_have_same_full_rank_topology_v1(result, compiled_specs=compiled_specs)
        or len({fragment["bound_unit"] for fragment in result}) != 1
    ):
        return result, {**receipt, "status": "SYMBOLIC_COMPARATIVE_PRECONDITIONS_FAILED"}
    current_date = date.fromisoformat(exact_movement[0]["date"])
    if result[0]["period"] is not None and result[0]["period"][0] != current_date:
        return result, {**receipt, "status": "CONFLICTING_TABLE_PERIOD_EVIDENCE"}
    if result[1]["period"] is not None and not (
        result[1]["period"][0] == current_date
        and result[1]["period_assignment_source_kind"] == "SELECTED_SECTION_CONTEXT"
    ):
        return result, {**receipt, "status": "UNEXPECTED_SECOND_TABLE_PERIOD_EVIDENCE"}
    result[0]["period"] = (current_date, exact_movement[0]["date_token"])
    result[0]["period_semantics_evidence"] = _period_semantics_evidence_v1(
        result[0]["period"],
        source_kind=exact_movement[0]["source_kind"],
        date_source_surfaces=[exact_movement[0]["source_exact"]],
        local_context_surfaces=[exact_movement[0]["source_exact"]],
        document_fiscal_close_year_binding_receipt=exact_movement[0][
            "document_fiscal_close_year_binding_receipt"
        ],
    )
    result[0]["period_role_hint"] = "CURRENT_PERIOD"
    result[1]["period"] = None
    result[1]["period_semantics_evidence"] = None
    result[1]["period_role_hint"] = "COMPARATIVE_PERIOD"
    assignments = [
        {
            "assignment_kind": "VISIBLE_CURRENT_CONTEXT_TO_FIRST_COMPONENT",
            "date": current_date.isoformat(),
            "document_fiscal_close_year_binding_receipt": canonical_clone_v1(
                exact_movement[0]["document_fiscal_close_year_binding_receipt"]
            ),
            "locator": canonical_clone_v1(result[0]["locator"]),
            "narrative_ordinal": exact_movement[0]["narrative_ordinal"],
            "period_role": "CURRENT_PERIOD",
            "source_exact": exact_movement[0]["source_exact"],
            "source_kind": exact_movement[0]["source_kind"],
        },
        {
            "assignment_kind": "SYMBOLIC_UNDATED_COMPARATIVE_SECOND_COMPONENT",
            "date": None,
            "document_fiscal_close_year_binding_receipt": None,
            "locator": canonical_clone_v1(result[1]["locator"]),
            "narrative_ordinal": None,
            "period_role": "COMPARATIVE_PERIOD",
            "source_exact": None,
            "source_kind": "ORDERED_ADJACENT_COMPONENT_TOPOLOGY",
        },
    ]
    return result, {
        **receipt,
        "assignments": assignments,
        "status": "CURRENT_PLUS_SYMBOLIC_COMPARATIVE_BOUND",
    }


def _assign_period_column_lane_roles(
    records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[int, str], list[dict[str, Any]], list[str]]:
    """Bind lane tables through one local, ordered, one-to-one assignment."""

    if not records:
        return {}, [], []
    declared_order = [item["role"] for item in compiled_specs["layout"]["lane_roles"]]
    candidates = []
    for ordinal, record in enumerate(records):
        classification = record["classification"]
        explicit = classification["context_lane_role"]
        axis = (
            [explicit]
            if explicit is not None
            else list(classification["context_lane_candidates_in_source_order"])
        )
        if (
            not axis
            or classification["context_reset_visible"]
            or classification["structural_hard_negative_visible"]
        ):
            return {}, [], ["ROLLFORWARD_LOCAL_LANE_ASSIGNMENT_EVIDENCE_INCOMPLETE"]
        candidates.append((ordinal, axis))

    assignments: list[dict[int, str]] = []

    def assign(index: int, used: frozenset[str], current: dict[int, str]) -> None:
        if index == len(candidates):
            assignments.append(dict(current))
            return
        ordinal, roles = candidates[index]
        for role in roles:
            if role not in used:
                current[ordinal] = role
                assign(index + 1, used | {role}, current)
                current.pop(ordinal)

    assign(0, frozenset(), {})
    assignment_kind = "UNIQUE_LOCAL_CANDIDATE_ASSIGNMENT"
    selected: dict[int, str] | None = assignments[0] if len(assignments) == 1 else None
    if selected is None and all(
        record["classification"]["context_lane_role"] is None for record in records
    ):
        axes = [roles for _ordinal, roles in candidates]
        same_local_section = (
            len(
                {
                    (
                        record["locator"]["page_json_version_id"],
                        record["locator"]["section_id"],
                    )
                    for record in records
                }
            )
            == 1
        )
        expected_order = sorted(axes[0], key=declared_order.index) if axes else []
        if (
            same_local_section
            and all(axis == axes[0] for axis in axes)
            and len(axes[0]) == len(records)
            and len(axes[0]) == len(set(axes[0]))
            and axes[0] == expected_order
        ):
            selected = dict(enumerate(axes[0]))
            assignment_kind = "ORDERED_LOCAL_NARRATIVE_TO_TABLE_ASSIGNMENT"
    if selected is None:
        return {}, [], ["ROLLFORWARD_LOCAL_LANE_ASSIGNMENT_NOT_UNIQUE"]
    receipts = [
        {
            "assignment_kind": assignment_kind,
            "assigned_lane_role": selected[ordinal],
            "candidate_lane_roles_in_source_order": list(candidates[ordinal][1]),
            "locator": canonical_clone_v1(records[ordinal]["locator"]),
        }
        for ordinal in range(len(records))
    ]
    return selected, receipts, []


def _region_axis(regions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = {
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    result = []
    for region in regions:
        if type(region) is not dict or set(region) != fields:
            raise _error("roll-forward component region locator is invalid")
        if (
            type(region["document_id"]) is not str
            or _DOCUMENT_ID.fullmatch(region["document_id"]) is None
            or type(region["source_logical_name"]) is not str
            or not region["source_logical_name"].strip()
            or type(region["source_sha256"]) is not str
            or _SOURCE_SHA256.fullmatch(region["source_sha256"]) is None
            or type(region["page_json_version_id"]) is not str
            or _PAGE_JSON_VERSION_ID.fullmatch(region["page_json_version_id"]) is None
            or type(region["physical_page"]) is not int
            or region["physical_page"] <= 0
            or type(region["section_id"]) is not str
            or re.fullmatch(r"s[1-9][0-9]*", region["section_id"]) is None
            or type(region["table_id"]) is not str
            or re.fullmatch(r"t[1-9][0-9]*", region["table_id"]) is None
        ):
            raise _error("roll-forward component region identity is invalid")
        result.append(canonical_clone_v1(region))
    ordered = sorted(
        result,
        key=lambda item: (
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
            item["page_json_version_id"],
        ),
    )
    if ordered != result or len({canonical_json_sha256_v1(item) for item in result}) != len(result):
        raise _error("roll-forward component region axis is unordered or duplicate")
    # Three physical regions are needed only when two of them are the
    # authenticated row-split halves of one logical component and the third
    # is the other period component.  The evaluator enforces that logical
    # reduction after loading the exact page JSON.
    if len(result) not in {1, 2, 3} or result[-1]["physical_page"] - result[0]["physical_page"] > 1:
        raise _error("roll-forward component region span is out of bounds")
    source_axis = {
        (
            item["document_id"],
            item["source_logical_name"],
            item["source_sha256"],
        )
        for item in result
    }
    if len(source_axis) != 1:
        raise _error("roll-forward component regions cross one immutable document source")
    version_by_page: dict[int, str] = {}
    for item in result:
        previous = version_by_page.setdefault(item["physical_page"], item["page_json_version_id"])
        if previous != item["page_json_version_id"]:
            raise _error("roll-forward component page selects multiple JSON versions")
    return result


def _ordered_page_version_axis(
    region_axis: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    seen: set[int] = set()
    for item in region_axis:
        if item["physical_page"] in seen:
            continue
        seen.add(item["physical_page"])
        result.append(
            {
                "page_json_version_id": item["page_json_version_id"],
                "physical_page": item["physical_page"],
            }
        )
    return result


def build_gemini_json_rollforward_region_query_receipt_v1(
    regions: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Bind one query result to one immutable source and exact ordered regions."""

    region_axis = _region_axis(regions)
    first = region_axis[0]
    material = {
        "authentication_kind": QUERY_RECEIPT_AUTHENTICATION_KIND,
        "document_id": first["document_id"],
        "exact_region_count": len(region_axis),
        "format_version": QUERY_RECEIPT_FORMAT_VERSION,
        "ordered_page_json_version_axis_sha256": canonical_json_sha256_v1(
            _ordered_page_version_axis(region_axis)
        ),
        "ordered_region_axis_sha256": canonical_json_sha256_v1(region_axis),
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
    }
    return {
        **material,
        "query_receipt_id": "gjfrqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _validated_region_query_receipt_v1(
    value: Any, *, region_axis: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    expected = build_gemini_json_rollforward_region_query_receipt_v1(
        [canonical_clone_v1(item) for item in region_axis]
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("roll-forward query receipt does not authenticate exact regions")
    return canonical_clone_v1(expected)


def _validated_document_unit_context_evidence_v1(
    value: Any,
    *,
    document_id: str,
    source_logical_name: str,
    source_sha256: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = {
        "canonical_unit",
        "canonical_units",
        "distinct_page_count",
        "document_id",
        "document_ordinal",
        "evidence",
        "evidence_axis_sha256",
        "minimum_distinct_page_count",
        "rule",
        "source_logical_name",
        "source_sha256",
        "status",
    }
    evidence_fields = {
        "canonical_unit",
        "column_id",
        "currency",
        "magnitude_power10",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_kind",
        "table_id",
        "text_exact",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("document_id") != document_id
        or value.get("source_logical_name") != source_logical_name
        or value.get("source_sha256") != source_sha256
        or type(value.get("document_ordinal")) is not int
        or value["document_ordinal"] <= 0
        or type(value.get("evidence")) is not list
        or value.get("minimum_distinct_page_count") != 2
        or value.get("rule")
        != (
            "SELECTED_PAGE_VERSION_ONLY_EXPLICIT_TABLE_UNIT_MAGNITUDE_AND_"
            "CURRENCY_TWO_PAGE_UNIQUE_CANONICAL_MONEY_UNIT_CONSENSUS"
        )
    ):
        raise _error("roll-forward document-unit context identity is invalid")
    binding_by_unit = {
        item["canonical_unit"]: item for item in compiled_specs["layout"]["unit_bindings"]
    }
    evidence = value["evidence"]
    expected_order = sorted(
        evidence,
        key=lambda item: (
            item.get("selected_page_ordinal", 0),
            int(item.get("section_id", "s0")[1:]),
            int(item.get("table_id", "t0")[1:]),
            item.get("source_kind", ""),
            item.get("column_id") or "",
            item.get("text_exact", ""),
            item.get("canonical_unit", ""),
        ),
    )
    if expected_order != evidence or len(
        {canonical_json_sha256_v1(item) for item in evidence}
    ) != len(evidence):
        raise _error("roll-forward document-unit evidence axis is unordered")
    for item in evidence:
        binding = binding_by_unit.get(item.get("canonical_unit"))
        if (
            type(item) is not dict
            or set(item) != evidence_fields
            or binding is None
            or not binding["document_consensus_eligible"]
            or item.get("currency") != binding["currency"]
            or item.get("magnitude_power10") != binding["magnitude_power10"]
            or type(item.get("page_json_version_id")) is not str
            or _PAGE_JSON_VERSION_ID.fullmatch(item["page_json_version_id"]) is None
            or type(item.get("physical_page")) is not int
            or item["physical_page"] <= 0
            or type(item.get("section_id")) is not str
            or not re.fullmatch(r"s[1-9][0-9]*", item["section_id"])
            or type(item.get("table_id")) is not str
            or not re.fullmatch(r"t[1-9][0-9]*", item["table_id"])
            or item.get("source_kind") != "TABLE_UNIT"
            or item.get("column_id") is not None
            or type(item.get("text_exact")) is not str
            or not item["text_exact"]
            or item["canonical_unit"]
            not in _canonical_money_units_from_surface_v1(
                item["text_exact"],
                compiled_specs=compiled_specs,
                document_consensus_only=True,
            )
        ):
            raise _error("roll-forward document-unit evidence is invalid")
    canonical_units = sorted({item["canonical_unit"] for item in evidence})
    distinct_page_count = len(
        {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
    )
    status = (
        "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        if len(canonical_units) == 1 and distinct_page_count >= 2
        else "CONFLICTING_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
        if len(canonical_units) > 1
        else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_MONEY_UNIT_EVIDENCE"
    )
    if (
        value.get("canonical_units") != canonical_units
        or value.get("canonical_unit")
        != (canonical_units[0] if status.startswith("UNIQUE_") else None)
        or value.get("distinct_page_count") != distinct_page_count
        or value.get("status") != status
        or value.get("evidence_axis_sha256") != canonical_json_sha256_v1(evidence)
    ):
        raise _error("roll-forward document-unit consensus receipt drifted")
    return canonical_clone_v1(value)


def _validated_document_fiscal_close_context_evidence_v1(
    value: Any,
    *,
    document_id: str,
    source_logical_name: str,
    source_sha256: str,
) -> dict[str, Any] | None:
    """Validate exact-year fiscal-close carriers projected from selected JSON versions."""

    if value is None:
        return None
    fields = {
        "document_id",
        "document_ordinal",
        "rule",
        "source_logical_name",
        "source_sha256",
        "year_context_axis_sha256",
        "year_contexts",
    }
    year_fields = {
        "day",
        "distinct_page_count",
        "evidence",
        "evidence_axis_sha256",
        "minimum_distinct_page_count",
        "month",
        "month_day_axis",
        "status",
        "year",
    }
    evidence_fields = {
        "column_id",
        "date",
        "day",
        "month",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_kind",
        "table_id",
        "text_exact",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("document_id") != document_id
        or value.get("source_logical_name") != source_logical_name
        or value.get("source_sha256") != source_sha256
        or type(value.get("document_ordinal")) is not int
        or value["document_ordinal"] <= 0
        or value.get("rule")
        != (
            "SELECTED_PAGE_VERSION_ONLY_ANNUAL_REPORTING_TITLE_OR_BALANCE_"
            "SHEET_COMPARATIVE_DATE_EXACT_YEAR_TWO_PAGE_UNIQUE_FISCAL_"
            "CLOSE_MONTH_DAY_CONSENSUS"
        )
        or type(value.get("year_contexts")) is not list
    ):
        raise _error("roll-forward document fiscal-close context identity is invalid")
    year_contexts = value["year_contexts"]
    if any(
        type(item) is not dict or type(item.get("year")) is not int for item in year_contexts
    ) or [item["year"] for item in year_contexts] != sorted(
        {item["year"] for item in year_contexts}
    ):
        raise _error("roll-forward document fiscal-close year axis is unordered")

    def annual_reporting_surface(surface: str) -> bool:
        folded = _normalized(surface)
        annual = bool(
            ("nam tai chinh" in folded and "ket thuc" in folded)
            or re.search(r"\bnam (?:duoc )?ket thuc\b", folded)
            or "financial year ended" in folded
            or "year ended" in folded
        )
        reporting = any(
            marker in folded
            for marker in ("bao cao tai chinh", "thuyet minh bao cao", "financial statement")
        )
        return annual and (reporting or "nam tai chinh" in folded)

    def annual_reporting_dates(surface: str) -> set[date]:
        folded = _normalized(surface)
        if not annual_reporting_surface(surface):
            return set()
        grammar = re.compile(
            r"(?:nam tai chinh|nam(?: duoc)?|financial year|year)\s+"
            r"(?:duoc\s+)?(?:ket thuc(?:\s+vao)?(?:\s+ngay)?|ended(?:\s+on)?)\s*$"
        )
        governed = set()
        for match in [*_DATE_DMY.finditer(folded), *_DATE_WORDS.finditer(folded)]:
            if grammar.search(folded[: match.start()]) is None:
                continue
            try:
                governed.add(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
            except ValueError:
                continue
        return governed

    for year_context in year_contexts:
        if (
            type(year_context) is not dict
            or set(year_context) != year_fields
            or type(year_context.get("year")) is not int
            or year_context["year"] < 1900
            or type(year_context.get("evidence")) is not list
            or year_context.get("minimum_distinct_page_count") != 2
            or type(year_context.get("month_day_axis")) is not list
        ):
            raise _error("roll-forward document fiscal-close year context is invalid")
        evidence = year_context["evidence"]
        expected_order = sorted(
            evidence,
            key=lambda item: (
                item.get("selected_page_ordinal", 0),
                int(item.get("section_id", "s0")[1:]),
                int(item.get("table_id", "t0")[1:]) if item.get("table_id") else 0,
                item.get("column_id") or "",
                item.get("source_kind", ""),
                item.get("date", ""),
                item.get("text_exact", ""),
            ),
        )
        if expected_order != evidence or len(
            {canonical_json_sha256_v1(item) for item in evidence}
        ) != len(evidence):
            raise _error("roll-forward document fiscal-close evidence axis is unordered")
        for item in evidence:
            if (
                type(item) is not dict
                or set(item) != evidence_fields
                or type(item.get("page_json_version_id")) is not str
                or _PAGE_JSON_VERSION_ID.fullmatch(item["page_json_version_id"]) is None
                or type(item.get("physical_page")) is not int
                or item["physical_page"] <= 0
                or type(item.get("section_id")) is not str
                or re.fullmatch(r"s[1-9][0-9]*", item["section_id"]) is None
                or type(item.get("selected_page_ordinal")) is not int
                or item["selected_page_ordinal"] <= 0
                or type(item.get("text_exact")) is not str
                or not item["text_exact"]
                or item.get("source_kind")
                not in {
                    "ANNUAL_REPORTING_SECTION_TITLE",
                    "BALANCE_SHEET_COMPARATIVE_DATE_COLUMN",
                }
            ):
                raise _error("roll-forward document fiscal-close evidence is invalid")
            try:
                parsed = date.fromisoformat(item["date"])
            except (KeyError, TypeError, ValueError) as exc:
                raise _error("roll-forward document fiscal-close date is invalid") from exc
            folded = _normalized(item["text_exact"])
            exact_full_dates = {
                token[0]
                for token in _date_tokens(item["text_exact"])
                if _DATE_DMY.search(folded) or _DATE_WORDS.search(folded)
            }
            if (
                parsed.year != year_context["year"]
                or item.get("month") != parsed.month
                or item.get("day") != parsed.day
                or parsed not in exact_full_dates
                or (
                    item["source_kind"] == "ANNUAL_REPORTING_SECTION_TITLE"
                    and (
                        item.get("table_id") is not None
                        or item.get("column_id") is not None
                        or parsed not in annual_reporting_dates(item["text_exact"])
                    )
                )
                or (
                    item["source_kind"] == "BALANCE_SHEET_COMPARATIVE_DATE_COLUMN"
                    and (
                        type(item.get("table_id")) is not str
                        or re.fullmatch(r"t[1-9][0-9]*", item["table_id"]) is None
                        or type(item.get("column_id")) is not str
                        or re.fullmatch(r"c[1-9][0-9]*", item["column_id"]) is None
                    )
                )
            ):
                raise _error("roll-forward document fiscal-close carrier is invalid")
        month_day_axis = sorted({(item["month"], item["day"]) for item in evidence})
        distinct_page_count = len(
            {(item["physical_page"], item["page_json_version_id"]) for item in evidence}
        )
        status = (
            "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
            if len(month_day_axis) == 1 and distinct_page_count >= 2
            else "CONFLICTING_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_EVIDENCE"
            if len(month_day_axis) > 1
            else "INSUFFICIENT_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_EVIDENCE"
        )
        if (
            year_context.get("month_day_axis")
            != [{"day": day, "month": month} for month, day in month_day_axis]
            or year_context.get("month")
            != (month_day_axis[0][0] if status.startswith("UNIQUE_") else None)
            or year_context.get("day")
            != (month_day_axis[0][1] if status.startswith("UNIQUE_") else None)
            or year_context.get("distinct_page_count") != distinct_page_count
            or year_context.get("status") != status
            or year_context.get("evidence_axis_sha256") != canonical_json_sha256_v1(evidence)
        ):
            raise _error("roll-forward document fiscal-close year receipt drifted")
    if value.get("year_context_axis_sha256") != canonical_json_sha256_v1(year_contexts):
        raise _error("roll-forward document fiscal-close context receipt drifted")
    return canonical_clone_v1(value)


def _document_fiscal_close_year_binding_receipt_v1(
    context: Mapping[str, Any] | None, *, year: int
) -> dict[str, Any] | None:
    if context is None:
        return None
    year_contexts = [item for item in context["year_contexts"] if item["year"] == year]
    if (
        len(year_contexts) != 1
        or year_contexts[0]["status"] != "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
    ):
        return None
    return {
        "context_rule": context["rule"],
        "document_id": context["document_id"],
        "document_ordinal": context["document_ordinal"],
        "rule": (
            "EXACT_BARE_PERIOD_YEAR_BOUND_TO_AUTHENTICATED_SELECTED_VERSION_"
            "DOCUMENT_FISCAL_CLOSE_YEAR_CONTEXT"
        ),
        "source_logical_name": context["source_logical_name"],
        "source_sha256": context["source_sha256"],
        "year_context": canonical_clone_v1(year_contexts[0]),
    }


def _endpoint_source_receipt(item: Mapping[str, Any]) -> dict[str, Any]:
    """Keep one endpoint's exact source and solved-cell provenance."""

    return canonical_clone_v1(
        {
            key: item[key]
            for key in (
                "assignment_kind",
                "block_ordinal",
                "bound_unit",
                "cell",
                "column_ordinal",
                "endpoint_date",
                "locator",
                "movement_role",
                "period_date",
                "period_semantics_evidence",
                "period_role",
                "row_hierarchy_path_exact",
                "row_id",
                "row_label_exact",
                "source_block_ordinal",
                "source_movement_role",
            )
        }
    )


def _two_period_endpoint_continuity_v1(
    role_vectors: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate chained or parallel two-period endpoint semantics per lane."""

    movement_by_kind = {
        item["kind"]: item["role"] for item in compiled_specs["layout"]["movement_roles"]
    }
    opening_role = movement_by_kind["OPENING"]
    closing_role = movement_by_kind["CLOSING"]
    by_key: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for vector in role_vectors:
        by_key.setdefault(
            (vector["period_role"], vector["lane_role"], vector["movement_role"]), []
        ).append(vector)
    if {vector["period_role"] for vector in role_vectors} <= {"CURRENT_PERIOD"}:
        return [], []
    if not {
        vector.get("period_date")
        for vector in role_vectors
        if vector["period_role"] == "CURRENT_PERIOD"
    } - {None}:
        return [], []
    lanes = sorted({vector["lane_role"] for vector in role_vectors})
    receipts: list[dict[str, Any]] = []
    reasons: list[str] = []
    for lane_role in lanes:
        keys = (
            ("COMPARATIVE_PERIOD", lane_role, opening_role),
            ("COMPARATIVE_PERIOD", lane_role, closing_role),
            ("CURRENT_PERIOD", lane_role, opening_role),
            ("CURRENT_PERIOD", lane_role, closing_role),
        )
        if any(len(by_key.get(key, [])) != 1 for key in keys):
            reasons.append(f"ROLLFORWARD_ENDPOINT_CONTINUITY_INCOMPLETE:{lane_role}")
            continue
        previous_opening, previous_closing, next_opening, following_closing = (
            by_key[key][0] for key in keys
        )
        try:
            previous_period = (
                date.fromisoformat(previous_closing["period_date"])
                if previous_closing["period_date"] is not None
                else None
            )
            following_period = date.fromisoformat(following_closing["period_date"])
        except (TypeError, ValueError):
            reasons.append(f"ROLLFORWARD_ENDPOINT_PERIOD_DATE_INVALID:{lane_role}")
            continue
        if following_period is None:
            reasons.append(f"ROLLFORWARD_ENDPOINT_PERIOD_DATE_INVALID:{lane_role}")
            continue
        valid = True
        endpoints = (
            (previous_opening, previous_closing, previous_period),
            (next_opening, following_closing, following_period),
        )
        parsed_endpoint_dates: list[tuple[date | None, date | None]] = []
        for opening, closing, period in endpoints:
            try:
                opening_date = (
                    date.fromisoformat(opening["endpoint_date"])
                    if opening["endpoint_date"] is not None
                    else None
                )
                closing_date = (
                    date.fromisoformat(closing["endpoint_date"])
                    if closing["endpoint_date"] is not None
                    else None
                )
            except (TypeError, ValueError):
                opening_date = closing_date = None
                valid = False
            parsed_endpoint_dates.append((opening_date, closing_date))
            if period is not None:
                if opening_date is not None and opening_date >= period:
                    valid = False
                if closing_date is not None and closing_date != period:
                    valid = False
            if (
                opening_date is not None
                and closing_date is not None
                and opening_date >= closing_date
            ):
                valid = False
        (
            (previous_open_date, previous_close_date),
            (
                next_open_date,
                following_close_date,
            ),
        ) = parsed_endpoint_dates
        endpoint_date_alignment_receipt = None

        def aligned_one_year(previous: date | None, following: date | None) -> bool:
            return (
                previous is not None
                and following is not None
                and following.year == previous.year + 1
                and (following.month, following.day) == (previous.month, previous.day)
            )

        period_windows_aligned = previous_period is not None and aligned_one_year(
            previous_period, following_period
        )
        # A closing movement row is already bound to its exact period date.
        # When the row label itself omits a date, that authenticated period
        # assignment is the closing endpoint; no date is fabricated for an
        # opening row.
        effective_previous_close_date = previous_close_date or previous_period
        effective_following_close_date = following_close_date or following_period
        closing_endpoints_aligned = aligned_one_year(
            effective_previous_close_date,
            effective_following_close_date,
        )
        opening_endpoints_aligned = aligned_one_year(previous_open_date, next_open_date)

        def annual_or_fiscal_surface(value: Any) -> bool:
            folded = _normalized(value)
            return bool(
                folded
                and (
                    "nam tai chinh" in folded
                    or re.search(r"\bnam (?:duoc )?ket thuc\b", folded)
                    or "trong nam" in folded
                    or "financial year" in folded
                    or "year ended" in folded
                    or "during the year" in folded
                    or re.search(r"\bannual\b", folded)
                )
            )

        def valid_document_fiscal_close_year_binding(
            evidence: Mapping[str, Any], expected: date
        ) -> bool:
            receipt = evidence.get("document_fiscal_close_year_binding_receipt")
            if receipt is None:
                return False
            if (
                type(receipt) is not dict
                or set(receipt)
                != {
                    "context_rule",
                    "document_id",
                    "document_ordinal",
                    "rule",
                    "source_logical_name",
                    "source_sha256",
                    "year_context",
                }
                or receipt.get("rule")
                != (
                    "EXACT_BARE_PERIOD_YEAR_BOUND_TO_AUTHENTICATED_SELECTED_VERSION_"
                    "DOCUMENT_FISCAL_CLOSE_YEAR_CONTEXT"
                )
                or type(receipt.get("year_context")) is not dict
            ):
                return False
            year_context = receipt["year_context"]
            if (
                year_context.get("year") != expected.year
                or year_context.get("status")
                != "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
                or type(year_context.get("month")) is not int
                or type(year_context.get("day")) is not int
                or type(year_context.get("evidence")) is not list
                or not year_context["evidence"]
                or year_context.get("evidence_axis_sha256")
                != canonical_json_sha256_v1(year_context["evidence"])
                or year_context.get("distinct_page_count", 0) < 2
            ):
                return False
            try:
                if (
                    date(
                        expected.year,
                        year_context["month"],
                        year_context["day"],
                    )
                    != expected
                ):
                    return False
            except ValueError:
                return False
            observed_month_days = set()
            observed_pages = set()
            for item in year_context["evidence"]:
                if type(item) is not dict or type(item.get("text_exact")) is not str:
                    return False
                folded = _normalized(item["text_exact"])
                if not (_DATE_DMY.search(folded) or _DATE_WORDS.search(folded)):
                    return False
                try:
                    parsed = date.fromisoformat(item["date"])
                except (KeyError, TypeError, ValueError):
                    return False
                if parsed.year != expected.year or not any(
                    token[0] == parsed for token in _date_tokens(item["text_exact"])
                ):
                    return False
                observed_month_days.add((parsed.month, parsed.day))
                observed_pages.add((item.get("physical_page"), item.get("page_json_version_id")))
            return (
                observed_month_days == {(year_context["month"], year_context["day"])}
                and len(observed_pages) == year_context["distinct_page_count"]
                and len(observed_pages) >= 2
            )

        def exact_period_source_visible(item: Mapping[str, Any], expected: date) -> bool:
            evidence = item.get("period_semantics_evidence")
            if (
                type(evidence) is not dict
                or set(evidence)
                != {
                    "date_source_exact_axis",
                    "document_fiscal_close_year_binding_receipt",
                    "local_context_exact_axis",
                    "period_date",
                    "source_kind",
                }
                or evidence.get("period_date") != expected.isoformat()
                or type(evidence.get("date_source_exact_axis")) is not list
                or not evidence["date_source_exact_axis"]
                or type(evidence.get("local_context_exact_axis")) is not list
                or type(evidence.get("source_kind")) is not str
                or not evidence["source_kind"]
            ):
                return False
            document_year_bound = valid_document_fiscal_close_year_binding(evidence, expected)
            return all(
                type(source) is str
                and bool(source)
                and (
                    (
                        (resolved := _movement_period_end_token_v1(source)) is not None
                        and resolved[1] != "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
                        and resolved[0][0] == expected
                    )
                    or (
                        document_year_bound
                        and resolved is not None
                        and resolved[1] == "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
                        and resolved[0][0].year == expected.year
                    )
                )
                for source in evidence["date_source_exact_axis"]
            )

        def authoritative_period_source_visible(item: Mapping[str, Any], expected: date) -> bool:
            if not exact_period_source_visible(item, expected):
                return False
            evidence = item["period_semantics_evidence"]
            date_sources = evidence["date_source_exact_axis"]
            has_exact_period_end = any(
                (resolved := _movement_period_end_token_v1(source)) is not None
                and resolved[1] != "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
                and resolved[0][0] == expected
                for source in date_sources
            )
            return bool(
                has_exact_period_end
                or valid_document_fiscal_close_year_binding(evidence, expected)
            )

        def explicit_row_role_visible(item: Mapping[str, Any], role: str) -> bool:
            hierarchy = item.get("row_hierarchy_path_exact")
            return (
                type(item.get("row_label_exact")) is str
                and type(hierarchy) is list
                and bool(hierarchy)
                and _matches_alias(
                    item["row_label_exact"],
                    compiled_specs["aliases_by_role"][role],
                )
            )

        def fiscal_year_end_semantics(
            opening: Mapping[str, Any],
            closing: Mapping[str, Any],
            period: date,
        ) -> dict[str, Any] | None:
            evidence = closing.get("period_semantics_evidence")
            if (
                not authoritative_period_source_visible(closing, period)
                or type(evidence) is not dict
            ):
                return None
            exact_surfaces = [
                *evidence["date_source_exact_axis"],
                *evidence["local_context_exact_axis"],
            ]
            matched_surfaces = []
            for surface in exact_surfaces:
                if annual_or_fiscal_surface(surface):
                    matched_surfaces.append(surface)
            if not matched_surfaces:
                return None
            return {
                "classification": "SOURCE_VISIBLE_ANNUAL_OR_FISCAL_YEAR_END",
                "matched_source_exact_axis": list(dict.fromkeys(matched_surfaces)),
                "period_date": period.isoformat(),
                "period_semantics_evidence": canonical_clone_v1(evidence),
            }

        def next_fiscal_anniversary(period: date) -> date:
            try:
                return period.replace(year=period.year + 1)
            except ValueError:
                # A 29-Feb close has a 28-Feb anniversary in a non-leap fiscal cycle.
                return date(period.year + 1, period.month, period.day - 1)

        previous_fiscal_semantics = (
            fiscal_year_end_semantics(previous_opening, previous_closing, previous_period)
            if previous_period is not None
            else None
        )
        fiscal_cycle_anniversary = (
            next_fiscal_anniversary(previous_period) if previous_period is not None else None
        )
        fiscal_boundary_context = (
            previous_period is not None
            and previous_fiscal_semantics is not None
            and fiscal_cycle_anniversary is not None
            and previous_period < following_period
            and following_period <= fiscal_cycle_anniversary
            and previous_close_date is None
            and next_open_date is None
            and exact_period_source_visible(following_closing, following_period)
            and explicit_row_role_visible(previous_opening, opening_role)
            and explicit_row_role_visible(previous_closing, closing_role)
            and explicit_row_role_visible(next_opening, opening_role)
            and explicit_row_role_visible(following_closing, closing_role)
        )
        exact_calendar_boundary_context = (
            previous_period is not None
            and (previous_period.month, previous_period.day) == (12, 31)
            and following_period.year == previous_period.year + 1
            and previous_period < following_period <= date(following_period.year, 12, 31)
            and previous_close_date is None
            and next_open_date is None
            and authoritative_period_source_visible(previous_closing, previous_period)
            and authoritative_period_source_visible(following_closing, following_period)
            and explicit_row_role_visible(previous_opening, opening_role)
            and explicit_row_role_visible(previous_closing, closing_role)
            and explicit_row_role_visible(next_opening, opening_role)
            and explicit_row_role_visible(following_closing, closing_role)
        )

        shared_opening = next_opening["assignment_kind"] == "SHARED_PREVIOUS_CLOSING_AS_OPENING"
        previous_coefficient = previous_closing["cell"]["coefficient"]
        next_coefficient = next_opening["cell"]["coefficient"]
        endpoint_value_rounding_receipt = None
        chain_gap = (
            (next_open_date - previous_close_date).days
            if next_open_date is not None and previous_close_date is not None
            else None
        )
        if previous_period is None:
            continuity_kind = (
                "PARALLEL_SYMBOLIC_COMPARATIVE_WINDOW"
                if previous_closing["resolved_period"] == "COMPARATIVE_UNDATED"
                else None
            )
        elif shared_opening or chain_gap in {0, 1}:
            continuity_kind = "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN"
        elif (
            period_windows_aligned
            and closing_endpoints_aligned
            and authoritative_period_source_visible(previous_closing, previous_period)
            and authoritative_period_source_visible(following_closing, following_period)
        ):
            continuity_kind = "PARALLEL_PERIOD_WINDOWS_NO_CROSS_VALUE_EQUALITY"
        elif fiscal_boundary_context:
            continuity_kind = "CHAINED_FISCAL_BOUNDARY_CONTEXT_PRIOR_CLOSE_TO_CURRENT_OPEN"
        elif exact_calendar_boundary_context:
            continuity_kind = "CHAINED_EXACT_PRIOR_CALENDAR_CLOSE_TO_CURRENT_OPEN"
        else:
            continuity_kind = None
        valid = valid and continuity_kind is not None

        if (
            previous_coefficient is None
            or next_coefficient is None
            or previous_closing["bound_unit"] is None
            or previous_closing["bound_unit"] != next_opening["bound_unit"]
        ):
            valid = False
        if continuity_kind in {
            "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN",
            "CHAINED_FISCAL_BOUNDARY_CONTEXT_PRIOR_CLOSE_TO_CURRENT_OPEN",
            "CHAINED_EXACT_PRIOR_CALENDAR_CLOSE_TO_CURRENT_OPEN",
        }:
            if previous_coefficient != next_coefficient:
                if (
                    not shared_opening
                    and type(previous_coefficient) is int
                    and type(next_coefficient) is int
                    and abs(previous_coefficient - next_coefficient) == 1
                    and previous_closing["cell"].get("state") == "RAW_SIGNED_INTEGER"
                    and next_opening["cell"].get("state") == "RAW_SIGNED_INTEGER"
                ):
                    endpoint_value_rounding_receipt = {
                        "difference_in_display_units": (
                            next_coefficient - previous_coefficient
                        ),
                        "rule": (
                            "SOURCE_VISIBLE_ADJACENT_PERIOD_ENDPOINTS_MAY_DIFFER_BY_"
                            "ONE_DISPLAY_UNIT_WITHOUT_REWRITING_EITHER_VALUE"
                        ),
                        "status": "EXACT_ONE_DISPLAY_UNIT_ENDPOINT_ROUNDING",
                    }
                else:
                    valid = False
            if continuity_kind == "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN":
                if previous_close_date is None or next_open_date is None:
                    valid = False
                if chain_gap not in {0, 1}:
                    valid = False
                if shared_opening and chain_gap != 0:
                    valid = False
        elif continuity_kind == "PARALLEL_PERIOD_WINDOWS_NO_CROSS_VALUE_EQUALITY":
            if not (
                period_windows_aligned
                and closing_endpoints_aligned
                and authoritative_period_source_visible(previous_closing, previous_period)
                and authoritative_period_source_visible(following_closing, following_period)
            ):
                valid = False
            elif not opening_endpoints_aligned:
                # Parallel disclosure windows need not start on aligned dates.
                # Preserve the source-visible mismatch as diagnostic evidence
                # only after the final relation is known to be parallel.
                endpoint_date_alignment_receipt = {
                    "derivation_kind": ("PARALLEL_PERIOD_OPENING_WINDOW_MISMATCH_SOURCE_VISIBLE"),
                    "following_opening": _endpoint_source_receipt(next_opening),
                    "previous_opening": _endpoint_source_receipt(previous_opening),
                }
        if shared_opening and (
            continuity_kind != "CHAINED_PRIOR_CLOSE_TO_CURRENT_OPEN"
            or next_opening["locator"] != previous_closing["locator"]
            or next_opening["row_id"] != previous_closing["row_id"]
            or next_opening["column_ordinal"] != previous_closing["column_ordinal"]
            or next_opening["source_movement_role"] != closing_role
            or next_opening["source_block_ordinal"] != previous_closing["block_ordinal"]
            or next_opening["cell"] != previous_closing["cell"]
        ):
            valid = False
        if not valid:
            reasons.append(f"ROLLFORWARD_ENDPOINT_CONTINUITY_INVALID:{lane_role}")
            continue
        boundary_semantics_receipt = None
        if continuity_kind == "CHAINED_FISCAL_BOUNDARY_CONTEXT_PRIOR_CLOSE_TO_CURRENT_OPEN":
            boundary_semantics_receipt = {
                "current_period_evidence": canonical_clone_v1(
                    following_closing["period_semantics_evidence"]
                ),
                "current_reporting_end": following_period.isoformat(),
                "fiscal_cycle_anniversary": fiscal_cycle_anniversary.isoformat(),
                "previous_fiscal_close": previous_period.isoformat(),
                "previous_fiscal_year_end_semantics": canonical_clone_v1(previous_fiscal_semantics),
                "rule": (
                    "SOURCE_VISIBLE_ANNUAL_OR_FISCAL_YEAR_END_TO_REPORTING_END_"
                    "WITHIN_IMMEDIATELY_FOLLOWING_FISCAL_CYCLE_AND_EXPLICIT_"
                    "OPEN_CLOSE_ROWS"
                ),
            }
        elif continuity_kind == "CHAINED_EXACT_PRIOR_CALENDAR_CLOSE_TO_CURRENT_OPEN":
            boundary_semantics_receipt = {
                "current_period_evidence": canonical_clone_v1(
                    following_closing["period_semantics_evidence"]
                ),
                "current_reporting_end": following_period.isoformat(),
                "previous_period_evidence": canonical_clone_v1(
                    previous_closing["period_semantics_evidence"]
                ),
                "previous_reporting_close": previous_period.isoformat(),
                "rule": (
                    "SOURCE_VISIBLE_EXACT_PRIOR_CALENDAR_CLOSE_TO_REPORTING_END_"
                    "WITHIN_IMMEDIATELY_FOLLOWING_CALENDAR_YEAR_EXPLICIT_OPEN_CLOSE_"
                    "ROWS_SAME_LANE_UNIT_AND_CROSS_ENDPOINT_VALUE"
                ),
            }
        receipts.append(
            {
                "boundary_semantics_receipt": boundary_semantics_receipt,
                "following_closing": _endpoint_source_receipt(following_closing),
                "following_period": following_period.isoformat(),
                "continuity_kind": continuity_kind,
                "endpoint_date_alignment_receipt": endpoint_date_alignment_receipt,
                "lane_role": lane_role,
                "next_opening": _endpoint_source_receipt(next_opening),
                "previous_closing": _endpoint_source_receipt(previous_closing),
                "previous_opening": _endpoint_source_receipt(previous_opening),
                "previous_period": (
                    previous_period.isoformat() if previous_period is not None else None
                ),
                "rule": (
                    "SAME_DOCUMENT_LANE_UNIT_EXACT_ENDPOINT_DIRECTION_CHAINED_OR_"
                    "PARALLEL_PERIOD_WINDOW_SEMANTICS"
                ),
                **(
                    {"endpoint_value_rounding_receipt": endpoint_value_rounding_receipt}
                    if endpoint_value_rounding_receipt is not None
                    else {}
                ),
            }
        )
    return receipts, reasons


def _bounded_population_reset_fence_v1(
    region_axis: Sequence[Mapping[str, Any]],
    *,
    page_json_by_version: Mapping[str, Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    include_intervening_surfaces: bool,
) -> dict[str, Any]:
    """Scan selected components and only the structural interval between them.

    A containing section can hold unrelated schedules before or after the
    selected roll-forward.  Those sibling tables are not part of a one-table
    population interval.  Conversely, every table/section strictly between
    two selected components remains a reset fence, including all of its row
    labels and hierarchy paths.
    """

    first_page = region_axis[0]["physical_page"]
    last_page = region_axis[-1]["physical_page"]
    lower_section = int(region_axis[0]["section_id"][1:])
    upper_section = int(region_axis[-1]["section_id"][1:])
    selected_table_keys = {
        (
            item["physical_page"],
            item["page_json_version_id"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        )
        for item in region_axis
    }
    aliases = sorted(
        {
            *compiled_specs["layout"]["population_policy"]["reset_aliases"],
            *compiled_specs["layout"]["population_policy"]["hard_negative_aliases"],
        }
    )
    hits: list[dict[str, Any]] = []
    checked_pages = []
    seen_pages: set[tuple[int, str]] = set()
    for locator in region_axis:
        key = (locator["physical_page"], locator["page_json_version_id"])
        if key in seen_pages:
            continue
        seen_pages.add(key)
        physical_page, version_id = key
        page_json = page_json_by_version[version_id]
        sections = page_json.get("sections")
        if type(sections) is not list:
            raise _error("roll-forward page section axis is invalid")
        selected_by_section: dict[int, list[int]] = {}
        for item in region_axis:
            if (
                item["physical_page"] == physical_page
                and item["page_json_version_id"] == version_id
            ):
                selected_by_section.setdefault(int(item["section_id"][1:]), []).append(
                    int(item["table_id"][1:])
                )
        if include_intervening_surfaces:
            start = lower_section if physical_page == first_page else 1
            stop = upper_section if physical_page == last_page else len(sections)
            section_ordinals = list(range(start, stop + 1))
        else:
            section_ordinals = sorted(selected_by_section)
            start = section_ordinals[0]
            stop = section_ordinals[-1]
        if not section_ordinals or not 1 <= start <= stop <= len(sections):
            raise _error("roll-forward reset-fence section interval is invalid")
        checked_section_table_intervals = []
        for section_ordinal in section_ordinals:
            section = sections[section_ordinal - 1]
            if not isinstance(section, Mapping):
                raise _error("roll-forward reset-fence section is invalid")
            narratives = section.get("narratives_exact")
            tables = section.get("tables")
            if type(narratives) is not list or type(tables) is not list:
                raise _error("roll-forward reset-fence section axes are invalid")
            if include_intervening_surfaces:
                is_first_boundary = physical_page == first_page and section_ordinal == lower_section
                is_last_boundary = physical_page == last_page and section_ordinal == upper_section
                first_table = int(region_axis[0]["table_id"][1:]) if is_first_boundary else 1
                last_table = (
                    int(region_axis[-1]["table_id"][1:]) if is_last_boundary else len(tables)
                )
                table_intervals = [(first_table, last_table)]
                if not 1 <= first_table <= last_table <= len(tables):
                    # A strictly intervening prose-only section still forms a
                    # reset fence even though it contributes no table surfaces.
                    if tables or is_first_boundary or is_last_boundary:
                        raise _error("roll-forward reset-fence table interval is invalid")
                    table_intervals = []
            else:
                table_intervals = [
                    (table_ordinal, table_ordinal)
                    for table_ordinal in sorted(selected_by_section[section_ordinal])
                ]
                if any(
                    not 1 <= first_table <= last_table <= len(tables)
                    for first_table, last_table in table_intervals
                ):
                    raise _error("roll-forward reset-fence table interval is invalid")
            checked_section_table_intervals.extend(
                {
                    "first_table_ordinal": first_table,
                    "last_table_ordinal": last_table,
                    "section_ordinal": section_ordinal,
                }
                for first_table, last_table in table_intervals
            )
            surfaces = [
                ("SECTION_TITLE", section.get("title_exact")),
                *(("SECTION_NARRATIVE", narrative) for narrative in narratives),
            ]
            for first_table, last_table in table_intervals:
                for table_ordinal in range(first_table, last_table + 1):
                    table = tables[table_ordinal - 1]
                    if not isinstance(table, Mapping):
                        raise _error("roll-forward reset-fence table is invalid")
                    surfaces.append(("TABLE_TITLE", table.get("title_exact")))
                    columns = table.get("columns")
                    rows = table.get("rows")
                    if type(columns) is not list or type(rows) is not list:
                        raise _error("roll-forward reset-fence table axes are invalid")
                    is_selected_table = (
                        physical_page,
                        version_id,
                        section_ordinal,
                        table_ordinal,
                    ) in selected_table_keys
                    lane_by_column = (
                        _projected_lane_columns_v1(
                            columns,
                            compiled_specs=compiled_specs,
                        )[0]
                        if is_selected_table
                        else []
                    )
                    project_selected_lanes = (
                        len({role for role in lane_by_column if role is not None})
                        >= compiled_specs["layout"]["minimum_required_lanes"]
                    )
                    for column_ordinal, column in enumerate(columns):
                        if not isinstance(column, Mapping):
                            raise _error("roll-forward reset-fence column is invalid")
                        header_path = column.get("header_path_exact")
                        if type(header_path) is not list:
                            raise _error("roll-forward reset-fence header path is invalid")
                        if project_selected_lanes and lane_by_column[column_ordinal] is None:
                            continue
                        surfaces.extend(("COLUMN_HEADER", value) for value in header_path)
                    for row in rows:
                        if not isinstance(row, Mapping):
                            raise _error("roll-forward reset-fence row is invalid")
                        hierarchy = row.get("hierarchy_path_exact")
                        if type(hierarchy) is not list:
                            raise _error("roll-forward reset-fence row hierarchy is invalid")
                        surfaces.append(("ROW_LABEL", row.get("label_exact")))
                        surfaces.extend(("ROW_HIERARCHY", value) for value in hierarchy)
            hits.extend(
                {
                    "page_json_version_id": version_id,
                    "physical_page": physical_page,
                    "section_ordinal": section_ordinal,
                    "source_kind": source_kind,
                    "text_exact": value,
                }
                for source_kind, value in surfaces
                if type(value) is str and _matches_alias(value, aliases)
            )
        checked_pages.append(
            {
                "first_section_ordinal": start,
                "last_section_ordinal": stop,
                "page_json_version_id": version_id,
                "physical_page": physical_page,
                "section_table_intervals": checked_section_table_intervals,
            }
        )
    return {
        "checked_page_intervals": checked_pages,
        "scope_kind": (
            "SELECTED_COMPONENTS_AND_STRICTLY_INTERVENING_SURFACES"
            if include_intervening_surfaces
            else "INDEPENDENT_LOCAL_OWNER_SELECTED_COMPONENTS_ONLY"
        ),
        "reset_hits": hits,
        "status": "RESET_FENCE_CLEAR" if not hits else "RESET_FENCE_VIOLATED",
    }


def evaluate_gemini_json_rollforward_family_cluster_v1(
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_fiscal_close_context_evidence: Mapping[str, Any] | None = None,
    document_unit_context_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one ordered one/two-table two-period roll-forward cluster."""

    region_axis = _region_axis(regions)
    checked_query_receipt = _validated_region_query_receipt_v1(
        query_receipt,
        region_axis=region_axis,
    )
    page_json_by_version, source_repair_overlay_receipts = (
        _apply_authenticated_source_repair_overlay_v1(
            region_axis=region_axis,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
        )
    )
    first_region = region_axis[0]
    checked_document_unit_context = _validated_document_unit_context_evidence_v1(
        document_unit_context_evidence,
        document_id=first_region["document_id"],
        source_logical_name=first_region["source_logical_name"],
        source_sha256=first_region["source_sha256"],
        compiled_specs=compiled_specs,
    )
    checked_document_fiscal_close_context = _validated_document_fiscal_close_context_evidence_v1(
        document_fiscal_close_context_evidence,
        document_id=first_region["document_id"],
        source_logical_name=first_region["source_logical_name"],
        source_sha256=first_region["source_sha256"],
    )
    fragments = []
    period_column_records = []
    component_classifications = []
    reasons = []
    complementary_candidates = []
    following_owner_backbinding_candidates = []
    for owner_ordinal, owner_locator in enumerate(region_axis):
        for continuation_locator in region_axis[owner_ordinal + 1 :]:
            owner_page = page_json_by_version.get(owner_locator["page_json_version_id"])
            continuation_page = page_json_by_version.get(
                continuation_locator["page_json_version_id"]
            )
            if type(owner_page) is not dict or type(continuation_page) is not dict:
                continue
            owner_section, owner_table = _source_table(
                owner_page,
                section_id=owner_locator["section_id"],
                table_id=owner_locator["table_id"],
            )
            continuation_section, continuation_table = _source_table(
                continuation_page,
                section_id=continuation_locator["section_id"],
                table_id=continuation_locator["table_id"],
            )
            complementary = build_gemini_json_rollforward_complementary_continuation_v1(
                owner_locator=owner_locator,
                owner_section=owner_section,
                owner_table=owner_table,
                continuation_locator=continuation_locator,
                continuation_section=continuation_section,
                continuation_table=continuation_table,
                compiled_specs=compiled_specs,
            )
            if complementary is not None:
                complementary_candidates.append(complementary)
            backbinding = build_gemini_json_rollforward_following_owner_backbinding_v1(
                preceding_locator=owner_locator,
                preceding_section=owner_section,
                preceding_table=owner_table,
                following_locator=continuation_locator,
                following_section=continuation_section,
                following_table=continuation_table,
                compiled_specs=compiled_specs,
            )
            if backbinding is not None:
                following_owner_backbinding_candidates.append(backbinding)
    if len(complementary_candidates) > 1:
        raise _error("roll-forward complementary continuation axis is ambiguous")
    complementary_continuation = (
        complementary_candidates[0] if complementary_candidates else None
    )
    if len(following_owner_backbinding_candidates) > 1:
        raise _error("roll-forward following-owner backbinding axis is ambiguous")
    following_owner_backbinding = (
        following_owner_backbinding_candidates[0]
        if following_owner_backbinding_candidates
        else None
    )
    if complementary_continuation is not None and following_owner_backbinding is not None:
        raise _error("roll-forward continuation binding kind is ambiguous")
    if len(region_axis) == 3 and complementary_continuation is None:
        raise _error("three roll-forward regions lack one complementary continuation")
    complementary_owner_locator = (
        complementary_continuation["receipt"]["owner_locator"]
        if complementary_continuation is not None
        else None
    )
    complementary_continuation_locator = (
        complementary_continuation["receipt"]["continuation_locator"]
        if complementary_continuation is not None
        else None
    )
    following_owner_backbound_locator = (
        following_owner_backbinding["preceding_locator"]
        if following_owner_backbinding is not None
        else None
    )
    for locator in region_axis:
        page_json = page_json_by_version.get(locator["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("roll-forward selected page JSON is absent")
        section, table = _source_table(
            page_json,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        try:
            classification = classify_gemini_json_rollforward_table_v1(
                section=section,
                table=table,
                compiled_specs=compiled_specs,
            )
            component_classifications.append(
                {
                    "bound_unit": _bound_unit(table, compiled_specs=compiled_specs),
                    **canonical_clone_v1(classification),
                    "locator": canonical_clone_v1(locator),
                }
            )
            if (
                classification["context_reset_visible"]
                or classification["structural_hard_negative_visible"]
            ):
                reasons.append("ROLLFORWARD_LOCAL_POPULATION_RESET_OR_HARD_NEGATIVE")
            if complementary_continuation_locator == locator:
                continue
            evaluation_locator = locator
            evaluation_section = section
            evaluation_table = table
            row_source_refs = None
            if complementary_owner_locator == locator:
                evaluation_section = complementary_continuation["combined_section"]
                evaluation_table = complementary_continuation["combined_table"]
                row_source_refs = complementary_continuation["row_source_refs"]
                classification = complementary_continuation["receipt"][
                    "logical_classification"
                ]
            lane_columns = _period_lane_cells_from_lane_columns(
                locator=evaluation_locator,
                section=evaluation_section,
                table=evaluation_table,
                compiled_specs=compiled_specs,
                row_source_refs=row_source_refs,
            )
        except GeminiJsonRollforwardAccountingFamilyV1Error:
            reasons.append("ROLLFORWARD_COMPONENT_TABLE_STRUCTURE_INVALID")
            continue
        if lane_columns:
            fragments.extend(lane_columns)
            continue
        period_column_records.append(
            {
                "classification": classification,
                "locator": evaluation_locator,
                "section": evaluation_section,
                "table": evaluation_table,
            }
        )
    lane_assignments, lane_assignment_receipts, assignment_reasons = (
        _assign_period_column_lane_roles(
            period_column_records,
            compiled_specs=compiled_specs,
        )
    )
    reasons.extend(assignment_reasons)
    for ordinal, record in enumerate(period_column_records):
        lane_role = lane_assignments.get(ordinal)
        if lane_role is None:
            continue
        try:
            fragments.extend(
                _period_lane_cells_from_period_columns(
                    locator=record["locator"],
                    section=record["section"],
                    table=record["table"],
                    compiled_specs=compiled_specs,
                    lane_role_override=lane_role,
                )
            )
        except GeminiJsonRollforwardAccountingFamilyV1Error:
            reasons.append("ROLLFORWARD_COMPONENT_TABLE_STRUCTURE_INVALID")
    fragments, period_assignment_receipt = _resolve_ordered_period_components_v1(
        fragments,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        document_fiscal_close_context_evidence=(checked_document_fiscal_close_context),
    )
    horizontal_total_zero_recovery_receipts = [
        canonical_clone_v1(receipt)
        for fragment in fragments
        for receipt in fragment.get("horizontal_total_zero_recovery_receipts", [])
    ]
    for fragment in fragments:
        period = fragment.get("period")
        evidence = fragment.get("period_semantics_evidence")
        if period is None or type(evidence) is not dict:
            continue
        date_sources = evidence.get("date_source_exact_axis")
        if type(date_sources) is not list:
            continue
        resolved_date_sources = [
            _movement_period_end_token_v1(source)
            for source in date_sources
            if type(source) is str
        ]
        if not resolved_date_sources or any(
            resolved is None or resolved[1] != "BARE_YEAR_FISCAL_CLOSE_CANDIDATE"
            for resolved in resolved_date_sources
        ):
            continue
        year_binding = _document_fiscal_close_year_binding_receipt_v1(
            checked_document_fiscal_close_context,
            year=period[0].year,
        )
        if year_binding is None:
            continue
        year_context = year_binding["year_context"]
        try:
            bound_period = date(period[0].year, year_context["month"], year_context["day"])
        except (TypeError, ValueError):
            continue
        fragment["period"] = (bound_period, period[1])
        evidence["period_date"] = bound_period.isoformat()
        evidence["document_fiscal_close_year_binding_receipt"] = year_binding
    aggregate_population_axis = []
    for fragment in fragments:
        receipt = fragment["lane_population_assignment_receipt"]
        if receipt is None:
            continue
        decision_by_lane = {item["lane_role"]: item for item in receipt["decisions"]}
        for lane_role in sorted(
            {role for role in receipt["raw_lane_roles_by_column"] if role is not None}
        ):
            if receipt["raw_lane_roles_by_column"].count(lane_role) < 2:
                continue
            decision = decision_by_lane.get(lane_role)
            aggregate_population_axis.append(
                {
                    "aggregate_identity_normalized": (
                        decision["aggregate_identity_normalized"] if decision else None
                    ),
                    "block_ordinal": fragment["block_ordinal"],
                    "lane_role": lane_role,
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "status": "UNIQUE_EXACT_HORIZONTAL_AGGREGATE" if decision else "UNRESOLVED",
                }
            )
    for lane_role in sorted({item["lane_role"] for item in aggregate_population_axis}):
        identities = {
            item["aggregate_identity_normalized"]
            for item in aggregate_population_axis
            if item["lane_role"] == lane_role and item["aggregate_identity_normalized"] is not None
        }
        if len(identities) > 1:
            reasons.append(f"ROLLFORWARD_AGGREGATE_POPULATION_MISMATCH:{lane_role}")
    owner_components = [item for item in component_classifications if item["local_owner_visible"]]
    continuation_components = [
        item for item in component_classifications if not item["local_owner_visible"]
    ]
    if not owner_components:
        reasons.append("ROLLFORWARD_LOCAL_POPULATION_OWNER_NOT_VISIBLE")

    def locator_order(item: Mapping[str, Any]) -> tuple[int, int, int]:
        return (
            item["locator"]["physical_page"],
            int(item["locator"]["section_id"][1:]),
            int(item["locator"]["table_id"][1:]),
        )

    unbound_continuations = [
        item
        for item in continuation_components
        if item["locator"] != following_owner_backbound_locator
        if not any(locator_order(owner) < locator_order(item) for owner in owner_components)
    ]
    if unbound_continuations:
        reasons.append("ROLLFORWARD_BOUNDED_OWNER_CONTINUATION_DIRECTION_INVALID")
    if any(
        not item["continuation_evidence"]
        and item["locator"] != following_owner_backbound_locator
        for item in continuation_components
    ):
        reasons.append("ROLLFORWARD_EXPLICIT_CONTINUATION_EVIDENCE_NOT_VISIBLE")
    population_reset_axis = (
        [complementary_owner_locator, complementary_continuation_locator]
        if complementary_continuation is not None
        else region_axis
    )
    reset_fence_receipt = _bounded_population_reset_fence_v1(
        population_reset_axis,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        include_intervening_surfaces=(
            bool(continuation_components)
            or complementary_continuation is not None
            or following_owner_backbinding is not None
        ),
    )
    if reset_fence_receipt["reset_hits"]:
        reasons.append("ROLLFORWARD_SELECTED_INTERVAL_POPULATION_RESET_OR_HARD_NEGATIVE_VISIBLE")
        if continuation_components:
            reasons.append("ROLLFORWARD_BOUNDED_OWNER_CONTINUATION_RESET_FENCE_VIOLATED")
    population_receipt = {
        "binding_kind": (
            "FOLLOWING_LOCAL_OWNER_BACKBINDS_IMMEDIATELY_PRECEDING_COMPLETE_COMPONENT"
            if following_owner_backbinding is not None
            else
            "ALL_COMPONENTS_EXPLICIT_LOCAL_OWNER"
            if owner_components and not continuation_components
            else "BOUNDED_SELECTED_COMPONENT_OWNER_CONTINUATION"
            if owner_components
            else "UNRESOLVED_NO_LOCAL_OWNER"
        ),
        "continuation_component_locators": [item["locator"] for item in continuation_components],
        "continuation_evidence_receipts": [
            {
                "evidence": item["continuation_evidence"],
                "locator": item["locator"],
            }
            for item in continuation_components
        ],
        "max_physical_page_span": (
            region_axis[-1]["physical_page"] - region_axis[0]["physical_page"]
        ),
        "owner_component_locators": [item["locator"] for item in owner_components],
        "reset_fence_receipt": reset_fence_receipt,
        "reset_or_hard_negative_visible": bool(reset_fence_receipt["reset_hits"])
        or any(
            item["context_reset_visible"] or item["structural_hard_negative_visible"]
            for item in component_classifications
        ),
        "rule": (
            "AT_LEAST_ONE_SELECTED_COMPONENT_LOCAL_OWNER_OTHER_COMPONENTS_ONLY_"
            "WITHIN_ORDERED_ONE_PAGE_RESET_FENCED_CLUSTER"
        ),
        "unbound_continuation_locators": [item["locator"] for item in unbound_continuations],
    }
    if complementary_continuation is not None:
        population_receipt["logical_continuation_receipt"] = canonical_clone_v1(
            complementary_continuation["receipt"]
        )
    if following_owner_backbinding is not None:
        population_receipt["following_owner_backbinding_receipt"] = canonical_clone_v1(
            following_owner_backbinding
        )
    local_unit_axis = [
        {
            "block_ordinal": fragment["block_ordinal"],
            "bound_unit": fragment["bound_unit"],
            "locator": canonical_clone_v1(fragment["locator"]),
        }
        for fragment in fragments
    ]
    local_units = [fragment["bound_unit"] for fragment in fragments]
    if local_units and all(unit is None for unit in local_units):
        if (
            checked_document_unit_context is not None
            and checked_document_unit_context["status"]
            == "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
        ):
            for fragment in fragments:
                fragment["bound_unit"] = checked_document_unit_context["canonical_unit"]
            unit_assignment_kind = "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_INHERITED"
        else:
            unit_assignment_kind = "UNRESOLVED_NO_LOCAL_OR_DOCUMENT_UNIT_CONSENSUS"
            reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    elif local_units and all(unit is not None for unit in local_units):
        unit_assignment_kind = "ALL_COMPONENTS_EXPLICIT_LOCAL_CANONICAL_UNIT"
    else:
        unit_assignment_kind = "MIXED_LOCAL_VISIBLE_AND_MISSING_UNIT_NOT_INHERITED"
        reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    bound_units = [fragment["bound_unit"] for fragment in fragments]
    if not bound_units:
        reasons.append("ROLLFORWARD_MONEY_UNIT_NOT_VISIBLE")
    if len({unit for unit in bound_units if unit is not None}) > 1:
        reasons.append("ROLLFORWARD_MONEY_UNIT_MISMATCH_ACROSS_PERIODS_OR_COMPONENTS")
    # Document-wide evidence is authority-bearing only when it actually closes
    # a locally unit-less component set.  Keeping irrelevant context out of a
    # locally explicit candidate also makes replay invariant to unrelated unit
    # surfaces elsewhere in the same selected document frontier.
    receipt_document_unit_context = (
        checked_document_unit_context
        if unit_assignment_kind
        in {
            "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_INHERITED",
            "UNRESOLVED_NO_LOCAL_OR_DOCUMENT_UNIT_CONSENSUS",
        }
        else None
    )
    unit_provenance_receipt = {
        "assignment_kind": unit_assignment_kind,
        "document_unit_context_evidence": receipt_document_unit_context,
        "local_unit_axis": local_unit_axis,
        "resolved_canonical_unit": (
            next(iter({unit for unit in bound_units if unit is not None}))
            if len({unit for unit in bound_units if unit is not None}) == 1
            else None
        ),
        "rule": (
            "LOCAL_CANONICAL_UNIT_OR_SELECTED_VERSION_DOCUMENT_TWO_PAGE_"
            "UNIQUE_MAGNITUDE_CURRENCY_CONSENSUS_NO_SCALE_CONVERSION"
        ),
    }
    period_roles = ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
    hinted_roles = [fragment["period_role_hint"] for fragment in fragments]
    hint_axis_resolved = (
        bool(fragments)
        and all(role in period_roles for role in hinted_roles)
        and set(hinted_roles) == set(period_roles)
    )
    single_current_axis_resolved = (
        len(fragments) == 1
        and hinted_roles == ["CURRENT_PERIOD"]
        and period_assignment_receipt["status"]
        in {
            "SINGLE_CURRENT_EXPLICIT_ROLE_BOUND",
            "SINGLE_CURRENT_PERIOD_CONTEXT_BOUND",
        }
    )
    dated = [fragment for fragment in fragments if fragment["period"] is not None]
    dates = sorted({fragment["period"][0] for fragment in dated}, reverse=True)
    date_axis_resolved = len(dates) == 2 and len(dated) == len(fragments)
    if not hint_axis_resolved and not date_axis_resolved and not single_current_axis_resolved:
        reasons.append("ROLLFORWARD_EXACT_TWO_PERIOD_AXIS_NOT_RESOLVED")
    period_role_by_date = {
        period: "CURRENT_PERIOD" if ordinal == 0 else "COMPARATIVE_PERIOD"
        for ordinal, period in enumerate(dates)
    }
    source_role_vectors = []
    for fragment in fragments:
        if hint_axis_resolved or single_current_axis_resolved:
            period_role = fragment["period_role_hint"]
        else:
            if fragment["period"] is None or fragment["period"][0] not in period_role_by_date:
                continue
            period_role = period_role_by_date[fragment["period"][0]]
        for item in fragment["cells"]:
            record = {
                **canonical_clone_v1(item),
                "block_ordinal": fragment["block_ordinal"],
                "bound_unit": fragment["bound_unit"],
                "locator": canonical_clone_v1(item.get("locator", fragment["locator"])),
                "period_date": (
                    fragment["period"][0].isoformat() if fragment["period"] is not None else None
                ),
                "period_semantics_evidence": canonical_clone_v1(
                    fragment["period_semantics_evidence"]
                ),
                "period_role": period_role,
                "resolved_period": (
                    fragment["period"][1]
                    if fragment["period"] is not None
                    else "CURRENT_UNDATED"
                    if period_role == "CURRENT_PERIOD"
                    else "COMPARATIVE_UNDATED"
                ),
            }
            source_role_vectors.append(canonical_clone_v1(record))
    projected_role_vectors, duplicate_source_ambiguities, duplicate_reasons = (
        project_gemini_json_rollforward_source_role_vectors_v1(
            source_role_vectors,
            compiled_specs=compiled_specs,
        )
    )
    projected_role_vectors, directional_deduction_normalization_receipts = (
        normalize_gemini_json_rollforward_directional_deductions_v1(
            projected_role_vectors,
            compiled_specs=compiled_specs,
        )
    )
    reasons.extend(duplicate_reasons)
    merged = {
        (record["period_role"], record["lane_role"], record["movement_role"]): record
        for record in projected_role_vectors
    }

    required_lanes = {
        item["role"] for item in compiled_specs["layout"]["lane_roles"] if not item["optional"]
    }
    movement_specs = compiled_specs["layout"]["movement_roles"]
    required_movements = {item["role"] for item in movement_specs if item["required"]}
    lanes_by_period = {
        period_role: {lane for period, lane, _movement in merged if period == period_role}
        for period_role in period_roles
    }
    required_period_roles = (
        ("CURRENT_PERIOD",) if single_current_axis_resolved else period_roles
    )
    for period_role in required_period_roles:
        if required_lanes <= lanes_by_period[period_role]:
            continue
        reasons.append(
            "ROLLFORWARD_REQUIRED_CURRENT_LANES_INCOMPLETE"
            if period_role == "CURRENT_PERIOD"
            else "ROLLFORWARD_REQUIRED_COMPARATIVE_LANES_INCOMPLETE"
        )
    if (
        not single_current_axis_resolved
        and lanes_by_period["CURRENT_PERIOD"] != lanes_by_period["COMPARATIVE_PERIOD"]
    ):
        reasons.append("ROLLFORWARD_LANE_POPULATION_MISMATCH_ACROSS_PERIODS")
    equations = []
    role_vectors = []
    potential_mappings = []
    unresolved_frontiers = []
    bindings = compiled_specs["schema"]["bindings"]
    for period_role in period_roles:
        for lane_role in sorted(lanes_by_period[period_role]):
            cells = {
                movement: canonical_clone_v1(record["cell"])
                for (period, lane, movement), record in merged.items()
                if period == period_role and lane == lane_role
            }
            scope = lane_role if period_role == "CURRENT_PERIOD" else f"{period_role}:{lane_role}"
            solution: dict[str, Any] | None = None
            if not required_movements <= set(cells):
                reasons.append(f"ROLLFORWARD_REQUIRED_MOVEMENTS_INCOMPLETE:{scope}")
            else:
                solution = solve_one_unknown_rollforward_lane_v1(
                    cells,
                    movement_specs=movement_specs,
                )
                if solution["status"] == "EXACT_ONE_UNKNOWN_INFERRED":
                    role = solution["inferred_role"]
                    cells[role] = {
                        **cells[role],
                        "coefficient": solution["inferred_coefficient"],
                        "state": "INFERRED_ONE_UNKNOWN_FULL_RANK",
                    }
                equation = {
                    "equation_rank": 1,
                    "inferred_coefficient": solution.get("inferred_coefficient"),
                    "inferred_role": solution.get("inferred_role"),
                    "lane_role": lane_role,
                    "period_role": period_role,
                    "role_coefficients": [
                        {
                            "coefficient": cells[item["role"]]["coefficient"],
                            "equation_coefficient": item["equation_coefficient"],
                            "role": item["role"],
                            "state": cells[item["role"]]["state"],
                        }
                        for item in movement_specs
                        if item["role"] in cells
                    ],
                    "status": solution["status"],
                }
                equations.append(equation)
                if solution["status"] not in {
                    "EXACT",
                    "EXACT_DISPLAY_UNIT_ROUNDING",
                    "EXACT_ONE_UNKNOWN_INFERRED",
                }:
                    reason = f"ROLLFORWARD_LANE_EQUATION_{solution['status']}:{scope}"
                    reasons.append(reason)
                    unresolved_frontiers.append(
                        {
                            "lane_role": lane_role,
                            "period_role": period_role,
                            "reason": reason,
                            "unknown_roles": solution.get("unknown_roles", []),
                            "source_records": [
                                {
                                    "locator": record["locator"],
                                    "movement_role": record["movement_role"],
                                    "row_id": record["row_id"],
                                }
                                for record in source_role_vectors
                                if record["period_role"] == period_role
                                and record["lane_role"] == lane_role
                            ],
                        }
                    )
            for movement_role, cell in sorted(cells.items()):
                record = merged[(period_role, lane_role, movement_role)]
                vector = {
                    "assignment_kind": record["assignment_kind"],
                    "block_ordinal": record["block_ordinal"],
                    "bound_unit": record["bound_unit"],
                    "cell": cell,
                    "column_ordinal": record["column_ordinal"],
                    "endpoint_date": record["endpoint_date"],
                    "lane_role": lane_role,
                    "locator": record["locator"],
                    "movement_role": movement_role,
                    "period_date": record["period_date"],
                    "period_role": period_role,
                    "period_semantics_evidence": record["period_semantics_evidence"],
                    "resolved_period": record["resolved_period"],
                    "row_hierarchy_path_exact": record["row_hierarchy_path_exact"],
                    "row_id": record["row_id"],
                    "row_label_exact": record["row_label_exact"],
                    "source_block_ordinal": record["source_block_ordinal"],
                    "source_movement_role": record["source_movement_role"],
                }
                role_vectors.append(vector)
                if period_role != "CURRENT_PERIOD":
                    continue
                report_norm_id = bindings.get((lane_role, movement_role))
                if report_norm_id is None or not _is_source_observed_mapping_cell_v1(cell):
                    continue
                material = {
                    **canonical_clone_v1(vector),
                    "mapping_kind": (
                        "DECLARATIVE_EXACT_ADDITIVE_SOURCE_ROWS_ROLLFORWARD_PROPOSAL"
                        if cell["state"] == "AGGREGATED_EXACT_SOURCE_ROWS"
                        else "DECLARATIVE_EXACT_DIRECTIONAL_DEDUCTION_ROLLFORWARD_PROPOSAL"
                        if cell["state"] == "NORMALIZED_DIRECTIONAL_DEDUCTION"
                        else "DECLARATIVE_VISIBLE_ROLLFORWARD_CELL_PROPOSAL"
                    ),
                    "report_norm_id": report_norm_id,
                }
                potential_mappings.append(
                    {
                        **material,
                        "item_mapping_id": "gjfrfmv1:item:" + canonical_json_sha256_v1(material),
                    }
                )
    endpoint_continuity_receipts, endpoint_reasons = _two_period_endpoint_continuity_v1(
        role_vectors,
        compiled_specs=compiled_specs,
    )
    reasons.extend(endpoint_reasons)
    reasons = sorted(set(reasons))
    if complementary_continuation is not None:
        logical_classifications = [
            complementary_continuation["receipt"]["logical_classification"],
            *(
                item
                for item in component_classifications
                # The two physical halves are represented by the one logical
                # classification above.
                if item["locator"] != complementary_owner_locator
                and item["locator"] != complementary_continuation_locator
            ),
        ]
        orientation = classify_gemini_json_rollforward_cluster_layout_v1(
            logical_classifications
        )
    else:
        orientation = classify_gemini_json_rollforward_cluster_layout_v1(
            component_classifications
        )
    if orientation not in compiled_specs["layout"]["allowed_orientations"]:
        reasons.append("ROLLFORWARD_LAYOUT_ORIENTATION_NOT_DECLARED")
    mappings = [] if reasons else potential_mappings
    first = region_axis[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "bound_unit": (
                next(iter({unit for unit in bound_units if unit is not None}))
                if len({unit for unit in bound_units if unit is not None}) == 1
                else None
            ),
            "component_classifications": component_classifications,
            "component_region_axis_sha256": canonical_json_sha256_v1(region_axis),
            "duplicate_source_ambiguities": duplicate_source_ambiguities,
            **(
                {
                    "directional_deduction_normalization_receipts": (
                        directional_deduction_normalization_receipts
                    )
                }
                if directional_deduction_normalization_receipts
                else {}
            ),
            **(
                {
                    "horizontal_total_zero_recovery_receipts": (
                        horizontal_total_zero_recovery_receipts
                    )
                }
                if horizontal_total_zero_recovery_receipts
                else {}
            ),
            **(
                {"source_repair_overlay_receipts": source_repair_overlay_receipts}
                if source_repair_overlay_receipts
                else {}
            ),
            "endpoint_continuity_receipts": endpoint_continuity_receipts,
            "equations": equations,
            "lane_assignment_receipts": lane_assignment_receipts,
            "lane_population_assignment_receipts": [
                {
                    "block_ordinal": fragment["block_ordinal"],
                    "locator": canonical_clone_v1(fragment["locator"]),
                    "receipt": canonical_clone_v1(fragment["lane_population_assignment_receipt"]),
                }
                for fragment in fragments
                if fragment["lane_population_assignment_receipt"] is not None
            ],
            "lane_population_continuity_receipt": {
                "aggregate_population_axis": aggregate_population_axis,
                "rule": "SAME_EXACT_DECLARED_AGGREGATE_IDENTITY_ACROSS_PERIOD_COMPONENTS",
            },
            "orientation": orientation,
            "period_assignment_receipt": period_assignment_receipt,
            "period_lane_populations": {
                period_role: sorted(lanes_by_period[period_role]) for period_role in period_roles
            },
            "population_receipt": population_receipt,
            "potential_mapping_count": len(potential_mappings),
            "query_receipt": checked_query_receipt,
            "role_vectors": role_vectors,
            "rule": "EXACT_SIGNED_ROLLFORWARD_ONE_UNKNOWN_FULL_RANK",
            "source_role_vectors": source_role_vectors,
            "unresolved_frontiers": unresolved_frontiers,
            "unit_provenance_receipt": unit_provenance_receipt,
        },
        "component_regions": region_axis,
        "component_table_refs": [
            {"section_id": item["section_id"], "table_id": item["table_id"]}
            for item in region_axis
            if item["page_json_version_id"] == first["page_json_version_id"]
        ],
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": reasons,
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": UNRESOLVED if reasons else READY,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_rollforward_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Sequence[dict[str, Any]],
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
    document_fiscal_close_context_evidence: Mapping[str, Any] | None = None,
    document_unit_context_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild and exact-compare one candidate, including every provenance receipt."""

    rebuilt = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
        document_fiscal_close_context_evidence=(document_fiscal_close_context_evidence),
        document_unit_context_evidence=document_unit_context_evidence,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("roll-forward family candidate does not replay exactly")
    return rebuilt
