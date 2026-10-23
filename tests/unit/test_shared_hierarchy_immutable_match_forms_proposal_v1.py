"""UNRUN differential tests for the separately reviewed shared performance draft.

Apply the proposal ONLY in a reviewed private checkout before running this file.
No runtime substitution is used. The baseline predicate below is copied from
aa9ff2e08ede08592d00d1b290da2e5bf09f3bf3, hierarchical module SHA-256
3f53529552a01abd8543b648088cda27cb4b1fe492a082399b2f24e8d04eb6da.
It does not call the new form-preparation or prepared predicate.
Config tests use actual imported-checkout F36/F37/F39 topology matchers, not
handmade shortened alias lists. These are not a speed/source/acceptance gate.
"""
from __future__ import annotations

import copy
import json
import re
import unicodedata
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from bctc_ai.evaluation import gemini_json_hierarchical_accounting_family_v1 as subject
from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)


def _old_matches(value, alias):
    """Embedded OLD predicate, retaining all branches and normalization calls."""
    folded = subject._normalized(value)
    alias = subject._normalized(alias)
    forms = {folded, subject._without_leading_ordinal(folded)}
    # Preserve BOTH old interpretations of a literal backslash-n token.
    if type(value) is str and "\\n" in value:
        preserved_n = subject._normalized(value.replace("\\n", " n"))
        forms |= {preserved_n, subject._without_leading_ordinal(preserved_n)}
    forms |= {
        form.removeprefix(prefix).strip()
        for form in tuple(forms)
        for prefix in ("trong do ", "bao gom ")
        if form.startswith(prefix)
    }
    if alias in forms:
        return True
    suffixes = {form.removeprefix(alias).strip() for form in forms if form.startswith(alias + " ")}
    allowed_suffix_tokens = {
        "1", "2", "3", "4", "5", "i", "ii", "iii", "iv", "v",
    }

    def is_note_reference_suffix(suffix):
        tokens = suffix.split()
        if tokens[:1] == ["xem"]:
            tokens = tokens[1:]
        if tokens[:2] != ["thuyet", "minh"]:
            return False
        reference = tokens[2:]
        if reference[:1] == ["so"]:
            reference = reference[1:]
        if not reference:
            return False
        groups = []
        current = []
        for token in reference:
            if token == "va":
                if not current:
                    return False
                groups.append(current)
                current = []
            else:
                current.append(token)
        if not current:
            return False
        groups.append(current)
        return bool(
            1 <= len(groups) <= 3
            and all(
                1 <= len(group) <= 3
                and group[0].isdigit()
                and all(
                    token.isdigit()
                    or re.fullmatch(r"[a-z]", token)
                    or re.fullmatch(r"[ivxlcdm]+", token)
                    for token in group[1:]
                )
                for group in groups
            )
        )

    return bool(suffixes) and all(
        suffix
        and (
            all(token in allowed_suffix_tokens for token in suffix.split())
            or is_note_reference_suffix(suffix)
        )
        for suffix in suffixes
    )


def _reference_row_modes(row, *, topology, aliases_by_role, fallback_within_role=None):
    """Pre-provider row policy; EXACT uses the embedded old predicate.

    Declared equivalences are disabled in this differential. Nonexact and scope
    helpers are unchanged by this proposal and are used without a provider.
    """
    def self_contained(within, kind):
        if not kind.startswith("EXACT_NORMALIZED"):
            return False
        label = subject._normalized(row.get("label_exact"))
        return any(
            len(alias.split()) >= 3 and (label == alias or label.startswith(alias + " "))
            for raw in aliases_by_role[within]
            if (alias := subject._normalized(raw))
        )

    explicit = subject._path_has_role(
        row.get("hierarchy_path_exact"), aliases=topology["parent"]["aliases"],
        label_exact=row.get("label_exact"),
    ) or any(
        child["role_kind"] == "STRUCTURAL_GROUP" and subject._path_has_role(
            row.get("hierarchy_path_exact"), aliases=aliases_by_role[child["role"]],
            label_exact=row.get("label_exact"),
        ) for child in topology["children"]
    )
    scoped, unscoped = defaultdict(list), defaultdict(list)
    for child in topology["children"]:
        for matcher in child["matchers"]:
            if matcher.get("match_mode", "EXACT_NORMALIZED") == "EXACT_NORMALIZED":
                aliases = [subject._normalized(alias) for alias in matcher["aliases"]]
                kind = "EXACT_NORMALIZED" if any(
                    _old_matches(row.get("label_exact"), alias) for alias in aliases
                ) else None
            else:
                kind = subject._matcher_match_kind(row.get("label_exact"), matcher)
            if kind is None:
                continue
            role, within = child["role"], matcher["within_role"]
            if within is None:
                unscoped[role].append(kind)
            elif ((within == fallback_within_role and not explicit)
                  or subject._path_has_role(
                      row.get("hierarchy_path_exact"), aliases=aliases_by_role[within],
                      label_exact=row.get("label_exact"),
                  ) or self_contained(within, kind)):
                scoped[role].append(kind)
    selected = scoped or unscoped
    matches = sorted(selected)
    kinds = {role: next(c["role_kind"] for c in topology["children"] if c["role"] == role)
             for role in matches}
    if len(matches) > 1 and set(kinds.values()) != {"STRUCTURAL_GROUP", "ADDITIVE_CHILD"}:
        raise subject._error("Gemini JSON hierarchy row matches multiple incompatible roles")
    rank = {"CONTAINS_NORMALIZED_PHRASE": 1, "CONTAINS_ORDERED_NORMALIZED_PHRASES": 2,
            "EXACT_NORMALIZED": 3,
            "EXACT_NORMALIZED_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL": 2,
            "EXACT_NORMALIZED_SINGLE_MEMBER_ABBREVIATION_EQUIVALENCE": 2,
            "EXACT_NORMALIZED_WITH_TRAILING_ORGANIZATION_QUALIFIER": 2}
    return {role: max(selected[role], key=lambda kind: rank[kind]) for role in matches}


def _single_role(matchers):
    return {"topology": {"parent": {"aliases": ["Printed root owner"]}, "children": [
        {"role": "LINE", "role_kind": "ADDITIVE_CHILD", "matchers": [
            {"within_role": None, **matcher} for matcher in matchers
        ]},
    ]}, "aliases_by_role": {"LINE": ["Cost"]}}


def _row_outcome(operation, row, arguments):
    try:
        return "return", operation(row, **arguments)
    except (ValueError, KeyError, TypeError) as error:
        return "error", type(error), str(error)


class ImmutableMatchFormsDifferentialTests(unittest.TestCase):
    def assert_same(self, value, alias):
        expected = _old_matches(value, alias)
        actual = subject._matches(value, alias)
        self.assertIs(type(actual), bool)
        self.assertIs(actual, expected)
        forms = subject._match_value_forms_v1(value)
        self.assertIs(type(forms), frozenset)
        self.assertIs(subject._matches_prepared_forms_v1(forms, alias), expected)

    def test_adversarial_predicate_vectors(self):
        alias = "Chi phí hoạt động"
        positive = [
            alias, "II. " + alias, "II 3 " + alias, "Trong đó: " + alias,
            "Bao gồm " + alias, alias + " 1 IV",
            alias + " (xem thuyết minh số 12(a) và 13)",
            alias + " thuyết minh 12 a và 13 ii và 14",
            unicodedata.normalize("NFD", alias), alias.upper(),
        ]
        negative = [
            "Không phải " + alias, alias + " khác", alias + " 6",
            alias + " VI", alias + " thuyết minh", alias + " thuyết minh và 12",
            alias + " thuyết minh 12 và 13 và 14 và 15",
            alias + " thuyết minh 12 và", alias + " thuyết minh a",
            "Trong đó bao gồm " + alias, alias + " (kiểm toán viên điều chỉnh)",
        ]
        for value in positive:
            with self.subTest(value=value, expected=True):
                self.assertTrue(_old_matches(value, alias))
                self.assert_same(value, alias)
        for value in negative:
            with self.subTest(value=value, expected=False):
                self.assertFalse(_old_matches(value, alias))
                self.assert_same(value, alias)

    def test_literal_backslash_n_keeps_both_original_interpretations(self):
        raw = "Tiền gửi trong\\nước"
        for alias in ("Tiền gửi trong nước", "Tiền gửi trong ước"):
            with self.subTest(alias=alias):
                self.assertTrue(_old_matches(raw, alias))
                self.assert_same(raw, alias)
        actual_newline = "Tiền gửi trong\nước"
        self.assertFalse(_old_matches(actual_newline, "Tiền gửi trong nước"))
        self.assert_same(actual_newline, "Tiền gửi trong nước")

    def test_direct_wrapper_retains_empty_and_hashable_non_string_behavior(self):
        for value in (None, "", False, 0, 1.5, (), ("a",)):
            for alias in ("", None, "Chi phí"):
                with self.subTest(value=value, alias=alias):
                    self.assert_same(value, alias)

    def test_direct_wrapper_retains_unhashable_input_errors(self):
        for value, alias in (([], "chi phi"), ({}, "chi phi"), ("chi phi", [])):
            with self.subTest(value=value, alias=alias):
                with self.assertRaises(TypeError):
                    _old_matches(value, alias)
                with self.assertRaises(TypeError):
                    subject._matches(value, alias)

    def test_prepared_forms_are_detached_immutable_and_not_global_memoized(self):
        first = subject._match_value_forms_v1("II. Chi phí")
        with self.assertRaises(AttributeError):
            first.add("foreign")
        second = subject._match_value_forms_v1("II. Chi phí")
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertNotEqual(first, subject._match_value_forms_v1("II. Thu nhập"))

    def test_empty_alias_loop_keeps_old_no_value_evaluation_behavior(self):
        for value in ([], {}, None, "Chi phí"):
            with self.subTest(value=value):
                self.assertIsNone(subject._matcher_match_kind(
                    value, {"aliases": [], "match_mode": "EXACT_NORMALIZED"},
                ))

    def test_match_kind_precedence_and_equivalence_switches(self):
        cases = [
            ("Chi phí (NHNN)", {"aliases": ["Chi phí", "Chi phí (NHNN)"],
                               "allow_decorative_parenthetical_removal": True},
             True, "EXACT_NORMALIZED"),
            ("Chi phí (ABC)", {"aliases": ["Chi phí"], "allow_decorative_parenthetical_removal": True},
             True, "EXACT_NORMALIZED_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"),
            ("Chi phí (ABC)", {"aliases": ["Chi phí"], "allow_decorative_parenthetical_removal": True},
             False, None),
            ("Công ty 1TV", {"aliases": ["Công ty MTV"], "normalize_single_member_abbreviations": True},
             True, "EXACT_NORMALIZED_SINGLE_MEMBER_ABBREVIATION_EQUIVALENCE"),
            ("Công ty 1TV", {"aliases": ["Công ty MTV"], "normalize_single_member_abbreviations": True},
             False, None),
            ("Chi phí tại Hà Nội", {"aliases": ["Chi phí"], "allow_trailing_organization_qualifier": True},
             True, "EXACT_NORMALIZED_WITH_TRAILING_ORGANIZATION_QUALIFIER"),
            ("Chi phí tại Hà Nội", {"aliases": ["Chi phí"], "allow_trailing_organization_qualifier": True},
             False, None),
        ]
        for value, spec, enabled, expected in cases:
            with self.subTest(value=value, spec=spec, enabled=enabled):
                before = copy.deepcopy(spec)
                self.assertEqual(subject._matcher_match_kind(
                    value, spec, enable_declared_equivalences=enabled,
                ), expected)
                self.assertEqual(spec, before)

    def test_non_exact_modes_and_invalid_mode_remain_separate(self):
        self.assertEqual(subject._matcher_match_kind(
            "Khoản chi phí quản lý", {"aliases": ["chi phí"], "match_mode": "CONTAINS_NORMALIZED_PHRASE"},
        ), "CONTAINS_NORMALIZED_PHRASE")
        self.assertEqual(subject._matcher_match_kind(
            "Chi phí quản lý", {"aliases": ["chi", "quản lý"], "match_mode": "CONTAINS_ORDERED_NORMALIZED_PHRASES"},
        ), "CONTAINS_ORDERED_NORMALIZED_PHRASES")
        self.assertIsNone(subject._matcher_match_kind(
            "Quản lý chi", {"aliases": ["chi", "quản lý"], "match_mode": "CONTAINS_ORDERED_NORMALIZED_PHRASES"},
        ))
        with self.assertRaises(ValueError):
            subject._matcher_match_kind("Chi phí", {"aliases": ["chi phí"], "match_mode": "UNSUPPORTED"})

    def test_actual_f36_f37_f39_matcher_configs_differential(self):
        root = Path(subject.__file__).resolve().parents[3]
        paths = (
            "tm-operating-expense-topology-v1.json",
            "tm-credit-risk-provision-expense-topology-v1.json",
            "tm-income-tax-topology-v1.json",
        )
        matcher_count = alias_count = 0
        for name in paths:
            raw = json.loads((root / "config/families" / name).read_bytes())
            compiled = compile_accounting_family_topology_spec_v1(raw)
            for child in compiled["children"]:
                for matcher in child["matchers"]:
                    if matcher.get("match_mode", "EXACT_NORMALIZED") != "EXACT_NORMALIZED":
                        continue
                    matcher_count += 1
                    before = copy.deepcopy(matcher)
                    for alias in matcher["aliases"]:
                        alias_count += 1
                        values = (
                            alias, "IV. " + alias, "Trong đó: " + alias,
                            alias + " (xem thuyết minh số 12a và 13)",
                            alias + " ngoài phạm vi", "không " + alias,
                        )
                        for value in values:
                            with self.subTest(config=name, role=child["role"], alias=alias, value=value):
                                for candidate_alias in matcher["aliases"]:
                                    self.assert_same(value, candidate_alias)
                                expected = "EXACT_NORMALIZED" if any(
                                    _old_matches(value, candidate_alias)
                                    for candidate_alias in matcher["aliases"]
                                ) else None
                                self.assertEqual(subject._matcher_match_kind(
                                    value, matcher, enable_declared_equivalences=False,
                                ), expected)
                    self.assertEqual(matcher, before)
        self.assertGreater(matcher_count, 0)
        self.assertGreater(alias_count, matcher_count)

    def test_row_reuses_successful_forms_once_across_exact_matchers_only_per_invocation(self):
        arguments = _single_role([{"aliases": []}, {"aliases": ["Unrelated"]},
                                  {"aliases": ["Cost"]}, {"aliases": ["Other"]}])
        row = {"label_exact": "Cost", "hierarchy_path_exact": None}
        with patch.object(subject, "_match_value_forms_v1", wraps=subject._match_value_forms_v1) as prepare:
            self.assertEqual(subject._row_role_match_modes(row, **arguments), {"LINE": "EXACT_NORMALIZED"})
            self.assertEqual([call.args[0] for call in prepare.call_args_list], ["Cost"])
            row["label_exact"] = "Other"  # same object, fresh invocation: never an identity/global cache
            self.assertEqual(subject._row_role_match_modes(row, **arguments), {"LINE": "EXACT_NORMALIZED"})
            self.assertEqual([call.args[0] for call in prepare.call_args_list], ["Cost", "Other"])

    def test_row_empty_alias_and_nonexact_paths_never_call_value_forms_provider(self):
        empty = _single_role([{"aliases": []}])
        with patch.object(subject, "_match_value_forms_v1", wraps=subject._match_value_forms_v1) as prepare:
            for value in ([], {}, None, "Cost"):
                with self.subTest(value=value):
                    self.assertEqual(subject._row_role_match_modes(
                        {"label_exact": value, "hierarchy_path_exact": None}, **empty,
                    ), {})
            nonexact = _single_role([
                {"aliases": [], "match_mode": "EXACT_NORMALIZED"},
                {"aliases": ["cost"], "match_mode": "CONTAINS_NORMALIZED_PHRASE"},
            ])
            self.assertEqual(subject._row_role_match_modes(
                {"label_exact": "Cost detail", "hierarchy_path_exact": None}, **nonexact,
            ), {"LINE": "CONTAINS_NORMALIZED_PHRASE"})
            self.assertEqual(prepare.call_count, 0)

    def test_row_alias_validation_precedes_lazy_label_preparation_and_keeps_error_order(self):
        arguments = _single_role([{"aliases": [{}]}])
        row = {"label_exact": [], "hierarchy_path_exact": None}
        with patch.object(subject, "_match_value_forms_v1", wraps=subject._match_value_forms_v1) as prepare:
            with self.assertRaisesRegex(TypeError, "dict"):
                _reference_row_modes(row, **arguments)
            with self.assertRaisesRegex(TypeError, "dict"):
                subject._row_role_match_modes(row, **arguments)
            self.assertEqual(prepare.call_count, 0)  # invalid alias fails before the invalid list label
        events = []
        real_normalized, real_prepare = subject._normalized, subject._match_value_forms_v1

        def normalize(value):
            events.append(("normalized", repr(value)))
            return real_normalized(value)

        def prepare(value):
            events.append(("prepare", repr(value)))
            return real_prepare(value)

        with patch.object(subject, "_normalized", side_effect=normalize), patch.object(
            subject, "_match_value_forms_v1", side_effect=prepare,
        ):
            with self.assertRaisesRegex(TypeError, "list"):
                subject._row_role_match_modes(row, **_single_role([{"aliases": ["Cost"]}]))
        self.assertEqual(events, [("normalized", repr("Cost")), ("prepare", "[]"), ("normalized", "[]")])

    def test_row_scope_errors_still_happen_before_alias_or_label_form_work(self):
        row = {"label_exact": [], "hierarchy_path_exact": None}
        arguments = _single_role([{"aliases": [{}]}])
        del arguments["topology"]["parent"]
        with patch.object(subject, "_match_value_forms_v1", wraps=subject._match_value_forms_v1) as prepare:
            for operation in (_reference_row_modes, subject._row_role_match_modes):
                with self.subTest(operation=operation.__name__):
                    with self.assertRaisesRegex(KeyError, "parent"):
                        operation(row, **arguments)
            self.assertEqual(prepare.call_count, 0)

    def test_row_decorative_forms_remain_fresh_and_secondary_to_exact(self):
        matcher = {"aliases": ["Cost"], "allow_decorative_parenthetical_removal": True}
        arguments = _single_role([matcher, copy.deepcopy(matcher)])
        row = {"label_exact": "Cost (ABC)", "hierarchy_path_exact": None}
        with patch.object(subject, "_match_value_forms_v1", wraps=subject._match_value_forms_v1) as prepare:
            self.assertEqual(subject._row_role_match_modes(
                row, **arguments, enable_declared_equivalences=True,
            ), {"LINE": "EXACT_NORMALIZED_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"})
            self.assertEqual([call.args[0] for call in prepare.call_args_list], ["Cost (ABC)", "Cost  ", "Cost  "])
        arguments["topology"]["children"][0]["matchers"].append({"within_role": None, "aliases": ["Cost (ABC)"]})
        self.assertEqual(subject._row_role_match_modes(
            row, **arguments, enable_declared_equivalences=True,
        ), {"LINE": "EXACT_NORMALIZED"})

    def test_compiled_f36_f37_f39_row_role_outputs_match_old_exact_predicate(self):
        root = Path(subject.__file__).resolve().parents[3]
        checks = matched = 0
        for name in ("tm-operating-expense-topology-v1.json", "tm-credit-risk-provision-expense-topology-v1.json",
                     "tm-income-tax-topology-v1.json"):
            topology = compile_accounting_family_topology_spec_v1(json.loads(
                (root / "config/families" / name).read_bytes(),
            ))
            aliases = {child["role"]: sorted({alias for matcher in child["matchers"] for alias in matcher["aliases"]})
                       for child in topology["children"]}
            for child in topology["children"]:
                for matcher in child["matchers"]:
                    if not matcher["aliases"]:
                        continue
                    label, within = matcher["aliases"][0], matcher["within_role"]
                    owner = aliases[within][0] if within is not None else topology["parent"]["aliases"][0]
                    for value in (label, "Trong đó: " + label, label + " outside"):
                        for path, fallback in (([], None), ([], within), ([owner, value], within)):
                            row = {"label_exact": value, "hierarchy_path_exact": path}
                            arguments = {"topology": topology, "aliases_by_role": aliases, "fallback_within_role": fallback}

                            with self.subTest(config=name, role=child["role"], value=value, path=path, fallback=fallback):
                                before = copy.deepcopy(row)
                                expected = _row_outcome(_reference_row_modes, row, arguments)
                                actual = _row_outcome(subject._row_role_match_modes, row, arguments)
                                self.assertEqual(actual, expected)
                                self.assertEqual(row, before)
                                checks += 1
                                matched += bool(actual[0] == "return" and actual[1])
        self.assertGreater(checks, 0)
        self.assertGreater(matched, 0)


if __name__ == "__main__":
    unittest.main()
