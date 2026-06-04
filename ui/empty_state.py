# empty_state.py — Shown in the document area when no PDF is loaded.
# ---------------------------------------------------------------------------

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyState(QWidget):
    """Centered placeholder: document icon, message, Open File button."""

    open_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyState")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 64px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("Open a PDF to begin reading")
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Arabic books, scanned PDFs, highlights, and notes")
        subtitle.setObjectName("EmptySubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        open_btn = QPushButton("Open File")
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(self.open_clicked.emit)
        layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
