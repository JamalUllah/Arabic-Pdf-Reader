from __future__ import annotations

from PySide6.QtCore import Qt

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


class PageNoteDialog(QDialog):
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
        return self._spin.value()


class BookmarkTitleDialog(QDialog):
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
