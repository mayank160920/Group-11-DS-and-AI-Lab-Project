from __future__ import annotations

from dataclasses import dataclass
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


class KeyValuePairs(dict[str, str]):
    def __iter__(self):
        return iter(self.items())


@dataclass(slots=True)
class StructuredPage:
    page_number: int
    raw_text: str
    section_headers: list[str]
    key_value_pairs: dict[str, str]
    index_text: str

    def __post_init__(self) -> None:
        if not isinstance(self.key_value_pairs, KeyValuePairs):
            object.__setattr__(self, "key_value_pairs", KeyValuePairs(self.key_value_pairs))

    @property
    def page_num(self) -> int:
        return self.page_number

    @property
    def composite_index(self) -> str:
        return self.index_text
