# pdf_document.py — Handles opening a PDF and turning pages into images.
# ---------------------------------------------------------------------------
# Called by: ui/pdf_viewer.py, ui/main_window.py, core/ocr_service.py
# Does NOT handle: buttons, windows, or OCR (those live in other files)
#
# Key OOP idea:
#   PdfDocument is a CLASS — a blueprint for "one open PDF file".
#   self.file_path, self.page_count are ATTRIBUTES (data on the object).
#   self.open(), self.render_page() are METHODS (actions on the object).
#
# Library reference: see imports_guide.py in the project root.

# --- __future__.annotations ---
# Allows modern type hints like Path | None without quote-wrapping.
from __future__ import annotations

# --- pathlib.Path (Python built-in) ---
# Object-oriented file paths: Path("book.pdf"), path.is_file(), path.read_bytes()
from pathlib import Path

# --- fitz = PyMuPDF (pip install pymupdf) ---
# PDF engine: fitz.open() opens a file, page.get_pixmap() renders to image,
# page.get_text() extracts embedded text. Named "fitz" for historical reasons.
import fitz


class PdfDocument:
    """
    Wrapper around one PDF file on disk.

    Attributes (data stored on each PdfDocument instance):
        file_path (Path | None): Path to the PDF, or None if nothing open.
        page_count (int): Total number of pages (0 if not open).
    """

    def __init__(self, file_path: str | Path | None = None) -> None:
        """
        Create a PdfDocument object. Optionally open a file immediately.

        Args:
            file_path: Path to a .pdf file, or None for an empty document holder.
        """
        # self = "this specific PdfDocument object we are building right now"
        self.file_path: Path | None = Path(file_path) if file_path else None
        self.page_count: int = 0

        # Leading underscore (_doc) is a Python convention meaning
        # "internal use — other code should not touch this directly".
        self._doc: fitz.Document | None = None

        if file_path:
            self.open(file_path)

    def open(self, file_path: str | Path) -> None:
        """
        Open a PDF from disk and store it on this object.

        Args:
            file_path: Path to the PDF file.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If PyMuPDF cannot read the file.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")

        # fitz.open() returns a Document object — we store it on self._doc
        self._doc = fitz.open(path)
        self.file_path = path
        # len(self._doc) works because PyMuPDF Document supports len()
        self.page_count = len(self._doc)

    def close(self) -> None:
        """Release the PDF from memory."""
        if self._doc is not None:
            self._doc.close()
        self._doc = None
        self.page_count = 0

    @property
    def is_open(self) -> bool:
        """
        Property — looks like an attribute (doc.is_open) but runs code.

        Returns True if a PDF is currently loaded.
        """
        return self._doc is not None

    def get_page_text(self, page_index: int) -> str:
        """
        Extract embedded text from a page (works for text-based PDFs only).

        Args:
            page_index: 0-based page number (first page = 0).

        Returns:
            str: Text content, or empty string for scanned/image-only pages.
        """
        self._require_open()
        page = self._doc[page_index]  # bracket access gets one page
        return page.get_text("text").strip()

    def is_scanned_page(self, page_index: int, min_chars: int = 20) -> bool:
        """
        Guess whether a page is a scanned image (little or no embedded text).

        Args:
            page_index: 0-based page index.
            min_chars: Pages with fewer characters than this are "scanned".

        Returns:
            bool: True if the page likely needs OCR.
        """
        text = self.get_page_text(page_index)
        return len(text) < min_chars

    def render_page(
        self,
        page_index: int,
        zoom: float = 1.0,
    ) -> tuple[bytes, int, int]:
        """
        Turn one PDF page into a PNG image (bytes) for display in Qt.

        PyMuPDF renders at 72 DPI when the matrix scale is 1.0, which produces
        blurry text on modern displays.  We always render at a minimum of
        144 DPI (BASE_DPI_SCALE = 2.0) so the image is sharp enough to study.
        The UI zoom factor from the toolbar is applied on top of that base.

        The returned width/height are the *logical* page dimensions (at 72 DPI
        equivalent) so the coordinate-mapping math in pdf_viewer stays correct.

        Args:
            page_index: 0-based page index.
            zoom: UI scale factor (1.0 = 100 %, 2.0 = 200 %, …).

        Returns:
            tuple: (png_bytes, logical_width_px, logical_height_px)
        """
        BASE_DPI_SCALE = 2.0   # renders at 144 DPI; raise to 3.0 for 216 DPI

        self._require_open()
        page = self._doc[page_index]

        # Apply both the base DPI scale and the user's zoom level
        render_scale = BASE_DPI_SCALE * zoom
        matrix = fitz.Matrix(render_scale, render_scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        png_bytes = pixmap.tobytes("png")
        return png_bytes, pixmap.width, pixmap.height

    def render_page_pil(self, page_index: int, zoom: float = 2.0):
        """
        Render page as a Pillow Image (used by OCR).

        Args:
            page_index: 0-based page index.
            zoom: Higher zoom = better OCR accuracy but slower.

        Returns:
            PIL.Image.Image
        """
        # Imported here (not at top) so pdf_document.py loads even if Pillow missing
        # until OCR is actually used. PIL.Image = Pillow's image class.
        from PIL import Image
        # io.BytesIO = treat bytes in memory like a file (PNG bytes → Image.open)
        import io

        png_bytes, _, _ = self.render_page(page_index, zoom=zoom)
        return Image.open(io.BytesIO(png_bytes))

    def file_hash(self) -> str:
        """
        Short hash of the file for cache keys (OCR cache, annotations).

        Returns:
            str: First 16 hex chars of SHA-256, or "" if no file.
        """
        # hashlib (Python built-in) — SHA-256 fingerprint of file for cache keys
        import hashlib

        if not self.file_path or not self.file_path.is_file():
            return ""
        digest = hashlib.sha256(self.file_path.read_bytes()).hexdigest()
        return digest[:16]

    def _require_open(self) -> None:
        """Internal helper — raise if no PDF is loaded."""
        if self._doc is None:
            raise RuntimeError("No PDF is open. Call open() first.")
