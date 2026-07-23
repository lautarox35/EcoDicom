"""Ventana principal de EcoDICOM."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from app.device.capture import CameraDevice, list_camera_devices, save_bgr_frame
from app.device.easycap import easycap_status_message
from app.device.welld_wed3100 import ConnectionStatus, connect_wed3100
from app.models.image import CapturedImage
from app.storage.database import Database
from app.storage.filesystem import export_study_dicoms
from app.ui.widgets.image_preview import ImagePreview
from app.ui.widgets.live_preview import LivePreview
from app.ui.widgets.patient_form import PatientForm
from app.ui.widgets.study_form import StudyForm


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle("EcoDICOM - Ecografía veterinaria a DICOM")
        self.resize(1280, 800)
        self._cameras: list[CameraDevice] = []
        self._build()
        self.refresh_capture_devices()

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        panels = QHBoxLayout()
        self.patient_form = PatientForm()

        center = QVBoxLayout()
        self.live_preview = LivePreview()
        self.image_preview = ImagePreview()
        center.addWidget(self.live_preview, stretch=3)
        center.addWidget(self.image_preview, stretch=2)
        center_wrap = QWidget()
        center_wrap.setLayout(center)

        self.study_form = StudyForm()

        panels.addWidget(self.patient_form, stretch=2)
        panels.addWidget(center_wrap, stretch=4)
        panels.addWidget(self.study_form, stretch=2)
        root.addLayout(panels, stretch=1)

        capture_row = QHBoxLayout()
        capture_row.addWidget(QLabel("Capturadora:"))
        self.combo_camera = QComboBox()
        self.combo_camera.setMinimumWidth(280)
        self.btn_refresh_cameras = QPushButton("Actualizar dispositivos")
        self.btn_start_preview = QPushButton("Iniciar vista en vivo")
        capture_row.addWidget(self.combo_camera, stretch=1)
        capture_row.addWidget(self.btn_refresh_cameras)
        capture_row.addWidget(self.btn_start_preview)
        self.chk_enhance = QCheckBox("Mejorar calidad")
        self.chk_enhance.setChecked(True)
        self.chk_enhance.setToolTip(
            "Contraste (CLAHE), nitidez y upscale al capturar para DICOM."
        )
        capture_row.addWidget(self.chk_enhance)
        root.addLayout(capture_row)

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

        self.capture_label = QLabel("easierCAP: —")
        self.capture_label.setStyleSheet("color: #666;")
        root.addWidget(self.capture_label)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(
            "Elija AV TO USB2.0 [easierCAP] y pulse Iniciar vista en vivo."
        )

        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_import.clicked.connect(self.on_import)
        self.btn_capture.clicked.connect(self.on_capture)
        self.btn_create.clicked.connect(self.on_create_dicom)
        self.btn_save.clicked.connect(self.on_save_study)
        self.btn_refresh_cameras.clicked.connect(self.refresh_capture_devices)
        self.btn_start_preview.clicked.connect(self.start_live_preview)
        self.combo_camera.currentIndexChanged.connect(self._on_camera_changed)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.live_preview.stop()
        super().closeEvent(event)

    def _selected_camera(self) -> CameraDevice | None:
        index = self.combo_camera.currentData()
        if index is None:
            return None
        for cam in self._cameras:
            if cam.index == int(index):
                return cam
        return None

    def start_live_preview(self) -> None:
        cam = self._selected_camera()
        if cam is None:
            QMessageBox.warning(
                self,
                "Vista en vivo",
                "No hay capturadora seleccionada. Elija AV TO USB2.0 [easierCAP].",
            )
            return
        self.live_preview.start(
            camera_index=cam.index,
            backend=cam.backend,
            for_easycap=cam.is_easycap,
        )
        self.statusBar().showMessage(f"Vista en vivo: {cam.label}")

    def _on_camera_changed(self, _row: int) -> None:
        if self._selected_camera() is not None and self.live_preview.is_running():
            self.start_live_preview()

    def refresh_capture_devices(self) -> None:
        self.live_preview.stop()
        previous = self.combo_camera.currentData()
        self.combo_camera.blockSignals(True)
        self.combo_camera.clear()
        self._cameras = list_camera_devices()

        detected, msg = easycap_status_message()
        color = "#2e7d32" if detected else "#c62828"
        self.capture_label.setText(msg)
        self.capture_label.setStyleSheet(f"color: {color};")

        if not self._cameras:
            self.combo_camera.addItem("(sin dispositivos de video)", None)
            self.btn_capture.setEnabled(False)
            self.combo_camera.blockSignals(False)
            self.statusBar().showMessage(
                "Sin capturadora. Conecte la easierCAP y pulse Actualizar dispositivos."
            )
            return

        preferred_row = 0
        for i, cam in enumerate(self._cameras):
            self.combo_camera.addItem(cam.label, cam.index)
            if cam.is_easycap:
                preferred_row = i

        if previous is not None:
            idx = self.combo_camera.findData(previous)
            if idx >= 0:
                preferred_row = idx

        self.combo_camera.setCurrentIndex(preferred_row)
        self.combo_camera.blockSignals(False)
        self.btn_capture.setEnabled(True)
        current = self._cameras[preferred_row]
        self.statusBar().showMessage(f"Capturadora lista: {current.label}")
        self.start_live_preview()

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
        self.refresh_capture_devices()

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
        # Preferir el frame de la vista en vivo (evita conflicto de dispositivo en Windows)
        frame = self.live_preview.latest_frame()
        if frame is None:
            cam = self._selected_camera()
            if cam is None:
                QMessageBox.warning(
                    self,
                    "Captura",
                    "No hay capturadora seleccionada. Conecte la easierCAP y actualice dispositivos.",
                )
                return
            self.start_live_preview()
            QMessageBox.information(
                self,
                "Captura",
                "Se inició la vista en vivo. Cuando vea la imagen del ecógrafo, "
                "pulse otra vez Capturar imagen.",
            )
            return
        try:
            path = save_bgr_frame(frame, enhance=self.chk_enhance.isChecked())
        except RuntimeError as exc:
            QMessageBox.warning(self, "Captura", str(exc))
            return
        self.image_preview.add_image(CapturedImage(path=path, source="capture"))
        self.statusBar().showMessage(
            f"Captura guardada: {path.name} — puede dibujar sobre ella abajo."
        )

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
        self.image_preview.save_current_annotation(silent=True)
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
        self.image_preview.save_current_annotation(silent=True)
        if not self._validate_ready():
            return
        patient = self.patient_form.get_patient()
        study = self.study_form.get_study()
        images = self.image_preview.images()

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
