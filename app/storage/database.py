"""Persistencia SQLite local."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.config import DATABASE_PATH
from app.models.patient import Patient
from app.models.study import Study


class Database:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DATABASE_PATH

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT NOT NULL,
                    animal_name TEXT NOT NULL,
                    species TEXT,
                    breed TEXT,
                    sex TEXT,
                    age TEXT,
                    weight_kg REAL,
                    owner TEXT,
                    veterinarian TEXT,
                    clinic TEXT,
                    birth_date TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(patient_id, animal_name)
                );

                CREATE TABLE IF NOT EXISTS studies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_db_id INTEGER NOT NULL,
                    study_instance_uid TEXT NOT NULL UNIQUE,
                    series_instance_uid TEXT,
                    study_datetime TEXT NOT NULL,
                    study_type TEXT,
                    organ TEXT,
                    observations TEXT,
                    folder_path TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (patient_db_id) REFERENCES patients(id)
                );

                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    study_db_id INTEGER NOT NULL,
                    source_path TEXT,
                    dicom_path TEXT,
                    sop_instance_uid TEXT,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (study_db_id) REFERENCES studies(id)
                );
                """
            )

    def upsert_patient(self, patient: Patient) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM patients WHERE patient_id = ? AND animal_name = ?",
                (patient.patient_id, patient.animal_name),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE patients SET
                        species=?, breed=?, sex=?, age=?, weight_kg=?,
                        owner=?, veterinarian=?, clinic=?, birth_date=?
                    WHERE id=?
                    """,
                    (
                        patient.species,
                        patient.breed,
                        patient.sex,
                        patient.age,
                        patient.weight_kg,
                        patient.owner,
                        patient.veterinarian,
                        patient.clinic,
                        patient.birth_date,
                        row["id"],
                    ),
                )
                patient.db_id = int(row["id"])
                return patient.db_id

            cur = conn.execute(
                """
                INSERT INTO patients (
                    patient_id, animal_name, species, breed, sex, age, weight_kg,
                    owner, veterinarian, clinic, birth_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient.patient_id,
                    patient.animal_name,
                    patient.species,
                    patient.breed,
                    patient.sex,
                    patient.age,
                    patient.weight_kg,
                    patient.owner,
                    patient.veterinarian,
                    patient.clinic,
                    patient.birth_date,
                    now,
                ),
            )
            patient.db_id = int(cur.lastrowid)
            return patient.db_id

    def save_study(
        self,
        patient: Patient,
        study: Study,
        folder_path: Path,
        images: list[dict[str, Any]],
    ) -> int:
        patient_db_id = self.upsert_patient(patient)
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM studies WHERE study_instance_uid = ?",
                (study.study_instance_uid,),
            ).fetchone()
            if existing:
                study_db_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE studies SET
                        series_instance_uid=?, study_datetime=?, study_type=?,
                        organ=?, observations=?, folder_path=?
                    WHERE id=?
                    """,
                    (
                        study.series_instance_uid,
                        study.study_datetime.isoformat(timespec="seconds"),
                        study.study_type,
                        study.organ,
                        study.observations,
                        str(folder_path),
                        study_db_id,
                    ),
                )
                conn.execute("DELETE FROM images WHERE study_db_id = ?", (study_db_id,))
            else:
                cur = conn.execute(
                    """
                    INSERT INTO studies (
                        patient_db_id, study_instance_uid, series_instance_uid,
                        study_datetime, study_type, organ, observations,
                        folder_path, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        patient_db_id,
                        study.study_instance_uid,
                        study.series_instance_uid,
                        study.study_datetime.isoformat(timespec="seconds"),
                        study.study_type,
                        study.organ,
                        study.observations,
                        str(folder_path),
                        now,
                    ),
                )
                study_db_id = int(cur.lastrowid)

            for img in images:
                conn.execute(
                    """
                    INSERT INTO images (
                        study_db_id, source_path, dicom_path, sop_instance_uid,
                        source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        study_db_id,
                        img.get("source_path"),
                        img.get("dicom_path"),
                        img.get("sop_instance_uid"),
                        img.get("source", "import"),
                        now,
                    ),
                )
            study.db_id = study_db_id
            return study_db_id

    def list_recent_studies(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.id AS study_db_id,
                    s.study_instance_uid,
                    s.series_instance_uid,
                    s.study_datetime,
                    s.study_type,
                    s.organ,
                    s.observations,
                    s.folder_path,
                    s.created_at,
                    p.id AS patient_db_id,
                    p.patient_id,
                    p.animal_name,
                    p.species,
                    p.breed,
                    p.sex,
                    p.age,
                    p.weight_kg,
                    p.owner,
                    p.veterinarian,
                    p.clinic,
                    p.birth_date,
                    (
                        SELECT COUNT(*) FROM images i WHERE i.study_db_id = s.id
                    ) AS image_count
                FROM studies s
                JOIN patients p ON p.id = s.patient_db_id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_study_detail(self, study_db_id: int) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    s.id AS study_db_id,
                    s.study_instance_uid,
                    s.series_instance_uid,
                    s.study_datetime,
                    s.study_type,
                    s.organ,
                    s.observations,
                    s.folder_path,
                    s.created_at,
                    p.id AS patient_db_id,
                    p.patient_id,
                    p.animal_name,
                    p.species,
                    p.breed,
                    p.sex,
                    p.age,
                    p.weight_kg,
                    p.owner,
                    p.veterinarian,
                    p.clinic,
                    p.birth_date
                FROM studies s
                JOIN patients p ON p.id = s.patient_db_id
                WHERE s.id = ?
                """,
                (study_db_id,),
            ).fetchone()
            if not row:
                return None
            detail = dict(row)
            images = conn.execute(
                """
                SELECT id, source_path, dicom_path, sop_instance_uid, source, created_at
                FROM images
                WHERE study_db_id = ?
                ORDER BY id
                """,
                (study_db_id,),
            ).fetchall()
            detail["images"] = [dict(i) for i in images]
            return detail

    def find_study_by_uid(self, study_instance_uid: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM studies WHERE study_instance_uid = ?
                """,
                (study_instance_uid,),
            ).fetchone()
            if not row:
                return None
            return self.get_study_detail(int(row["id"]))

    def update_study_fields(
        self,
        study_db_id: int,
        patient_fields: dict[str, Any],
        study_fields: dict[str, Any],
    ) -> None:
        """Actualiza paciente + estudio en la base local."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT patient_db_id FROM studies WHERE id = ?",
                (study_db_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"Estudio id={study_db_id} no encontrado")
            patient_db_id = int(row["patient_db_id"])
            conn.execute(
                """
                UPDATE patients SET
                    patient_id=?, animal_name=?, species=?, breed=?, sex=?,
                    age=?, weight_kg=?, owner=?, veterinarian=?, clinic=?, birth_date=?
                WHERE id=?
                """,
                (
                    patient_fields.get("patient_id", ""),
                    patient_fields.get("animal_name", ""),
                    patient_fields.get("species", ""),
                    patient_fields.get("breed", ""),
                    patient_fields.get("sex", ""),
                    patient_fields.get("age", ""),
                    patient_fields.get("weight_kg"),
                    patient_fields.get("owner", ""),
                    patient_fields.get("veterinarian", ""),
                    patient_fields.get("clinic", ""),
                    patient_fields.get("birth_date", ""),
                    patient_db_id,
                ),
            )
            conn.execute(
                """
                UPDATE studies SET
                    study_type=?, organ=?, observations=?
                WHERE id=?
                """,
                (
                    study_fields.get("study_type", ""),
                    study_fields.get("organ", ""),
                    study_fields.get("observations", ""),
                    study_db_id,
                ),
            )

    def delete_study(self, study_db_id: int, delete_files: bool = True) -> list[str]:
        """
        Borra estudio e imágenes de la DB.
        Si el paciente queda sin estudios, también se elimina (libera el PatientID).
        Si delete_files=True, elimina los .dcm y carpetas vacías.
        """
        removed: list[str] = []
        folder_path: Optional[str] = None
        patient_db_id: Optional[int] = None
        image_paths: list[str] = []

        with self.connect() as conn:
            study = conn.execute(
                "SELECT patient_db_id, folder_path FROM studies WHERE id = ?",
                (study_db_id,),
            ).fetchone()
            if not study:
                return removed
            patient_db_id = int(study["patient_db_id"])
            folder_path = study["folder_path"]
            images = conn.execute(
                "SELECT dicom_path FROM images WHERE study_db_id = ?",
                (study_db_id,),
            ).fetchall()
            image_paths = [str(i["dicom_path"]) for i in images if i["dicom_path"]]

            conn.execute("DELETE FROM images WHERE study_db_id = ?", (study_db_id,))
            conn.execute("DELETE FROM studies WHERE id = ?", (study_db_id,))

            remaining = conn.execute(
                "SELECT COUNT(*) AS n FROM studies WHERE patient_db_id = ?",
                (patient_db_id,),
            ).fetchone()
            if remaining and int(remaining["n"]) == 0:
                conn.execute("DELETE FROM patients WHERE id = ?", (patient_db_id,))
            conn.commit()

        if delete_files:
            paths: list[Path] = [Path(p) for p in image_paths]
            if folder_path:
                folder = Path(folder_path)
                if folder.is_dir():
                    paths.extend(folder.glob("*.dcm"))
            seen: set[str] = set()
            for path in paths:
                key = str(path.resolve()) if path.exists() else str(path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    if path.is_file():
                        path.unlink()
                        removed.append(str(path))
                except OSError:
                    pass
            self._remove_empty_dirs(folder_path)
        return removed

    def _remove_empty_dirs(self, folder_path: Optional[str]) -> None:
        if not folder_path:
            return
        folder = Path(folder_path)
        try:
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
            parent = folder.parent
            if parent.is_dir() and not any(parent.iterdir()):
                # Solo vaciar carpetas bajo Estudios/
                from app.config import STUDIES_DIR

                if STUDIES_DIR in parent.parents or parent == STUDIES_DIR:
                    parent.rmdir()
        except OSError:
            pass

    def delete_image_record(self, dicom_path: str) -> None:
        """Borra el registro de imagen; si el estudio queda vacío, lo elimina (y paciente huérfano)."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT study_db_id FROM images WHERE dicom_path = ?",
                (dicom_path,),
            ).fetchone()
            conn.execute("DELETE FROM images WHERE dicom_path = ?", (dicom_path,))
            if row:
                study_db_id = int(row["study_db_id"])
                left = conn.execute(
                    "SELECT COUNT(*) AS n FROM images WHERE study_db_id = ?",
                    (study_db_id,),
                ).fetchone()
                if left and int(left["n"]) == 0:
                    study = conn.execute(
                        "SELECT patient_db_id, folder_path FROM studies WHERE id = ?",
                        (study_db_id,),
                    ).fetchone()
                    conn.execute("DELETE FROM studies WHERE id = ?", (study_db_id,))
                    if study:
                        patient_db_id = int(study["patient_db_id"])
                        rem = conn.execute(
                            "SELECT COUNT(*) AS n FROM studies WHERE patient_db_id = ?",
                            (patient_db_id,),
                        ).fetchone()
                        if rem and int(rem["n"]) == 0:
                            conn.execute(
                                "DELETE FROM patients WHERE id = ?", (patient_db_id,)
                            )
            conn.commit()

    def delete_studies_for_folder(self, folder: Path) -> int:
        """Elimina de la DB todos los estudios asociados a una carpeta."""
        try:
            folder_resolved = folder.resolve()
        except OSError:
            folder_resolved = folder
        ids: list[int] = []
        with self.connect() as conn:
            for row in conn.execute("SELECT id, folder_path FROM studies").fetchall():
                fp = row["folder_path"]
                if not fp:
                    continue
                try:
                    if Path(fp).resolve() == folder_resolved:
                        ids.append(int(row["id"]))
                except OSError:
                    if str(fp) == str(folder):
                        ids.append(int(row["id"]))
            for row in conn.execute(
                "SELECT DISTINCT study_db_id, dicom_path FROM images"
            ).fetchall():
                dcm = row["dicom_path"]
                if not dcm:
                    continue
                try:
                    if Path(dcm).resolve().parent == folder_resolved:
                        ids.append(int(row["study_db_id"]))
                except OSError:
                    if Path(dcm).parent == folder:
                        ids.append(int(row["study_db_id"]))
        removed = 0
        for sid in sorted(set(ids)):
            self.delete_study(sid, delete_files=False)
            removed += 1
        return removed

    def purge_orphaned_studies(self) -> int:
        """
        Elimina de la DB estudios sin carpeta ni archivos .dcm en disco
        (p. ej. borrados manualmente desde el Explorador).
        También limpia pacientes sin estudios.
        """
        removed = 0
        for study in self.list_recent_studies(limit=500):
            study_id = int(study["study_db_id"])
            detail = self.get_study_detail(study_id)
            if not detail:
                continue
            has_file = False
            folder = detail.get("folder_path")
            if folder and Path(folder).is_dir():
                if any(Path(folder).glob("*.dcm")):
                    has_file = True
            if not has_file:
                for img in detail.get("images") or []:
                    dcm = img.get("dicom_path")
                    if dcm and Path(dcm).is_file():
                        has_file = True
                        break
            if not has_file:
                self.delete_study(study_id, delete_files=False)
                removed += 1

        # Pacientes huérfanos (sin ningún estudio)
        with self.connect() as conn:
            orphans = conn.execute(
                """
                SELECT p.id FROM patients p
                LEFT JOIN studies s ON s.patient_db_id = p.id
                WHERE s.id IS NULL
                """
            ).fetchall()
            for row in orphans:
                conn.execute("DELETE FROM patients WHERE id = ?", (int(row["id"]),))
            conn.commit()
        return removed

