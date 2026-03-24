from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from src.shared_types import InputType, LoadedInput, PageImage


class ImageLoader:
    MAX_IMAGE_SIZE = (4096, 4096)

    def load_image(self, image_path: str | Path) -> LoadedInput:
        path = Path(image_path)

        with Image.open(path) as img:
            image = img.convert("RGB")
            if image.width > self.MAX_IMAGE_SIZE[0] or image.height > self.MAX_IMAGE_SIZE[1]:
                image.thumbnail(self.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

        page_image = self._to_page_image(image=image, page_number=0)
        return LoadedInput(
            input_type=InputType.IMAGE,
            source_path=path,
            total_pages=1,
            page_images={0: page_image},
        )

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
