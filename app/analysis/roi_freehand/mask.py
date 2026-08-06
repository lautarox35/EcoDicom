"""Rasterizado de máscara poligonal (solo píxeles interiores)."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from app.analysis.roi_freehand.models import PolygonROI


def polygon_mask(
    polygon: PolygonROI,
    image_shape: Tuple[int, int],
) -> Optional[np.ndarray]:
    """
    Máscara bool HxW con True dentro del polígono.

    Usa ``cv2.fillPoly`` sobre el bounding box y pega en la imagen completa
    (eficiente en imágenes grandes).
    """
    h, w = image_shape
    verts = polygon.as_int_vertices()
    if len(verts) < 3 or h <= 0 or w <= 0:
        return None

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    x0 = max(0, min(xs))
    y0 = max(0, min(ys))
    x1 = min(w, max(xs) + 1)
    y1 = min(h, max(ys) + 1)
    if x1 <= x0 or y1 <= y0:
        return None

    # Vértices relativos al bbox
    local = np.array(
        [[[vx - x0, vy - y0] for vx, vy in verts]],
        dtype=np.int32,
    )
    bh, bw = y1 - y0, x1 - x0
    try:
        import cv2

        crop = np.zeros((bh, bw), dtype=np.uint8)
        cv2.fillPoly(crop, local, 1)
    except Exception:  # noqa: BLE001
        crop = _fill_poly_numpy(bh, bw, [(vx - x0, vy - y0) for vx, vy in verts])

    full = np.zeros((h, w), dtype=bool)
    full[y0:y1, x0:x1] = crop.astype(bool)
    return full


def _fill_poly_numpy(
    height: int, width: int, verts: list[tuple[int, int]]
) -> np.ndarray:
    """Fallback scanline simple sin OpenCV."""
    mask = np.zeros((height, width), dtype=np.uint8)
    if len(verts) < 3:
        return mask
    # Usar matplotlib path si está disponible; si no, ray casting por fila
    try:
        from matplotlib.path import Path as MplPath

        yy, xx = np.mgrid[0:height, 0:width]
        points = np.vstack((xx.ravel(), yy.ravel())).T
        path = MplPath(verts)
        inside = path.contains_points(points).reshape(height, width)
        return inside.astype(np.uint8)
    except Exception:  # noqa: BLE001
        pass

    # Ray casting por píxel (lento pero correcto para fallback)
    n = len(verts)
    for y in range(height):
        for x in range(width):
            inside = False
            j = n - 1
            for i in range(n):
                xi, yi = verts[i]
                xj, yj = verts[j]
                if ((yi > y) != (yj > y)) and (
                    x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
                ):
                    inside = not inside
                j = i
            if inside:
                mask[y, x] = 1
    return mask
