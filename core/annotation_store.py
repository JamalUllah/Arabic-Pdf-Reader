from __future__ import annotations

import json

from dataclasses import dataclass, field, asdict

from datetime import datetime, timezone

from pathlib import Path

from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Highlight:
    page: int
    rects: list[list[float]]
    color: str = "yellow"
    text: str = ""
    created: str = field(default_factory=_now_iso)


@dataclass
class StickyNote:
    page: int
    x: float
    y: float
    content: str = ""
    color: str = "yellow"
    created: str = field(default_factory=_now_iso)


@dataclass
class PageNote:
    page: int
    content: str = ""
    updated: str = field(default_factory=_now_iso)


@dataclass
class Bookmark:
    page: int
    title: str = ""
    created: str = field(default_factory=_now_iso)


class AnnotationStore:
    def __init__(self, pdf_path: Path | str, pdf_hash: str = "") -> None:
        self.pdf_path = Path(pdf_path)
        self.pdf_hash = pdf_hash
        self.highlights: list[Highlight] = []
        self.sticky_notes: list[StickyNote] = []
        self.page_notes: list[PageNote] = []
        self.bookmarks: list[Bookmark] = []

    @property
    def sidecar_path(self) -> Path:
        return self.pdf_path.with_suffix(self.pdf_path.suffix + ".apr.json")

    def load(self) -> None:
        path = self.sidecar_path
        if not path.is_file():
            return

        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        self.pdf_hash = raw.get("pdf_hash", self.pdf_hash)
        self.highlights = [Highlight(**h) for h in raw.get("highlights", [])]
        self.sticky_notes = [StickyNote(**n) for n in raw.get("sticky_notes", [])]
        self.page_notes = [PageNote(**n) for n in raw.get("page_notes", [])]
        self.bookmarks = [Bookmark(**b) for b in raw.get("bookmarks", [])]

    def save(self) -> None:
        """Write all annotations to the sidecar JSON file."""
        payload = {
            "pdf_path": str(self.pdf_path),
            "pdf_hash": self.pdf_hash,
            "bookmarks": [asdict(b) for b in self.bookmarks],
            "page_notes": [asdict(n) for n in self.page_notes],
            "sticky_notes": [asdict(n) for n in self.sticky_notes],
            "highlights": [asdict(h) for h in self.highlights],
        }
        self.sidecar_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_highlight(
        self,
        page: int,
        rects: list[list[float]],
        color: str = "yellow",
        text: str = "",
    ) -> Highlight:
        h = Highlight(page=page, rects=rects, color=color, text=text)
        self.highlights.append(h)
        return h

    def add_sticky_note(
        self,
        page: int,
        x: float,
        y: float,
        content: str,
        color: str = "yellow",
    ) -> StickyNote:
        note = StickyNote(page=page, x=x, y=y, content=content, color=color)
        self.sticky_notes.append(note)
        return note

    def get_page_note(self, page: int) -> PageNote | None:
        for note in self.page_notes:
            if note.page == page:
                return note
        return None

    def set_page_note(self, page: int, content: str) -> PageNote:
        existing = self.get_page_note(page)
        if existing:
            existing.content = content
            existing.updated = _now_iso()
            return existing
        note = PageNote(page=page, content=content)
        self.page_notes.append(note)
        return note

    def add_bookmark(self, page: int, title: str = "") -> Bookmark:
        for bm in self.bookmarks:
            if bm.page == page:
                if title:
                    bm.title = title
                return bm
        if not title:
            title = f"Page {page + 1}"
        bm = Bookmark(page=page, title=title)
        self.bookmarks.append(bm)
        return bm

    def remove_bookmark(self, page: int) -> None:
        self.bookmarks = [b for b in self.bookmarks if b.page != page]

    def highlights_for_page(self, page: int) -> list[Highlight]:
        return [h for h in self.highlights if h.page == page]

    def sticky_notes_for_page(self, page: int) -> list[StickyNote]:
        return [n for n in self.sticky_notes if n.page == page]

    def search(self, query: str) -> dict[str, list[Any]]:
        q = query.lower().strip()
        if not q:
            return {"highlights": [], "sticky_notes": [], "page_notes": []}

        return {
            "highlights": [h for h in self.highlights if q in h.text.lower()],
            "sticky_notes": [n for n in self.sticky_notes if q in n.content.lower()],
            "page_notes": [n for n in self.page_notes if q in n.content.lower()],
        }
