"""Tests del generador DICOM."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.dicom.generator import create_ultrasound_dicom, save_dicom
from app.models.patient import Patient
from app.models.study import Study, StudyType


@pytest.fixture()
def sample_png(tmp_path: Path) -> Path:
    from PIL import Image

    path = tmp_path / "test.png"
    Image.new("RGB", (320, 240), color=(30, 30, 30)).save(path)
    return path


def test_create_ultrasound_dicom(sample_png: Path, tmp_path: Path) -> None:
    patient = Patient(
        animal_name="Rex",
        patient_id="T-100",
        species="Canino",
        breed="Mestizo",
        sex="M",
        age="3 años",
        weight_kg=12.0,
        owner="Owner Test",
        veterinarian="Vet Test",
        clinic="Clinic Test",
    )
    study = Study(
        study_datetime=datetime(2026, 7, 22, 15, 30, 0),
        study_type=StudyType.ABDOMINAL.value,
        organ="Bazo",
        observations="Test unitario",
    )
    ds = create_ultrasound_dicom(sample_png, patient, study)
    assert ds.Modality == "US"
    assert ds.PatientID == "T-100"
    assert str(ds.PatientSpeciesDescription) == "Canino"
    assert ds.Rows == 240
    assert ds.Columns == 320
    assert ds.StudyInstanceUID
    assert ds.SeriesInstanceUID
    assert ds.SOPInstanceUID
    assert ds.StudyInstanceUID != ds.SeriesInstanceUID

    out = tmp_path / "out.dcm"
    save_dicom(ds, out)
    assert out.is_file()
    assert out.stat().st_size > 0

    import pydicom

    loaded = pydicom.dcmread(out)
    assert loaded.Modality == "US"
    assert loaded.PatientName is not None
