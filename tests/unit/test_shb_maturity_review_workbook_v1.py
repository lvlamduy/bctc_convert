from __future__ import annotations

import hashlib

import pytest

from bctc_ai.export.shb_maturity_review_workbook_v1 import (
    ARTIFACT_ROLE,
    CLAIM_BOUNDARY,
    E0042_RELATIVE_PATH,
    E0042_SHA256,
    E0042_SIZE_BYTES,
    E0042_VERIFICATION_ID,
    ShbMaturityReviewWorkbookV1Error,
    _validate_verification,
)


def test_exact_corrected_e0042_bytes_are_the_only_numeric_verification_input(
    project_root,
) -> None:
    payload = (project_root / E0042_RELATIVE_PATH).read_bytes()

    assert (len(payload), hashlib.sha256(payload).hexdigest()) == (
        E0042_SIZE_BYTES,
        E0042_SHA256,
    )
    verification = _validate_verification(payload)
    assert verification["verification_id"] == E0042_VERIFICATION_ID
    assert verification["metrics"]["exact_eight_cell_agreement"] is True
    assert verification["metrics"]["reader_score_decision_use_count"] == 0

    tampered = payload.replace(b"225.268.906", b"225.268.907", 1)
    with pytest.raises(ShbMaturityReviewWorkbookV1Error, match="byte identity"):
        _validate_verification(tampered)


def test_public_claim_is_explicitly_review_only_and_denies_export_authority() -> None:
    assert ARTIFACT_ROLE == "REVIEW_ONLY_NON_CANONICAL_NON_EXPORT_AUTHORITY"
    assert "REVIEW_VIEW_ONLY" in CLAIM_BOUNDARY
    assert "NO_ACCEPTED_SCHEMA_MAPPING" in CLAIM_BOUNDARY
    assert CLAIM_BOUNDARY.endswith("NO_ACCEPTED_SCHEMA_MAPPING") is False
    assert "EXPORT_AUTHORITY" in CLAIM_BOUNDARY
