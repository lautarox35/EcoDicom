"""Modelo de estudio de ecografía."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StudyType(str, Enum):
    ABDOMINAL = "Ecografía abdominal"
    CARDIAC = "Ecografía cardíaca"
    REPRODUCTIVE = "Ecografía reproductiva"
    OTHER = "Otro"


STUDY_TYPE_CHOICES = [t.value for t in StudyType]


@dataclass
class Study:
    study_datetime: datetime = field(default_factory=datetime.now)
    study_type: str = StudyType.ABDOMINAL.value
    organ: str = ""
    observations: str = ""
    # Parámetros de adquisición (manuales, como en pantalla del ecógrafo)
    probe: str = ""  # Prob / sonda
    frequency: str = ""  # Freq
    fav: str = ""  # Fav
    gain: str = ""  # Ganancia
    study_instance_uid: str = ""
    series_instance_uid: str = ""
    db_id: Optional[int] = field(default=None, repr=False)

    def study_description(self) -> str:
        parts = [self.study_type]
        if self.organ.strip():
            parts.append(self.organ.strip())
        return " - ".join(parts)

    def acquisition_lines(self) -> list[str]:
        """Líneas de metadatos de adquisición no vacías."""
        mapping = [
            ("Prob", self.probe),
            ("Freq", self.frequency),
            ("Fav", self.fav),
            ("Gain", self.gain),
        ]
        return [f"{label}: {value.strip()}" for label, value in mapping if value.strip()]

    def image_comments(self) -> str:
        """Observaciones + parámetros de adquisición para tag ImageComments."""
        parts: list[str] = []
        acq = self.acquisition_lines()
        if acq:
            parts.append("Adquisición: " + " | ".join(acq))
        if self.observations.strip():
            parts.append(self.observations.strip())
        return "\n".join(parts)[:10240]

    def date_str(self) -> str:
        return self.study_datetime.strftime("%Y%m%d")

    def time_str(self) -> str:
        return self.study_datetime.strftime("%H%M%S")

    def folder_date(self) -> str:
        return self.study_datetime.strftime("%Y-%m-%d")
