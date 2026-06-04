# text_layer.py — Helpers for Arabic text display and clipboard.
# ---------------------------------------------------------------------------
# Called by: ui/pdf_viewer.py
#
# OCR gives us raw Arabic text; display and clipboard need "shaping"
# so letters connect properly and read right-to-left.
#
# Library reference: see imports_guide.py in the project root.

from __future__ import annotations

# --- arabic_reshaper (pip) ---
# Arabic letters change shape (connected script). reshape() fixes letter forms.
import arabic_reshaper

# --- bidi.algorithm.get_display (python-bidi, pip) ---
# Reorders characters for right-to-left display and clipboard paste.
from bidi.algorithm import get_display

# --- OcrWord (our dataclass from core.ocr_service) ---
# One recognized word + its normalized x,y,w,h on the page.
from core.ocr_service import OcrWord


def shape_arabic_for_display(text: str) -> str:
    """
    Prepare Arabic text for on-screen display (RTL, connected letters).

    Args:
        text: Raw Arabic string from OCR or PDF.

    Returns:
        str: Text safe to show in Qt widgets.
    """
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def shape_arabic_for_clipboard(text: str) -> str:
    """
    Prepare Arabic text for copying to clipboard / pasting into Notepad.

    Same shaping as display — ensures pasted text reads correctly.
    """
    return shape_arabic_for_display(text)


def words_to_full_text(words: list[OcrWord]) -> str:
    """
    Join OCR words into one string (space-separated).

    Args:
        words: List of OcrWord from OCR.

    Returns:
        str: Combined text.
    """
    return " ".join(w.text for w in words if w.text.strip())


def find_words_in_rect(
    words: list[OcrWord],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> list[OcrWord]:
    """
    Find OCR words whose center point falls inside a selection rectangle.

    Coordinates are normalized (0.0–1.0).

    Args:
        words: All words on the page.
        x0, y0, x1, y1: Selection rectangle (fractions of page size).

    Returns:
        list[OcrWord]: Words inside the selection.
    """
    # Normalize so x0 < x1 and y0 < y1 regardless of drag direction
    left = min(x0, x1)
    right = max(x0, x1)
    top = min(y0, y1)
    bottom = max(y0, y1)

    selected: list[OcrWord] = []
    for word in words:
        cx = word.x + word.w / 2
        cy = word.y + word.h / 2
        if left <= cx <= right and top <= cy <= bottom:
            selected.append(word)
    return selected
