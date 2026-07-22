"""Ventana principal de EcoDICOM."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_CAMERA_INDEX
from app.device.capture import capture_frame
from app.device.welld_wed3100 import ConnectionStatus, connect_wed3100
from app.models.image import CapturedImage
from app.storage.database import Database
from app.storage.filesystem import export_study_dicoms
from app.ui.widgets.image_preview import ImagePreview
from app.ui.widgets.patient_form import PatientForm
from app.ui.widgets.study_form import StudyForm


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle("EcoDICOM - Ecografía veterinaria a DICOM")
        self.resize(1200, 720)
        self._build()

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        panels = QHBoxLayout()
        self.patient_form = PatientForm()
        self.image_preview = ImagePreview()
        self.study_form = StudyForm()

        panels.addWidget(self.patient_form, stretch=2)
        panels.addWidget(self.image_preview, stretch=3)
        panels.addWidget(self.study_form, stretch=2)
        root.addLayout(panels, stretch=1)

        buttons = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ecógrafo")
        self.btn_import = QPushButton("Importar imagen")
        self.btn_capture = QPushButton("Capturar imagen")
        self.btn_create = QPushButton("Crear DICOM")
        self.btn_save = QPushButton("Guardar estudio")

        for btn in (
            self.btn_connect,
            self.btn_import,
            self.btn_capture,
            self.btn_create,
            self.btn_save,
        ):
            buttons.addWidget(btn)
        root.addLayout(buttons)

        self.device_label = QLabel("Estado ecógrafo: Desconectado")
        self.device_label.setStyleSheet("color: #666;")
        root.addWidget(self.device_label)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Listo — priorice Importar imagen mientras no haya protocolo USB.")

        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_capture.clicked.connect(self.on_capture)
        self.btn_create.clicked.connect(self.on_create_dicom)
        self.btn_save.clicked.connect(self.on_save_study)

    def on_connect(self) -> None:
        result = connect_wed3100()
        self.device_label.setText(f"Estado ecógrafo: {result.status.value}")
        icon = QMessageBox.Icon.Information
        if result.status == ConnectionStatus.ERROR:
            icon = QMessageBox.Icon.Warning
        elif result.status == ConnectionStatus.DISCONNECTED:
            icon = QMessageBox.Icon.Information
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle("Conexión Well-D WED-3100")
        msg.setText(result.message)
        msg.exec()
        self.statusBar().showMessage(result.status.value)

    def on_import(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar imágenes",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Todos (*.*)",
        )
        if not paths:
            return
        for p in paths:
            self.image_preview.add_image(CapturedImage(path=Path(p), source="import"))
        self.statusBar().showMessage(f"Importadas {len(paths)} imagen(es).")

    def on_capture(self) -> None:
        try:
            path = capture_frame(DEFAULT_CAMERA_INDEX)
        except RuntimeError as exc:
            QMessageBox.warning(self, "Captura", str(exc))
            return
        self.image_preview.add_image(CapturedImage(path=path, source="capture"))
        self.statusBar().showMessage(f"Captura guardada: {path.name}")

    def _validate_ready(self) -> bool:
        patient = self.patient_form.get_patient()
        if not patient.animal_name or not patient.patient_id:
            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Indique al menos Nombre del animal e ID paciente.",
            )
            return False
        if not self.image_preview.images():
            QMessageBox.warning(
                self,
                "Sin imágenes",
                "Importe o capture al menos una imagen antes de continuar.",
            )
            return False
        return True

    def on_create_dicom(self) -> None:
        if not self._validate_ready():
            return
        patient = self.patient_form.get_patient()
        study = self.study_form.get_study()
        try:
            folder, exported = export_study_dicoms(
                patient, study, self.image_preview.images()
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error DICOM", str(exc))
            return

        self.study_form.set_uids(study.study_instance_uid, study.series_instance_uid)
        # Refresh preview list with dicom paths
        self.image_preview.clear()
        for img in exported:
            self.image_preview.add_image(img)

        QMessageBox.information(
            self,
            "DICOM creado",
            f"Se generaron {len(exported)} archivo(s) en:\n{folder}",
        )
        self.statusBar().showMessage(f"DICOM en {folder}")

    def on_save_study(self) -> None:
        if not self._validate_ready():
            return
        patient = self.patient_form.get_patient()
        study = self.study_form.get_study()
        images = self.image_preview.images()

        # Si aún no hay DICOM, generarlos
        if any(img.dicom_path is None for img in images):
            try:
                folder, exported = export_study_dicoms(patient, study, images)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error al guardar", str(exc))
                return
            self.image_preview.clear()
            for img in exported:
                self.image_preview.add_image(img)
            images = exported
        else:
            from app.storage.filesystem import study_folder

            folder = study_folder(patient, study)

        self.study_form.set_uids(study.study_instance_uid, study.series_instance_uid)

        image_rows = [
            {
                "source_path": str(img.path),
                "dicom_path": str(img.dicom_path) if img.dicom_path else None,
                "sop_instance_uid": img.sop_instance_uid,
                "source": img.source,
            }
            for img in images
        ]
        try:
            self.db.save_study(patient, study, folder, image_rows)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error base de datos", str(exc))
            return

        QMessageBox.information(
            self,
            "Estudio guardado",
            f"Estudio guardado en la base de datos y en:\n{folder}",
        )
        self.statusBar().showMessage("Estudio guardado correctamente.")
