from __future__ import annotations

import pytest

from bctc_ai.core.contracts import (
    BoundingBox,
    EvidenceGate,
    EvidenceStatus,
    PipelineRecord,
    Provenance,
)


def test_high_confidence_requires_cell_provenance_and_all_gates():
    record = PipelineRecord(
        document_id="sha256:abc",
        statement_type="CDKT",
        raw_value="1",
        normalized_value="1",
        status=EvidenceStatus.AUTO_VERIFIED_HIGH,
    )
    with pytest.raises(ValueError, match="cell provenance"):
        record.validate()

    record.provenance = Provenance(
        document_hash="abc",
        page=1,
        label_bbox=BoundingBox(0, 0, 1, 1),
        value_bbox=BoundingBox(2, 0, 3, 1),
    )
    with pytest.raises(ValueError, match="evidence gate"):
        record.validate()

    record.acceptance_gate = EvidenceGate(
        **{key: True for key in EvidenceGate.__dataclass_fields__}
    )
    record.validate()


def test_invalid_bbox_is_rejected():
    with pytest.raises(ValueError):
        BoundingBox(10, 0, 2, 4)
