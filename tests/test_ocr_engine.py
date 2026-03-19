from __future__ import annotations

import fitz
import pytest

from ocr.ocr_engine import OCREngine


def create_text_pdf(path) -> None:
    document = fitz.open()
    page = document.new_page()
    text = "\n".join(
        [
            "CLAIM SUMMARY",
            "Member Information",
            "Deductible: 500",
            "Copay: 25",
            "Coinsurance: 20%",
            "This policy covers preventive visits.",
        ]
    )
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


class FakePaddleResult:
    def __init__(self, markdown_text: str) -> None:
        self.markdown = {"markdown_texts": markdown_text}


class FakePaddlePipeline:
    def __init__(self, results) -> None:
        self._results = results

    def predict(self, input: str):
        return iter(self._results)


def test_surya_backend_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        OCREngine(engine="surya")


def test_structured_page_has_required_fields(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "ocr.pdf"
    create_text_pdf(pdf_path)

    fake_results = [
        FakePaddleResult(
            "# CLAIM SUMMARY\n\n## Member Information\n\nDeductible: 500\nCopay: 25\nCoinsurance: 20%"
        )
    ]
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_pipeline",
        lambda self: FakePaddlePipeline(fake_results),
    )

    engine = OCREngine(engine="paddle")
    pages = engine.process_pdf(pdf_path)

    assert len(pages) == 1
    page = pages[0]
    assert page.page_number == 1
    assert isinstance(page.raw_text, str)
    assert isinstance(page.section_headers, list)
    assert isinstance(page.key_value_pairs, dict)
    assert isinstance(page.index_text, str)


def test_index_text_contains_raw_numeric_values(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "ocr.pdf"
    create_text_pdf(pdf_path)

    fake_results = [
        FakePaddleResult(
            "# CLAIM SUMMARY\n\nDeductible: 500\nCopay: 25\nCoinsurance: 20%\nThis policy covers preventive visits."
        )
    ]
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_pipeline",
        lambda self: FakePaddlePipeline(fake_results),
    )

    engine = OCREngine(engine="paddle")
    page = engine.process_pdf(pdf_path)[0]

    assert "500" in page.index_text
    assert "25" in page.index_text
    assert "20%" in page.index_text


def test_section_headers_detected(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "ocr.pdf"
    create_text_pdf(pdf_path)

    fake_results = [
        FakePaddleResult(
            "# CLAIM SUMMARY\n\n## Member Information\n\nDeductible: 500\nCopay: 25"
        )
    ]
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_pipeline",
        lambda self: FakePaddlePipeline(fake_results),
    )

    engine = OCREngine(engine="paddle")
    page = engine.process_pdf(pdf_path)[0]

    assert "CLAIM SUMMARY" in page.section_headers
    assert "Member Information" in page.section_headers


def test_key_value_pairs_extracted(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "ocr.pdf"
    create_text_pdf(pdf_path)

    fake_results = [
        FakePaddleResult(
            "# CLAIM SUMMARY\n\n- Deductible: 500\n- Copay: 25\n- Coinsurance: 20%"
        )
    ]
    monkeypatch.setattr(
        OCREngine,
        "_create_paddle_pipeline",
        lambda self: FakePaddlePipeline(fake_results),
    )

    engine = OCREngine(engine="paddle")
    page = engine.process_pdf(pdf_path)[0]

    assert page.key_value_pairs["Deductible"] == "500"
    assert page.key_value_pairs["Copay"] == "25"
    assert page.key_value_pairs["Coinsurance"] == "20%"
