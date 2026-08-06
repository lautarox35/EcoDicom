"""Análisis de ecogenicidad dentro de un polígono."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from app.analysis.echogenicity.analyzer import DEFAULT_WHITE_THRESHOLD, EcogenicityAnalyzer
from app.analysis.echogenicity.histogram import HistogramGenerator
from app.analysis.roi_freehand.geometry import compute_geometry
from app.analysis.roi_freehand.mask import polygon_mask
from app.analysis.roi_freehand.models import FreehandAnalysisResult, PolygonROI


class FreehandROIAnalyzer:
    """Combina geometría + ecogenicidad solo sobre píxeles del polígono."""

    def __init__(self, white_threshold: int = DEFAULT_WHITE_THRESHOLD) -> None:
        self._eco = EcogenicityAnalyzer(white_threshold)

    def set_white_threshold(self, value: int) -> None:
        """Actualiza umbral de blanco."""
        self._eco.set_white_threshold(value)

    @property
    def white_threshold(self) -> int:
        return self._eco.white_threshold

    def analyze(
        self,
        gray: np.ndarray,
        polygon: PolygonROI,
        *,
        spacing_mm: Optional[Tuple[float, float]] = None,
        roi_label: Optional[str] = None,
    ) -> Optional[FreehandAnalysisResult]:
        """
        Analiza un polígono cerrado sobre el array gris original.

        Returns
        -------
        FreehandAnalysisResult o None si no hay píxeles interiores.
        """
        if gray is None or gray.ndim != 2 or gray.size == 0:
            return None
        if not polygon.closed or len(polygon.points) < 3:
            return None

        geom = compute_geometry(polygon, spacing_mm)
        if geom is None:
            return None

        mask = polygon_mask(polygon, gray.shape[:2])
        if mask is None or not np.any(mask):
            return None

        flat = np.asarray(gray, dtype=np.uint8)[mask]
        if flat.size == 0:
            return None

        stats = EcogenicityAnalyzer._statistics(flat)
        white_pct = EcogenicityAnalyzer._white_percentage(
            flat, self._eco.white_threshold
        )
        dist = EcogenicityAnalyzer._distribution(flat)
        hist = HistogramGenerator.compute(flat)
        label = roi_label or polygon.roi_id or "ROI 1"

        return FreehandAnalysisResult(
            polygon=polygon.copy(),
            geometry=geom,
            statistics=stats,
            white_threshold=self._eco.white_threshold,
            white_percentage=white_pct,
            distribution=dist,
            histogram=hist,
            roi_label=label,
        )
