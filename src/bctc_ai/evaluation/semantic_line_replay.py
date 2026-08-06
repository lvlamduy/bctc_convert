from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bctc_ai.document_phase.statement_locator import OCRPage
from bctc_ai.ocr.semantic_line_fusion import SemanticFieldRole, SemanticLineProposal


class SemanticLineReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenSemanticProposalBuild:
    document: str
    reader: str
    proposals: tuple[SemanticLineProposal, ...]
    skipped_sample_ids: tuple[str, ...]
    expected_or_reference_fields_read: bool
    ppocr_source_text_and_bbox_verified: bool


_CATEGORY_ROLES = {
    "TITLE": SemanticFieldRole.TITLE,
    "OFF_BALANCE_TITLE": SemanticFieldRole.SCOPE_WORDING,
    "SECTION": SemanticFieldRole.SECTION,
    "METHOD": SemanticFieldRole.METHOD,
    "LABEL": SemanticFieldRole.LABEL,
    "DUPLICATE_LABEL": SemanticFieldRole.LABEL,
    "OFF_BALANCE_LABEL": SemanticFieldRole.SCOPE_WORDING,
    "NOTES_ANCHOR": SemanticFieldRole.LABEL,
}


def build_frozen_semantic_proposals(
    *,
    crop_manifest: dict[str, Any],
    inference_result: dict[str, Any],
    geometry_pages: tuple[OCRPage, ...],
    document: str,
    reader: str,
) -> FrozenSemanticProposalBuild:
    if (
        crop_manifest.get("format_version") != 1
        or crop_manifest.get("experiment_id") != "E-0024"
        or crop_manifest.get("state") != "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE"
        or crop_manifest.get("dataset_role") != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
    ):
        raise SemanticLineReplayError("frozen crop-manifest identity or role drifted")
    if (
        inference_result.get("format_version") != 1
        or inference_result.get("experiment_id") not in {"E-0025", "E-0026"}
        or inference_result.get("state")
        != "REFERENCE_BLIND_DEEPSEEK_BOUNDED_LINE_INFERENCE_COMPLETE"
        or inference_result.get("dataset_role") != crop_manifest.get("dataset_role")
        or inference_result.get("reference_text_available_to_reader") is not False
    ):
        raise SemanticLineReplayError("semantic inference identity or reference policy drifted")
    authority = inference_result.get("authority")
    if not isinstance(authority, dict) or not authority or any(
        bool(value) for value in authority.values()
    ):
        raise SemanticLineReplayError("semantic inference grants forbidden authority")
    raw_crops = crop_manifest.get("samples")
    raw_predictions = inference_result.get("samples")
    if (
        not isinstance(raw_crops, list)
        or not isinstance(raw_predictions, list)
        or len(raw_crops) != crop_manifest.get("sample_count")
        or len(raw_predictions) != inference_result.get("sample_count")
        or len(raw_crops) != len(raw_predictions)
    ):
        raise SemanticLineReplayError("semantic crop/prediction denominator drifted")
    predictions: dict[str, dict[str, Any]] = {}
    for raw in raw_predictions:
        if not isinstance(raw, dict) or not isinstance(raw.get("sample_id"), str):
            raise SemanticLineReplayError("semantic prediction record is invalid")
        sample_id = raw["sample_id"]
        if not sample_id or sample_id in predictions:
            raise SemanticLineReplayError("semantic prediction IDs are empty or duplicated")
        predictions[sample_id] = raw

    pages = {page.page: page for page in geometry_pages}
    if len(pages) != len(geometry_pages):
        raise SemanticLineReplayError("geometry page identities are duplicated")
    proposals = []
    skipped = []
    seen_crop_ids: set[str] = set()
    for crop in raw_crops:
        if not isinstance(crop, dict) or not isinstance(crop.get("sample_id"), str):
            raise SemanticLineReplayError("frozen crop record is invalid")
        sample_id = crop["sample_id"]
        if not sample_id or sample_id in seen_crop_ids or sample_id not in predictions:
            raise SemanticLineReplayError("frozen crop IDs are empty, duplicated or unpaired")
        seen_crop_ids.add(sample_id)
        prediction = predictions[sample_id]
        for key in ("category", "crop_path", "crop_sha256"):
            if str(prediction.get(key, "")) != str(crop.get(key, "")):
                raise SemanticLineReplayError(f"semantic crop identity drifted at {key}")
        if str(crop.get("document", "")) != document:
            continue
        category = str(crop.get("category", ""))
        role = _CATEGORY_ROLES.get(category)
        if role is None:
            raise SemanticLineReplayError(f"unrecognized semantic crop category: {category}")
        if prediction.get("status") != "PARSED_SEMANTIC_PROPOSAL_ONLY":
            skipped.append(sample_id)
            continue
        page_number = crop.get("page")
        line_index = crop.get("ppocr_result_index")
        if (
            isinstance(page_number, bool)
            or not isinstance(page_number, int)
            or isinstance(line_index, bool)
            or not isinstance(line_index, int)
            or page_number not in pages
            or line_index < 0
            or line_index >= len(pages[page_number].lines)
        ):
            raise SemanticLineReplayError("semantic crop source page/line binding is invalid")
        source = pages[page_number].lines[line_index]
        raw_bbox = crop.get("ppocr_bbox")
        if (
            source.text != str(crop.get("ppocr_text", ""))
            or not isinstance(raw_bbox, list)
            or len(raw_bbox) != 4
            or tuple(source.bbox) != tuple(float(value) for value in raw_bbox)
        ):
            raise SemanticLineReplayError("semantic crop PP-OCR source text/bbox drifted")
        proposals.append(
            SemanticLineProposal(
                proposal_id=sample_id,
                reader=reader,
                page=page_number,
                source_line_indices=(line_index,),
                source_texts=(source.text,),
                source_bboxes=(source.bbox,),
                field_role=role,
                raw_proposal_text=str(prediction.get("proposal_text", "")),
                crop_sha256=str(crop.get("crop_sha256", "")),
                reader_score=(
                    float(prediction["reader_score"])
                    if prediction.get("reader_score") is not None
                    else None
                ),
            )
        )
    return FrozenSemanticProposalBuild(
        document=document,
        reader=reader,
        proposals=tuple(proposals),
        skipped_sample_ids=tuple(skipped),
        expected_or_reference_fields_read=False,
        ppocr_source_text_and_bbox_verified=True,
    )


__all__ = [
    "FrozenSemanticProposalBuild",
    "SemanticLineReplayError",
    "build_frozen_semantic_proposals",
]
