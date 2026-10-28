"""F37 D1 (split-section path only): an owner section titled "Dự phòng rủi ro cho vay khách hàng".

Real shape: EIB parent annual 2025 (FULL271 doc 39) p32, section "10. DỰ PHÒNG RỦI RO CHO VAY KHÁCH HÀNG" over a
transposed table with exactly Dự phòng chung | Dự phòng cụ thể columns and provision actions. The generic owner test
(_is_structural_customer_movement) wants "dự phòng rủi ro tín dụng" + "thay đổi|tăng giảm|đối với", so this title
was not an owner. D1 accepts it only in the split-section binder; a competing owner title still vetoes.
"""
import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    _family37_layout_member_kind_v1,
    _family37_split_customer_movement_v1,
)

ROOT = Path(__file__).resolve().parents[2]
P032 = json.loads(
    (ROOT / "tests/fixtures/source_structure/f37-annual-split-sections-20261028-v1/eib039_p032.json").read_bytes())


def _owner_and_table():
    owner = copy.deepcopy(P032["sections"][0])
    return owner, owner["tables"][0]


def test_eib039_owner_title_is_accepted_only_by_the_split_check():
    owner, table = _owner_and_table()
    assert _family37_layout_member_kind_v1(owner, table) is None  # the shared owner test is unchanged
    assert _family37_split_customer_movement_v1(owner, table) is True


@pytest.mark.parametrize("title", [
    "10. DỰ PHÒNG RỦI RO CHO VAY CÁC TỔ CHỨC TÍN DỤNG KHÁC",   # interbank owner
    "10. DỰ PHÒNG RỦI RO CHO KHOẢN MUA NỢ",                    # purchased debt owner
    "10. CHO VAY KHÁCH HÀNG",                                  # no provision words
])
def test_other_owner_titles_are_not_accepted(title):
    owner, table = _owner_and_table()
    owner["title_exact"] = title
    assert _family37_split_customer_movement_v1(owner, table) is False


def test_table_without_general_specific_columns_is_not_accepted():
    owner, table = _owner_and_table()
    table["columns"] = [column for column in table["columns"]
                        if "cụ thể" not in " ".join(column.get("header_path_exact") or []).lower()]
    assert _family37_split_customer_movement_v1(owner, table) is False
