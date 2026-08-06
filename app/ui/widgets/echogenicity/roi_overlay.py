"""Dibujo del overlay ROI sobre el canvas."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from app.analysis.echogenicity.models import ROIRect

ROI_BORDER = QColor("#14b8a6")
ROI_FILL = QColor(20, 184, 166, 40)
HANDLE_SIZE = 8


class ROIOverlay:
    """Dibuja borde teal, relleno semitransparente y handles de esquina."""

    @staticmethod
    def paint(
        painter: QPainter,
        roi: Optional[ROIRect],
        display_rect: tuple[int, int, int, int],
        image_size: tuple[int, int],
    ) -> None:
        """
        Pinta el ROI mapeado de coords de imagen a coords de widget.

        Parameters
        ----------
        display_rect:
            (x, y, w, h) del letterbox de la imagen en el widget.
        image_size:
            (width, height) de la imagen nativa.
        """
        if roi is None or roi.is_empty():
            return
        img_w, img_h = image_size
        if img_w <= 0 or img_h <= 0:
            return
        dx, dy, dw, dh = display_rect
        if dw <= 0 or dh <= 0:
            return

        def to_widget(ix: int, iy: int) -> QPoint:
            wx = dx + int(ix * dw / img_w)
            wy = dy + int(iy * dh / img_h)
            return QPoint(wx, wy)

        p0 = to_widget(roi.x, roi.y)
        p1 = to_widget(roi.x + roi.width, roi.y + roi.height)
        rect = QRect(p0, p1).normalized()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(rect, ROI_FILL)
        pen = QPen(ROI_BORDER, 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(rect)

        half = HANDLE_SIZE // 2
        painter.setBrush(ROI_BORDER)
        painter.setPen(QPen(QColor("#0f766e"), 1))
        for corner in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            painter.drawRect(corner.x() - half, corner.y() - half, HANDLE_SIZE, HANDLE_SIZE)
        painter.restore()
