"""Modelo de calibración espacial (mm/píxel)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

CalibrationSource = Literal[
    "PixelSpacing",
    "ImagerPixelSpacing",
    "NominalScannedPixelSpacing",
    "PhysicalDelta",
    "Manual",
    "Unknown",
]


@dataclass(frozen=True)
class ImageCalibration:
    """
    Calibración espacial de una imagen.

    ``pixel_spacing_x``: mm por píxel en eje horizontal (columnas).
    ``pixel_spacing_y``: mm por píxel en eje vertical (filas).
    """

    source: CalibrationSource
    pixel_spacing_x: Optional[float]
    pixel_spacing_y: Optional[float]
    unit: Literal["mm"] = "mm"
    calibrated: bool = False

    @property
    def spacing_row_col(self) -> Optional[tuple[float, float]]:
        """``(row_mm, col_mm)`` compatible con geometría ROI, o None."""
        if not self.calibrated:
            return None
        if self.pixel_spacing_y is None or self.pixel_spacing_x is None:
            return None
        return (float(self.pixel_spacing_y), float(self.pixel_spacing_x))

    @classmethod
    def unknown(cls) -> "ImageCalibration":
        return cls(
            source="Unknown",
            pixel_spacing_x=None,
            pixel_spacing_y=None,
            calibrated=False,
        )

    @classmethod
    def manual(cls, mm_per_px: float) -> "ImageCalibration":
        s = max(1e-9, float(mm_per_px))
        return cls(
            source="Manual",
            pixel_spacing_x=s,
            pixel_spacing_y=s,
            calibrated=True,
        )

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "pixelSpacingX": self.pixel_spacing_x,
            "pixelSpacingY": self.pixel_spacing_y,
            "unit": self.unit,
            "calibrated": self.calibrated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageCalibration":
        src = data.get("source", "Unknown")
        if src not in (
            "PixelSpacing",
            "ImagerPixelSpacing",
            "NominalScannedPixelSpacing",
            "PhysicalDelta",
            "Manual",
            "Unknown",
        ):
            src = "Unknown"
        x = data.get("pixelSpacingX")
        y = data.get("pixelSpacingY")
        calibrated = bool(data.get("calibrated", False)) and x is not None and y is not None
        return cls(
            source=src,  # type: ignore[arg-type]
            pixel_spacing_x=float(x) if x is not None else None,
            pixel_spacing_y=float(y) if y is not None else None,
            calibrated=calibrated,
        )
