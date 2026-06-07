from __future__ import annotations

import json

import sys

from dataclasses import dataclass, asdict

from pathlib import Path

import pytesseract

from PIL import Image

if sys.platform == "win32":
    tesseract_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if tesseract_path.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)


@dataclass
class OcrWord:
    text: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class OcrResult:
    page_index: int
    words: list[OcrWord]
    language: str = "ara"


def check_tesseract_installed() -> tuple[bool, str]:
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
    img_width, img_height = image.size

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

        if not text or conf < 0:
            continue

        left = data["left"][i]
        top = data["top"][i]
        width = data["width"][i]
        height = data["height"][i]

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
    def __init__(self, cache_dir: Path | str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, pdf_hash: str, page_index: int) -> Path:
        return self.cache_dir / f"{pdf_hash}_page_{page_index}.json"

    def has(self, pdf_hash: str, page_index: int) -> bool:
        return self._cache_path(pdf_hash, page_index).is_file()

    def load(self, pdf_hash: str, page_index: int) -> OcrResult | None:
        path = self._cache_path(pdf_hash, page_index)
        if not path.is_file():
            return None

        raw = json.loads(path.read_text(encoding="utf-8"))
        words = [OcrWord(**w) for w in raw.get("words", [])]
        return OcrResult(page_index=page_index, words=words, language=raw.get("language", "ara"))

    def save(self, pdf_hash: str, result: OcrResult) -> None:
        path = self._cache_path(pdf_hash, result.page_index)
        payload = {
            "page_index": result.page_index,
            "language": result.language,
            "words": [asdict(w) for w in result.words],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
