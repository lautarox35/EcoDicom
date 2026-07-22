"""Captura de frames con OpenCV (webcam o capturadora USB)."""

from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.config import DEFAULT_CAMERA_INDEX, SAMPLE_IMAGES_DIR, ensure_directories


def _camera_backends() -> list[int]:
    """Backends preferidos por plataforma (orden de intento)."""
    system = platform.system()
    if system == "Windows":
        return [cv2.CAP_DSHOW, cv2.CAP_ANY]
    if system == "Darwin":
        # AVFoundation es el backend nativo en macOS
        backends = [cv2.CAP_ANY]
        if hasattr(cv2, "CAP_AVFOUNDATION"):
            backends.insert(0, cv2.CAP_AVFOUNDATION)
        return backends
    return [cv2.CAP_ANY]


def _open_capture(camera_index: int) -> cv2.VideoCapture:
    last: Optional[cv2.VideoCapture] = None
    for backend in _camera_backends():
        cap = cv2.VideoCapture(camera_index, backend)
        if cap.isOpened():
            return cap
        cap.release()
        last = cap
    return last if last is not None else cv2.VideoCapture(camera_index)


def list_camera_indices(max_index: int = 5) -> list[int]:
    available: list[int] = []
    for i in range(max_index):
        cap = _open_capture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
        else:
            cap.release()
    return available


def capture_frame(
    camera_index: int = DEFAULT_CAMERA_INDEX,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Captura un frame de la cámara/capturadora y lo guarda como PNG.
    Lanza RuntimeError si no hay dispositivo disponible.
    """
    ensure_directories()
    out_dir = Path(output_dir) if output_dir else SAMPLE_IMAGES_DIR / "captures"
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = _open_capture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(
            f"No se pudo abrir la cámara/capturadora en el índice {camera_index}. "
            "Conecte una capturadora de video o use Importar imagen. "
            "En macOS, conceda permiso de Cámara a EcoDICOM en Ajustes del Sistema."
        )

    frame: Optional[np.ndarray] = None
    for _ in range(5):
        ok, frame = cap.read()
        if not ok:
            frame = None
    cap.release()

    if frame is None:
        raise RuntimeError("La cámara está abierta pero no devolvió imagen.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"capture_{stamp}.png"
    if not cv2.imwrite(str(out_path), frame):
        raise RuntimeError(f"No se pudo guardar la captura en {out_path}")
    return out_path
