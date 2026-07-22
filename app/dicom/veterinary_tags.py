"""Tags DICOM veterinarios (Patient Module no humano)."""

from __future__ import annotations

import re

from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from app.models.patient import Patient


def _normalize_sex(sex: str) -> str:
    value = (sex or "").strip().upper()
    mapping = {
        "M": "M",
        "MALE": "M",
        "MACHO": "M",
        "F": "F",
        "FEMALE": "F",
        "HEMBRA": "F",
        "O": "O",
        "OTHER": "O",
        "OTRO": "O",
        "U": "U",
        "UNKNOWN": "U",
        "DESCONOCIDO": "U",
    }
    return mapping.get(value, "U" if value else "")


def _format_patient_age(age: str) -> str:
    """Convierte edad libre a formato DICOM AS (nnnD/W/M/Y) si es posible."""
    raw = (age or "").strip()
    if not raw:
        return ""

    # Ya en formato DICOM aproximado
    if re.fullmatch(r"\d{1,3}[DWMY]", raw.upper()):
        num = raw[:-1].zfill(3)
        return f"{num}{raw[-1].upper()}"

    match = re.search(r"(\d+)\s*(año|anos|años|year|years|y|a)?", raw, re.IGNORECASE)
    if match:
        years = int(match.group(1))
        return f"{years:03d}Y"

    return ""


def apply_veterinary_patient_tags(ds: Dataset, patient: Patient) -> None:
    """Aplica tags del Patient Module veterinario al dataset."""
    ds.PatientName = patient.dicom_patient_name()
    ds.PatientID = patient.patient_id.strip() or "UNKNOWN"

    if patient.birth_date.strip():
        ds.PatientBirthDate = patient.birth_date.strip()
    else:
        ds.PatientBirthDate = ""

    sex = _normalize_sex(patient.sex)
    if sex:
        ds.PatientSex = sex

    age = _format_patient_age(patient.age)
    if age:
        ds.PatientAge = age

    if patient.weight_kg is not None:
        ds.PatientWeight = float(patient.weight_kg)

    # Tags veterinarios estándar
    if patient.species.strip():
        ds.PatientSpeciesDescription = patient.species.strip()

    if patient.breed.strip():
        ds.PatientBreedDescription = patient.breed.strip()

    # BreedRegistrationSequence requerido (tipo 2C) para no-humanos: puede estar vacío
    breed_item = Dataset()
    if patient.patient_id.strip():
        breed_item.BreedRegistrationNumber = patient.patient_id.strip()
    # Tipo 2C: secuencia presente; ítem opcional con número si hay ID
    if patient.patient_id.strip():
        ds.BreedRegistrationSequence = Sequence([breed_item])
    else:
        ds.BreedRegistrationSequence = Sequence([])

    if patient.owner.strip():
        ds.ResponsiblePerson = patient.owner.strip()
        ds.ResponsiblePersonRole = "OWNER"

    if patient.clinic.strip():
        ds.InstitutionName = patient.clinic.strip()

    if patient.veterinarian.strip():
        ds.ReferringPhysicianName = patient.veterinarian.strip().replace(" ", "^")
        ds.OperatorsName = patient.veterinarian.strip().replace(" ", "^")


def private_creator_block() -> tuple[str, str]:
    """Identificador de bloque privado EcoDICOM (para uso futuro)."""
    return ("ECODICOM", "EcoDICOM Vet MVP 0.1")
