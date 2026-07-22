"""Modelo de imagen capturada o importada."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CapturedImage:
    path: Path
    source: str = "import"  # import | capture | device
    captured_at: datetime = field(default_factory=datetime.now)
    sop_instance_uid: str = ""
    dicom_path: Optional[Path] = None
    db_id: Optional[int] = field(default=None, repr=False)

    @property
    def filename(self) -> str:
        return self.path.name
