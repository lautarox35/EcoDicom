"""Generación de archivos DICOM Ultrasound Image Storage desde JPG/PNG."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, UID, generate_uid

from app.config import APP_NAME, APP_VERSION
from app.dicom.uid import new_series_uid, new_sop_uid, new_study_uid
from app.dicom.veterinary_tags import apply_veterinary_patient_tags
from app.models.patient import Patient
from app.models.study import Study

# Ultrasound Image Storage SOP Class
ULTRASOUND_IMAGE_STORAGE = UID("1.2.840.10008.5.1.4.1.1.6.1")


def _load_pixel_array(image_path: Path) -> tuple[np.ndarray, str, int, int]:
    """
    Carga imagen y devuelve (array, photometric, samples_per_pixel, bits).
    Escala de grises → MONOCHROME2; color → RGB.
    """
    img = Image.open(image_path)
    img.load()

    if img.mode in ("L", "I;16", "I"):
        arr = np.asarray(img.convert("L"), dtype=np.uint8)
        return arr, "MONOCHROME2", 1, 8

    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.uint8)
    return arr, "RGB", 3, 8


def create_ultrasound_dicom(
    image_path: Union[str, Path],
    patient: Patient,
    study: Study,
    *,
    series_number: int = 1,
    instance_number: int = 1,
    study_uid: Optional[str] = None,
    series_uid: Optional[str] = None,
    sop_uid: Optional[str] = None,
) -> FileDataset:
    """
    Crea un Dataset DICOM válido (Ultrasound Image Storage) a partir de una imagen.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Imagen no encontrada: {path}")

    pixel_array, photometric, samples, bits = _load_pixel_array(path)

    study_uid = study_uid or study.study_instance_uid or new_study_uid()
    series_uid = series_uid or study.series_instance_uid or new_series_uid()
    sop_uid = sop_uid or new_sop_uid()

    study.study_instance_uid = study_uid
    study.series_instance_uid = series_uid

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ULTRASOUND_IMAGE_STORAGE
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.ImplementationVersionName = f"{APP_NAME}_{APP_VERSION}"[:16]

    ds = FileDataset(
        f"{sop_uid}.dcm",
        {},
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    # SOP Common
    ds.SOPClassUID = ULTRASOUND_IMAGE_STORAGE
    ds.SOPInstanceUID = sop_uid

    # Patient
    apply_veterinary_patient_tags(ds, patient)

    # Study
    ds.StudyInstanceUID = study_uid
    ds.StudyDate = study.date_str()
    ds.StudyTime = study.time_str()
    ds.StudyDescription = study.study_description()
    ds.AccessionNumber = ""
    ds.StudyID = study.date_str()

    # Series
    ds.SeriesInstanceUID = series_uid
    ds.Modality = "US"
    ds.SeriesNumber = series_number
    ds.SeriesDescription = study.study_description()
    ds.SeriesDate = study.date_str()
    ds.SeriesTime = study.time_str()

    # Equipment
    ds.Manufacturer = "EcoDICOM"
    ds.ManufacturerModelName = "WED-3100 Bridge"
    ds.SoftwareVersions = APP_VERSION
    ds.ConversionType = "WSD"

    # Image / Instance
    ds.InstanceNumber = instance_number
    now = datetime.now()
    ds.ContentDate = now.strftime("%Y%m%d")
    ds.ContentTime = now.strftime("%H%M%S")
    ds.ImageType = ["DERIVED", "SECONDARY"]

    if study.observations.strip() or study.acquisition_lines():
        ds.ImageComments = study.image_comments()

    # Metadatos de adquisición (carga manual)
    if study.frequency.strip() or study.fav.strip() or study.gain.strip() or study.probe.strip():
        acq_bits = []
        if study.probe.strip():
            acq_bits.append(f"Prob={study.probe.strip()}")
        if study.frequency.strip():
            acq_bits.append(f"Freq={study.frequency.strip()}")
        if study.fav.strip():
            acq_bits.append(f"Fav={study.fav.strip()}")
        if study.gain.strip():
            acq_bits.append(f"Gain={study.gain.strip()}")
        ds.AcquisitionDeviceProcessingDescription = "; ".join(acq_bits)[:64]

    rows, cols = pixel_array.shape[0], pixel_array.shape[1]
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = samples
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated = bits
    ds.BitsStored = bits
    ds.HighBit = bits - 1
    ds.PixelRepresentation = 0

    if samples == 3:
        ds.PlanarConfiguration = 0

    ds.PixelData = pixel_array.tobytes()
    return ds


def save_dicom(ds: FileDataset, output_path: Union[str, Path]) -> Path:
    """Guarda el dataset en disco."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.save_as(out, enforce_file_format=True)
    return out
