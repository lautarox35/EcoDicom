"""Modelos de ROI libre (polígono)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.analysis.echogenicity.models import IntensityDistribution, ROIStatistics


@dataclass(frozen=True)
class Point2D:
    """Punto en coordenadas de imagen nativa."""

    x: float
    y: float


@dataclass
class PolygonROI:
    """
    Polígono ROI en coords de imagen.

    Preparado para multi-ROI (roi_id, color, visible).
    """

    points: list[Point2D] = field(default_factory=list)
    roi_id: str = "ROI 1"
    color: str = "#14b8a6"
    visible: bool = True
    closed: bool = False

    def copy(self) -> "PolygonROI":
        """Copia profunda de puntos."""
        return PolygonROI(
            points=[Point2D(p.x, p.y) for p in self.points],
            roi_id=self.roi_id,
            color=self.color,
            visible=self.visible,
            closed=self.closed,
        )

    def as_xy_arrays(self) -> tuple[list[float], list[float]]:
        """Listas x e y separadas."""
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return xs, ys

    def as_int_vertices(self) -> list[tuple[int, int]]:
        """Vértices enteros para rasterizado."""
        return [(int(round(p.x)), int(round(p.y))) for p in self.points]


@dataclass(frozen=True)
class GeometryResult:
    """Geometría del polígono cerrado."""

    pixel_area: float
    area_mm2: Optional[float]
    area_cm2: Optional[float]
    perimeter_px: float
    perimeter_mm: Optional[float]
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    row_spacing_mm: Optional[float]
    col_spacing_mm: Optional[float]


@dataclass(frozen=True)
class FreehandAnalysisResult:
    """Resultado completo: geometría + ecogenicidad dentro del polígono."""

    polygon: PolygonROI
    geometry: GeometryResult
    statistics: ROIStatistics
    white_threshold: int
    white_percentage: float
    distribution: IntensityDistribution
    histogram: tuple[int, ...] = field(default_factory=tuple)
    roi_label: str = "ROI 1"
