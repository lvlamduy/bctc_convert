from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bctc_ai.core.contracts import BoundingBox


@dataclass(frozen=True)
class TextBox:
    raw_text: str
    normalized_text: str
    bbox: BoundingBox
    confidence: float | None
    source_image_hash: str


@dataclass
class ReadResult:
    backend: str
    text_boxes: list[TextBox] = field(default_factory=list)
    structure: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class DocumentReader(ABC):
    @abstractmethod
    def read_page(self, image: Path) -> ReadResult: ...

    @abstractmethod
    def read_region(self, image: Path, bbox: BoundingBox) -> ReadResult: ...

    @abstractmethod
    def read_table(self, image: Path, bbox: BoundingBox | None = None) -> ReadResult: ...

    @abstractmethod
    def read_row(self, image: Path, bbox: BoundingBox) -> ReadResult: ...

    @abstractmethod
    def read_cell(self, image: Path, bbox: BoundingBox) -> ReadResult: ...

    @abstractmethod
    def return_text_boxes(self, result: ReadResult) -> list[TextBox]: ...

    @abstractmethod
    def return_structure(self, result: ReadResult) -> dict[str, Any]: ...
