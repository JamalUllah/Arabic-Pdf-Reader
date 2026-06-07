from __future__ import annotations

from pathlib import Path

import fitz


class PdfDocument:
    def __init__(self, file_path: str | Path | None = None) -> None:
        self.file_path: Path | None = Path(file_path) if file_path else None
        self.page_count: int = 0

        self._doc: fitz.Document | None = None

        if file_path:
            self.open(file_path)

    def open(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")

        self._doc = fitz.open(path)
        self.file_path = path
        self.page_count = len(self._doc)

    def close(self) -> None:
        if self._doc is not None:
            self._doc.close()
        self._doc = None
        self.page_count = 0

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    def get_page_text(self, page_index: int) -> str:
        self._require_open()
        page = self._doc[page_index]
        return page.get_text("text").strip()

    def is_scanned_page(self, page_index: int, min_chars: int = 20) -> bool:
        text = self.get_page_text(page_index)
        return len(text) < min_chars

    def render_page(
        self,
        page_index: int,
        zoom: float = 1.0,
    ) -> tuple[bytes, int, int]:
        BASE_DPI_SCALE = 4.0

        self._require_open()
        page = self._doc[page_index]

        render_scale = BASE_DPI_SCALE * zoom
        matrix = fitz.Matrix(render_scale, render_scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        png_bytes = pixmap.tobytes("png")
        return png_bytes, pixmap.width, pixmap.height

    def render_page_pil(self, page_index: int, zoom: float = 2.0):
        from PIL import Image
        import io

        png_bytes, _, _ = self.render_page(page_index, zoom=zoom)
        return Image.open(io.BytesIO(png_bytes))

    def file_hash(self) -> str:
        import hashlib

        if not self.file_path or not self.file_path.is_file():
            return ""
        digest = hashlib.sha256(self.file_path.read_bytes()).hexdigest()
        return digest[:16]

    def _require_open(self) -> None:
        if self._doc is None:
            raise RuntimeError("No PDF is open. Call open() first.")
