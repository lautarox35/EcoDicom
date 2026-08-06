"""Análisis de ecogenicidad por ROI sobre datos de píxel originales."""

from app.analysis.echogenicity.analyzer import EcogenicityAnalyzer
from app.analysis.echogenicity.compare import compare_ecogenicity
from app.analysis.echogenicity.export import export_roi_analysis, result_to_dict
from app.analysis.echogenicity.grayscale import load_gray_from_path, to_grayscale_u8
from app.analysis.echogenicity.histogram import HistogramGenerator
from app.analysis.echogenicity.models import (
    EcogenicityResult,
    IntensityDistribution,
    ROIRect,
    ROIStatistics,
)

__all__ = [
    "EcogenicityAnalyzer",
    "EcogenicityResult",
    "HistogramGenerator",
    "IntensityDistribution",
    "ROIRect",
    "ROIStatistics",
    "compare_ecogenicity",
    "export_roi_analysis",
    "load_gray_from_path",
    "result_to_dict",
    "to_grayscale_u8",
]
