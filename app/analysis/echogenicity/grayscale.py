"""Conversión a escala de grises uint8 (0–255)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


def to_grayscale_u8(image: np.ndarray) -> np.ndarray:
    """
    Convierte un array de imagen a gris uint8 2D.

    - 2D: se escala/castea a uint8.
    - RGB/BGR HxWx3: luminancia BT.601 ``0.299R + 0.587G + 0.114B``.
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Imagen vacía o inválida")

    arr = image
    if arr.ndim == 2:
        if arr.dtype == np.uint8:
            return np.ascontiguousarray(arr)
        amin = float(arr.min())
        amax = float(arr.max())
        if amax > amin:
            scaled = (arr.astype(np.float64) - amin) * (255.0 / (amax - amin))
        else:
            scaled = np.zeros_like(arr, dtype=np.float64)
        return np.clip(scaled, 0, 255).astype(np.uint8)

    if arr.ndim == 3 and arr.shape[-1] >= 3:
        # Asumimos canal orden RGB (como dicom_pixel_rgb / PIL).
        rgb = arr[..., :3].astype(np.float64)
        gray = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        return np.clip(gray, 0, 255).astype(np.uint8)

    raise ValueError(f"Forma de imagen no soportada: {arr.shape}")


def load_gray_from_path(path: Path) -> Optional[np.ndarray]:
    """
    Carga un archivo de imagen (PNG/JPG/…) y lo convierte a gris uint8.

    Usa los píxeles del archivo en disco, no un pixmap de pantalla.
    """
    try:
        from PIL import Image as PILImage
    except ImportError:
        return None
    try:
        with PILImage.open(path) as im:
            rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
        return to_grayscale_u8(rgb)
    except Exception:  # noqa: BLE001
        return None
