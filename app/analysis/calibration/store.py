"""Persistencia de calibración manual (JSON, sin modificar el DICOM)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from app.analysis.calibration.models import ImageCalibration
from app.config import PROJECT_ROOT

CALIBRATIONS_DIR = PROJECT_ROOT / "calibraciones"


def _key_for_path(image_path: Path) -> str:
    resolved = str(image_path.resolve())
    return hashlib.sha1(resolved.encode("utf-8")).hexdigest()


def calibration_file_for(image_path: Path) -> Path:
    """Ruta del JSON de calibración asociada a una imagen."""
    CALIBRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    return CALIBRATIONS_DIR / f"{_key_for_path(image_path)}.json"


def save_manual_calibration(image_path: Path, calib: ImageCalibration) -> Path:
    """Guarda calibración (típicamente Manual) asociada a la imagen."""
    path = calibration_file_for(image_path)
    payload = {
        "imagePath": str(image_path.resolve()),
        **calib.to_dict(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_manual_calibration(image_path: Path) -> Optional[ImageCalibration]:
    """Carga calibración guardada para la imagen, o None."""
    path = calibration_file_for(image_path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        calib = ImageCalibration.from_dict(data)
        if calib.calibrated:
            return calib
    except Exception:  # noqa: BLE001
        return None
    return None
