from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QEvent
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
    QTransform,
    QWheelEvent,
)

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsEllipseItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
)

from core.annotation_store import AnnotationStore, Highlight, StickyNote
from core.ocr_service import OcrWord
from core.pdf_document import PdfDocument
from core.text_layer import find_words_in_rect, shape_arabic_for_clipboard, words_to_full_text
from ui.note_dialog import StickyNoteDialog


class SelectionToolbar(QWidget):
    def __init__(self, parent=None, on_highlight=None, on_copy=None, on_close=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.on_highlight = on_highlight
        self.on_copy = on_copy
        self.on_close = on_close
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #cccccc;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
        
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(8, 8, 8, 8)
        v_layout.setSpacing(8)
        
        colors_layout = QHBoxLayout()
        colors_layout.setSpacing(10)
        
        color_styles = [
            ("yellow", "#FFF000"),
            ("green", "#64FF64"),
            ("pink", "#FF64C8")
        ]
        
        for color_name, hex_color in color_styles:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border-radius: 12px;
                    border: 1px solid rgba(0,0,0,0.1);
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(0,0,0,0.3);
                }}
            """)
            btn.clicked.connect(lambda checked=False, c=color_name: self._trigger_highlight(c))
            colors_layout.addWidget(btn)
            
        self.btn_copy = QPushButton("Copy Text")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border-radius: 6px;
                padding: 6px 12px;
                border: 1px solid #e0e0e0;
                color: #333333;
                font-family: sans-serif;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.btn_copy.clicked.connect(self._trigger_copy)
        
        v_layout.addLayout(colors_layout)
        v_layout.addWidget(self.btn_copy)
        layout.addWidget(container)
        
    def _trigger_highlight(self, color):
        if self.on_highlight:
            self.on_highlight(color)
        self.close()
        
    def _trigger_copy(self):
        if self.on_copy:
            self.on_copy()
        self.close()

    def hideEvent(self, event):
        if self.on_close:
            self.on_close()
        super().hideEvent(event)


class ToolMode(Enum):
    NAVIGATE = auto()
    HIGHLIGHT = auto()
    STICKY_NOTE = auto()


COLOR_MAP = {
    "yellow": QColor(255, 240, 0, 100),
    "green": QColor(100, 255, 100, 100),
    "pink": QColor(255, 100, 200, 100),
}


class PdfViewer(QGraphicsView):
    status_message = Signal(str)
    annotation_changed = Signal()
    sticky_note_added = Signal(int, float, float, str)
    wheel_zoom_requested = Signal(int)
    page_nav_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pdf: PdfDocument | None = None
        self._annotations: AnnotationStore | None = None

        self._current_page: int = 0
        self._zoom: float = 1.0
        self._rotation: int = 0
        self._page_width: int = 1
        self._page_height: int = 1
        self._unrotated_page_width: int = 1
        self._unrotated_page_height: int = 1
        
        self._gesture_zoom_accum: float = 0.0

        # OCR words for current page (empty until OCR runs)
        self._ocr_words: list[OcrWord] = []

        self._tool_mode = ToolMode.NAVIGATE

        # Drag state for highlight selection rectangle
        self._drag_start: QPointF | None = None
        self._rubber_band: QGraphicsRectItem | None = None
        self._selection_items: list[QGraphicsRectItem] = []
        self._selected_words: list[OcrWord] = []

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: #F0F0F2; border: none;")

        # Ctrl+C copies selected OCR text
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_shortcut.activated.connect(self._copy_selection)

    def set_pdf(self, pdf: PdfDocument | None) -> None:
        """Attach a PdfDocument after user opens a file."""
        self._pdf = pdf
        self._current_page = 0

    def set_annotations(self, store: AnnotationStore | None) -> None:
        """Attach annotation store for drawing saved highlights/notes."""
        self._annotations = store

    def set_ocr_words(self, words: list[OcrWord]) -> None:
        """Called after OCR completes — stores words and redraws overlays."""
        self._ocr_words = self._sort_words_rtl(words)
        self._redraw_overlays()

    def _sort_words_rtl(self, words: list[OcrWord]) -> list[OcrWord]:
        """Sorts OCR words strictly Top-to-Bottom, Right-to-Left (logical reading order)."""
        if not words:
            return []
            
        # 1. Sort vertically to prepare for line grouping
        words_sorted = sorted(words, key=lambda w: w.y)
        lines = []
        current_line = []
        
        current_line_top = words_sorted[0].y
        current_line_bottom = words_sorted[0].y + words_sorted[0].h
        
        for w in words_sorted:
            w_cy = w.y + w.h / 2
            line_cy = (current_line_top + current_line_bottom) / 2
            
            # 2. Check overlap to handle diacritics vertically (overlap logic)
            if (current_line_top <= w_cy <= current_line_bottom) or (w.y <= line_cy <= w.y + w.h):
                current_line.append(w)
                current_line_top = min(current_line_top, w.y)
                current_line_bottom = max(current_line_bottom, w.y + w.h)
            else:
                lines.append(current_line)
                current_line = [w]
                current_line_top = w.y
                current_line_bottom = w.y + w.h
                
        if current_line:
            lines.append(current_line)
            
        sorted_words = []
        for line in lines:
            line.sort(key=lambda w: w.x + w.w, reverse=True)
            sorted_words.extend(line)
            
        return sorted_words

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        if self._pdf and self._pdf.is_open:
            self.show_page(self._current_page)

    def set_tool_mode(self, mode: ToolMode) -> None:
        self._tool_mode = mode
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def current_page(self) -> int:
        return self._current_page

    def rotate_cw(self) -> None:
        self._rotation = (self._rotation + 90) % 360
        if self._pdf and self._pdf.is_open:
            self.show_page(self._current_page)

    def has_document(self) -> bool:
        return self._pdf is not None and self._pdf.is_open

    def show_page(self, page_index: int) -> None:
        if not self._pdf or not self._pdf.is_open:
            return

        page_index = max(0, min(page_index, self._pdf.page_count - 1))
        self._current_page = page_index
        self._clear_selection()

        png_bytes, unrotated_w, unrotated_h = self._pdf.render_page(page_index, zoom=self._zoom)
        self._unrotated_page_width = unrotated_w
        self._unrotated_page_height = unrotated_h

        image = QImage.fromData(png_bytes, "PNG")
        if self._rotation:
            transform = QTransform().rotate(self._rotation)
            image = image.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        pixmap = QPixmap.fromImage(image)

        self._scene.clear()
        self._page_width = pixmap.width()
        self._page_height = pixmap.height()

        margin = 24
        page_item = QGraphicsPixmapItem(pixmap)
        page_item.setOffset(margin, margin)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        page_item.setGraphicsEffect(shadow)
        self._scene.addItem(page_item)

        total_w = pixmap.width() + margin * 2
        total_h = pixmap.height() + margin * 2
        self._scene.setSceneRect(0, 0, total_w, total_h)
        self.setSceneRect(self._scene.sceneRect())
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self._redraw_overlays()

        scanned = self._pdf.is_scanned_page(page_index)
        msg = f"Page {page_index + 1}/{self._pdf.page_count}"
        if scanned and not self._ocr_words:
            msg += " — Scanned page (run OCR to select text)"
        self.status_message.emit(msg)

    def _redraw_overlays(self) -> None:
        if not self._annotations:
            return

        page = self._current_page
        w, h = self._page_width, self._page_height
        margin = 24

        for hl in self._annotations.highlights_for_page(page):
            color = COLOR_MAP.get(hl.color, COLOR_MAP["yellow"])
            for norm_rect in hl.rects:
                scene_rect = self._map_unrotated_normalized_rect_to_scene_rect(norm_rect)
                item = QGraphicsRectItem(scene_rect)
                item.setBrush(QBrush(color))
                item.setPen(QPen(Qt.PenStyle.NoPen))
                item.setZValue(10)
                self._scene.addItem(item)

        for note in self._annotations.sticky_notes_for_page(page):
            scene_pos = self._map_unrotated_normalized_point_to_scene_point(QPointF(note.x, note.y))
            cx = scene_pos.x()
            cy = scene_pos.y()
            pin = QGraphicsEllipseItem(cx - 8, cy - 8, 16, 16)
            pin.setBrush(QBrush(QColor(255, 220, 0)))
            pin.setPen(QPen(QColor(180, 140, 0), 2))
            pin.setZValue(20)
            pin.setToolTip(note.content[:200])
            self._scene.addItem(pin)


    def mousePressEvent(self, event) -> None:
        if not self._pdf or not self._pdf.is_open:
            super().mousePressEvent(event)
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        margin = 24

        if self._tool_mode in (ToolMode.HIGHLIGHT, ToolMode.NAVIGATE) and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = scene_pos
            self._clear_selection()
            return

        if self._tool_mode == ToolMode.STICKY_NOTE and event.button() == Qt.MouseButton.LeftButton:
            self._place_sticky_note(scene_pos)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start:
            scene_pos = self.mapToScene(event.position().toPoint())
            self._update_text_selection(self._drag_start, scene_pos)
            return
        super().mouseMoveEvent(event)

    def _closest_word_index(self, norm_pos: QPointF) -> int | None:
        if not self._ocr_words:
            return None
        
        nx, ny = norm_pos.x(), norm_pos.y()
        
        for i, w in enumerate(self._ocr_words):
            if w.x <= nx <= w.x + w.w and w.y <= ny <= w.y + w.h:
                return i
                
        best_dist = float('inf')
        best_idx = None
        for i, w in enumerate(self._ocr_words):
            dx = max(w.x - nx, 0.0, nx - (w.x + w.w))
            dy = max(w.y - ny, 0.0, ny - (w.y + w.h))
            
            dist = dx*dx + (dy * 5.0)**2
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def _update_text_selection(self, start_pos: QPointF, end_pos: QPointF) -> None:
        if not self._ocr_words:
            return

        start_norm = self._map_scene_point_to_unrotated_normalized(start_pos)
        end_norm = self._map_scene_point_to_unrotated_normalized(end_pos)

        start_idx = self._closest_word_index(start_norm)
        end_idx = self._closest_word_index(end_norm)

        if start_idx is None or end_idx is None:
            return

        min_idx = min(start_idx, end_idx)
        max_idx = max(start_idx, end_idx)

        new_selected = self._ocr_words[min_idx:max_idx+1]

        if getattr(self, '_selected_words', None) == new_selected:
            return
            
        self._clear_selection_items()
        self._selected_words = new_selected

        rects = self._group_words_into_rects(self._selected_words)
        for r in rects:
            scene_rect = self._map_unrotated_normalized_rect_to_scene_rect(r)
            scene_rect.adjust(-2, -2, 2, 2)
            item = QGraphicsRectItem(scene_rect)
            item.setPen(QPen(Qt.PenStyle.NoPen))
            item.setBrush(QBrush(QColor(0, 120, 255, 60)))
            item.setZValue(15)
            self._scene.addItem(item)
            self._selection_items.append(item)

    def _clear_selection_items(self) -> None:
        for item in getattr(self, '_selection_items', []):
            if item.scene() == self._scene:
                self._scene.removeItem(item)
        self._selection_items = []
        
        if getattr(self, '_rubber_band', None):
            if self._rubber_band.scene() == self._scene:
                self._scene.removeItem(self._rubber_band)
            self._rubber_band = None

    def _clear_selection(self) -> None:
        self._clear_selection_items()
        self._selected_words = []

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_start and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            dx = scene_pos.x() - self._drag_start.x()
            dy = scene_pos.y() - self._drag_start.y()
            dist_sq = dx*dx + dy*dy
            
            if dist_sq >= 25 and self._selected_words:
                self._show_contextual_menu(event.globalPosition().toPoint())
            else:
                self._clear_selection()

            self._drag_start = None
            return
        super().mouseReleaseEvent(event)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                self._gesture_zoom_accum += event.value()
                if self._gesture_zoom_accum > 0.1:
                    self.wheel_zoom_requested.emit(1)
                    self._gesture_zoom_accum = 0.0
                elif self._gesture_zoom_accum < -0.1:
                    self.wheel_zoom_requested.emit(-1)
                    self._gesture_zoom_accum = 0.0
                return True
        return super().event(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.wheel_zoom_requested.emit(1)
            elif delta < 0:
                self.wheel_zoom_requested.emit(-1)
            event.accept()
            return

        vbar = self.verticalScrollBar()
        at_top = vbar.value() <= vbar.minimum()
        at_bottom = vbar.value() >= vbar.maximum()

        super().wheelEvent(event)

        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
            delta = event.angleDelta().y()
            if delta < 0 and at_bottom:
                self.page_nav_requested.emit(1)
            elif delta > 0 and at_top:
                self.page_nav_requested.emit(-1)

    def _show_contextual_menu(self, global_pos) -> None:
        if hasattr(self, '_selection_toolbar') and self._selection_toolbar:
            self._selection_toolbar.close()
            
        self._selection_toolbar = SelectionToolbar(
            parent=self.window(),
            on_highlight=self._finish_highlight,
            on_copy=self._copy_selection_and_clear,
            on_close=self._clear_selection
        )
        self._selection_toolbar.show()
        
        tw = self._selection_toolbar.width()
        th = self._selection_toolbar.height()
        
        self._selection_toolbar.move(global_pos.x() - tw // 2, global_pos.y() - th - 10)

    def _copy_selection_and_clear(self) -> None:
        self._copy_selection()
        self._clear_selection()

    def _group_words_into_rects(self, words: list[OcrWord]) -> list[list[float]]:
        if not words:
            return []

        by_yc = sorted(words, key=lambda w: w.y + w.h / 2)

        heights = sorted(w.h for w in by_yc)
        median_h = heights[len(heights) // 2]
        threshold = median_h * 0.5

        lines: list[list[OcrWord]] = []
        current: list[OcrWord] = [by_yc[0]]

        for prev, curr in zip(by_yc, by_yc[1:]):
            gap = (curr.y + curr.h / 2) - (prev.y + prev.h / 2)
            if gap > threshold:
                lines.append(current)
                current = [curr]
            else:
                current.append(curr)
        lines.append(current)

        all_words = self._ocr_words if self._ocr_words else words
        page_x0 = min(w.x       for w in all_words)
        page_x1 = max(w.x + w.w for w in all_words)

        if len(lines) == 1:
            ln = lines[0]
            return [[min(w.x for w in ln), min(w.y for w in ln),
                     max(w.x + w.w for w in ln), max(w.y + w.h for w in ln)]]

        rects: list[list[float]] = []
        n = len(lines)
        for i, ln in enumerate(lines):
            y0 = min(w.y       for w in ln)
            y1 = max(w.y + w.h for w in ln)
            lx0 = min(w.x       for w in ln)
            lx1 = max(w.x + w.w for w in ln)

            if i == 0:
                x0, x1 = lx0, page_x1
            elif i == n - 1:
                x0, x1 = page_x0, lx1
            else:
                x0, x1 = page_x0, page_x1

            rects.append([x0, y0, x1, y1])

        return rects


    def _finish_highlight(self, color: str = "yellow") -> None:
        if not self._annotations or not self._selected_words:
            self._clear_selection()
            return

        text = words_to_full_text(self._selected_words)
        rects = self._group_words_into_rects(self._selected_words)

        self._annotations.add_highlight(
            page=self._current_page,
            rects=rects, color=color, text=text)
        self._redraw_overlays()
        self.annotation_changed.emit()
        self.status_message.emit(f"Highlight added on page {self._current_page + 1}")
        self._clear_selection()

    def _place_sticky_note(self, scene_pos: QPointF) -> None:
        dlg = StickyNoteDialog(parent=self)
        if not dlg.exec():
            return

        content = dlg.text()
        if not content:
            return

        norm_pos = self._map_scene_point_to_unrotated_normalized(scene_pos)
        nx, ny = norm_pos.x(), norm_pos.y()

        if self._annotations:
            self._annotations.add_sticky_note(
                page=self._current_page,
                x=nx,
                y=ny,
                content=content,
            )
            self._redraw_overlays()
            self.annotation_changed.emit()

        self.sticky_note_added.emit(self._current_page, nx, ny, content)
        self.status_message.emit("Sticky note added")

    def _select_word_at(self, scene_pos: QPointF) -> None:
        norm_pos = self._map_scene_point_to_unrotated_normalized(scene_pos)
        nx, ny = norm_pos.x(), norm_pos.y()
        hits = find_words_in_rect(self._ocr_words, nx, ny, nx, ny)
        if hits:
            self._selected_words = hits
            self.status_message.emit(f"Selected: {hits[0].text} (Ctrl+C to copy)")

    def _map_scene_point_to_unrotated_normalized(self, scene_pos: QPointF) -> QPointF:
        margin = 24
        view_x = scene_pos.x() - margin
        view_y = scene_pos.y() - margin

        if self._rotation == 90:
            unrotated_x = self._unrotated_page_width - view_y
            unrotated_y = view_x
        elif self._rotation == 180:
            unrotated_x = self._unrotated_page_width - view_x
            unrotated_y = self._unrotated_page_height - view_y
        elif self._rotation == 270:
            unrotated_x = view_y
            unrotated_y = self._unrotated_page_height - view_x
        else:
            unrotated_x = view_x
            unrotated_y = view_y

        nx = unrotated_x / self._unrotated_page_width if self._unrotated_page_width > 0 else 0
        ny = unrotated_y / self._unrotated_page_height if self._unrotated_page_height > 0 else 0
        return QPointF(max(0, nx), max(0, ny))

    def _map_unrotated_normalized_point_to_scene_point(self, norm_pos: QPointF) -> QPointF:
        margin = 24
        page_x = norm_pos.x() * self._unrotated_page_width
        page_y = norm_pos.y() * self._unrotated_page_height

        if self._rotation == 90:
            view_x = page_y
            view_y = self._unrotated_page_width - page_x
        elif self._rotation == 180:
            view_x = self._unrotated_page_width - page_x
            view_y = self._unrotated_page_height - page_y
        elif self._rotation == 270:
            view_x = self._unrotated_page_height - page_y
            view_y = page_x
        else:
            view_x = page_x
            view_y = page_y
        return QPointF(view_x + margin, view_y + margin)

    def _map_unrotated_normalized_rect_to_scene_rect(self, norm_rect: list[float]) -> QRectF:
        nx0, ny0, nx1, ny1 = norm_rect
        p1_scene = self._map_unrotated_normalized_point_to_scene_point(QPointF(nx0, ny0))
        p2_scene = self._map_unrotated_normalized_point_to_scene_point(QPointF(nx1, ny1))
        return QRectF(p1_scene, p2_scene).normalized()

    def _copy_selection(self) -> None:
        if not self._selected_words:
            return
        text = words_to_full_text(self._selected_words)
        shaped = shape_arabic_for_clipboard(text)
        QApplication.clipboard().setText(shaped)
        self.status_message.emit("Copied to clipboard")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._scene.items():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
