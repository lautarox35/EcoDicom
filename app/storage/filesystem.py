"""Gestión de carpetas y archivos de estudios."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

from app.config import STUDIES_DIR, ensure_directories
from app.dicom.generator import create_ultrasound_dicom, save_dicom
from app.dicom.uid import new_series_uid, new_sop_uid, new_study_uid
from app.models.image import CapturedImage
from app.models.patient import Patient
from app.models.study import Study


def _safe_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80] or "SinNombre"


def study_folder(patient: Patient, study: Study) -> Path:
    ensure_directories()
    patient_dir = _safe_name(patient.display_name())
    date_dir = study.folder_date()
    folder = STUDIES_DIR / patient_dir / date_dir
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def export_study_dicoms(
    patient: Patient,
    study: Study,
    images: Iterable[CapturedImage],
) -> tuple[Path, list[CapturedImage]]:
    """
    Genera archivos .dcm en Estudios/Paciente/Fecha/ y actualiza UIDs.
    """
    images_list = list(images)
    if not images_list:
        raise ValueError("No hay imágenes para exportar.")

    if not study.study_instance_uid:
        study.study_instance_uid = new_study_uid()
    if not study.series_instance_uid:
        study.series_instance_uid = new_series_uid()

    folder = study_folder(patient, study)
    exported: list[CapturedImage] = []

    for index, image in enumerate(images_list, start=1):
        sop_uid = image.sop_instance_uid or new_sop_uid()
        image.sop_instance_uid = sop_uid

        ds = create_ultrasound_dicom(
            image.path,
            patient,
            study,
            series_number=1,
            instance_number=index,
            study_uid=study.study_instance_uid,
            series_uid=study.series_instance_uid,
            sop_uid=sop_uid,
        )
        out_name = f"{study.study_instance_uid}_img{index:02d}.dcm"
        # Windows path length: use short suffix if UID is very long
        if len(out_name) > 120:
            out_name = f"estudio_img{index:02d}.dcm"

        out_path = folder / out_name
        save_dicom(ds, out_path)
        image.dicom_path = out_path
        exported.append(image)

    return folder, exported
