"""Exportación JSON de ROI libre."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.analysis.roi_freehand.models import FreehandAnalysisResult


def result_to_dict(result: FreehandAnalysisResult) -> dict[str, Any]:
    """Serializa al schema del brief de ROI libre."""
    g = result.geometry
    s = result.statistics
    d = result.distribution
    # id numérico si el label es "ROI N"
    roi_num = 1
    parts = result.roi_label.split()
    if parts and parts[-1].isdigit():
        roi_num = int(parts[-1])

    return {
        "id": roi_num,
        "type": "freehand",
        "points": [{"x": p.x, "y": p.y} for p in result.polygon.points],
        "pixelArea": round(g.pixel_area, 2),
        "areaMM2": None if g.area_mm2 is None else round(g.area_mm2, 2),
        "areaCM2": None if g.area_cm2 is None else round(g.area_cm2, 2),
        "perimeterMM": None if g.perimeter_mm is None else round(g.perimeter_mm, 2),
        "perimeterPx": round(g.perimeter_px, 2),
        "centroid": {
            "x": round(g.centroid_x, 1),
            "y": round(g.centroid_y, 1),
        },
        "boundingBox": {
            "x": g.bbox_x,
            "y": g.bbox_y,
            "width": g.bbox_width,
            "height": g.bbox_height,
        },
        "pixelCount": s.pixel_count,
        "statistics": {
            "min": s.min_intensity,
            "max": s.max_intensity,
            "mean": round(s.mean, 1),
            "median": round(s.median, 1),
            "stdDev": round(s.std_dev, 1),
        },
        "whiteThreshold": result.white_threshold,
        "whitePercentage": round(result.white_percentage, 1),
        "distribution": {
            "black": round(d.black, 1),
            "dark": round(d.dark, 1),
            "gray": round(d.gray, 1),
            "light": round(d.light, 1),
            "white": round(d.white, 1),
        },
    }


def export_freehand_roi(result: FreehandAnalysisResult, path: Path) -> Path:
    """Escribe el análisis a un archivo JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
