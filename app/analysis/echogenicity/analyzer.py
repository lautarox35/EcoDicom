"""Analizador de ecogenicidad sobre Pixel Data / arrays originales."""

from __future__ import annotations

from typing import Optional

import numpy as np

from app.analysis.echogenicity.histogram import HistogramGenerator
from app.analysis.echogenicity.models import (
    EcogenicityResult,
    IntensityDistribution,
    ROIRect,
    ROIStatistics,
)

DEFAULT_WHITE_THRESHOLD = 180


class EcogenicityAnalyzer:
    """
    Analiza la distribución de intensidades dentro de uno o más ROI.

    Opera únicamente sobre el recorte del ROI en el array gris original;
    no usa la imagen renderizada en pantalla.
    """

    def __init__(self, white_threshold: int = DEFAULT_WHITE_THRESHOLD) -> None:
        self.white_threshold = int(np.clip(white_threshold, 0, 255))

    def set_white_threshold(self, value: int) -> None:
        """Actualiza el umbral de blanco (0–255)."""
        self.white_threshold = int(np.clip(value, 0, 255))

    def analyze(
        self,
        gray: np.ndarray,
        roi: ROIRect,
        *,
        roi_label: Optional[str] = None,
    ) -> Optional[EcogenicityResult]:
        """
        Calcula estadísticas, % blanco, distribución e histograma del ROI.

        Returns
        -------
        EcogenicityResult o None si el ROI no contiene píxeles.
        """
        if gray is None or gray.ndim != 2 or gray.size == 0:
            return None

        img_h, img_w = gray.shape[:2]
        rect = roi.normalized().clamped(img_w, img_h)
        if rect.is_empty():
            return None

        crop = gray[rect.y : rect.y + rect.height, rect.x : rect.x + rect.width]
        if crop.size == 0:
            return None

        flat = np.asarray(crop, dtype=np.uint8).ravel()
        stats = self._statistics(flat)
        white_pct = self._white_percentage(flat, self.white_threshold)
        dist = self._distribution(flat)
        hist = HistogramGenerator.compute(crop)
        label = roi_label or rect.roi_id or "ROI 1"

        return EcogenicityResult(
            roi=ROIRect(rect.x, rect.y, rect.width, rect.height, label),
            statistics=stats,
            white_threshold=self.white_threshold,
            white_percentage=white_pct,
            distribution=dist,
            histogram=hist,
            roi_label=label,
        )

    def analyze_many(
        self,
        gray: np.ndarray,
        rois: list[ROIRect],
    ) -> list[EcogenicityResult]:
        """Analiza varios ROI (arquitectura multi-ROI)."""
        results: list[EcogenicityResult] = []
        for i, roi in enumerate(rois, start=1):
            label = roi.roi_id if roi.roi_id else f"ROI {i}"
            result = self.analyze(gray, roi, roi_label=label)
            if result is not None:
                results.append(result)
        return results

    @staticmethod
    def _statistics(flat: np.ndarray) -> ROIStatistics:
        """Estadísticas descriptivas sobre el vector de intensidades."""
        count = int(flat.size)
        return ROIStatistics(
            pixel_count=count,
            min_intensity=int(flat.min()),
            max_intensity=int(flat.max()),
            mean=float(np.mean(flat)),
            median=float(np.median(flat)),
            std_dev=float(np.std(flat)),
        )

    @staticmethod
    def _white_percentage(flat: np.ndarray, threshold: int) -> float:
        """Porcentaje de píxeles con intensidad >= umbral."""
        if flat.size == 0:
            return 0.0
        white = int(np.count_nonzero(flat >= threshold))
        return (white / flat.size) * 100.0

    @staticmethod
    def _distribution(flat: np.ndarray) -> IntensityDistribution:
        """Porcentajes por categorías de gris del brief clínico."""
        n = flat.size
        if n == 0:
            return IntensityDistribution(0.0, 0.0, 0.0, 0.0, 0.0)

        def pct(mask: np.ndarray) -> float:
            return (int(np.count_nonzero(mask)) / n) * 100.0

        return IntensityDistribution(
            black=pct(flat <= 50),
            dark=pct((flat >= 51) & (flat <= 100)),
            gray=pct((flat >= 101) & (flat <= 150)),
            light=pct((flat >= 151) & (flat <= 180)),
            white=pct(flat >= 181),
        )
