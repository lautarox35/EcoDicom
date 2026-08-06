"""Compatibilidad: spacing ROI libre vía ImageCalibration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from app.analysis.calibration.models import ImageCalibration
from app.analysis.calibration.reader import load_image_calibration, read_dicom_calibration

# Ya no se fuerza un default “falso”; Unknown deja mediciones en px.
DEFAULT_PIXEL_SPACING_MM = 0.10  # solo hint UI si el usuario quiere calibrar a mano


def read_pixel_spacing_mm(path: Path) -> Optional[Tuple[float, float]]:
    """``(row_mm, col_mm)`` desde DICOM, o None."""
    calib = read_dicom_calibration(path)
    return calib.spacing_row_col


def resolve_spacing_mm(
    dicom_spacing: Optional[Tuple[float, float]],
    manual_mm_per_px: float = DEFAULT_PIXEL_SPACING_MM,
) -> Optional[Tuple[float, float]]:
    """
    Spacing efectivo o None si no hay calibración real.

    Nota: ya no inventa mm desde un default silencioso.
    """
    if dicom_spacing is not None:
        row_s, col_s = float(dicom_spacing[0]), float(dicom_spacing[1])
        if row_s > 0 and col_s > 0:
            return (row_s, col_s)
    return None


def calibration_for_path(path: Optional[Path]) -> ImageCalibration:
    """Carga calibración completa (DICOM → manual → Unknown)."""
    if path is None:
        return ImageCalibration.unknown()
    return load_image_calibration(Path(path))
