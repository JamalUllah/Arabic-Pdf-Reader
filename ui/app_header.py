from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem, QWidget


class AppHeader(QWidget):
    back_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AppHeader")
        self.setFixedHeight(64)

        self._drag_pos: QPoint | None = None
        self._window = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(12)

        self._back_btn = QPushButton("←")
        self._back_btn.setObjectName("BackButton")
        self._back_btn.setToolTip("Close document")
        self._back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self._back_btn)

        self._title = QLabel("Reader")
        self._title.setObjectName("HeaderTitle")
        layout.addWidget(self._title)

        dot = QLabel("·")
        dot.setObjectName("HeaderDot")
        layout.addWidget(dot)

        self._filename = QLabel("No file open")
        self._filename.setObjectName("HeaderFilename")
        layout.addWidget(self._filename)

        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self._min_btn = QPushButton("—")
        self._min_btn.setObjectName("WindowControl")
        self._min_btn.setFixedSize(46, 32)
        self._min_btn.clicked.connect(self._on_minimize)
        layout.addWidget(self._min_btn)

        self._max_btn = QPushButton("□")
        self._max_btn.setObjectName("WindowControl")
        self._max_btn.setFixedSize(46, 32)
        self._max_btn.clicked.connect(self._on_maximize)
        layout.addWidget(self._max_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("WindowClose")
        self._close_btn.setFixedSize(46, 32)
        self._close_btn.clicked.connect(self._on_close)
        layout.addWidget(self._close_btn)

    def set_filename(self, name: str) -> None:
        self._filename.setText(name or "No file open")

    def _on_minimize(self) -> None:
        if self._window:
            self._window.showMinimized()

    def _on_maximize(self) -> None:
        if not self._window:
            return
        if self._window.isMaximized():
            self._window.showNormal()
            self._max_btn.setText("□")
        else:
            self._window.showMaximized()
            self._max_btn.setText("❐")

    def _on_close(self) -> None:
        if self._window:
            self._window.close()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._window:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton and self._window:
            if not self._window.isMaximized():
                self._window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_maximize()
        super().mouseDoubleClickEvent(event)
