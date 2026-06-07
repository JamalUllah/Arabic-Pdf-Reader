from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)

from ui.widgets import FluentToolButton, IconToolButton, ToolbarDivider


class ReaderToolbar(QWidget):
    open_clicked = Signal()
    prev_clicked = Signal()
    next_clicked = Signal()
    go_to_page_requested = Signal(int)
    zoom_changed = Signal(float)
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    ocr_page_clicked = Signal()
    ocr_all_clicked = Signal()
    highlight_mode_toggled = Signal(bool)
    note_mode_toggled = Signal(bool)
    bookmark_clicked = Signal()
    page_note_clicked = Signal()
    search_requested = Signal(str)
    sidebar_toggle_clicked = Signal()
    rotate_clicked = Signal()
    view_mode_changed = Signal(str)
    find_clicked = Signal()
    annotate_menu_requested = Signal()
    layers_clicked = Signal()
    print_clicked = Signal()

    _ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PrimaryToolbar")
        self.setFixedHeight(56)

        self._zoom_index = 3
        self._total_pages = 1

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 4, 12, 4)
        row.setSpacing(8)

        find_btn = FluentToolButton("🔍", "Find")
        find_btn.clicked.connect(self._on_find_click)
        row.addWidget(find_btn)

        self._annotate_btn = QToolButton()
        self._annotate_btn.setText("✎\nAnnotate")
        self._annotate_btn.setToolTip("Annotate")
        self._annotate_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._annotate_btn.setStyleSheet("text-align: center; font-size: 11px; min-width: 52px;")
        annotate_menu = QMenu(self)
        annotate_menu.addAction("Highlight", lambda: self._activate_highlight(True))
        annotate_menu.addAction("Sticky Note", lambda: self._activate_note(True))
        annotate_menu.addAction("Page Note", self.page_note_clicked.emit)
        annotate_menu.addAction("Add Bookmark", self.bookmark_clicked.emit)
        self._annotate_btn.setMenu(annotate_menu)
        row.addWidget(self._annotate_btn)

        clip_btn = FluentToolButton("✂", "Clip")
        clip_btn.setToolTip("OCR current page (extract text from scan)")
        clip_btn.clicked.connect(self.ocr_page_clicked.emit)
        row.addWidget(clip_btn)

        row.addWidget(ToolbarDivider())

        prev_btn = IconToolButton("‹", "Previous page")
        prev_btn.clicked.connect(self.prev_clicked.emit)
        row.addWidget(prev_btn)

        page_lbl = QLabel("Page")
        page_lbl.setStyleSheet("color: #5F6368;")
        row.addWidget(page_lbl)

        self._page_input = QLineEdit()
        self._page_input.setFixedWidth(60)
        self._page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_input.returnPressed.connect(self._on_go_pressed)
        row.addWidget(self._page_input)

        self._page_of_label = QLabel("of 1")
        self._page_of_label.setStyleSheet("color: #5F6368;")
        row.addWidget(self._page_of_label)

        next_btn = IconToolButton("›", "Next page")
        next_btn.clicked.connect(self.next_clicked.emit)
        row.addWidget(next_btn)

        row.addWidget(ToolbarDivider())

        zoom_out = IconToolButton("−", "Zoom out")
        zoom_out.clicked.connect(self._zoom_out)
        row.addWidget(zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setObjectName("ZoomLabel")
        row.addWidget(self._zoom_label)

        zoom_in = IconToolButton("+", "Zoom in")
        zoom_in.clicked.connect(self._zoom_in)
        row.addWidget(zoom_in)

        row.addWidget(ToolbarDivider())

        self._view_single = IconToolButton("▭", "Single page", checkable=True)
        self._view_single.setChecked(True)
        self._view_two = IconToolButton("▭▭", "Two page view", checkable=True)
        self._view_continuous = IconToolButton("☰", "Continuous scroll", checkable=True)
        for btn, mode in [
            (self._view_single, "single"),
            (self._view_two, "two"),
            (self._view_continuous, "continuous"),
        ]:
            btn.clicked.connect(lambda checked, m=mode: self._set_view_mode(m))
            row.addWidget(btn)

        row.addWidget(ToolbarDivider())

        rotate_btn = IconToolButton("↻", "Rotate page")
        rotate_btn.clicked.connect(self.rotate_clicked.emit)
        row.addWidget(rotate_btn)

        read_btn = IconToolButton("🔊", "Read aloud (coming soon)")
        read_btn.setEnabled(False)
        row.addWidget(read_btn)

        row.addWidget(ToolbarDivider())

        self._sidebar_btn = IconToolButton("☰", "Toggle sidebar", checkable=True)
        self._sidebar_btn.setChecked(True)
        self._sidebar_btn.clicked.connect(self.sidebar_toggle_clicked.emit)
        row.addWidget(self._sidebar_btn)

        layers_btn = IconToolButton("▦", "Highlights & layers")
        layers_btn.clicked.connect(self.layers_clicked.emit)
        row.addWidget(layers_btn)

        attach_btn = IconToolButton("📎", "OCR all pages")
        attach_btn.clicked.connect(self.ocr_all_clicked.emit)
        row.addWidget(attach_btn)

        share_btn = IconToolButton("⤴", "Open file")
        share_btn.clicked.connect(self.open_clicked.emit)
        row.addWidget(share_btn)

        print_btn = IconToolButton("🖨", "Print (coming soon)")
        print_btn.clicked.connect(self.print_clicked.emit)
        row.addWidget(print_btn)

        more_btn = QToolButton()
        more_btn.setText("⋯")
        more_btn.setToolTip("More options")
        more_btn.setFixedSize(36, 36)
        more_menu = QMenu(self)
        more_menu.addAction("Open PDF...", self.open_clicked.emit)
        more_menu.addAction("OCR This Page", self.ocr_page_clicked.emit)
        more_menu.addAction("OCR All Pages", self.ocr_all_clicked.emit)
        more_menu.addSeparator()
        more_menu.addAction("Highlight Mode", lambda: self._activate_highlight(True))
        more_menu.addAction("Sticky Note Mode", lambda: self._activate_note(True))
        more_btn.setMenu(more_menu)
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row.addWidget(more_btn)

        row.addStretch()

        self._search_input = QLineEdit(self)
        self._search_input.setPlaceholderText("Search notes and highlights...")
        self._search_input.hide()
        self._search_input.returnPressed.connect(self._on_search)

    def _activate_highlight(self, enabled: bool) -> None:
        self._highlight_active = enabled
        self.highlight_mode_toggled.emit(enabled)

    def _activate_note(self, enabled: bool) -> None:
        self.note_mode_toggled.emit(enabled)

    def _set_view_mode(self, mode: str) -> None:
        self._view_single.setChecked(mode == "single")
        self._view_two.setChecked(mode == "two")
        self._view_continuous.setChecked(mode == "continuous")
        self.view_mode_changed.emit(mode)

    def _zoom_out(self) -> None:
        if self._zoom_index > 0:
            self._zoom_index -= 1
            self._emit_zoom()

    def _zoom_in(self) -> None:
        if self._zoom_index < len(self._ZOOM_LEVELS) - 1:
            self._zoom_index += 1
            self._emit_zoom()

    def _emit_zoom(self) -> None:
        z = self._ZOOM_LEVELS[self._zoom_index]
        self._zoom_label.setText(f"{int(z * 100)}%")
        self.zoom_changed.emit(z)

    def _on_go_pressed(self) -> None:
        text = self._page_input.text().strip()
        if text.isdigit():
            self.go_to_page_requested.emit(int(text))

    def _on_search(self) -> None:
        self.search_requested.emit(self._search_input.text().strip())

    def _on_find_click(self) -> None:
        self.prompt_search()

    def get_search_query(self) -> str:
        return self._search_input.text().strip()

    def prompt_search(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        dialog = QInputDialog(self)
        dialog.setWindowTitle("Find")
        dialog.setLabelText("Search notes and highlights:")
        dialog.setStyleSheet("")
        ok = dialog.exec()
        text = dialog.textValue()

        if ok and text.strip():
            self.search_requested.emit(text.strip())

    def set_page_info(self, current_1based: int, total: int) -> None:
        self._total_pages = total
        self._page_input.setText(str(current_1based))
        self._page_of_label.setText(f"of {total}")

    def set_zoom(self, zoom: float) -> None:
        closest = min(range(len(self._ZOOM_LEVELS)), key=lambda i: abs(self._ZOOM_LEVELS[i] - zoom))
        self._zoom_index = closest
        self._zoom_label.setText(f"{int(self._ZOOM_LEVELS[self._zoom_index] * 100)}%")

    def set_highlight_mode(self, enabled: bool) -> None:
        _ = enabled

    def set_note_mode(self, enabled: bool) -> None:
        _ = enabled

    def set_sidebar_visible(self, visible: bool) -> None:
        self._sidebar_btn.setChecked(visible)

    def current_zoom(self) -> float:
        return self._ZOOM_LEVELS[self._zoom_index]
    