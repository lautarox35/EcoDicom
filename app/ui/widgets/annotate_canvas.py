"""Canvas de anotación tipo Paint sobre una imagen capturada."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from PySide6.QtCore import QPoint, QPointF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from app.analysis.echogenicity.models import ROIRect
from app.analysis.roi_freehand.models import Point2D, PolygonROI
from app.ui.widgets.echogenicity.calibrate_tool import CalibrateLineTool
from app.ui.widgets.echogenicity.freehand_overlay import FreehandOverlay
from app.ui.widgets.echogenicity.freehand_tool import FreehandROITool
from app.ui.widgets.echogenicity.roi_overlay import ROIOverlay
from app.ui.widgets.echogenicity.roi_selection_tool import ROISelectionTool

CanvasMode = Literal["paint", "roi", "freehand", "calibrate"]


class AnnotateCanvas(QWidget):
    """Dibuja con el mouse sobre una imagen (coordenadas en espacio de imagen)."""

    image_changed = Signal()
    roi_changed = Signal(object)  # ROIRect | None
    roi_committed = Signal(object)  # ROIRect | None — al soltar el mouse
    freehand_changed = Signal(object)  # PolygonROI | None
    freehand_committed = Signal(object)  # PolygonROI | None
    calibrate_line_done = Signal(float)  # longitud en píxeles

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

        self._mode: CanvasMode = "paint"
        self._roi_tool = ROISelectionTool()
        self._roi_dragging = False
        self._roi_debounce = QTimer(self)
        self._roi_debounce.setSingleShot(True)
        self._roi_debounce.setInterval(40)
        self._roi_debounce.timeout.connect(self._emit_roi_changed)

        self._freehand = FreehandROITool()
        self._freehand_active = False
        self._freehand_cursor: Optional[Point2D] = None
        self._freehand_debounce = QTimer(self)
        self._freehand_debounce.setSingleShot(True)
        self._freehand_debounce.setInterval(40)
        self._freehand_debounce.timeout.connect(self._emit_freehand_changed)

        self._calibrate = CalibrateLineTool()
        self._calibrate_cursor: Optional[Point2D] = None

    def mode(self) -> CanvasMode:
        """Modo actual."""
        return self._mode

    def set_mode(self, mode: CanvasMode) -> None:
        """Cambia entre Paint, ROI, freehand y calibración."""
        if mode not in ("paint", "roi", "freehand", "calibrate"):
            return
        self._mode = mode
        self._drawing = False
        self._roi_dragging = False
        self._freehand_active = False
        self._freehand_cursor = None
        if mode != "calibrate":
            self._calibrate.clear()
            self._calibrate_cursor = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def clear_calibrate(self) -> None:
        self._calibrate.clear()
        self._calibrate_cursor = None
        self.update()

    def clear_roi(self) -> None:
        """Elimina el ROI rectangular activo."""
        self._roi_tool.clear()
        self.roi_changed.emit(None)
        self.update()

    def clear_freehand(self) -> None:
        """Elimina el polígono libre."""
        self._freehand.clear()
        self._freehand_cursor = None
        self.freehand_changed.emit(None)
        self.update()

    def active_roi(self) -> Optional[ROIRect]:
        """ROI rectangular activo en coordenadas de imagen nativa."""
        return self._roi_tool.active_roi

    def active_freehand(self) -> Optional[PolygonROI]:
        """Polígono libre actual (copia)."""
        poly = self._freehand.polygon
        if not poly.points:
            return None
        return poly.copy()

    def image_size(self) -> Optional[tuple[int, int]]:
        """(width, height) de la imagen base, o None."""
        if self._base is None or self._base.isNull():
            return None
        return (self._base.width(), self._base.height())

    def display_rect(self) -> Optional[tuple[int, int, int, int]]:
        """Rectángulo letterbox (x, y, w, h) en coords de widget."""
        return self._display_rect

    def widget_to_image(self, pos: QPoint) -> Optional[QPoint]:
        """Mapea un punto del widget a coordenadas de imagen nativa."""
        return self._widget_to_image(pos)

    def has_image(self) -> bool:
        return self._base is not None and not self._base.isNull()

    def clear_canvas(self) -> None:
        self._base = None
        self._overlay = None
        self._undo_stack.clear()
        self._drawing = False
        self._last_img_pos = None
        self._roi_tool.clear()
        self._freehand.clear()
        self.update()

    def load_path(self, path: Path) -> bool:
        pix = QPixmap(str(path))
        if pix.isNull():
            self.clear_canvas()
            return False
        return self.load_pixmap(pix)

    def load_pixmap(self, pix: QPixmap) -> bool:
        if pix.isNull():
            self.clear_canvas()
            return False
        self._base = pix
        self._overlay = QPixmap(pix.size())
        self._overlay.fill(Qt.GlobalColor.transparent)
        self._undo_stack.clear()
        self._roi_tool.clear()
        self._freehand.clear()
        self.update()
        return True

    def composite_rgb(self) -> Optional["np.ndarray"]:
        """Devuelve la imagen anotada como RGB uint8 (H, W, 3)."""
        import numpy as np
        from PySide6.QtCore import QBuffer, QIODevice
        from PySide6.QtGui import QImage

        pix = self.composite_pixmap()
        if pix is None:
            return None
        image = pix.toImage().convertToFormat(QImage.Format.Format_RGB888)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        data = bytes(buffer.data())
        buffer.close()
        from io import BytesIO

        from PIL import Image as PILImage

        pil = PILImage.open(BytesIO(data)).convert("RGB")
        return np.asarray(pil, dtype=np.uint8).copy()

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

    def _widget_to_image(self, pos: QPoint, *, clamp: bool = False) -> Optional[QPoint]:
        self._ensure_display_rect()
        if self._base is None or self._display_rect is None:
            return None
        x, y, w, h = self._display_rect
        if w <= 0 or h <= 0:
            return None
        px, py = pos.x(), pos.y()
        if clamp:
            px = max(x, min(x + w - 1, px))
            py = max(y, min(y + h - 1, py))
        elif px < x or py < y or px >= x + w or py >= y + h:
            return None
        ix = int((px - x) * self._base.width() / w)
        iy = int((py - y) * self._base.height() / h)
        ix = max(0, min(self._base.width() - 1, ix))
        iy = max(0, min(self._base.height() - 1, iy))
        return QPoint(ix, iy)

    def _ensure_display_rect(self) -> None:
        """Calcula el letterbox sin esperar a paintEvent (crítico para el primer click)."""
        if self._base is None or self._base.isNull():
            self._display_rect = None
            return
        if self.width() <= 0 or self.height() <= 0:
            return
        scaled = self._base.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._display_rect = (x, y, scaled.width(), scaled.height())

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

    def _emit_roi_changed(self) -> None:
        self.roi_changed.emit(self._roi_tool.active_roi)

    def _emit_freehand_changed(self) -> None:
        self.freehand_changed.emit(self.active_freehand())

    def _apply_roi_cursor(self, img_pos: Optional[QPoint]) -> None:
        if self._mode != "roi" or img_pos is None:
            return
        name = self._roi_tool.cursor_for_pos(img_pos.x(), img_pos.y())
        cursors = {
            "cross": Qt.CursorShape.CrossCursor,
            "size_all": Qt.CursorShape.SizeAllCursor,
            "size_fdiag": Qt.CursorShape.SizeFDiagCursor,
            "size_bdiag": Qt.CursorShape.SizeBDiagCursor,
        }
        self.setCursor(cursors.get(name, Qt.CursorShape.CrossCursor))

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

        if self._mode == "roi":
            ROIOverlay.paint(
                painter,
                self._roi_tool.active_roi,
                self._display_rect,
                (self._base.width(), self._base.height()),
            )
        elif self._mode == "freehand":
            FreehandOverlay.paint(
                painter,
                self._freehand.polygon,
                self._display_rect,
                (self._base.width(), self._base.height()),
                cursor_img=None if self._freehand.is_closed() else self._freehand_cursor,
            )
        elif self._mode == "calibrate":
            self._paint_calibrate_line(
                painter,
                self._display_rect,
                (self._base.width(), self._base.height()),
            )

    def _paint_calibrate_line(
        self,
        painter: QPainter,
        display_rect: tuple[int, int, int, int],
        image_size: tuple[int, int],
    ) -> None:
        img_w, img_h = image_size
        dx, dy, dw, dh = display_rect
        if img_w <= 0 or dh <= 0:
            return

        def to_w(p: Point2D) -> QPointF:
            return QPointF(dx + p.x * dw / img_w, dy + p.y * dh / img_h)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#38bdf8"), 2)
        painter.setPen(pen)
        if self._calibrate.p1 is not None:
            p1 = to_w(self._calibrate.p1)
            painter.setBrush(QColor("#38bdf8"))
            painter.drawEllipse(p1, 4, 4)
            end = self._calibrate.p2 or self._calibrate_cursor
            if end is not None:
                p2 = to_w(end)
                painter.drawLine(p1, p2)
                painter.drawEllipse(p2, 4, 4)
        painter.restore()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if (
            self._mode != "freehand"
            or event.button() != Qt.MouseButton.LeftButton
            or self._base is None
        ):
            return
        img_pos = self._widget_to_image(event.position().toPoint(), clamp=True)
        if img_pos is None:
            return
        action = self._freehand.begin_double_click(float(img_pos.x()), float(img_pos.y()))
        self.update()
        poly = self.active_freehand()
        self.freehand_changed.emit(poly)
        if action == "close":
            self.freehand_committed.emit(poly)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._base is None:
            return
        img_pos = self._widget_to_image(event.position().toPoint())
        if img_pos is None:
            return

        if self._mode == "calibrate":
            action = self._calibrate.click(float(img_pos.x()), float(img_pos.y()))
            self.update()
            if action == "complete":
                length = self._calibrate.length_px()
                if length is not None and length > 0:
                    self.calibrate_line_done.emit(float(length))
            return

        if self._mode == "freehand":
            self._freehand_active = True
            self.grabMouse()
            action = self._freehand.begin_click(float(img_pos.x()), float(img_pos.y()))
            self.update()
            if action == "close":
                self._freehand_active = False
                try:
                    self.releaseMouse()
                except RuntimeError:
                    pass
                poly = self.active_freehand()
                self.freehand_changed.emit(poly)
                self.freehand_committed.emit(poly)
            elif action == "vertex_drag":
                self._freehand_debounce.start()
            else:
                self.freehand_changed.emit(self.active_freehand())
            return

        if self._mode == "roi":
            self._roi_dragging = True
            self.grabMouse()
            self._roi_tool.begin_press(img_pos.x(), img_pos.y())
            self.update()
            self._roi_debounce.start()
            return

        self._push_undo()
        self._drawing = True
        self._last_img_pos = img_pos
        self._stroke(img_pos, img_pos)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._mode == "calibrate":
            img_pos = self._widget_to_image(event.position().toPoint(), clamp=True)
            if img_pos is not None:
                self._calibrate_cursor = Point2D(float(img_pos.x()), float(img_pos.y()))
            self.update()
            return

        if self._mode == "freehand":
            img_pos = self._widget_to_image(event.position().toPoint(), clamp=self._freehand_active)
            if img_pos is not None:
                self._freehand_cursor = Point2D(float(img_pos.x()), float(img_pos.y()))
                if self._freehand.is_closed() and not self._freehand_active:
                    hit = self._freehand.hit_vertex(float(img_pos.x()), float(img_pos.y()))
                    self.setCursor(
                        Qt.CursorShape.SizeAllCursor
                        if hit is not None
                        else Qt.CursorShape.CrossCursor
                    )
                if self._freehand_active:
                    self._freehand.continue_drag(float(img_pos.x()), float(img_pos.y()))
                    self._freehand_debounce.start()
            self.update()
            return

        if self._mode == "roi":
            if not self._roi_dragging:
                img_pos = self._widget_to_image(event.position().toPoint())
                self._apply_roi_cursor(img_pos)
                return
            if self._base is None:
                return
            img_pos = self._widget_to_image(event.position().toPoint(), clamp=True)
            if img_pos is None:
                return
            self._roi_tool.update_drag(
                img_pos.x(),
                img_pos.y(),
                self._base.width(),
                self._base.height(),
            )
            self.update()
            self._roi_debounce.start()
            return

        if not self._drawing or self._last_img_pos is None:
            return
        img_pos = self._widget_to_image(event.position().toPoint())
        if img_pos is None:
            return
        self._stroke(self._last_img_pos, img_pos)
        self._last_img_pos = img_pos
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._mode == "freehand" and self._freehand_active:
            self._freehand_active = False
            try:
                self.releaseMouse()
            except RuntimeError:
                pass
            self._freehand_debounce.stop()
            img_pos = self._widget_to_image(event.position().toPoint(), clamp=True)
            if img_pos is not None:
                self._freehand.continue_drag(float(img_pos.x()), float(img_pos.y()))
            action = self._freehand.end_drag()
            self.update()
            poly = self.active_freehand()
            self.freehand_changed.emit(poly)
            if action == "edited" or (poly is not None and poly.closed):
                self.freehand_committed.emit(poly)
            return

        if self._mode == "roi" and self._roi_dragging:
            self._roi_dragging = False
            try:
                self.releaseMouse()
            except RuntimeError:
                pass
            self._roi_debounce.stop()
            img_pos = self._widget_to_image(event.position().toPoint(), clamp=True)
            if img_pos is not None and self._base is not None:
                self._roi_tool.update_drag(
                    img_pos.x(),
                    img_pos.y(),
                    self._base.width(),
                    self._base.height(),
                )
            roi = self._roi_tool.end_drag()
            self.update()
            self.roi_changed.emit(roi)
            self.roi_committed.emit(roi)
            return

        if self._drawing:
            self._drawing = False
            self._last_img_pos = None
            self.image_changed.emit()
