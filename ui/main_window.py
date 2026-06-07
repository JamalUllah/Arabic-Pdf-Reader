# main_window.py — Main application window; wires UI to core logic.
# ---------------------------------------------------------------------------
# Fluent three-pane layout:
#   AppHeader (64px) → ReaderToolbar (56px) → Sidebar (left) + DocumentViewport

from __future__ import annotations

import sys
import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.annotation_store import AnnotationStore
from core.ocr_service import OcrCache, OcrResult, check_tesseract_installed, run_ocr_on_image
from core.pdf_document import PdfDocument
from ui.app_header import AppHeader
from ui.empty_state import EmptyState
from ui.fluent_theme import build_stylesheet
from ui.note_dialog import BookmarkTitleDialog, GoToPageDialog, PageNoteDialog
from ui.pdf_viewer import PdfViewer, ToolMode
from ui.sidebar import Sidebar
from ui.toolbar import ReaderToolbar
from ui.widgets import DocumentViewport

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RECENT_FILE = DATA_DIR / "recent.json"
OCR_CACHE_DIR = DATA_DIR / "ocr_cache"

# Constants for native window event handling (Windows-specific)
if sys.platform == "win32":
    import ctypes
    from ctypes.wintypes import MSG

    HT_LEFT = 10
    HT_RIGHT = 11
    HT_TOP = 12
    HT_TOPLEFT = 13
    HT_TOPRIGHT = 14
    HT_BOTTOM = 15
    HT_BOTTOMLEFT = 16
    HT_BOTTOMRIGHT = 17


class OcrWorker(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, pdf: PdfDocument, page_index: int, cache: OcrCache, pdf_hash: str) -> None:
        super().__init__()
        self._pdf = pdf
        self._page_index = page_index
        self._cache = cache
        self._pdf_hash = pdf_hash

    @Slot()
    def run_ocr(self) -> None:
        try:
            self.progress.emit(f"OCR page {self._page_index + 1}...")
            pil_image = self._pdf.render_page_pil(self._page_index, zoom=2.0)
            words = run_ocr_on_image(pil_image, language="ara")
            result = OcrResult(page_index=self._page_index, words=words, language="ara")
            self._cache.save(self._pdf_hash, result)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class OcrAllPagesWorker(QObject):
    """Runs OCR on all pages of a PDF in a background thread."""

    finished = Signal()
    error = Signal(str)
    page_finished = Signal(int)  # 1-based page number
    progress_text = Signal(str)

    def __init__(self, pdf: PdfDocument, cache: OcrCache, pdf_hash: str) -> None:
        super().__init__()
        self._pdf = pdf
        self._cache = cache
        self._pdf_hash = pdf_hash
        self._is_cancelled = False

    @Slot()
    def run(self) -> None:
        """Loop through all pages and run OCR if not cached."""
        try:
            total_pages = self._pdf.page_count
            for i in range(total_pages):
                if self._is_cancelled:
                    break
                self.progress_text.emit(f"OCR page {i + 1} / {total_pages}")
                if not self._cache.has(self._pdf_hash, i):
                    pil = self._pdf.render_page_pil(i, zoom=2.0)
                    words = run_ocr_on_image(pil, language="ara")
                    self._cache.save(self._pdf_hash, OcrResult(page_index=i, words=words))
                self.page_finished.emit(i + 1)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()  # Ensure finished is always emitted for cleanup

    @Slot()
    def cancel(self) -> None:
        """Signal from UI to stop the OCR loop."""
        self._is_cancelled = True


class MainWindow(QMainWindow):
    """Top-level Fluent Design PDF reader window."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Reader")
        self.resize(1280, 860)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setStyleSheet(build_stylesheet())
        self.menuBar().hide()

        self._pdf = PdfDocument()
        self._annotations: AnnotationStore | None = None
        self._ocr_cache = OcrCache(OCR_CACHE_DIR)
        self.border_width = 8  # For hit-testing the resize handles

        # Background OCR state — initialized here so signal handlers never hit AttributeError
        self._thread = None
        self._worker = None
        self._ocr_all_thread = None
        self._ocr_all_worker = None
        self._ocr_progress_dialog = None

        # --- Shell layout ---
        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self._header = AppHeader(self)
        shell_layout.addWidget(self._header)

        self._toolbar = ReaderToolbar(self)
        shell_layout.addWidget(self._toolbar)

        content = QWidget()
        content_row = QHBoxLayout(content)
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        self._sidebar = Sidebar(go_to_page_fn=self.go_to_page, parent=self)
        content_row.addWidget(self._sidebar)

        viewport = DocumentViewport()
        viewport_layout = QVBoxLayout(viewport)
        viewport_layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._empty = EmptyState()
        self._viewer = PdfViewer()
        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._viewer)
        self._stack.setCurrentWidget(self._empty)
        viewport_layout.addWidget(self._stack)
        content_row.addWidget(viewport, stretch=1)

        shell_layout.addWidget(content, stretch=1)
        self.setCentralWidget(shell)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Open a PDF to begin reading.")

        self._wire_signals()
        self._wire_shortcuts()
 
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        QTimer.singleShot(100, self._check_tesseract_on_startup)

    def _show_message_box(self, icon: QMessageBox.Icon, title: str, text: str) -> None:
        """Create and show a message box, resetting the stylesheet to ensure readability."""
        dlg = QMessageBox(self)
        dlg.setIcon(icon)
        dlg.setWindowTitle(title)
        dlg.setText(text)
        dlg.setStyleSheet("")  # Reset to default system style
        dlg.exec()

    def _check_tesseract_on_startup(self) -> None:
        """Check for Tesseract after UI is shown, so it doesn't block startup."""
        ok, msg = check_tesseract_installed()
        if not ok:
            self._show_message_box(QMessageBox.Icon.Warning, "Tesseract not found", msg)

    def nativeEvent(self, eventType, message):
        """Handle native Windows events to enable resizing and snapping."""
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            msg = MSG.from_address(message.__int__())
            if msg.message == 0x0084:  # WM_NCHITTEST
                # Get mouse position in screen coordinates
                x = ctypes.c_short(msg.lParam & 0xFFFF).value
                y = ctypes.c_short(msg.lParam >> 16).value
                rect = self.geometry()

                # Check corners first due to overlap
                if x >= rect.left() and x < rect.left() + self.border_width:
                    if y >= rect.top() and y < rect.top() + self.border_width:
                        return True, HT_TOPLEFT
                    if y <= rect.bottom() and y > rect.bottom() - self.border_width:
                        return True, HT_BOTTOMLEFT

                if x <= rect.right() and x > rect.right() - self.border_width:
                    if y >= rect.top() and y < rect.top() + self.border_width:
                        return True, HT_TOPRIGHT
                    if y <= rect.bottom() and y > rect.bottom() - self.border_width:
                        return True, HT_BOTTOMRIGHT

                # Check edges
                if x >= rect.left() and x < rect.left() + self.border_width:
                    return True, HT_LEFT
                if x <= rect.right() and x > rect.right() - self.border_width:
                    return True, HT_RIGHT
                if y >= rect.top() and y < rect.top() + self.border_width:
                    return True, HT_TOP
                if y <= rect.bottom() and y > rect.bottom() - self.border_width:
                    return True, HT_BOTTOM

        return super().nativeEvent(eventType, message)

    def resizeEvent(self, event) -> None:
        """Handle window resize to create a responsive layout."""
        super().resizeEvent(event)

        # Threshold for a "narrow" window where the sidebar should be hidden.
        # Sidebar is 320px wide. Let's give the viewer at least ~500px.
        narrow_width_threshold = 850

        if self.width() < narrow_width_threshold:
            if self._sidebar.isVisible():
                self._sidebar.hide()
                self._toolbar.set_sidebar_visible(False)
        else:
            if not self._sidebar.isVisible():
                self._sidebar.show()
                self._toolbar.set_sidebar_visible(True)

    def _wire_signals(self) -> None:
        self._header.back_clicked.connect(self._on_back)
        self._empty.open_clicked.connect(self.on_open_pdf)

        self._toolbar.open_clicked.connect(self.on_open_pdf)
        self._toolbar.prev_clicked.connect(self.on_prev_page)
        self._toolbar.next_clicked.connect(self.on_next_page)
        self._toolbar.go_to_page_requested.connect(self.on_go_to_page_1based)
        self._toolbar.zoom_changed.connect(self._viewer.set_zoom)
        self._toolbar.ocr_page_clicked.connect(self.on_ocr_page)
        self._toolbar.ocr_all_clicked.connect(self.on_ocr_all)
        self._toolbar.highlight_mode_toggled.connect(self._on_highlight_mode)
        self._toolbar.note_mode_toggled.connect(self._on_note_mode)
        self._toolbar.bookmark_clicked.connect(self.on_add_bookmark)
        self._toolbar.page_note_clicked.connect(self.on_page_note)
        self._toolbar.search_requested.connect(self.on_search)
        self._toolbar.sidebar_toggle_clicked.connect(self._toggle_sidebar)
        self._toolbar.rotate_clicked.connect(self._viewer.rotate_cw)
        self._toolbar.layers_clicked.connect(self._sidebar.show_highlights_tab)
        self._toolbar.print_clicked.connect(self._on_print_stub)
        self._toolbar.view_mode_changed.connect(self._on_view_mode)

        self._viewer.status_message.connect(self._status.showMessage)
        self._viewer.annotation_changed.connect(self._save_annotations)

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, self.on_open_pdf)
        QShortcut(QKeySequence("Ctrl+G"), self, self.on_go_to_page_dialog)
        QShortcut(QKeySequence("Ctrl+D"), self, self.on_add_bookmark)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.on_prev_page)
        QShortcut(QKeySequence("Ctrl+Right"), self, self.on_next_page)
        QShortcut(QKeySequence("Ctrl+F"), self, self._on_find)

    def _toggle_sidebar(self) -> None:
        visible = not self._sidebar.isVisible()
        self._sidebar.setVisible(visible)
        self._toolbar.set_sidebar_visible(visible)

    def _on_find(self) -> None:
        self._toolbar.prompt_search()
        self._sidebar.focus_find()

    def _on_print_stub(self) -> None:
        self._show_message_box(QMessageBox.Icon.Information, "Print", "Print support is coming in a future version.")

    def _on_view_mode(self, mode: str) -> None:
        if mode in ("two", "continuous"):
            self._status.showMessage(f"{mode.title()} view — showing single page for now (full layout coming soon).")

    def _cancel_ocr_threads(self) -> None:
        """Signal any running OCR workers to stop before closing the document."""
        if self._ocr_all_worker is not None:
            self._ocr_all_worker.cancel()
        if self._ocr_progress_dialog is not None:
            self._ocr_progress_dialog.close()
            self._ocr_progress_dialog = None

    def _on_back(self) -> None:
        if self._pdf.is_open:
            self._cancel_ocr_threads()
            self._save_annotations()
            self._pdf.close()
            self._annotations = None
            self._viewer.set_pdf(None)
            self._sidebar.set_pdf(None)
            self._sidebar.refresh_from_store(None)
            self._header.set_filename("")
            self._stack.setCurrentWidget(self._empty)
            self._status.showMessage("Document closed.")
        else:
            self.close()

    def closeEvent(self, event) -> None:
        self._cancel_ocr_threads()
        self._save_annotations()
        if self._pdf.is_open:
            self._pdf.close()
        super().closeEvent(event)

    def on_open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if not path:
            return

        try:
            self._pdf.close()
            self._pdf.open(path)
        except (FileNotFoundError, RuntimeError) as exc:
            self._show_message_box(QMessageBox.Icon.Critical, "Cannot open PDF", str(exc))
            return

        pdf_hash = self._pdf.file_hash()
        self._annotations = AnnotationStore(path, pdf_hash=pdf_hash)
        try:
            self._annotations.load()
        except Exception:
            # Corrupted or unreadable sidecar — start fresh rather than crashing
            self._annotations = AnnotationStore(path, pdf_hash=pdf_hash)

        self._viewer.set_pdf(self._pdf)
        self._viewer.set_annotations(self._annotations)
        # Pass pdf to refresh_from_store so it renders thumbnails once; skip set_pdf() to avoid double render
        self._sidebar.refresh_from_store(self._annotations, self._pdf)

        self._stack.setCurrentWidget(self._viewer)
        self._viewer.show_page(0)
        self._toolbar.set_page_info(1, self._pdf.page_count)
        self._header.set_filename(Path(path).name)
        self._status.showMessage(f"Opened: {Path(path).name} ({self._pdf.page_count} pages)")

        self._add_recent_file(path)
        self._load_ocr_for_current_page()

    def _add_recent_file(self, path: str) -> None:
        recent: list[str] = []
        try:
            if RECENT_FILE.is_file():
                recent = json.loads(RECENT_FILE.read_text(encoding="utf-8"))
            if path in recent:
                recent.remove(path)
            recent.insert(0, path)
            recent = recent[:10]
            RECENT_FILE.write_text(json.dumps(recent, indent=2), encoding="utf-8")
        except Exception:
            pass  # Never let a broken recent-file list block opening a PDF

    def on_prev_page(self) -> None:
        if not self._pdf.is_open:
            return
        self.go_to_page(self._viewer.current_page() - 1)

    def on_next_page(self) -> None:
        if not self._pdf.is_open:
            return
        self.go_to_page(self._viewer.current_page() + 1)

    def on_go_to_page_1based(self, page_1based: int) -> None:
        self.go_to_page(page_1based - 1)

    def go_to_page(self, page_index: int) -> None:
        if not self._pdf.is_open:
            return
        page_index = max(0, min(page_index, self._pdf.page_count - 1))
        self._viewer.show_page(page_index)
        self._toolbar.set_page_info(page_index + 1, self._pdf.page_count)
        self._sidebar.highlight_current_page(page_index)
        self._load_ocr_for_current_page()

    def on_go_to_page_dialog(self) -> None:
        if not self._pdf.is_open:
            return
        dlg = GoToPageDialog(
            parent=self,
            current_page=self._viewer.current_page() + 1,
            total_pages=self._pdf.page_count,
        )
        if dlg.exec():
            self.on_go_to_page_1based(dlg.page_number())

    def _load_ocr_for_current_page(self) -> None:
        if not self._pdf.is_open:
            return
        page = self._viewer.current_page()
        pdf_hash = self._pdf.file_hash()
        cached = self._ocr_cache.load(pdf_hash, page)
        if cached:
            self._viewer.set_ocr_words(cached.words)
        else:
            self._viewer.set_ocr_words([])

    def on_ocr_page(self) -> None:
        if not self._pdf.is_open:
            return
        ok, msg = check_tesseract_installed()
        if not ok:
            self._show_message_box(QMessageBox.Icon.Warning, "Tesseract not found", msg)
            return
        self._run_ocr_background(self._viewer.current_page())

    def on_ocr_all(self) -> None:
        if not self._pdf.is_open:
            return
        ok, msg = check_tesseract_installed()
        if not ok:
            self._show_message_box(QMessageBox.Icon.Warning, "Tesseract not found", msg)
            return

        self._ocr_progress_dialog = QProgressDialog(
            "Preparing to OCR all pages...", "Cancel", 0, self._pdf.page_count, self
        )
        self._ocr_progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._ocr_progress_dialog.setStyleSheet("")  # Reset style for readability
        self._ocr_progress_dialog.show()

        pdf_hash = self._pdf.file_hash()
        self._ocr_all_thread = QThread()
        self._ocr_all_worker = OcrAllPagesWorker(self._pdf, self._ocr_cache, pdf_hash)
        self._ocr_all_worker.moveToThread(self._ocr_all_thread)

        self._ocr_all_thread.started.connect(self._ocr_all_worker.run)
        self._ocr_progress_dialog.canceled.connect(self._ocr_all_worker.cancel)

        self._ocr_all_worker.page_finished.connect(self._on_ocr_all_page_finished)
        self._ocr_all_worker.progress_text.connect(self._on_ocr_all_progress_text)
        self._ocr_all_worker.finished.connect(self._on_ocr_all_finished)
        self._ocr_all_worker.error.connect(self._on_ocr_all_error)

        # Auto-cleanup
        self._ocr_all_worker.finished.connect(self._ocr_all_thread.quit)
        self._ocr_all_worker.finished.connect(self._ocr_all_worker.deleteLater)
        self._ocr_all_thread.finished.connect(self._ocr_all_thread.deleteLater)

        self._ocr_all_thread.start()

    def _on_ocr_all_page_finished(self, page_num: int) -> None:
        """Update progress dialog value when a page is done."""
        if self._ocr_progress_dialog:
            self._ocr_progress_dialog.setValue(page_num)

    def _on_ocr_all_progress_text(self, text: str) -> None:
        """Update progress dialog label text."""
        if self._ocr_progress_dialog:
            self._ocr_progress_dialog.setLabelText(text)

    def _on_ocr_all_error(self, message: str) -> None:
        """Called when the OCR-all worker encounters an error on any page."""
        self._show_message_box(QMessageBox.Icon.Critical, "OCR failed", message)

    def _on_ocr_all_finished(self) -> None:
        """Called when the worker loop completes or is cancelled."""
        if self._ocr_progress_dialog and not self._ocr_progress_dialog.wasCanceled():
            self._status.showMessage("OCR for all pages complete.")
            self._load_ocr_for_current_page()
            self._sidebar.refresh_from_store(self._annotations, self._pdf)
        else:
            self._status.showMessage("OCR for all pages cancelled.")
        self._ocr_progress_dialog = None

    def _run_ocr_background(self, page_index: int) -> None:
        pdf_hash = self._pdf.file_hash()
        if self._ocr_cache.has(pdf_hash, page_index):
            cached = self._ocr_cache.load(pdf_hash, page_index)
            if cached:
                self._viewer.set_ocr_words(cached.words)
                self._status.showMessage(f"OCR loaded from cache ({len(cached.words)} words)")
            return

        self._thread = QThread()
        self._worker = OcrWorker(self._pdf, page_index, self._ocr_cache, pdf_hash)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_ocr)
        self._worker.finished.connect(self._on_ocr_finished)
        self._worker.error.connect(self._on_ocr_error)
        self._worker.progress.connect(self._status.showMessage)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_ocr_finished(self, result: OcrResult) -> None:
        if result.page_index == self._viewer.current_page():
            self._viewer.set_ocr_words(result.words)
        self._status.showMessage(f"OCR done — {len(result.words)} words on page {result.page_index + 1}")

    def _on_ocr_error(self, message: str) -> None:
        self._show_message_box(QMessageBox.Icon.Critical, "OCR failed", message)

    def _on_highlight_mode(self, enabled: bool) -> None:
        self._viewer.set_tool_mode(ToolMode.HIGHLIGHT if enabled else ToolMode.NAVIGATE)
        if enabled:
            self._status.showMessage("Highlight mode — drag to highlight text")

    def _on_note_mode(self, enabled: bool) -> None:
        self._viewer.set_tool_mode(ToolMode.STICKY_NOTE if enabled else ToolMode.NAVIGATE)
        if enabled:
            self._status.showMessage("Sticky note mode — click on the page")

    def on_page_note(self) -> None:
        if not self._pdf.is_open or not self._annotations:
            return
        page = self._viewer.current_page()
        existing = self._annotations.get_page_note(page)
        initial = existing.content if existing else ""
        dlg = PageNoteDialog(parent=self, page_number=page + 1, initial_text=initial)
        if dlg.exec():
            self._annotations.set_page_note(page, dlg.text())
            self._save_annotations()
            self._sidebar.refresh_from_store(self._annotations, self._pdf)
            self._sidebar.show_highlights_tab()
            self._status.showMessage(f"Page note saved for page {page + 1}")

    def on_add_bookmark(self) -> None:
        if not self._pdf.is_open or not self._annotations:
            return
        page = self._viewer.current_page()
        dlg = BookmarkTitleDialog(parent=self, page_number=page + 1)
        if not dlg.exec():
            return  # User cancelled — do not add or modify bookmark
        title = dlg.title()
        self._annotations.add_bookmark(page, title)
        self._save_annotations()
        self._sidebar.refresh_from_store(self._annotations, self._pdf)
        self._sidebar.show_bookmarks_tab()
        self._status.showMessage(f"Bookmark added: {title}")

    def on_search(self, query: str) -> None:
        if not self._annotations or not query:
            self._sidebar.refresh_from_store(self._annotations, self._pdf)
            return
        self._sidebar.show_search_results(self._annotations, query)
        self._status.showMessage(f"Search results for: {query}")

    def _save_annotations(self) -> None:
        if self._annotations:
            self._annotations.save()