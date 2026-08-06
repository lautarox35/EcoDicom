"""Generación de histograma de intensidades 0–255."""

from __future__ import annotations

import numpy as np


class HistogramGenerator:
    """Construye histograma completo de intensidades en rango 0–255."""

    BINS = 256

    @staticmethod
    def compute(gray_roi: np.ndarray) -> tuple[int, ...]:
        """
        Calcula conteo de píxeles por intensidad.

        Parameters
        ----------
        gray_roi:
            Recorte 2D uint8 (solo píxeles del ROI).
        """
        if gray_roi is None or gray_roi.size == 0:
            return tuple(0 for _ in range(HistogramGenerator.BINS))
        flat = np.asarray(gray_roi, dtype=np.uint8).ravel()
        counts = np.bincount(flat, minlength=HistogramGenerator.BINS)
        return tuple(int(v) for v in counts[: HistogramGenerator.BINS])
