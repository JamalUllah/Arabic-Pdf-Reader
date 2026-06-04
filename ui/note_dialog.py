# note_dialog.py — Popup dialogs for sticky notes and go-to-page.
# ---------------------------------------------------------------------------
# Called by: ui/main_window.py, ui/pdf_viewer.py
#
# QDialog is a small popup window that blocks until the user clicks OK/Cancel.
#
# Library reference: see imports_guide.py in the project root.

from __future__ import annotations

# --- Qt ---
# Qt.LayoutDirection.RightToLeft : Arabic text flows right-to-left in QTextEdit
from PySide6.QtCore import Qt

# --- PySide6.QtWidgets ---
# QDialog         : Popup window base (StickyNote, GoToPage, Bookmark dialogs)
# QDialogButtonBox: Standard OK / Cancel button row
# QTextEdit       : Multi-line Arabic note editor
# QSpinBox        : Pick page number in GoToPageDialog
# QLineEdit       : Bookmark title input
# QFormLayout     : Label + field pairs
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)


class StickyNoteDialog(QDialog):
    """
    Dialog to create or edit a sticky note's text.

    Usage:
        dlg = StickyNoteDialog(parent=self, initial_text="...")
        if dlg.exec():          # exec() shows dialog and waits
            text = dlg.text()   # user clicked OK
    """

    def __init__(
        self,
        parent=None,
        initial_text: str = "",
        title: str = "Sticky Note",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        self._editor = QTextEdit()
        self._editor.setPlainText(initial_text)
        # RTL layout for Arabic typing
        self._editor.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        # clicked.connect(...) — when OK clicked, call self.accept()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        """Return the note text the user entered."""
        return self._editor.toPlainText().strip()


class PageNoteDialog(QDialog):
    """Dialog to edit a page-level summary note."""

    def __init__(self, parent=None, page_number: int = 1, initial_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Page Note — Page {page_number}")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Notes for page {page_number}:"))

        self._editor = QTextEdit()
        self._editor.setPlainText(initial_text)
        self._editor.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self._editor.toPlainText().strip()


class GoToPageDialog(QDialog):
    """Dialog asking the user which page number to jump to."""

    def __init__(self, parent=None, current_page: int = 1, total_pages: int = 1) -> None:
        super().__init__(parent)
        self.setWindowTitle("Go to Page")

        layout = QFormLayout(self)

        self._spin = QSpinBox()
        self._spin.setMinimum(1)
        self._spin.setMaximum(max(1, total_pages))
        self._spin.setValue(current_page)
        layout.addRow("Page number:", self._spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def page_number(self) -> int:
        """Return 1-based page number from the spin box."""
        return self._spin.value()


class BookmarkTitleDialog(QDialog):
    """Optional dialog to name a bookmark."""

    def __init__(self, parent=None, page_number: int = 1, initial_title: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Bookmark")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Bookmark page {page_number}:"))

        self._title_edit = QLineEdit()
        self._title_edit.setText(initial_title or f"Page {page_number}")
        layout.addWidget(self._title_edit)

        row = QHBoxLayout()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)

    def title(self) -> str:
        text = self._title_edit.text().strip()
        return text if text else "Bookmark"
