"""Cálculo geométrico de polígonos (área, perímetro, centroide, bbox)."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from app.analysis.roi_freehand.models import GeometryResult, Point2D, PolygonROI


def compute_geometry(
    polygon: PolygonROI,
    spacing_mm: Optional[Tuple[float, float]] = None,
) -> Optional[GeometryResult]:
    """
    Calcula geometría del polígono cerrado.

    Parameters
    ----------
    spacing_mm:
        ``(row_mm, col_mm)`` por píxel, o None si no hay calibración.
    """
    pts = polygon.points
    if len(pts) < 3:
        return None

    xs = np.array([p.x for p in pts], dtype=np.float64)
    ys = np.array([p.y for p in pts], dtype=np.float64)

    # Shoelace (área absoluta en px²)
    area_px = 0.5 * abs(
        float(np.dot(xs, np.roll(ys, -1)) - np.dot(ys, np.roll(xs, -1)))
    )
    if area_px <= 0:
        return None

    # Perímetro en px
    dx = np.roll(xs, -1) - xs
    dy = np.roll(ys, -1) - ys
    peri_px = float(np.sum(np.hypot(dx, dy)))

    # Centroide (promedio de vértices; suficiente para UI clínica)
    cx = float(np.mean(xs))
    cy = float(np.mean(ys))

    x0 = int(np.floor(xs.min()))
    y0 = int(np.floor(ys.min()))
    x1 = int(np.ceil(xs.max()))
    y1 = int(np.ceil(ys.max()))

    area_mm2: Optional[float] = None
    area_cm2: Optional[float] = None
    peri_mm: Optional[float] = None
    row_s = col_s = None
    if spacing_mm is not None:
        row_s, col_s = float(spacing_mm[0]), float(spacing_mm[1])
        # Área: px² * row * col
        area_mm2 = area_px * row_s * col_s
        area_cm2 = area_mm2 / 100.0
        # Perímetro: px * promedio(spacingX, spacingY)
        peri_mm = peri_px * (row_s + col_s) / 2.0

    return GeometryResult(
        pixel_area=area_px,
        area_mm2=area_mm2,
        area_cm2=area_cm2,
        perimeter_px=peri_px,
        perimeter_mm=peri_mm,
        centroid_x=cx,
        centroid_y=cy,
        bbox_x=x0,
        bbox_y=y0,
        bbox_width=max(0, x1 - x0),
        bbox_height=max(0, y1 - y0),
        row_spacing_mm=row_s,
        col_spacing_mm=col_s,
    )
