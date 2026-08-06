"""Helpers de medición en mm a partir de ImageCalibration."""

from __future__ import annotations

import math
from typing import Optional

from app.analysis.calibration.models import ImageCalibration


def length_mm(pixels: float, calib: ImageCalibration) -> Optional[float]:
    """Longitud en mm usando promedio de spacing X/Y (línea genérica)."""
    if not calib.calibrated or calib.pixel_spacing_x is None or calib.pixel_spacing_y is None:
        return None
    avg = (calib.pixel_spacing_x + calib.pixel_spacing_y) / 2.0
    return float(pixels) * avg


def length_mm_anisotropic(
    dx_px: float,
    dy_px: float,
    calib: ImageCalibration,
) -> Optional[float]:
    """Longitud en mm de un segmento con spacing anisotrópico."""
    if not calib.calibrated or calib.pixel_spacing_x is None or calib.pixel_spacing_y is None:
        return None
    return math.hypot(dx_px * calib.pixel_spacing_x, dy_px * calib.pixel_spacing_y)


def area_mm2(pixel_area: float, calib: ImageCalibration) -> Optional[float]:
    """Área en mm²."""
    if not calib.calibrated or calib.pixel_spacing_x is None or calib.pixel_spacing_y is None:
        return None
    return float(pixel_area) * calib.pixel_spacing_x * calib.pixel_spacing_y


def perimeter_mm(perimeter_px: float, calib: ImageCalibration) -> Optional[float]:
    """Perímetro en mm (promedio de spacings)."""
    return length_mm(perimeter_px, calib)


def size_mm(
    width_px: float,
    height_px: float,
    calib: ImageCalibration,
) -> Optional[tuple[float, float]]:
    """Ancho y alto en mm (bounding box)."""
    if not calib.calibrated or calib.pixel_spacing_x is None or calib.pixel_spacing_y is None:
        return None
    return (
        float(width_px) * calib.pixel_spacing_x,
        float(height_px) * calib.pixel_spacing_y,
    )
