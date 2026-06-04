# widgets.py — Reusable Fluent-style UI building blocks.
# ---------------------------------------------------------------------------

from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget, QLabel


class ToolbarDivider(QFrame):
    """Thin vertical line between toolbar groups."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ToolbarDivider")
        self.setFrameShape(QFrame.Shape.VLine)


class FluentToolButton(QPushButton):
    """
    Toolbar button with optional icon character and label below/beside.
    Used for Find, Annotate, Clip, etc.
    """

    def __init__(
        self,
        icon_text: str,
        label: str,
        parent=None,
        checkable: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setCheckable(checkable)
        self.setToolTip(label)
        self.setText(f"{icon_text}\n{label}")
        self.setStyleSheet("text-align: center; font-size: 11px; min-width: 52px; max-width: 72px;")


class IconToolButton(QPushButton):
    """Compact icon-only toolbar button (prev/next, zoom, view modes)."""

    def __init__(self, icon_text: str, tooltip: str = "", parent=None, checkable: bool = False) -> None:
        super().__init__(icon_text, parent)
        self.setCheckable(checkable)
        self.setToolTip(tooltip)
        self.setFixedSize(36, 36)


class DocumentViewport(QWidget):
    """Gray canvas area wrapping the PDF viewer or empty state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DocumentViewport")
