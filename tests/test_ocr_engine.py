from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from PIL import Image

from src.input.input_handler import InputHandler
from src.ocr.ocr_engine import OCREngine
from src.shared_types import InputType, LoadedInput, PageImage


def create_page_image(page_number: int, size: tuple[int, int] = (32, 32)) -> PageImage:
    image = Image.new("RGB", size, color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return PageImage(
        page_number=page_number,
        image=image,
        image_base64=encoded,
        mime_type="image/png",
        width=size[0],
        height=size[1],
    )


def create_loaded_input(page_numbers: list[int]) -> LoadedInput:
    page_images = {
        page_number: create_page_image(page_number=page_number)
        for page_number in page_numbers
    }
    return LoadedInput(
        input_type=InputType.PDF,
        source_path=Path("sample.pdf"),
        total_pages=len(page_images),
        page_images=page_images,
    )


class FakePaddleOCR:
    def __init__(self, page_lines: list[list[str]]) -> None:
        self.page_lines = page_lines
        self.calls = 0

    def predict(self, image):
        result = [{"rec_texts": self.page_lines[self.calls]}]
        self.calls += 1
        return result


def test_unsupported_backend_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported OCR engine"):
        OCREngine(engine="surya")


def test_process_loaded_input_builds_structured_page(monkeypatch) -> None:
    page_lines = [
        [
            "CLAIM SUMMARY",
            "Member Information",
            "Deductible: 500",
            "Copay: 25",
            "Coinsurance: 20%",
            "This policy covers preventive visits.",
        ]
    ]
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_ocr",
        lambda self: FakePaddleOCR(page_lines),
    )

    engine = OCREngine(engine="paddle")
    page = engine.process_loaded_input(create_loaded_input([0]))[0]

    assert page.page_number == 0
    assert page.raw_text == "\n".join(page_lines[0])
    assert "CLAIM SUMMARY" in page.section_headers
    assert "Member Information" in page.section_headers
    assert ("Deductible", "500") in page.key_value_pairs
    assert ("Copay", "25") in page.key_value_pairs
    assert ("Coinsurance", "20%") in page.key_value_pairs
    assert "500" in page.index_text
    assert "25" in page.index_text
    assert "20%" in page.index_text


def test_process_loaded_input_returns_pages_in_page_order(monkeypatch) -> None:
    page_lines = [["PAGE ZERO"], ["PAGE TWO"]]
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_ocr",
        lambda self: FakePaddleOCR(page_lines),
    )

    engine = OCREngine(engine="paddle")
    loaded_input = create_loaded_input([2, 0])
    pages = engine.process_loaded_input(loaded_input)

    assert [page.page_number for page in pages] == [0, 2]
    assert [page.raw_text for page in pages] == ["PAGE ZERO", "PAGE TWO"]


def test_process_pdf_can_return_pages_as_dict(monkeypatch) -> None:
    page_lines = [["CLAIM SUMMARY", "Deductible: 500"]]
    loaded_input = create_loaded_input([0])

    monkeypatch.setattr(
        InputHandler,
        "load",
        lambda self, pdf_path: loaded_input,
    )
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_ocr",
        lambda self: FakePaddleOCR(page_lines),
    )

    engine = OCREngine(engine="paddle")
    pages = engine.process_pdf("ignored.pdf", as_dict=True)

    assert list(pages) == [0]
    assert pages[0].page_number == 0
    assert pages[0].raw_text == "\n".join(page_lines[0])
