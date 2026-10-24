"""Pure whole-table root closure (Codex 0324-0326): synthetic inventory + disposition records, no I/O, no amounts."""

from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.root_closure_v1 import family_root_line_v1, root_closure_v1

ROOT = Path(__file__).resolve().parents[2]
TOP = ["TAX_FEES", "EMPLOYEE_EXPENSE", "ASSET_EXPENSE", "ADMIN_EXPENSE", "DEPOSIT_INSURANCE_EXPENSE",
       "OTHER_ASSET_PROVISION", "OTHER_OPERATING_EXPENSE"]
V, N = ("1", "1"), (None, None)  # printed / all-null money cells (amounts are irrelevant to topology)
T_ROOT = "UNLABELED_ORIGINAL_ROW_KIND_TOTAL:NULL_LABEL"


@pytest.fixture(scope="module")
def family():
    return load_notes_config_v1(ROOT).families["OPERATING_EXPENSE"]


def lpb():
    """LPB FULL69 page 64's ORIGINAL layout: (label, kind, values, parent index, line)."""

    return [
        ("Chi nộp thuế và các khoản phí, lệ phí", "ITEM", V, None, "TAX_FEES"),               # r1
        ("Chi phí cho nhân viên", "ITEM", V, None, "EMPLOYEE_EXPENSE"),                       # r2
        ("Trong đó:", "GROUP", N, 1, None),                                                    # r3 wrapper of r2
        ("Chi lương và phụ cấp", "ITEM", V, 2, "SALARY_ALLOWANCE"),                           # r4
        ("Chi phí khác cho nhân viên", "ITEM", V, 2, "OTHER_EMPLOYEE_EXPENSE"),               # r5
        ("Chi về tài sản", "ITEM", V, None, "ASSET_EXPENSE"),                                  # r6
        ("Trong đó:", "GROUP", N, 5, None),                                                    # r7 wrapper of r6
        ("Khấu hao tài sản cố định", "ITEM", V, 6, "DEPRECIATION_EXPENSE"),                   # r8
        ("Chi cho hoạt động quản lý công vụ", "ITEM", V, None, "ADMIN_EXPENSE"),               # r9
        ("Trong đó:", "GROUP", N, 8, None),                                                    # r10 wrapper of r9
        ("Công tác phí", "ITEM", V, 9, "TRAVEL_EXPENSE"),                                     # r11
        ("Chi phí khác cho hoạt động quản lý", "ITEM", V, 9, None),                           # r12 unread detail
        ("Chi nộp phí bảo hiểm, bảo hiểm tiền gửi của khách hàng", "ITEM", V, None, "DEPOSIT_INSURANCE_EXPENSE"),  # r13
        ("Chi phí dự phòng khác", "ITEM", V, None, "OTHER_ASSET_PROVISION"),                  # r14
        ("Chi phí hoạt động khác", "ITEM", V, None, "OTHER_OPERATING_EXPENSE"),               # r15
        (None, "TOTAL", V, None, "TOTAL_OPERATING_EXPENSE"),                                   # r16 unlabeled root (T)
    ]


PAGE_BLOB = "a" * 64  # the stored two-LF page bytes' SHA-256, shared by the inventory page and the notes bridge


def build(spec, *, statuses=("PASS", "PASS"), terms=None, reasons=None, dispositions=None, root_reason=T_ROOT, texts=None):
    """(inventory, disposition) of one EXACT single table from a compact row spec.

    The ORIGINAL table prints a TEXT column first (a note reference such as "28"; ``texts`` gives it per row, null by
    default) and two MONEY columns, which the notes lanes c2 / c3 occupy through the identity bridge column map.
    """

    paths, inv_rows, note_rows = [], [], []
    reasons, dispositions, texts = reasons or {}, dispositions or {}, texts or {}
    for i, (label, kind, values, parent, line) in enumerate(spec):
        path = (paths[parent] if parent is not None else []) + [label]
        paths.append(path)
        original = [texts.get(i), *values]
        inv_rows.append({"record_type": "row", "document_ordinal": 69, "page_json_version_id": "v64",
                         "pointer": f"/sections/0/tables/0/rows/{i}", "row_ordinal": i + 1,
                         # The producer's real envelope (inventory _fields): {"present": bool, "value": raw}.
                         "fields": {key: {"present": True, "value": value} for key, value in
                                    (("row_kind", kind), ("label_exact", label), ("hierarchy_path_exact", path))},
                         "value_axis": {"count": 3, "item_types": [type(v).__name__ for v in original],
                                        "null_column_ordinals": [c for c, v in enumerate(original, 1) if v is None]}})
        valued = any(v is not None for v in values)
        disposition = dispositions.get(i) or ("MEMBER" if line else ("SOURCE_ONLY" if valued else "HEADING"))
        reason = reasons.get(i) or (("LINE_RULE" if label else root_reason) if line else ("NO_LINE_RULE" if valued else "NO_VALUES"))
        note_rows.append({"row_id": f"r{i + 1}", "label_exact": label, "parent_row_id": None if parent is None else f"r{parent + 1}",
                          "line": line if disposition == "MEMBER" else None, "disposition": disposition, "reason": reason})
    frontier = terms if terms is not None else [line for (_l, _k, _v, parent, line) in spec if parent is None and line in TOP]
    inventory = {"page": {"record_type": "page", "axis": {"page_json_version_id": "v64", "physical_page": 64},
                          "source_proof": {"stored_blob_two_lf_sha256": PAGE_BLOB}},
                 "table": {"record_type": "table", "pointer": "/sections/0/tables/0", "page_json_version_id": "v64"},
                 "columns": [{"record_type": "column", "column_ordinal": c, "column_exact": {"value_kind": kind}}
                             for c, kind in ((1, "TEXT"), (2, "MONEY"), (3, "MONEY"))],
                 "rows": inv_rows, "unsupported": []}
    disposition = {"family": "OPERATING_EXPENSE", "status": "EVALUATED", "fragments": [],
                   "source_bridges": [{"status": "EXACT", "page_json_version_id": "v64", "section_ordinal": 1, "table_ordinal": 1,
                                       "original_blob_sha256": PAGE_BLOB, "row_count": len(spec),
                                       "column_map": {"c1": 1, "c2": 2, "c3": 3}}],
                   "rows": note_rows, "lanes": [{"column_id": "c2"}, {"column_id": "c3"}],
                   "equations": [{"name": "EMPLOYEE_FROM_DETAIL", "lane": lane, "status": "PASS",
                                  "terms": ["SALARY_ALLOWANCE", "OTHER_EMPLOYEE_EXPENSE"]} for lane in ("c2", "c3")]
                   + [{"name": "TOTAL_FROM_TOP_LEVEL_LINES", "lane": lane, "status": status, "terms": list(frontier)}
                      for lane, status in zip(("c2", "c3"), statuses, strict=True) if status is not None]}
    return inventory, disposition


def lane_status(result):
    return [lane["status"] for lane in result["lanes"]]


def test_the_family_root_is_the_one_equation_target_that_is_no_term(family):
    assert family_root_line_v1(family) == "TOTAL_OPERATING_EXPENSE"


def test_lpb_layout_with_its_unlabeled_root_closes_every_lane(family):
    result = root_closure_v1(*build(lpb()), family)
    assert result["status"] == "EVALUATED" and lane_status(result) == ["ROOT_CLOSED", "ROOT_CLOSED"]
    classes = {row["row_ordinal"]: (row["class"], row.get("owner_row_ordinal")) for row in result["rows"]}
    assert classes[1] == ("FRONTIER", None) and classes[3] == ("WRAPPER", 2) and classes[4] == ("DETAIL", 2)
    assert classes[12] == ("DETAIL", 9)  # the unread admin detail, through the r10 wrapper, owned once by ADMIN
    assert classes[16] == ("ROOT", None) and len(classes) == 16  # every row partitioned


def test_a_labeled_root_needs_the_same_positive_closure(family):
    spec = lpb()
    spec[-1] = ("Tổng chi phí hoạt động", "ITEM", V, None, "TOTAL_OPERATING_EXPENSE")
    assert lane_status(root_closure_v1(*build(spec), family)) == ["ROOT_CLOSED", "ROOT_CLOSED"]


def test_the_producers_declared_rounding_pass_is_a_passing_root_equation(family):
    result = root_closure_v1(*build(lpb(), statuses=("PASS_WITHIN_DECLARED_ROUNDING", "PASS")), family)
    assert lane_status(result) == ["ROOT_CLOSED", "ROOT_CLOSED"]
    assert result["lanes"][0]["root_equation_status"] == "PASS_WITHIN_DECLARED_ROUNDING"


@pytest.mark.parametrize("status", ["FAIL", "NOT_EVALUABLE", "INCOMPLETE_UNREAD_ROWS_IN_SPAN"])
def test_only_the_lane_whose_root_equation_does_not_pass_stays_open(family, status):
    assert lane_status(root_closure_v1(*build(lpb(), statuses=(status, "PASS")), family)) == [
        f"NOT_ROOT_CLOSED:ROOT_EQUATION_{status}", "ROOT_CLOSED"]


def test_a_local_employee_proof_is_no_root_proof(family):
    spec = [row for row in lpb() if row[4] != "TOTAL_OPERATING_EXPENSE"]  # no printed root at all
    result = root_closure_v1(*build(spec, statuses=(None, None)), family)
    assert lane_status(result) == ["NOT_ROOT_CLOSED:ROOT_ROWS_0", "NOT_ROOT_CLOSED:ROOT_ROWS_0"]


def _insert(spec, at, row):
    spec.insert(at, row)
    return [(label, kind, values, None if parent is None else (parent + 1 if parent >= at else parent), line)
            for label, kind, values, parent, line in spec]


@pytest.mark.parametrize("mutate,why", [
    (lambda s: _insert(s, 0, ("Chi phí chưa phân loại", "ITEM", V, None, None)), "UNACCOUNTED_VALUED_ROW:r1"),
    (lambda s: _insert(s, 13, ("Chi phí chưa phân loại", "ITEM", V, None, None)), "UNACCOUNTED_VALUED_ROW:r14"),
    (lambda s: s + [("Dự phòng đầu tư dài hạn", "ITEM", N, None, None)], "ROOT_NOT_FINAL_SOURCE_ROW:r16"),
    (lambda s: [r if i != 13 else (r[0], r[1], N, None, None) for i, r in enumerate(s)], "BLANK_ROOT_OPERAND:r14"),
    (lambda s: _insert(s, 14, ("Tổng chi phí hoạt động", "ITEM", N, None, None)), "BLANK_PRINTED_ROOT_LINE:r15"),
    (lambda s: [r if i != 12 else (r[0], r[1], r[2], 8, r[4]) for i, r in enumerate(s)], "ROOT_TERM_NOT_AT_SOURCE_TOP_LEVEL:r13"),
    (lambda s: [r if i != 7 else (r[0], r[1], r[2], None, r[4]) for i, r in enumerate(s)], "UNACCOUNTED_VALUED_ROW:r8"),
    (lambda s: [r if i != 9 else (r[0], "ITEM", r[2], r[3], r[4]) for i, r in enumerate(s)], "UNACCOUNTED_VALUED_ROW:r11"),
    (lambda s: [r if i != 9 else (r[0], r[1], ("1", None), r[3], r[4]) for i, r in enumerate(s)], "UNACCOUNTED_VALUED_ROW:r11"),
    (lambda s: _insert(s, 0, ("Ghi chú", "ITEM", N, None, None)), "UNRESOLVED_BLANK_ROW:r1"),
    (lambda s: _insert(s, 15, (None, "TOTAL", V, None, "TOTAL_OPERATING_EXPENSE")), "ROOT_ROWS_2"),
    (lambda s: s[:-1] + [("Tổng chi phí hoạt động", "ITEM", V, 8, "TOTAL_OPERATING_EXPENSE")], "ROOT_NOT_AT_SOURCE_TOP_LEVEL:r16"),
])
def test_every_row_is_partitioned_or_refuses_the_closure(family, mutate, why):
    spec = mutate(lpb())
    result = root_closure_v1(*build(spec), family)
    assert result["status"] == "EVALUATED" and lane_status(result) == [f"NOT_ROOT_CLOSED:{why}"] * 2


@pytest.mark.parametrize("disposition,reason,why", [
    ("AMBIGUOUS", "ROW_MATCHES_SEVERAL_LINES", "UNACCOUNTED_VALUED_ROW:AMBIGUOUS:r12"),
    ("SOURCE_ONLY", "ROW_VETO:STOCK_BASIS", "UNACCOUNTED_VALUED_ROW:SOURCE_ONLY:r12"),
])
def test_ambiguous_or_vetoed_rows_are_never_accounted_as_detail(family, disposition, reason, why):
    result = root_closure_v1(*build(lpb(), dispositions={11: disposition}, reasons={11: reason}), family)
    assert lane_status(result) == [f"NOT_ROOT_CLOSED:{why}"] * 2


def test_a_text_note_reference_never_makes_a_blank_root_operand_valued(family):
    # Codex 0328: ORIGINAL ["28", null, null] is numerically blank - its two MONEY operands are unknown.
    spec = [r if i != 13 else (r[0], r[1], N, None, None) for i, r in enumerate(lpb())]
    result = root_closure_v1(*build(spec, texts={13: "28"}), family)
    assert lane_status(result) == ["NOT_ROOT_CLOSED:BLANK_ROOT_OPERAND:r14"] * 2


def test_a_wrapper_needs_every_original_cell_null_not_only_its_money_cells(family):
    # A "Trong đó:" GROUP printing a TEXT reference is no transparent wrapper: the lines under it reach no frontier owner.
    result = root_closure_v1(*build(lpb(), texts={9: "x"}), family)
    assert lane_status(result) == ["NOT_ROOT_CLOSED:UNACCOUNTED_VALUED_ROW:r11"] * 2


def test_an_explicit_null_label_is_kept_distinct_from_a_missing_one(family):
    # LPB's unlabeled root prints label_exact = null: {"present": true, "value": null} closes; the same field ABSENT
    # from the ORIGINAL row is a different source fact and is never read as that null (Codex 0330/0332).
    inventory, disposition = build(lpb())
    assert inventory["rows"][15]["fields"]["label_exact"] == {"present": True, "value": None}
    assert lane_status(root_closure_v1(inventory, disposition, family)) == ["ROOT_CLOSED", "ROOT_CLOSED"]
    inventory["rows"][15]["fields"]["label_exact"] = {"present": False, "value": None}
    assert root_closure_v1(inventory, disposition, family)["status"] == "UNRESOLVED:ORIGINAL_ROW_FIELD_ABSENT:label_exact:r16"


def test_root_equation_terms_must_be_exactly_the_frontier(family):
    result = root_closure_v1(*build(lpb(), terms=[t for t in TOP if t != "TAX_FEES"]), family)
    assert lane_status(result) == ["NOT_ROOT_CLOSED:ROOT_EQUATION_TERMS_DIFFER_FROM_FRONTIER"] * 2


def _merged(inv, disp):
    disp["fragments"] = [{"physical_page": 64}, {"physical_page": 65}]


def _shifted(inv, disp):
    disp["source_bridges"][0]["status"] = "EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT"


def _unsupported(inv, disp):
    inv["unsupported"] = [{"record_type": "unsupported_shape", "pointer": "/sections/0/tables/0/rows/3/values_exact"}]


def _row_count(inv, disp):
    inv["rows"].pop()


def _label(inv, disp):
    disp["rows"][0]["label_exact"] = "khác"


def _value_state(inv, disp):
    disp["rows"][2]["disposition"] = "SOURCE_ONLY"  # notes says valued, the ORIGINAL row is all null


def _other_table(inv, disp):
    disp["source_bridges"][0]["table_ordinal"] = 2


def _not_evaluated(inv, disp):
    disp["status"] = "REJECTED"


def _page_binding(inv, disp):
    disp["source_bridges"][0]["original_blob_sha256"] = "b" * 64


def _lane_outside_map(inv, disp):
    disp["lanes"].append({"column_id": "c4"})


def _lane_on_text(inv, disp):
    disp["lanes"][0]["column_id"] = "c1"


def _parent_edge(inv, disp):
    disp["rows"][3]["parent_row_id"] = "r2"  # notes says EMPLOYEE; the ORIGINAL path proves the r3 wrapper


def _field_absent(inv, disp):
    inv["rows"][0]["fields"]["label_exact"] = {"present": False, "value": None}  # missing is not an explicit null


def _field_flat(inv, disp):
    inv["rows"][0]["fields"]["label_exact"] = "Chi nộp thuế và các khoản phí, lệ phí"  # an unenveloped raw value


@pytest.mark.parametrize("mutate,why", [
    (_merged, "CONTINUATION_MERGED_TABLE_NOT_SUPPORTED_V1"),
    (_shifted, "SOURCE_BRIDGE_NOT_EXACT:EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT"),
    (_unsupported, "UNSUPPORTED_ORIGINAL_SHAPE:/sections/0/tables/0/rows/3/values_exact"),
    (_row_count, "ROW_COUNT_DIFFERS"),
    (_label, "ROW_AXIS_DIFFERS:r1"),
    (_value_state, "VALUE_STATE_DISAGREES:r3"),
    (_other_table, "BRIDGE_AND_INVENTORY_NAME_DIFFERENT_TABLES"),
    (_not_evaluated, "TABLE_NOT_EVALUATED:REJECTED"),
    (_page_binding, "PAGE_BINDING_DIFFERS"),
    (_lane_outside_map, "LANE_COLUMN_NOT_IN_PROVEN_COLUMN_MAP:c4"),
    (_lane_on_text, "LANE_COLUMN_NOT_ORIGINAL_MONEY:c1"),
    (_parent_edge, "PARENT_EDGE_DIFFERS_FROM_ORIGINAL:r4"),
    (_field_absent, "ORIGINAL_ROW_FIELD_ABSENT:label_exact:r1"),
    (_field_flat, "ORIGINAL_ROW_FIELD_ENVELOPE_MALFORMED:label_exact:r1"),
])
def test_unprovable_inputs_are_named_unresolved_never_closed(family, mutate, why):
    inventory, disposition = build(lpb())
    mutate(inventory, disposition)
    result = root_closure_v1(inventory, disposition, family)
    assert result["status"] == f"UNRESOLVED:{why}" and result["lanes"] == []
