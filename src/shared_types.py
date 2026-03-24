from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PIL import Image


class InputType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"


@dataclass(slots=True)
class PageImage:
    page_number: int
    image: Image.Image
    image_base64: str
    mime_type: str
    width: int
    height: int


@dataclass(slots=True)
class LoadedInput:
    input_type: InputType
    source_path: Path
    total_pages: int
    page_images: dict[int, PageImage]


@dataclass(slots=True)
class StructuredPage:
    page_number: int
    raw_text: str = ""
    section_headers: list[str] = field(default_factory=list)
    key_value_pairs: list[tuple[str, str]] = field(default_factory=list)
    index_text: str = ""

    @property
    def page_num(self) -> int:
        return self.page_number

    @property
    def composite_index(self) -> str:
        return self.index_text
