"""Production lexical regressions without prototype helper stubs.

Legacy hashes captured before activation from exact evaluator
177521586f3ff794e06345e2df5bd996a99d615939f0980940450b43692522e6.
Public period/scope/PDF/financial gates remain independently required.
"""
import copy
import unicodedata
import unittest
from hashlib import sha256

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1

LEGACY_RECEIPT_HASHES = (
    "967d56c607d8b378353cdf3dccbf967e357f6b2a3956bcd52138be4af4f65dc1",
    "5ead3619c30df51f2c6cb093cf6204af458aa16ea06f46d4db04d45d6c724742",
    "cf08f2c74b4fcd2356a75724bca3c6c25b407c18a8a662cce589d1cdf2570d40",
    "d99b2f4a922d9efc84c312ed0a3740d7bdf585bed4553ec30d236d0c05109889",
    "ebc85378613d3911e0fa6a73d2adab9cc7c4cd1a73ba2ff0518b535d7c1dd88f",
    "387f8ce351ae33da0b8ea239410e1b89a6249702eb04c3df1a4be83a92906f9f",
    "8c2325a6881d258ee18c177292b1cad8f09a341101f317da2cbc052d8ea81c1a",
)


class TestOwnedExplicitRangeCaption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposed = staticmethod(family._owned_flow_date_range_caption_constraint)

    def section(self, statement="INCOME_STATEMENT", kind="PRIMARY_STATEMENT"):
        return {"content_kind": kind, "statement_type": statement}

    def caption(self, *, written=False, start="01/01/2026", end="30/06/2026", scope="RIÊNG"):
        def render(value):
            d, m, y = value.split("/")
            return f"{d} tháng {m} năm {y}" if written else value
        title = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG" + (" " + scope if scope else "")
        return title + "\nCho giai đoạn từ ngày " + render(start) + " đến ngày " + render(end)

    def call(self, caption, section=None, source_kind="SECTION_TITLE"):
        return self.proposed(section or self.section(), source_kind=source_kind, source_exact=caption)

    def assert_hold(self, caption, **kwargs):
        result = self.call(caption, **kwargs)
        self.assertIsNotNone(result)
        self.assertIs(result["supported"], False)
        self.assertTrue(result["source_date_range_evidence"]["reasons"])
        return result

    def test_two_whole_bare_scaffolds_both_title_carriers(self):
        for written in (False, True):
            for source_kind in ("SECTION_TITLE", "TABLE_TITLE"):
                for end, months in (("31/03/2026", 3), ("30/06/2026", 6), ("30/09/2026", 9)):
                    with self.subTest(written=written, source_kind=source_kind, end=end):
                        raw = self.caption(written=written, end=end)
                        value = self.call(raw, source_kind=source_kind)
                        self.assertTrue(value["supported"])
                        self.assertEqual(value["printed_months"], months)
                        self.assertEqual(value["printed_start_date"], "2026-01-01")
                        self.assertEqual(value["source_exact"], raw)

    def test_scope_furniture_never_grants_scope_or_other_authority(self):
        for scope in ("", "RIÊNG", "HỢP NHẤT"):
            value = self.call(self.caption(scope=scope))
            self.assertTrue(value["supported"])
            proof = value["source_date_range_evidence"]
            for key in ("report_scope_permission_granted", "unit_permission_granted",
                        "comparative_year_permission_granted", "amounts_used_as_authority",
                        "source_period_keys_modified", "start_dates_inferred",
                        "sibling_or_other_surface_used"):
                self.assertIs(proof[key], False)
            self.assertNotIn("resolved_source_duration_semantics", value)

    def test_nfc_nfd_case_and_declared_layout(self):
        for written in (False, True):
            raw = self.caption(written=written)
            for value in (raw, unicodedata.normalize("NFD", raw), raw.upper(),
                          raw.replace("\n", "\\n"), raw.replace(" ", "\u00a0")):
                with self.subTest(written=written, value=value):
                    self.assertTrue(self.call(value)["supported"])
                    self.assertEqual(self.call(value)["source_exact"], value)

    def test_actual_calendar_dates_and_interim_ytd_only(self):
        pairs = [
            ("01/01/2026", "31/12/2026"),  # Annual stays explicitly unsupported.
            ("01/01/2026", "30/06/2025"), ("01/01/2025", "30/06/2026"),
            ("01/04/2026", "30/06/2026"), ("02/01/2026", "30/06/2026"),
            ("01/01/2026", "31/06/2026"), ("01/01/2026", "29/02/2026"),
            ("01/01/2024", "29/02/2024"), ("01/01/2026", "30/03/2026"),
            ("01/01/2026", "31/09/2026"), ("01/01/0000", "31/03/0000"),
        ]
        for written in (False, True):
            for start, end in pairs:
                with self.subTest(written=written, start=start, end=end):
                    self.assert_hold(self.caption(written=written, start=start, end=end))
        annual = self.assert_hold(self.caption(end="31/12/2026"))
        self.assertIn("PRINTED_ANNUAL_RANGE_NOT_GRANTED_BY_INTERIM_ROUTE",
                      annual["source_date_range_evidence"]["reasons"])

    def test_raw_numeric_annotations_and_unicode_numerals_cannot_be_folded(self):
        for written in (False, True):
            raw = self.caption(written=written)
            for wrong in (raw.replace("2026", "2026\u0301", 1),
                          raw.replace("30", "30\u0300", 1),
                          raw.replace("01", "01\u20dd", 1),
                          raw.replace("2026", "２０２６", 1),
                          raw.replace("2026", "20 26", 1),
                          raw.replace("2026", "2026¹", 1)):
                with self.subTest(written=written, wrong=wrong):
                    self.assert_hold(wrong)

    def test_raw_controls_and_invisible_annotations_veto_before_layout_permission(self):
        raw = self.caption()
        for bad in ("\v", "\f", "\x00", "\x85", "\u200b", "\u2060", "\ufeff"):
            self.assert_hold(raw.replace("Cho ", "Cho" + bad, 1))
        # A surrogate is not canonical source JSON; it must never yield PASS.
        with self.assertRaises(UnicodeError):
            self.call(raw + "\ud800")

    def test_whole_caption_no_prologue_form_method_or_extra_assertion_stripping(self):
        raw = self.caption()
        for wrong in (
            "Ngân hàng Thương mại Cổ phần Ví Dụ\n" + raw,
            "Mẫu số: B03/TCTD\n" + raw, raw + "\nB03a/TCTD",
            raw + " (tiếp theo)", raw + " (phương pháp trực tiếp)",
            raw + ".", raw + "; kỳ trước kết thúc ngày 30/06/2024",
            raw.replace("Cho giai đoạn", "Không cho giai đoạn"),
            raw.replace("Cho giai đoạn", "Thời kỳ tài chính"),
            raw.replace("HOẠT ĐỘNG RIÊNG", "HOẠT ĐỘNG của riêng Ngân hàng"),
        ):
            with self.subTest(wrong=wrong):
                self.assert_hold(wrong)

    def test_written_dates_cannot_mix_notations_or_have_missing_tokens(self):
        raw = self.caption(written=True)
        for wrong in (
            raw.replace("01 tháng 01 năm 2026", "01/01/2026"),
            raw.replace("30 tháng 06 năm 2026", "30/06/2026"),
            raw.replace(" tháng 01", " 01", 1),
            raw.replace(" năm 2026", " 2026", 1),
        ):
            self.assert_hold(wrong)

    def test_wrong_owner_or_cash_flow_cannot_borrow_new_income_route(self):
        raw = self.caption()
        for section in (self.section(kind="FINANCIAL_NOTE"), self.section("CASH_FLOW"),
                        self.section("BALANCE_SHEET")):
            self.assert_hold(raw, section=section)
        for source_kind in ("NARRATIVE", "ROW_ANCESTOR"):
            self.assertIsNone(self.call(raw, source_kind=source_kind))
        cf = raw.replace("KẾT QUẢ HOẠT ĐỘNG", "LƯU CHUYỂN TIỀN TỆ")
        self.assert_hold(cf, section=self.section("CASH_FLOW"))

    def test_input_unchanged_source_sha_receipt_and_raw_lines_bound(self):
        section = self.section()
        before = copy.deepcopy(section)
        raw = self.caption(written=True).replace("\n", "\\n")
        result = self.call(raw, section=section)
        proof = result["source_date_range_evidence"]
        self.assertEqual(section, before)
        self.assertEqual(proof["source_exact"], raw)
        self.assertEqual(proof["source_sha256"], sha256(raw.encode()).hexdigest())
        self.assertEqual(proof["source_lines_exact"], raw.split("\n"))
        material = {k: v for k, v in proof.items() if k != "receipt_id"}
        self.assertEqual(proof["receipt_id"],
                         "gjitfav1:owned-flow-date-range-caption:" + canonical_json_sha256_v1(material))
        self.assertNotEqual(proof["receipt_id"], self.call(self.caption())["source_date_range_evidence"]["receipt_id"])

    def test_old_complete_and_unsupported_routes_keep_exact_receipt_bytes(self):
        income = ("Báo cáo kết quả hoạt động riêng giữa niên độ "
                  "cho giai đoạn từ ngày 01/01/2026 đến ngày 30/06/2026")
        cf = ("Báo cáo lưu chuyển tiền tệ hợp nhất giữa niên độ "
              "cho giai đoạn từ ngày 01/01/2026 đến ngày 30/06/2026")
        for index, (section, raw) in enumerate((
            (self.section(), income),
            (self.section(), income.replace("giữa niên độ", "giữa niên độ (tiếp theo)")),
            (self.section(), income + " (tiếp theo)"),
            (self.section(), income.replace("30/06", "31/12")),
            (self.section("CASH_FLOW"), cf + " (phương pháp trực tiếp)"),
            (self.section("CASH_FLOW"), cf + " (phương pháp gián tiếp)"),
            (self.section(), income + " thêm khẳng định"),
        )):
            with self.subTest(raw=raw):
                kwargs = {"source_kind": "SECTION_TITLE", "source_exact": raw}
                self.assertEqual(sha256(canonical_json_bytes_v1(self.proposed(section, **kwargs))).hexdigest(), LEGACY_RECEIPT_HASHES[index])

    def test_contrary_caption_endpoints_are_retained_not_replaced_or_borrowed(self):
        left = self.call(self.caption(end="31/03/2026"))
        frozen = copy.deepcopy(left)
        right = self.call(self.caption(end="30/06/2026"))
        self.assertTrue(left["supported"] and right["supported"])
        self.assertNotEqual(left["printed_end_date"], right["printed_end_date"])
        self.assertEqual(left, frozen)
        # This only checks independent lexical outputs. The unchanged production
        # whole-census/pair-consistency gates must reject contradictory owners.


if __name__ == "__main__":
    unittest.main()
