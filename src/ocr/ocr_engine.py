from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shared_types import StructuredPage
from paddlex.inference.pipelines.paddleocr_vl.result import PaddleOCRVLResult

class OCREngine:
    SUPPORTED_ENGINES = {"surya", "paddle"}
    KEY_VALUE_PATTERN = re.compile(
        r"^\s*(?:[-*]\s+)?(?:#+\s+)?([^:\n]{1,80}):\s*(.+?)\s*$",
        re.MULTILINE,
    )

    def __init__(
        self,
        engine: str = "paddle",
        *,
        device: str = "cpu",
        pipeline_version: str = "v1.5",
        use_doc_orientation_classify: bool = False,
        use_doc_unwarping: bool = False
    ) -> None:
        if engine not in self.SUPPORTED_ENGINES:
            supported = ", ".join(sorted(self.SUPPORTED_ENGINES))
            raise ValueError(f"Unsupported OCR engine '{engine}'. Supported engines: {supported}")

        if engine == "surya":
            raise NotImplementedError("The 'surya' OCR backend is not implemented yet.")

        self.engine = engine
        self.device = device
        self.pipeline_version = pipeline_version
        self.use_doc_orientation_classify = use_doc_orientation_classify
        self.use_doc_unwarping = use_doc_unwarping
        self._pipeline: Any | None = None

    def process_pdf(self, pdf_path: str | Path) -> list[StructuredPage]:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        pipeline = self._get_pipeline()
        pages: list[StructuredPage] = []
        predictions = pipeline.predict(input=str(path))

        for page_number, result in enumerate(predictions, start=1):
            raw_text = self._extract_raw_text(result)
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

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            self._pipeline = self._create_paddle_pipeline()
        return self._pipeline

    def _create_paddle_pipeline(self) -> Any:
        try:
            from paddleocr import PaddleOCRVL
        except ImportError as exc:
            raise ImportError(
                "PaddleOCR is required for the 'paddle' backend. "
                "Install it in a Python 3.8-3.12 environment with "
                "`python -m pip install -U \"paddleocr[doc-parser]\"` "
                "after installing a compatible PaddlePaddle build."
            ) from exc

        return PaddleOCRVL(
            device=self.device,
            pipeline_version=self.pipeline_version,
            use_doc_orientation_classify=self.use_doc_orientation_classify,
            use_doc_unwarping=self.use_doc_unwarping,
            use_angle_cls=True,
            enable_mkldnn=False # MKL-DNN can cause issues in some environments, so we disable it by default
        )

    def _extract_raw_text(self, result: PaddleOCRVLResult) -> str:
        markdown_text = result.markdown["markdown_texts"]
        text = self._flatten_text(markdown_text)
        return text
        
    def _extract_section_headers(self, raw_text: str) -> list[str]:
        headers: list[str] = []

        for line in raw_text.splitlines():
            candidate = self._normalize_line(line)
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
            cleaned_key = self._normalize_line(key)
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

    def _normalize_line(self, line: str) -> str:
        cleaned = line.strip()
        cleaned = re.sub(r"^[#>\-*]+\s*", "", cleaned)
        return " ".join(cleaned.split())

    def _flatten_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (list, tuple)):
            parts = [self._flatten_text(item) for item in value]
            return "\n".join(part for part in parts if part).strip()
        return str(value).strip()
