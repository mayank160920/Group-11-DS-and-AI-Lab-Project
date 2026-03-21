from __future__ import annotations

from pathlib import Path

from ingestion.page_image_store import PageImageStore
from input.image_loader import ImageLoader
from shared_types import InputType, LoadedInput


class InputHandler:
    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

    def __init__(
        self,
        image_loader: ImageLoader | None = None,
        page_image_store: PageImageStore | None = None,
    ) -> None:
        self.image_loader = image_loader or ImageLoader()
        self.page_image_store = page_image_store or PageImageStore()

    def detect_input_type(self, path: str | Path) -> InputType:
        suffix = Path(path).suffix.lower()

        if suffix in self.PDF_EXTENSIONS:
            return InputType.PDF
        if suffix in self.IMAGE_EXTENSIONS:
            return InputType.IMAGE

        supported_formats = sorted(self.PDF_EXTENSIONS | self.IMAGE_EXTENSIONS)
        raise ValueError(
            "Unsupported input format. Supported formats are: "
            + ", ".join(supported_formats)
        )

    def load(self, input_path: str | Path) -> LoadedInput:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        input_type = self.detect_input_type(path)
        if input_type is InputType.PDF:
            return self._load_pdf(path)
        return self._load_image(path)

    def _load_pdf(self, pdf_path: Path) -> LoadedInput:
        total_pages = self.page_image_store.load_pdf(pdf_path)
        return LoadedInput(
            input_type=InputType.PDF,
            source_path=pdf_path,
            total_pages=total_pages,
            page_images=self.page_image_store.get_all_pages(),
        )

    def _load_image(self, image_path: Path) -> LoadedInput:
        return self.image_loader.load_image(image_path)
