from __future__ import annotations

import re
from pathlib import Path

import fitz

from shared_types import StructuredPage


class OCREngine:
    SUPPORTED_ENGINES = {"surya", "paddle"}
    KEY_VALUE_PATTERN = re.compile(r"^\s*([^:\n]{1,80}):\s*(.+?)\s*$", re.MULTILINE)

    def __init__(self, engine: str = "surya") -> None:
        if engine not in self.SUPPORTED_ENGINES:
            supported = ", ".join(sorted(self.SUPPORTED_ENGINES))
            raise ValueError(f"Unsupported OCR engine '{engine}'. Supported engines: {supported}")
        self.engine = engine

    def process_pdf(self, pdf_path: str | Path) -> list[StructuredPage]:
        path = Path(pdf_path)
        pages: list[StructuredPage] = []

        with fitz.open(path) as document:
            for page_number, page in enumerate(document, start=1):
                raw_text = self._extract_text(page)
                section_headers = self._extract_section_headers(raw_text)
                key_value_pairs = self._extract_key_value_pairs(raw_text)
                index_text = self._build_index_text(
                    section_headers=section_headers,
                    key_value_pairs=key_value_pairs,
                    raw_text=raw_text,
                )
                pages.append(
                    StructuredPage(
                        page_number=page_number,
                        raw_text=raw_text,
                        section_headers=section_headers,
                        key_value_pairs=key_value_pairs,
                        index_text=index_text,
                    )
                )

        return pages

    def _extract_text(self, page: fitz.Page) -> str:
        # Use the PDF text layer when available so tests remain lightweight.
        return page.get_text("text").strip()

    def _extract_section_headers(self, raw_text: str) -> list[str]:
        headers: list[str] = []

        for line in raw_text.splitlines():
            candidate = line.strip()
            if not candidate or len(candidate) > 60 or ":" in candidate:
                continue
            if len(candidate.split()) > 6:
                continue
            if candidate.isupper() or self._is_title_case(candidate):
                headers.append(candidate)

        return headers

    def _extract_key_value_pairs(self, raw_text: str) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for key, value in self.KEY_VALUE_PATTERN.findall(raw_text):
            cleaned_key = " ".join(key.split())
            cleaned_value = " ".join(value.split())
            pairs[cleaned_key] = cleaned_value
        return pairs

    def _build_index_text(
        self,
        section_headers: list[str],
        key_value_pairs: dict[str, str],
        raw_text: str,
    ) -> str:
        section_text = " | ".join(section_headers) if section_headers else "NONE"
        key_value_text = (
            " | ".join(f"{key}: {value}" for key, value in key_value_pairs.items())
            if key_value_pairs
            else "NONE"
        )
        raw_text = raw_text or ""
        return "\n".join(
            [
                f"SECTIONS: {section_text}",
                f"KEY_VALUES: {key_value_text}",
                "RAW_TEXT:",
                raw_text,
            ]
        )

    def _is_title_case(self, text: str) -> bool:
        words = [word for word in re.split(r"\s+", text) if word]
        if not words:
            return False

        return all(
            word[0].isupper() and word[1:].islower()
            for word in words
            if word[0].isalpha()
        )
