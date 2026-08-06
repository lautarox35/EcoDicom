"""Overlay de polígono ROI libre."""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF

from app.analysis.roi_freehand.models import Point2D, PolygonROI

ROI_BORDER = QColor("#14b8a6")
ROI_FILL = QColor(20, 184, 166, 64)  # ~25%
HANDLE_SIZE = 7


class FreehandOverlay:
    """Dibuja polígono abierto o cerrado con handles."""

    @staticmethod
    def paint(
        painter: QPainter,
        polygon: Optional[PolygonROI],
        display_rect: tuple[int, int, int, int],
        image_size: tuple[int, int],
        *,
        cursor_img: Optional[Point2D] = None,
    ) -> None:
        if polygon is None or not polygon.points or not polygon.visible:
            return
        img_w, img_h = image_size
        dx, dy, dw, dh = display_rect
        if img_w <= 0 or img_h <= 0 or dw <= 0 or dh <= 0:
            return

        def to_w(p: Point2D) -> QPointF:
            return QPointF(
                dx + p.x * dw / img_w,
                dy + p.y * dh / img_h,
            )

        pts = [to_w(p) for p in polygon.points]
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if polygon.closed and len(pts) >= 3:
            poly = QPolygonF(pts)
            painter.setBrush(ROI_FILL)
            painter.setPen(QPen(ROI_BORDER, 2))
            painter.drawPolygon(poly)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(ROI_BORDER, 2))
            for i in range(1, len(pts)):
                painter.drawLine(pts[i - 1], pts[i])
            # Línea elástica al cursor
            if cursor_img is not None and pts:
                painter.setPen(QPen(ROI_BORDER, 1, Qt.PenStyle.DashLine))
                painter.drawLine(pts[-1], to_w(cursor_img))
                if len(pts) >= 2:
                    painter.drawLine(pts[0], to_w(cursor_img))

        # Handles
        half = HANDLE_SIZE / 2
        painter.setBrush(ROI_BORDER)
        painter.setPen(QPen(QColor("#0f766e"), 1))
        for pt in pts:
            painter.drawRect(
                int(pt.x() - half), int(pt.y() - half), HANDLE_SIZE, HANDLE_SIZE
            )
        painter.restore()
