"""Canvas de anotación tipo Paint sobre una imagen capturada."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class AnnotateCanvas(QWidget):
    """Dibuja con el mouse sobre una imagen (coordenadas en espacio de imagen)."""

    image_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setStyleSheet("background: #111; border: 1px solid #444;")
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._base: Optional[QPixmap] = None
        self._overlay: Optional[QPixmap] = None
        self._undo_stack: list[QPixmap] = []
        self._drawing = False
        self._last_img_pos: Optional[QPoint] = None
        self._pen_color = QColor(255, 40, 40)
        self._pen_width = 4
        self._eraser = False
        self._display_rect: Optional[tuple[int, int, int, int]] = None

    def has_image(self) -> bool:
        return self._base is not None and not self._base.isNull()

    def clear_canvas(self) -> None:
        self._base = None
        self._overlay = None
        self._undo_stack.clear()
        self._drawing = False
        self._last_img_pos = None
        self.update()

    def load_path(self, path: Path) -> bool:
        pix = QPixmap(str(path))
        if pix.isNull():
            self.clear_canvas()
            return False
        self._base = pix
        self._overlay = QPixmap(pix.size())
        self._overlay.fill(Qt.GlobalColor.transparent)
        self._undo_stack.clear()
        self.update()
        return True

    def set_pen_color(self, color: QColor) -> None:
        self._pen_color = color
        self._eraser = False

    def set_pen_width(self, width: int) -> None:
        self._pen_width = max(1, int(width))

    def set_eraser(self, enabled: bool) -> None:
        self._eraser = enabled

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._overlay = self._undo_stack.pop()
        self.update()
        self.image_changed.emit()

    def clear_drawings(self) -> None:
        if self._overlay is None or self._base is None:
            return
        self._push_undo()
        self._overlay = QPixmap(self._base.size())
        self._overlay.fill(Qt.GlobalColor.transparent)
        self.update()
        self.image_changed.emit()

    def composite_pixmap(self) -> Optional[QPixmap]:
        if self._base is None:
            return None
        result = QPixmap(self._base.size())
        result.fill(Qt.GlobalColor.black)
        painter = QPainter(result)
        painter.drawPixmap(0, 0, self._base)
        if self._overlay is not None:
            painter.drawPixmap(0, 0, self._overlay)
        painter.end()
        return result

    def save_to_path(self, path: Path) -> bool:
        pix = self.composite_pixmap()
        if pix is None:
            return False
        return pix.save(str(path), "PNG")

    def _push_undo(self) -> None:
        if self._overlay is None:
            return
        self._undo_stack.append(self._overlay.copy())
        if len(self._undo_stack) > 40:
            self._undo_stack.pop(0)

    def _widget_to_image(self, pos: QPoint) -> Optional[QPoint]:
        if self._base is None or self._display_rect is None:
            return None
        x, y, w, h = self._display_rect
        if w <= 0 or h <= 0:
            return None
        if pos.x() < x or pos.y() < y or pos.x() >= x + w or pos.y() >= y + h:
            return None
        ix = int((pos.x() - x) * self._base.width() / w)
        iy = int((pos.y() - y) * self._base.height() / h)
        ix = max(0, min(self._base.width() - 1, ix))
        iy = max(0, min(self._base.height() - 1, iy))
        return QPoint(ix, iy)

    def _stroke(self, a: QPoint, b: QPoint) -> None:
        if self._overlay is None:
            return
        painter = QPainter(self._overlay)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._eraser:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(QColor(0, 0, 0, 0), max(2, self._pen_width * 2), Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        else:
            pen = QPen(self._pen_color, self._pen_width, Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        if a == b:
            painter.drawPoint(a)
        else:
            painter.drawLine(a, b)
        painter.end()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(17, 17, 17))
        if self._base is None:
            painter.setPen(QColor(170, 170, 170))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sin imágenes")
            self._display_rect = None
            return

        scaled = self._base.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._display_rect = (x, y, scaled.width(), scaled.height())
        painter.drawPixmap(x, y, scaled)

        if self._overlay is not None:
            overlay_scaled = self._overlay.scaled(
                scaled.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(x, y, overlay_scaled)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._base is None:
            return
        img_pos = self._widget_to_image(event.position().toPoint())
        if img_pos is None:
            return
        self._push_undo()
        self._drawing = True
        self._last_img_pos = img_pos
        self._stroke(img_pos, img_pos)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._drawing or self._last_img_pos is None:
            return
        img_pos = self._widget_to_image(event.position().toPoint())
        if img_pos is None:
            return
        self._stroke(self._last_img_pos, img_pos)
        self._last_img_pos = img_pos
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            self._last_img_pos = None
            self.image_changed.emit()
