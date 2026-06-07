# ocr_service.py — Offline Arabic OCR using Tesseract.
# ---------------------------------------------------------------------------
# Called by: ui/main_window.py (when user clicks "OCR this page")
# Does NOT handle: displaying images or buttons
#
# Plain functions vs class methods:
#   run_ocr_on_image() is a standalone FUNCTION — not tied to an object.
#   OcrCache is a CLASS — stores cache directory and knows how to save/load.
#
# Library reference: see imports_guide.py in the project root.

from __future__ import annotations

# --- json (Python built-in) ---
# Read/write OCR cache files as .json on disk (json.load, json.dump).
import json

# --- sys (Python built-in) ---
import sys

# --- dataclasses (Python built-in) ---
# @dataclass auto-creates __init__ for data classes (OcrWord, OcrResult).
# asdict() converts a dataclass instance to a plain dict for json.dump.
from dataclasses import dataclass, asdict

# --- pathlib.Path ---
# Build cache file paths: cache_dir / f"{hash}_page_{n}.json"
from pathlib import Path

# --- pytesseract (pip) — bridge to Tesseract OCR executable ---
# image_to_data() returns word text + pixel bounding boxes.
# get_tesseract_version() checks Tesseract is installed on Windows.
import pytesseract

# --- PIL.Image (Pillow, pip) ---
# Image type that pytesseract accepts; we load PNG bytes from PyMuPDF into it.
from PIL import Image

# On Windows, try to auto-detect the default Tesseract installation path.
# This avoids requiring users to manually edit their system PATH.
if sys.platform == "win32":
    # Default path from the UB-Mannheim installer
    tesseract_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if tesseract_path.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)


# @dataclass automatically creates __init__ for us — each OcrWord holds one word.
@dataclass
class OcrWord:
    """
    One word detected by OCR with its position on the page.

    Attributes:
        text: The recognized word.
        x, y, w, h: Bounding box in normalized coordinates (0.0 to 1.0).
                     x,y = top-left corner as fraction of page width/height.
    """

    text: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class OcrResult:
    """All words found on one page."""

    page_index: int
    words: list[OcrWord]
    language: str = "ara"


def check_tesseract_installed() -> tuple[bool, str]:
    """
    Check whether Tesseract is available on this computer.

    Returns:
        tuple: (is_ok, message_for_user)
    """
    try:
        pytesseract.get_tesseract_version()
        return True, "Tesseract is installed."
    except pytesseract.TesseractNotFoundError:
        return False, (
            "Tesseract OCR is not installed.\n\n"
            "Download for Windows:\n"
            "https://github.com/UB-Mannheim/tesseract/wiki\n\n"
            "Make sure to install the Arabic language pack (ara)."
        )


def run_ocr_on_image(image: Image.Image, language: str = "ara") -> list[OcrWord]:
    """
    Run Tesseract OCR on a Pillow image and return word bounding boxes.

    This is a plain FUNCTION (not a method) — you call it as:
        words = run_ocr_on_image(pil_image)

    Args:
        image: PIL Image of a PDF page.
        language: Tesseract language code ("ara" = Arabic, "ara+eng" = mixed).

    Returns:
        list[OcrWord]: Detected words with normalized positions.
    """
    img_width, img_height = image.size

    # image_to_data returns a dict with lists: text, left, top, width, height, conf, ...
    data = pytesseract.image_to_data(
        image,
        lang=language,
        output_type=pytesseract.Output.DICT,
    )

    words: list[OcrWord] = []
    n_boxes = len(data["text"])

    for i in range(n_boxes):
        text = (data["text"][i] or "").strip()
        conf = int(data["conf"][i]) if data["conf"][i] != "-1" else -1

        # Skip empty text or low-confidence garbage
        if not text or conf < 0:
            continue

        left = data["left"][i]
        top = data["top"][i]
        width = data["width"][i]
        height = data["height"][i]

        # Convert pixel coordinates to 0.0–1.0 fractions (zoom-independent)
        words.append(
            OcrWord(
                text=text,
                x=left / img_width,
                y=top / img_height,
                w=width / img_width,
                h=height / img_height,
            )
        )

    return words


class OcrCache:
    """
    Saves OCR results to disk so we don't re-run Tesseract on every visit.

    Each cached page is a JSON file:
        data/ocr_cache/{pdf_hash}_page_{n}.json
    """

    def __init__(self, cache_dir: Path | str) -> None:
        # Path(...) converts string to Path object for easy / joining
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, pdf_hash: str, page_index: int) -> Path:
        """Build the file path for one page's cache."""
        return self.cache_dir / f"{pdf_hash}_page_{page_index}.json"

    def has(self, pdf_hash: str, page_index: int) -> bool:
        """Return True if we already OCR'd this page before."""
        return self._cache_path(pdf_hash, page_index).is_file()

    def load(self, pdf_hash: str, page_index: int) -> OcrResult | None:
        """
        Load cached OCR result from disk.

        Returns:
            OcrResult or None if not cached or cache is unreadable.
        """
        path = self._cache_path(pdf_hash, page_index)
        if not path.is_file():
            return None

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            words = [OcrWord(**w) for w in raw.get("words", [])]
            return OcrResult(page_index=page_index, words=words, language=raw.get("language", "ara"))
        except Exception:
            # Corrupted or version-mismatched cache — delete and return None so OCR reruns
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

    def save(self, pdf_hash: str, result: OcrResult) -> None:
        """Save OCR result to disk as JSON."""
        path = self._cache_path(pdf_hash, result.page_index)
        payload = {
            "page_index": result.page_index,
            "language": result.language,
            "words": [asdict(w) for w in result.words],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")