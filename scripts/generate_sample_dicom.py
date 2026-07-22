"""Genera un DICOM de prueba desde una imagen JPG/PNG (sin UI)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Asegura import del paquete app desde la raíz del repo
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import SAMPLE_IMAGES_DIR, STUDIES_DIR, ensure_directories
from app.dicom.generator import create_ultrasound_dicom, save_dicom
from app.models.patient import Patient
from app.models.study import Study, StudyType


def ensure_sample_image() -> Path:
    """Crea un PNG de muestra si no existe ninguno."""
    ensure_directories()
    existing = list(SAMPLE_IMAGES_DIR.glob("*.png")) + list(SAMPLE_IMAGES_DIR.glob("*.jpg"))
    if existing:
        return existing[0]

    from PIL import Image, ImageDraw

    path = SAMPLE_IMAGES_DIR / "sample_ultrasound.png"
    img = Image.new("L", (640, 480), color=20)
    draw = ImageDraw.Draw(img)
    # Simula un sector ecográfico simple
    draw.pieslice((80, 40, 560, 520), start=200, end=340, fill=160)
    draw.ellipse((280, 180, 360, 260), fill=90)
    draw.text((20, 20), "EcoDICOM sample", fill=220)
    img.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un DICOM US de prueba")
    parser.add_argument(
        "-i",
        "--image",
        type=Path,
        help="Ruta a JPG/PNG (por defecto: sample_images/)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Ruta de salida .dcm",
    )
    args = parser.parse_args()

    image_path = args.image or ensure_sample_image()
    if not image_path.is_file():
        print(f"Imagen no encontrada: {image_path}", file=sys.stderr)
        return 1

    patient = Patient(
        animal_name="Luna",
        patient_id="VET-001",
        species="Canino",
        breed="Labrador Retriever",
        sex="F",
        age="5 años",
        weight_kg=28.5,
        owner="Ana Perez",
        veterinarian="Dr. Garcia",
        clinic="Clinica Vet Demo",
    )
    study = Study(
        study_datetime=datetime.now(),
        study_type=StudyType.ABDOMINAL.value,
        organ="Higado",
        observations="Estudio de prueba EcoDICOM MVP",
    )

    ds = create_ultrasound_dicom(image_path, patient, study)
    out = args.output
    if out is None:
        ensure_directories()
        folder = STUDIES_DIR / "VET-001_Luna" / study.folder_date()
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / "sample_estudio.dcm"

    save_dicom(ds, out)
    print(f"DICOM generado: {out}")
    print(f"  SOPClassUID: {ds.SOPClassUID}")
    print(f"  StudyInstanceUID: {ds.StudyInstanceUID}")
    print(f"  SeriesInstanceUID: {ds.SeriesInstanceUID}")
    print(f"  SOPInstanceUID: {ds.SOPInstanceUID}")
    print(f"  PatientName: {ds.PatientName}")
    print(f"  Species: {getattr(ds, 'PatientSpeciesDescription', '')}")
    print(f"  Modality: {ds.Modality}")
    print(f"  Rows x Cols: {ds.Rows} x {ds.Columns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
