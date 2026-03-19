from __future__ import annotations

from pathlib import Path

from input.input_handler import InputHandler
from shared_types import LoadedInput


class DocumentProcessor:
    def __init__(self, input_handler: InputHandler | None = None) -> None:
        self.input_handler = input_handler or InputHandler()

    def process(self, input_path: str | Path) -> LoadedInput:
        return self.input_handler.load(input_path)
