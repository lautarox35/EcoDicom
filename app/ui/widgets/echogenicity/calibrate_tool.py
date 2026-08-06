"""Herramienta de línea de calibración (dos puntos)."""

from __future__ import annotations

import math
from typing import Optional

from app.analysis.roi_freehand.models import Point2D


class CalibrateLineTool:
    """Dibuja una línea de referencia entre dos clics."""

    def __init__(self) -> None:
        self.p1: Optional[Point2D] = None
        self.p2: Optional[Point2D] = None

    def clear(self) -> None:
        self.p1 = None
        self.p2 = None

    def click(self, x: float, y: float) -> str:
        """
        Returns
        -------
        ``first`` | ``complete``
        """
        if self.p1 is None:
            self.p1 = Point2D(x, y)
            self.p2 = None
            return "first"
        self.p2 = Point2D(x, y)
        return "complete"

    def length_px(self) -> Optional[float]:
        if self.p1 is None or self.p2 is None:
            return None
        return math.hypot(self.p2.x - self.p1.x, self.p2.y - self.p1.y)

    def is_complete(self) -> bool:
        return self.p1 is not None and self.p2 is not None
