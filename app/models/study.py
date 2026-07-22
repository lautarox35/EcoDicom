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
    study_instance_uid: str = ""
    series_instance_uid: str = ""
    db_id: Optional[int] = field(default=None, repr=False)

    def study_description(self) -> str:
        parts = [self.study_type]
        if self.organ.strip():
            parts.append(self.organ.strip())
        return " - ".join(parts)

    def date_str(self) -> str:
        return self.study_datetime.strftime("%Y%m%d")

    def time_str(self) -> str:
        return self.study_datetime.strftime("%H%M%S")

    def folder_date(self) -> str:
        return self.study_datetime.strftime("%Y-%m-%d")
