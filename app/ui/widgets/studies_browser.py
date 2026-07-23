"""Apartado para listar, editar, borrar y anotar estudios DICOM."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import STUDIES_DIR
from app.dicom.viewer import (
    dicom_pixel_rgb,
    format_summary_text,
    read_dicom_summary,
    save_rgb_into_dicom,
    update_dicom_metadata,
)
from app.models.patient import Patient
from app.models.study import STUDY_TYPE_CHOICES, Study
from app.storage.database import Database
from app.ui.widgets.annotate_canvas import AnnotateCanvas


class StudiesBrowserDialog(QDialog):
    """Lista estudios, edita datos, borra y dibuja sobre DICOM."""

    COLORS = {
        "Rojo": QColor(255, 40, 40),
        "Amarillo": QColor(255, 220, 0),
        "Verde": QColor(40, 200, 80),
        "Blanco": QColor(255, 255, 255),
        "Cian": QColor(0, 220, 255),
    }

    def __init__(self, db: Database, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Estudios DICOM — ver / editar / dibujar / borrar")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setSizeGripEnabled(True)
        self.setMinimumSize(860, 520)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            self.resize(min(1100, int(avail.width() * 0.9)), min(640, int(avail.height() * 0.85)))
        else:
            self.resize(1000, 600)
        self._current_detail: Optional[dict[str, Any]] = None
        self._current_dicom: Optional[Path] = None
        self._build()
        self.refresh()

    def _compact_line(self) -> QLineEdit:
        edit = QLineEdit()
        edit.setMaximumHeight(26)
        return edit

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_save_meta = QPushButton("Guardar datos")
        self.btn_delete_file = QPushButton("Borrar archivo")
        self.btn_delete_study = QPushButton("Borrar estudio")
        self.btn_open_folder = QPushButton("Abrir carpeta")
        self.btn_save_draw = QPushButton("Guardar dibujo")
        for btn in (
            self.btn_refresh,
            self.btn_save_meta,
            self.btn_delete_file,
            self.btn_delete_study,
            self.btn_open_folder,
            self.btn_save_draw,
        ):
            btn.setMaximumHeight(28)
            toolbar.addWidget(btn)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Estudios"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Estudio", "Detalle"])
        self.tree.setColumnWidth(0, 180)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        # Formulario compacto (2 columnas) en scroll de altura limitada
        form_box = QGroupBox("Datos del estudio")
        form_box.setFlat(True)
        grid = QGridLayout(form_box)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        self.ed_patient_id = self._compact_line()
        self.ed_animal_name = self._compact_line()
        self.ed_species = self._compact_line()
        self.ed_breed = self._compact_line()
        self.ed_sex = self._compact_line()
        self.ed_age = self._compact_line()
        self.ed_weight = self._compact_line()
        self.ed_owner = self._compact_line()
        self.ed_vet = self._compact_line()
        self.ed_clinic = self._compact_line()
        self.ed_birth = self._compact_line()
        self.combo_type = QComboBox()
        self.combo_type.addItems(STUDY_TYPE_CHOICES)
        self.combo_type.setEditable(True)
        self.combo_type.setMaximumHeight(26)
        self.ed_organ = self._compact_line()
        self.ed_obs = self._compact_line()
        self.ed_obs.setPlaceholderText("Observaciones")

        rows_left = [
            ("ID", self.ed_patient_id),
            ("Nombre", self.ed_animal_name),
            ("Especie", self.ed_species),
            ("Raza", self.ed_breed),
            ("Sexo", self.ed_sex),
            ("Edad", self.ed_age),
            ("Peso kg", self.ed_weight),
        ]
        rows_right = [
            ("Dueño", self.ed_owner),
            ("Veterinario", self.ed_vet),
            ("Clínica", self.ed_clinic),
            ("Nac. YYYYMMDD", self.ed_birth),
            ("Tipo", self.combo_type),
            ("Órgano", self.ed_organ),
            ("Observaciones", self.ed_obs),
        ]
        for i, (label, widget) in enumerate(rows_left):
            grid.addWidget(QLabel(label), i, 0)
            grid.addWidget(widget, i, 1)
        for i, (label, widget) in enumerate(rows_right):
            grid.addWidget(QLabel(label), i, 2)
            grid.addWidget(widget, i, 3)

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setWidget(form_box)
        form_scroll.setMaximumHeight(170)
        form_scroll.setMinimumHeight(120)
        form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_layout.addWidget(form_scroll)

        bottom = QSplitter(Qt.Orientation.Horizontal)

        files_panel = QWidget()
        files_col = QVBoxLayout(files_panel)
        files_col.setContentsMargins(0, 0, 0, 0)
        files_col.addWidget(QLabel("Archivos DICOM"))
        self.file_list = QListWidget()
        self.file_list.setMaximumWidth(220)
        files_col.addWidget(self.file_list, stretch=2)
        self.meta_extra = QTextEdit()
        self.meta_extra.setReadOnly(True)
        self.meta_extra.setMaximumHeight(90)
        self.meta_extra.setPlaceholderText("Tags DICOM")
        files_col.addWidget(self.meta_extra, stretch=1)
        bottom.addWidget(files_panel)

        draw_panel = QWidget()
        draw_col = QVBoxLayout(draw_panel)
        draw_col.setContentsMargins(0, 0, 0, 0)
        tools = QHBoxLayout()
        tools.addWidget(QLabel("Color:"))
        self.combo_color = QComboBox()
        for name in self.COLORS:
            self.combo_color.addItem(name)
        self.combo_color.setMaximumWidth(100)
        tools.addWidget(self.combo_color)
        tools.addWidget(QLabel("Grosor:"))
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(1, 24)
        self.slider_width.setValue(4)
        self.slider_width.setMinimumWidth(100)
        self.slider_width.setMaximumHeight(22)
        self.slider_width.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: none; height: 4px; background: #9e9e9e; border-radius: 2px;
            }
            QSlider::sub-page:horizontal { background: #1976d2; border-radius: 2px; }
            QSlider::add-page:horizontal { background: #cfcfcf; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #fff; border: 2px solid #1976d2;
                width: 14px; height: 14px; margin: -6px 0; border-radius: 8px;
            }
            """
        )
        tools.addWidget(self.slider_width)
        self.lbl_width = QLabel("4 px")
        tools.addWidget(self.lbl_width)
        self.btn_pen = QPushButton("Lápiz")
        self.btn_eraser = QPushButton("Borrar trazo")
        self.btn_undo = QPushButton("Deshacer")
        self.btn_clear_draw = QPushButton("Limpiar")
        for b in (self.btn_pen, self.btn_eraser, self.btn_undo, self.btn_clear_draw):
            b.setMaximumHeight(26)
            tools.addWidget(b)
        tools.addStretch(1)
        draw_col.addLayout(tools)

        self.canvas = AnnotateCanvas()
        self.canvas.setMinimumHeight(220)
        draw_col.addWidget(self.canvas, stretch=1)
        bottom.addWidget(draw_panel)
        bottom.setStretchFactor(0, 1)
        bottom.setStretchFactor(1, 4)

        right_layout.addWidget(bottom, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([260, 740])
        root.addWidget(splitter, stretch=1)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_save_meta.clicked.connect(self.save_metadata)
        self.btn_delete_file.clicked.connect(self.delete_selected_file)
        self.btn_delete_study.clicked.connect(self.delete_selected_study)
        self.btn_open_folder.clicked.connect(self.open_study_folder)
        self.btn_save_draw.clicked.connect(self.save_drawing)
        self.tree.currentItemChanged.connect(self._on_study_selected)
        self.file_list.currentItemChanged.connect(self._on_file_selected)
        self.combo_color.currentTextChanged.connect(self._on_color)
        self.slider_width.valueChanged.connect(self._on_width)
        self.btn_pen.clicked.connect(lambda: self.canvas.set_eraser(False))
        self.btn_eraser.clicked.connect(lambda: self.canvas.set_eraser(True))
        self.btn_undo.clicked.connect(self.canvas.undo)
        self.btn_clear_draw.clicked.connect(self.canvas.clear_drawings)
        self._on_color(self.combo_color.currentText())
        self._on_width(self.slider_width.value())

    def _on_color(self, name: str) -> None:
        self.canvas.set_pen_color(self.COLORS.get(name, QColor(255, 40, 40)))

    def _on_width(self, value: int) -> None:
        self.canvas.set_pen_width(value)
        self.lbl_width.setText(f"{value} px")

    def _clear_form(self) -> None:
        for w in (
            self.ed_patient_id,
            self.ed_animal_name,
            self.ed_species,
            self.ed_breed,
            self.ed_sex,
            self.ed_age,
            self.ed_weight,
            self.ed_owner,
            self.ed_vet,
            self.ed_clinic,
            self.ed_birth,
            self.ed_organ,
            self.ed_obs,
        ):
            w.clear()
        self.combo_type.setCurrentIndex(0)
        self._current_detail = None

    def _fill_form(self, detail: dict[str, Any]) -> None:
        self._current_detail = detail
        self.ed_patient_id.setText(str(detail.get("patient_id") or ""))
        self.ed_animal_name.setText(str(detail.get("animal_name") or ""))
        self.ed_species.setText(str(detail.get("species") or ""))
        self.ed_breed.setText(str(detail.get("breed") or ""))
        self.ed_sex.setText(str(detail.get("sex") or ""))
        self.ed_age.setText(str(detail.get("age") or ""))
        weight = detail.get("weight_kg")
        self.ed_weight.setText("" if weight is None else str(weight))
        self.ed_owner.setText(str(detail.get("owner") or ""))
        self.ed_vet.setText(str(detail.get("veterinarian") or ""))
        self.ed_clinic.setText(str(detail.get("clinic") or ""))
        self.ed_birth.setText(str(detail.get("birth_date") or ""))
        stype = str(detail.get("study_type") or "")
        idx = self.combo_type.findText(stype)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        else:
            self.combo_type.setEditText(stype)
        self.ed_organ.setText(str(detail.get("organ") or ""))
        self.ed_obs.setText(str(detail.get("observations") or ""))

    def _form_patient_study(self) -> tuple[Patient, Study]:
        weight_raw = self.ed_weight.text().strip().replace(",", ".")
        try:
            weight = float(weight_raw) if weight_raw else None
        except ValueError:
            weight = None
        patient = Patient(
            patient_id=self.ed_patient_id.text().strip(),
            animal_name=self.ed_animal_name.text().strip(),
            species=self.ed_species.text().strip(),
            breed=self.ed_breed.text().strip(),
            sex=self.ed_sex.text().strip(),
            age=self.ed_age.text().strip(),
            weight_kg=weight,
            owner=self.ed_owner.text().strip(),
            veterinarian=self.ed_vet.text().strip(),
            clinic=self.ed_clinic.text().strip(),
            birth_date=self.ed_birth.text().strip(),
        )
        study = Study(
            study_type=self.combo_type.currentText().strip(),
            organ=self.ed_organ.text().strip(),
            observations=self.ed_obs.text().strip(),
        )
        if self._current_detail:
            study.study_instance_uid = str(
                self._current_detail.get("study_instance_uid") or ""
            )
            study.series_instance_uid = str(
                self._current_detail.get("series_instance_uid") or ""
            )
            dt = self._current_detail.get("study_datetime")
            if dt:
                try:
                    study.study_datetime = datetime.fromisoformat(str(dt))
                except ValueError:
                    pass
        return patient, study

    def refresh(self) -> None:
        # Limpiar registros huérfanos (carpetas borradas a mano)
        try:
            purged = self.db.purge_orphaned_studies()
        except Exception:  # noqa: BLE001
            purged = 0

        self.tree.clear()
        self.file_list.clear()
        self.meta_extra.clear()
        self.canvas.clear_canvas()
        self._current_dicom = None
        self._clear_form()

        studies = self.db.list_recent_studies(limit=200)
        label_db = f"{len(studies)} estudio(s)"
        if purged:
            label_db += f" · {purged} huérfano(s) quitado(s)"
        root_db = QTreeWidgetItem(["Base de datos", label_db])
        self.tree.addTopLevelItem(root_db)
        for study in studies:
            label = (
                f"{study.get('patient_id', '')} — {study.get('animal_name', '')}"
            ).strip(" —")
            detail = (
                f"{study.get('study_datetime', '')} | "
                f"{study.get('study_type', '')} | "
                f"{study.get('image_count', 0)} img"
            )
            item = QTreeWidgetItem([label or "Estudio", detail])
            item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "db", "study": study})
            root_db.addChild(item)
        root_db.setExpanded(True)

        disk_root = QTreeWidgetItem(["Carpeta Estudios/", str(STUDIES_DIR)])
        self.tree.addTopLevelItem(disk_root)
        if STUDIES_DIR.is_dir():
            for patient_dir in sorted(STUDIES_DIR.iterdir()):
                if not patient_dir.is_dir():
                    continue
                p_item = QTreeWidgetItem([patient_dir.name, "paciente"])
                disk_root.addChild(p_item)
                for date_dir in sorted(patient_dir.iterdir(), reverse=True):
                    if not date_dir.is_dir():
                        continue
                    dcms = sorted(date_dir.glob("*.dcm"))
                    if not dcms:
                        continue
                    d_item = QTreeWidgetItem(
                        [date_dir.name, f"{len(dcms)} archivo(s)"]
                    )
                    d_item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        {
                            "kind": "folder",
                            "folder": str(date_dir),
                            "files": [str(p) for p in dcms],
                        },
                    )
                    p_item.addChild(d_item)
        disk_root.setExpanded(True)

    def _on_study_selected(
        self,
        current: Optional[QTreeWidgetItem],
        _previous: Optional[QTreeWidgetItem],
    ) -> None:
        self.file_list.clear()
        self.meta_extra.clear()
        self.canvas.clear_canvas()
        self._current_dicom = None
        if current is None:
            self._clear_form()
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            self._clear_form()
            return

        if data.get("kind") == "db":
            detail = self.db.get_study_detail(int(data["study"]["study_db_id"]))
            if not detail:
                return
            self._fill_form(detail)
            files = self._collect_files(detail)
            self._fill_file_list(files)
            if files:
                self.file_list.setCurrentRow(0)
            return

        if data.get("kind") == "folder":
            self._clear_form()
            files = [Path(p) for p in data.get("files", [])]
            self._fill_file_list(files)
            if files:
                try:
                    summary = read_dicom_summary(files[0])
                    self._fill_form_from_dicom_summary(summary, data.get("folder"))
                except Exception:  # noqa: BLE001
                    pass
                self.file_list.setCurrentRow(0)

    def _fill_form_from_dicom_summary(
        self, summary: dict[str, Any], folder: Optional[str]
    ) -> None:
        self._current_detail = {
            "study_db_id": None,
            "folder_path": folder,
            "study_instance_uid": summary.get("StudyInstanceUID"),
            "series_instance_uid": summary.get("SeriesInstanceUID"),
            "study_datetime": None,
        }
        self.ed_patient_id.setText(str(summary.get("PatientID") or ""))
        self.ed_animal_name.setText(
            str(summary.get("PatientName") or "").replace("^", " ")
        )
        self.ed_species.setText(str(summary.get("PatientSpeciesDescription") or ""))
        self.ed_breed.setText(str(summary.get("PatientBreedDescription") or ""))
        self.ed_sex.setText(str(summary.get("PatientSex") or ""))
        self.ed_age.setText(str(summary.get("PatientAge") or ""))
        self.ed_weight.setText(str(summary.get("PatientWeight") or ""))
        self.ed_owner.setText(str(summary.get("ResponsiblePerson") or ""))
        self.ed_vet.setText(
            str(summary.get("ReferringPhysicianName") or "").replace("^", " ")
        )
        self.ed_clinic.setText(str(summary.get("InstitutionName") or ""))
        self.ed_birth.setText(str(summary.get("PatientBirthDate") or ""))
        self.combo_type.setEditText(str(summary.get("StudyDescription") or ""))
        self.ed_organ.clear()
        self.ed_obs.clear()

    def _collect_files(self, detail: dict[str, Any]) -> list[Path]:
        files: list[Path] = []
        for img in detail.get("images") or []:
            dcm = img.get("dicom_path")
            if dcm and Path(dcm).is_file():
                files.append(Path(dcm))
        folder = detail.get("folder_path")
        if folder and Path(folder).is_dir():
            for p in sorted(Path(folder).glob("*.dcm")):
                if p not in files:
                    files.append(p)
        return files

    def _fill_file_list(self, files: list[Path]) -> None:
        self.file_list.clear()
        for path in files:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.file_list.addItem(item)

    def _on_file_selected(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            self._current_dicom = None
            self.canvas.clear_canvas()
            return
        path = Path(str(current.data(Qt.ItemDataRole.UserRole)))
        self._current_dicom = path
        if not path.is_file():
            self.meta_extra.setPlainText(f"No existe:\n{path}")
            self.canvas.clear_canvas()
            return
        try:
            summary = read_dicom_summary(path)
            self.meta_extra.setPlainText(format_summary_text(summary))
        except Exception as exc:  # noqa: BLE001
            self.meta_extra.setPlainText(f"Error leyendo DICOM: {exc}")

        rgb = dicom_pixel_rgb(path)
        if rgb is None:
            self.canvas.clear_canvas()
            return
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        self.canvas.load_pixmap(QPixmap.fromImage(image))

    def save_metadata(self) -> None:
        patient, study = self._form_patient_study()
        if not patient.patient_id or not patient.animal_name:
            QMessageBox.warning(
                self, "Datos", "Indique al menos ID paciente y Nombre del animal."
            )
            return

        files = self._files_for_current()
        try:
            if self._current_detail and self._current_detail.get("study_db_id"):
                weight_raw = self.ed_weight.text().strip().replace(",", ".")
                try:
                    weight = float(weight_raw) if weight_raw else None
                except ValueError:
                    weight = None
                self.db.update_study_fields(
                    int(self._current_detail["study_db_id"]),
                    {
                        "patient_id": patient.patient_id,
                        "animal_name": patient.animal_name,
                        "species": patient.species,
                        "breed": patient.breed,
                        "sex": patient.sex,
                        "age": patient.age,
                        "weight_kg": weight,
                        "owner": patient.owner,
                        "veterinarian": patient.veterinarian,
                        "clinic": patient.clinic,
                        "birth_date": patient.birth_date,
                    },
                    {
                        "study_type": study.study_type,
                        "organ": study.organ,
                        "observations": study.observations,
                    },
                )
            for path in files:
                if path.is_file():
                    update_dicom_metadata(path, patient, study)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al guardar", str(exc))
            return

        QMessageBox.information(
            self,
            "Guardado",
            f"Datos actualizados en la base y en {len(files)} archivo(s) DICOM.",
        )
        if self._current_dicom and self._current_dicom.is_file():
            try:
                self.meta_extra.setPlainText(
                    format_summary_text(read_dicom_summary(self._current_dicom))
                )
            except Exception:  # noqa: BLE001
                pass
        self.refresh()

    def save_drawing(self) -> None:
        if self._current_dicom is None or not self._current_dicom.is_file():
            QMessageBox.information(
                self, "Dibujo", "Seleccione un archivo DICOM para dibujar."
            )
            return
        if not self.canvas.has_image():
            QMessageBox.information(self, "Dibujo", "No hay imagen cargada.")
            return
        rgb = self.canvas.composite_rgb()
        if rgb is None:
            QMessageBox.warning(self, "Dibujo", "No se pudo obtener la imagen anotada.")
            return
        try:
            save_rgb_into_dicom(self._current_dicom, rgb)
            self._on_file_selected(self.file_list.currentItem(), None)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al guardar dibujo", str(exc))
            return
        QMessageBox.information(
            self,
            "Dibujo guardado",
            f"Anotación guardada en:\n{self._current_dicom.name}",
        )

    def delete_selected_file(self) -> None:
        path = self._current_dicom
        if path is None or not path.is_file():
            QMessageBox.information(self, "Borrar", "Seleccione un archivo DICOM.")
            return
        confirm = QMessageBox.question(
            self,
            "Borrar archivo",
            f"¿Borrar permanentemente?\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_image_record(str(path))
            path.unlink()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.refresh()
        QMessageBox.information(self, "Borrado", "Archivo DICOM eliminado.")

    def delete_selected_study(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            QMessageBox.information(self, "Borrar", "Seleccione un estudio.")
            return
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}

        if data.get("kind") == "db":
            study = data["study"]
            confirm = QMessageBox.question(
                self,
                "Borrar estudio",
                f"¿Borrar el estudio de {study.get('animal_name')} "
                f"y sus archivos DICOM?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            try:
                self.db.delete_study(int(study["study_db_id"]), delete_files=True)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", str(exc))
                return
            self.refresh()
            QMessageBox.information(self, "Borrado", "Estudio eliminado.")
            return

        if data.get("kind") == "folder":
            folder = Path(data["folder"])
            files = list(folder.glob("*.dcm")) if folder.is_dir() else []
            confirm = QMessageBox.question(
                self,
                "Borrar carpeta",
                f"¿Borrar {len(files)} archivo(s) DICOM en?\n{folder}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            for path in files:
                try:
                    self.db.delete_image_record(str(path))
                    path.unlink()
                except OSError:
                    pass
            self.refresh()
            QMessageBox.information(self, "Borrado", "Archivos de la carpeta eliminados.")
            return

        QMessageBox.information(
            self,
            "Borrar",
            "Seleccione un estudio de la base de datos o una carpeta de fecha.",
        )

    def _files_for_current(self) -> list[Path]:
        files: list[Path] = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item is None:
                continue
            path = Path(str(item.data(Qt.ItemDataRole.UserRole)))
            if path.is_file():
                files.append(path)
        if not files and self._current_dicom and self._current_dicom.is_file():
            files.append(self._current_dicom)
        return files

    def _selected_folder(self) -> Optional[Path]:
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("kind") == "folder":
            return Path(data["folder"])
        if data.get("kind") == "db":
            folder = (data.get("study") or {}).get("folder_path")
            return Path(folder) if folder else None
        if self._current_detail and self._current_detail.get("folder_path"):
            return Path(str(self._current_detail["folder_path"]))
        if self._current_dicom:
            return self._current_dicom.parent
        return None

    def open_study_folder(self) -> None:
        folder = self._selected_folder()
        if folder is None or not folder.exists():
            QMessageBox.information(self, "Carpeta", "No hay carpeta seleccionada.")
            return
        path = str(folder)
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
