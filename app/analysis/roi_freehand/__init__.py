"""Análisis geométrico y de ecogenicidad para ROI libre (polígono)."""

from app.analysis.roi_freehand.analyzer import FreehandROIAnalyzer
from app.analysis.roi_freehand.export import export_freehand_roi, result_to_dict
from app.analysis.roi_freehand.geometry import compute_geometry
from app.analysis.roi_freehand.models import (
    FreehandAnalysisResult,
    GeometryResult,
    Point2D,
    PolygonROI,
)
from app.analysis.roi_freehand.spacing import read_pixel_spacing_mm, resolve_spacing_mm

__all__ = [
    "FreehandAnalysisResult",
    "FreehandROIAnalyzer",
    "GeometryResult",
    "Point2D",
    "PolygonROI",
    "compute_geometry",
    "export_freehand_roi",
    "read_pixel_spacing_mm",
    "resolve_spacing_mm",
    "result_to_dict",
]
