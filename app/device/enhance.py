"""Mejora de calidad para frames de easierCAP / ecografía."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.config import (
    ENHANCE_CLAHE_CLIP,
    ENHANCE_DENOISE,
    ENHANCE_ENABLED,
    ENHANCE_SHARPEN,
    ENHANCE_UPSCALE,
)


@dataclass
class EnhanceSettings:
    enabled: bool = ENHANCE_ENABLED
    clahe_clip: float = ENHANCE_CLAHE_CLIP
    denoise: float = ENHANCE_DENOISE
    sharpen: float = ENHANCE_SHARPEN
    upscale: float = ENHANCE_UPSCALE


_DEFAULT = EnhanceSettings()


def enhance_frame(
    frame: np.ndarray,
    settings: EnhanceSettings | None = None,
) -> np.ndarray:
    """
    Realza contraste/nitidez típicos de señal composite (easierCAP).
    No altera el tamaño salvo upscale > 1.
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return frame

    cfg = settings or _DEFAULT
    if not cfg.enabled:
        return frame

    out = frame
    if cfg.upscale and cfg.upscale > 1.01:
        out = cv2.resize(
            out,
            None,
            fx=cfg.upscale,
            fy=cfg.upscale,
            interpolation=cv2.INTER_CUBIC,
        )

    # Denoise suave (composite suele ser ruidoso)
    if cfg.denoise > 0:
        d = max(1, int(round(cfg.denoise)))
        # d impar para bilateral
        if d % 2 == 0:
            d += 1
        out = cv2.bilateralFilter(out, d=d, sigmaColor=40, sigmaSpace=40)

    # CLAHE en canal de luminancia (mejor para ecografía)
    if cfg.clahe_clip > 0:
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=float(cfg.clahe_clip), tileGridSize=(8, 8))
        l_ch = clahe.apply(l_ch)
        out = cv2.cvtColor(cv2.merge([l_ch, a_ch, b_ch]), cv2.COLOR_LAB2BGR)

    # Unsharp mask
    if cfg.sharpen > 0:
        blur = cv2.GaussianBlur(out, (0, 0), sigmaX=1.2)
        amount = float(cfg.sharpen)
        out = cv2.addWeighted(out, 1.0 + amount, blur, -amount, 0)

    return out
