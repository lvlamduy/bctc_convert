from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from bctc_ai.core.atomic import atomic_write_bytes, atomic_write_json
from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.schema.xlsx_reader import read_rows

if TYPE_CHECKING:
    from bctc_ai.schema.registry import SchemaItem


BUSINESS_UPDATE_AUDIT = "data/registered/schema_business_update_5712_5713_5714_5718.json"

CDKT_BASELINE_WORKBOOK = "template/Bank_CDKT_ReportNormId.xlsx"
KQKD_BASELINE_WORKBOOK = "template/Bank_KQKD_ReportNormId.xlsx"
LCTT_BASELINE_WORKBOOK = "template/Bank_LCTT_ReportNormId.xlsx"
TM_BASELINE_WORKBOOK = "template/Bank_TM_ReportNormId.xlsx"
CDKT_WORKBOOK = "template/Bank_CDKT_ReportNormId.v2.xlsx"
KQKD_WORKBOOK = "template/Bank_KQKD_ReportNormId.v2.xlsx"
LCTT_WORKBOOK = "template/Bank_LCTT_ReportNormId.v2.xlsx"
TM_WORKBOOK = "template/Bank_TM_ReportNormId.v2.xlsx"

CDKT_BEFORE_SHA256 = "a07ff47f7c41011fe4ca5a66681106d476586ded9013b5874cbb9f67a6ad8486"
KQKD_BEFORE_SHA256 = "6033001b85a236fce4b29437d56cc02d7c6a21f95e82b43de043b1268eb74615"
LCTT_BEFORE_SHA256 = "2c9d52737c492f115895eab9a571da2269fcfd3c3e77539ec581782e579d260a"
TM_BEFORE_SHA256 = "fa284e3af1f90c8a206308f63e6d35e77a9fbf1abcaf60abcb59877c47275140"

CDKT_BEFORE_ROW_COUNT = 78
KQKD_BEFORE_ROW_COUNT = 25
CDKT_AFTER_ROW_COUNT = 79
KQKD_AFTER_ROW_COUNT = 26
LCTT_BEFORE_ROW_COUNT = 108
LCTT_AFTER_ROW_COUNT = 109
TM_BEFORE_ROW_COUNT = 1386
TM_AFTER_ROW_COUNT = 1418

CDKT_TOTAL_EQUITY_ID = 5712
CDKT_TOTAL_EQUITY_NAME = "TỔNG VỐN CHỦ SỞ HỮU"
CDKT_TOTAL_EQUITY_SOURCE_ROW = 78
CDKT_TOTAL_EQUITY_DISPLAY_ORDER = 76
CDKT_TOTAL_EQUITY_PREDECESSOR_ID = 4306
CDKT_TOTAL_EQUITY_SUCCESSOR_ID = 4305

KQKD_TOTAL_OPERATING_INCOME_ID = 5713
KQKD_TOTAL_OPERATING_INCOME_NAME = "TỔNG THU NHẬP HOẠT ĐỘNG"
KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW = 15
KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER = 13
KQKD_TOTAL_OPERATING_INCOME_PREDECESSOR_ID = 4393
KQKD_TOTAL_OPERATING_INCOME_SUCCESSOR_ID = 4391

LCTT_INVESTMENT_CONTRIBUTION_NET_ID = 5714
LCTT_INVESTMENT_CONTRIBUTION_NET_NAME = "Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác"
LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW = 93
LCTT_INVESTMENT_CONTRIBUTION_NET_DISPLAY_ORDER = 91
LCTT_INVESTMENT_CONTRIBUTION_NET_PREDECESSOR_ID = 4146
LCTT_INVESTMENT_CONTRIBUTION_NET_SUCCESSOR_ID = 4120

TM_TOTAL_INTERBANK_PROVISION_ID = 5718
TM_TOTAL_INTERBANK_PROVISION_NAME = (
    "Tổng dự phòng rủi ro tiền gửi và cho vay các tổ chức tín dụng khác"
)
TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW = 34
TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER = 32
TM_TOTAL_INTERBANK_PROVISION_PREDECESSOR_ID = 591
TM_TOTAL_INTERBANK_PROVISION_SUCCESSOR_ID = 592

TM_EDUCATION_ID = 737
TM_EDUCATION_OLD_NAME = " + Giáo dục và đào tạo, y tế"
TM_EDUCATION_NAME = "Giáo dục & Đào tạo"
TM_EDUCATION_BASELINE_SOURCE_ROW = 179

TM_HEALTH_SOCIAL_ID = 5719
TM_HEALTH_SOCIAL_NAME = "Y tế & hoạt động trợ giúp xã hội"
TM_HEALTH_SOCIAL_SOURCE_ROW = 182
TM_HEALTH_SOCIAL_DISPLAY_ORDER = 180
TM_HEALTH_SOCIAL_PREDECESSOR_ID = TM_EDUCATION_ID
TM_HEALTH_SOCIAL_SUCCESSOR_ID = 738

TM_ARTS_RECREATION_ID = 5720
TM_ARTS_RECREATION_NAME = "Ngành nghệ thuật vui chơi giải trí"
TM_ARTS_RECREATION_SOURCE_ROW = 189
TM_ARTS_RECREATION_DISPLAY_ORDER = 187
TM_ARTS_RECREATION_PREDECESSOR_ID = 743
TM_ARTS_RECREATION_SUCCESSOR_ID = 5721

TM_OTHER_SERVICES_ID = 5721
TM_OTHER_SERVICES_NAME = "Ngành hoạt động dịch vụ khác"
TM_OTHER_SERVICES_SOURCE_ROW = 190
TM_OTHER_SERVICES_DISPLAY_ORDER = 188
TM_OTHER_SERVICES_PREDECESSOR_ID = 5720
TM_OTHER_SERVICES_SUCCESSOR_ID = 5722

TM_HOUSEHOLD_EMPLOYMENT_ID = 5722
TM_HOUSEHOLD_EMPLOYMENT_NAME = (
    "Ngành hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất sản phẩm "
    "vật chất và dịch vụ tự tiêu dùng của hộ gia đình"
)
TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW = 191
TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER = 189
TM_HOUSEHOLD_EMPLOYMENT_PREDECESSOR_ID = 5721
TM_HOUSEHOLD_EMPLOYMENT_SUCCESSOR_ID = 744

TM_PURCHASED_PRINCIPAL_ID = 5738
TM_PURCHASED_PRINCIPAL_NAME = "Nợ gốc đã mua"
TM_PURCHASED_PRINCIPAL_SOURCE_ROW = 256
TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER = 254
TM_PURCHASED_PRINCIPAL_PREDECESSOR_ID = 803
TM_PURCHASED_PRINCIPAL_SUCCESSOR_ID = 5739

TM_PURCHASED_INTEREST_ID = 5739
TM_PURCHASED_INTEREST_NAME = "Lãi của khoản nợ đã mua"
TM_PURCHASED_INTEREST_SOURCE_ROW = 257
TM_PURCHASED_INTEREST_DISPLAY_ORDER = 255
TM_PURCHASED_INTEREST_PREDECESSOR_ID = 5738
TM_PURCHASED_INTEREST_SUCCESSOR_ID = 804

TM_GOVERNMENT_GUARANTEED_DEBT_ID = 5740
TM_GOVERNMENT_GUARANTEED_DEBT_NAME = "Chứng khoán nợ do Chính phủ bảo lãnh"
TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW = 262
TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER = 260
TM_GOVERNMENT_GUARANTEED_DEBT_PREDECESSOR_ID = 807
TM_GOVERNMENT_GUARANTEED_DEBT_SUCCESSOR_ID = 808

TM_FX_BUY_ID = 5741
TM_FX_BUY_NAME = "Cam kết mua ngoại tệ"
TM_FX_BUY_SOURCE_ROW = 772
TM_FX_BUY_DISPLAY_ORDER = 770
TM_FX_BUY_PREDECESSOR_ID = 1301
TM_FX_BUY_SUCCESSOR_ID = 5742

TM_FX_SELL_ID = 5742
TM_FX_SELL_NAME = "Cam kết bán ngoại tệ"
TM_FX_SELL_SOURCE_ROW = 773
TM_FX_SELL_DISPLAY_ORDER = 771
TM_FX_SELL_PREDECESSOR_ID = 5741
TM_FX_SELL_SUCCESSOR_ID = 1302

TM_SWAP_BUY_ID = 5743
TM_SWAP_BUY_NAME = "Cam kết mua giao dịch hoán đổi tiền tệ"
TM_SWAP_BUY_SOURCE_ROW = 775
TM_SWAP_BUY_DISPLAY_ORDER = 773
TM_SWAP_BUY_PREDECESSOR_ID = 1302
TM_SWAP_BUY_SUCCESSOR_ID = 5744

TM_SWAP_SELL_ID = 5744
TM_SWAP_SELL_NAME = "Cam kết bán giao dịch hoán đổi tiền tệ"
TM_SWAP_SELL_SOURCE_ROW = 776
TM_SWAP_SELL_DISPLAY_ORDER = 774
TM_SWAP_SELL_PREDECESSOR_ID = 5743
TM_SWAP_SELL_SUCCESSOR_ID = 1303

TM_MARGIN_LOAN_CANONICAL_NAME = "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
TM_MARGIN_LOAN_TYPE_ID = 5745
TM_MARGIN_LOAN_TYPE_SOURCE_ROW = 170
TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER = 168
TM_MARGIN_LOAN_TYPE_PREDECESSOR_ID = 726
TM_MARGIN_LOAN_TYPE_SUCCESSOR_ID = 727

TM_MARGIN_LOAN_QUALITY_ID = 5746
TM_MARGIN_LOAN_QUALITY_NAME = "Trong đó: Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
TM_MARGIN_LOAN_QUALITY_SOURCE_ROW = 197
TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER = 195
TM_MARGIN_LOAN_QUALITY_PREDECESSOR_ID = 747
TM_MARGIN_LOAN_QUALITY_SUCCESSOR_ID = 748

TM_MARGIN_LOAN_MATURITY_ID = 5747
TM_MARGIN_LOAN_MATURITY_SOURCE_ROW = 206
TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER = 204
TM_MARGIN_LOAN_MATURITY_PREDECESSOR_ID = 755
TM_MARGIN_LOAN_MATURITY_SUCCESSOR_ID = 756

TM_MARGIN_LOAN_BUSINESS_ID = 5748
TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW = 234
TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER = 232
TM_MARGIN_LOAN_BUSINESS_PREDECESSOR_ID = 782
TM_MARGIN_LOAN_BUSINESS_SUCCESSOR_ID = 783

TM_MARGIN_LOAN_INDUSTRY_ID = 5749
TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW = 194
TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER = 192
TM_MARGIN_LOAN_INDUSTRY_PREDECESSOR_ID = 745
TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID = 746

TM_PAGE50_TAX_INSERT_SOURCE_ROW = 702
TM_PAGE50_TAX_INSERT_DISPLAY_ORDER = 700
TM_PAGE50_TAX_SCHEMA_ITEMS: tuple[tuple[int, str], ...] = (
    (5723, "Chi phí thuế thu nhập hiện hành"),
    (5724, "Năm hiện hành"),
    (5725, "Chi phí/(hoàn nhập) thuế thu nhập hoãn lại"),
    (5726, "Chi phí/(thu nhập) thuế thu nhập hoãn lại"),
    (5727, "Chi phí thuế thu nhập"),
    (5728, "Tổng lợi nhuận theo kế toán trước thuế hợp nhất"),
    (
        5729,
        "Thu nhập không chịu thuế (bao gồm cổ tức, lợi nhuận từ các đơn vị, các khoản "
        "điều chỉnh hợp nhất không chịu thuế) và các khoản khác",
    ),
    (5730, "Các chi phí không được khấu trừ của riêng Ngân hàng"),
    (5731, "Thu nhập chịu thuế TNDN ước tính tại Việt Nam"),
    (5732, "Chi phí thuế TNDN hiện hành riêng Ngân hàng (i)"),
    (
        5733,
        "Điều chỉnh trong năm cho thuế thu nhập hiện hành của các năm trước (ii)",
    ),
    (5734, "Chi phí thuế TNDN chi nhánh nước ngoài (iii)"),
    (5735, "Chi phí thuế TNDN của các công ty con (iv)"),
    (5736, "Chi phí/(hoàn nhập) thuế TNDN hoãn lại (v)"),
    (5737, "Chi phí thuế TNDN (i+ii+iii+iv+v)"),
)
TM_PAGE50_TAX_SCHEMA_IDS = tuple(schema_id for schema_id, _name in TM_PAGE50_TAX_SCHEMA_ITEMS)
TM_PAGE50_TAX_PREDECESSOR_ID = 1246
TM_PAGE50_TAX_SUCCESSOR_ID = 1247

TM_LOAN_INDUSTRY_PARENT_ID = 727
TM_LOAN_BUSINESS_PARENT_ID = 766
TM_LOAN_BUSINESS_OTHER_ID = 782
TM_PROVISION_MOVEMENT_ID = 783
TM_GENERAL_PROVISION_MOVEMENT_ID = 784
TM_SPECIFIC_PROVISION_MOVEMENT_ID = 792

CDKT_4350_OLD_NAME = "Chứng khoán đầu tư sẵn sàng để hàng"
CDKT_4350_CORRECTED_NAME = "Chứng khoán đầu tư sẵn sàng để bán"
TM_770_OLD_NAME = "+ Công ty TNHH MTV vốn nhà nước trên 50%"
TM_770_CORRECTED_NAME = "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%"
TM_770_BASELINE_SOURCE_ROW = 212

REVIEWED_EXTERNAL_IDS = frozenset((*range(5701, 5712), 5715, 5716, 5717))
NEW_SCHEMA_IDS = frozenset(
    {
        CDKT_TOTAL_EQUITY_ID,
        KQKD_TOTAL_OPERATING_INCOME_ID,
        LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
        TM_TOTAL_INTERBANK_PROVISION_ID,
        TM_HEALTH_SOCIAL_ID,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
        *TM_PAGE50_TAX_SCHEMA_IDS,
        TM_PURCHASED_PRINCIPAL_ID,
        TM_PURCHASED_INTEREST_ID,
        TM_GOVERNMENT_GUARANTEED_DEBT_ID,
        TM_FX_BUY_ID,
        TM_FX_SELL_ID,
        TM_SWAP_BUY_ID,
        TM_SWAP_SELL_ID,
        TM_MARGIN_LOAN_TYPE_ID,
        TM_MARGIN_LOAN_QUALITY_ID,
        TM_MARGIN_LOAN_MATURITY_ID,
        TM_MARGIN_LOAN_BUSINESS_ID,
        TM_MARGIN_LOAN_INDUSTRY_ID,
    }
)

CDKT_4325_COMPONENTS = (4364, 4365, 4342, 4341, 4343, 5699)
CDKT_TOTAL_EQUITY_COMPONENTS = (4325, 4306)
KQKD_TOTAL_OPERATING_INCOME_COMPONENTS = (4385, 4386, 4387, 4388, 4389, 4390, 4393)
LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS = (4120, 4121)
TM_TOTAL_INTERBANK_PROVISION_COMPONENTS = (583, 590)
TM_PROVISION_MOVEMENT_COMPONENTS = (
    TM_GENERAL_PROVISION_MOVEMENT_ID,
    TM_SPECIFIC_PROVISION_MOVEMENT_ID,
)
TM_PAGE50_TAX_FORMULAS = (
    (5727, (5723, 5725)),
    (5731, (5728, 5729, 5730)),
    (5737, (5732, 5733, 5734, 5735, 5736)),
)
TM_FX_COMMITMENT_COMPONENTS = (TM_FX_BUY_ID, TM_FX_SELL_ID, 1302)
TM_SWAP_COMMITMENT_COMPONENTS = (TM_SWAP_BUY_ID, TM_SWAP_SELL_ID)

BUSINESS_FORMULAS: tuple[dict[str, object], ...] = (
    {
        "statement_type": "CDKT",
        "schema_id": 4325,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_4325_COMPONENTS),
    },
    {
        "statement_type": "CDKT",
        "schema_id": CDKT_TOTAL_EQUITY_ID,
        "operator": "SUM",
        "component_schema_ids": list(CDKT_TOTAL_EQUITY_COMPONENTS),
    },
    {
        "statement_type": "KQKD",
        "schema_id": KQKD_TOTAL_OPERATING_INCOME_ID,
        "operator": "SUM",
        "component_schema_ids": list(KQKD_TOTAL_OPERATING_INCOME_COMPONENTS),
    },
    {
        "statement_type": "LCTT",
        "schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
        "operator": "SUM",
        "component_schema_ids": list(LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS),
    },
    {
        "statement_type": "TM",
        "schema_id": TM_TOTAL_INTERBANK_PROVISION_ID,
        "operator": "SUM",
        "component_schema_ids": list(TM_TOTAL_INTERBANK_PROVISION_COMPONENTS),
    },
    {
        "statement_type": "TM",
        "schema_id": TM_PROVISION_MOVEMENT_ID,
        "operator": "SUM",
        "component_schema_ids": list(TM_PROVISION_MOVEMENT_COMPONENTS),
    },
    *(
        {
            "statement_type": "TM",
            "schema_id": schema_id,
            "operator": "SUM",
            "component_schema_ids": list(component_ids),
        }
        for schema_id, component_ids in TM_PAGE50_TAX_FORMULAS
    ),
    {
        "statement_type": "TM",
        "schema_id": 1301,
        "operator": "SUM",
        "component_schema_ids": list(TM_FX_COMMITMENT_COMPONENTS),
    },
    {
        "statement_type": "TM",
        "schema_id": 1302,
        "operator": "SUM",
        "component_schema_ids": list(TM_SWAP_COMMITMENT_COMPONENTS),
    },
)

_SHEET_MEMBER = "xl/worksheets/sheet1.xml"
_SHARED_STRINGS_MEMBER = "xl/sharedStrings.xml"
_TARGET_MEMBERS = frozenset({_SHEET_MEMBER, _SHARED_STRINGS_MEMBER})
_ROW_PATTERN = re.compile(rb'<row r="(?P<row>\d+)"[^>]*>.*?</row>', re.DOTALL)


class BusinessSchemaUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class BusinessSchemaUpdateResult:
    status: str
    audit_path: str
    workbook_sha256: dict[str, str]


def _member_hashes(payload: bytes) -> dict[str, str]:
    with ZipFile(io.BytesIO(payload)) as archive:
        return {
            info.filename: hashlib.sha256(archive.read(info.filename)).hexdigest()
            for info in archive.infolist()
        }


def _identity_records(path: Path) -> list[dict[str, object]]:
    return [
        {
            "source_row": source_row,
            "ordinal": row.get("A", ""),
            "report_norm_id": row.get("B", ""),
            "report_norm_name": row.get("C", ""),
        }
        for source_row, row in enumerate(read_rows(path), start=1)
    ]


def _item_pairs(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "report_norm_id": record["report_norm_id"],
            "report_norm_name": record["report_norm_name"],
        }
        for record in records
        if record["report_norm_id"] != "ReportNormId"
    ]


def _records_hash(records: Iterable[dict[str, object]]) -> str:
    return stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records
    )


def _replace_once(payload: bytes, old: bytes, new: bytes, *, description: str) -> bytes:
    if payload.count(old) != 1:
        raise BusinessSchemaUpdateError(f"expected exactly one {description} marker")
    return payload.replace(old, new, 1)


def _xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _patch_shared_strings(
    payload: bytes,
    *,
    append_name: str,
    replace_name: tuple[str, str] | None = None,
) -> tuple[bytes, int]:
    escaped_append_name = _xml_escape(append_name).encode("utf-8")
    exact_name_pattern = re.compile(rb"<t(?:\s[^>]*)?>" + re.escape(escaped_append_name) + rb"</t>")
    if exact_name_pattern.search(payload):
        raise BusinessSchemaUpdateError(f"shared string already contains {append_name!r}")
    if replace_name is not None:
        old_name, new_name = replace_name
        payload = _replace_once(
            payload,
            f"<t>{_xml_escape(old_name)}</t>".encode(),
            f"<t>{_xml_escape(new_name)}</t>".encode(),
            description=f"shared-string correction {old_name!r}",
        )

    root_match = re.search(rb"<sst\b[^>]*>", payload)
    if root_match is None:
        raise BusinessSchemaUpdateError("sharedStrings.xml has no sst root")
    root = root_match.group(0)
    count_match = re.search(rb'\bcount="(\d+)"', root)
    unique_match = re.search(rb'\buniqueCount="(\d+)"', root)
    if count_match is None or unique_match is None:
        raise BusinessSchemaUpdateError("sharedStrings.xml lacks count metadata")
    count = int(count_match.group(1))
    unique_count = int(unique_match.group(1))
    if unique_count != payload.count(b"<si>"):
        raise BusinessSchemaUpdateError("shared-string declared/actual unique counts differ")
    new_root = root.replace(
        count_match.group(0), f'count="{count + 1}"'.encode("ascii"), 1
    ).replace(unique_match.group(0), f'uniqueCount="{unique_count + 1}"'.encode("ascii"), 1)
    patched = _replace_once(payload, root, new_root, description="shared-string root")
    appended = f"<si><t>{_xml_escape(append_name)}</t></si></sst>".encode()
    patched = _replace_once(
        patched,
        b"</sst>",
        appended,
        description="shared-string closing tag",
    )
    return patched, unique_count


def _append_or_reuse_shared_string(payload: bytes, *, name: str) -> tuple[bytes, int]:
    escaped_name = _xml_escape(name).encode("utf-8")
    exact_name_pattern = re.compile(rb"<t(?:\s[^>]*)?>" + re.escape(escaped_name) + rb"</t>")
    blocks = re.findall(rb"<si>.*?</si>", payload, re.DOTALL)
    matches = [index for index, block in enumerate(blocks) if exact_name_pattern.search(block)]
    if len(matches) > 1:
        raise BusinessSchemaUpdateError(f"shared string is not unique for {name!r}")
    if matches:
        return payload, matches[0]
    return _patch_shared_strings(payload, append_name=name)


def _shift_row(payload: bytes, *, source_row: int) -> bytes:
    shifted = source_row + 1
    result = _replace_once(
        payload,
        f'<row r="{source_row}"'.encode("ascii"),
        f'<row r="{shifted}"'.encode("ascii"),
        description=f"row {source_row} coordinate",
    )
    for column in "ABC":
        result = _replace_once(
            result,
            f'r="{column}{source_row}"'.encode("ascii"),
            f'r="{column}{shifted}"'.encode("ascii"),
            description=f"cell {column}{source_row} coordinate",
        )
    ordinal_pattern = re.compile(
        rb'(<c r="A' + str(shifted).encode("ascii") + rb'"[^>]*><v>)(\d+)(</v></c>)'
    )
    match = ordinal_pattern.search(result)
    if match is None:
        raise BusinessSchemaUpdateError(f"row {source_row} has no ordinal cell")
    ordinal = int(match.group(2))
    return ordinal_pattern.sub(
        match.group(1) + str(ordinal + 1).encode("ascii") + match.group(3),
        result,
        count=1,
    )


def _insert_sheet_row(
    payload: bytes,
    *,
    before_row_count: int,
    insert_source_row: int,
    schema_id: int,
    display_order: int,
    shared_string_index: int,
) -> bytes:
    patched = _replace_once(
        payload,
        f'<dimension ref="A1:C{before_row_count}"/>'.encode("ascii"),
        f'<dimension ref="A1:C{before_row_count + 1}"/>'.encode("ascii"),
        description="worksheet dimension",
    )
    matches = list(_ROW_PATTERN.finditer(patched))
    row_numbers = [int(match.group("row")) for match in matches]
    if row_numbers != list(range(1, before_row_count + 1)):
        raise BusinessSchemaUpdateError("worksheet row coordinates are not contiguous")

    parts: list[bytes] = []
    cursor = 0
    inserted = False
    row_attributes = (
        ' spans="1:3" ht="15" x14ac:dyDescent="0.2"'
        if b"xmlns:x14ac=" in patched
        else ' spans="1:3"'
    )
    new_row = (
        f'<row r="{insert_source_row}"{row_attributes}>'
        f'<c r="A{insert_source_row}" s="1"><v>{display_order}</v></c>'
        f'<c r="B{insert_source_row}"><v>{schema_id}</v></c>'
        f'<c r="C{insert_source_row}" t="s"><v>{shared_string_index}</v></c></row>'
    ).encode("ascii")
    for match in matches:
        source_row = int(match.group("row"))
        parts.append(patched[cursor : match.start()])
        if source_row == insert_source_row:
            parts.append(new_row)
            inserted = True
        row_payload = match.group(0)
        parts.append(
            _shift_row(row_payload, source_row=source_row)
            if source_row >= insert_source_row
            else row_payload
        )
        cursor = match.end()
    parts.append(patched[cursor:])
    if not inserted:
        raise BusinessSchemaUpdateError(f"worksheet insertion row {insert_source_row} is absent")
    return b"".join(parts)


def _retarget_shared_string_cell(
    payload: bytes,
    *,
    source_row: int,
    shared_string_index: int,
) -> bytes:
    pattern = re.compile(
        rb'(<c r="C' + str(source_row).encode("ascii") + rb'" t="s"><v>)(\d+)(</v></c>)'
    )
    matches = list(pattern.finditer(payload))
    if len(matches) != 1:
        raise BusinessSchemaUpdateError(f"expected exactly one shared-string cell at C{source_row}")
    return pattern.sub(
        lambda match: match.group(1) + str(shared_string_index).encode("ascii") + match.group(3),
        payload,
        count=1,
    )


def _build_updated_workbook(
    before: bytes,
    *,
    statement_type: str,
) -> tuple[bytes, dict[str, str], dict[str, str]]:
    before_hashes = _member_hashes(before)
    with ZipFile(io.BytesIO(before)) as source:
        if statement_type == "CDKT":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=CDKT_TOTAL_EQUITY_NAME,
                replace_name=(CDKT_4350_OLD_NAME, CDKT_4350_CORRECTED_NAME),
            )
            sheet = _insert_sheet_row(
                source.read(_SHEET_MEMBER),
                before_row_count=CDKT_BEFORE_ROW_COUNT,
                insert_source_row=CDKT_TOTAL_EQUITY_SOURCE_ROW,
                schema_id=CDKT_TOTAL_EQUITY_ID,
                display_order=CDKT_TOTAL_EQUITY_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
        elif statement_type == "KQKD":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=KQKD_TOTAL_OPERATING_INCOME_NAME,
            )
            sheet = _insert_sheet_row(
                source.read(_SHEET_MEMBER),
                before_row_count=KQKD_BEFORE_ROW_COUNT,
                insert_source_row=KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW,
                schema_id=KQKD_TOTAL_OPERATING_INCOME_ID,
                display_order=KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
        elif statement_type == "LCTT":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=LCTT_INVESTMENT_CONTRIBUTION_NET_NAME,
            )
            sheet = _insert_sheet_row(
                source.read(_SHEET_MEMBER),
                before_row_count=LCTT_BEFORE_ROW_COUNT,
                insert_source_row=LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW,
                schema_id=LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
                display_order=LCTT_INVESTMENT_CONTRIBUTION_NET_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
        elif statement_type == "TM":
            shared_strings, shared_string_index = _patch_shared_strings(
                source.read(_SHARED_STRINGS_MEMBER),
                append_name=TM_TOTAL_INTERBANK_PROVISION_NAME,
            )
            shared_strings, correction_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_770_CORRECTED_NAME,
            )
            shared_strings, education_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_EDUCATION_NAME,
            )
            shared_strings, health_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_HEALTH_SOCIAL_NAME,
            )
            shared_strings, arts_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_ARTS_RECREATION_NAME,
            )
            shared_strings, other_services_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_OTHER_SERVICES_NAME,
            )
            shared_strings, household_string_index = _patch_shared_strings(
                shared_strings,
                append_name=TM_HOUSEHOLD_EMPLOYMENT_NAME,
            )
            shared_strings, purchased_principal_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_PURCHASED_PRINCIPAL_NAME,
            )
            shared_strings, purchased_interest_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_PURCHASED_INTEREST_NAME,
            )
            shared_strings, guaranteed_debt_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_GOVERNMENT_GUARANTEED_DEBT_NAME,
            )
            shared_strings, fx_buy_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_FX_BUY_NAME,
            )
            shared_strings, fx_sell_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_FX_SELL_NAME,
            )
            shared_strings, swap_buy_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_SWAP_BUY_NAME,
            )
            shared_strings, swap_sell_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_SWAP_SELL_NAME,
            )
            shared_strings, margin_loan_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_MARGIN_LOAN_CANONICAL_NAME,
            )
            shared_strings, margin_quality_string_index = _append_or_reuse_shared_string(
                shared_strings,
                name=TM_MARGIN_LOAN_QUALITY_NAME,
            )
            tax_string_indices: dict[int, int] = {}
            for schema_id, name in TM_PAGE50_TAX_SCHEMA_ITEMS:
                shared_strings, tax_string_indices[schema_id] = _append_or_reuse_shared_string(
                    shared_strings,
                    name=name,
                )
            baseline_sheet = _retarget_shared_string_cell(
                source.read(_SHEET_MEMBER),
                source_row=TM_770_BASELINE_SOURCE_ROW,
                shared_string_index=correction_string_index,
            )
            baseline_sheet = _retarget_shared_string_cell(
                baseline_sheet,
                source_row=TM_EDUCATION_BASELINE_SOURCE_ROW,
                shared_string_index=education_string_index,
            )
            sheet = _insert_sheet_row(
                baseline_sheet,
                before_row_count=TM_BEFORE_ROW_COUNT,
                insert_source_row=TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW,
                schema_id=TM_TOTAL_INTERBANK_PROVISION_ID,
                display_order=TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER,
                shared_string_index=shared_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 1,
                insert_source_row=TM_MARGIN_LOAN_TYPE_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_TYPE_ID,
                display_order=TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 2,
                insert_source_row=TM_HEALTH_SOCIAL_SOURCE_ROW,
                schema_id=TM_HEALTH_SOCIAL_ID,
                display_order=TM_HEALTH_SOCIAL_DISPLAY_ORDER,
                shared_string_index=health_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 3,
                insert_source_row=TM_ARTS_RECREATION_SOURCE_ROW,
                schema_id=TM_ARTS_RECREATION_ID,
                display_order=TM_ARTS_RECREATION_DISPLAY_ORDER,
                shared_string_index=arts_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 4,
                insert_source_row=TM_OTHER_SERVICES_SOURCE_ROW,
                schema_id=TM_OTHER_SERVICES_ID,
                display_order=TM_OTHER_SERVICES_DISPLAY_ORDER,
                shared_string_index=other_services_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 5,
                insert_source_row=TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW,
                schema_id=TM_HOUSEHOLD_EMPLOYMENT_ID,
                display_order=TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER,
                shared_string_index=household_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 6,
                insert_source_row=TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_INDUSTRY_ID,
                display_order=TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 7,
                insert_source_row=TM_MARGIN_LOAN_QUALITY_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_QUALITY_ID,
                display_order=TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER,
                shared_string_index=margin_quality_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 8,
                insert_source_row=TM_MARGIN_LOAN_MATURITY_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_MATURITY_ID,
                display_order=TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 9,
                insert_source_row=TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW,
                schema_id=TM_MARGIN_LOAN_BUSINESS_ID,
                display_order=TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER,
                shared_string_index=margin_loan_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 10,
                insert_source_row=TM_PURCHASED_PRINCIPAL_SOURCE_ROW,
                schema_id=TM_PURCHASED_PRINCIPAL_ID,
                display_order=TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER,
                shared_string_index=purchased_principal_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 11,
                insert_source_row=TM_PURCHASED_INTEREST_SOURCE_ROW,
                schema_id=TM_PURCHASED_INTEREST_ID,
                display_order=TM_PURCHASED_INTEREST_DISPLAY_ORDER,
                shared_string_index=purchased_interest_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 12,
                insert_source_row=TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW,
                schema_id=TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                display_order=TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER,
                shared_string_index=guaranteed_debt_string_index,
            )
            for offset, (schema_id, _name) in enumerate(TM_PAGE50_TAX_SCHEMA_ITEMS):
                sheet = _insert_sheet_row(
                    sheet,
                    before_row_count=TM_BEFORE_ROW_COUNT + 13 + offset,
                    insert_source_row=TM_PAGE50_TAX_INSERT_SOURCE_ROW + offset,
                    schema_id=schema_id,
                    display_order=TM_PAGE50_TAX_INSERT_DISPLAY_ORDER + offset,
                    shared_string_index=tax_string_indices[schema_id],
                )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 28,
                insert_source_row=TM_FX_BUY_SOURCE_ROW,
                schema_id=TM_FX_BUY_ID,
                display_order=TM_FX_BUY_DISPLAY_ORDER,
                shared_string_index=fx_buy_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 29,
                insert_source_row=TM_FX_SELL_SOURCE_ROW,
                schema_id=TM_FX_SELL_ID,
                display_order=TM_FX_SELL_DISPLAY_ORDER,
                shared_string_index=fx_sell_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 30,
                insert_source_row=TM_SWAP_BUY_SOURCE_ROW,
                schema_id=TM_SWAP_BUY_ID,
                display_order=TM_SWAP_BUY_DISPLAY_ORDER,
                shared_string_index=swap_buy_string_index,
            )
            sheet = _insert_sheet_row(
                sheet,
                before_row_count=TM_BEFORE_ROW_COUNT + 31,
                insert_source_row=TM_SWAP_SELL_SOURCE_ROW,
                schema_id=TM_SWAP_SELL_ID,
                display_order=TM_SWAP_SELL_DISPLAY_ORDER,
                shared_string_index=swap_sell_string_index,
            )
        else:
            raise BusinessSchemaUpdateError(
                f"unsupported business update statement {statement_type}"
            )

        output = io.BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as destination:
            destination.comment = source.comment
            for info in source.infolist():
                member = source.read(info.filename)
                if info.filename == _SHARED_STRINGS_MEMBER:
                    member = shared_strings
                elif info.filename == _SHEET_MEMBER:
                    member = sheet
                destination.writestr(info, member)
    after = output.getvalue()
    after_hashes = _member_hashes(after)
    if set(before_hashes) != set(after_hashes):
        raise BusinessSchemaUpdateError("XLSX ZIP member set changed during business update")
    changed = {name for name in before_hashes if before_hashes[name] != after_hashes[name]}
    if changed != _TARGET_MEMBERS:
        raise BusinessSchemaUpdateError(f"unexpected XLSX members changed: {sorted(changed)}")
    return after, before_hashes, after_hashes


def _assert_contiguous_ordinals(records: Sequence[dict[str, object]], *, statement: str) -> None:
    items = [record for record in records if record["report_norm_id"] != "ReportNormId"]
    ordinals = [record["ordinal"] for record in items]
    if ordinals != [str(index) for index in range(len(items))]:
        raise BusinessSchemaUpdateError(f"{statement} display ordinals are not contiguous")


def _assert_candidate(
    before_path: Path,
    candidate_path: Path,
    *,
    statement: str,
) -> None:
    before = _identity_records(before_path)
    after = _identity_records(candidate_path)
    _assert_contiguous_ordinals(after, statement=statement)
    if statement == "CDKT":
        if len(after) != CDKT_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("CDKT candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        if by_id["4350"]["report_norm_name"] != CDKT_4350_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("CDKT 4350 display correction is absent")
        inserted = by_id[str(CDKT_TOTAL_EQUITY_ID)]
        if inserted != {
            "source_row": CDKT_TOTAL_EQUITY_SOURCE_ROW,
            "ordinal": str(CDKT_TOTAL_EQUITY_DISPLAY_ORDER),
            "report_norm_id": str(CDKT_TOTAL_EQUITY_ID),
            "report_norm_name": CDKT_TOTAL_EQUITY_NAME,
        }:
            raise BusinessSchemaUpdateError("CDKT total-equity identity/position drifted")
        ids = [record["report_norm_id"] for record in after]
        index = ids.index(str(CDKT_TOTAL_EQUITY_ID))
        if (ids[index - 1], ids[index + 1]) != (
            str(CDKT_TOTAL_EQUITY_PREDECESSOR_ID),
            str(CDKT_TOTAL_EQUITY_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("CDKT total-equity anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"] != str(CDKT_TOTAL_EQUITY_ID)
        ]
        for record in new_pairs:
            if record["report_norm_id"] == "4350":
                record["report_norm_name"] = CDKT_4350_OLD_NAME
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("CDKT candidate changed an unauthorized identity/order")
    elif statement == "KQKD":
        if len(after) != KQKD_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("KQKD candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        inserted = by_id[str(KQKD_TOTAL_OPERATING_INCOME_ID)]
        if inserted != {
            "source_row": KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW,
            "ordinal": str(KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER),
            "report_norm_id": str(KQKD_TOTAL_OPERATING_INCOME_ID),
            "report_norm_name": KQKD_TOTAL_OPERATING_INCOME_NAME,
        }:
            raise BusinessSchemaUpdateError("KQKD total-operating-income identity/position drifted")
        ids = [record["report_norm_id"] for record in after]
        index = ids.index(str(KQKD_TOTAL_OPERATING_INCOME_ID))
        if (ids[index - 1], ids[index + 1]) != (
            str(KQKD_TOTAL_OPERATING_INCOME_PREDECESSOR_ID),
            str(KQKD_TOTAL_OPERATING_INCOME_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("KQKD total-operating-income anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"] != str(KQKD_TOTAL_OPERATING_INCOME_ID)
        ]
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("KQKD candidate changed an existing identity/order")
    elif statement == "LCTT":
        if len(after) != LCTT_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("LCTT candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        inserted = by_id[str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID)]
        if inserted != {
            "source_row": LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW,
            "ordinal": str(LCTT_INVESTMENT_CONTRIBUTION_NET_DISPLAY_ORDER),
            "report_norm_id": str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID),
            "report_norm_name": LCTT_INVESTMENT_CONTRIBUTION_NET_NAME,
        }:
            raise BusinessSchemaUpdateError(
                "LCTT investment-contribution aggregate identity/position drifted"
            )
        ids = [record["report_norm_id"] for record in after]
        index = ids.index(str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID))
        if (ids[index - 1], ids[index + 1]) != (
            str(LCTT_INVESTMENT_CONTRIBUTION_NET_PREDECESSOR_ID),
            str(LCTT_INVESTMENT_CONTRIBUTION_NET_SUCCESSOR_ID),
        ):
            raise BusinessSchemaUpdateError("LCTT investment-contribution anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"] != str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID)
        ]
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("LCTT candidate changed an existing identity/order")
    elif statement == "TM":
        if len(after) != TM_AFTER_ROW_COUNT:
            raise BusinessSchemaUpdateError("TM candidate row count drifted")
        by_id = {record["report_norm_id"]: record for record in after}
        if by_id["770"]["report_norm_name"] != TM_770_CORRECTED_NAME:
            raise BusinessSchemaUpdateError("TM 770 display correction is absent")
        if by_id[str(TM_EDUCATION_ID)]["report_norm_name"] != TM_EDUCATION_NAME:
            raise BusinessSchemaUpdateError("TM 737 education display correction is absent")
        additions = (
            (
                TM_TOTAL_INTERBANK_PROVISION_ID,
                TM_TOTAL_INTERBANK_PROVISION_NAME,
                TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW,
                TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER,
            ),
            (
                TM_HEALTH_SOCIAL_ID,
                TM_HEALTH_SOCIAL_NAME,
                TM_HEALTH_SOCIAL_SOURCE_ROW,
                TM_HEALTH_SOCIAL_DISPLAY_ORDER,
            ),
            (
                TM_ARTS_RECREATION_ID,
                TM_ARTS_RECREATION_NAME,
                TM_ARTS_RECREATION_SOURCE_ROW,
                TM_ARTS_RECREATION_DISPLAY_ORDER,
            ),
            (
                TM_OTHER_SERVICES_ID,
                TM_OTHER_SERVICES_NAME,
                TM_OTHER_SERVICES_SOURCE_ROW,
                TM_OTHER_SERVICES_DISPLAY_ORDER,
            ),
            (
                TM_HOUSEHOLD_EMPLOYMENT_ID,
                TM_HOUSEHOLD_EMPLOYMENT_NAME,
                TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW,
                TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER,
            ),
            (
                TM_PURCHASED_PRINCIPAL_ID,
                TM_PURCHASED_PRINCIPAL_NAME,
                TM_PURCHASED_PRINCIPAL_SOURCE_ROW,
                TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER,
            ),
            (
                TM_PURCHASED_INTEREST_ID,
                TM_PURCHASED_INTEREST_NAME,
                TM_PURCHASED_INTEREST_SOURCE_ROW,
                TM_PURCHASED_INTEREST_DISPLAY_ORDER,
            ),
            (
                TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                TM_GOVERNMENT_GUARANTEED_DEBT_NAME,
                TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW,
                TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER,
            ),
            (
                TM_FX_BUY_ID,
                TM_FX_BUY_NAME,
                TM_FX_BUY_SOURCE_ROW,
                TM_FX_BUY_DISPLAY_ORDER,
            ),
            (
                TM_FX_SELL_ID,
                TM_FX_SELL_NAME,
                TM_FX_SELL_SOURCE_ROW,
                TM_FX_SELL_DISPLAY_ORDER,
            ),
            (
                TM_SWAP_BUY_ID,
                TM_SWAP_BUY_NAME,
                TM_SWAP_BUY_SOURCE_ROW,
                TM_SWAP_BUY_DISPLAY_ORDER,
            ),
            (
                TM_SWAP_SELL_ID,
                TM_SWAP_SELL_NAME,
                TM_SWAP_SELL_SOURCE_ROW,
                TM_SWAP_SELL_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_TYPE_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_TYPE_SOURCE_ROW,
                TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_QUALITY_ID,
                TM_MARGIN_LOAN_QUALITY_NAME,
                TM_MARGIN_LOAN_QUALITY_SOURCE_ROW,
                TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_MATURITY_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_MATURITY_SOURCE_ROW,
                TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_BUSINESS_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW,
                TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER,
            ),
            (
                TM_MARGIN_LOAN_INDUSTRY_ID,
                TM_MARGIN_LOAN_CANONICAL_NAME,
                TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW,
                TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER,
            ),
            *(
                (
                    schema_id,
                    name,
                    TM_PAGE50_TAX_INSERT_SOURCE_ROW + offset,
                    TM_PAGE50_TAX_INSERT_DISPLAY_ORDER + offset,
                )
                for offset, (schema_id, name) in enumerate(TM_PAGE50_TAX_SCHEMA_ITEMS)
            ),
        )
        for schema_id, name, source_row, display_order in additions:
            if by_id[str(schema_id)] != {
                "source_row": source_row,
                "ordinal": str(display_order),
                "report_norm_id": str(schema_id),
                "report_norm_name": name,
            }:
                raise BusinessSchemaUpdateError(f"TM {schema_id} identity/position drifted")
        ids = [record["report_norm_id"] for record in after]
        expected_anchors = {
            TM_TOTAL_INTERBANK_PROVISION_ID: (
                TM_TOTAL_INTERBANK_PROVISION_PREDECESSOR_ID,
                TM_TOTAL_INTERBANK_PROVISION_SUCCESSOR_ID,
            ),
            TM_HEALTH_SOCIAL_ID: (
                TM_HEALTH_SOCIAL_PREDECESSOR_ID,
                TM_HEALTH_SOCIAL_SUCCESSOR_ID,
            ),
            TM_ARTS_RECREATION_ID: (
                TM_ARTS_RECREATION_PREDECESSOR_ID,
                TM_ARTS_RECREATION_SUCCESSOR_ID,
            ),
            TM_OTHER_SERVICES_ID: (
                TM_OTHER_SERVICES_PREDECESSOR_ID,
                TM_OTHER_SERVICES_SUCCESSOR_ID,
            ),
            TM_HOUSEHOLD_EMPLOYMENT_ID: (
                TM_HOUSEHOLD_EMPLOYMENT_PREDECESSOR_ID,
                TM_HOUSEHOLD_EMPLOYMENT_SUCCESSOR_ID,
            ),
            TM_PURCHASED_PRINCIPAL_ID: (
                TM_PURCHASED_PRINCIPAL_PREDECESSOR_ID,
                TM_PURCHASED_PRINCIPAL_SUCCESSOR_ID,
            ),
            TM_PURCHASED_INTEREST_ID: (
                TM_PURCHASED_INTEREST_PREDECESSOR_ID,
                TM_PURCHASED_INTEREST_SUCCESSOR_ID,
            ),
            TM_GOVERNMENT_GUARANTEED_DEBT_ID: (
                TM_GOVERNMENT_GUARANTEED_DEBT_PREDECESSOR_ID,
                TM_GOVERNMENT_GUARANTEED_DEBT_SUCCESSOR_ID,
            ),
            TM_FX_BUY_ID: (
                TM_FX_BUY_PREDECESSOR_ID,
                TM_FX_BUY_SUCCESSOR_ID,
            ),
            TM_FX_SELL_ID: (
                TM_FX_SELL_PREDECESSOR_ID,
                TM_FX_SELL_SUCCESSOR_ID,
            ),
            TM_SWAP_BUY_ID: (
                TM_SWAP_BUY_PREDECESSOR_ID,
                TM_SWAP_BUY_SUCCESSOR_ID,
            ),
            TM_SWAP_SELL_ID: (
                TM_SWAP_SELL_PREDECESSOR_ID,
                TM_SWAP_SELL_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_TYPE_ID: (
                TM_MARGIN_LOAN_TYPE_PREDECESSOR_ID,
                TM_MARGIN_LOAN_TYPE_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_QUALITY_ID: (
                TM_MARGIN_LOAN_QUALITY_PREDECESSOR_ID,
                TM_MARGIN_LOAN_QUALITY_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_MATURITY_ID: (
                TM_MARGIN_LOAN_MATURITY_PREDECESSOR_ID,
                TM_MARGIN_LOAN_MATURITY_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_BUSINESS_ID: (
                TM_MARGIN_LOAN_BUSINESS_PREDECESSOR_ID,
                TM_MARGIN_LOAN_BUSINESS_SUCCESSOR_ID,
            ),
            TM_MARGIN_LOAN_INDUSTRY_ID: (
                TM_MARGIN_LOAN_INDUSTRY_PREDECESSOR_ID,
                TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID,
            ),
            **{
                schema_id: (
                    (
                        TM_PAGE50_TAX_PREDECESSOR_ID
                        if offset == 0
                        else TM_PAGE50_TAX_SCHEMA_IDS[offset - 1]
                    ),
                    (
                        TM_PAGE50_TAX_SUCCESSOR_ID
                        if offset == len(TM_PAGE50_TAX_SCHEMA_IDS) - 1
                        else TM_PAGE50_TAX_SCHEMA_IDS[offset + 1]
                    ),
                )
                for offset, schema_id in enumerate(TM_PAGE50_TAX_SCHEMA_IDS)
            },
        }
        for schema_id, anchors in expected_anchors.items():
            index = ids.index(str(schema_id))
            if (ids[index - 1], ids[index + 1]) != tuple(str(item) for item in anchors):
                raise BusinessSchemaUpdateError(f"TM {schema_id} anchors drifted")
        old_pairs = _item_pairs(before)
        new_pairs = [
            record
            for record in _item_pairs(after)
            if record["report_norm_id"] not in {str(schema_id) for schema_id in NEW_SCHEMA_IDS}
        ]
        for record in new_pairs:
            if record["report_norm_id"] == "770":
                record["report_norm_name"] = TM_770_OLD_NAME
            elif record["report_norm_id"] == str(TM_EDUCATION_ID):
                record["report_norm_name"] = TM_EDUCATION_OLD_NAME
        if new_pairs != old_pairs:
            raise BusinessSchemaUpdateError("TM candidate changed an unauthorized identity/order")
    else:
        raise BusinessSchemaUpdateError(f"unsupported candidate statement {statement}")


def _schema_ids(paths: dict[str, Path]) -> dict[int, str]:
    seen: dict[int, str] = {}
    for statement, path in paths.items():
        for row in read_rows(path):
            raw = row.get("B", "").strip()
            if not raw or raw == "ReportNormId":
                continue
            try:
                schema_id = int(raw)
            except ValueError as exc:
                raise BusinessSchemaUpdateError(
                    f"non-integer schema ID in collision scan: {statement} {raw!r}"
                ) from exc
            if schema_id in seen:
                raise BusinessSchemaUpdateError(
                    f"global schema ID collision: {schema_id} in {seen[schema_id]} and {statement}"
                )
            seen[schema_id] = statement
    return seen


def _assert_global_identity(
    project_root: Path,
    *,
    cdkt_path: Path | None = None,
    kqkd_path: Path | None = None,
    lctt_path: Path | None = None,
    tm_path: Path | None = None,
    overrides: dict[str, Path] | None = None,
    expected_count: int,
) -> dict[int, str]:
    paths = {
        "CDKT": cdkt_path or project_root / CDKT_WORKBOOK,
        "KQKD": kqkd_path or project_root / KQKD_WORKBOOK,
        "LCTT": lctt_path or project_root / LCTT_WORKBOOK,
        "TM": tm_path or project_root / TM_WORKBOOK,
    }
    paths.update(overrides or {})
    seen = _schema_ids(paths)
    if len(seen) != expected_count:
        raise BusinessSchemaUpdateError(
            f"global schema count drifted: expected={expected_count}, actual={len(seen)}"
        )
    if NEW_SCHEMA_IDS & REVIEWED_EXTERNAL_IDS:
        raise BusinessSchemaUpdateError("new schema IDs collide with reviewed external IDs")
    return seen


def _expected_formulas() -> list[dict[str, object]]:
    return [dict(record) for record in BUSINESS_FORMULAS]


def _expected_schema_changes() -> list[dict[str, object]]:
    return [
        {
            "change": "ADD",
            "statement_type": "CDKT",
            "schema_id": CDKT_TOTAL_EQUITY_ID,
            "canonical_name": CDKT_TOTAL_EQUITY_NAME,
            "source_row": CDKT_TOTAL_EQUITY_SOURCE_ROW,
            "display_order_zero_based": CDKT_TOTAL_EQUITY_DISPLAY_ORDER,
            "previous_schema_id": CDKT_TOTAL_EQUITY_PREDECESSOR_ID,
            "next_schema_id": CDKT_TOTAL_EQUITY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "KQKD",
            "schema_id": KQKD_TOTAL_OPERATING_INCOME_ID,
            "canonical_name": KQKD_TOTAL_OPERATING_INCOME_NAME,
            "source_row": KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW,
            "display_order_zero_based": KQKD_TOTAL_OPERATING_INCOME_DISPLAY_ORDER,
            "previous_schema_id": KQKD_TOTAL_OPERATING_INCOME_PREDECESSOR_ID,
            "next_schema_id": KQKD_TOTAL_OPERATING_INCOME_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "LCTT",
            "schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
            "canonical_name": LCTT_INVESTMENT_CONTRIBUTION_NET_NAME,
            "source_row": LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW,
            "display_order_zero_based": LCTT_INVESTMENT_CONTRIBUTION_NET_DISPLAY_ORDER,
            "previous_schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_PREDECESSOR_ID,
            "next_schema_id": LCTT_INVESTMENT_CONTRIBUTION_NET_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_TOTAL_INTERBANK_PROVISION_ID,
            "canonical_name": TM_TOTAL_INTERBANK_PROVISION_NAME,
            "source_row": TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW,
            "display_order_zero_based": TM_TOTAL_INTERBANK_PROVISION_DISPLAY_ORDER,
            "previous_schema_id": TM_TOTAL_INTERBANK_PROVISION_PREDECESSOR_ID,
            "next_schema_id": TM_TOTAL_INTERBANK_PROVISION_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_HEALTH_SOCIAL_ID,
            "canonical_name": TM_HEALTH_SOCIAL_NAME,
            "source_row": TM_HEALTH_SOCIAL_SOURCE_ROW,
            "display_order_zero_based": TM_HEALTH_SOCIAL_DISPLAY_ORDER,
            "previous_schema_id": TM_HEALTH_SOCIAL_PREDECESSOR_ID,
            "next_schema_id": TM_HEALTH_SOCIAL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_ARTS_RECREATION_ID,
            "canonical_name": TM_ARTS_RECREATION_NAME,
            "source_row": TM_ARTS_RECREATION_SOURCE_ROW,
            "display_order_zero_based": TM_ARTS_RECREATION_DISPLAY_ORDER,
            "previous_schema_id": TM_ARTS_RECREATION_PREDECESSOR_ID,
            "next_schema_id": TM_ARTS_RECREATION_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_OTHER_SERVICES_ID,
            "canonical_name": TM_OTHER_SERVICES_NAME,
            "source_row": TM_OTHER_SERVICES_SOURCE_ROW,
            "display_order_zero_based": TM_OTHER_SERVICES_DISPLAY_ORDER,
            "previous_schema_id": TM_OTHER_SERVICES_PREDECESSOR_ID,
            "next_schema_id": TM_OTHER_SERVICES_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_HOUSEHOLD_EMPLOYMENT_ID,
            "canonical_name": TM_HOUSEHOLD_EMPLOYMENT_NAME,
            "source_row": TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW,
            "display_order_zero_based": TM_HOUSEHOLD_EMPLOYMENT_DISPLAY_ORDER,
            "previous_schema_id": TM_HOUSEHOLD_EMPLOYMENT_PREDECESSOR_ID,
            "next_schema_id": TM_HOUSEHOLD_EMPLOYMENT_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_PURCHASED_PRINCIPAL_ID,
            "canonical_name": TM_PURCHASED_PRINCIPAL_NAME,
            "source_row": TM_PURCHASED_PRINCIPAL_SOURCE_ROW,
            "display_order_zero_based": TM_PURCHASED_PRINCIPAL_DISPLAY_ORDER,
            "previous_schema_id": TM_PURCHASED_PRINCIPAL_PREDECESSOR_ID,
            "next_schema_id": TM_PURCHASED_PRINCIPAL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_PURCHASED_INTEREST_ID,
            "canonical_name": TM_PURCHASED_INTEREST_NAME,
            "source_row": TM_PURCHASED_INTEREST_SOURCE_ROW,
            "display_order_zero_based": TM_PURCHASED_INTEREST_DISPLAY_ORDER,
            "previous_schema_id": TM_PURCHASED_INTEREST_PREDECESSOR_ID,
            "next_schema_id": TM_PURCHASED_INTEREST_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_GOVERNMENT_GUARANTEED_DEBT_ID,
            "canonical_name": TM_GOVERNMENT_GUARANTEED_DEBT_NAME,
            "source_row": TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW,
            "display_order_zero_based": TM_GOVERNMENT_GUARANTEED_DEBT_DISPLAY_ORDER,
            "previous_schema_id": TM_GOVERNMENT_GUARANTEED_DEBT_PREDECESSOR_ID,
            "next_schema_id": TM_GOVERNMENT_GUARANTEED_DEBT_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_FX_BUY_ID,
            "canonical_name": TM_FX_BUY_NAME,
            "source_row": TM_FX_BUY_SOURCE_ROW,
            "display_order_zero_based": TM_FX_BUY_DISPLAY_ORDER,
            "previous_schema_id": TM_FX_BUY_PREDECESSOR_ID,
            "next_schema_id": TM_FX_BUY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_FX_SELL_ID,
            "canonical_name": TM_FX_SELL_NAME,
            "source_row": TM_FX_SELL_SOURCE_ROW,
            "display_order_zero_based": TM_FX_SELL_DISPLAY_ORDER,
            "previous_schema_id": TM_FX_SELL_PREDECESSOR_ID,
            "next_schema_id": TM_FX_SELL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_SWAP_BUY_ID,
            "canonical_name": TM_SWAP_BUY_NAME,
            "source_row": TM_SWAP_BUY_SOURCE_ROW,
            "display_order_zero_based": TM_SWAP_BUY_DISPLAY_ORDER,
            "previous_schema_id": TM_SWAP_BUY_PREDECESSOR_ID,
            "next_schema_id": TM_SWAP_BUY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_SWAP_SELL_ID,
            "canonical_name": TM_SWAP_SELL_NAME,
            "source_row": TM_SWAP_SELL_SOURCE_ROW,
            "display_order_zero_based": TM_SWAP_SELL_DISPLAY_ORDER,
            "previous_schema_id": TM_SWAP_SELL_PREDECESSOR_ID,
            "next_schema_id": TM_SWAP_SELL_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_TYPE_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_TYPE_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_TYPE_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_TYPE_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_TYPE_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_QUALITY_ID,
            "canonical_name": TM_MARGIN_LOAN_QUALITY_NAME,
            "source_row": TM_MARGIN_LOAN_QUALITY_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_QUALITY_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_QUALITY_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_QUALITY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_MATURITY_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_MATURITY_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_MATURITY_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_MATURITY_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_MATURITY_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_BUSINESS_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_BUSINESS_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_BUSINESS_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_BUSINESS_SUCCESSOR_ID,
        },
        {
            "change": "ADD",
            "statement_type": "TM",
            "schema_id": TM_MARGIN_LOAN_INDUSTRY_ID,
            "canonical_name": TM_MARGIN_LOAN_CANONICAL_NAME,
            "source_row": TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW,
            "display_order_zero_based": TM_MARGIN_LOAN_INDUSTRY_DISPLAY_ORDER,
            "previous_schema_id": TM_MARGIN_LOAN_INDUSTRY_PREDECESSOR_ID,
            "next_schema_id": TM_MARGIN_LOAN_INDUSTRY_SUCCESSOR_ID,
        },
        *(
            {
                "change": "ADD",
                "statement_type": "TM",
                "schema_id": schema_id,
                "canonical_name": name,
                "source_row": TM_PAGE50_TAX_INSERT_SOURCE_ROW + offset,
                "display_order_zero_based": TM_PAGE50_TAX_INSERT_DISPLAY_ORDER + offset,
                "previous_schema_id": (
                    TM_PAGE50_TAX_PREDECESSOR_ID
                    if offset == 0
                    else TM_PAGE50_TAX_SCHEMA_IDS[offset - 1]
                ),
                "next_schema_id": (
                    TM_PAGE50_TAX_SUCCESSOR_ID
                    if offset == len(TM_PAGE50_TAX_SCHEMA_IDS) - 1
                    else TM_PAGE50_TAX_SCHEMA_IDS[offset + 1]
                ),
            }
            for offset, (schema_id, name) in enumerate(TM_PAGE50_TAX_SCHEMA_ITEMS)
        ),
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "CDKT",
            "schema_id": 4350,
            "before": CDKT_4350_OLD_NAME,
            "after": CDKT_4350_CORRECTED_NAME,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "TM",
            "schema_id": 770,
            "before": TM_770_OLD_NAME,
            "after": TM_770_CORRECTED_NAME,
        },
        {
            "change": "CORRECT_DISPLAY_NAME",
            "statement_type": "TM",
            "schema_id": TM_EDUCATION_ID,
            "before": TM_EDUCATION_OLD_NAME,
            "after": TM_EDUCATION_NAME,
        },
    ]


def verify_business_schema_update(project_root: Path, audit_path: Path) -> dict[str, object]:
    project_root = project_root.resolve()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        audit.get("format_version") != 1
        or audit.get("migration_id") != "BUSINESS-SCHEMA-5712-5713-5714-5718-5749"
        or audit.get("status") != "APPLIED_AND_VERIFIED"
    ):
        raise BusinessSchemaUpdateError("invalid business-schema update audit identity")
    if audit.get("business_formulas") != _expected_formulas():
        raise BusinessSchemaUpdateError("business formula audit drifted")
    if audit.get("schema_changes") != _expected_schema_changes():
        raise BusinessSchemaUpdateError("business schema-change audit drifted")
    if audit.get("authority") != {
        "approved_on": "2026-08-08",
        "policy": "USER_AUTHORIZED_BUSINESS_SCHEMA_UPDATE",
    }:
        raise BusinessSchemaUpdateError("business schema authority drifted")
    collision = audit.get("collision_safety")
    if not isinstance(collision, dict) or collision.get("reviewed_external_ids") != sorted(
        REVIEWED_EXTERNAL_IDS
    ):
        raise BusinessSchemaUpdateError("reviewed-external collision audit drifted")
    if collision.get("new_ids_disjoint_from_reviewed_external_ids") is not True:
        raise BusinessSchemaUpdateError("business update lacks external-ID disjointness proof")
    if collision != {
        "baseline_global_schema_count": 1593,
        "result_global_schema_count": 1628,
        "new_ids": sorted(NEW_SCHEMA_IDS),
        "reviewed_external_ids": sorted(REVIEWED_EXTERNAL_IDS),
        "new_ids_disjoint_from_reviewed_external_ids": True,
        "result_ids_globally_unique": True,
    }:
        raise BusinessSchemaUpdateError("business update collision proof drifted")

    expected_workbooks = {
        "CDKT": (
            CDKT_BASELINE_WORKBOOK,
            CDKT_WORKBOOK,
            CDKT_BEFORE_SHA256,
            CDKT_AFTER_ROW_COUNT,
        ),
        "KQKD": (
            KQKD_BASELINE_WORKBOOK,
            KQKD_WORKBOOK,
            KQKD_BEFORE_SHA256,
            KQKD_AFTER_ROW_COUNT,
        ),
        "LCTT": (
            LCTT_BASELINE_WORKBOOK,
            LCTT_WORKBOOK,
            LCTT_BEFORE_SHA256,
            LCTT_AFTER_ROW_COUNT,
        ),
        "TM": (
            TM_BASELINE_WORKBOOK,
            TM_WORKBOOK,
            TM_BEFORE_SHA256,
            TM_AFTER_ROW_COUNT,
        ),
    }
    raw_workbooks = audit.get("workbooks")
    if not isinstance(raw_workbooks, dict) or set(raw_workbooks) != set(expected_workbooks):
        raise BusinessSchemaUpdateError("business update workbook audit set drifted")
    for statement, (
        baseline_relative,
        relative,
        before_hash,
        row_count,
    ) in expected_workbooks.items():
        record = raw_workbooks[statement]
        if not isinstance(record, dict):
            raise BusinessSchemaUpdateError(f"invalid {statement} workbook audit")
        if (
            record.get("baseline_path") != baseline_relative
            or record.get("path") != relative
            or record.get("before_sha256") != before_hash
            or record.get("before_row_count_including_header")
            != {
                "CDKT": CDKT_BEFORE_ROW_COUNT,
                "KQKD": KQKD_BEFORE_ROW_COUNT,
                "LCTT": LCTT_BEFORE_ROW_COUNT,
                "TM": TM_BEFORE_ROW_COUNT,
            }[statement]
            or record.get("after_row_count_including_header") != row_count
        ):
            raise BusinessSchemaUpdateError(f"{statement} baseline identity drifted")
        if sha256_file(project_root / baseline_relative) != before_hash:
            raise BusinessSchemaUpdateError(f"{statement} sealed baseline workbook changed")
        path = project_root / relative
        current_payload = path.read_bytes()
        if sha256_bytes(current_payload) != record.get("after_sha256"):
            raise BusinessSchemaUpdateError(f"{statement} workbook differs from audited result")
        reproduced, _, _ = _build_updated_workbook(
            (project_root / baseline_relative).read_bytes(),
            statement_type=statement,
        )
        if current_payload != reproduced:
            raise BusinessSchemaUpdateError(
                f"{statement} workbook is not byte-identical to deterministic replay"
            )
        records = _identity_records(path)
        if len(records) != row_count:
            raise BusinessSchemaUpdateError(f"{statement} audited row count drifted")
        _assert_contiguous_ordinals(records, statement=statement)
        _assert_candidate(project_root / baseline_relative, path, statement=statement)
        preservation = record.get("preservation")
        if not isinstance(preservation, dict):
            raise BusinessSchemaUpdateError(f"{statement} preservation audit is absent")
        baseline_records = _identity_records(project_root / baseline_relative)
        if preservation.get("existing_item_id_name_order_sha256") != _records_hash(
            _item_pairs(baseline_records)
        ):
            raise BusinessSchemaUpdateError(f"{statement} baseline item/order hash drifted")
        if (
            preservation.get("existing_ids_and_relative_order_preserved") is not True
            or preservation.get("zip_member_set_preserved") is not True
            or preservation.get("only_changed_zip_members") != sorted(_TARGET_MEMBERS)
            or preservation.get("allowed_existing_name_corrections")
            != (
                [
                    {
                        "schema_id": 4350,
                        "before": CDKT_4350_OLD_NAME,
                        "after": CDKT_4350_CORRECTED_NAME,
                    }
                ]
                if statement == "CDKT"
                else (
                    [
                        {
                            "schema_id": 770,
                            "before": TM_770_OLD_NAME,
                            "after": TM_770_CORRECTED_NAME,
                        },
                        {
                            "schema_id": TM_EDUCATION_ID,
                            "before": TM_EDUCATION_OLD_NAME,
                            "after": TM_EDUCATION_NAME,
                        },
                    ]
                    if statement == "TM"
                    else []
                )
            )
        ):
            raise BusinessSchemaUpdateError(f"{statement} preservation claims drifted")
        baseline_member_hashes = _member_hashes((project_root / baseline_relative).read_bytes())
        if preservation.get("changed_zip_members_before_sha256") != {
            member: baseline_member_hashes[member] for member in sorted(_TARGET_MEMBERS)
        }:
            raise BusinessSchemaUpdateError(f"{statement} changed-member baseline hashes drifted")
        member_hashes = _member_hashes(path.read_bytes())
        for member, expected_hash in preservation.get("unchanged_zip_members_sha256", {}).items():
            if member_hashes.get(member) != expected_hash:
                raise BusinessSchemaUpdateError(f"{statement} unchanged member drift: {member}")
        if preservation.get("changed_zip_members_after_sha256") != {
            member: member_hashes[member] for member in sorted(_TARGET_MEMBERS)
        }:
            raise BusinessSchemaUpdateError(f"{statement} changed-member result hashes drifted")

    cdkt_records = _identity_records(project_root / CDKT_WORKBOOK)
    kqkd_records = _identity_records(project_root / KQKD_WORKBOOK)
    lctt_records = _identity_records(project_root / LCTT_WORKBOOK)
    tm_records = _identity_records(project_root / TM_WORKBOOK)
    cdkt_by_id = {record["report_norm_id"]: record for record in cdkt_records}
    kqkd_by_id = {record["report_norm_id"]: record for record in kqkd_records}
    lctt_by_id = {record["report_norm_id"]: record for record in lctt_records}
    tm_by_id = {record["report_norm_id"]: record for record in tm_records}
    if cdkt_by_id["4350"]["report_norm_name"] != CDKT_4350_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("CDKT 4350 correction drifted")
    if cdkt_by_id[str(CDKT_TOTAL_EQUITY_ID)]["source_row"] != CDKT_TOTAL_EQUITY_SOURCE_ROW:
        raise BusinessSchemaUpdateError("CDKT 5712 row position drifted")
    if (
        kqkd_by_id[str(KQKD_TOTAL_OPERATING_INCOME_ID)]["source_row"]
        != KQKD_TOTAL_OPERATING_INCOME_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("KQKD 5713 row position drifted")
    if (
        lctt_by_id[str(LCTT_INVESTMENT_CONTRIBUTION_NET_ID)]["source_row"]
        != LCTT_INVESTMENT_CONTRIBUTION_NET_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("LCTT 5714 row position drifted")
    if tm_by_id["770"]["report_norm_name"] != TM_770_CORRECTED_NAME:
        raise BusinessSchemaUpdateError("TM 770 correction drifted")
    if tm_by_id[str(TM_EDUCATION_ID)]["report_norm_name"] != TM_EDUCATION_NAME:
        raise BusinessSchemaUpdateError("TM 737 correction drifted")
    if (
        tm_by_id[str(TM_TOTAL_INTERBANK_PROVISION_ID)]["source_row"]
        != TM_TOTAL_INTERBANK_PROVISION_SOURCE_ROW
    ):
        raise BusinessSchemaUpdateError("TM 5718 row position drifted")
    for schema_id, source_row in (
        (TM_HEALTH_SOCIAL_ID, TM_HEALTH_SOCIAL_SOURCE_ROW),
        (TM_ARTS_RECREATION_ID, TM_ARTS_RECREATION_SOURCE_ROW),
        (TM_OTHER_SERVICES_ID, TM_OTHER_SERVICES_SOURCE_ROW),
        (TM_HOUSEHOLD_EMPLOYMENT_ID, TM_HOUSEHOLD_EMPLOYMENT_SOURCE_ROW),
        (TM_PURCHASED_PRINCIPAL_ID, TM_PURCHASED_PRINCIPAL_SOURCE_ROW),
        (TM_PURCHASED_INTEREST_ID, TM_PURCHASED_INTEREST_SOURCE_ROW),
        (
            TM_GOVERNMENT_GUARANTEED_DEBT_ID,
            TM_GOVERNMENT_GUARANTEED_DEBT_SOURCE_ROW,
        ),
        (TM_FX_BUY_ID, TM_FX_BUY_SOURCE_ROW),
        (TM_FX_SELL_ID, TM_FX_SELL_SOURCE_ROW),
        (TM_SWAP_BUY_ID, TM_SWAP_BUY_SOURCE_ROW),
        (TM_SWAP_SELL_ID, TM_SWAP_SELL_SOURCE_ROW),
        (TM_MARGIN_LOAN_TYPE_ID, TM_MARGIN_LOAN_TYPE_SOURCE_ROW),
        (TM_MARGIN_LOAN_QUALITY_ID, TM_MARGIN_LOAN_QUALITY_SOURCE_ROW),
        (TM_MARGIN_LOAN_MATURITY_ID, TM_MARGIN_LOAN_MATURITY_SOURCE_ROW),
        (TM_MARGIN_LOAN_BUSINESS_ID, TM_MARGIN_LOAN_BUSINESS_SOURCE_ROW),
        (TM_MARGIN_LOAN_INDUSTRY_ID, TM_MARGIN_LOAN_INDUSTRY_SOURCE_ROW),
        *(
            (schema_id, TM_PAGE50_TAX_INSERT_SOURCE_ROW + offset)
            for offset, schema_id in enumerate(TM_PAGE50_TAX_SCHEMA_IDS)
        ),
    ):
        if tm_by_id[str(schema_id)]["source_row"] != source_row:
            raise BusinessSchemaUpdateError(f"TM {schema_id} row position drifted")

    unaffected = audit.get("unaffected_workbooks_sha256")
    expected_unaffected: dict[str, str] = {}
    if unaffected != expected_unaffected:
        raise BusinessSchemaUpdateError("unaffected workbook pins drifted")
    for relative, expected_hash in expected_unaffected.items():
        if sha256_file(project_root / relative) != expected_hash:
            raise BusinessSchemaUpdateError(f"unaffected workbook changed: {relative}")

    seen = _assert_global_identity(project_root, expected_count=1628)
    if seen.get(CDKT_TOTAL_EQUITY_ID) != "CDKT":
        raise BusinessSchemaUpdateError("CDKT 5712 is not globally unique and correctly scoped")
    if seen.get(KQKD_TOTAL_OPERATING_INCOME_ID) != "KQKD":
        raise BusinessSchemaUpdateError("KQKD 5713 is not globally unique and correctly scoped")
    if seen.get(LCTT_INVESTMENT_CONTRIBUTION_NET_ID) != "LCTT":
        raise BusinessSchemaUpdateError("LCTT 5714 is not globally unique and correctly scoped")
    if seen.get(TM_TOTAL_INTERBANK_PROVISION_ID) != "TM":
        raise BusinessSchemaUpdateError("TM 5718 is not globally unique and correctly scoped")
    for schema_id in (
        TM_HEALTH_SOCIAL_ID,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
        *TM_PAGE50_TAX_SCHEMA_IDS,
        TM_PURCHASED_PRINCIPAL_ID,
        TM_PURCHASED_INTEREST_ID,
        TM_GOVERNMENT_GUARANTEED_DEBT_ID,
        TM_FX_BUY_ID,
        TM_FX_SELL_ID,
        TM_SWAP_BUY_ID,
        TM_SWAP_SELL_ID,
        TM_MARGIN_LOAN_TYPE_ID,
        TM_MARGIN_LOAN_QUALITY_ID,
        TM_MARGIN_LOAN_MATURITY_ID,
        TM_MARGIN_LOAN_BUSINESS_ID,
        TM_MARGIN_LOAN_INDUSTRY_ID,
    ):
        if seen.get(schema_id) != "TM":
            raise BusinessSchemaUpdateError(
                f"TM {schema_id} is not globally unique and correctly scoped"
            )
    if set(seen) & REVIEWED_EXTERNAL_IDS:
        raise BusinessSchemaUpdateError("current schema collides with reviewed external IDs")

    supporting = audit.get("supporting_hierarchy_workbooks_sha256")
    if (
        audit.get("supporting_hierarchy_workbooks_mutated") is not False
        or not isinstance(supporting, dict)
        or not supporting
    ):
        raise BusinessSchemaUpdateError("supporting hierarchy preservation audit is absent")
    for relative, expected_hash in supporting.items():
        if sha256_file(project_root / relative) != expected_hash:
            raise BusinessSchemaUpdateError(f"supporting hierarchy workbook changed: {relative}")
    return audit


def apply_business_schema_update(
    project_root: Path,
    *,
    audit_path: Path | None = None,
) -> BusinessSchemaUpdateResult:
    project_root = project_root.resolve()
    audit_path = (
        audit_path.resolve() if audit_path is not None else project_root / BUSINESS_UPDATE_AUDIT
    )
    if audit_path.is_file():
        audit = verify_business_schema_update(project_root, audit_path)
        return BusinessSchemaUpdateResult(
            status="ALREADY_APPLIED_AND_VERIFIED",
            audit_path=str(audit_path),
            workbook_sha256={
                statement: str(record["after_sha256"])
                for statement, record in audit["workbooks"].items()
            },
        )

    baseline_paths = {
        "CDKT": project_root / CDKT_BASELINE_WORKBOOK,
        "KQKD": project_root / KQKD_BASELINE_WORKBOOK,
        "LCTT": project_root / LCTT_BASELINE_WORKBOOK,
        "TM": project_root / TM_BASELINE_WORKBOOK,
    }
    workbook_paths = {
        "CDKT": project_root / CDKT_WORKBOOK,
        "KQKD": project_root / KQKD_WORKBOOK,
        "LCTT": project_root / LCTT_WORKBOOK,
        "TM": project_root / TM_WORKBOOK,
    }
    preexisting_paths = {path for path in workbook_paths.values() if path.exists()}
    before_payloads = {statement: path.read_bytes() for statement, path in baseline_paths.items()}
    if sha256_bytes(before_payloads["CDKT"]) != CDKT_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("CDKT workbook is not the authorized baseline")
    if sha256_bytes(before_payloads["KQKD"]) != KQKD_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("KQKD workbook is not the authorized baseline")
    if sha256_bytes(before_payloads["LCTT"]) != LCTT_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("LCTT workbook is not the authorized baseline")
    if sha256_bytes(before_payloads["TM"]) != TM_BEFORE_SHA256:
        raise BusinessSchemaUpdateError("TM workbook is not the authorized baseline")
    before_seen = _assert_global_identity(
        project_root,
        cdkt_path=baseline_paths["CDKT"],
        kqkd_path=baseline_paths["KQKD"],
        lctt_path=baseline_paths["LCTT"],
        tm_path=baseline_paths["TM"],
        expected_count=1593,
    )
    if NEW_SCHEMA_IDS & set(before_seen):
        raise BusinessSchemaUpdateError("one or more authorized new IDs already exist")
    if set(before_seen) & REVIEWED_EXTERNAL_IDS:
        raise BusinessSchemaUpdateError("baseline schema collides with reviewed external IDs")

    candidate_payloads: dict[str, bytes] = {}
    before_member_hashes: dict[str, dict[str, str]] = {}
    after_member_hashes: dict[str, dict[str, str]] = {}
    for statement in ("CDKT", "KQKD", "LCTT", "TM"):
        after, before_members, after_members = _build_updated_workbook(
            before_payloads[statement], statement_type=statement
        )
        candidate_payloads[statement] = after
        before_member_hashes[statement] = before_members
        after_member_hashes[statement] = after_members
        if workbook_paths[statement].exists() and sha256_file(
            workbook_paths[statement]
        ) != sha256_bytes(after):
            raise BusinessSchemaUpdateError(
                f"existing {statement} v2 workbook differs from deterministic candidate"
            )

    candidate_paths: dict[str, Path] = {}
    try:
        for statement, payload in candidate_payloads.items():
            descriptor, name = tempfile.mkstemp(
                prefix=f".{statement.lower()}-business-schema-candidate-",
                suffix=".xlsx",
                dir=workbook_paths[statement].parent,
            )
            path = Path(name)
            candidate_paths[statement] = path
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            _assert_candidate(baseline_paths[statement], path, statement=statement)
        candidate_seen = _assert_global_identity(
            project_root,
            overrides=candidate_paths,
            expected_count=1628,
        )
        if (
            candidate_seen.get(CDKT_TOTAL_EQUITY_ID) != "CDKT"
            or candidate_seen.get(KQKD_TOTAL_OPERATING_INCOME_ID) != "KQKD"
            or candidate_seen.get(LCTT_INVESTMENT_CONTRIBUTION_NET_ID) != "LCTT"
            or candidate_seen.get(TM_TOTAL_INTERBANK_PROVISION_ID) != "TM"
            or any(
                candidate_seen.get(schema_id) != "TM"
                for schema_id in (
                    TM_HEALTH_SOCIAL_ID,
                    TM_ARTS_RECREATION_ID,
                    TM_OTHER_SERVICES_ID,
                    TM_HOUSEHOLD_EMPLOYMENT_ID,
                    *TM_PAGE50_TAX_SCHEMA_IDS,
                    TM_PURCHASED_PRINCIPAL_ID,
                    TM_PURCHASED_INTEREST_ID,
                    TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                    TM_FX_BUY_ID,
                    TM_FX_SELL_ID,
                    TM_SWAP_BUY_ID,
                    TM_SWAP_SELL_ID,
                    TM_MARGIN_LOAN_TYPE_ID,
                    TM_MARGIN_LOAN_QUALITY_ID,
                    TM_MARGIN_LOAN_MATURITY_ID,
                    TM_MARGIN_LOAN_BUSINESS_ID,
                    TM_MARGIN_LOAN_INDUSTRY_ID,
                )
            )
        ):
            raise BusinessSchemaUpdateError("candidate global ID/statement bindings drifted")
    finally:
        for path in candidate_paths.values():
            path.unlink(missing_ok=True)

    hierarchy_paths = (
        "vst_level/vst_bank_balance_sheet.xlsx",
        "vst_level/vst_bank_income_sheet.xlsx",
        "vst_level/vst_bank_cashflow_sheet.xlsx",
        "vst_level/vst_bank_detailed_notes_sheet.xlsx",
    )
    supporting_hashes = {
        relative: sha256_file(project_root / relative) for relative in hierarchy_paths
    }
    workbook_audit: dict[str, dict[str, object]] = {}
    for statement in ("CDKT", "KQKD", "LCTT", "TM"):
        before_records = _identity_records(baseline_paths[statement])
        unchanged_members = {
            name: digest
            for name, digest in before_member_hashes[statement].items()
            if name not in _TARGET_MEMBERS
        }
        workbook_audit[statement] = {
            "baseline_path": {
                "CDKT": CDKT_BASELINE_WORKBOOK,
                "KQKD": KQKD_BASELINE_WORKBOOK,
                "LCTT": LCTT_BASELINE_WORKBOOK,
                "TM": TM_BASELINE_WORKBOOK,
            }[statement],
            "path": {
                "CDKT": CDKT_WORKBOOK,
                "KQKD": KQKD_WORKBOOK,
                "LCTT": LCTT_WORKBOOK,
                "TM": TM_WORKBOOK,
            }[statement],
            "before_sha256": {
                "CDKT": CDKT_BEFORE_SHA256,
                "KQKD": KQKD_BEFORE_SHA256,
                "LCTT": LCTT_BEFORE_SHA256,
                "TM": TM_BEFORE_SHA256,
            }[statement],
            "after_sha256": sha256_bytes(candidate_payloads[statement]),
            "before_row_count_including_header": len(before_records),
            "after_row_count_including_header": {
                "CDKT": CDKT_AFTER_ROW_COUNT,
                "KQKD": KQKD_AFTER_ROW_COUNT,
                "LCTT": LCTT_AFTER_ROW_COUNT,
                "TM": TM_AFTER_ROW_COUNT,
            }[statement],
            "preservation": {
                "existing_item_id_name_order_sha256": _records_hash(_item_pairs(before_records)),
                "existing_ids_and_relative_order_preserved": True,
                "allowed_existing_name_corrections": (
                    [
                        {
                            "schema_id": 4350,
                            "before": CDKT_4350_OLD_NAME,
                            "after": CDKT_4350_CORRECTED_NAME,
                        }
                    ]
                    if statement == "CDKT"
                    else (
                        [
                            {
                                "schema_id": 770,
                                "before": TM_770_OLD_NAME,
                                "after": TM_770_CORRECTED_NAME,
                            },
                            {
                                "schema_id": TM_EDUCATION_ID,
                                "before": TM_EDUCATION_OLD_NAME,
                                "after": TM_EDUCATION_NAME,
                            },
                        ]
                        if statement == "TM"
                        else []
                    )
                ),
                "zip_member_set_preserved": True,
                "only_changed_zip_members": sorted(_TARGET_MEMBERS),
                "unchanged_zip_members_sha256": unchanged_members,
                "changed_zip_members_before_sha256": {
                    name: before_member_hashes[statement][name] for name in sorted(_TARGET_MEMBERS)
                },
                "changed_zip_members_after_sha256": {
                    name: after_member_hashes[statement][name] for name in sorted(_TARGET_MEMBERS)
                },
            },
        }

    audit: dict[str, object] = {
        "format_version": 1,
        "migration_id": "BUSINESS-SCHEMA-5712-5713-5714-5718-5749",
        "status": "APPLIED_AND_VERIFIED",
        "applied_at": datetime.now(UTC).isoformat(),
        "authority": {
            "approved_on": "2026-08-08",
            "policy": "USER_AUTHORIZED_BUSINESS_SCHEMA_UPDATE",
        },
        "collision_safety": {
            "baseline_global_schema_count": 1593,
            "result_global_schema_count": 1628,
            "new_ids": sorted(NEW_SCHEMA_IDS),
            "reviewed_external_ids": sorted(REVIEWED_EXTERNAL_IDS),
            "new_ids_disjoint_from_reviewed_external_ids": True,
            "result_ids_globally_unique": True,
        },
        "schema_changes": _expected_schema_changes(),
        "business_formulas": _expected_formulas(),
        "workbooks": workbook_audit,
        "unaffected_workbooks_sha256": {},
        "supporting_hierarchy_workbooks_mutated": False,
        "supporting_hierarchy_workbooks_sha256": supporting_hashes,
    }

    try:
        for statement in ("CDKT", "KQKD", "LCTT", "TM"):
            mode = baseline_paths[statement].stat().st_mode & 0o777
            atomic_write_bytes(workbook_paths[statement], candidate_payloads[statement], mode=mode)
        atomic_write_json(audit_path, audit)
        verify_business_schema_update(project_root, audit_path)
    except Exception:
        for path in workbook_paths.values():
            if path not in preexisting_paths:
                path.unlink(missing_ok=True)
        audit_path.unlink(missing_ok=True)
        raise

    return BusinessSchemaUpdateResult(
        status="APPLIED_AND_VERIFIED",
        audit_path=str(audit_path),
        workbook_sha256={
            statement: sha256_bytes(payload) for statement, payload in candidate_payloads.items()
        },
    )


def apply_business_formula_hierarchy(schema: Sequence[SchemaItem]) -> None:
    """Apply the authorized formula hierarchy after the supplied VST hierarchy.

    The VST workbooks stay immutable. Their original edges are loaded first, then
    this small, audited overlay introduces the new totals and corrects the
    pre-existing 4325 component boundary required by the approved formulas.
    """

    by_key = {(item.statement_type, item.schema_id): item for item in schema}
    if not any(
        key in by_key
        for key in (
            ("CDKT", 5712),
            ("KQKD", 5713),
            ("LCTT", 5714),
            ("TM", 5718),
        )
    ):
        return
    required = (
        {
            ("CDKT", schema_id)
            for schema_id in (4304, 4305, 4306, 4325, 4364, *CDKT_4325_COMPONENTS, 5712)
        }
        | {
            ("KQKD", schema_id)
            for schema_id in (4376, 4391, *KQKD_TOTAL_OPERATING_INCOME_COMPONENTS, 5713)
        }
        | {
            ("LCTT", schema_id)
            for schema_id in (4111, 4118, 4119, 4143, 4144, 4145, 4146, 4147, 4120, 4121, 5714)
        }
        | {("TM", schema_id) for schema_id in (575, *TM_TOTAL_INTERBANK_PROVISION_COMPONENTS, 5718)}
        | {
            ("TM", schema_id)
            for schema_id in (
                TM_LOAN_INDUSTRY_PARENT_ID,
                TM_EDUCATION_ID,
                TM_HEALTH_SOCIAL_ID,
                TM_ARTS_RECREATION_ID,
                TM_OTHER_SERVICES_ID,
                TM_HOUSEHOLD_EMPLOYMENT_ID,
                TM_LOAN_BUSINESS_PARENT_ID,
                TM_LOAN_BUSINESS_OTHER_ID,
                *range(784, 800),
                1142,
                *TM_PAGE50_TAX_SCHEMA_IDS,
                800,
                805,
                TM_PURCHASED_PRINCIPAL_ID,
                TM_PURCHASED_INTEREST_ID,
                TM_GOVERNMENT_GUARANTEED_DEBT_ID,
                1294,
                1301,
                1302,
                TM_FX_BUY_ID,
                TM_FX_SELL_ID,
                TM_SWAP_BUY_ID,
                TM_SWAP_SELL_ID,
                717,
                747,
                752,
                TM_MARGIN_LOAN_TYPE_ID,
                TM_MARGIN_LOAN_QUALITY_ID,
                TM_MARGIN_LOAN_MATURITY_ID,
                TM_MARGIN_LOAN_BUSINESS_ID,
                TM_MARGIN_LOAN_INDUSTRY_ID,
            )
        }
    )
    missing = sorted(required - set(by_key))
    if missing:
        raise BusinessSchemaUpdateError(f"business-formula hierarchy lacks schema items: {missing}")

    expected_initial_parents = {
        ("CDKT", 4325): 4305,
        ("CDKT", 4306): 4305,
        ("CDKT", 4365): 4364,
        **{("KQKD", schema_id): 4376 for schema_id in KQKD_TOTAL_OPERATING_INCOME_COMPONENTS},
        ("KQKD", 4391): 4376,
        ("LCTT", 4120): 4111,
        ("LCTT", 4121): 4111,
        ("TM", TM_EDUCATION_ID): TM_LOAN_INDUSTRY_PARENT_ID,
        ("TM", TM_LOAN_BUSINESS_OTHER_ID): TM_LOAN_BUSINESS_PARENT_ID,
        **{("TM", schema_id): TM_PROVISION_MOVEMENT_ID for schema_id in range(784, 800)},
        ("TM", 1301): 1294,
        ("TM", 1302): 1294,
        ("TM", TM_MARGIN_LOAN_TYPE_ID): None,
        ("TM", TM_MARGIN_LOAN_QUALITY_ID): None,
        ("TM", TM_MARGIN_LOAN_MATURITY_ID): None,
        ("TM", TM_MARGIN_LOAN_BUSINESS_ID): None,
        ("TM", TM_MARGIN_LOAN_INDUSTRY_ID): None,
    }
    for key, expected_parent in expected_initial_parents.items():
        if by_key[key].parent_id != expected_parent:
            raise BusinessSchemaUpdateError(
                f"pre-overlay hierarchy parent drift at {key}: "
                f"expected={expected_parent}, actual={by_key[key].parent_id}"
            )

    by_key[("CDKT", 4365)].parent_id = 4325
    by_key[("CDKT", 4325)].parent_id = CDKT_TOTAL_EQUITY_ID
    by_key[("CDKT", 4306)].parent_id = CDKT_TOTAL_EQUITY_ID
    by_key[("CDKT", CDKT_TOTAL_EQUITY_ID)].parent_id = 4305
    by_key[("CDKT", CDKT_TOTAL_EQUITY_ID)].hierarchy_level = 2
    by_key[("CDKT", CDKT_TOTAL_EQUITY_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in KQKD_TOTAL_OPERATING_INCOME_COMPONENTS:
        by_key[("KQKD", schema_id)].parent_id = KQKD_TOTAL_OPERATING_INCOME_ID
    by_key[("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID)].parent_id = 4376
    by_key[("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID)].hierarchy_level = 0
    by_key[("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS:
        by_key[("LCTT", schema_id)].parent_id = LCTT_INVESTMENT_CONTRIBUTION_NET_ID
    by_key[("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID)].parent_id = 4111
    by_key[("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID)].hierarchy_level = 3
    by_key[("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    by_key[("TM", TM_TOTAL_INTERBANK_PROVISION_ID)].parent_id = 575
    by_key[("TM", TM_TOTAL_INTERBANK_PROVISION_ID)].hierarchy_level = 2
    by_key[("TM", TM_TOTAL_INTERBANK_PROVISION_ID)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (
        TM_HEALTH_SOCIAL_ID,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
    ):
        by_key[("TM", schema_id)].parent_id = TM_LOAN_INDUSTRY_PARENT_ID
        by_key[("TM", schema_id)].hierarchy_level = 3
        by_key[("TM", schema_id)].hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in range(785, 792):
        by_key[("TM", schema_id)].parent_id = TM_GENERAL_PROVISION_MOVEMENT_ID
    for schema_id in range(793, 800):
        by_key[("TM", schema_id)].parent_id = TM_SPECIFIC_PROVISION_MOVEMENT_ID

    page50_parent_by_id = {
        5723: 5727,
        5724: 5723,
        5725: 5727,
        5726: 5725,
        5727: 1142,
        5728: 5731,
        5729: 5731,
        5730: 5731,
        5731: 1142,
        5732: 5737,
        5733: 5737,
        5734: 5737,
        5735: 5737,
        5736: 5737,
        5737: 1142,
    }
    page50_level_by_id = {
        5723: 2,
        5724: 3,
        5725: 2,
        5726: 3,
        5727: 1,
        5728: 2,
        5729: 2,
        5730: 2,
        5731: 1,
        5732: 2,
        5733: 2,
        5734: 2,
        5735: 2,
        5736: 2,
        5737: 1,
    }
    for schema_id in TM_PAGE50_TAX_SCHEMA_IDS:
        item = by_key[("TM", schema_id)]
        item.parent_id = page50_parent_by_id[schema_id]
        item.hierarchy_level = page50_level_by_id[schema_id]
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (TM_PURCHASED_PRINCIPAL_ID, TM_PURCHASED_INTEREST_ID):
        item = by_key[("TM", schema_id)]
        item.parent_id = 800
        item.hierarchy_level = 2
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    guaranteed = by_key[("TM", TM_GOVERNMENT_GUARANTEED_DEBT_ID)]
    guaranteed.parent_id = 805
    guaranteed.hierarchy_level = 3
    guaranteed.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for schema_id in (TM_FX_BUY_ID, TM_FX_SELL_ID):
        item = by_key[("TM", schema_id)]
        item.parent_id = 1301
        item.hierarchy_level = 3
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT
    swap = by_key[("TM", 1302)]
    swap.parent_id = 1301
    swap.hierarchy_level = 3
    swap.hierarchy_source = BUSINESS_UPDATE_AUDIT
    for schema_id in (TM_SWAP_BUY_ID, TM_SWAP_SELL_ID):
        item = by_key[("TM", schema_id)]
        item.parent_id = 1302
        item.hierarchy_level = 4
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    margin_hierarchy = {
        TM_MARGIN_LOAN_TYPE_ID: (717, 3),
        TM_MARGIN_LOAN_QUALITY_ID: (747, 4),
        TM_MARGIN_LOAN_MATURITY_ID: (752, 3),
        TM_MARGIN_LOAN_BUSINESS_ID: (766, 3),
        TM_MARGIN_LOAN_INDUSTRY_ID: (727, 3),
    }
    for schema_id, (parent_id, level) in margin_hierarchy.items():
        item = by_key[("TM", schema_id)]
        item.parent_id = parent_id
        item.hierarchy_level = level
        item.hierarchy_source = BUSINESS_UPDATE_AUDIT

    for item in schema:
        item.children = []
        item.siblings = []
    for item in sorted(
        schema, key=lambda candidate: (candidate.statement_type, candidate.display_order)
    ):
        if item.parent_id is not None:
            by_key[(item.statement_type, item.parent_id)].children.append(item.schema_id)
    for item in schema:
        if item.parent_id is not None:
            siblings = by_key[(item.statement_type, item.parent_id)].children
            item.siblings = [schema_id for schema_id in siblings if schema_id != item.schema_id]

    exact_edges = {
        ("CDKT", 4364): (4337, 4373, 4338, 4340, 4374, 4339),
        ("CDKT", 4325): CDKT_4325_COMPONENTS,
        ("CDKT", CDKT_TOTAL_EQUITY_ID): CDKT_TOTAL_EQUITY_COMPONENTS,
        ("CDKT", 4305): (4304, CDKT_TOTAL_EQUITY_ID),
        ("KQKD", KQKD_TOTAL_OPERATING_INCOME_ID): KQKD_TOTAL_OPERATING_INCOME_COMPONENTS,
        ("KQKD", 4376): (KQKD_TOTAL_OPERATING_INCOME_ID, 4391),
        ("LCTT", LCTT_INVESTMENT_CONTRIBUTION_NET_ID): (
            LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS
        ),
        ("LCTT", 4111): (4118, 4119, 4143, 4144, 4145, 4146, 5714, 4147),
        ("TM", 575): (576, 585, 5718),
        ("TM", 576): (577, 578, 579, 580, 581, 582, 583, 584),
        ("TM", 585): (586, 587, 588, 589, 590, 591),
        ("TM", 5718): (),
        ("TM", TM_LOAN_INDUSTRY_PARENT_ID): (
            728,
            729,
            730,
            731,
            732,
            733,
            734,
            735,
            736,
            TM_EDUCATION_ID,
            TM_HEALTH_SOCIAL_ID,
            738,
            739,
            740,
            741,
            742,
            743,
            TM_ARTS_RECREATION_ID,
            TM_OTHER_SERVICES_ID,
            TM_HOUSEHOLD_EMPLOYMENT_ID,
            744,
            745,
            TM_MARGIN_LOAN_INDUSTRY_ID,
        ),
        ("TM", 717): (*range(718, 727), TM_MARGIN_LOAN_TYPE_ID),
        ("TM", 747): (TM_MARGIN_LOAN_QUALITY_ID,),
        ("TM", 752): (753, 754, 755, TM_MARGIN_LOAN_MATURITY_ID),
        ("TM", TM_LOAN_BUSINESS_PARENT_ID): (
            *range(767, 783),
            TM_MARGIN_LOAN_BUSINESS_ID,
        ),
        ("TM", TM_PROVISION_MOVEMENT_ID): TM_PROVISION_MOVEMENT_COMPONENTS,
        ("TM", TM_GENERAL_PROVISION_MOVEMENT_ID): tuple(range(785, 792)),
        ("TM", TM_SPECIFIC_PROVISION_MOVEMENT_ID): tuple(range(793, 800)),
        ("TM", 1142): (
            1143,
            1151,
            1157,
            1167,
            1175,
            1188,
            1193,
            1198,
            1205,
            1221,
            1229,
            1240,
            5727,
            5731,
            5737,
        ),
        ("TM", 5723): (5724,),
        ("TM", 5725): (5726,),
        ("TM", 5727): (5723, 5725),
        ("TM", 5731): (5728, 5729, 5730),
        ("TM", 5737): (5732, 5733, 5734, 5735, 5736),
        ("TM", 800): (801, 802, 803, 5738, 5739),
        ("TM", 805): (
            806,
            807,
            5740,
            808,
            809,
            810,
            811,
            812,
            813,
            814,
            815,
            816,
            817,
            818,
            819,
            820,
            821,
            822,
            823,
            824,
            825,
            826,
            827,
            828,
        ),
        ("TM", 1294): (1295, 1296, 1297, 1298, 1299, 1300, 1301, 1303, 1304),
        ("TM", 1301): TM_FX_COMMITMENT_COMPONENTS,
        ("TM", 1302): TM_SWAP_COMMITMENT_COMPONENTS,
    }
    for key, expected_children in exact_edges.items():
        if tuple(by_key[key].children) != expected_children:
            raise BusinessSchemaUpdateError(
                f"business-formula hierarchy children drift at {key}: "
                f"expected={expected_children}, actual={tuple(by_key[key].children)}"
            )
