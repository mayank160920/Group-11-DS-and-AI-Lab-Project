from __future__ import annotations

import base64
import io
from pathlib import Path

import fitz
from PIL import Image

from src.shared_types import PageImage


class PageImageStore:
    def __init__(self, dpi: int = 150) -> None:
        self.dpi = dpi
        self._pages: dict[int, PageImage] = {}

    def load_pdf(self, pdf_path: str | Path) -> int:
        path = Path(pdf_path)
        self._pages = {}
        scale = self.dpi / 72

        with fitz.open(path) as document:
            for page_index, page in enumerate(document):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                self._pages[page_index] = self._to_page_image(image=image, page_number=page_index)

        return len(self._pages)

    def get_pages(self, page_numbers: list[int]) -> dict[int, PageImage]:
        missing_pages = [page_number for page_number in page_numbers if page_number not in self._pages]
        if missing_pages:
            raise KeyError(f"Requested pages are not loaded: {missing_pages}")

        return {page_number: self._pages[page_number] for page_number in page_numbers}

    def get_all_pages(self) -> dict[int, PageImage]:
        return dict(self._pages)

    def _to_page_image(self, image: Image.Image, page_number: int) -> PageImage:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return PageImage(
            page_number=page_number,
            image=image,
            image_base64=encoded,
            mime_type="image/png",
            width=image.width,
            height=image.height,
        )

    # Compatibility methods for kartik's rag notebook
    def get(self, page_num: int) -> str:
        page_image = self._pages.get(page_num)
        if page_image is None:
            raise KeyError(f"Page number {page_num} not found in the store.")
        return page_image.image_base64
    
    def all_pages(self) -> list[int]:
        return list(self._pages.keys())
    
    def page_count(self) -> int:
        return len(self._pages)