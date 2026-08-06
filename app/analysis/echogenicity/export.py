"""Exportación de resultados de análisis ROI a JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.analysis.echogenicity.models import EcogenicityResult


def result_to_dict(result: EcogenicityResult) -> dict[str, Any]:
    """Serializa un resultado al schema JSON del brief."""
    return {
        "roi": {
            "x": result.roi.x,
            "y": result.roi.y,
            "width": result.roi.width,
            "height": result.roi.height,
            "id": result.roi_label,
        },
        "pixelCount": result.statistics.pixel_count,
        "min": result.statistics.min_intensity,
        "max": result.statistics.max_intensity,
        "mean": round(result.statistics.mean, 1),
        "median": round(result.statistics.median, 1),
        "stdDev": round(result.statistics.std_dev, 1),
        "whiteThreshold": result.white_threshold,
        "whitePercentage": round(result.white_percentage, 1),
        "distribution": {
            "black": round(result.distribution.black, 1),
            "dark": round(result.distribution.dark, 1),
            "gray": round(result.distribution.gray, 1),
            "light": round(result.distribution.light, 1),
            "white": round(result.distribution.white, 1),
        },
    }


def export_roi_analysis(result: EcogenicityResult, path: Path) -> Path:
    """
    Escribe el análisis a un archivo JSON.

    Returns
    -------
    Path del archivo escrito.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = result_to_dict(result)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
