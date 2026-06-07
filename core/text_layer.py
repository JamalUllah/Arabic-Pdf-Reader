from __future__ import annotations

import arabic_reshaper

from bidi.algorithm import get_display

from core.ocr_service import OcrWord


def shape_arabic_for_display(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def shape_arabic_for_clipboard(text: str) -> str:
    return shape_arabic_for_display(text)


def words_to_full_text(words: list[OcrWord]) -> str:
    return " ".join(w.text for w in words if w.text.strip())


def find_words_in_rect(
    words: list[OcrWord],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> list[OcrWord]:
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
