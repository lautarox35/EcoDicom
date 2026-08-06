"""Herramienta de dibujo ROI libre (polígono / freehand)."""

from __future__ import annotations

import math
from typing import Optional

from app.analysis.roi_freehand.models import Point2D, PolygonROI

CLOSE_HIT_PX = 12
SAMPLE_DIST_PX = 4
VERTEX_HIT_PX = 10


class FreehandROITool:
    """
    Dibujo por clics / arrastre y edición de vértices (un ROI en v1).

    Estados: idle → drawing → closed (editable).
    """

    def __init__(self) -> None:
        self._polygon = PolygonROI(roi_id="ROI 1")
        self._dragging_vertex: Optional[int] = None
        self._drawing_stroke = False

    @property
    def polygon(self) -> PolygonROI:
        return self._polygon

    def clear(self) -> None:
        """Reinicia el polígono."""
        self._polygon = PolygonROI(roi_id="ROI 1")
        self._dragging_vertex = None
        self._drawing_stroke = False

    def is_closed(self) -> bool:
        return self._polygon.closed

    def begin_click(self, x: float, y: float) -> str:
        """
        Click simple.

        Returns
        -------
        Acción: ``vertex_drag`` | ``close`` | ``add`` | ``ignore``
        """
        if self._polygon.closed:
            idx = self.hit_vertex(x, y)
            if idx is not None:
                self._dragging_vertex = idx
                return "vertex_drag"
            return "ignore"

        # Cerrar si cerca del primer punto y hay >= 3
        if len(self._polygon.points) >= 3 and self._near_first(x, y):
            self._polygon.closed = True
            return "close"

        self._polygon.points.append(Point2D(x, y))
        self._drawing_stroke = True
        return "add"

    def begin_double_click(self, x: float, y: float) -> str:
        """Doble clic: cierra el polígono (mín. 3 puntos)."""
        if self._polygon.closed:
            return self.begin_click(x, y)
        if len(self._polygon.points) < 3:
            # Asegurar último punto
            if not self._polygon.points or self._dist(
                self._polygon.points[-1], x, y
            ) > SAMPLE_DIST_PX:
                self._polygon.points.append(Point2D(x, y))
        if len(self._polygon.points) >= 3:
            self._polygon.closed = True
            self._drawing_stroke = False
            return "close"
        return "ignore"

    def continue_drag(self, x: float, y: float) -> None:
        """Arrastre: freehand o mover vértice."""
        if self._dragging_vertex is not None and self._polygon.closed:
            i = self._dragging_vertex
            if 0 <= i < len(self._polygon.points):
                self._polygon.points[i] = Point2D(x, y)
            return

        if self._polygon.closed or not self._drawing_stroke:
            return
        if not self._polygon.points:
            self._polygon.points.append(Point2D(x, y))
            return
        last = self._polygon.points[-1]
        if self._dist(last, x, y) >= SAMPLE_DIST_PX:
            self._polygon.points.append(Point2D(x, y))

    def end_drag(self) -> str:
        """Fin de arrastre."""
        self._dragging_vertex = None
        self._drawing_stroke = False
        if self._polygon.closed:
            return "edited"
        return "drawing"

    def hit_vertex(self, x: float, y: float) -> Optional[int]:
        """Índice del vértice bajo el cursor, o None."""
        for i, p in enumerate(self._polygon.points):
            if self._dist(p, x, y) <= VERTEX_HIT_PX:
                return i
        return None

    def _near_first(self, x: float, y: float) -> bool:
        if not self._polygon.points:
            return False
        return self._dist(self._polygon.points[0], x, y) <= CLOSE_HIT_PX

    @staticmethod
    def _dist(p: Point2D, x: float, y: float) -> float:
        return math.hypot(p.x - x, p.y - y)
