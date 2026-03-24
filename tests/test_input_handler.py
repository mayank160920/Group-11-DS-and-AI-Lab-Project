from __future__ import annotations

import fitz
import pytest
from PIL import Image

from src.input.input_handler import InputHandler
from src.shared_types import InputType


def create_pdf(path, page_count: int = 2) -> None:
    document = fitz.open()
    for page_number in range(page_count):
        page = document.new_page()
        page.insert_text((72, 72), f"Page {page_number + 1}")
    document.save(path)
    document.close()


def create_png(path) -> None:
    image = Image.new("RGB", (120, 80), color="white")
    image.save(path, format="PNG")


def test_detect_input_type_pdf(tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, page_count=1)

    handler = InputHandler()

    assert handler.detect_input_type(pdf_path) is InputType.PDF


def test_detect_input_type_png(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    create_png(image_path)

    handler = InputHandler()

    assert handler.detect_input_type(image_path) is InputType.IMAGE


def test_unknown_extension_raises_value_error(tmp_path) -> None:
    unknown_file = tmp_path / "sample.txt"
    unknown_file.write_text("test", encoding="utf-8")

    handler = InputHandler()

    with pytest.raises(ValueError, match="Supported formats"):
        handler.detect_input_type(unknown_file)


def test_missing_file_raises_file_not_found() -> None:
    handler = InputHandler()

    with pytest.raises(FileNotFoundError):
        handler.load("missing.pdf")


def test_loaded_input_total_pages_for_pdf(tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, page_count=3)

    handler = InputHandler()
    loaded = handler.load(pdf_path)

    assert loaded.input_type is InputType.PDF
    assert loaded.source_path == pdf_path
    assert loaded.total_pages == 3
    assert sorted(loaded.page_images) == [0, 1, 2]
    assert all(page.mime_type == "image/png" for page in loaded.page_images.values())
    assert all(page.image_base64 for page in loaded.page_images.values())


def test_loaded_input_total_pages_for_image(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    create_png(image_path)

    handler = InputHandler()
    loaded = handler.load(image_path)

    assert loaded.input_type is InputType.IMAGE
    assert loaded.source_path == image_path
    assert loaded.total_pages == 1
    assert sorted(loaded.page_images) == [0]
    page_image = loaded.page_images[0]
    assert page_image.width == 120
    assert page_image.height == 80
    assert page_image.mime_type == "image/png"
    assert page_image.image_base64
