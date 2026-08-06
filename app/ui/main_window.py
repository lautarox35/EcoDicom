"""Ventana principal de EcoDICOM."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_VERSION
from app.device.capture import CameraDevice, list_camera_devices, save_bgr_frame
from app.device.easycap import easycap_status_message
from app.models.image import CapturedImage
from app.storage.database import Database
from app.storage.filesystem import export_study_dicoms
from app.ui.widgets.image_preview import ImagePreview
from app.ui.widgets.live_preview import LivePreview
from app.ui.widgets.patient_form import PatientForm
from app.ui.widgets.studies_browser import StudiesBrowserDialog
from app.ui.widgets.study_form import StudyForm
from app.update_check import RELEASES_PAGE, check_latest_release


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle(f"EcoDICOM {APP_VERSION} - Ecografía veterinaria a DICOM")
        self.resize(1280, 800)
        self._cameras: list[CameraDevice] = []
        self._build()
        self.refresh_capture_devices()

    def _build(self) -> None:
        help_menu = self.menuBar().addMenu("Ayuda")
        act_updates = help_menu.addAction("Buscar actualizaciones…")
        act_updates.triggered.connect(self.on_check_updates)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        panels = QSplitter(Qt.Orientation.Horizontal)
        panels.setChildrenCollapsible(False)
        panels.setHandleWidth(6)
        panels.setStyleSheet(
            "QSplitter::handle { background: #c5c5c5; }"
            "QSplitter::handle:hover { background: #1976d2; }"
        )

        self.patient_form = PatientForm()
        self.patient_form.setMinimumWidth(200)

        # Vista en vivo / capturas: divisor vertical arrastrable
        center_split = QSplitter(Qt.Orientation.Vertical)
        center_split.setChildrenCollapsible(False)
        center_split.setHandleWidth(6)
        center_split.setStyleSheet(
            "QSplitter::handle { background: #c5c5c5; }"
            "QSplitter::handle:hover { background: #1976d2; }"
        )
        self.live_preview = LivePreview()
        self.image_preview = ImagePreview()
        self.live_preview.setMinimumHeight(120)
        self.image_preview.setMinimumHeight(160)
        # Al redimensionar la ventana: capturas crecen; live mantiene su alto
        # (el usuario puede cambiar la proporción arrastrando el divisor).
        self.live_preview.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self.image_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        center_split.addWidget(self.live_preview)
        center_split.addWidget(self.image_preview)
        center_split.setStretchFactor(0, 0)
        center_split.setStretchFactor(1, 1)
        center_split.setSizes([240, 480])

        # Columna derecha: estudio + herramientas de acción
        right = QWidget()
        right.setMinimumWidth(220)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.study_form = StudyForm()
        right_layout.addWidget(self.study_form)

        tools = QGroupBox("Herramientas")
        tools_layout = QVBoxLayout(tools)
        tools_layout.setSpacing(6)

        self.btn_import = QPushButton("Importar imagen")
        self.btn_import.setToolTip("Abrir imágenes desde disco (PNG, JPG, etc.).")
        self.btn_capture = QPushButton("Capturar imagen")
        self.btn_capture.setToolTip("Congela el frame actual de la vista en vivo.")
        self.btn_create = QPushButton("1. Crear DICOM")
        self.btn_create.setToolTip(
            "Genera los archivos .dcm y los registra en la base local."
        )
        self.btn_create.setStyleSheet(
            "QPushButton { font-weight: 600; padding: 8px 12px; }"
        )
        self.btn_save = QPushButton("2. Guardar estudio")
        self.btn_save.setToolTip(
            "Guarda el estudio. Si aún no hay DICOM, los crea automáticamente."
        )
        self.btn_studies = QPushButton("Ver estudios")
        self.btn_studies.setToolTip("Abrir, editar o anotar estudios ya guardados.")

        for btn in (
            self.btn_import,
            self.btn_capture,
            self.btn_create,
            self.btn_save,
            self.btn_studies,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(32)
            tools_layout.addWidget(btn)

        right_layout.addWidget(tools)
        right_layout.addStretch(1)

        panels.addWidget(self.patient_form)
        panels.addWidget(center_split)
        panels.addWidget(right)
        panels.setStretchFactor(0, 0)
        panels.setStretchFactor(1, 1)
        panels.setStretchFactor(2, 0)
        panels.setSizes([280, 720, 280])
        root.addWidget(panels, stretch=1)

        self._view_splitter = center_split
        self._main_splitter = panels

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

        self.capture_label = QLabel("easierCAP: —")
        self.capture_label.setStyleSheet("color: #666;")
        root.addWidget(self.capture_label)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(
            "Elija AV TO USB2.0 [easierCAP] → Iniciar vista en vivo → Capturar → Crear DICOM."
        )

        self.btn_import.clicked.connect(self.on_import)
        self.btn_capture.clicked.connect(self.on_capture)
        self.btn_create.clicked.connect(self.on_create_dicom)
        self.btn_save.clicked.connect(self.on_save_study)
        self.btn_studies.clicked.connect(self.on_view_studies)
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

        image_rows = [
            {
                "source_path": str(img.path),
                "dicom_path": str(img.dicom_path) if img.dicom_path else None,
                "sop_instance_uid": img.sop_instance_uid,
                "source": img.source,
            }
            for img in exported
        ]
        try:
            self.db.save_study(patient, study, folder, image_rows)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self,
                "DICOM creado",
                f"Archivos generados en:\n{folder}\n\n"
                f"No se pudo registrar en la base local: {exc}",
            )
            self.statusBar().showMessage(f"DICOM en {folder} (sin registro DB)")
            return

        QMessageBox.information(
            self,
            "DICOM creado",
            f"Se generaron {len(exported)} archivo(s) en:\n{folder}\n\n"
            "Ya puede verlos en «Ver estudios DICOM».",
        )
        self.statusBar().showMessage(f"DICOM en {folder}")

    def on_view_studies(self) -> None:
        dialog = StudiesBrowserDialog(self.db, parent=self)
        dialog.exec()

    def on_check_updates(self) -> None:
        self.statusBar().showMessage("Consultando GitHub Releases…")
        info = check_latest_release()
        self.statusBar().showMessage(info.message.split("\n")[0])

        if info.update_available:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Actualización disponible")
            box.setText(info.message)
            box.setInformativeText(
                "Se abrirá la página de Releases para descargar el zip."
            )
            open_btn = box.addButton(
                "Abrir Releases", QMessageBox.ButtonRole.AcceptRole
            )
            box.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is open_btn:
                QDesktopServices.openUrl(QUrl(info.html_url or RELEASES_PAGE))
            return

        # Sin update o error de red: mensaje simple + opción de abrir Releases
        box = QMessageBox(self)
        box.setIcon(
            QMessageBox.Icon.Warning
            if info.message.startswith("Sin conexión")
            or "HTTP" in info.message
            or "No hay releases" in info.message
            else QMessageBox.Icon.Information
        )
        box.setWindowTitle("Buscar actualizaciones")
        box.setText(info.message)
        open_btn = box.addButton("Abrir Releases", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl(info.html_url or RELEASES_PAGE))

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
