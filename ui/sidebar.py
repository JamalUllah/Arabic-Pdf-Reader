# sidebar.py — Left navigation panel (320px) with Pages, Bookmarks, Notes, Details.
# ---------------------------------------------------------------------------

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.annotation_store import AnnotationStore, Bookmark, Highlight, PageNote, StickyNote
from core.pdf_document import PdfDocument
from core.text_layer import shape_arabic_for_display


class Sidebar(QWidget):
    """
    Left docked sidebar: Pages | Bookmarks | Notes | Details.

    Width 320px, light gray Fluent background.
    """

    SIDEBAR_WIDTH = 320

    def __init__(self, go_to_page_fn: Callable[[int], None], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarPanel")
        self.setFixedWidth(self.SIDEBAR_WIDTH)

        self._go_to_page = go_to_page_fn
        self._pdf: PdfDocument | None = None
        self._store: AnnotationStore | None = None
        self._current_page = 0
        self._file_header_expanded = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- Pages tab (thumbnails) ---
        self._pages_list = QListWidget()
        self._pages_list.setIconSize(QSize(80, 110))
        self._pages_list.itemClicked.connect(self._on_page_thumb_clicked)
        self._tabs.addTab(self._pages_list, "Pages")

        # --- Bookmarks tab ---
        bookmarks_container = QWidget()
        bm_layout = QVBoxLayout(bookmarks_container)
        bm_layout.setContentsMargins(0, 8, 0, 8)

        file_header_row = QHBoxLayout()
        self._file_header_btn = QPushButton("▼")
        self._file_header_btn.setFixedWidth(28)
        self._file_header_btn.setStyleSheet("border:none; background:transparent;")
        self._file_header_btn.clicked.connect(self._toggle_file_header)
        file_header_row.addWidget(self._file_header_btn)
        self._file_title = QLabel("No file")
        self._file_title.setObjectName("SidebarSectionTitle")
        file_header_row.addWidget(self._file_title)
        file_header_row.addStretch()
        bm_layout.addLayout(file_header_row)

        self._bookmarks_list = QListWidget()
        self._bookmarks_list.itemClicked.connect(self._on_bookmark_clicked)
        bm_layout.addWidget(self._bookmarks_list)
        self._tabs.addTab(bookmarks_container, "Bookmarks")

        # --- Notes tab (page notes + sticky + highlights) ---
        self._notes_list = QListWidget()
        self._notes_list.itemDoubleClicked.connect(self._on_item_clicked)
        self._tabs.addTab(self._notes_list, "Notes")

        # --- Details tab ---
        details_scroll = QScrollArea()
        details_scroll.setWidgetResizable(True)
        self._details_widget = QWidget()
        self._details_form = QFormLayout(self._details_widget)
        self._details_form.setContentsMargins(16, 16, 16, 16)
        self._details_form.setSpacing(10)
        details_scroll.setWidget(self._details_widget)
        self._tabs.addTab(details_scroll, "Details")

        self._detail_labels: dict[str, QLabel] = {}
        for key in ("File", "Pages", "Path", "OCR status", "Bookmarks", "Notes", "Highlights"):
            val = QLabel("—")
            val.setWordWrap(True)
            val.setStyleSheet("color: #5F6368;")
            self._details_form.addRow(f"{key}:", val)
            self._detail_labels[key] = val

    def _toggle_file_header(self) -> None:
        self._file_header_expanded = not self._file_header_expanded
        self._file_header_btn.setText("▼" if self._file_header_expanded else "▶")
        self._bookmarks_list.setVisible(self._file_header_expanded)

    def set_pdf(self, pdf: PdfDocument | None) -> None:
        self._pdf = pdf
        self._refresh_pages_tab()

    def set_current_page(self, page_index: int) -> None:
        self._current_page = page_index
        for i in range(self._pages_list.count()):
            item = self._pages_list.item(i)
            if item and int(item.data(Qt.ItemDataRole.UserRole)) == page_index:
                self._pages_list.setCurrentItem(item)
                break

    def _refresh_pages_tab(self) -> None:
        self._pages_list.clear()
        if not self._pdf or not self._pdf.is_open:
            return
        for i in range(self._pdf.page_count):
            try:
                png, w, h = self._pdf.render_page(i, zoom=0.15)
                img = QImage.fromData(png, "PNG")
                pix = QPixmap.fromImage(img)
                icon = QIcon(pix)
            except Exception:
                icon = QIcon()
            item = QListWidgetItem(icon, f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._pages_list.addItem(item)

    def _on_page_thumb_clicked(self, item: QListWidgetItem) -> None:
        page = item.data(Qt.ItemDataRole.UserRole)
        if page is not None:
            self._go_to_page(int(page))

    def _on_bookmark_clicked(self, item: QListWidgetItem) -> None:
        page = item.data(Qt.ItemDataRole.UserRole)
        if page is not None:
            self._go_to_page(int(page))

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        page = item.data(Qt.ItemDataRole.UserRole)
        if page is not None:
            self._go_to_page(int(page))

    def refresh_from_store(self, store: AnnotationStore | None, pdf: PdfDocument | None = None) -> None:
        self._store = store
        if pdf:
            self._pdf = pdf
            self._refresh_pages_tab()

        self._bookmarks_list.clear()
        self._notes_list.clear()

        if not store or not self._pdf or not self._pdf.is_open:
            self._file_title.setText("No file")
            self._update_details(None)
            return

        name = self._pdf.file_path.name if self._pdf.file_path else "Document"
        self._file_title.setText(name)

        for bm in sorted(store.bookmarks, key=lambda b: b.page):
            self._add_bookmark_item(bm)

        for note in sorted(store.page_notes, key=lambda n: n.page):
            self._add_note_item("Page note", note.page, note.content)
        for note in sorted(store.sticky_notes, key=lambda n: n.page):
            self._add_note_item("Sticky", note.page, note.content)
        for hl in sorted(store.highlights, key=lambda h: h.page):
            preview = hl.text or f"{hl.color} highlight"
            self._add_note_item("Highlight", hl.page, preview)

        self._update_details(store)

    def _add_bookmark_item(self, bm: Bookmark) -> None:
        dots_count = max(4, 24 - len(bm.title))
        text = f"{bm.title}{'.' * dots_count}{bm.page + 1}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, bm.page)
        self._bookmarks_list.addItem(item)

    def _add_note_item(self, kind: str, page: int, content: str) -> None:
        preview = content[:50] + ("..." if len(content) > 50 else "")
        display = shape_arabic_for_display(preview) if preview else "(empty)"
        item = QListWidgetItem(f"[{kind}] p.{page + 1}: {display}")
        item.setData(Qt.ItemDataRole.UserRole, page)
        self._notes_list.addItem(item)

    def _update_details(self, store: AnnotationStore | None) -> None:
        if not self._pdf or not self._pdf.is_open:
            for lbl in self._detail_labels.values():
                lbl.setText("—")
            return

        path = str(self._pdf.file_path) if self._pdf.file_path else "—"
        self._detail_labels["File"].setText(self._pdf.file_path.name if self._pdf.file_path else "—")
        self._detail_labels["Pages"].setText(str(self._pdf.page_count))
        self._detail_labels["Path"].setText(path)
        scanned = sum(1 for i in range(self._pdf.page_count) if self._pdf.is_scanned_page(i))
        self._detail_labels["OCR status"].setText(
            f"{scanned} scanned page(s) may need OCR" if scanned else "Text layers detected"
        )
        if store:
            self._detail_labels["Bookmarks"].setText(str(len(store.bookmarks)))
            self._detail_labels["Notes"].setText(str(len(store.page_notes) + len(store.sticky_notes)))
            self._detail_labels["Highlights"].setText(str(len(store.highlights)))

    def show_search_results(self, store: AnnotationStore, query: str) -> None:
        self._notes_list.clear()
        results = store.search(query)
        for hl in results["highlights"]:
            self._add_note_item("Highlight", hl.page, hl.text or hl.color)
        for note in results["sticky_notes"]:
            self._add_note_item("Sticky", note.page, note.content)
        for note in results["page_notes"]:
            self._add_note_item("Page note", note.page, note.content)
        self._tabs.setCurrentIndex(2)  # Notes tab

    def show_highlights_tab(self) -> None:
        self._tabs.setCurrentIndex(2)

    def show_bookmarks_tab(self) -> None:
        self._tabs.setCurrentIndex(1)

    def focus_find(self) -> None:
        self._tabs.setCurrentIndex(2)

    def highlight_current_page(self, page_index: int) -> None:
        self.set_current_page(page_index)
