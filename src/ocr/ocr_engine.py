from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from src.input.input_handler import InputHandler
from src.shared_types import LoadedInput, StructuredPage


class OCREngine:
    SUPPORTED_ENGINES = {"paddle"}

    KEY_VALUE_PATTERN = re.compile(
        r"^\s*(?:[-*]\s+)?(?:#+\s+)?([^:\n]{1,80}):\s*(.+?)\s*$",
        re.MULTILINE,
    )

    def __init__(
        self,
        engine: str = "paddle",
        *,
        lang: str = "en",
        show_log: bool = False,
        device: str = "cpu",
        use_doc_orientation_classify: bool = False,
        use_doc_unwarping: bool = False,
        use_textline_orientation: bool = False,
        use_angle_cls: bool = False,  # Deprecated but included for compatibility
    ) -> None:
        if engine not in self.SUPPORTED_ENGINES:
            supported = ", ".join(sorted(self.SUPPORTED_ENGINES))
            raise ValueError(
                f"Unsupported OCR engine '{engine}'. Supported engines: {supported}"
            )

        if engine == "surya":
            raise NotImplementedError(
                "The 'surya' backend is not implemented yet. Use engine='paddle'."
            )

        self.engine = engine
        self.lang = lang
        self.show_log = show_log
        self._ocr: Any | None = None

        self.device = device
        self.use_doc_orientation_classify = use_doc_orientation_classify
        self.use_doc_unwarping = use_doc_unwarping
        self.use_textline_orientation = use_textline_orientation
        self.use_angle_cls = use_angle_cls

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def process_pdf(self, pdf_path: str | Path, as_dict: bool = False) -> list[StructuredPage] | dict[int, StructuredPage]:
        """
        Convenience wrapper:
        PDF -> InputHandler -> rendered page images -> OCR per page
        """
        loaded_input = InputHandler().load(pdf_path)
        st_page = self.process_loaded_input(loaded_input)
        if as_dict:
            st_page_dict = {page.page_number: page for page in st_page}
            return st_page_dict
        return st_page

    def process_loaded_input(self, loaded_input: LoadedInput) -> list[StructuredPage]:
        """
        OCR all pages from a LoadedInput object.

        Assumes loaded_input.page_images contains page_number -> PageImage.
        Returns pages in ascending page order.
        """
        structured_pages: list[StructuredPage] = []

        for page_number in sorted(loaded_input.page_images.keys()):
            page_image = loaded_input.page_images[page_number]
            structured_pages.append(
                self.process_page_image(
                    page_number=page_number,
                    image_b64=page_image.image_base64,
                )
            )

        return structured_pages

    def process_page_image(self, page_number: int, image_b64: str) -> StructuredPage:
        """
        OCR a single base64-encoded page image and return a StructuredPage.
        """
        image = self._decode_base64_image(image_b64)
        result = self._get_ocr().predict(image)

        lines = self._extract_lines_from_paddle_result(result)
        raw_text = "\n".join(lines).strip()

        section_headers = self._extract_section_headers(raw_text)
        key_value_pairs = self._extract_key_value_pairs(raw_text)
        index_text = self._build_index_text(
            section_headers=section_headers,
            key_value_pairs=key_value_pairs,
            raw_text=raw_text,
        )

        page = StructuredPage(
            page_number=page_number,
            raw_text=raw_text,
            section_headers=section_headers,
            key_value_pairs=key_value_pairs,
            index_text=index_text,
        )

        return page

    # ---------------------------------------------------------------------
    # OCR backend
    # ---------------------------------------------------------------------

    def _get_ocr(self) -> Any:
        if self._ocr is None:
            self._ocr = self._create_paddle_ocr()
        return self._ocr

    def _create_paddle_ocr(self) -> Any:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ImportError(
                "PaddleOCR is required for OCREngine(engine='paddle'). "
                "Install it with:\n"
                "  pip install paddleocr\n"
                "and also install a compatible PaddlePaddle build for your system."
            ) from exc

        return PaddleOCR(
            device=self.device,
            text_recognition_model_name="PP-OCRv3_mobile_rec",
            text_detection_model_name="PP-OCRv3_mobile_det",
            use_doc_orientation_classify=self.use_doc_orientation_classify,
            use_doc_unwarping=self.use_doc_unwarping,
            use_textline_orientation=self.use_textline_orientation,
            use_angle_cls=self.use_angle_cls,  # Deprecated but included for compatibility
            enable_mkldnn=False,  # MKL-DNN can cause issues in some environments, so we disable it by default
        )

    # ---------------------------------------------------------------------
    # OCR parsing
    # ---------------------------------------------------------------------

    def _decode_base64_image(self, image_b64: str) -> np.ndarray:
        try:
            image_bytes = base64.b64decode(image_b64)
            np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        except Exception as exc:
            raise ValueError(f"Failed to decode base64 page image: {exc}") from exc

        if image is None:
            raise ValueError(
                "Failed to decode base64 page image: cv2.imdecode returned None"
            )

        return image

    def _extract_lines_from_paddle_result(self, result: Any) -> list[str]:
        """
        Standard PaddleOCR result shape is typically:

        [
          [
            [box_points, (text, confidence)],
            [box_points, (text, confidence)],
            ...
          ]
        ]

        This method extracts the text strings safely.
        """
        if not result:
            return []

        lines: list[str] = []

        # Usually result[0] is the page list of OCR line detections.
        page_result = result[0]
        if page_result is None:
            return []

        for text in page_result["rec_texts"]:
            cleaned = self._normalize_line(text)
            if cleaned:
                lines.append(cleaned)

        return lines

    # ---------------------------------------------------------------------
    # Structuring heuristics
    # ---------------------------------------------------------------------

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

    def _extract_key_value_pairs(self, raw_text: str) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for key, value in self.KEY_VALUE_PATTERN.findall(raw_text):
            cleaned_key = self._normalize_line(key)
            cleaned_value = " ".join(value.split())
            pairs.append((cleaned_key, cleaned_value))
        return pairs

    def _build_index_text(
        self,
        *,
        section_headers: list[str],
        key_value_pairs: list[tuple[str, str]],
        raw_text: str,
    ) -> str:
        """
        Important: no summarization.
        Preserve numeric values and original OCR text for downstream retrieval.
        """
        section_text = " | ".join(section_headers) if section_headers else "NONE"
        key_value_text = (
            " | ".join(f"{key}: {value}" for key, value in key_value_pairs)
            if key_value_pairs
            else "NONE"
        )

        return "\n".join(
            [
                f"SECTIONS: {section_text}",
                f"KEY_VALUES: {key_value_text}",
                "RAW_TEXT:",
                raw_text or "",
            ]
        )

    # ---------------------------------------------------------------------
    # Utility helpers
    # ---------------------------------------------------------------------

    def _is_title_case(self, text: str) -> bool:
        words = [word for word in re.split(r"\s+", text) if word]
        if not words:
            return False

        title_like_count = 0
        alpha_count = 0

        for word in words:
            stripped = word.strip("()[]{}.,;:-")
            if not stripped:
                continue
            if not stripped[0].isalpha():
                continue

            alpha_count += 1
            if stripped[0].isupper() and stripped[1:].islower():
                title_like_count += 1

        return alpha_count > 0 and title_like_count == alpha_count

    def _normalize_line(self, line: str) -> str:
        cleaned = line.strip()
        cleaned = re.sub(r"^[#>\-*]+\s*", "", cleaned)
        return " ".join(cleaned.split())
