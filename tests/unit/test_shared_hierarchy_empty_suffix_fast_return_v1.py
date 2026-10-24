"""UNRUN differential controls for the isolated empty-suffix early-return draft.

The literal reference is the aeb353f5 prepared predicate (hierarchy SHA bed0757).
Only its alias normalizer is qualified through subject; no new predicate calls.
These lexical/unit controls grant no source, financial or measured-speed claim.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from bctc_ai.evaluation import gemini_json_hierarchical_accounting_family_v1 as subject
from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)


def _old_prepared(forms: frozenset[str], alias: str) -> bool:
    """Apply the unchanged alias/suffix predicate to immutable value forms."""

    alias = subject._normalized(alias)
    if alias in forms:
        return True
    suffixes = {form.removeprefix(alias).strip() for form in forms if form.startswith(alias + " ")}
    allowed_suffix_tokens = {
        "1",
        "2",
        "3",
        "4",
        "5",
        "i",
        "ii",
        "iii",
        "iv",
        "v",
    }

    def is_note_reference_suffix(suffix: str) -> bool:
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


@pytest.mark.parametrize(
    ("forms", "alias", "expected"),
    [
        ((), "chi phi", False),
        (("unrelated",), "chi phi", False),
        (("unrelated", "another"), "chi phi", False),
        (("chi phix",), "chi phi", False),
        (("prefix chi phi",), "chi phi", False),
        (("chi phi",), "Chi phí", True),
        (("chi phi", "chi phi invalid"), "chi phi", True),
        (("",), "", True),
        (("unrelated",), "", False),
        (("chi phi ",), "chi phi", False),
        (("chi phi 1",), "chi phi", True),
        (("chi phi i", "chi phi v"), "chi phi", True),
        (("chi phi 1 2",), "chi phi", True),
        (("chi phi 6",), "chi phi", False),
        (("chi phi 1", "chi phi unrelated"), "chi phi", False),
        (("chi phi thuyet minh 12",), "chi phi", True),
        (("chi phi xem thuyet minh so 12 a",), "chi phi", True),
        (("chi phi thuyet minh 12 ii va 13",), "chi phi", True),
        (("chi phi thuyet minh 12 va 13 va 14",), "chi phi", True),
        (("chi phi thuyet minh 12 va 13 va 14 va 15",), "chi phi", False),
        (("chi phi thuyet minh",), "chi phi", False),
        (("chi phi thuyet minh a",), "chi phi", False),
        (("chi phi thuyet minh va 12",), "chi phi", False),
        (("chi phi thuyet minh 12 va",), "chi phi", False),
        (("chi phi thuyet minh 12 va va 13",), "chi phi", False),
    ],
)
def test_empty_suffix_fast_return_matches_literal_reference(forms, alias, expected):
    prepared = frozenset(forms)
    assert _old_prepared(prepared, alias) is expected
    assert subject._matches_prepared_forms_v1(prepared, alias) is expected


def _outcome(function, *arguments):
    try:
        return ("RETURN", type(value := function(*arguments)), value)
    except Exception as error:
        return ("RAISE", type(error), str(error))


@pytest.mark.parametrize(
    ("forms", "alias"),
    [
        (None, "chi phi"),
        (frozenset(), []),
        (frozenset(), {}),
        (frozenset(), set()),
        (None, []),
        (frozenset({1}), "chi phi"),
        (frozenset({"unrelated"}), 42),
    ],
)
def test_preexisting_type_and_alias_error_outcomes_are_unchanged(forms, alias):
    assert _outcome(subject._matches_prepared_forms_v1, forms, alias) == _outcome(
        _old_prepared, forms, alias,
    )


def test_alias_validation_membership_iteration_order_is_unchanged():
    original_normalized = subject._normalized
    observed = []
    for predicate in (_old_prepared, subject._matches_prepared_forms_v1):
        events = []

        def normalize(alias, _events=events):
            _events.append(("normalize", alias))
            return original_normalized(alias)

        class Forms:
            def __init__(self, event_log):
                self.event_log = event_log

            def __contains__(self, alias):
                self.event_log.append(("contains", alias))
                return False

            def __iter__(self):
                self.event_log.append(("iterate",))
                return iter(("unrelated",))

        with patch.object(subject, "_normalized", normalize):
            assert predicate(Forms(events), "Chi phí") is False
        observed.append(events)
    assert observed[0] == observed[1] == [
        ("normalize", "Chi phí"), ("contains", "chi phi"), ("iterate",),
    ]


def test_public_wrapper_remains_equivalent_on_prepared_value_variants():
    for value in ("Chi phí", "IV. Chi phí", "Trong đó: Chi phí",
                  "Chi phí (xem thuyết minh 12a)", "Chi phí ngoài phạm vi",
                  "không liên quan", "", None, 42):
        for alias in ("chi phí", "không liên quan", "", None):
            forms = subject._match_value_forms_v1(value)
            assert _outcome(subject._matches, value, alias) == _outcome(
                _old_prepared, forms, alias,
            )


def test_empty_suffix_return_does_not_mutate_or_reuse_caller_forms():
    forms = frozenset({"unrelated", "another"})
    before = copy.deepcopy(forms)
    for alias in ("chi phi", "unrelated", "chi phi", "another"):
        assert subject._matches_prepared_forms_v1(forms, alias) is _old_prepared(forms, alias)
    assert forms == before


@pytest.mark.parametrize(
    "config_name",
    [
        "tm-operating-expense-topology-v1.json",
        "tm-credit-risk-provision-expense-topology-v1.json",
        "tm-income-tax-topology-v1.json",
    ],
)
def test_actual_compiled_matcher_aliases_match_literal_reference(config_name):
    root = Path(subject.__file__).resolve().parents[3]
    raw = json.loads((root / "config/families" / config_name).read_bytes())
    topology = compile_accounting_family_topology_spec_v1(raw)
    before = copy.deepcopy(topology)
    aliases = [
        alias
        for child in topology["children"]
        for matcher in child["matchers"]
        if matcher.get("match_mode", "EXACT_NORMALIZED") == "EXACT_NORMALIZED"
        for alias in matcher["aliases"]
    ]
    assert aliases
    for alias in aliases:
        for value in (alias, "IV. " + alias, "Trong đó: " + alias,
                      alias + " (xem thuyết minh số 12a và 13)",
                      alias + " ngoài phạm vi", "không " + alias):
            prepared = subject._match_value_forms_v1(value)
            assert subject._matches_prepared_forms_v1(prepared, alias) is _old_prepared(prepared, alias)
    assert topology == before
