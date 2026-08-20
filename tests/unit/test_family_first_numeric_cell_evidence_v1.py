from __future__ import annotations

import copy
import io

import pytest
from PIL import Image

from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    FamilyFirstNumericCellEvidenceV1Error,
    build_family_first_ppocrv6_numeric_cell_evidence_v1,
    parse_visible_financial_numeric_token_v1,
    validate_family_first_ppocrv6_numeric_cell_evidence_replay_v1,
)


def _crop(color: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (80, 24), color=color).save(stream, format="PNG")
    return stream.getvalue()


def _provider(text: str = "603.040.884") -> dict[str, object]:
    return {
        "input_path": None,
        "page_index": None,
        "rec_score": 0.999,
        "rec_text": text,
    }


@pytest.mark.parametrize(
    ("token", "classification", "coefficient", "scale", "separator"),
    [
        ("603.040.884", "SIGNED_NUMBER", 603_040_884, 0, "GROUPED_INTEGER_POINT"),
        ("(14.765)", "SIGNED_NUMBER", -14_765, 0, "GROUPED_INTEGER_POINT"),
        ("26.335,00", "SIGNED_NUMBER", 2_633_500, 2, "GROUPED_POINT_DECIMAL_COMMA"),
        ("165,68", "SIGNED_NUMBER", 16_568, 2, "DECIMAL_COMMA"),
        ("1,234.50", "SIGNED_NUMBER", 123_450, 2, "GROUPED_COMMA_DECIMAL_POINT"),
        ("12,5%", "SIGNED_NUMBER", 125, 1, "DECIMAL_COMMA"),
        ("0", "SIGNED_NUMBER", 0, 0, "NONE"),
        ("-", "DASH_ZERO", 0, 0, "DASH"),
        ("–", "DASH_ZERO", 0, 0, "DASH"),
        ("", "BLANK_UNRESOLVED", None, None, None),
        ("97.043.85", "UNRESOLVED_TOKEN", None, None, None),
        ("1.234x", "UNRESOLVED_TOKEN", None, None, None),
    ],
)
def test_conservative_numeric_token_grammar(
    token: str,
    classification: str,
    coefficient: int | None,
    scale: int | None,
    separator: str | None,
) -> None:
    parsed = parse_visible_financial_numeric_token_v1(token)

    assert parsed["classification"] == classification
    assert parsed["coefficient"] == coefficient
    assert parsed["scale"] == scale
    assert parsed["separator_interpretation"] == separator


def test_dash_is_zero_but_blank_and_malformed_digits_are_not() -> None:
    dash = parse_visible_financial_numeric_token_v1("  —  ")
    blank = parse_visible_financial_numeric_token_v1("   ")
    dropped_digit = parse_visible_financial_numeric_token_v1("97.043.85")

    assert dash["classification"] == "DASH_ZERO"
    assert dash["coefficient"] == 0
    assert blank["classification"] == "BLANK_UNRESOLVED"
    assert blank["coefficient"] is None
    assert dropped_digit["classification"] == "UNRESOLVED_TOKEN"
    assert dropped_digit["coefficient"] is None


def test_crop_and_raw_recognition_are_hash_bound_and_replay_exactly() -> None:
    crop = _crop()
    provider = _provider()
    evidence = build_family_first_ppocrv6_numeric_cell_evidence_v1(
        crop_png_bytes=crop,
        recognizer_payload=provider,
    )

    assert evidence["parsed_token"]["coefficient"] == 603_040_884
    assert evidence["provider_recognition"] == {"raw_text": "603.040.884", "score": 0.999}
    assert evidence["authority"]["numeric_evidence_only"] is True
    assert evidence["authority"]["accounting_closure_used_to_change_digits"] is False
    assert (
        validate_family_first_ppocrv6_numeric_cell_evidence_replay_v1(
            evidence,
            crop_png_bytes=crop,
            recognizer_payload=provider,
        )
        == evidence
    )

    with pytest.raises(FamilyFirstNumericCellEvidenceV1Error, match="replay exactly"):
        validate_family_first_ppocrv6_numeric_cell_evidence_replay_v1(
            evidence,
            crop_png_bytes=_crop((250, 250, 250)),
            recognizer_payload=provider,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update({"extra": True}),
        lambda value: value.__setitem__("page_index", 0),
        lambda value: value.__setitem__("rec_score", True),
        lambda value: value.__setitem__("rec_score", float("nan")),
        lambda value: value.__setitem__("rec_text", 7),
    ],
)
def test_provider_schema_and_exact_scalar_types_fail_closed(mutation) -> None:
    provider = copy.deepcopy(_provider())
    mutation(provider)

    with pytest.raises(FamilyFirstNumericCellEvidenceV1Error):
        build_family_first_ppocrv6_numeric_cell_evidence_v1(
            crop_png_bytes=_crop(),
            recognizer_payload=provider,
        )


def test_coordinated_record_rehash_cannot_pass_live_replay() -> None:
    crop = _crop()
    provider = _provider()
    build_family_first_ppocrv6_numeric_cell_evidence_v1(
        crop_png_bytes=crop,
        recognizer_payload=provider,
    )
    changed_provider = _provider("603.040.889")
    changed = build_family_first_ppocrv6_numeric_cell_evidence_v1(
        crop_png_bytes=crop,
        recognizer_payload=changed_provider,
    )

    with pytest.raises(FamilyFirstNumericCellEvidenceV1Error, match="replay exactly"):
        validate_family_first_ppocrv6_numeric_cell_evidence_replay_v1(
            changed,
            crop_png_bytes=crop,
            recognizer_payload=provider,
        )
