"""Generación de UIDs DICOM."""

from __future__ import annotations

from pydicom.uid import generate_uid

from app.config import UID_PREFIX


def new_uid() -> str:
    """Genera un UID DICOM válido bajo el prefijo configurado."""
    return generate_uid(prefix=f"{UID_PREFIX}.")


def new_study_uid() -> str:
    return new_uid()


def new_series_uid() -> str:
    return new_uid()


def new_sop_uid() -> str:
    return new_uid()
