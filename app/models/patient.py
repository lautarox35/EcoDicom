"""Modelo de paciente veterinario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Patient:
    animal_name: str = ""
    patient_id: str = ""
    species: str = ""
    breed: str = ""
    sex: str = ""  # M, F, O, U
    age: str = ""  # texto libre, ej. "5Y" o "3 años"
    weight_kg: Optional[float] = None
    owner: str = ""
    veterinarian: str = ""
    clinic: str = ""
    birth_date: str = ""  # YYYYMMDD opcional
    db_id: Optional[int] = field(default=None, repr=False)

    def display_name(self) -> str:
        name = self.animal_name.strip() or "SinNombre"
        pid = self.patient_id.strip() or "SinID"
        return f"{pid}_{name}"

    def dicom_patient_name(self) -> str:
        """Formato PN DICOM: Apellido^Nombre (usamos nombre del animal)."""
        name = self.animal_name.strip() or "UNKNOWN"
        return name.replace(" ", "^")
