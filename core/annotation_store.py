# annotation_store.py — Load/save highlights, notes, and bookmarks.
# ---------------------------------------------------------------------------
# Called by: ui/main_window.py, ui/sidebar.py
#
# Data is stored in a "sidecar" JSON file next to the PDF:
#   mybook.pdf  →  mybook.pdf.apr.json
#
# apr = Arabic PDF Reader
#
# Library reference: see imports_guide.py in the project root.

from __future__ import annotations

# --- json ---
# Save/load sidecar file yourbook.pdf.apr.json with highlights, notes, bookmarks.
import json

# --- dataclasses ---
# @dataclass builds Highlight, StickyNote, PageNote, Bookmark data classes.
# field(default_factory=...) sets dynamic defaults (e.g. timestamp at creation).
# asdict() turns a dataclass into a dict before json.dump.
from dataclasses import dataclass, field, asdict

# --- datetime ---
# Record when notes/bookmarks were created or updated (ISO format strings).
from datetime import datetime, timezone

# --- pathlib.Path ---
# Paths to PDF and sidecar JSON: pdf_path.with_suffix(".pdf.apr.json")
from pathlib import Path

# --- typing.Any ---
# Type hint meaning "any JSON-compatible value" in search() return dict.
from typing import Any


def _now_iso() -> str:
    """Current UTC time as ISO string for JSON timestamps."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Highlight:
    """A colored highlight region on one page."""

    page: int  # 0-based page index
    rects: list[list[float]]  # [[x0,y0,x1,y1], ...] normalized 0-1
    color: str = "yellow"
    text: str = ""
    created: str = field(default_factory=_now_iso)


@dataclass
class StickyNote:
    """Adobe-style sticky note pinned to a position on a page."""

    page: int
    x: float  # normalized 0-1
    y: float
    content: str = ""
    color: str = "yellow"
    created: str = field(default_factory=_now_iso)


@dataclass
class PageNote:
    """Free-form note attached to a page number (not a pin on the page)."""

    page: int
    content: str = ""
    updated: str = field(default_factory=_now_iso)


@dataclass
class Bookmark:
    """Bookmark pointing to a page."""

    page: int
    title: str = ""
    created: str = field(default_factory=_now_iso)


class AnnotationStore:
    """
    Holds all user annotations for one PDF and saves them to JSON.

    Usage pattern:
        store = AnnotationStore(pdf_path)
        store.load()
        store.add_bookmark(5, "Important chapter")
        store.save()
    """

    def __init__(self, pdf_path: Path | str, pdf_hash: str = "") -> None:
        self.pdf_path = Path(pdf_path)
        self.pdf_hash = pdf_hash
        self.highlights: list[Highlight] = []
        self.sticky_notes: list[StickyNote] = []
        self.page_notes: list[PageNote] = []
        self.bookmarks: list[Bookmark] = []

    @property
    def sidecar_path(self) -> Path:
        """Path to the .apr.json file for this PDF."""
        return self.pdf_path.with_suffix(self.pdf_path.suffix + ".apr.json")

    def load(self) -> None:
        """Load annotations from disk if the sidecar file exists."""
        path = self.sidecar_path
        if not path.is_file():
            return

        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return  # Corrupted JSON — start with empty annotations

        self.pdf_hash = raw.get("pdf_hash", self.pdf_hash)

        # Helper: safely construct a dataclass, ignoring unknown keys and skipping bad entries
        def _safe_load(cls, items):
            import dataclasses
            valid_keys = {f.name for f in dataclasses.fields(cls)}
            result = []
            for item in items:
                try:
                    filtered = {k: v for k, v in item.items() if k in valid_keys}
                    result.append(cls(**filtered))
                except Exception:
                    pass  # Skip malformed entries
            return result

        self.highlights = _safe_load(Highlight, raw.get("highlights", []))
        self.sticky_notes = _safe_load(StickyNote, raw.get("sticky_notes", []))
        self.page_notes = _safe_load(PageNote, raw.get("page_notes", []))
        self.bookmarks = _safe_load(Bookmark, raw.get("bookmarks", []))

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
        """Add a highlight and return the new Highlight object."""
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
        """Add a sticky note at normalized (x, y) on a page."""
        note = StickyNote(page=page, x=x, y=y, content=content, color=color)
        self.sticky_notes.append(note)
        return note

    def get_page_note(self, page: int) -> PageNote | None:
        """Get the page note for a page, or None."""
        for note in self.page_notes:
            if note.page == page:
                return note
        return None

    def set_page_note(self, page: int, content: str) -> PageNote:
        """Create or update the page-level note for a page."""
        existing = self.get_page_note(page)
        if existing:
            existing.content = content
            existing.updated = _now_iso()
            return existing
        note = PageNote(page=page, content=content)
        self.page_notes.append(note)
        return note

    def add_bookmark(self, page: int, title: str = "") -> Bookmark:
        """Add a bookmark (does not duplicate same page)."""
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
        """Remove bookmark for a page if it exists."""
        self.bookmarks = [b for b in self.bookmarks if b.page != page]

    def highlights_for_page(self, page: int) -> list[Highlight]:
        return [h for h in self.highlights if h.page == page]

    def sticky_notes_for_page(self, page: int) -> list[StickyNote]:
        return [n for n in self.sticky_notes if n.page == page]

    def search(self, query: str) -> dict[str, list[Any]]:
        """
        Search highlights, sticky notes, and page notes by keyword.

        Returns:
            dict with keys: highlights, sticky_notes, page_notes
        """
        q = query.lower().strip()
        if not q:
            return {"highlights": [], "sticky_notes": [], "page_notes": []}

        return {
            "highlights": [h for h in self.highlights if q in h.text.lower()],
            "sticky_notes": [n for n in self.sticky_notes if q in n.content.lower()],
            "page_notes": [n for n in self.page_notes if q in n.content.lower()],
        }