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

    def list_recent_studies(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.*, p.animal_name, p.patient_id
                FROM studies s
                JOIN patients p ON p.id = s.patient_db_id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
