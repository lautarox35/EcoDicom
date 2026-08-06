"""Comparación entre resultados de ecogenicidad (multi-ROI futuro)."""

from __future__ import annotations

from app.analysis.echogenicity.models import EcogenicityComparison, EcogenicityResult


def compare_ecogenicity(
    a: EcogenicityResult,
    b: EcogenicityResult,
) -> EcogenicityComparison:
    """
    Compara el porcentaje de ecogenicidad (blanco) entre dos ROI.

    La diferencia es ``|a - b|`` en puntos porcentuales.
    """
    return EcogenicityComparison(
        roi_a_label=a.roi_label,
        roi_b_label=b.roi_label,
        white_percentage_a=a.white_percentage,
        white_percentage_b=b.white_percentage,
        difference=abs(a.white_percentage - b.white_percentage),
    )
