"""Lectura de metadatos e imagen de archivos DICOM generados."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
from pydicom import dcmread
from pydicom.dataset import FileDataset

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.study import Study


def _tag(ds: FileDataset, name: str, default: str = "") -> str:
    value = getattr(ds, name, None)
    if value is None:
        return default
    return str(value).strip()


def read_dicom_summary(path: Path) -> dict[str, Any]:
    """Extrae datos clínicos/técnicos legibles de un .dcm."""
    ds = dcmread(str(path), force=True)
    summary = {
        "path": str(path),
        "filename": path.name,
        "PatientName": _tag(ds, "PatientName"),
        "PatientID": _tag(ds, "PatientID"),
        "PatientSex": _tag(ds, "PatientSex"),
        "PatientAge": _tag(ds, "PatientAge"),
        "PatientWeight": _tag(ds, "PatientWeight"),
        "PatientBirthDate": _tag(ds, "PatientBirthDate"),
        "PatientSpeciesDescription": _tag(ds, "PatientSpeciesDescription"),
        "PatientBreedDescription": _tag(ds, "PatientBreedDescription"),
        "AcquisitionDeviceProcessingDescription": _tag(
            ds, "AcquisitionDeviceProcessingDescription"
        ),
        "ImageComments": _tag(ds, "ImageComments"),
        "ResponsiblePerson": _tag(ds, "ResponsiblePerson"),
        "InstitutionName": _tag(ds, "InstitutionName"),
        "ReferringPhysicianName": _tag(ds, "ReferringPhysicianName"),
        "StudyDate": _tag(ds, "StudyDate"),
        "StudyTime": _tag(ds, "StudyTime"),
        "StudyDescription": _tag(ds, "StudyDescription"),
        "Modality": _tag(ds, "Modality"),
        "StudyInstanceUID": _tag(ds, "StudyInstanceUID"),
        "SeriesInstanceUID": _tag(ds, "SeriesInstanceUID"),
        "SOPInstanceUID": _tag(ds, "SOPInstanceUID"),
        "Rows": getattr(ds, "Rows", None),
        "Columns": getattr(ds, "Columns", None),
        "PhotometricInterpretation": _tag(ds, "PhotometricInterpretation"),
    }
    return summary


def dicom_pixel_rgb(path: Path) -> Optional[np.ndarray]:
    """Devuelve array RGB uint8 para preview, o None si no hay píxeles."""
    try:
        ds = dcmread(str(path), force=True)
        if not hasattr(ds, "pixel_array"):
            return None
        arr = ds.pixel_array
    except Exception:  # noqa: BLE001
        return None

    if arr is None:
        return None

    if arr.ndim == 2:
        gray = arr.astype(np.uint8) if arr.dtype != np.uint8 else arr
        return np.stack([gray, gray, gray], axis=-1)

    if arr.ndim == 3 and arr.shape[-1] == 3:
        return arr.astype(np.uint8) if arr.dtype != np.uint8 else arr

    # Multiframe u otros: tomar primer frame si aplica
    if arr.ndim == 3 and arr.shape[0] > 0 and arr.shape[-1] != 3:
        frame = arr[0]
        if frame.ndim == 2:
            g = frame.astype(np.uint8)
            return np.stack([g, g, g], axis=-1)
    return None


def dicom_pixel_gray(path: Path) -> Optional[np.ndarray]:
    """
    Devuelve Pixel Data en escala de grises uint8 (H×W).

    Independiente del render en pantalla; usa el array DICOM original.
    """
    from app.analysis.echogenicity.grayscale import to_grayscale_u8

    rgb = dicom_pixel_rgb(path)
    if rgb is None:
        return None
    try:
        return to_grayscale_u8(rgb)
    except ValueError:
        return None


def dicom_pixel_spacing_mm(path: Path) -> Optional[tuple[float, float]]:
    """``(row_mm, col_mm)`` desde calibración DICOM, o None."""
    from app.analysis.calibration.reader import load_image_calibration

    return load_image_calibration(path).spacing_row_col


def dicom_image_calibration(path: Path):
    """Calibración espacial completa para un archivo DICOM."""
    from app.analysis.calibration.reader import load_image_calibration

    return load_image_calibration(path)


def format_summary_text(summary: dict[str, Any]) -> str:
    labels = [
        ("Paciente", "PatientName"),
        ("ID paciente", "PatientID"),
        ("Especie", "PatientSpeciesDescription"),
        ("Raza", "PatientBreedDescription"),
        ("Adquisición", "AcquisitionDeviceProcessingDescription"),
        ("Comentarios", "ImageComments"),
        ("Sexo", "PatientSex"),
        ("Edad", "PatientAge"),
        ("Peso (kg)", "PatientWeight"),
        ("Nacimiento", "PatientBirthDate"),
        ("Dueño", "ResponsiblePerson"),
        ("Veterinario", "ReferringPhysicianName"),
        ("Clínica", "InstitutionName"),
        ("Fecha estudio", "StudyDate"),
        ("Hora estudio", "StudyTime"),
        ("Descripción", "StudyDescription"),
        ("Modalidad", "Modality"),
        ("Tamaño", None),
        ("Study UID", "StudyInstanceUID"),
        ("Series UID", "SeriesInstanceUID"),
        ("SOP UID", "SOPInstanceUID"),
        ("Archivo", "filename"),
        ("Ruta", "path"),
    ]
    lines: list[str] = []
    for label, key in labels:
        if key is None:
            rows = summary.get("Rows")
            cols = summary.get("Columns")
            photo = summary.get("PhotometricInterpretation") or ""
            if rows and cols:
                lines.append(f"{label}: {cols}×{rows}  {photo}")
            continue
        value = summary.get(key) or ""
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def update_dicom_metadata(path: Path, patient: Patient, study: Study) -> None:
    """Actualiza tags de paciente/estudio en un .dcm existente (conserva píxeles)."""
    from app.dicom.veterinary_tags import apply_veterinary_patient_tags

    ds = dcmread(str(path), force=True)
    apply_veterinary_patient_tags(ds, patient)
    ds.StudyDescription = study.study_description()
    ds.SeriesDescription = study.study_description()
    comments = study.image_comments()
    if comments:
        ds.ImageComments = comments
    elif hasattr(ds, "ImageComments"):
        ds.ImageComments = ""
    if study.frequency.strip() or study.fav.strip() or study.gain.strip() or study.probe.strip():
        bits = []
        if study.probe.strip():
            bits.append(f"Prob={study.probe.strip()}")
        if study.frequency.strip():
            bits.append(f"Freq={study.frequency.strip()}")
        if study.fav.strip():
            bits.append(f"Fav={study.fav.strip()}")
        if study.gain.strip():
            bits.append(f"Gain={study.gain.strip()}")
        ds.AcquisitionDeviceProcessingDescription = "; ".join(bits)[:64]
    ds.save_as(path, enforce_file_format=True)


def save_rgb_into_dicom(path: Path, rgb: np.ndarray) -> None:
    """Reemplaza PixelData de un DICOM con una imagen RGB uint8 (anotaciones)."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("Se espera array RGB HxWx3")
    ds = dcmread(str(path), force=True)
    arr = np.ascontiguousarray(rgb.astype(np.uint8))
    rows, cols = arr.shape[0], arr.shape[1]
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 3
    ds.PhotometricInterpretation = "RGB"
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PlanarConfiguration = 0
    ds.PixelData = arr.tobytes()
    ds.save_as(path, enforce_file_format=True)
