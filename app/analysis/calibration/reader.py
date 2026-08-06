"""Lectura de calibración desde tags DICOM + override manual persistido."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.analysis.calibration.models import ImageCalibration
from app.analysis.calibration.store import load_manual_calibration


# DICOM PhysicalUnitsXDirection / YDirection (US Region Calibration Module)
_UNIT_NONE = 0
_UNIT_CM = 3


def log_calibration(calib: ImageCalibration) -> None:
    """Log de calibración en consola."""
    found = {
        "PixelSpacing": "PixelSpacing encontrado",
        "ImagerPixelSpacing": "ImagerPixelSpacing encontrado",
        "NominalScannedPixelSpacing": "NominalScannedPixelSpacing encontrado",
        "PhysicalDelta": "PhysicalDelta encontrado",
        "Manual": "Calibración manual",
    }.get(calib.source)
    if found:
        print(found)
    print("Calibration:")
    print(f"  Source: {calib.source}")
    if calib.calibrated and calib.pixel_spacing_x is not None:
        print(f"  Pixel X: {calib.pixel_spacing_x:.4f} mm")
        print(f"  Pixel Y: {calib.pixel_spacing_y:.4f} mm")
    else:
        print("  Estado: Sin calibración")


def _pair_from_spacing(value: Any) -> Optional[tuple[float, float]]:
    """PixelSpacing-like: [row, col] → (row, col) mm."""
    try:
        row_s = float(value[0])
        col_s = float(value[1]) if len(value) > 1 else row_s
        if row_s > 0 and col_s > 0:
            return (row_s, col_s)
    except (TypeError, ValueError, IndexError):
        return None
    return None


def _from_spacing_tag(
    value: Any,
    source: str,
) -> Optional[ImageCalibration]:
    pair = _pair_from_spacing(value)
    if pair is None:
        return None
    row_s, col_s = pair
    # pixelSpacingX = col, pixelSpacingY = row (spec del brief)
    return ImageCalibration(
        source=source,  # type: ignore[arg-type]
        pixel_spacing_x=col_s,
        pixel_spacing_y=row_s,
        calibrated=True,
    )


def _physical_delta_to_mm(delta: float, units_code: Optional[int]) -> Optional[float]:
    """Convierte Physical Delta a mm según PhysicalUnits*Direction."""
    try:
        d = float(delta)
    except (TypeError, ValueError):
        return None
    if d <= 0:
        return None
    # 3 = cm (DICOM US Region). Sin código / None: asumir cm (práctica US).
    if units_code is None or int(units_code) in (_UNIT_NONE, _UNIT_CM):
        return d * 10.0
    # Otras unidades: tratar el delta como mm ya (p. ej. vendor non-standard).
    return d


def _from_physical_delta(ds: Any) -> Optional[ImageCalibration]:
    """PhysicalDeltaX/Y en Sequence of Ultrasound Regions o raíz."""
    dx = dy = None
    ux = uy = None

    # Preferir primera región US si existe
    seq = getattr(ds, "SequenceOfUltrasoundRegions", None)
    if seq:
        try:
            region = seq[0]
            dx = getattr(region, "PhysicalDeltaX", None)
            dy = getattr(region, "PhysicalDeltaY", None)
            ux = getattr(region, "PhysicalUnitsXDirection", None)
            uy = getattr(region, "PhysicalUnitsYDirection", None)
        except Exception:  # noqa: BLE001
            pass

    if dx is None:
        dx = getattr(ds, "PhysicalDeltaX", None)
    if dy is None:
        dy = getattr(ds, "PhysicalDeltaY", None)
    if ux is None:
        ux = getattr(ds, "PhysicalUnitsXDirection", None)
    if uy is None:
        uy = getattr(ds, "PhysicalUnitsYDirection", None)

    if dx is None or dy is None:
        return None

    try:
        ux_i = int(ux) if ux is not None else None
        uy_i = int(uy) if uy is not None else None
    except (TypeError, ValueError):
        ux_i = uy_i = None

    mm_x = _physical_delta_to_mm(dx, ux_i)
    mm_y = _physical_delta_to_mm(dy, uy_i)
    if mm_x is None or mm_y is None:
        return None

    return ImageCalibration(
        source="PhysicalDelta",
        pixel_spacing_x=mm_x,
        pixel_spacing_y=mm_y,
        calibrated=True,
    )


def read_dicom_calibration(path: Path) -> ImageCalibration:
    """
    Lee calibración desde tags DICOM con prioridad:

    1. PixelSpacing
    2. ImagerPixelSpacing
    3. NominalScannedPixelSpacing
    4. PhysicalDeltaX/Y
    5. Unknown
    """
    try:
        from pydicom import dcmread
    except ImportError:
        return ImageCalibration.unknown()

    try:
        ds = dcmread(str(path), force=True, stop_before_pixels=True)
    except Exception:  # noqa: BLE001
        return ImageCalibration.unknown()

    for attr, source in (
        ("PixelSpacing", "PixelSpacing"),
        ("ImagerPixelSpacing", "ImagerPixelSpacing"),
        ("NominalScannedPixelSpacing", "NominalScannedPixelSpacing"),
    ):
        value = getattr(ds, attr, None)
        if value is not None:
            calib = _from_spacing_tag(value, source)
            if calib is not None:
                return calib

    phys = _from_physical_delta(ds)
    if phys is not None:
        return phys

    return ImageCalibration.unknown()


def load_image_calibration(path: Optional[Path]) -> ImageCalibration:
    """
    Calibración efectiva para una imagen:

    1. Tags DICOM (si es .dcm)
    2. Calibración manual persistida
    3. Unknown
    """
    if path is None:
        return ImageCalibration.unknown()

    path = Path(path)
    calib = ImageCalibration.unknown()

    if path.suffix.lower() in {".dcm", ".dicom"} or _looks_like_dicom(path):
        calib = read_dicom_calibration(path)
        if calib.calibrated:
            log_calibration(calib)
            return calib

    manual = load_manual_calibration(path)
    if manual is not None and manual.calibrated:
        log_calibration(manual)
        return manual

    if not calib.calibrated:
        print("Calibration:\n  Source: Unknown\n  Estado: Sin calibración")
    return calib


def _looks_like_dicom(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except Exception:  # noqa: BLE001
        return False
