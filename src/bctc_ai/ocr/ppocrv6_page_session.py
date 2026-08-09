from __future__ import annotations

import statistics
import sys
import time
from math import isfinite
from pathlib import Path
from typing import Any


class PPOCRV6PageSessionError(RuntimeError):
    """Pinned PP-OCRv6 page reading failed without a complete result."""


_PATH_KEYS = {
    "input_path",
    "img_path",
    "image_path",
    "model_dir",
    "output_path",
    "save_path",
}


def _deny_network_connections() -> None:
    def audit_hook(event: str, _arguments: tuple[Any, ...]) -> None:
        if event == "socket.connect":
            raise PPOCRV6PageSessionError(
                "network access is forbidden during sealed PP-OCRv6 inference"
            )

    sys.addaudithook(audit_hook)


def _plain_json(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return _plain_json(value.tolist())
    if isinstance(value, dict):
        return {
            str(key): _plain_json(item)
            for key, item in value.items()
            if str(key).casefold() not in _PATH_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        raise PPOCRV6PageSessionError("PP-OCRv6 emitted a non-finite JSON number")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise PPOCRV6PageSessionError(f"PP-OCRv6 emitted unsupported JSON type: {type(value)}")


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise PPOCRV6PageSessionError(f"{label} must be a finite non-boolean number")
    return float(value)


def _validate_point(point: Any, *, width: int, height: int, label: str) -> None:
    if not isinstance(point, list) or len(point) != 2:
        raise PPOCRV6PageSessionError(f"{label} must be an [x, y] point")
    x = _finite_number(point[0], f"{label} x")
    y = _finite_number(point[1], f"{label} y")
    if not 0 <= x <= width or not 0 <= y <= height:
        raise PPOCRV6PageSessionError(f"{label} lies outside the rendered page")


def _validate_box(box: Any, *, width: int, height: int, label: str) -> None:
    if not isinstance(box, list) or len(box) != 4:
        raise PPOCRV6PageSessionError(f"{label} must be [x0, y0, x1, y1]")
    x0, y0, x1, y1 = (_finite_number(value, label) for value in box)
    if not 0 <= x0 < x1 <= width or not 0 <= y0 < y1 <= height:
        raise PPOCRV6PageSessionError(f"{label} is invalid or outside the rendered page")


def validate_ppocrv6_payload(
    payload: dict[str, Any],
    *,
    pixel_width: int,
    pixel_height: int,
) -> dict[str, int]:
    if (
        isinstance(pixel_width, bool)
        or isinstance(pixel_height, bool)
        or not isinstance(pixel_width, int)
        or not isinstance(pixel_height, int)
        or pixel_width <= 0
        or pixel_height <= 0
    ):
        raise PPOCRV6PageSessionError("render dimensions must be positive")
    if payload.get("return_word_box") is not True:
        raise PPOCRV6PageSessionError("PP-OCRv6 result omitted required word boxes")
    line_fields = (
        "rec_texts",
        "rec_scores",
        "rec_polys",
        "rec_boxes",
        "text_word_boxes",
        "text_word",
    )
    for field in line_fields:
        if field not in payload or not isinstance(payload[field], list):
            raise PPOCRV6PageSessionError(f"PP-OCRv6 required list field is absent: {field}")
    counts = {field: len(payload[field]) for field in line_fields}
    if len(set(counts.values())) != 1:
        raise PPOCRV6PageSessionError(f"inconsistent PP-OCRv6 line axes: {counts}")
    for index in range(counts["rec_texts"]):
        if not isinstance(payload["rec_texts"][index], str):
            raise PPOCRV6PageSessionError(f"OCR line text is not a string: {index}")
        score = _finite_number(payload["rec_scores"][index], f"OCR line score {index}")
        if not 0 <= score <= 1:
            raise PPOCRV6PageSessionError(f"OCR line score is outside [0, 1]: {index}")
        polygon = payload["rec_polys"][index]
        if not isinstance(polygon, list) or len(polygon) != 4:
            raise PPOCRV6PageSessionError(f"OCR line polygon is not a quadrilateral: {index}")
        for point_index, point in enumerate(polygon):
            _validate_point(
                point,
                width=pixel_width,
                height=pixel_height,
                label=f"OCR line {index} polygon point {point_index}",
            )
        area_twice = abs(
            sum(
                _finite_number(polygon[point][0], "polygon x")
                * _finite_number(polygon[(point + 1) % 4][1], "polygon y")
                - _finite_number(polygon[(point + 1) % 4][0], "polygon x")
                * _finite_number(polygon[point][1], "polygon y")
                for point in range(4)
            )
        )
        if area_twice == 0:
            raise PPOCRV6PageSessionError(f"OCR line polygon is degenerate: {index}")
        _validate_box(
            payload["rec_boxes"][index],
            width=pixel_width,
            height=pixel_height,
            label=f"OCR line box {index}",
        )
        boxes = payload["text_word_boxes"][index]
        texts = payload["text_word"][index]
        if not isinstance(boxes, list) or not isinstance(texts, list):
            raise PPOCRV6PageSessionError(f"OCR word axes are not lists on line {index}")
        if len(boxes) != len(texts):
            raise PPOCRV6PageSessionError(f"inconsistent PP-OCRv6 word axis on line {index}")
        for word_index, (box, text) in enumerate(zip(boxes, texts, strict=True)):
            if not isinstance(text, str):
                raise PPOCRV6PageSessionError(
                    f"OCR word text is not a string on line {index}, word {word_index}"
                )
            _validate_box(
                box,
                width=pixel_width,
                height=pixel_height,
                label=f"OCR word box line {index} word {word_index}",
            )
    return {
        "line_count": counts["rec_texts"],
        "word_token_count": sum(len(line) for line in payload["text_word"]),
    }


def _bbox_polygon(box: list[int | float]) -> list[list[int | float]]:
    if len(box) != 4:
        raise PPOCRV6PageSessionError("OCR bbox must have four coordinates")
    x0, y0, x1, y1 = box
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def model_neutral_page_result(
    payload: dict[str, Any],
    *,
    coordinate_authority: dict[str, Any],
) -> dict[str, Any]:
    # Geometry conversion runs in the source-reader environment. Keeping this
    # import local lets the isolated Paddle provider import and execute the
    # pinned inference session without installing PyMuPDF into that runtime.
    from bctc_ai.rendering.page_reader import (
        public_coordinate_authority,
        transform_pixel_polygon_to_unrotated_mpt,
    )

    dimensions = coordinate_authority.get("pixel_dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != 2:
        raise PPOCRV6PageSessionError("coordinate authority lacks render dimensions")
    geometry = validate_ppocrv6_payload(
        payload,
        pixel_width=int(dimensions[0]),
        pixel_height=int(dimensions[1]),
    )
    lines: list[dict[str, Any]] = []
    all_words: list[dict[str, Any]] = []
    for index in range(geometry["line_count"]):
        raw_polygon = _plain_json(payload["rec_polys"][index])
        raw_bbox = _plain_json(payload["rec_boxes"][index])
        word_texts = payload["text_word"][index]
        word_boxes = payload["text_word_boxes"][index]
        words = []
        for raw_text, raw_word_box in zip(word_texts, word_boxes, strict=True):
            raw_word_box = _plain_json(raw_word_box)
            canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(
                _bbox_polygon(raw_word_box), coordinate_authority
            )
            canonical_bbox = [
                min(point[0] for point in canonical_polygon),
                min(point[1] for point in canonical_polygon),
                max(point[0] for point in canonical_polygon),
                max(point[1] for point in canonical_polygon),
            ]
            word = {
                "raw_text": str(raw_text),
                "score": None,
                "score_kind": "PP_OCRV6_LINE_SCORE_ONLY",
                "raw_pixel_bbox": raw_word_box,
                "canonical_bbox_mpt": canonical_bbox,
                "canonical_polygon_mpt": canonical_polygon,
            }
            words.append(word)
            all_words.append(word)
        canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(
            raw_polygon, coordinate_authority
        )
        score = float(payload["rec_scores"][index])
        lines.append(
            {
                "raw_text": str(payload["rec_texts"][index]),
                "score": score,
                "score_kind": "PP_OCRV6_LINE_RECOGNITION_SCORE",
                "raw_pixel_bbox": raw_bbox,
                "raw_pixel_polygon": raw_polygon,
                "canonical_bbox_mpt": [
                    min(point[0] for point in canonical_polygon),
                    min(point[1] for point in canonical_polygon),
                    max(point[0] for point in canonical_polygon),
                    max(point[1] for point in canonical_polygon),
                ],
                "canonical_polygon_mpt": canonical_polygon,
                "words": words,
            }
        )
    scores = [float(score) for score in payload["rec_scores"]]
    return {
        "status": "OCR_WORD_BOX_READ_COMPLETE",
        "coordinate_authority": public_coordinate_authority(coordinate_authority),
        "lines": lines,
        "words": all_words,
        "metrics": {
            **geometry,
            "minimum_line_score": min(scores) if scores else None,
            "mean_line_score": statistics.fmean(scores) if scores else None,
            "lines_below_0_8": sum(score < 0.8 for score in scores),
            "lines_below_0_9": sum(score < 0.9 for score in scores),
        },
        "source_blank_claimed": False,
    }


class PPOCRV6PageSession:
    """One pinned, role-neutral PP-OCRv6 model load reused across page reads."""

    def __init__(
        self,
        *,
        configuration_path: Path,
        detection_model_directory: Path,
        recognition_model_directory: Path,
        cpu_threads: int,
    ) -> None:
        if cpu_threads < 1:
            raise PPOCRV6PageSessionError("PP-OCRv6 CPU threads must be positive")
        for path in (
            configuration_path,
            detection_model_directory,
            recognition_model_directory,
        ):
            if not path.exists():
                raise PPOCRV6PageSessionError(f"PP-OCRv6 input is absent: {path}")
        self._configuration_path = configuration_path.resolve()
        self._detection_model_directory = detection_model_directory.resolve()
        self._recognition_model_directory = recognition_model_directory.resolve()
        self._cpu_threads = cpu_threads
        self._pipeline: Any | None = None
        self.model_load_wall_seconds: float | None = None

    def __enter__(self) -> PPOCRV6PageSession:
        _deny_network_connections()
        import paddle
        from paddleocr import PaddleOCR

        started = time.perf_counter()
        self._pipeline = PaddleOCR(
            paddlex_config=self._configuration_path.as_posix(),
            text_detection_model_dir=self._detection_model_directory.as_posix(),
            text_recognition_model_dir=self._recognition_model_directory.as_posix(),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            return_word_box=True,
            device="cpu",
            engine="paddle",
            enable_hpi=False,
            precision="fp32",
            enable_mkldnn=False,
            cpu_threads=self._cpu_threads,
        )
        self.model_load_wall_seconds = time.perf_counter() - started
        if paddle.device.get_device() != "cpu" or paddle.device.is_compiled_with_cuda():
            raise PPOCRV6PageSessionError("PP-OCRv6 runtime device drifted")
        return self

    def __exit__(self, *_arguments: Any) -> None:
        self._pipeline = None

    def predict(
        self,
        image_path: Path,
        *,
        pixel_width: int,
        pixel_height: int,
    ) -> tuple[dict[str, Any], float]:
        if self._pipeline is None:
            raise PPOCRV6PageSessionError("PP-OCRv6 session is not loaded")
        started = time.perf_counter()
        results = self._pipeline.predict(
            image_path.resolve().as_posix(),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            return_word_box=True,
        )
        elapsed = time.perf_counter() - started
        if len(results) != 1:
            raise PPOCRV6PageSessionError(
                f"expected one PP-OCRv6 page result, received {len(results)}"
            )
        payload = _plain_json(results[0].json["res"])
        if not isinstance(payload, dict):
            raise PPOCRV6PageSessionError("PP-OCRv6 page result is not an object")
        validate_ppocrv6_payload(
            payload,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
        return payload, elapsed
